from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db import get_session as get_db
from app.auth.dependencies import get_current_tenant

from app.produtos_models import Produto
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.kit_config_fiscal_models import KitConfigFiscal

router = APIRouter(prefix="/produtos", tags=["Fiscal Produto V2"])


@router.get("/{produto_id}/fiscal")
def get_fiscal_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Retorna fiscal do produto.
    Prioridade:
    1. produto_config_fiscal (V2)
    2. campos fiscais legados da tabela produtos
    """
    try:
        fiscal_v2 = (
            db.query(ProdutoConfigFiscal)
            .filter(
                ProdutoConfigFiscal.tenant_id == tenant_id,
                ProdutoConfigFiscal.produto_id == produto_id,
            )
            .first()
        )

        if fiscal_v2:
            return {
                "origem": "produto_v2",
                "herdado_da_empresa": fiscal_v2.herdado_da_empresa or False,
                "origem_mercadoria": fiscal_v2.origem_mercadoria,
                "ncm": fiscal_v2.ncm,
                "cest": fiscal_v2.cest,
                "cfop_venda": fiscal_v2.cfop_venda,
                "cst_icms": fiscal_v2.cst_icms,
                "icms_aliquota": float(fiscal_v2.icms_aliquota) if fiscal_v2.icms_aliquota is not None else None,
                "icms_st": fiscal_v2.icms_st or False,
                "pis_aliquota": float(fiscal_v2.pis_aliquota) if fiscal_v2.pis_aliquota is not None else None,
                "cofins_aliquota": float(fiscal_v2.cofins_aliquota) if fiscal_v2.cofins_aliquota is not None else None,
            }

        produto = (
            db.query(Produto)
            .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
            .first()
        )

        if not produto:
            return {
                "origem": "produto_nao_encontrado",
                "herdado_da_empresa": False,
                "origem_mercadoria": None,
                "ncm": None,
                "cest": None,
                "cfop_venda": None,
                "cst_icms": None,
                "icms_aliquota": None,
                "icms_st": False,
                "pis_aliquota": None,
                "cofins_aliquota": None,
            }

        return {
            "origem": "produto_legado",
            "herdado_da_empresa": False,
            "origem_mercadoria": getattr(produto, "origem", None),
            "ncm": getattr(produto, "ncm", None),
            "cest": getattr(produto, "cest", None),
            "cfop_venda": getattr(produto, "cfop", None),
            "cst_icms": None,
            "icms_aliquota": float(getattr(produto, "aliquota_icms", 0) or 0) if getattr(produto, "aliquota_icms", None) is not None else None,
            "icms_st": False,
            "pis_aliquota": float(getattr(produto, "aliquota_pis", 0) or 0) if getattr(produto, "aliquota_pis", None) is not None else None,
            "cofins_aliquota": float(getattr(produto, "aliquota_cofins", 0) or 0) if getattr(produto, "aliquota_cofins", None) is not None else None,
        }
    
    except Exception as e:
        # Log do erro e retorno de estrutura vazia ao invés de 500
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao buscar fiscal do produto {produto_id}: {str(e)}")
        
        return {
            "origem": "erro",
            "herdado_da_empresa": False,
            "origem_mercadoria": None,
            "ncm": None,
            "cest": None,
            "cfop_venda": None,
            "cst_icms": None,
            "icms_aliquota": None,
            "icms_st": False,
            "pis_aliquota": None,
            "cofins_aliquota": None,
        }


@router.get("/{produto_id}/kit/fiscal")
def get_fiscal_kit(
    produto_id: int,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Retorna fiscal do KIT.
    Prioridade:
    1. kit_config_fiscal (V2)
    2. fallback para fiscal do produto (se não existir config de kit)
    """
    try:
        # Verificar se é KIT
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.tenant_id == tenant_id,
                Produto.tipo_produto == "KIT"
            )
            .first()
        )

        if not produto:
            raise HTTPException(status_code=404, detail="Kit não encontrado")

        kit_fiscal_v2 = (
            db.query(KitConfigFiscal)
            .filter(
                KitConfigFiscal.tenant_id == tenant_id,
                KitConfigFiscal.produto_kit_id == produto_id,
            )
            .first()
        )

        if kit_fiscal_v2:
            return {
                "origem": "kit_v2",
                "herdado_da_empresa": kit_fiscal_v2.herdado_da_empresa or False,
                "origem_mercadoria": kit_fiscal_v2.origem_mercadoria,
                "ncm": kit_fiscal_v2.ncm,
                "cest": kit_fiscal_v2.cest,
                "cfop": kit_fiscal_v2.cfop,
                "cst_icms": kit_fiscal_v2.cst_icms,
                "icms_aliquota": float(kit_fiscal_v2.icms_aliquota) if kit_fiscal_v2.icms_aliquota is not None else None,
                "icms_st": kit_fiscal_v2.icms_st or False,
                "pis_aliquota": float(kit_fiscal_v2.pis_aliquota) if kit_fiscal_v2.pis_aliquota is not None else None,
                "cofins_aliquota": float(kit_fiscal_v2.cofins_aliquota) if kit_fiscal_v2.cofins_aliquota is not None else None,
            }

        # Fallback: retornar fiscal do produto
        return get_fiscal_produto(produto_id, db, tenant_id)
    
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao buscar fiscal do kit {produto_id}: {str(e)}")
        
        return {
            "origem": "erro",
            "herdado_da_empresa": False,
            "origem_mercadoria": None,
            "ncm": None,
            "cest": None,
            "cfop": None,
            "cst_icms": None,
            "icms_aliquota": None,
            "icms_st": False,
            "pis_aliquota": None,
            "cofins_aliquota": None,
        }


@router.put("/{produto_id}/fiscal")
def put_fiscal_produto(
    produto_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Salva configuração fiscal V2 do produto.
    Sempre grava em produto_config_fiscal.
    """
    fiscal = (
        db.query(ProdutoConfigFiscal)
        .filter(
            ProdutoConfigFiscal.tenant_id == tenant_id,
            ProdutoConfigFiscal.produto_id == produto_id,
        )
        .first()
    )

    if not fiscal:
        fiscal = ProdutoConfigFiscal(
            tenant_id=tenant_id,
            produto_id=produto_id,
            herdado_da_empresa=False,
        )
        db.add(fiscal)

    # Campos fiscais
    fiscal.origem_mercadoria = payload.get("origem_mercadoria")
    fiscal.ncm = payload.get("ncm")
    fiscal.cest = payload.get("cest")
    fiscal.cfop_venda = payload.get("cfop")

    fiscal.cst_icms = payload.get("cst_icms")
    fiscal.icms_aliquota = payload.get("icms_aliquota")
    fiscal.icms_st = payload.get("icms_st")

    fiscal.pis_aliquota = payload.get("pis_aliquota")
    fiscal.cofins_aliquota = payload.get("cofins_aliquota")

    fiscal.herdado_da_empresa = False

    db.commit()
    db.refresh(fiscal)

    return {
        "status": "ok",
        "origem": "produto_v2",
        "produto_id": produto_id,
    }


@router.put("/{produto_id}/kit/fiscal")
def put_fiscal_kit(
    produto_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Salva configuração fiscal V2 do KIT.
    Só permitido para produtos do tipo KIT.
    """
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    if not produto or produto.tipo_produto != "KIT":
        return {
            "error": "Produto informado não é um KIT"
        }

    fiscal = (
        db.query(KitConfigFiscal)
        .filter(
            KitConfigFiscal.tenant_id == tenant_id,
            KitConfigFiscal.produto_kit_id == produto_id,
        )
        .first()
    )

    if not fiscal:
        fiscal = KitConfigFiscal(
            tenant_id=tenant_id,
            produto_kit_id=produto_id,
            herdado_da_empresa=False,
        )
        db.add(fiscal)

    # Campos fiscais
    fiscal.origem_mercadoria = payload.get("origem_mercadoria")
    fiscal.ncm = payload.get("ncm")
    fiscal.cest = payload.get("cest")
    fiscal.cfop = payload.get("cfop")

    fiscal.cst_icms = payload.get("cst_icms")
    fiscal.icms_aliquota = payload.get("icms_aliquota")
    fiscal.icms_st = payload.get("icms_st")

    fiscal.pis_aliquota = payload.get("pis_aliquota")
    fiscal.cofins_aliquota = payload.get("cofins_aliquota")

    fiscal.herdado_da_empresa = False

    db.commit()
    db.refresh(fiscal)

    return {
        "status": "ok",
        "origem": "kit_v2",
        "produto_id": produto_id,
    }
