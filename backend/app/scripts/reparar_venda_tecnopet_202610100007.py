"""Reparo pontual e auditado da venda Tecnopet #202610100007.

Simula por padrao; --apply persiste em uma unica transacao. Nao executa uma
devolucao nem movimenta dinheiro real: remove juntas as duas entradas obsoletas
e a sangria usada para compensa-las, mantendo o mesmo liquido no caixa.

Pode ser executado com ``python -m app.scripts.reparar_venda_tecnopet_202610100007``
ou enviado por stdin ao Python do container existente (sem depender de codigo
novo na imagem). A auditoria guarda todas as colunas das linhas alteradas.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from uuid import UUID

if __package__ in {None, ""} and "__file__" in globals() and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.tenancy.context import tenant_context
from app.utils.tenant_safe_sql import execute_tenant_safe


TENANT_ID = "86219670-d501-4f43-8042-85d78c4de353"
SALE_ID = 1365844
SALE_NUMBER = "202610100007"
CUSTOMER_ID = 16685
CASH_REGISTER_ID = 378
PAYMENT_ID = 260970
PAYMENT_FORM_ID = 74
RECEIPT_ID = 10047
VALID_MOVEMENT_ID = 3609
REMOVED_MOVEMENT_IDS = (3606, 3608, 3613)
REPAIR_KEY = "tecnopet-sale-202610100007-payment-repair-v1"
AUDIT_ACTION = "business.sale.payment_repair"
PAYMENT_REFERENCE = f"PAGAMENTO-{PAYMENT_ID}"
PAYMENT_TOKEN = f"[venda_pagamento:{PAYMENT_ID}]"
REASON = (
    "Reparo autorizado por Lucas em 10/10/2026: excluir entradas duplicadas e "
    "sangria compensatoria juntas, restituir credito de pagamento excluido e "
    "cancelar lancamentos obsoletos da venda #202610100007."
)
CENT = Decimal("0.01")


class RepairStateChanged(RuntimeError):
    """O estado deixou de corresponder ao caso investigado; nenhuma escrita."""


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _json(value: Any) -> str:
    def convert(item: Any) -> str:
        if isinstance(item, Decimal):
            return format(item, "f")
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, UUID):
            return str(item)
        raise TypeError(f"Valor nao serializavel: {type(item).__name__}")

    return json.dumps(value, default=convert, ensure_ascii=False, sort_keys=True)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RepairStateChanged(message)


def _execute(db, sql: str, params: dict | None = None, *, insert: bool = False):
    return execute_tenant_safe(
        db,
        sql,
        params={**(params or {}), "tenant_id": TENANT_ID} if insert else params,
        tenant_id=TENANT_ID,
        require_tenant=not insert,
    )


def _rows(
    db, table: str, where: str, params: dict, *, lock: bool = False
) -> list[dict]:
    # Table names/conditions are constants from this module, never CLI input.
    suffix = (
        " FOR UPDATE" if lock and db.get_bind().dialect.name == "postgresql" else ""
    )
    result = _execute(
        db,
        f"SELECT * FROM {table} WHERE {{tenant_filter}} AND ({where}) ORDER BY id{suffix}",
        params,
    )
    return [dict(row) for row in result.mappings()]


def _one(db, table: str, row_id: int, *, lock: bool = False) -> dict:
    rows = _rows(db, table, "id = :row_id", {"row_id": row_id}, lock=lock)
    _require(len(rows) == 1, f"Registro {table}/{row_id} ausente neste tenant.")
    return rows[0]


def _cash_net(movements: list[dict]) -> Decimal:
    total = Decimal("0")
    for movement in movements:
        value = _money(movement["valor"])
        if movement["tipo"] in {"sangria", "despesa", "devolucao"}:
            total -= value
        elif movement["tipo"] in {"venda", "suprimento"}:
            total += value
        else:
            # The known repair movements never include transferencias. Using
            # the complete caixa only for unchanged-row comparison avoids
            # imposing a sign convention on unrelated movement kinds.
            continue
    return _money(total)


def _marked_note(note: str | None) -> str:
    tokens = re.findall(r"\[venda_pagamento:(\d+)\]", note or "")
    _require(
        not tokens or tokens == [str(PAYMENT_ID)],
        "Vinculo de recebivel conflita com o pagamento valido.",
    )
    return note if tokens else f"{note or ''} {PAYMENT_TOKEN}".strip()


def _without_timestamp(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "updated_at"}


def _capture(db, *, lock: bool) -> dict:
    params = {
        "sale_id": SALE_ID,
        "customer_id": CUSTOMER_ID,
        "caixa_id": CASH_REGISTER_ID,
    }
    return {
        "payments": _rows(
            db, "venda_pagamentos", "venda_id = :sale_id", params, lock=lock
        ),
        "movements": _rows(
            db,
            "movimentacoes_caixa",
            "venda_id = :sale_id OR id = 3613",
            params,
            lock=lock,
        ),
        "receivables": _rows(
            db, "contas_receber", "venda_id = :sale_id", params, lock=lock
        ),
        "receipts": _rows(
            db, "recebimentos", "conta_receber_id = 14870", {}, lock=lock
        ),
        "financial_entries": _rows(
            db,
            "lancamentos_manuais",
            "documento IN ('VENDA-1365844', 'VENDA-1365844-SALDO', 'VENDA-1365844-REALIZADO')",
            params,
            lock=lock,
        ),
        "credit_logs": _rows(
            db, "credito_logs", "cliente_id = :customer_id", params, lock=lock
        ),
        "returns": _rows(
            db, "vendas_devolucoes", "venda_id = :sale_id", params, lock=lock
        ),
        "payment_deletion_audits": _rows(
            db, "audit_logs", "id IN (64287, 64288, 64303)", {}, lock=lock
        ),
        "cash_register_movements": _rows(
            db, "movimentacoes_caixa", "caixa_id = :caixa_id", params, lock=lock
        ),
    }


def _validate(before: dict) -> None:
    sale, caixa, customer = before["sale"], before["cash_register"], before["customer"]
    _require(
        sale["numero_venda"] == SALE_NUMBER and sale["cliente_id"] == CUSTOMER_ID,
        "Numero ou cliente da venda mudou.",
    )
    _require(
        sale["status"] == "finalizada" and _money(sale["total"]) == Decimal("115.00"),
        "A venda deve continuar finalizada com total 115.00.",
    )
    _require(sale["caixa_id"] == CASH_REGISTER_ID, "Caixa da venda mudou.")
    # Removing +230 and its compensating -230 has no effect on a closed
    # register's reconciliation. Every opening/closing field is preserved.
    _require(
        caixa["numero_caixa"] == 9 and caixa["status"] in {"aberto", "fechado"},
        "Estado inesperado do caixa #9.",
    )
    _require(
        _money(customer["credito"]) == Decimal("0.33"),
        "Credito atual da cliente mudou.",
    )
    payments = before["payments"]
    _require(
        len(payments) == 1 and payments[0]["id"] == PAYMENT_ID,
        "Pagamentos da venda mudaram.",
    )
    payment = payments[0]
    _require(
        payment["forma_pagamento"].lower() == "dinheiro"
        and _money(payment["valor"]) == Decimal("115.00")
        and payment["forma_pagamento_id"] == PAYMENT_FORM_ID
        and payment["status"] == "pendente"
        and payment["caixa_id"] == CASH_REGISTER_ID,
        "Pagamento valido nao corresponde ao investigado.",
    )
    movements = {row["id"]: row for row in before["movements"]}
    _require(set(movements) == {3606, 3608, 3609, 3613}, "Movimentos da venda mudaram.")
    for row_id in (3606, 3608, 3609):
        row = movements[row_id]
        _require(
            row["tipo"] == "venda"
            and row["venda_id"] == SALE_ID
            and row["caixa_id"] == CASH_REGISTER_ID
            and row["forma_pagamento"].lower() == "dinheiro"
            and _money(row["valor"]) == Decimal("115.00"),
            f"Entrada {row_id} mudou.",
        )
    sangria = movements[3613]
    description = str(sangria["descricao"] or "").upper()
    _require(
        sangria["tipo"] == "sangria"
        and sangria["venda_id"] is None
        and sangria["caixa_id"] == CASH_REGISTER_ID
        and sangria["forma_pagamento"].lower() == "dinheiro"
        and _money(sangria["valor"]) == Decimal("230.00")
        and "TRIPLICADA" in description
        and "MARINA" in description
        and "NÃO FOI SANGRIA" in description,
        "Sangria compensatoria nao corresponde ao ajuste investigado.",
    )
    _require(
        _cash_net(before["movements"]) == Decimal("115.00"),
        "Liquido original inesperado.",
    )
    _require(
        movements[VALID_MOVEMENT_ID].get("documento") in (None, "", PAYMENT_REFERENCE),
        "Referencia da entrada valida ja esta ocupada; revisar antes de substituir.",
    )
    entries = {row["id"]: row for row in before["financial_entries"]}
    _require(
        set(entries) == {13067, 13068, 13069},
        "Lancamentos financeiros da venda mudaram.",
    )
    for row_id, amount, status, document in (
        (13067, "115.00", "realizado", "VENDA-1365844"),
        (13068, "115.00", "previsto", "VENDA-1365844-SALDO"),
        (13069, "4.90", "realizado", "VENDA-1365844-REALIZADO"),
    ):
        entry = entries[row_id]
        _require(
            _money(entry["valor"]) == Decimal(amount)
            and entry["status"] == status
            and entry["documento"] == document
            and entry["tipo"] == "entrada",
            f"Lancamento financeiro {row_id} mudou.",
        )
    receivables = before["receivables"]
    _require(
        len(receivables) == 1 and receivables[0]["id"] == 14870,
        "Contas a receber mudaram.",
    )
    account = receivables[0]
    _require(
        account["cliente_id"] == CUSTOMER_ID
        and account["status"] == "recebido"
        and all(
            _money(account[field]) == Decimal("115.00")
            for field in ("valor_original", "valor_final", "valor_recebido")
        ),
        "Conta a receber nao corresponde a quitacao final.",
    )
    _marked_note(account.get("observacoes"))
    _require(len(before["receipts"]) == 1, "Baixas da conta a receber mudaram.")
    receipt = before["receipts"][0]
    _require(
        receipt["id"] == RECEIPT_ID
        and _money(receipt["valor_recebido"]) == Decimal("115.00")
        and receipt["forma_pagamento_id"] == PAYMENT_FORM_ID
        and receipt["user_id"] == 74
        and str(receipt["data_recebimento"]) == "2026-10-10",
        "Baixa da conta a receber nao corresponde ao pagamento valido.",
    )
    _marked_note(receipt.get("observacoes"))
    _require(
        not before["returns"], "Ja existe devolucao desta venda; refazer diagnostico."
    )
    # An undocumented credit restoration must never be repeated by this repair.
    _require(
        not any(
            log["referencia_id"] == SALE_ID and log["tipo"] != "uso_venda"
            for log in before["credit_logs"]
        ),
        "Existe outro ajuste de credito vinculado a venda.",
    )
    audits = {row["id"]: row for row in before["payment_deletion_audits"]}
    _require(
        set(audits) == {64287, 64288, 64303},
        "Auditorias originais de exclusao ausentes.",
    )
    for audit_id, payment_id, amount, method in (
        (64287, 260765, "4.90", "Crédito Cliente"),
        (64288, 260964, "115.00", "dinheiro"),
        (64303, 260968, "115.00", "dinheiro"),
    ):
        audit = audits[audit_id]
        details = str(audit["details"] or "")
        _require(
            audit["action"] == "delete"
            and audit["entity_type"] == "venda_pagamentos"
            and audit["entity_id"] == payment_id
            and amount in details
            and method.lower() in details.lower()
            and f"#{SALE_ID}" in details,
            f"Auditoria {audit_id} nao comprova exclusao do pagamento original.",
        )


def repair_sale(db, *, apply: bool = False) -> dict:
    """Owns commit/rollback; call with a fresh session, with no pending work."""
    try:
        with tenant_context(TENANT_ID):
            # Serialize concurrent repairs/payments in the same order used by
            # the payment fix: caixa -> venda -> cliente -> child records.
            caixa = _one(db, "caixas", CASH_REGISTER_ID, lock=apply)
            sale = _one(db, "vendas", SALE_ID, lock=apply)
            marker = _rows(
                db,
                "audit_logs",
                "action = :action AND entity_type = 'sale' AND entity_id = :sale_id",
                {"action": AUDIT_ACTION, "sale_id": SALE_ID},
                lock=apply,
            )
            matching = [
                row
                for row in marker
                if json.loads(row["new_value"] or "{}").get("repair_key") == REPAIR_KEY
            ]
            if matching:
                saved = json.loads(matching[0]["new_value"])
                _require(
                    saved.get("status") == "applied",
                    "Marcador de reparo incompleto; revisar auditoria.",
                )
                db.rollback()
                return {
                    "ok": True,
                    "status": "already_applied",
                    "dry_run": not apply,
                    "repair_key": REPAIR_KEY,
                    "audit_id": matching[0]["id"],
                    **saved["summary"],
                }
            customer = _one(db, "clientes", CUSTOMER_ID, lock=apply)
            before = {
                "sale": sale,
                "cash_register": caixa,
                "customer": customer,
                **_capture(db, lock=apply),
            }
            _validate(before)
            summary = {
                "sale_number": SALE_NUMBER,
                "cash_net_before": "115.00",
                "cash_net_after": "115.00",
                "cash_delta": "0.00",
                "credit_before": "0.33",
                "credit_restored": "4.90",
                "credit_after": "5.23",
                "removed_movement_ids": list(REMOVED_MOVEMENT_IDS),
                "preserved_movement_id": VALID_MOVEMENT_ID,
                "cancelled_financial_entry_ids": [13068, 13069],
                "linked_payment_id": PAYMENT_ID,
                "linked_receipt_id": before["receipts"][0]["id"],
            }
            if not apply:
                db.rollback()
                return {
                    "ok": True,
                    "status": "planned",
                    "dry_run": True,
                    "repair_key": REPAIR_KEY,
                    **summary,
                }

            for row_id in REMOVED_MOVEMENT_IDS:
                result = _execute(
                    db,
                    "DELETE FROM movimentacoes_caixa WHERE {tenant_filter} AND id = :row_id",
                    {"row_id": row_id},
                )
                _require(result.rowcount == 1, f"Movimento {row_id} nao foi removido.")
            result = _execute(
                db,
                "UPDATE clientes SET credito = :credit, updated_at = CURRENT_TIMESTAMP "
                "WHERE {tenant_filter} AND id = :customer_id AND credito = :old_credit",
                {"credit": "5.23", "old_credit": "0.33", "customer_id": CUSTOMER_ID},
            )
            _require(result.rowcount == 1, "Credito mudou durante o reparo.")
            credit_id = _execute(
                db,
                "INSERT INTO credito_logs (tenant_id, cliente_id, tipo, valor, saldo_anterior, saldo_atual, "
                "motivo, referencia_id, usuario_nome) VALUES (:tenant_id, :customer_id, 'estorno_venda', "
                ":value, :old_credit, :credit, :reason, :sale_id, :actor) RETURNING id",
                {
                    "customer_id": CUSTOMER_ID,
                    "value": "4.90",
                    "old_credit": "0.33",
                    "credit": "5.23",
                    "reason": REASON,
                    "sale_id": SALE_ID,
                    "actor": "Reparo autorizado por Lucas",
                },
                insert=True,
            ).scalar_one()
            for row_id in (13068, 13069):
                original = next(
                    row for row in before["financial_entries"] if row["id"] == row_id
                )
                note = f"{original.get('observacoes') or ''}\n{REASON}".strip()
                result = _execute(
                    db,
                    "UPDATE lancamentos_manuais SET status = 'cancelado', observacoes = :note, "
                    "updated_at = CURRENT_TIMESTAMP WHERE {tenant_filter} AND id = :row_id",
                    {"row_id": row_id, "note": note},
                )
                _require(
                    result.rowcount == 1, f"Lancamento {row_id} nao foi cancelado."
                )
            _execute(
                db,
                "UPDATE movimentacoes_caixa SET documento = :reference, updated_at = CURRENT_TIMESTAMP "
                "WHERE {tenant_filter} AND id = :row_id",
                {"row_id": VALID_MOVEMENT_ID, "reference": PAYMENT_REFERENCE},
            )
            marked_account = _marked_note(before["receivables"][0].get("observacoes"))
            _execute(
                db,
                "UPDATE contas_receber SET observacoes = :note, updated_at = CURRENT_TIMESTAMP "
                "WHERE {tenant_filter} AND id = 14870",
                {"note": marked_account},
            )
            marked_receipt = _marked_note(before["receipts"][0].get("observacoes"))
            _execute(
                db,
                "UPDATE recebimentos SET observacoes = :note WHERE {tenant_filter} AND id = :receipt_id",
                {"note": marked_receipt, "receipt_id": before["receipts"][0]["id"]},
            )
            after = {
                "sale": _one(db, "vendas", SALE_ID),
                "cash_register": _one(db, "caixas", CASH_REGISTER_ID),
                "customer": _one(db, "clientes", CUSTOMER_ID),
                **_capture(db, lock=False),
            }
            _require(
                _cash_net(after["movements"]) == _cash_net(before["movements"]),
                "Liquido do caso mudou.",
            )
            expected_movements = [
                {**row, "documento": PAYMENT_REFERENCE}
                if row["id"] == VALID_MOVEMENT_ID
                else row
                for row in before["cash_register_movements"]
                if row["id"] not in REMOVED_MOVEMENT_IDS
            ]

            def normalize(rows):
                return [
                    _without_timestamp(row) if row["id"] == VALID_MOVEMENT_ID else row
                    for row in rows
                ]

            _require(
                normalize(after["cash_register_movements"])
                == normalize(expected_movements),
                "Outros movimentos do caixa mudaram.",
            )
            expected_account = {
                **before["receivables"][0],
                "observacoes": marked_account,
            }
            expected_receipt = {**before["receipts"][0], "observacoes": marked_receipt}
            _require(
                len(after["receivables"]) == 1
                and _without_timestamp(after["receivables"][0])
                == _without_timestamp(expected_account)
                and after["receipts"] == [expected_receipt],
                "Valores dos recebiveis mudaram.",
            )
            _require(
                _money(after["customer"]["credito"]) == Decimal("5.23"),
                "Credito nao foi restituido.",
            )
            _require(
                after["cash_register"] == caixa
                and after["sale"] == sale
                and after["payments"] == before["payments"],
                "Venda, pagamento, conta a receber ou fechamento do caixa mudaram.",
            )
            audit_id = _execute(
                db,
                "INSERT INTO audit_logs (tenant_id, user_id, action, entity_type, entity_id, old_value, "
                "new_value, details) VALUES (:tenant_id, NULL, :action, 'sale', :sale_id, :old_value, :new_value, :details) RETURNING id",
                {
                    "action": AUDIT_ACTION,
                    "sale_id": SALE_ID,
                    "old_value": _json(before),
                    "new_value": _json(
                        {
                            "repair_key": REPAIR_KEY,
                            "status": "applied",
                            "summary": summary,
                            "credit_log_id": credit_id,
                            "after": after,
                        }
                    ),
                    "details": _json(
                        {"repair_key": REPAIR_KEY, "authorization": REASON}
                    ),
                },
                insert=True,
            ).scalar_one()
            # The audit insert above is part of this transaction (commit=False
            # semantics). An audit failure rolls back cash, credit and finance.
            db.commit()
            return {
                "ok": True,
                "status": "applied",
                "dry_run": False,
                "repair_key": REPAIR_KEY,
                "audit_id": audit_id,
                "credit_log_id": credit_id,
                **summary,
            }
    except Exception:
        db.rollback()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica o reparo; sem esta flag somente simula.",
    )
    args = parser.parse_args(argv)
    from app.db import SessionLocal

    with SessionLocal() as db:
        try:
            result = repair_sale(db, apply=args.apply)
        except Exception as exc:
            print(
                _json({"ok": False, "dry_run": not args.apply, "error": str(exc)}),
                file=sys.stderr,
            )
            return 1
        print(_json(result))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
