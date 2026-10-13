"""Metadados dos cupons emitidos usados ao editar uma venda."""

import re

from sqlalchemy import or_

from app.campaigns.models import Coupon


def carregar_cupons_detalhes_venda(db, venda, tenant_id) -> list[dict]:
    if str(venda.tenant_id) != str(tenant_id):
        return []
    codigos = list(
        dict.fromkeys(
            codigo.strip().upper()
            for codigo in re.split(r"[,;|]+", str(venda.cupom_code or ""))
            if codigo.strip()
        )
    )
    if not codigos:
        return []
    # Os parametros pertencem ao cupom ja emitido, nao a configuracao atual
    # da campanha. Cupons consumidos/estornados continuam legiveis na venda.
    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.code.in_(codigos),
            or_(Coupon.customer_id.is_(None), Coupon.customer_id == venda.cliente_id),
        )
        .all()
    )
    por_codigo = {cupom.code: cupom for cupom in cupons}
    return [
        {
            "code": codigo,
            "coupon_type": getattr(
                por_codigo[codigo].coupon_type, "value", por_codigo[codigo].coupon_type
            ),
            "discount_value": float(por_codigo[codigo].discount_value)
            if por_codigo[codigo].discount_value is not None
            else None,
            "discount_percent": float(por_codigo[codigo].discount_percent)
            if por_codigo[codigo].discount_percent is not None
            else None,
        }
        for codigo in codigos
        if codigo in por_codigo
    ]
