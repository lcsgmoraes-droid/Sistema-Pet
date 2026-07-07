"""Reparos de contas a pagar ausentes para notas processadas."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.reparos_consistencia_common import (
    _as_date,
    _date_str,
    _money,
    _money_str,
    _resolve_tipo_produto_revenda_id,
    _rows,
)


def _fetch_notas_sem_contas_pagar(
    db: Session, params: dict[str, Any]
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            ne.id AS nota_id,
            ne.numero_nota AS numero_nota,
            ne.fornecedor_id AS fornecedor_id,
            ne.data_emissao AS data_emissao,
            ne.data_entrada AS data_entrada,
            ne.valor_total AS valor_total,
            ne.xml_content AS xml_content,
            ne.status AS status,
            COALESCE(ne.percentual_online, 0) AS percentual_online,
            COALESCE(ne.percentual_loja, 100) AS percentual_loja,
            ne.user_id AS user_id
        FROM notas_entrada ne
        WHERE CAST(ne.tenant_id AS TEXT) = :tenant_id
          AND ne.data_entrada >= :data_inicio
          AND ne.data_entrada < :data_fim
          AND NOT EXISTS (
              SELECT 1
              FROM contas_pagar cp
              WHERE CAST(cp.tenant_id AS TEXT) = CAST(ne.tenant_id AS TEXT)
                AND cp.nota_entrada_id = ne.id
          )
        ORDER BY ne.data_entrada ASC, ne.id ASC
        """,
        params,
    )


def _duplicatas_nota(
    nota: dict[str, Any], parse_xml: Callable[[str], dict[str, Any]]
) -> tuple[list[dict[str, Any]], str | None]:
    xml_content = str(nota.get("xml_content") or "")
    if not xml_content.strip():
        return [], "Nota sem XML salvo para extrair duplicatas."

    try:
        dados_xml = parse_xml(xml_content)
    except Exception as exc:  # pragma: no cover - detalhe vem de XML real
        return [], f"XML da nota nao pode ser interpretado: {exc}"

    duplicatas = list(dados_xml.get("duplicatas") or [])
    if not duplicatas:
        data_base = _as_date(nota["data_emissao"] or nota["data_entrada"])
        duplicatas = [
            {
                "numero": f"{nota['numero_nota']}-1",
                "vencimento": data_base + timedelta(days=30),
                "valor": nota["valor_total"],
            }
        ]

    total_dup = sum((_money(dup.get("valor")) for dup in duplicatas), Decimal("0.00"))
    total_nota = _money(nota["valor_total"])
    if abs(total_dup - total_nota) > Decimal("0.05"):
        return [], (
            "Soma das duplicatas diverge do valor da nota: "
            f"{_money_str(total_dup)} vs {_money_str(total_nota)}."
        )

    return duplicatas, None


def _build_cp_missing_actions(
    db: Session,
    *,
    tenant_id: str,
    params: dict[str, Any],
    parse_xml: Callable[[str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    tipo_produto_revenda_id = _resolve_tipo_produto_revenda_id(db, tenant_id=tenant_id)

    for nota in _fetch_notas_sem_contas_pagar(db, params):
        if str(nota["status"]).lower() != "processada":
            skipped.append(
                {
                    "tipo": "nota_sem_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "status": nota["status"],
                    "motivo": "Nota ainda nao esta processada; CP nao foi criado automaticamente.",
                }
            )
            continue

        duplicatas, error = _duplicatas_nota(nota, parse_xml)
        if error:
            skipped.append(
                {
                    "tipo": "nota_sem_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "status": nota["status"],
                    "motivo": error,
                }
            )
            continue

        eh_parcelado = len(duplicatas) > 1
        for idx, dup in enumerate(duplicatas, start=1):
            valor = _money(dup.get("valor"))
            actions.append(
                {
                    "tipo": "criar_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "fornecedor_id": nota["fornecedor_id"],
                    "tipo_despesa_id": tipo_produto_revenda_id,
                    "descricao": f"NF-e {nota['numero_nota']} - Parcela {dup.get('numero', idx)}",
                    "valor_original": _money_str(valor),
                    "valor_final": _money_str(valor),
                    "data_emissao": _date_str(nota["data_emissao"]),
                    "data_vencimento": _date_str(dup.get("vencimento")),
                    "status": "pendente",
                    "eh_parcelado": eh_parcelado,
                    "numero_parcela": idx if eh_parcelado else None,
                    "total_parcelas": len(duplicatas) if eh_parcelado else None,
                    "dre_subcategoria_id": None,
                    "nfe_numero": str(nota["numero_nota"]),
                    "documento": str(dup.get("numero") or ""),
                    "afeta_dre": False,
                    "percentual_online": _money_str(nota["percentual_online"]),
                    "percentual_loja": _money_str(nota["percentual_loja"]),
                    "user_id": int(nota["user_id"]),
                    "tenant_id": tenant_id,
                }
            )

    return actions, skipped


def _insert_conta_pagar(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                fornecedor_id, tipo_despesa_id, descricao,
                valor_original, valor_final, valor_pago,
                data_emissao, data_vencimento, status,
                eh_parcelado, numero_parcela, total_parcelas,
                dre_subcategoria_id, nota_entrada_id, nfe_numero, documento,
                afeta_dre,
                percentual_online, percentual_loja, user_id, tenant_id
            )
            VALUES (
                :fornecedor_id, :tipo_despesa_id, :descricao,
                :valor_original, :valor_final, 0,
                :data_emissao, :data_vencimento, :status,
                :eh_parcelado, :numero_parcela, :total_parcelas,
                :dre_subcategoria_id, :nota_id, :nfe_numero, :documento,
                :afeta_dre,
                :percentual_online, :percentual_loja, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        action,
    ).first()
    return int(row[0])


def _apply_cp_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for action in actions:
        conta_id = _insert_conta_pagar(db, action)
        applied.append({**action, "conta_pagar_id": conta_id})
    return applied
