"""Projeção dos documentos externos na Central NF-e, sem Venda fictícia."""

from decimal import Decimal
from app.ecommerceai_fiscal.models import ExternalFiscalOrder
from app.services.nfe_cache_service import upsert_nota_cache

SOURCE = "ecommerceai_fiscal"


def sync_note(db, row):
    if not row.numero or not row.chave:
        return
    source = row.source
    recipient = source.get("recipient") or {}
    status = {
        "authorized": "autorizada",
        "canceled": "cancelada",
        "rejected": "rejeitada",
    }.get(row.status, "processando")
    note = {
        "id": f"fiscal-externa-{row.id}",
        "numero": row.numero,
        "serie": row.payload["serie"],
        "tipo": "nfe",
        "tipo_codigo": 0,
        "modelo": 55,
        "chave": row.chave,
        "status": status,
        "data_emissao": row.submitted_at.isoformat() if row.submitted_at else None,
        "valor": float(
            Decimal(
                (row.discount_audit or {}).get(
                    "effective_invoice_total", source["totals"]["invoice_total"]
                )
            )
        ),
        "cliente": {
            "nome": recipient.get("name"),
            "cpf_cnpj": recipient.get("document"),
        },
        "canal": "amazon",
        "canal_label": "Amazon",
        "numero_pedido_loja": row.external_order_id,
        "provedor": "intnfe",
        "origem": "fiscal_externa",
        "fiscal_order_id": row.id,
    }
    upsert_nota_cache(
        db,
        row.tenant_id,
        note,
        source=SOURCE,
        resumo_payload={"fiscal_order_id": row.id},
        substituir_origem_remota=True,
    )


def sync_notes(db, tenant_id, *, desde=None):
    query = db.query(ExternalFiscalOrder).filter(
        ExternalFiscalOrder.tenant_id == tenant_id,
        ExternalFiscalOrder.numero.isnot(None),
    )
    if desde:
        query = query.filter(ExternalFiscalOrder.updated_at >= desde)
    for row in query.all():
        sync_note(db, row)
