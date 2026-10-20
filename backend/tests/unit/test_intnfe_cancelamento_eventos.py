"""Cancelamento recusado ou pendente não equivale a uma nota cancelada."""

from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.intnfe import emission
from app.intnfe.client import IntNFeError
from app.nfe.listagem_normalizacao import _normalizar_nota_venda_local


RECUSA_501 = {
    "tipoEvento": "Cancelamento",
    "tipoEventoCodigo": 110111,
    "autorizado": False,
    "protocolo": None,
    "codigoRetorno": "501",
    "motivoRetorno": "NFC-e autorizada ha mais de . 30 minutos",
    "criadoEm": "2026-10-20T16:52:06.447Z",
    "xmlEvento": None,
}


def venda_teste():
    return SimpleNamespace(
        id=1368366,
        tenant_id=uuid4(),
        numero_venda="202610200012",
        status="pago_nf",
        nfe_provider="intnfe",
        nfe_tipo="nfce",
        nfe_modelo="65",
        nfe_correlation_id="corr-nota",
        nfe_status="autorizada",
        nfe_numero=18574,
        nfe_serie=2,
        nfe_chave="1" * 44,
        nfe_protocolo="141261734844045",
        nfe_ambiente=1,
        nfe_xml="<xml />",
        nfe_data_emissao=None,
        nfe_data_autorizacao=datetime(2026, 10, 20, 13, 21, 24),
        nfe_codigo_erro=None,
        nfe_motivo_rejeicao=None,
        nfe_cancelamento_status=None,
        nfe_cancelamento_codigo=None,
        nfe_cancelamento_motivo=None,
        nfe_cancelamento_solicitado_em=None,
        nfe_bling_id=None,
        canal="loja_fisica",
        loja_origem="Loja",
        total=37.9,
        cliente=None,
    )


@pytest.fixture
def contexto(monkeypatch):
    venda, db, api = venda_teste(), MagicMock(), MagicMock()
    api.document_status.return_value = {"status": 3}
    api.document_events.return_value = []
    api.cancel_document.return_value = {}
    monkeypatch.setattr(emission, "_connection", lambda *_args, **_kw: object())
    monkeypatch.setattr(emission, "_access_token", lambda *_args: "token-teste")
    monkeypatch.setattr(emission, "_remember_sequence_start", lambda *_args: None)
    monkeypatch.setattr(emission, "tentar_enfileirar_documento", lambda *_args: None)
    audit = MagicMock()
    monkeypatch.setattr(emission, "log_action", audit)
    return venda, db, api, audit


@pytest.mark.parametrize("resposta", [{}, {"success": True}, {"status": "processando"}])
def test_post_aceito_com_nota_autorizada_e_sem_eventos_continua_solicitado(
    contexto, resposta
):
    venda, db, api, audit = contexto
    api.cancel_document.return_value = resposta

    resultado = emission.cancel(
        db, venda, api, "Cliente desistiu desta compra", user_id=74
    )

    assert resultado["success"] is False
    assert resultado["cancelamento_status"] == "solicitado"
    assert resultado["cancelamento_solicitado"] is True
    assert venda.nfe_status == "autorizada"
    assert venda.nfe_cancelamento_solicitado_em.tzinfo is not None
    assert [c.kwargs["action"] for c in audit.call_args_list] == [
        "nfe_cancelamento_tentativa",
        "nfe_cancelamento_resultado",
    ]
    assert all(c.kwargs["commit"] is False for c in audit.call_args_list)
    assert db.commit.call_count == 2


@pytest.mark.parametrize("origem", ["post", "eventos"])
def test_recusa_501_fica_explicita_sem_marcar_nota_cancelada(contexto, origem):
    venda, db, api, _audit = contexto
    venda.status = "cancelada"
    if origem == "post":
        api.cancel_document.return_value = RECUSA_501
        resultado = emission.cancel(db, venda, api, "Cliente desistiu desta compra")
    else:
        api.document_events.return_value = [RECUSA_501]
        resultado = emission.reconcile(db, venda, api)

    assert resultado["cancelamento_status"] == "recusado"
    assert resultado["cancelamento_codigo"] == "501"
    assert "30 minutos" in resultado["cancelamento_motivo"]
    assert resultado["cancelamento_solicitado"] is False
    assert venda.nfe_status == "autorizada"
    assert venda.status == "cancelada"
    assert venda.nfe_motivo_rejeicao is None
    assert venda.nfe_codigo_erro is None
    assert venda.nfe_cancelamento_codigo == "501"
    assert resultado["pendencia_fiscal_cancelamento"] is True
    nota = _normalizar_nota_venda_local(venda)
    assert nota["status"] == "autorizada"
    assert nota["venda_status"] == "cancelada"
    assert nota["nfe_cancelamento_status"] == "recusado"
    assert nota["cancelamento_codigo"] == "501"


def test_http200_com_erro_no_corpo_nao_vira_solicitacao_aceita(contexto):
    venda, db, api, _audit = contexto
    api.cancel_document.return_value = {
        "erro": "CancelamentoRecusado",
        "mensagem": "Pedido recusado pelo emissor",
    }

    resultado = emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert resultado["success"] is False
    assert resultado["cancelamento_status"] == "recusado"
    assert resultado["cancelamento_solicitado"] is False
    assert resultado["cancelamento_codigo"] == "CancelamentoRecusado"


@pytest.mark.parametrize("confirmacao", ["status", "evento"])
def test_confirmacao_precisa_status5_ou_evento_autorizado_com_protocolo(
    contexto, confirmacao
):
    venda, db, api, _audit = contexto
    if confirmacao == "status":
        api.document_status.return_value = {"status": 5}
    else:
        api.document_events.return_value = [
            {
                **RECUSA_501,
                "autorizado": True,
                "protocolo": "135260000000001",
                "codigoRetorno": "135",
            }
        ]

    resultado = emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert resultado["success"] is True
    assert resultado["cancelamento_status"] == "confirmado"
    assert resultado["cancelamento_solicitado"] is False
    assert venda.nfe_status == "cancelada"


def test_timeout_preserva_incerteza_e_detalhe_legivel_sem_falsa_aceitacao(contexto):
    from app.nfe_routes import _direct_failure

    venda, db, api, _audit = contexto
    api.cancel_document.side_effect = IntNFeError("EmissorIndisponivel", uncertain=True)

    with pytest.raises(emission.DirectEmissionError) as erro:
        emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    resposta = _direct_failure(erro.value)
    assert resposta.status_code == 503
    assert "recebimento" in resposta.detail["mensagem"]
    assert resposta.detail["cancelamento_status"] == "pendente"
    assert resposta.detail["cancelamento_solicitado"] is False
    assert venda.nfe_status == "autorizada"


def test_post_aceito_com_get_indisponivel_preserva_solicitado(contexto):
    venda, db, api, _audit = contexto
    api.document_status.side_effect = IntNFeError("EmissorIndisponivel")

    with pytest.raises(emission.DirectEmissionError) as erro:
        emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert erro.value.cancelamento["cancelamento_status"] == "solicitado"
    assert erro.value.cancelamento["cancelamento_solicitado"] is True
    assert venda.nfe_status == "autorizada"


@pytest.mark.parametrize("estado", ["pendente", "solicitado"])
def test_pedido_em_andamento_nao_dispara_outro_post(contexto, estado):
    venda, db, api, _audit = contexto
    venda.nfe_cancelamento_status = estado
    venda.nfe_cancelamento_solicitado_em = datetime.now(timezone.utc)

    with pytest.raises(emission.DirectEmissionError) as erro:
        emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert erro.value.status == 409
    assert "andamento" in str(erro.value)
    api.cancel_document.assert_not_called()


def test_timeout_tardio_nao_rebaixa_confirmacao_concorrente(contexto):
    venda, db, api, _audit = contexto

    def timeout(*_args):
        venda.nfe_status = "cancelada"
        venda.nfe_cancelamento_status = "confirmado"
        raise IntNFeError("EmissorIndisponivel", uncertain=True)

    api.cancel_document.side_effect = timeout
    resultado = emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert resultado["success"] is True
    assert resultado["cancelamento_status"] == "confirmado"
    assert resultado["cancelamento_solicitado"] is False
    assert venda.nfe_status == "cancelada"


def test_corpo_recusado_preserva_motivo_mesmo_se_consulta_falhar(contexto):
    venda, db, api, _audit = contexto
    api.cancel_document.return_value = RECUSA_501
    api.document_status.side_effect = IntNFeError("EmissorIndisponivel")

    resultado = emission.cancel(db, venda, api, "Cliente desistiu desta compra")

    assert resultado["success"] is False
    assert resultado["cancelamento_status"] == "recusado"
    assert resultado["cancelamento_codigo"] == "501"
    assert "30 minutos" in resultado["cancelamento_motivo"]


def test_nova_nota_nao_pode_ser_emitida_para_venda_ja_cancelada(contexto):
    venda, db, api, _audit = contexto
    venda.status = "cancelada"
    venda.nfe_correlation_id = None

    with pytest.raises(emission.DirectEmissionError, match="venda cancelada"):
        emission.issue(db, SimpleNamespace(id=venda.tenant_id), venda, "nfce", api)

    api.issue_document.assert_not_called()


def test_emissao_em_voo_nao_reativa_venda_cancelada_durante_envio(
    contexto, monkeypatch
):
    venda, db, api, _audit = contexto
    venda.nfe_correlation_id = None
    venda.nfe_idempotency_key = None
    monkeypatch.setattr(
        emission,
        "_connection",
        lambda *_args, **_kw: SimpleNamespace(emission_environment=1),
    )
    monkeypatch.setattr(emission, "build_payload", lambda *_args: {"serie": "2"})
    monkeypatch.setattr(
        emission, "reconcile", lambda _db, atual, *_a, **_kw: {"status": atual.status}
    )
    api.issue_document.return_value = {"correlationId": "corr-enviada"}

    def reler(_venda, **kwargs):
        if kwargs.get("attribute_names") == ["status"]:
            _venda.status = "cancelada"

    db.refresh.side_effect = reler
    resultado = emission.issue(
        db, SimpleNamespace(id=venda.tenant_id), venda, "nfce", api
    )

    assert resultado["status"] == "cancelada"
    assert venda.nfe_correlation_id == "corr-enviada"
    assert venda.status == "cancelada"


def test_recusa_antiga_nao_sobrescreve_nova_solicitacao(contexto):
    venda, db, api, _audit = contexto
    api.document_events.return_value = [RECUSA_501]
    venda.nfe_cancelamento_status = "solicitado"
    venda.nfe_cancelamento_solicitado_em = datetime(
        2026, 10, 21, 10, tzinfo=timezone.utc
    )

    resultado = emission.reconcile(db, venda, api)

    assert resultado["cancelamento_status"] == "solicitado"
    assert resultado["cancelamento_codigo"] is None


def test_consulta_preserva_horario_real_da_autorizacao(contexto):
    venda, db, api, _audit = contexto
    api.document_status.return_value = {
        "status": 3,
        "autorizadoEm": "2026-10-20T16:21:24.596Z",
    }

    emission.reconcile(db, venda, api)
    assert venda.nfe_data_autorizacao == datetime(2026, 10, 20, 13, 21, 24, 596000)
    api.document_status.return_value = {"status": 3}
    emission.reconcile(db, venda, api)
    assert venda.nfe_data_autorizacao == datetime(2026, 10, 20, 13, 21, 24, 596000)


def test_migration_aditiva_preserva_vendas_e_fiscal_ao_aplicar_e_reverter():
    migration = runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzl20261020a1_venda_cancelamento_fiscal.py"
        )
    )
    assert migration["down_revision"] == "zzzzk20261020a1"
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE vendas (id INTEGER PRIMARY KEY, status TEXT, nfe_status TEXT)"
            )
        )
        conn.execute(text("INSERT INTO vendas VALUES (1, 'cancelada', 'autorizada')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration["upgrade"]()
            assert {c["name"] for c in inspect(conn).get_columns("vendas")} >= {
                "nfe_cancelamento_status",
                "nfe_cancelamento_codigo",
                "nfe_cancelamento_motivo",
                "nfe_cancelamento_solicitado_em",
            }
            assert conn.execute(text("SELECT status,nfe_status FROM vendas")).one() == (
                "cancelada",
                "autorizada",
            )
            migration["downgrade"]()
            assert conn.execute(text("SELECT status,nfe_status FROM vendas")).one() == (
                "cancelada",
                "autorizada",
            )
    engine.dispose()


@pytest.mark.parametrize("vinculo", ["venda_id", "correlacao", "outro_tenant"])
def test_lista_real_enriquece_cache_intnfe_com_estado_atual_sem_vazar_payload(
    monkeypatch, vinculo
):
    from sqlalchemy.orm import Session
    from app.nfe import listagem_rapida
    from app.nfe_cache_models import BlingNotaFiscalCache
    from app.vendas_models import Venda
    from app.tenancy.context import tenant_context

    engine = create_engine("sqlite://")
    Venda.__table__.create(engine)
    BlingNotaFiscalCache.__table__.create(engine)
    tenant, outro = uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(
            Venda.__table__.insert().values(
                id=1,
                tenant_id=outro if vinculo == "outro_tenant" else tenant,
                numero_venda="202610200012",
                user_id=74,
                vendedor_id=74,
                total=37.9,
                subtotal=37.9,
                status="cancelada",
                nfe_status="autorizada",
                nfe_provider="intnfe",
                nfe_correlation_id="corr-nota",
                nfe_cancelamento_status="recusado",
                nfe_cancelamento_codigo="501",
                nfe_cancelamento_motivo=RECUSA_501["motivoRetorno"],
            )
        )
        conn.execute(
            BlingNotaFiscalCache.__table__.insert().values(
                id=1,
                tenant_id=tenant,
                venda_id=1 if vinculo != "correlacao" else None,
                provider="intnfe",
                bling_id="corr-nota",
                modelo=65,
                tipo="nfce",
                numero="18574",
                serie="2",
                status="Autorizada",
                source="local_venda",
                resumo_payload={"segredo": "NAO-EXIBIR", "cancelamento_codigo": "999"},
            )
        )
    monkeypatch.setattr(
        listagem_rapida, "tenant_pode_usar_bling_global", lambda *_: False
    )
    with tenant_context(tenant), Session(engine) as db:
        resposta = listagem_rapida.consultar_pagina(db, tenant)
        assert resposta["total"] == 1
        nota = resposta["notas"][0]
        assert "NAO-EXIBIR" not in str(nota)
        if vinculo == "outro_tenant":
            assert "cancelamento_motivo" not in nota
            assert "cancelamento_codigo" not in nota
        else:
            assert nota["status"] == "autorizada"
            assert nota["venda_status"] == "cancelada"
            assert nota["cancelamento_status"] == "recusado"
            assert nota["nfe_cancelamento_codigo"] == "501"
            assert "30 minutos" in nota["cancelamento_motivo"]
            assert nota["pendencia_fiscal_cancelamento"] is True
    engine.dispose()
