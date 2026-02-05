from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db import get_session as get_db
from app.auth.dependencies import get_current_tenant

from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.produtos_models import Produto
from app.services.pdv_fiscal_resolver import resolver_fiscal_item_pdv
from app.services.pdv_fiscal_calculo import calcular_fiscal_item_pdv

router = APIRouter(prefix="/pdv/fiscal", tags=["PDV Fiscal"])


@router.post("/calcular")
def calcular_fiscal_pdv_item(
    payload: dict,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Calcula o fiscal de um item do PDV.
    """

    produto_id = payload["produto_id"]
    variacao_id = payload.get("variacao_id")
    preco_unitario = Decimal(str(payload["preco_unitario"]))
    quantidade = Decimal(str(payload["quantidade"]))
    is_kit = payload.get("is_kit")

    # Fallback: detectar automaticamente se é KIT
    if is_kit is None:
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        if produto:
            is_kit = produto.tipo_produto == "KIT"

    # 1. Resolve fiscal
    fiscal_resolvido = resolver_fiscal_item_pdv(
        db=db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        variacao_id=variacao_id,
        is_kit=is_kit
    )

    # 2. Busca alíquotas da empresa
    empresa_fiscal = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if not empresa_fiscal:
        raise Exception("Configuração fiscal da empresa não encontrada")

    aliquotas = {
        "icms_aliquota_interna": empresa_fiscal.icms_aliquota_interna,
        "pis_aliquota": empresa_fiscal.pis_aliquota or 0,
        "cofins_aliquota": empresa_fiscal.cofins_aliquota or 0
    }

    # 3. Calcula impostos
    calculo = calcular_fiscal_item_pdv(
        preco_unitario=preco_unitario,
        quantidade=quantidade,
        fiscal=fiscal_resolvido,
        aliquotas_empresa=aliquotas
    )

    return {
        "origem_fiscal": fiscal_resolvido["origem"],
        **calculo
    }
