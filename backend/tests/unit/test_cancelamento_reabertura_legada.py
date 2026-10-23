"""Cancelar edição de venda legada não cria quitação nem libera fechamento vazio."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.campaigns import coupon_service, loyalty_service, sale_reopening_service
from app.campaigns.models import Coupon
from app.financeiro_models import ContaReceber, Recebimento
from app.models import AuditLog
from app.services.business_audit_service import log_business_event
from app.utils.timezone import as_brasilia_naive, now_brasilia
from app.vendas import VendaService, status_routes
from app.vendas import cancelamento_reabertura as restauracao
from app.vendas_models import Venda, VendaItem, VendaPagamento
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario


@pytest.fixture
def legado(cenario, monkeypatch):
    Coupon.__table__.create(cenario.db.get_bind())
    for modulo, nome in (
        (coupon_service, "reverse_coupon_redemptions_for_sale"),
        (loyalty_service, "void_loyalty_stamps_for_sale"),
    ):
        monkeypatch.setattr(modulo, nome, lambda *a, **kw: {})
    monkeypatch.setattr(
        sale_reopening_service,
        "void_quick_repurchase_coupons_for_sale",
        lambda *a, **kw: 0,
    )
    monkeypatch.setattr(Venda, "to_dict", lambda self: {"status": self.status})
    cenario.venda.status = "finalizada"
    cenario.venda.data_finalizacao = datetime(2026, 10, 2, 14, 30)
    cenario.venda.rentabilidade_snapshot = {"snapshot_version": 6, "total": 135}
    cenario.venda.rentabilidade_snapshot_em = datetime(2026, 10, 2, 14, 31)
    cenario.db.commit()
    cenario.usuario = SimpleNamespace(id=1, nome="Teste")
    return cenario


def _reabrir(cenario):
    return status_routes.reabrir_venda(1, cenario.db, (cenario.usuario, cenario.tenant))


def _cancelar(cenario, tenant=None, **dados):
    return status_routes.atualizar_status_venda(
        1,
        {"status": "finalizada", "cancelar_reabertura": True, **dados},
        cenario.db,
        (cenario.usuario, tenant or cenario.tenant),
    )


def _evento(cenario):
    return cenario.db.query(AuditLog).filter_by(action="business.sale.reopened").one()


def test_cancelar_reabertura_legada_restaura_estado_sem_criar_financeiro(
    legado, monkeypatch
):
    def nao_finalizar(**kwargs):
        pytest.fail("Cancelar reabertura legada não deve realizar nova finalização")

    monkeypatch.setattr(VendaService, "finalizar_venda", nao_finalizar)
    assert _reabrir(legado) == {"status": "aberta"}
    assert legado.venda.data_finalizacao is None
    evento = _evento(legado)
    snapshot = json.loads(evento.new_value)["metadata"]["legacy_restoration"]
    assert snapshot["data_finalizacao"] == "2026-10-02T14:30:00"
    assert _cancelar(legado) == {"success": True, "status": "finalizada"}
    assert legado.venda.data_finalizacao == datetime(2026, 10, 2, 14, 30)
    assert legado.venda.rentabilidade_snapshot["total"] == 135
    assert legado.venda.rentabilidade_snapshot_em == datetime(2026, 10, 2, 14, 31)
    for model in (VendaPagamento, ContaReceber, Recebimento):
        assert legado.db.query(model).count() == 0
    auditoria = (
        legado.db.query(AuditLog)
        .filter_by(action="business.sale.reopening_cancelled")
        .one()
    )
    assert json.loads(auditoria.new_value)["metadata"]["reopened_audit_id"] == evento.id


@pytest.mark.parametrize("alteracao", ["total", "item", "data", "observacoes"])
def test_cancelar_legado_rejeita_alteracao_persistida_apos_reabrir(legado, alteracao):
    _reabrir(legado)
    if alteracao == "item":
        legado.db.add(
            VendaItem(
                tenant_id=legado.tenant,
                venda_id=1,
                tipo="produto",
                produto_id=1,
                quantidade=1,
                preco_unitario=135,
                subtotal=135,
            )
        )
    elif alteracao == "total":
        legado.venda.total = Decimal("130.00")
    elif alteracao == "observacoes":
        legado.venda.observacoes = "Alteração salva após reabrir"
    else:
        legado.venda.updated_at += timedelta(seconds=1)
    legado.db.commit()
    with pytest.raises(HTTPException, match="alterada depois da reabertura") as erro:
        _cancelar(legado)
    assert erro.value.status_code == 409
    assert legado.venda.status == "aberta"
    assert legado.db.query(VendaPagamento).count() == 0


@pytest.mark.parametrize(
    "beneficio",
    [
        "commissions_removed",
        "coupon_reversal",
        "loyalty_void",
        "quick_repurchase_coupons_voided",
        "cashback_expenses_cancelled",
    ],
)
def test_cancelar_legado_rejeita_reabertura_que_removeu_beneficios(legado, beneficio):
    _reabrir(legado)
    evento = _evento(legado)
    dados = json.loads(evento.new_value)
    dados["metadata"][beneficio] = (
        {"removed": 1} if beneficio in {"coupon_reversal", "loyalty_void"} else 1
    )
    evento.new_value = json.dumps(dados)
    legado.db.commit()
    with pytest.raises(HTTPException, match="benefícios ou comissões"):
        _cancelar(legado)
    assert legado.venda.status == "aberta"


def test_flag_cancelamento_nao_libera_fechamento_de_venda_sem_auditoria(legado):
    legado.venda.status = "aberta"
    legado.db.commit()
    with pytest.raises(HTTPException, match="não há comprovação"):
        _cancelar(legado)
    assert legado.venda.status == "aberta"


def test_cancelar_legado_nao_acessa_venda_de_outro_tenant(legado):
    _reabrir(legado)
    with pytest.raises(HTTPException) as erro:
        _cancelar(legado, tenant=uuid4())
    assert erro.value.status_code == 404
    assert legado.venda.status == "aberta"


def test_cancelar_legado_rejeita_nota_fiscal_ativa(legado):
    _reabrir(legado)
    legado.venda.nfe_status = "autorizada"
    legado.db.commit()
    with pytest.raises(HTTPException, match="fiscal mudou"):
        _cancelar(legado)
    assert legado.venda.status == "aberta"


def _auditoria_antiga(cenario):
    cenario.venda.status = "aberta"
    cenario.venda.data_finalizacao = None
    cenario.venda.updated_at = now_brasilia()
    cenario.db.commit()
    return log_business_event(
        db=cenario.db,
        tenant_id=cenario.tenant,
        user_id=cenario.usuario.id,
        event="sale.reopened",
        entity_type="vendas",
        entity_id=1,
        old_value={"status": "finalizada"},
        metadata={
            "sale_number": cenario.venda.numero_venda,
            "previous_status": "finalizada",
            "new_status": "aberta",
            "customer_id": None,
            "coupon_code": None,
            "sale_total": 135.0,
            "commissions_removed": 0,
            "coupon_reversal": {},
            "loyalty_void": {},
        },
        commit=True,
    )


def test_cancelar_reabertura_antiga_intacta_sem_inventar_data_ou_pagamento(legado):
    _auditoria_antiga(legado)
    assert _cancelar(legado) == {"success": True, "status": "finalizada"}
    assert legado.venda.data_finalizacao is None
    assert legado.db.query(VendaPagamento).count() == 0
    auditoria = (
        legado.db.query(AuditLog)
        .filter_by(action="business.sale.reopening_cancelled")
        .one()
    )
    assert (
        json.loads(auditoria.new_value)["metadata"]["original_finalization_date_known"]
        is False
    )


@pytest.mark.parametrize("alteracao", ["venda", "auditoria", "item"])
def test_cancelar_reabertura_antiga_rejeita_alteracoes_posteriores(legado, alteracao):
    evento = _auditoria_antiga(legado)
    if alteracao == "venda":
        legado.venda.updated_at = evento.timestamp.replace(tzinfo=None) + timedelta(
            seconds=1
        )
    elif alteracao == "item":
        legado.db.add(
            VendaItem(
                tenant_id=legado.tenant,
                venda_id=1,
                tipo="produto",
                produto_id=1,
                quantidade=1,
                preco_unitario=135,
                subtotal=135,
                updated_at=evento.timestamp.replace(tzinfo=None) + timedelta(seconds=1),
            )
        )
    else:
        legado.db.add(
            AuditLog(
                tenant_id=legado.tenant,
                user_id=1,
                action="update",
                entity_type="vendas",
                entity_id=1,
                details="Venda alterada após reabertura",
            )
        )
    legado.db.commit()
    with pytest.raises(HTTPException) as erro:
        _cancelar(legado)
    assert erro.value.status_code == 409
    assert legado.venda.status == "aberta"


def test_venda_moderna_sem_pagamento_remanescente_nao_vira_legada(legado):
    evento = _auditoria_antiga(legado)
    dados = json.loads(evento.new_value)
    dados["metadata"]["legacy_restoration"] = None
    evento.new_value = json.dumps(dados)
    legado.db.commit()
    with pytest.raises(HTTPException, match="tinha registros financeiros"):
        _cancelar(legado)


def test_cancelamento_com_financeiro_mantem_orquestrador_existente(legado, monkeypatch):
    legado.venda.status = "aberta"
    legado.db.add(
        VendaPagamento(
            tenant_id=legado.tenant, venda_id=1, forma_pagamento="PIX", valor=135
        )
    )
    legado.db.commit()
    chamadas = []

    def finalizar(**kwargs):
        chamadas.append(kwargs)
        legado.venda.status = "finalizada"
        return {"venda": {"status": "finalizada"}}

    monkeypatch.setattr(VendaService, "finalizar_venda", finalizar)
    assert _cancelar(legado) == {"success": True, "status": "finalizada"}
    assert len(chamadas) == 1
    assert chamadas[0]["pagamentos"] == []


def test_beneficio_vinculado_e_detectado_por_tenant_e_numero_da_venda(legado):
    outro_tenant = uuid4()
    legado.db.execute(
        Coupon.__table__.insert().values(
            id=1,
            tenant_id=outro_tenant,
            customer_id=1,
            code="OUTRO",
            coupon_type="fixed",
            discount_value=1,
            meta={"source_kind": "quick_repurchase", "source_venda_id": "1"},
        )
    )
    legado.db.commit()
    assert not restauracao._tem_beneficios_vinculados(
        legado.db, legado.venda, legado.tenant
    )
    legado.db.execute(
        Coupon.__table__.update().where(Coupon.id == 1).values(tenant_id=legado.tenant)
    )
    legado.db.commit()
    assert restauracao._tem_beneficios_vinculados(
        legado.db, legado.venda, legado.tenant
    )


@pytest.mark.parametrize("alteracao", ["venda", "item"])
def test_reabertura_antiga_compara_horario_local_com_auditoria_utc(legado, alteracao):
    evento = _auditoria_antiga(legado)
    evento.timestamp = datetime(2026, 10, 23, 22, 0, tzinfo=timezone.utc)
    legado.venda.updated_at = datetime(2026, 10, 23, 19, 0)
    if alteracao == "venda":
        legado.venda.updated_at = datetime(2026, 10, 23, 19, 30)
    else:
        legado.db.add(
            VendaItem(
                tenant_id=legado.tenant,
                venda_id=1,
                tipo="produto",
                produto_id=1,
                quantidade=1,
                preco_unitario=135,
                subtotal=135,
                updated_at=datetime(2026, 10, 23, 19, 30),
            )
        )
    legado.db.commit()
    with pytest.raises(HTTPException) as erro:
        _cancelar(legado)
    assert erro.value.status_code == 409
    assert legado.venda.status == "aberta"


def test_reabertura_antiga_nao_aceita_financeiro_alterado_sem_mudar_venda(legado):
    evento = _auditoria_antiga(legado)
    legado.db.add(
        AuditLog(
            tenant_id=legado.tenant,
            user_id=1,
            action="delete",
            entity_type="venda_pagamentos",
            entity_id=22,
            old_value=json.dumps({"venda_id": 1}),
        )
    )
    legado.db.commit()
    assert as_brasilia_naive(legado.venda.updated_at) <= restauracao._horario_auditoria(
        evento.timestamp
    )
    with pytest.raises(HTTPException, match="alterações posteriores"):
        _cancelar(legado)
    assert legado.venda.status == "aberta"
