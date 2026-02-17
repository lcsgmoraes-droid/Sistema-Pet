from sqlalchemy.orm import Session
from app.produto_config_fiscal_models import ProdutoConfigFiscal


def aplicar_sugestao_fiscal_produto(
    db: Session,
    tenant_id: int,
    produto_id: int,
    sugestao: dict
):
    """
    Aplica manualmente uma sugestão fiscal ao produto.
    """

    config = (
        db.query(ProdutoConfigFiscal)
        .filter(
            ProdutoConfigFiscal.produto_id == produto_id,
            ProdutoConfigFiscal.tenant_id == tenant_id
        )
        .first()
    )

    if not config:
        config = ProdutoConfigFiscal(
            tenant_id=tenant_id,
            produto_id=produto_id,
            empresa_config_fiscal_id=sugestao.get("empresa_config_fiscal_id"),
            herdado_da_empresa=False
        )
        db.add(config)

    # Aplica campos sugeridos
    config.ncm = sugestao.get("ncm")
    config.cest = sugestao.get("cest")
    config.cst_icms = sugestao.get("cst_icms")
    config.icms_st = sugestao.get("icms_st")

    config.pis_cst = sugestao.get("pis_cst")
    config.cofins_cst = sugestao.get("cofins_cst")

    config.observacao_fiscal = sugestao.get("observacao")
    config.configuracao_sugerida = True

    db.commit()
    db.refresh(config)
    return config
