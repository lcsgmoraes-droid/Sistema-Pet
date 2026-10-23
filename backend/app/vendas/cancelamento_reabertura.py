"""Restaura apenas a reabertura intacta de venda legada sem financeiro.

Cancelar edição não é um recebimento nem uma nova finalização. A exceção é
comprovada pela auditoria e nunca se aplica ao fechamento normal de uma venda.
"""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import String, cast, or_

from app.financeiro_models import ContaReceber
from app.models import AuditLog
from app.services.business_audit_service import log_business_event
from app.utils.timezone import as_brasilia_naive
from app.vendas.fiscal_status import nota_fiscal_requer_regularizacao
from app.vendas_models import VendaItem, VendaPagamento


def _tem_financeiro(db, venda, tenant_id):
    return any(
        db.query(model.id).filter_by(tenant_id=tenant_id, venda_id=venda.id).first()
        is not None
        for model in (VendaPagamento, ContaReceber)
    )


def _hash_estado(db, venda, tenant_id):
    def campos(objeto):
        return {
            coluna.name: getattr(objeto, coluna.name)
            for coluna in objeto.__table__.columns
        }

    itens = (
        db.query(VendaItem)
        .filter_by(tenant_id=tenant_id, venda_id=venda.id)
        .order_by(VendaItem.id)
        .all()
    )
    estado = {"venda": campos(venda), "itens": [campos(item) for item in itens]}
    return hashlib.sha256(
        json.dumps(estado, default=str, sort_keys=True).encode("utf-8")
    ).hexdigest()


def preparar_restauracao_legada(db, venda, tenant_id):
    if venda.status != "finalizada" or _tem_financeiro(db, venda, tenant_id):
        return None
    return {
        "data_finalizacao": venda.data_finalizacao.isoformat()
        if venda.data_finalizacao
        else None,
        "rentabilidade_snapshot": venda.rentabilidade_snapshot,
        "rentabilidade_snapshot_em": venda.rentabilidade_snapshot_em.isoformat()
        if venda.rentabilidade_snapshot_em
        else None,
    }


def registrar_estado_reaberto(db, venda, tenant_id, restauracao):
    if restauracao is not None:
        db.flush()
        restauracao["estado_reaberto_sha256"] = _hash_estado(db, venda, tenant_id)
    return restauracao


def _objeto_json(valor):
    try:
        objeto = json.loads(valor or "{}")
        return objeto if isinstance(objeto, dict) else {}
    except (TypeError, ValueError):
        return {}


def _horario_auditoria(valor):
    # AuditLog grava um instante UTC; SQLite pode remover sua informação de fuso.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return as_brasilia_naive(valor)


def _houve_alteracao_posterior(db, venda, tenant_id, evento):
    posteriores = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.id > evento.id,
            or_(
                (AuditLog.entity_type == "vendas") & (AuditLog.entity_id == venda.id),
                AuditLog.entity_type.in_(("venda_pagamento", "venda_pagamentos")),
            ),
        )
        .all()
    )
    for log in posteriores:
        if log.entity_type != "vendas":
            anterior = _objeto_json(log.old_value)
            atual = _objeto_json(log.new_value)
            if venda.id in (
                anterior.get("venda_id"),
                atual.get("venda_id"),
                (atual.get("resultado") or {}).get("venda_id"),
            ):
                return True
            continue
        # A própria rota grava este segundo log logo após confirmar a reabertura.
        if not (
            log.action == "update"
            and log.user_id == evento.user_id
            and (log.details or "").startswith(f"Venda #{venda.id} reaberta (")
            and 0
            <= (
                _horario_auditoria(log.timestamp) - _horario_auditoria(evento.timestamp)
            ).total_seconds()
            <= 5
        ):
            return True
    return False


def _tem_beneficios_vinculados(db, venda, tenant_id):
    from app.campaigns.cashback_sale_reversal import (
        _sale_cashback_executions,
        _sale_redemptions,
    )
    from app.campaigns.models import Coupon

    if venda.cliente_id and (
        _sale_cashback_executions(
            db, tenant_id=tenant_id, sale_id=venda.id, customer_id=venda.cliente_id
        )
        or _sale_redemptions(
            db, tenant_id=tenant_id, sale_id=venda.id, customer_id=venda.cliente_id
        )
    ):
        return True
    # Cupons emitidos pela venda têm histórico próprio, mesmo depois de estornados.
    return (
        db.query(Coupon.id)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.meta["source_kind"].as_string() == "quick_repurchase",
            cast(Coupon.meta["source_venda_id"].as_string(), String) == str(venda.id),
        )
        .first()
        is not None
    )


def restaurar_reabertura_legada(db, venda, tenant_id, user_id):
    """True quando restaurou; False mantém a finalização financeira existente."""
    if _tem_financeiro(db, venda, tenant_id):
        return False

    def recusar(motivo):
        raise HTTPException(
            status_code=409,
            detail=(
                "Não foi possível cancelar a reabertura desta venda legada com "
                f"segurança: {motivo}. Nenhum pagamento foi criado."
            ),
        )

    if venda.status != "aberta" or nota_fiscal_requer_regularizacao(venda):
        recusar("o estado comercial ou fiscal mudou")
    evento = (
        db.query(AuditLog)
        .filter_by(
            tenant_id=tenant_id,
            entity_type="vendas",
            entity_id=venda.id,
            action="business.sale.reopened",
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .first()
    )
    if not evento:
        recusar("não há comprovação da finalização anterior na auditoria")
    metadata = _objeto_json(evento.new_value).get("metadata") or {}
    if (
        _objeto_json(evento.old_value).get("status") != "finalizada"
        or metadata.get("previous_status") != "finalizada"
        or metadata.get("new_status") != "aberta"
    ):
        recusar("a auditoria não comprova uma venda anteriormente finalizada")
    if _houve_alteracao_posterior(db, venda, tenant_id, evento):
        recusar("há alterações posteriores à reabertura")
    if (
        metadata.get("commissions_removed") != 0
        or any((metadata.get("coupon_reversal") or {}).values())
        # Campanhas consultadas podem ter apenas carimbos já estornados.
        # Esse contador não significa que a reabertura retirou benefícios.
        or any(
            valor
            for campo, valor in (metadata.get("loyalty_void") or {}).items()
            if campo != "affected_campaigns"
        )
        or metadata.get("quick_repurchase_coupons_voided", 0)
        or metadata.get("cashback_expenses_cancelled", 0)
        or _tem_beneficios_vinculados(db, venda, tenant_id)
    ):
        recusar("há benefícios ou comissões que exigem conferência")

    restauracao = metadata.get("legacy_restoration")
    if "legacy_restoration" in metadata and not restauracao:
        recusar("a venda tinha registros financeiros quando foi reaberta")
    if restauracao:
        if restauracao.get("estado_reaberto_sha256") != _hash_estado(
            db, venda, tenant_id
        ):
            recusar("a venda foi alterada depois da reabertura")
    else:
        # Compatibilidade conservadora com reaberturas anteriores ao snapshot.
        # A data original já foi apagada pelo código antigo e não é inventada.
        if (
            metadata.get("sale_number") != venda.numero_venda
            or metadata.get("customer_id") != venda.cliente_id
            or metadata.get("coupon_code") != venda.cupom_code
            or str(metadata.get("sale_total")) != str(float(venda.total))
            or venda.data_finalizacao is not None
            or not venda.updated_at
            or as_brasilia_naive(venda.updated_at)
            > _horario_auditoria(evento.timestamp)
        ):
            recusar("não há prova suficiente de que a venda permaneceu intacta")
        itens = (
            db.query(VendaItem).filter_by(tenant_id=tenant_id, venda_id=venda.id).all()
        )
        if any(
            not item.updated_at
            or as_brasilia_naive(item.updated_at) > _horario_auditoria(evento.timestamp)
            for item in itens
        ):
            recusar("há alterações posteriores à reabertura")
        restauracao = {}

    venda.status = "finalizada"
    for campo in ("data_finalizacao", "rentabilidade_snapshot_em"):
        valor = restauracao.get(campo)
        setattr(venda, campo, datetime.fromisoformat(valor) if valor else None)
    venda.rentabilidade_snapshot = restauracao.get("rentabilidade_snapshot")
    venda.updated_at = datetime.now()
    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event="sale.reopening_cancelled",
        entity_type="vendas",
        entity_id=venda.id,
        old_value={"status": "aberta"},
        metadata={
            "reopened_audit_id": evento.id,
            "status": "finalizada",
            "legacy_without_financial_records": True,
            "original_finalization_date_known": bool(restauracao),
        },
        details="Reabertura legada cancelada sem criar pagamentos ou recebíveis",
        commit=False,
    )
    db.commit()
    return True
