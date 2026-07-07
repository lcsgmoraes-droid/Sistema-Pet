"""Helpers compartilhados dos reparos de consistencia financeira."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value)
    return date.fromisoformat(text_value[:10])


def _date_str(value: Any) -> str | None:
    if value is None:
        return None
    return _as_date(value).isoformat()


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _resolve_forma_pagamento(
    db: Session, *, tenant_id: str, forma_pagamento: str
) -> dict[str, Any] | None:
    return _one(
        db,
        """
        SELECT id, nome, tipo, prazo_dias, prazo_recebimento
        FROM formas_pagamento
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND (
                lower(nome) = lower(:forma_pagamento)
             OR lower(tipo) = lower(:forma_pagamento)
          )
        ORDER BY
            CASE WHEN lower(nome) = lower(:forma_pagamento) THEN 0 ELSE 1 END,
            id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "forma_pagamento": forma_pagamento},
    )


def _resolve_dre_subcategoria_id(db: Session, *, tenant_id: str) -> int:
    row = _one(
        db,
        """
        SELECT dre_subcategoria_id
        FROM contas_receber
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND dre_subcategoria_id IS NOT NULL
        GROUP BY dre_subcategoria_id
        ORDER BY COUNT(*) DESC, dre_subcategoria_id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    return int(row["dre_subcategoria_id"]) if row else 1


def _resolve_tipo_produto_revenda_id(db: Session, *, tenant_id: str) -> int | None:
    row = _one(
        db,
        """
        SELECT id
        FROM tipo_despesas
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND lower(nome) IN (
                lower('Produto para Revenda'),
                lower('Fornecedor de Produto para Revenda')
          )
        ORDER BY id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if row:
        return int(row["id"])

    row = _one(
        db,
        """
        SELECT id
        FROM tipo_despesas
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND lower(nome) LIKE '%produto%'
          AND lower(nome) LIKE '%revenda%'
        ORDER BY nome ASC, id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    return int(row["id"]) if row else None


def _prazo_forma(forma: dict[str, Any] | None) -> int:
    if not forma:
        return 0
    return int(forma.get("prazo_dias") or forma.get("prazo_recebimento") or 0)


def _is_recebimento_imediato(
    *, forma_nome: str, forma: dict[str, Any] | None, numero_parcelas: int
) -> bool:
    if numero_parcelas > 1:
        return False
    tipo = str((forma or {}).get("tipo") or forma_nome or "").lower()
    nome = str((forma or {}).get("nome") or forma_nome or "").lower()
    imediatos = {"pix", "dinheiro", "debito", "dÃ©bito", "cartao_debito"}
    if tipo in imediatos or nome in imediatos:
        return True
    return forma is not None and _prazo_forma(forma) == 0
