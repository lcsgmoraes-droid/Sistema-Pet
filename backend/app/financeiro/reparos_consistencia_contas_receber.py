"""Reparos de contas a receber ausentes."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.contas_receber_service import ContasReceberService
from app.financeiro.reparos_consistencia_common import (
    _as_date,
    _date_str,
    _is_recebimento_imediato,
    _money,
    _money_str,
    _prazo_forma,
    _resolve_dre_subcategoria_id,
    _resolve_forma_pagamento,
    _rows,
)


def _fetch_vendas_sem_contas_receber(
    db: Session, params: dict[str, Any]
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            v.id AS venda_id,
            v.numero_venda AS numero_venda,
            v.cliente_id AS cliente_id,
            v.user_id AS user_id,
            v.data_venda AS data_venda,
            v.total AS total_venda,
            COALESCE(v.canal, 'loja_fisica') AS canal
        FROM vendas v
        WHERE CAST(v.tenant_id AS TEXT) = :tenant_id
          AND v.data_venda >= :data_inicio
          AND v.data_venda < :data_fim
          AND v.status = 'finalizada'
          AND NOT EXISTS (
              SELECT 1
              FROM contas_receber cr
              WHERE CAST(cr.tenant_id AS TEXT) = CAST(v.tenant_id AS TEXT)
                AND cr.venda_id = v.id
                AND COALESCE(cr.status, '') NOT IN ('cancelado', 'cancelada')
          )
        ORDER BY v.data_venda ASC, v.id ASC
        """,
        params,
    )


def _fetch_pagamentos_venda(
    db: Session, *, tenant_id: str, venda_id: int
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            id AS venda_pagamento_id,
            forma_pagamento,
            valor,
            COALESCE(numero_parcelas, 1) AS numero_parcelas,
            status,
            data_pagamento
        FROM venda_pagamentos
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND venda_id = :venda_id
        ORDER BY id ASC
        """,
        {"tenant_id": tenant_id, "venda_id": venda_id},
    )


def _skip_venda_sem_pagamento(venda: dict[str, Any]) -> dict[str, Any]:
    return {
        "tipo": "venda_sem_pagamento",
        "venda_id": int(venda["venda_id"]),
        "numero_venda": venda["numero_venda"],
        "motivo": "Venda finalizada sem venda_pagamentos para reconstruir CR.",
    }


def _cr_parcela_state(
    *,
    numero_parcelas: int,
    idx: int,
    pagamento_date: date,
    prazo: int,
    recebido: bool,
    valor_parcela: Decimal,
) -> tuple[date, str, Decimal, date | None]:
    if numero_parcelas > 1:
        return (
            pagamento_date + timedelta(days=30 * idx),
            "pendente",
            Decimal("0.00"),
            None,
        )
    if recebido:
        return pagamento_date, "recebido", valor_parcela, pagamento_date
    return pagamento_date + timedelta(days=prazo), "pendente", Decimal("0.00"), None


def _cr_descricao(venda: dict[str, Any], forma_nome: str, idx: int, total: int) -> str:
    if total == 1:
        return f"Venda {venda['numero_venda']} - {forma_nome}"
    return f"Venda {venda['numero_venda']} - Parcela {idx}/{total}"


def _build_cr_action(
    *,
    venda: dict[str, Any],
    tenant_id: str,
    forma: dict[str, Any] | None,
    forma_nome: str,
    dre_subcategoria_id: int,
    numero_parcelas: int,
    idx: int,
    valor_parcela: Decimal,
    vencimento: date,
    status: str,
    valor_recebido: Decimal,
    data_recebimento: date | None,
) -> dict[str, Any]:
    return {
        "tipo": "criar_conta_receber",
        "venda_id": int(venda["venda_id"]),
        "numero_venda": venda["numero_venda"],
        "cliente_id": venda["cliente_id"],
        "forma_pagamento_id": int(forma["id"]) if forma else None,
        "dre_subcategoria_id": dre_subcategoria_id,
        "canal": venda["canal"] or "loja_fisica",
        "valor_original": _money_str(valor_parcela),
        "valor_recebido": _money_str(valor_recebido),
        "valor_final": _money_str(valor_parcela),
        "data_emissao": _as_date(venda["data_venda"]).isoformat(),
        "data_vencimento": vencimento.isoformat(),
        "data_recebimento": _date_str(data_recebimento),
        "status": status,
        "eh_parcelado": numero_parcelas > 1,
        "numero_parcela": idx if numero_parcelas > 1 else None,
        "total_parcelas": numero_parcelas if numero_parcelas > 1 else None,
        "documento": f"VENDA-{venda['venda_id']}",
        "descricao": _cr_descricao(venda, forma_nome, idx, numero_parcelas),
        "observacoes": (
            "Reparo financeiro historico: CR reconstruido a partir de venda_pagamentos."
        ),
        "user_id": int(venda["user_id"]),
        "tenant_id": tenant_id,
    }


def _build_cr_actions_for_pagamento(
    db: Session,
    *,
    tenant_id: str,
    venda: dict[str, Any],
    pagamento: dict[str, Any],
    dre_subcategoria_id: int,
) -> list[dict[str, Any]]:
    forma_nome = str(pagamento["forma_pagamento"])
    forma = _resolve_forma_pagamento(db, tenant_id=tenant_id, forma_pagamento=forma_nome)
    numero_parcelas = max(int(pagamento["numero_parcelas"] or 1), 1)
    valores = ContasReceberService._distribuir_valor_parcelas(
        _money(pagamento["valor"]), numero_parcelas
    )
    pagamento_date = _as_date(pagamento["data_pagamento"] or venda["data_venda"])
    prazo = _prazo_forma(forma)
    recebido = _is_recebimento_imediato(
        forma_nome=forma_nome,
        forma=forma,
        numero_parcelas=numero_parcelas,
    )

    actions: list[dict[str, Any]] = []
    for idx, valor_parcela in enumerate(valores, start=1):
        vencimento, status, valor_recebido, data_recebimento = _cr_parcela_state(
            numero_parcelas=numero_parcelas,
            idx=idx,
            pagamento_date=pagamento_date,
            prazo=prazo,
            recebido=recebido,
            valor_parcela=valor_parcela,
        )
        actions.append(
            _build_cr_action(
                venda=venda,
                tenant_id=tenant_id,
                forma=forma,
                forma_nome=forma_nome,
                dre_subcategoria_id=dre_subcategoria_id,
                numero_parcelas=numero_parcelas,
                idx=idx,
                valor_parcela=valor_parcela,
                vencimento=vencimento,
                status=status,
                valor_recebido=valor_recebido,
                data_recebimento=data_recebimento,
            )
        )
    return actions


def _build_cr_missing_actions(
    db: Session, *, tenant_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    dre_subcategoria_id = _resolve_dre_subcategoria_id(db, tenant_id=tenant_id)

    for venda in _fetch_vendas_sem_contas_receber(db, params):
        pagamentos = _fetch_pagamentos_venda(
            db, tenant_id=tenant_id, venda_id=int(venda["venda_id"])
        )
        if not pagamentos:
            skipped.append(_skip_venda_sem_pagamento(venda))
            continue

        for pagamento in pagamentos:
            actions.extend(
                _build_cr_actions_for_pagamento(
                    db,
                    tenant_id=tenant_id,
                    venda=venda,
                    pagamento=pagamento,
                    dre_subcategoria_id=dre_subcategoria_id,
                )
            )

    return actions, skipped


def _insert_conta_receber(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO contas_receber (
                descricao, cliente_id, categoria_id, forma_pagamento_id,
                dre_subcategoria_id, canal, valor_original, valor_recebido,
                valor_desconto, valor_juros, valor_multa, valor_final,
                data_emissao, data_vencimento, data_recebimento, status,
                conciliado, eh_parcelado, numero_parcela, total_parcelas, venda_id,
                documento, observacoes, user_id, tenant_id
            )
            VALUES (
                :descricao, :cliente_id, NULL, :forma_pagamento_id,
                :dre_subcategoria_id, :canal, :valor_original, :valor_recebido,
                0, 0, 0, :valor_final,
                :data_emissao, :data_vencimento, :data_recebimento, :status,
                false, :eh_parcelado, :numero_parcela, :total_parcelas, :venda_id,
                :documento, :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        action,
    ).first()
    return int(row[0])


def _insert_recebimento(
    db: Session, action: dict[str, Any], *, conta_receber_id: int
) -> int | None:
    if action["status"] != "recebido":
        return None

    row = db.execute(
        text(
            """
            INSERT INTO recebimentos (
                conta_receber_id, forma_pagamento_id, valor_recebido,
                data_recebimento, observacoes, user_id, tenant_id
            )
            VALUES (
                :conta_receber_id, :forma_pagamento_id, :valor_recebido,
                :data_recebimento, :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        {
            "conta_receber_id": conta_receber_id,
            "forma_pagamento_id": action["forma_pagamento_id"],
            "valor_recebido": action["valor_recebido"],
            "data_recebimento": action["data_recebimento"],
            "observacoes": (
                "Reparo financeiro historico: recebimento reconstruido "
                "a partir de venda_pagamentos."
            ),
            "user_id": action["user_id"],
            "tenant_id": action["tenant_id"],
        },
    ).first()
    return int(row[0])


def _apply_cr_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for action in actions:
        conta_id = _insert_conta_receber(db, action)
        recebimento_id = _insert_recebimento(db, action, conta_receber_id=conta_id)
        applied.append(
            {
                **action,
                "conta_receber_id": conta_id,
                "recebimento_id": recebimento_id,
            }
        )
    return applied
