from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_tenant
from app.db import get_session as get_db
from app.produtos_models import Produto
from app.services.fiscal_config_service import (
    obter_ou_criar_config_fiscal_empresa_padrao,
)
from app.services.pdv_fiscal_calculo import calcular_fiscal_item_pdv
from app.services.pdv_fiscal_resolver import resolver_fiscal_item_pdv

router = APIRouter(prefix="/pdv/fiscal", tags=["PDV Fiscal"])


@router.post("/calcular")
def calcular_fiscal_pdv_item(
    payload: dict,
    db: Session = Depends(get_db),
    tenant_id=Depends(get_current_tenant),
):
    """
    Calcula o fiscal de um item do PDV.
    Tenants novos recebem uma configuracao fiscal padrao automaticamente.
    """
    preco_unitario = Decimal(str(payload["preco_unitario"]))
    quantidade = Decimal(str(payload["quantidade"]))
    produto_id = payload.get("produto_id")
    variacao_id = payload.get("variacao_id")
    is_kit = payload.get("is_kit")

    if not produto_id:
        return {
            "origem_fiscal": "sem_produto",
            "base_calculo": (preco_unitario * quantidade).quantize(Decimal("0.01")),
            "icms": Decimal("0.00"),
            "icms_st": Decimal("0.00"),
            "pis": Decimal("0.00"),
            "cofins": Decimal("0.00"),
            "total_impostos": Decimal("0.00"),
        }

    if is_kit is None:
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        if produto:
            is_kit = produto.tipo_produto == "KIT"

    fiscal_resolvido = resolver_fiscal_item_pdv(
        db=db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        variacao_id=variacao_id,
        is_kit=is_kit,
    )

    empresa_fiscal = obter_ou_criar_config_fiscal_empresa_padrao(
        db=db,
        tenant_id=tenant_id,
        commit=True,
    )

    aliquotas = {
        "icms_aliquota_interna": empresa_fiscal.icms_aliquota_interna,
        "pis_aliquota": empresa_fiscal.pis_aliquota or 0,
        "cofins_aliquota": empresa_fiscal.cofins_aliquota or 0,
    }

    calculo = calcular_fiscal_item_pdv(
        preco_unitario=preco_unitario,
        quantidade=quantidade,
        fiscal=fiscal_resolvido,
        aliquotas_empresa=aliquotas,
    )

    return {
        "origem_fiscal": fiscal_resolvido["origem"],
        **calculo,
    }
