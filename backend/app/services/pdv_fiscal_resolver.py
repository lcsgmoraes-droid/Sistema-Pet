from sqlalchemy.orm import Session

from app.kit_config_fiscal_models import KitConfigFiscal
from app.variacao_config_fiscal_models import VariacaoConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.empresa_config_fiscal_models import EmpresaConfigFiscal


def resolver_fiscal_item_pdv(
    db: Session,
    tenant_id: int,
    produto_id: int,
    variacao_id: int | None = None,
    is_kit: bool = False
):
    """
    Resolve a configuração fiscal final de um item no PDV.

    Prioridade:
    1. KIT
    2. Variação
    3. Produto
    4. Empresa
    """

    # 1️⃣ KIT
    if is_kit:
        kit_fiscal = (
            db.query(KitConfigFiscal)
            .filter(
                KitConfigFiscal.tenant_id == tenant_id,
                KitConfigFiscal.produto_kit_id == produto_id
            )
            .first()
        )

        if kit_fiscal:
            return {
                "origem": "kit",
                "ncm": kit_fiscal.ncm,
                "cest": kit_fiscal.cest,
                "cst_icms": kit_fiscal.cst_icms,
                "icms_st": kit_fiscal.icms_st
            }

    # 2️⃣ Variação
    if variacao_id:
        variacao_fiscal = (
            db.query(VariacaoConfigFiscal)
            .filter(
                VariacaoConfigFiscal.tenant_id == tenant_id,
                VariacaoConfigFiscal.variacao_id == variacao_id
            )
            .first()
        )

        if variacao_fiscal:
            return {
                "origem": "variacao",
                "ncm": variacao_fiscal.ncm,
                "cest": variacao_fiscal.cest,
                "cst_icms": variacao_fiscal.cst_icms,
                "icms_st": variacao_fiscal.icms_st,
                "pis_cst": variacao_fiscal.pis_cst,
                "cofins_cst": variacao_fiscal.cofins_cst
            }

    # 3️⃣ Produto
    produto_fiscal = (
        db.query(ProdutoConfigFiscal)
        .filter(
            ProdutoConfigFiscal.tenant_id == tenant_id,
            ProdutoConfigFiscal.produto_id == produto_id
        )
        .first()
    )

    if produto_fiscal:
        return {
            "origem": "produto",
            "ncm": produto_fiscal.ncm,
            "cest": produto_fiscal.cest,
            "cst_icms": produto_fiscal.cst_icms,
            "icms_st": produto_fiscal.icms_st,
            "pis_cst": produto_fiscal.pis_cst,
            "cofins_cst": produto_fiscal.cofins_cst
        }

    # 4️⃣ Empresa
    empresa_fiscal = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if not empresa_fiscal:
        raise Exception("Configuração fiscal da empresa não encontrada")

    return {
        "origem": "empresa",
        "ncm": None,
        "cest": None,
        "cst_icms": None,
        "icms_st": False,
        "pis_cst": empresa_fiscal.pis_cst_padrao,
        "cofins_cst": empresa_fiscal.cofins_cst_padrao
    }
