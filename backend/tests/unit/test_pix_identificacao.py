"""Identificação do Pix é uma conferência operacional, sem efeito financeiro."""

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.schema import CreateTable
from starlette.requests import Request

from app.alertas_gestor_routes import (
    listar_alertas_gestor,
    resolver_pix_gestor,
    router as gestor_router,
)
from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.auditoria import assinatura_item
from app.caixa.auditoria_routes import (
    ConferenciaItemSchema,
    conferir_item_caixa,
    identificar_pix_caixa,
    obter_auditoria_caixa,
    router as auditoria_router,
)
from app.caixa.pix_identificacao import (
    ACAO_PIX,
    AlteracaoIdentificacaoPixSchema,
    IdentificacaoPixSchema,
    item_pagamento_auditoria,
    listar_pendencias_pix,
)
from app.caixa_models import MovimentacaoCaixa
from app.caixa_routes import FecharCaixaSchema, fechar_caixa
from app.db import get_session
from app.models import AuditLog, User, UserTenant
from app.vendas_models import VendaPagamento
from tests.unit.test_caixa_recebimentos_auditoria import (  # noqa: F401
    caixa_session,
    recebimentos,
)


@pytest.fixture
def caso(request):
    return request.getfixturevalue("recebimentos")


@pytest.fixture
def caso_alertas(caso):
    # Estas tabelas existem somente no schema/banco descartável da fixture.
    with caso.db.get_bind().begin() as connection:
        for model in (User, UserTenant):
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    return caso


def consultar(caso):
    return obter_auditoria_caixa(caso.atual.id, caso.db, caso.auth)


def item_pix(caso):
    return next(
        item
        for item in consultar(caso)["pagamentos"]
        if item["id"] == caso.pagamentos[1].id
    )


def dados_pix(
    item, estado="nao_identificado", justificativa="Comprovante não localizado"
):
    return IdentificacaoPixSchema(
        pagamento_id=item["id"],
        assinatura=item["assinatura"],
        registro_id=item["identificacao_pix"]["registro_id"],
        estado=estado,
        justificativa=justificativa,
    )


def gravar(caso, estado="nao_identificado", justificativa="Comprovante não localizado"):
    return identificar_pix_caixa(
        caso.atual.id,
        dados_pix(item_pix(caso), estado, justificativa),
        caso.db,
        caso.auth,
    )


def logs_pix(caso):
    return caso.db.query(AuditLog).filter(AuditLog.action == ACAO_PIX).all()


def app_http(caso, *, gestor=False):
    app = FastAPI()
    app.include_router(
        gestor_router if gestor else auditoria_router,
        prefix="" if gestor else "/caixas",
    )
    app.dependency_overrides[get_session] = lambda: caso.db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: caso.auth
    return app


def test_get_inicial_disponibiliza_identificacao_independente_da_conferencia(caso):
    item = item_pix(caso)
    assert item["identificacao_pix"] == {
        "estado": "nao_conferido",
        "registro_id": None,
        "justificativa": None,
        "usuario_nome": None,
        "data": None,
        "pagamento_alterado": False,
        "historico": [],
    }
    assert item["estado_conferencia"] == "pendente"
    assert assinatura_item(item) == item["assinatura"]
    assert not logs_pix(caso)


@pytest.mark.parametrize("estado", ["identificado", "nao_identificado"])
def test_estado_persiste_justificativa_autoria_e_data_sem_mudar_financas(caso, estado):
    antes = consultar(caso)
    financeiros = deepcopy([p.to_dict() for p in caso.pagamentos])
    movimento = caso.movimento.to_dict()
    resposta = gravar(caso, estado, "  Conferido no aplicativo do banco  ")

    assert resposta["success"] is True
    registro = resposta["identificacao_pix"]
    assert registro["estado"] == estado
    assert registro["justificativa"] == "Conferido no aplicativo do banco"
    assert registro["usuario_nome"] == caso.auth[0].nome
    assert registro["usuario_id"] == caso.auth[0].id
    assert datetime.fromisoformat(registro["data"])
    assert len(registro["historico"]) == 1
    atual = consultar(caso)
    assert atual["resumo"] == antes["resumo"]
    assert [p.to_dict() for p in caso.pagamentos] == financeiros
    assert caso.movimento.to_dict() == movimento
    assert caso.db.query(MovimentacaoCaixa).count() == 1
    assert caso.venda.total == 90
    assert len(logs_pix(caso)) == 1


@pytest.mark.parametrize(
    "mudanca",
    [
        {"justificativa": ""},
        {"justificativa": " \n\t "},
        {"justificativa": "x" * 1001},
        {"estado": "nao_conferido"},
        {"pagamento_id": 0},
        {"registro_id": 0},
        {"assinatura": "invalida"},
    ],
)
@pytest.mark.asyncio
async def test_api_rejeita_payload_invalido_sem_gravar(caso, mudanca):
    payload = dados_pix(item_pix(caso)).model_dump() | mudanca
    async with AsyncClient(
        transport=ASGITransport(app=app_http(caso)), base_url="http://dev.test"
    ) as client:
        resposta = await client.post(
            f"/caixas/{caso.atual.id}/auditoria/pix", json=payload
        )
    assert resposta.status_code == 422
    assert not logs_pix(caso)


def test_transicao_mantem_historico_e_repeticao_atual_nao_duplica(caso):
    primeiro = gravar(caso)
    primeiro_id = primeiro["identificacao_pix"]["registro_id"]
    segundo = gravar(caso, "identificado", "Cliente enviou comprovante válido")
    atual = segundo["identificacao_pix"]
    assert atual["registro_id"] != primeiro_id
    assert [h["estado"] for h in atual["historico"]] == [
        "identificado",
        "nao_identificado",
    ]
    assert atual["historico"][1]["justificativa"] == "Comprovante não localizado"
    repetido = gravar(caso, "identificado", "Reenvio sem mudança de estado")
    assert repetido["identificacao_pix"]["registro_id"] == atual["registro_id"]
    assert repetido["identificacao_pix"]["justificativa"] == atual["justificativa"]
    assert len(logs_pix(caso)) == 2


def test_versao_desatualizada_retorna_409_sem_sobrescrever(caso):
    antigo = dados_pix(item_pix(caso))
    gravar(caso, "identificado", "Identificado pela operadora")
    with pytest.raises(HTTPException) as erro:
        identificar_pix_caixa(caso.atual.id, antigo, caso.db, caso.auth)
    assert erro.value.status_code == 409
    assert "identificação" in erro.value.detail
    assert len(logs_pix(caso)) == 1
    assert item_pix(caso)["identificacao_pix"]["estado"] == "identificado"


def test_pagamento_alterado_exige_nova_assinatura_preserva_pendencia_e_historico(caso):
    gravar(caso)
    antigo = dados_pix(item_pix(caso), "identificado", "Conferência após ajuste")
    caso.pagamentos[1].valor = 35
    caso.db.flush()
    with pytest.raises(HTTPException) as erro:
        identificar_pix_caixa(caso.atual.id, antigo, caso.db, caso.auth)
    assert erro.value.status_code == 409
    atual = item_pix(caso)
    assert atual["identificacao_pix"]["estado"] == "nao_conferido"
    assert atual["identificacao_pix"]["pagamento_alterado"] is True
    assert len(atual["identificacao_pix"]["historico"]) == 1
    assert len(listar_pendencias_pix(caso.db, caso.auth[1])) == 1
    resposta = gravar(caso, "identificado", "Valor corrigido e comprovante validado")
    assert resposta["identificacao_pix"]["estado"] == "identificado"
    assert resposta["identificacao_pix"]["pagamento_alterado"] is False
    assert len(resposta["identificacao_pix"]["historico"]) == 2
    assert not listar_pendencias_pix(caso.db, caso.auth[1])


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("forma_pagamento", "Dinheiro"),
        ("forma_pagamento", "Cartão de crédito"),
        ("valor", -40),
        ("valor", 0),
        ("status", "estornado"),
        ("status", "recusado"),
        ("status", "cancelado"),
    ],
)
def test_somente_pix_positivo_ativo_pode_receber_identificacao(caso, campo, valor):
    dados = dados_pix(item_pix(caso))
    setattr(caso.pagamentos[1], campo, valor)
    caso.db.flush()
    with pytest.raises(HTTPException) as erro:
        identificar_pix_caixa(caso.atual.id, dados, caso.db, caso.auth)
    assert erro.value.status_code == 404
    assert not logs_pix(caso)


def test_pagamento_de_outro_caixa_nao_e_aceito_no_fechamento_atual(caso):
    pagamento = caso.pagamentos[0]
    bruto = item_pagamento_auditoria(pagamento)
    dados = IdentificacaoPixSchema(
        pagamento_id=pagamento.id,
        assinatura=assinatura_item(bruto),
        estado="identificado",
        justificativa="Comprovante pertence ao caixa anterior",
    )
    with pytest.raises(HTTPException) as erro:
        identificar_pix_caixa(caso.atual.id, dados, caso.db, caso.auth)
    assert erro.value.status_code == 404
    assert not logs_pix(caso)


def test_empresa_e_operador_sem_acesso_nao_identificam_o_pagamento(caso):
    dados = dados_pix(item_pix(caso))
    for auth in [
        (caso.auth[0], uuid4()),
        (SimpleNamespace(id=92, nome="Outro operador"), caso.auth[1]),
    ]:
        with pytest.raises(HTTPException) as erro:
            identificar_pix_caixa(caso.atual.id, dados, caso.db, auth)
        assert erro.value.status_code == 404
    assert not logs_pix(caso)


@pytest.mark.parametrize("status", ["cancelada", "cancelado"])
def test_venda_cancelada_nao_recebe_identificacao(caso, status):
    dados = dados_pix(item_pix(caso))
    caso.venda.status = status
    caso.db.flush()
    item = item_pix(caso)
    assert item["identificacao_pix"] is None
    assert assinatura_item(item) == item["assinatura"]
    with pytest.raises(HTTPException) as erro:
        identificar_pix_caixa(caso.atual.id, dados, caso.db, caso.auth)
    assert erro.value.status_code == 404
    assert not logs_pix(caso)


def test_identificacao_nao_altera_ok_da_conferencia_geral_nem_assinatura(caso):
    item = item_pix(caso)
    conferir_item_caixa(
        caso.atual.id,
        ConferenciaItemSchema(
            tipo_item="pagamento",
            item_id=item["id"],
            assinatura=item["assinatura"],
            estado="ok",
            conferido=True,
        ),
        caso.db,
        caso.auth,
    )
    for estado in ("nao_identificado", "identificado"):
        gravar(caso, estado, "Conferência do comprovante independente")
        atual = item_pix(caso)
        assert atual["assinatura"] == item["assinatura"]
        assert assinatura_item(atual) == item["assinatura"]
        assert atual["estado_conferencia"] == "ok"
        assert atual["conferencia_alterada"] is False


@pytest.mark.asyncio
async def test_pix_nao_identificado_nao_bloqueia_fechamento(caso):
    gravar(caso)
    resposta = await fechar_caixa(
        caso.atual.id,
        FecharCaixaSchema(valor_informado=120),
        Request({"type": "http", "client": ("127.0.0.1", 1234), "headers": []}),
        caso.db,
        caso.auth,
    )
    assert resposta["status"] == "fechado"
    assert resposta["diferenca"] == 0
    assert item_pix(caso)["identificacao_pix"]["estado"] == "nao_identificado"
    assert len(listar_pendencias_pix(caso.db, caso.auth[1])) == 1


def test_pendencia_nunca_expira_e_resolucao_gerencial_funciona_em_caixa_fechado(
    caso_alertas,
):
    caso = caso_alertas
    gravar(caso)
    evento = logs_pix(caso)[0]
    evento.timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    caso.atual.status = "fechado"
    caso.atual.data_fechamento = datetime(2026, 10, 9, 18)
    caso.atual.valor_informado = 120
    caso.atual.valor_esperado = 120
    caso.db.flush()
    alertas = listar_alertas_gestor(
        data_inicio=date(2026, 10, 22),
        data_fim=date(2026, 10, 22),
        pagina=1,
        por_pagina=30,
        db=caso.db,
        user_and_tenant=caso.auth,
    )
    assert alertas["total"] == 1
    assert alertas["resumo"]["pix_nao_identificado"] == 1
    alerta = alertas["itens"][0]
    assert alerta["pagamento_id"] == caso.pagamentos[1].id
    assert alerta["independe_periodo"] is True
    assert alerta["justificativa"] == "Comprovante não localizado"
    gestor = (SimpleNamespace(id=92, nome="Gestora"), caso.auth[1])
    resposta = resolver_pix_gestor(
        alerta["pagamento_id"],
        AlteracaoIdentificacaoPixSchema(
            assinatura=alerta["assinatura"],
            registro_id=alerta["registro_id"],
            estado="identificado",
            justificativa="Gestora localizou o comprovante",
        ),
        caso.db,
        gestor,
    )
    assert resposta["identificacao_pix"]["usuario_nome"] == "Gestora"
    assert resposta["identificacao_pix"]["estado"] == "identificado"
    assert len(resposta["identificacao_pix"]["historico"]) == 2
    assert not listar_pendencias_pix(caso.db, caso.auth[1])
    assert caso.atual.status == "fechado"
    assert caso.atual.valor_informado == 120
    assert caso.pagamentos[1].valor == 40


def test_pendencias_usam_apenas_ultimo_estado_e_isolam_tenant(caso):
    gravar(caso)
    assert len(listar_pendencias_pix(caso.db, caso.auth[1])) == 1
    assert listar_pendencias_pix(caso.db, uuid4()) == []
    gravar(caso, "identificado", "Comprovante encontrado")
    assert listar_pendencias_pix(caso.db, caso.auth[1]) == []
    gravar(caso, "nao_identificado", "Comprovante não corresponde ao valor")
    assert len(listar_pendencias_pix(caso.db, caso.auth[1])) == 1
    caso.pagamentos[1].status = "estornado"
    caso.db.flush()
    assert listar_pendencias_pix(caso.db, caso.auth[1]) == []


def test_pendencia_antiga_convive_com_alerta_do_periodo_e_filtros(caso_alertas):
    caso = caso_alertas
    gravar(caso)
    evento = logs_pix(caso)[0]
    evento.timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    caso.atual.conferencia_abertura = {
        "numero_caixa": 1,
        "valor_fechamento": 99,
        "valor_abertura": 100,
        "diferenca": 1,
    }
    caso.db.flush()
    caso.db.expire_all()
    params = dict(
        data_inicio=date(2026, 10, 9),
        data_fim=date(2026, 10, 9),
        pagina=1,
        por_pagina=30,
        db=caso.db,
        user_and_tenant=caso.auth,
    )
    resultado = listar_alertas_gestor(**params)
    assert [item["tipo"] for item in resultado["itens"]] == [
        "diferenca_abertura",
        "pix_nao_identificado",
    ]
    assert resultado["total"] == 2
    filtrado = listar_alertas_gestor(**params, tipo="pix_nao_identificado")
    assert filtrado["total"] == 1
    assert filtrado["resumo"]["diferenca_abertura"] == 1
    sem_operador = listar_alertas_gestor(**params, operador_id=999)
    assert sem_operador["total"] == 0


def test_resolucao_gerencial_de_outro_tenant_nao_grava(caso):
    gravar(caso)
    dados = dados_pix(item_pix(caso), "identificado", "Comprovante recebido")
    with pytest.raises(HTTPException) as erro:
        resolver_pix_gestor(
            dados.pagamento_id,
            AlteracaoIdentificacaoPixSchema(
                **dados.model_dump(exclude={"pagamento_id"})
            ),
            caso.db,
            (SimpleNamespace(id=92, nome="Gestora externa"), uuid4()),
        )
    assert erro.value.status_code == 404
    assert len(logs_pix(caso)) == 1
    assert item_pix(caso)["identificacao_pix"]["estado"] == "nao_identificado"


@pytest.mark.asyncio
async def test_api_gerencial_exige_permissao_em_leitura_e_resolucao(caso, monkeypatch):
    chamadas = []

    def negar(db, user_id, permissao, tenant_id, **kwargs):
        chamadas.append((user_id, permissao, tenant_id))
        raise HTTPException(403, "Permissão negada")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    async with AsyncClient(
        transport=ASGITransport(app=app_http(caso, gestor=True)),
        base_url="http://dev.test",
    ) as client:
        leitura = await client.get("/alertas-gestor")
        resposta = await client.post(
            f"/alertas-gestor/pix/{caso.pagamentos[1].id}/identificacao",
            json=dados_pix(item_pix(caso), "identificado").model_dump(
                exclude={"pagamento_id"}
            ),
        )
    assert leitura.status_code == resposta.status_code == 403
    assert chamadas == [(caso.auth[0].id, "relatorios.gerencial", caso.auth[1])] * 2
    assert not logs_pix(caso)


def semear_pendencias(caso, quantidade):
    ids = []
    for _ in range(quantidade):
        pagamento = VendaPagamento(
            tenant_id=caso.auth[1],
            caixa_id=caso.atual.id,
            venda_id=caso.venda.id,
            forma_pagamento="Pix",
            valor=1,
            status="confirmado",
            data_pagamento=datetime(2026, 10, 9, 12),
        )
        caso.db.add(pagamento)
        caso.db.flush()
        assinatura = assinatura_item(item_pagamento_auditoria(pagamento))
        for estado in ("nao_identificado", "identificado", "nao_identificado"):
            caso.db.add(
                AuditLog(
                    tenant_id=caso.auth[1],
                    user_id=caso.auth[0].id,
                    action=ACAO_PIX,
                    entity_type="pix_pagamento",
                    entity_id=pagamento.id,
                    timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
                    new_value=json.dumps(
                        {
                            "estado": estado,
                            "assinatura": assinatura,
                            "caixa_id": pagamento.caixa_id,
                            "venda_id": pagamento.venda_id,
                            "pagamento_id": pagamento.id,
                            "usuario_nome": caso.auth[0].nome,
                        }
                    ),
                    details=f"Comprovante {estado}",
                )
            )
        ids.append(pagamento.id)
    caso.db.flush()
    return ids


def consultar_alertas_com_consultas(caso, *, pagina=1, por_pagina=30):
    consultas = []

    def registrar(_conn, _cursor, statement, _params, context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append((statement, context.compiled_parameters))

    engine = caso.db.get_bind()
    caso.db.expire_all()
    event.listen(engine, "before_cursor_execute", registrar)
    try:
        resultado = listar_alertas_gestor(
            data_inicio=date(2026, 10, 22),
            data_fim=date(2026, 10, 22),
            pagina=pagina,
            por_pagina=por_pagina,
            db=caso.db,
            user_and_tenant=caso.auth,
        )
    finally:
        event.remove(engine, "before_cursor_execute", registrar)
    return resultado, consultas


def test_consultas_da_central_nao_crescem_de_um_para_trinta_pix(caso_alertas):
    caso = caso_alertas
    semear_pendencias(caso, 1)
    primeiro, consultas_um = consultar_alertas_com_consultas(caso)
    semear_pendencias(caso, 29)
    trinta, consultas_trinta = consultar_alertas_com_consultas(caso)
    assert primeiro["total"] == 1
    assert trinta["total"] == 30
    assert len(consultas_um) == len(consultas_trinta)
    assert len(consultas_trinta) <= 12
    assert all(
        len(item["identificacao_pix"]["historico"]) == 3 for item in trinta["itens"]
    )
    assert not any("FROM contas_receber" in sql for sql, _ in consultas_trinta)


def test_historico_da_central_carrega_somente_pagamentos_da_pagina(caso_alertas):
    caso = caso_alertas
    ids = semear_pendencias(caso, 3)
    resultado, consultas = consultar_alertas_com_consultas(caso, pagina=2, por_pagina=1)
    assert resultado["total"] == 3
    assert len(resultado["itens"]) == 1
    item = resultado["itens"][0]
    assert item["pagamento_id"] in ids
    assert len(item["identificacao_pix"]["historico"]) == 3
    consultas_historico = [
        parametros
        for sql, parametros in consultas
        if "audit_logs.entity_id IN (" in sql
    ]
    assert len(consultas_historico) == 1
    ids_consultados = [
        valor
        for parametros in consultas_historico[0]
        for chave, valor in parametros.items()
        if chave.startswith("entity_id_")
    ]
    assert ids_consultados == [item["pagamento_id"]]


@pytest.mark.parametrize("por_pagina", [0, 101])
@pytest.mark.asyncio
async def test_api_limita_pagina_a_cem_alertas_antes_da_consulta(
    caso, monkeypatch, por_pagina
):
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *_args, **_kwargs: None,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_http(caso, gestor=True)),
        base_url="http://dev.test",
    ) as client:
        resposta = await client.get(
            "/alertas-gestor", params={"por_pagina": por_pagina}
        )
    assert resposta.status_code == 422
    assert not logs_pix(caso)
