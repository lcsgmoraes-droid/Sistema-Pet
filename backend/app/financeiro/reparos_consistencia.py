"""Reparos conservadores de consistencia financeira por tenant."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.financeiro.reparos_consistencia_centavos import (
    _apply_centavo_actions,
    _build_centavo_actions,
)
from app.financeiro.reparos_consistencia_common import _is_recebimento_imediato
from app.financeiro.reparos_consistencia_contas_pagar import (
    _apply_cp_actions,
    _build_cp_missing_actions,
)
from app.financeiro.reparos_consistencia_contas_receber import (
    _apply_cr_actions,
    _build_cr_missing_actions,
)
from app.notas_entrada.xml_parser import parse_nfe_xml


CONFIRM_TOKEN_REPARO_FINANCEIRO = "REPARAR_FINANCEIRO_HISTORICO"

__all__ = [
    "CONFIRM_TOKEN_REPARO_FINANCEIRO",
    "_is_recebimento_imediato",
    "reparar_financeiro_consistencia",
]


def _build_report(
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool,
    cr_actions: list[dict[str, Any]],
    cr_applied: list[dict[str, Any]],
    cr_skipped: list[dict[str, Any]],
    centavo_actions: list[dict[str, Any]],
    centavo_skipped: list[dict[str, Any]],
    cp_actions: list[dict[str, Any]],
    cp_applied: list[dict[str, Any]],
    cp_skipped: list[dict[str, Any]],
) -> dict[str, Any]:
    received_actions = [
        action
        for action in (cr_applied or cr_actions)
        if action["status"] == "recebido"
    ]
    return {
        "ok": True,
        "applied": bool(apply_changes),
        "dry_run": not bool(apply_changes),
        "tenant_id": tenant_id,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        "resumo": {
            "contas_receber_criadas": len(cr_actions),
            "recebimentos_criados": len(received_actions),
            "ajustes_centavos_aplicaveis": len(centavo_actions),
            "ajustes_centavos_pulados": len(centavo_skipped),
            "contas_pagar_criadas": len(cp_actions),
            "notas_puladas": len(cp_skipped),
            "itens_pulados": len(cr_skipped) + len(centavo_skipped) + len(cp_skipped),
        },
        "contas_receber": {
            "planejadas": cr_actions,
            "aplicadas": cr_applied,
            "puladas": cr_skipped,
        },
        "ajustes_centavos": {
            "planejados": centavo_actions,
            "aplicados": centavo_actions if apply_changes else [],
            "pulados": centavo_skipped,
        },
        "contas_pagar": {
            "planejadas": cp_actions,
            "aplicadas": cp_applied,
            "puladas": cp_skipped,
        },
    }


def reparar_financeiro_consistencia(
    db: Session,
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Planeja ou aplica reparos financeiros historicos seguros.

    Escopo intencionalmente conservador:
    - cria contas a receber ausentes a partir de venda_pagamentos;
    - ajusta centavos apenas em parcelas pendentes e sem recebimento;
    - cria contas a pagar apenas para notas processadas sem CP.
    """

    if apply_changes and confirm_token != CONFIRM_TOKEN_REPARO_FINANCEIRO:
        db.rollback()
        return {
            "ok": False,
            "applied": False,
            "dry_run": False,
            "error": f"confirm_token deve ser {CONFIRM_TOKEN_REPARO_FINANCEIRO}",
        }

    params = {
        "tenant_id": str(tenant_id),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }

    cr_actions, cr_skipped = _build_cr_missing_actions(
        db, tenant_id=str(tenant_id), params=params
    )
    centavo_actions, centavo_skipped = _build_centavo_actions(
        db, tenant_id=str(tenant_id), params=params
    )
    cp_actions, cp_skipped = _build_cp_missing_actions(
        db,
        tenant_id=str(tenant_id),
        params=params,
        parse_xml=parse_nfe_xml,
    )

    cr_applied: list[dict[str, Any]] = []
    cp_applied: list[dict[str, Any]] = []
    try:
        if apply_changes:
            cr_applied = _apply_cr_actions(db, cr_actions)
            _apply_centavo_actions(db, centavo_actions)
            cp_applied = _apply_cp_actions(db, cp_actions)
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return _build_report(
        tenant_id=str(tenant_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        apply_changes=apply_changes,
        cr_actions=cr_actions,
        cr_applied=cr_applied,
        cr_skipped=cr_skipped,
        centavo_actions=centavo_actions,
        centavo_skipped=centavo_skipped,
        cp_actions=cp_actions,
        cp_applied=cp_applied,
        cp_skipped=cp_skipped,
    )
