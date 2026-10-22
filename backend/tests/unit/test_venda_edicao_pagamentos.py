"""Edição com recebimento preservado exige exceção explícita antes de qualquer escrita."""

from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event, get_ident
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.financeiro_models import ContaReceber, Recebimento
from app.models import AuditLog
from app.vendas import crud_routes
from app.vendas.edicao_pagamentos import fotografar_pagamentos_edicao
from app.vendas.pagamento_excedente import ACAO_EXCESSO
from app.vendas.schemas import CriarVendaRequest
from app.vendas_models import Venda, VendaPagamento
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario


MOTIVO = (
    "Desconto concedido após a cobrança; valor excedente será conferido pelo gestor."
)


@pytest.fixture
def caso(cenario, monkeypatch):
    cenario.venda.total = Decimal("119.90")
    cenario.venda.subtotal = Decimal("119.90")
    cenario.venda.desconto_valor = 0
    cenario.db.commit()
    etapas = []
    monkeypatch.setattr(crud_routes, "log_action", lambda *a, **kw: None)
    monkeypatch.setattr(crud_routes, "validar_vendedor_funcionario", lambda *a: None)
    monkeypatch.setattr(
        crud_routes,
        "ajustar_estoque_edicao_venda",
        lambda **kw: etapas.append("estoque") or {},
    )
    monkeypatch.setattr(
        crud_routes,
        "atualizar_itens_venda_aberta",
        lambda **kw: etapas.append("itens") or {},
    )
    cenario.auth = (
        SimpleNamespace(id=1, nome="Operador", email="teste@dev.test"),
        cenario.tenant,
    )
    cenario.etapas = etapas
    return cenario


def registrar(caso, valor="119.90", forma="Cartão de crédito", **extra):
    pagamento = VendaPagamento(
        tenant_id=caso.tenant,
        venda_id=caso.venda.id,
        caixa_id=2,
        forma_pagamento=forma,
        valor=Decimal(str(valor)),
        status=extra.pop("status", "confirmado"),
        **extra,
    )
    caso.db.add(pagamento)
    caso.db.commit()
    return pagamento


def dados_edicao(desconto=10, *, motivo=None, contexto=None):
    return CriarVendaRequest(
        desconto_venda_valor=desconto,
        justificativa_pagamento_excedente=motivo,
        contexto_pagamento_excedente=contexto,
        itens=[
            {
                "tipo": "produto",
                "produto_id": 1,
                "quantidade": 1,
                "preco_unitario": 119.90,
                "subtotal": 119.90,
                "ignorar_recorrencia": True,
            }
        ],
    )


def salvar(caso, dados):
    return crud_routes.atualizar_venda(caso.venda.id, dados, caso.db, caso.auth)


def contexto_excecao(caso, dados=None):
    with pytest.raises(HTTPException) as erro:
        salvar(caso, dados or dados_edicao())
    assert erro.value.status_code == 409
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_REQUER_JUSTIFICATIVA"
    return erro.value.detail["contexto_pagamento_excedente"]


def test_desconto_cria_excesso_sem_motivo_e_bloqueado_antes_de_estoque(caso):
    pagamento = registrar(caso)
    contexto = contexto_excecao(caso)
    assert contexto == {
        "total_venda": 109.90,
        "total_ja_pago": 119.90,
        "total_novos_pagamentos": 0,
        "crediario_pendente": 0,
    }
    assert caso.venda.total == Decimal("119.90")
    assert caso.venda.desconto_valor == 0
    assert pagamento.valor == Decimal("119.90")
    assert caso.etapas == []
    assert caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).count() == 0


def test_excecao_justificada_preserva_pagamento_e_audita_antes_depois(caso):
    pagamento = registrar(caso)
    contexto = contexto_excecao(caso)
    resultado = salvar(caso, dados_edicao(motivo=f"  {MOTIVO}  ", contexto=contexto))
    assert resultado["total"] == 109.90
    assert caso.venda.total == Decimal("109.90")
    assert pagamento.valor == Decimal("119.90")
    assert caso.db.query(VendaPagamento).count() == 1
    assert caso.db.query(Recebimento).count() == 0
    assert caso.db.query(ContaReceber).count() == 0
    evento = caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).one()
    assert evento.tenant_id == caso.tenant
    assert evento.user_id == 1
    assert evento.entity_id == caso.venda.id
    assert evento.details == MOTIVO
    prova = json.loads(evento.new_value)
    assert prova["origem"] == "edicao_venda"
    assert prova["excedente"] == 10
    assert prova["contexto"] == contexto
    assert prova["alteracao_venda"]["antes"] == {"total": 119.90, "desconto_valor": 0}
    assert prova["alteracao_venda"]["depois"] == {"total": 109.90, "desconto_valor": 10}
    assert prova["alteracao_venda"]["formas_pagamento"] == [
        {"forma_pagamento": "Cartão de crédito", "total": 119.90, "quantidade": 1}
    ]
    assert json.loads(evento.old_value)["pagamentos"][0]["valor"] == 119.90


def test_contexto_antigo_recusado_apos_pagamento_mudar_sem_alterar_venda(caso):
    pagamento = registrar(caso)
    contexto = contexto_excecao(caso)
    caso.db.execute(
        VendaPagamento.__table__.update()
        .where(VendaPagamento.id == pagamento.id)
        .values(valor=120.90)
    )
    caso.db.commit()
    with pytest.raises(HTTPException) as erro:
        salvar(caso, dados_edicao(motivo=MOTIVO, contexto=contexto))
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_DESATUALIZADO"
    assert erro.value.detail["contexto_pagamento_excedente"]["total_ja_pago"] == 120.90
    assert caso.venda.total == Decimal("119.90")
    assert caso.etapas == []


def test_edicao_sem_aumentar_excesso_legado_nao_exige_nova_excecao(caso):
    registrar(caso)
    caso.venda.total = Decimal("109.90")
    caso.venda.desconto_valor = 10
    caso.db.commit()
    salvar(caso, dados_edicao())
    assert caso.venda.total == Decimal("109.90")
    assert caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).count() == 0


def test_contrapartidas_e_pagamentos_invalidos_nao_geram_excesso_falso(caso):
    registrar(caso)
    registrar(caso, -20)
    invalido = registrar(caso, 500)
    invalido.status = "estornado"
    caso.db.commit()
    salvar(caso, dados_edicao())
    assert caso.venda.total == Decimal("109.90")
    assert caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).count() == 0


def conta(caso, valor=100, recebido=0, forma_id=None):
    registro = ContaReceber(
        tenant_id=caso.tenant,
        venda_id=caso.venda.id,
        forma_pagamento_id=forma_id,
        descricao="Parcela da venda",
        valor_original=valor,
        valor_final=valor,
        valor_recebido=recebido,
        status="parcial" if recebido else "pendente",
        user_id=1,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=date(2026, 9, 4),
        data_vencimento=date(2026, 10, 4),
    )
    caso.db.add(registro)
    caso.db.flush()
    return registro


def test_crediario_pendente_desajustado_nao_aceita_excecao(caso):
    registrar(caso, 119.90, "Crediário", forma_pagamento_id=5)
    conta(caso, 119.90, forma_id=5)
    caso.db.commit()
    with pytest.raises(HTTPException, match="crediário desajustado"):
        salvar(caso, dados_edicao(motivo=MOTIVO))
    assert caso.venda.total == Decimal("119.90")
    assert caso.etapas == []


def test_beneficio_proprio_maior_que_novo_total_nao_aceita_excecao(caso):
    registrar(caso, 115, "Crédito Cliente")
    with pytest.raises(HTTPException, match="créditos ou cashback"):
        salvar(caso, dados_edicao(motivo=MOTIVO))
    assert caso.venda.total == Decimal("119.90")
    assert caso.etapas == []


def test_beneficio_valido_e_excesso_monetario_podem_ser_justificados(caso):
    registrar(caso, 109.90)
    registrar(caso, 10, "Crédito Cliente")
    contexto = contexto_excecao(caso)
    salvar(caso, dados_edicao(motivo=MOTIVO, contexto=contexto))
    assert caso.venda.total == Decimal("109.90")
    assert caso.db.query(VendaPagamento).count() == 2
    prova = json.loads(
        caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).one().new_value
    )
    assert prova["excedente"] == 10
    assert prova["alteracao_venda"]["creditos_utilizados"] == 10


def test_fotografia_deduplica_parcela_com_espelho_e_nao_chama_plano_recebido(caso):
    registrar(caso, 100, "Crediário", forma_pagamento_id=5)
    pagamento = registrar(caso, 20, "Pix")
    parcela = conta(caso, 100, 20, forma_id=5)
    caso.db.add(
        Recebimento(
            tenant_id=caso.tenant,
            conta_receber_id=parcela.id,
            forma_pagamento_id=1,
            valor_recebido=20,
            user_id=1,
            data_recebimento=date(2026, 9, 5),
            observacoes=f"[venda_pagamento:{pagamento.id}]",
        )
    )
    caso.db.commit()
    foto = fotografar_pagamentos_edicao(
        caso.db, venda=caso.venda, tenant_id=caso.tenant
    )
    assert foto["recebido_monetario"] == foto["total_ja_pago"] == 20
    assert foto["crediario_pendente"] == 80


def test_fotografia_legada_usa_conta_recebida_sem_inventar_recebimento(caso):
    conta(caso, 50, 50)
    caso.db.commit()
    foto = fotografar_pagamentos_edicao(
        caso.db, venda=caso.venda, tenant_id=caso.tenant
    )
    assert foto["total_ja_pago"] == 50
    assert foto["crediario_pendente"] == 0
    assert foto["pagamentos"][0]["origem"] == "conta_legada"


def test_edicao_soma_baixa_avulsa_a_vp_sem_truncar_ou_duplicar(caso):
    registrar(caso, 30)
    parcela = conta(caso, Decimal("89.90"), Decimal("89.90"))
    caso.db.add(
        Recebimento(
            tenant_id=caso.tenant,
            conta_receber_id=parcela.id,
            forma_pagamento_id=1,
            valor_recebido=Decimal("89.90"),
            user_id=1,
            data_recebimento=date(2026, 9, 5),
        )
    )
    caso.db.commit()
    contexto = contexto_excecao(caso)
    assert contexto["total_ja_pago"] == 119.90
    salvar(caso, dados_edicao(motivo=MOTIVO, contexto=contexto))
    assert caso.venda.total == Decimal("109.90")
    assert parcela.valor_recebido == Decimal("89.90")
    assert caso.db.query(VendaPagamento).one().valor == 30
    assert caso.db.query(Recebimento).count() == 1
    audit = caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).one()
    pagamentos = json.loads(audit.old_value)["pagamentos"]
    assert sorted(p["valor"] for p in pagamentos) == [30, 89.90]


def test_edicao_nao_ressuscita_mirror_de_pagamento_cancelado(caso):
    cancelado = registrar(caso, 119.90, status="cancelado")
    parcela = conta(caso, Decimal("119.90"), Decimal("119.90"))
    parcela.observacoes = f"[venda_pagamento:{cancelado.id}]"
    caso.db.add(
        Recebimento(
            tenant_id=caso.tenant,
            conta_receber_id=parcela.id,
            forma_pagamento_id=1,
            valor_recebido=Decimal("119.90"),
            user_id=1,
            data_recebimento=date(2026, 9, 5),
            observacoes=f"[venda_pagamento:{cancelado.id}]",
        )
    )
    caso.db.commit()
    salvar(caso, dados_edicao())
    assert caso.venda.total == Decimal("109.90")
    assert caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).count() == 0
    assert caso.db.query(Recebimento).count() == 1


def test_edicao_legada_preserva_recebido_integral_sem_usar_pago_limitado(caso):
    parcela = conta(caso, Decimal("119.90"), Decimal("119.90"))
    parcela.status = "recebido"
    caso.db.commit()
    contexto = contexto_excecao(caso)
    assert contexto["total_ja_pago"] == 119.90
    assert contexto["total_venda"] == 109.90
    salvar(caso, dados_edicao(motivo=MOTIVO, contexto=contexto))
    assert caso.venda.total == Decimal("109.90")
    assert parcela.valor_recebido == Decimal("119.90")
    assert caso.db.query(VendaPagamento).count() == 0
    assert caso.db.query(Recebimento).count() == 0
    prova = json.loads(
        caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).one().new_value
    )
    assert prova["alteracao_venda"]["recebido_monetario"] == 119.90
    assert prova["excedente"] == 10


def test_alterar_desconto_apos_confirmacao_exige_nova_fotografia(caso):
    registrar(caso)
    contexto = contexto_excecao(caso)
    with pytest.raises(HTTPException) as erro:
        salvar(caso, dados_edicao(desconto=15, motivo=MOTIVO, contexto=contexto))
    assert erro.value.status_code == 409
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_DESATUALIZADO"
    atualizado = erro.value.detail["contexto_pagamento_excedente"]
    assert atualizado["total_venda"] == 104.90
    assert caso.venda.total == Decimal("119.90")
    assert caso.etapas == []
    salvar(caso, dados_edicao(desconto=15, motivo=MOTIVO, contexto=atualizado))
    assert caso.venda.total == Decimal("104.90")


def test_venda_de_outro_tenant_nao_e_editada(caso):
    with pytest.raises(HTTPException) as erro:
        crud_routes.atualizar_venda(
            caso.venda.id, dados_edicao(), caso.db, (caso.auth[0], uuid4())
        )
    assert erro.value.status_code == 404
    assert caso.venda.total == Decimal("119.90")
    assert caso.etapas == []


def test_falha_no_estoque_nao_persiste_excecao_nem_desconto(caso, monkeypatch):
    registrar(caso)
    contexto = contexto_excecao(caso)

    def falhar(**_):
        raise HTTPException(400, "Falha de estoque simulada")

    monkeypatch.setattr(crud_routes, "ajustar_estoque_edicao_venda", falhar)
    with pytest.raises(HTTPException, match="estoque simulada"):
        salvar(caso, dados_edicao(motivo=MOTIVO, contexto=contexto))
    caso.db.rollback()
    assert caso.venda.total == Decimal("119.90")
    assert caso.db.query(AuditLog).filter_by(action=ACAO_EXCESSO).count() == 0


def test_fotografia_espera_baixa_em_andamento_sem_perder_o_recebimento(caso):
    engine = caso.db.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("Concorrência de locks exige PostgreSQL DEV descartável")
    registrar(caso, 100, "Crediário", forma_pagamento_id=5)
    parcela = conta(caso, 100, 0, forma_id=5)
    caso.db.commit()
    venda_id, conta_id, tenant = caso.venda.id, parcela.id, caso.tenant
    travada, liberar, esperando = Event(), Event(), Event()
    threads = {}

    def marcar_espera(_conn, _cursor, sql, _params, _context, _many):
        if (
            get_ident() == threads.get("edicao")
            and "FROM contas_receber" in sql
            and "FOR UPDATE" in sql
        ):
            esperando.set()

    def receber():
        from app.tenancy.context import clear_current_tenant, set_current_tenant

        set_current_tenant(tenant)
        try:
            with Session(engine) as db:
                registro = (
                    db.query(ContaReceber)
                    .filter_by(id=conta_id)
                    .with_for_update()
                    .one()
                )
                registro.valor_recebido = 20
                registro.status = "parcial"
                db.add(
                    Recebimento(
                        tenant_id=tenant,
                        conta_receber_id=conta_id,
                        forma_pagamento_id=1,
                        valor_recebido=20,
                        user_id=1,
                        data_recebimento=date(2026, 9, 5),
                    )
                )
                db.flush()
                travada.set()
                assert liberar.wait(8)
                db.commit()
        finally:
            clear_current_tenant()

    def fotografar():
        from app.tenancy.context import clear_current_tenant, set_current_tenant

        threads["edicao"] = get_ident()
        set_current_tenant(tenant)
        try:
            with Session(engine) as db:
                registro = (
                    db.query(Venda).filter_by(id=venda_id).with_for_update().one()
                )
                return fotografar_pagamentos_edicao(
                    db, venda=registro, tenant_id=tenant
                )
        finally:
            clear_current_tenant()

    event.listen(engine, "before_cursor_execute", marcar_espera)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            baixa = executor.submit(receber)
            try:
                assert travada.wait(8)
                edicao = executor.submit(fotografar)
                assert esperando.wait(8)
                assert not edicao.done()
            finally:
                liberar.set()
            baixa.result(timeout=8)
            foto = edicao.result(timeout=8)
    finally:
        liberar.set()
        event.remove(engine, "before_cursor_execute", marcar_espera)
    assert foto["total_ja_pago"] == foto["recebido_monetario"] == 20
    assert foto["crediario_pendente"] == 80
