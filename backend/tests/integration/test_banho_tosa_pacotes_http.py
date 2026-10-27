"""Fluxos HTTP com banco isolado: pacote, agenda, check-in e cancelamento.

Não acessa o ERP remoto, não envia lembretes e não registra pagamentos reais.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import (
    especie_raca_mestre_models,  # noqa: F401
    produto_identidade_models,  # noqa: F401
    vendas_devolucoes_models,  # noqa: F401
)
from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api import agenda_routes
from app.banho_tosa_models import (
    BanhoTosaAtendimento,
    BanhoTosaPacoteMovimento,
    BanhoTosaPacoteCredito,
    BanhoTosaServico,
)
from app.banho_tosa_routes import router
from app.db import get_session
from app.models import Cliente, Pet
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda, VendaPagamento
from app import rotas_entrega_models  # noqa: F401
from fastapi import HTTPException
from app import banho_tosa_cancelamento


@pytest.fixture
def fluxo(db_session, tenant_factory, user_factory, monkeypatch):
    db_session.join_transaction_mode = "create_savepoint"
    tenant = tenant_factory(nome="Banho e Tosa HTTP QA")
    tenant_id = UUID(str(tenant.id))
    user = user_factory(tenant_id=tenant_id)
    tutor = Cliente(
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tutor QA",
        codigo="TUTOR-BT-HTTP",
        is_cliente=True,
        ativo=True,
    )
    db_session.add(tutor)
    db_session.flush()
    pet = Pet(
        tenant_id=tenant_id,
        user_id=user.id,
        cliente_id=tutor.id,
        codigo="PET-BT-HTTP",
        nome="Pet QA",
        especie="Cao",
        ativo=True,
    )
    banho = BanhoTosaServico(
        tenant_id=tenant_id,
        nome="Banho QA",
        preco_base=50,
        duracao_padrao_minutos=30,
    )
    tosa = BanhoTosaServico(
        tenant_id=tenant_id,
        nome="Tosa QA",
        preco_base=80,
        duracao_padrao_minutos=30,
    )
    db_session.add_all([pet, banho, tosa])
    db_session.flush()
    identidade = {"tenant_id": tenant_id, "user": user}

    def sessao():
        set_current_tenant(identidade["tenant_id"])
        try:
            yield db_session
        finally:
            clear_current_tenant()

    def autenticado():
        set_current_tenant(identidade["tenant_id"])
        return identidade["user"], identidade["tenant_id"]

    monkeypatch.setattr(
        agenda_routes,
        "sincronizar_lembretes_agendamento_banho_tosa",
        lambda *args, **kwargs: None,
    )
    # Capacidade e notificações têm suas suítes próprias; aqui o foco é o saldo.
    monkeypatch.setattr(
        agenda_routes, "validar_capacidade_agenda", lambda *a, **k: None
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_current_user_and_tenant] = autenticado
    with TestClient(app) as client:
        yield SimpleNamespace(
            api=client,
            db=db_session,
            tenant_id=tenant_id,
            tutor=tutor,
            pet=pet,
            banho=banho,
            tosa=tosa,
            identidade=identidade,
        )


def enviar(f, caminho, payload, esperado=201):
    resposta = f.api.post(f"/banho-tosa/{caminho}", json=payload)
    assert resposta.status_code == esperado, resposta.text
    return resposta.json()


def contratar(f, nome_pacote="Mensal QA", **dados):
    pacote = enviar(
        f,
        "pacotes",
        {
            "nome": nome_pacote,
            "preco": "200.00",
            "validade_dias": 30,
            "servicos": [{"servico_id": f.banho.id, "quantidade_creditos": "4"}],
        },
    )
    return enviar(
        f,
        "pacotes/creditos",
        {
            "pacote_id": pacote["id"],
            "cliente_id": f.tutor.id,
            "pet_id": f.pet.id,
            **dados,
        },
    )


def agendar(f, servico=None, dia=None, quantidade="1", valor_unitario="50"):
    return enviar(
        f,
        "agendamentos",
        {
            "cliente_id": f.tutor.id,
            "pet_id": f.pet.id,
            "data_hora_inicio": datetime.combine(
                dia or date.today(), time(14)
            ).isoformat(),
            "servicos": [
                {
                    "servico_id": servico or f.banho.id,
                    "quantidade": quantidade,
                    "valor_unitario": valor_unitario,
                }
            ],
        },
    )


def saldo(f, credito_id):
    resposta = f.api.get("/banho-tosa/pacotes/creditos")
    assert resposta.status_code == 200, resposta.text
    return next(c for c in resposta.json() if c["id"] == credito_id)


def test_reserva_checkin_repetido_e_cancelamento_devolvem_um_credito(fluxo):
    f = fluxo
    credito = contratar(f)
    agendamento = agendar(f)
    reservado = saldo(f, credito["id"])
    assert Decimal(reservado["saldo_creditos"]) == 3
    assert Decimal(reservado["creditos_reservados"]) == 1
    assert Decimal(reservado["creditos_usados"]) == 0

    caminho = f"agendamentos/{agendamento['id']}/check-in"
    atendimento = enviar(f, caminho, {}, esperado=200)
    repetido = enviar(f, caminho, {}, esperado=200)
    assert repetido["id"] == atendimento["id"]
    consumido = saldo(f, credito["id"])
    assert Decimal(consumido["saldo_creditos"]) == 3
    assert Decimal(consumido["creditos_reservados"]) == 0
    assert Decimal(consumido["creditos_usados"]) == 1

    cancelar = f"atendimentos/{atendimento['id']}/cancelar-processo"
    enviar(f, cancelar, {"motivo": "Tutor precisou viajar"}, esperado=200)
    enviar(f, cancelar, {"motivo": "Tutor precisou viajar"}, esperado=200)
    devolvido = saldo(f, credito["id"])
    assert Decimal(devolvido["saldo_creditos"]) == 4
    assert Decimal(devolvido["creditos_usados"]) == 0


def test_cancelar_agendamento_devolve_reserva_e_servico_avulso_nao_usa_pacote(fluxo):
    f = fluxo
    credito = contratar(f)
    avulso = agendar(f, servico=f.tosa.id)
    assert Decimal(saldo(f, credito["id"])["saldo_creditos"]) == 4
    assert not any(s.get("pacote_credito_id") for s in avulso["servicos"])
    agendamento = agendar(f)
    resposta = f.api.patch(
        f"/banho-tosa/agendamentos/{agendamento['id']}/status",
        json={"status": "cancelado"},
    )
    assert resposta.status_code == 200, resposta.text
    devolvido = saldo(f, credito["id"])
    assert Decimal(devolvido["saldo_creditos"]) == 4
    assert Decimal(devolvido["creditos_reservados"]) == 0


def test_vencimento_preserva_saldo_e_prorrogacao_exige_motivo(fluxo):
    f = fluxo
    ontem = date.today() - timedelta(days=1)
    credito = contratar(
        f,
        data_inicio=(ontem - timedelta(days=30)).isoformat(),
        data_validade=ontem.isoformat(),
    )
    assert credito["vencido"] is True
    assert Decimal(credito["saldo_creditos"]) == 4
    agendamento = agendar(f)
    assert not any(s.get("pacote_credito_id") for s in agendamento["servicos"])
    caminho = f"/banho-tosa/pacotes/creditos/{credito['id']}/prorrogar"
    nova_validade = (date.today() + timedelta(days=7)).isoformat()
    resposta = f.api.post(caminho, json={"data_validade": nova_validade, "motivo": " "})
    assert resposta.status_code == 422
    resposta = f.api.post(
        caminho,
        json={
            "data_validade": nova_validade,
            "motivo": "Combinado: viagem do tutor",
        },
    )
    assert resposta.status_code == 200, resposta.text
    prorrogado = saldo(f, credito["id"])
    assert prorrogado["vencido"] is False
    assert Decimal(prorrogado["saldo_creditos"]) == 4
    set_current_tenant(f.tenant_id)
    movimentos = (
        f.db.query(BanhoTosaPacoteMovimento).filter_by(credito_id=credito["id"]).all()
    )
    assert any("viagem" in (m.observacoes or "") for m in movimentos)


def test_credito_exige_pet_e_contrato_nao_muda_com_edicao_catalogo(fluxo):
    f = fluxo
    credito = contratar(f)
    resposta = f.api.post(
        "/banho-tosa/pacotes/creditos",
        json={
            "pacote_id": credito["pacote_id"],
            "cliente_id": f.tutor.id,
        },
    )
    assert resposta.status_code == 422
    resposta = f.api.patch(
        f"/banho-tosa/pacotes/{credito['pacote_id']}",
        json={
            "servicos": [{"servico_id": f.tosa.id, "quantidade_creditos": "8"}],
        },
    )
    assert resposta.status_code == 200, resposta.text
    contrato = saldo(f, credito["id"])
    assert contrato["servicos"][0]["servico_id"] == f.banho.id
    assert Decimal(contrato["creditos_total"]) == 4


def test_cobranca_unica_em_aberto_nao_impede_reserva_ou_quita_pacote(fluxo):
    f = fluxo
    credito = contratar(f)
    caminho = f"pacotes/creditos/{credito['id']}/gerar-venda"
    venda = enviar(f, caminho, {}, esperado=200)
    repetida = enviar(f, caminho, {}, esperado=200)
    assert repetida["venda_id"] == venda["venda_id"]
    assert repetida["ja_existia"] is True
    aberto = saldo(f, credito["id"])
    assert aberto["status_pagamento"] == "pendente"
    assert Decimal(aberto["valor_pago"]) == 0
    assert Decimal(aberto["valor_restante"]) == 200
    agendar(f)
    reservado = saldo(f, credito["id"])
    assert Decimal(reservado["saldo_creditos"]) == 3
    assert reservado["status_pagamento"] == "pendente"
    assert Decimal(reservado["valor_restante"]) == 200


def test_encerramento_nao_apaga_historico_nem_cancela_cobranca(fluxo):
    f = fluxo
    credito = contratar(f)
    venda = enviar(f, f"pacotes/creditos/{credito['id']}/gerar-venda", {}, esperado=200)
    agendamento = agendar(f)
    caminho = f"/banho-tosa/pacotes/creditos/{credito['id']}/encerrar"
    resposta = f.api.post(caminho, json={"motivo": "Encerramento combinado"})
    assert resposta.status_code == 409
    resposta = f.api.patch(
        f"/banho-tosa/agendamentos/{agendamento['id']}/status",
        json={"status": "cancelado"},
    )
    assert resposta.status_code == 200, resposta.text
    resposta = f.api.post(caminho, json={"motivo": "Encerramento combinado"})
    assert resposta.status_code == 200, resposta.text
    encerrado = saldo(f, credito["id"])
    assert encerrado["status"] == "encerrado"
    assert Decimal(encerrado["saldo_creditos"]) == 0
    assert Decimal(encerrado["creditos_cancelados"]) == 4
    assert encerrado["venda_id"] == venda["venda_id"]
    assert encerrado["status_pagamento"] == "pendente"
    historico = f.api.get(f"/banho-tosa/pacotes/creditos/{credito['id']}/movimentos")
    assert historico.status_code == 200
    assert any(m["tipo"] == "encerramento" for m in historico.json())


def test_credito_de_outro_tenant_nao_pode_ser_lido_ou_alterado(
    fluxo, tenant_factory, user_factory
):
    f = fluxo
    credito = contratar(f)
    outro = tenant_factory(nome="Outra loja HTTP QA")
    outro_id = UUID(str(outro.id))
    outro_user = user_factory(tenant_id=outro_id)
    f.identidade.update(tenant_id=outro_id, user=outro_user)
    resposta = f.api.get("/banho-tosa/pacotes/creditos")
    assert resposta.status_code == 200
    assert resposta.json() == []
    for sufixo, dados in (
        (
            "prorrogar",
            {
                "data_validade": (date.today() + timedelta(days=90)).isoformat(),
                "motivo": "Tentativa outra loja",
            },
        ),
        ("encerrar", {"motivo": "Tentativa outra loja"}),
        ("gerar-venda", {}),
    ):
        resposta = f.api.post(
            f"/banho-tosa/pacotes/creditos/{credito['id']}/{sufixo}", json=dados
        )
        assert resposta.status_code == 404, resposta.text


def test_pacote_parcial_cobra_so_unidade_avulsa_e_taxi_sem_cancelar_contrato(fluxo):
    f = fluxo
    credito = contratar(f)
    cobranca_pacote = enviar(
        f, f"pacotes/creditos/{credito['id']}/gerar-venda", {}, esperado=200
    )
    agendamento = agendar(f, quantidade="5")
    assert Decimal(agendamento["servicos"][0]["pacote_quantidade"]) == 4
    enviar(f, "taxi-dog", {"agendamento_id": agendamento["id"], "valor_cobrado": "15"})
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    venda = enviar(f, f"atendimentos/{atendimento['id']}/venda", {}, esperado=200)
    assert Decimal(venda["total"]) == 65
    repetida = enviar(f, f"atendimentos/{atendimento['id']}/venda", {}, esperado=200)
    assert repetida["venda_id"] == venda["venda_id"]
    set_current_tenant(f.tenant_id)
    registro = f.db.query(Venda).filter_by(id=venda["venda_id"]).one()
    assert len(registro.itens) == 2
    assert sorted(Decimal(str(i.subtotal)) for i in registro.itens) == [15, 50]
    assert all(Decimal(str(i.quantidade)) == 1 for i in registro.itens)
    entrega = enviar(
        f,
        f"atendimentos/{atendimento['id']}/mover-etapa",
        {"tipo": "entregue", "iniciar_timer": False},
        esperado=200,
    )
    assert entrega["venda_id"] == venda["venda_id"]
    repetir_entrega = f.api.post(
        f"/banho-tosa/atendimentos/{atendimento['id']}/mover-etapa",
        json={"tipo": "entregue"},
    )
    assert repetir_entrega.status_code == 422
    cancelar = f"atendimentos/{atendimento['id']}/cancelar-processo"
    enviar(f, cancelar, {"motivo": "Atendimento lançado em duplicidade"}, esperado=200)
    enviar(f, cancelar, {"motivo": "Atendimento lançado em duplicidade"}, esperado=200)
    contrato = saldo(f, credito["id"])
    assert Decimal(contrato["saldo_creditos"]) == 4
    assert contrato["venda_id"] == cobranca_pacote["venda_id"]
    assert contrato["status_pagamento"] == "pendente"
    set_current_tenant(f.tenant_id)
    f.db.expire_all()
    assert f.db.query(Venda).filter_by(id=venda["venda_id"]).one().status == "cancelada"
    assert (
        f.db.query(Venda).filter_by(id=cobranca_pacote["venda_id"]).one().status
        != "cancelada"
    )


def test_entrega_zero_auditavel_nao_cria_venda_e_nao_volta_a_fila(fluxo):
    f = fluxo
    agendamento = agendar(f, valor_unitario="0")
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    caminho = f"/banho-tosa/atendimentos/{atendimento['id']}/mover-etapa"
    atalho = f.api.patch(
        f"/banho-tosa/atendimentos/{atendimento['id']}/status",
        json={"status": "entregue"},
    )
    assert atalho.status_code == 422
    sem_motivo = f.api.post(
        caminho, json={"tipo": "entregue", "entrega_sem_cobranca": True}
    )
    assert sem_motivo.status_code == 422
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert detalhe["status"] == "chegou"
    resposta = f.api.post(
        caminho,
        json={
            "tipo": "entregue",
            "iniciar_timer": False,
            "entrega_sem_cobranca": True,
            "motivo_sem_cobranca": "Cortesia autorizada",
        },
    )
    assert resposta.status_code == 200, resposta.text
    entregue = resposta.json()
    assert entregue["status"] == "entregue"
    assert entregue["venda_id"] is None
    assert entregue["entrega_sem_cobranca"] is True
    assert entregue["fechamento_alertas"] == []
    registro = next(
        o for o in entregue["ocorrencias"] if o["tipo"] == "entrega_sem_cobranca"
    )
    assert registro["created_by"] == f.identidade["user"].id
    assert "Cortesia autorizada" in registro["descricao"]
    protegido = f.api.delete(
        f"/banho-tosa/atendimentos/{atendimento['id']}/ocorrencias/{registro['id']}"
    )
    assert protegido.status_code == 422
    assert (
        f.api.post(
            caminho,
            json={
                "tipo": "entregue",
                "entrega_sem_cobranca": True,
                "motivo_sem_cobranca": "Repetido",
            },
        ).status_code
        == 422
    )
    assert (
        f.api.patch(
            f"/banho-tosa/atendimentos/{atendimento['id']}/status",
            json={"status": "chegou"},
        ).status_code
        == 422
    )
    pendencias = f.api.get("/banho-tosa/fechamentos/pendencias").json()
    assert not any(
        i["atendimento_id"] == atendimento["id"] for i in pendencias["itens"]
    )
    set_current_tenant(f.tenant_id)
    assert f.db.query(Venda).count() == 0


def test_entrega_sem_cobranca_nao_perdoa_valor_avulso_ou_taxi(fluxo):
    f = fluxo
    agendamento = agendar(f, valor_unitario="0")
    enviar(f, "taxi-dog", {"agendamento_id": agendamento["id"], "valor_cobrado": "15"})
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    resposta = f.api.post(
        f"/banho-tosa/atendimentos/{atendimento['id']}/mover-etapa",
        json={
            "tipo": "entregue",
            "entrega_sem_cobranca": True,
            "motivo_sem_cobranca": "Tentativa cortesia",
        },
    )
    assert resposta.status_code == 422
    assert "valores a cobrar" in resposta.json()["detail"]
    atual = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert atual["status"] == "chegou"
    assert Decimal(atual["valor_cobranca_pendente"]) == 15
    assert atual["entrega_sem_cobranca"] is False


def test_multiplos_contratos_nao_mostram_pago_quando_um_esta_pendente(fluxo):
    f = fluxo
    primeiro = contratar(f)
    segundo = contratar(f, nome_pacote="Mensal adicional QA")
    venda_primeiro = enviar(
        f, f"pacotes/creditos/{primeiro['id']}/gerar-venda", {}, esperado=200
    )
    enviar(f, f"pacotes/creditos/{segundo['id']}/gerar-venda", {}, esperado=200)
    set_current_tenant(f.tenant_id)
    f.db.add(
        VendaPagamento(
            tenant_id=f.tenant_id,
            venda_id=venda_primeiro["venda_id"],
            forma_pagamento="dinheiro",
            valor=200,
            status="aprovado",
        )
    )
    f.db.commit()
    agendamento = agendar(f, quantidade="5")
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert detalhe["pacote_status_pagamento"] == "parcial"
    assert Decimal(detalhe["pacote_valor_restante"]) == 200
    assert {p["status_pagamento"] for p in detalhe["pacotes_financeiro"]} == {
        "pago",
        "pendente",
    }
    assert len(detalhe["pacotes_financeiro"]) == 2

    # Devolver apenas o contrato pendente mantém o consumo do contrato pago,
    # sem continuar somando uma cobrança que já não pertence ao atendimento.
    enviar(
        f,
        f"pacotes/creditos/{segundo['id']}/estornar",
        {
            "atendimento_id": atendimento["id"],
            "observacoes": "Devolução parcial combinada",
        },
        esperado=200,
    )
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert detalhe["pacote_status_pagamento"] == "pago"
    assert Decimal(detalhe["pacote_valor_restante"]) == 0
    assert [p["credito_id"] for p in detalhe["pacotes_financeiro"]] == [primeiro["id"]]
    # O estorno do uso não perdoa a cobrança original do pacote devolvido.
    assert saldo(f, segundo["id"])["status_pagamento"] == "pendente"


def test_ficha_mostra_saldo_disponivel_descontando_outros_agendamentos(fluxo):
    f = fluxo
    credito = contratar(f)
    primeiro = agendar(f)
    atendimento = enviar(f, f"agendamentos/{primeiro['id']}/check-in", {}, esperado=200)
    agendar(f, dia=date.today() + timedelta(days=7))
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert detalhe["pacote_credito_id"] == credito["id"]
    assert Decimal(detalhe["pacote_saldo_creditos"]) == 2
    assert Decimal(saldo(f, credito["id"])["saldo_creditos"]) == 2


def test_falha_ao_devolver_pacote_desfaz_cancelamento_de_venda_e_pagamento(
    fluxo, monkeypatch
):
    f = fluxo
    credito = contratar(f)
    venda_pacote = enviar(
        f, f"pacotes/creditos/{credito['id']}/gerar-venda", {}, esperado=200
    )
    agendamento = agendar(f, quantidade="5")
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    venda_extra = enviar(f, f"atendimentos/{atendimento['id']}/venda", {}, esperado=200)
    set_current_tenant(f.tenant_id)
    for venda, valor in ((venda_pacote, 200), (venda_extra, 50)):
        f.db.add(
            VendaPagamento(
                tenant_id=f.tenant_id,
                venda_id=venda["venda_id"],
                forma_pagamento="dinheiro",
                valor=valor,
                status="aprovado",
            )
        )
    f.db.commit()
    devolver = banho_tosa_cancelamento.devolver_creditos_atendimento

    def falhar_depois_de_estornar(*args, **kwargs):
        devolver(*args, **kwargs)
        raise HTTPException(409, "Falha simulada depois do estorno")

    monkeypatch.setattr(
        banho_tosa_cancelamento,
        "devolver_creditos_atendimento",
        falhar_depois_de_estornar,
    )
    resposta = f.api.post(
        f"/banho-tosa/atendimentos/{atendimento['id']}/cancelar-processo",
        json={"motivo": "Cancelamento com falha simulada"},
    )
    assert resposta.status_code == 409
    contrato = saldo(f, credito["id"])
    assert Decimal(contrato["creditos_usados"]) == 4
    assert Decimal(contrato["saldo_creditos"]) == 0
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert detalhe["status"] == "chegou"
    assert detalhe["pacote_credito_id"] == credito["id"]
    set_current_tenant(f.tenant_id)
    f.db.expire_all()
    for venda in (venda_pacote, venda_extra):
        registro = f.db.query(Venda).filter_by(id=venda["venda_id"]).one()
        assert registro.status != "cancelada"
        assert registro.pagamentos[0].status == "aprovado"


def test_composicao_banho_e_tosa_confirma_todos_consumos_do_mesmo_contrato(fluxo):
    f = fluxo
    pacote = enviar(
        f,
        "pacotes",
        {
            "nome": "Banho e tosa combinado QA",
            "preco": "300",
            "validade_dias": 30,
            "servicos": [
                {"servico_id": f.banho.id, "quantidade_creditos": "4"},
                {"servico_id": f.tosa.id, "quantidade_creditos": "2"},
            ],
        },
    )
    credito = enviar(
        f,
        "pacotes/creditos",
        {
            "pacote_id": pacote["id"],
            "cliente_id": f.tutor.id,
            "pet_id": f.pet.id,
        },
    )
    agendamento = enviar(
        f,
        "agendamentos",
        {
            "cliente_id": f.tutor.id,
            "pet_id": f.pet.id,
            "data_hora_inicio": datetime.combine(date.today(), time(14)).isoformat(),
            "servicos": [
                {"servico_id": f.banho.id, "quantidade": "1", "valor_unitario": "50"},
                {"servico_id": f.tosa.id, "quantidade": "1", "valor_unitario": "80"},
            ],
        },
    )
    reservado = saldo(f, credito["id"])
    assert Decimal(reservado["creditos_reservados"]) == 2
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    consumido = saldo(f, credito["id"])
    assert Decimal(consumido["creditos_usados"]) == 2
    assert Decimal(consumido["creditos_reservados"]) == 0
    por_servico = {
        s["servico_id"]: Decimal(s["saldo_creditos"]) for s in consumido["servicos"]
    }
    assert por_servico == {f.banho.id: Decimal("3"), f.tosa.id: Decimal("1")}
    enviar(
        f,
        f"atendimentos/{atendimento['id']}/cancelar-processo",
        {"motivo": "Tutor remarcou ambos serviços"},
        esperado=200,
    )
    devolvido = saldo(f, credito["id"])
    assert Decimal(devolvido["creditos_usados"]) == 0
    assert {
        s["servico_id"]: Decimal(s["saldo_creditos"]) for s in devolvido["servicos"]
    } == {f.banho.id: Decimal("4"), f.tosa.id: Decimal("2")}


def test_fechamentos_encontra_pendencias_antigas_apos_lotes_sem_cobranca(fluxo):
    f = fluxo
    set_current_tenant(f.tenant_id)
    pendentes = [
        BanhoTosaAtendimento(
            tenant_id=f.tenant_id,
            cliente_id=f.tutor.id,
            pet_id=f.pet.id,
            status="pronto",
        )
        for _ in range(2)
    ]
    f.db.add_all(pendentes)
    f.db.flush()
    ids_pendentes = {item.id for item in pendentes}
    f.db.add_all(
        [
            BanhoTosaAtendimento(
                tenant_id=f.tenant_id,
                cliente_id=f.tutor.id,
                pet_id=f.pet.id,
                status="entregue",
                ocorrencias=[
                    {"tipo": "entrega_sem_cobranca", "system_generated": True}
                ],
            )
            for _ in range(5)
        ]
    )
    f.db.commit()
    resposta = f.api.get("/banho-tosa/fechamentos/pendencias", params={"limit": 2})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["total"] == 2
    assert {
        item["atendimento_id"] for item in resposta.json()["itens"]
    } == ids_pendentes


def _simular_consumo_anterior_a_reserva_por_item(f):
    # Primeiro cria agenda/check-in sem contrato, como registros já existentes
    # antes da implantação. O movimento antigo não tinha os três novos vínculos.
    agendamento = agendar(f)
    enviar(f, "taxi-dog", {"agendamento_id": agendamento["id"], "valor_cobrado": "15"})
    atendimento = enviar(
        f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200
    )
    credito = contratar(f)
    venda = enviar(f, f"pacotes/creditos/{credito['id']}/gerar-venda", {}, esperado=200)
    set_current_tenant(f.tenant_id)
    contrato = f.db.query(BanhoTosaPacoteCredito).filter_by(id=credito["id"]).one()
    contrato.servicos = None
    contrato.pet_id = None
    contrato.creditos_usados = Decimal("1")
    movimento = BanhoTosaPacoteMovimento(
        tenant_id=f.tenant_id,
        credito_id=credito["id"],
        atendimento_id=atendimento["id"],
        tipo="consumo",
        quantidade=1,
        saldo_apos=3,
        observacoes="Consumo registrado no fluxo anterior",
        created_by=f.identidade["user"].id,
    )
    f.db.add(movimento)
    f.db.flush()
    registro = f.db.query(BanhoTosaAtendimento).filter_by(id=atendimento["id"]).one()
    registro.pacote_credito_id = credito["id"]
    registro.pacote_movimento_id = movimento.id
    f.db.commit()
    return agendamento, atendimento, credito, venda


def test_consumo_legado_preserva_cobertura_sem_nova_venda_ou_baixa(fluxo):
    f = fluxo
    agendamento, atendimento, credito, venda = (
        _simular_consumo_anterior_a_reserva_por_item(f)
    )
    repetido = enviar(f, f"agendamentos/{agendamento['id']}/check-in", {}, esperado=200)
    assert repetido["id"] == atendimento["id"]
    contrato = saldo(f, credito["id"])
    assert Decimal(contrato["creditos_usados"]) == 1
    assert Decimal(contrato["servicos"][0]["creditos_usados"]) == 1
    assert Decimal(contrato["servicos"][0]["saldo_creditos"]) == 3
    detalhe = f.api.get(f"/banho-tosa/atendimentos/{atendimento['id']}").json()
    assert Decimal(detalhe["valor_cobranca_pendente"]) == 0
    entregue = enviar(
        f,
        f"atendimentos/{atendimento['id']}/mover-etapa",
        {"tipo": "entregue", "iniciar_timer": False},
        esperado=200,
    )
    assert entregue["status"] == "entregue"
    assert entregue["venda_id"] is None
    assert entregue["pacote_status_pagamento"] == "pendente"
    assert Decimal(entregue["pacote_valor_restante"]) == 200
    set_current_tenant(f.tenant_id)
    assert [v.id for v in f.db.query(Venda).all()] == [venda["venda_id"]]


def test_cancelamento_consumo_legado_restaura_saldo_por_servico(fluxo):
    f = fluxo
    _, atendimento, credito, venda = _simular_consumo_anterior_a_reserva_por_item(f)
    enviar(
        f,
        f"atendimentos/{atendimento['id']}/cancelar-processo",
        {"motivo": "Tutor remarcou o atendimento antigo"},
        esperado=200,
    )
    enviar(
        f,
        f"atendimentos/{atendimento['id']}/cancelar-processo",
        {"motivo": "Tutor remarcou o atendimento antigo"},
        esperado=200,
    )
    contrato = saldo(f, credito["id"])
    assert Decimal(contrato["creditos_usados"]) == 0
    assert Decimal(contrato["servicos"][0]["creditos_usados"]) == 0
    assert Decimal(contrato["servicos"][0]["saldo_creditos"]) == 4
    assert contrato["venda_id"] == venda["venda_id"]
    assert contrato["status_pagamento"] == "pendente"
    historico = f.api.get(
        f"/banho-tosa/pacotes/creditos/{credito['id']}/movimentos"
    ).json()
    assert sum(m["tipo"] == "estorno" for m in historico) == 1


def test_fechamentos_continua_busca_apos_orcamento_fixo_sem_ocultar_pendencias(
    fluxo, monkeypatch
):
    from app import banho_tosa_fechamento

    monkeypatch.setattr(banho_tosa_fechamento, "MAX_PAGINAS_PENDENCIAS", 2)
    monkeypatch.setattr(banho_tosa_fechamento, "TAMANHO_LOTE_PENDENCIAS", 2)
    f = fluxo
    set_current_tenant(f.tenant_id)
    pendente = BanhoTosaAtendimento(
        tenant_id=f.tenant_id, cliente_id=f.tutor.id, pet_id=f.pet.id, status="pronto"
    )
    f.db.add(pendente)
    f.db.flush()
    pendente_id = pendente.id
    f.db.add_all(
        [
            BanhoTosaAtendimento(
                tenant_id=f.tenant_id,
                cliente_id=f.tutor.id,
                pet_id=f.pet.id,
                status="entregue",
                ocorrencias=[
                    {"tipo": "entrega_sem_cobranca", "system_generated": True}
                ],
            )
            for _ in range(5)
        ]
    )
    f.db.commit()
    primeira = f.api.get(
        "/banho-tosa/fechamentos/pendencias", params={"limit": 2}
    ).json()
    assert primeira["itens"] == []
    assert primeira["busca_incompleta"] is True
    assert primeira["proximo_cursor"] > 0
    sincronizada = f.api.post(
        "/banho-tosa/fechamentos/pendencias/sincronizar", params={"limit": 2}
    ).json()
    assert sincronizada["total_processados"] == 0
    assert sincronizada["busca_incompleta"] is True
    assert sincronizada["proximo_cursor"] == primeira["proximo_cursor"]
    segunda = f.api.get(
        "/banho-tosa/fechamentos/pendencias",
        params={"limit": 2, "cursor": primeira["proximo_cursor"]},
    ).json()
    assert segunda["busca_incompleta"] is False
    assert segunda["proximo_cursor"] is None
    assert [item["atendimento_id"] for item in segunda["itens"]] == [pendente_id]


def test_fechamentos_cursor_nao_pula_pendencias_no_meio_do_lote(fluxo, monkeypatch):
    from app import banho_tosa_fechamento

    monkeypatch.setattr(banho_tosa_fechamento, "TAMANHO_LOTE_PENDENCIAS", 2)
    f = fluxo
    set_current_tenant(f.tenant_id)
    registros = [
        BanhoTosaAtendimento(
            tenant_id=f.tenant_id,
            cliente_id=f.tutor.id,
            pet_id=f.pet.id,
            status="pronto",
        )
        for _ in range(3)
    ]
    f.db.add_all(registros)
    f.db.commit()
    ids_esperados = {item.id for item in registros}
    cursor = None
    encontrados = []
    for _ in range(3):
        params = {"limit": 1}
        if cursor is not None:
            params["cursor"] = cursor
        pagina = f.api.get("/banho-tosa/fechamentos/pendencias", params=params).json()
        encontrados.extend(item["atendimento_id"] for item in pagina["itens"])
        cursor = pagina["proximo_cursor"]
    assert cursor is None
    assert len(encontrados) == len(set(encontrados)) == 3
    assert set(encontrados) == ids_esperados
