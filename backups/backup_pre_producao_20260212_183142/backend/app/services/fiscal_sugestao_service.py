from sqlalchemy.orm import Session
from app.fiscal_catalogo_produtos_models import FiscalCatalogoProdutos


def sugerir_fiscal_por_descricao(
    db: Session,
    descricao_produto: str
):
    """
    Retorna sugestões fiscais com base na descrição do produto.
    Não grava nada no banco.
    """

    descricao = descricao_produto.lower()

    sugestoes = []

    registros = (
        db.query(FiscalCatalogoProdutos)
        .filter(FiscalCatalogoProdutos.ativo.is_(True))
        .all()
    )

    for r in registros:
        palavras = [p.strip().lower() for p in r.palavras_chave.split(",")]

        score = sum(1 for p in palavras if p in descricao)

        if score > 0:
            sugestoes.append({
                "categoria_fiscal": r.categoria_fiscal,
                "ncm": r.ncm,
                "cest": r.cest,
                "cst_icms": r.cst_icms,
                "icms_st": r.icms_st,
                "pis_cst": r.pis_cst,
                "cofins_cst": r.cofins_cst,
                "observacao": r.observacao,
                "score": score
            })

    # Ordena por melhor match
    sugestoes.sort(key=lambda x: x["score"], reverse=True)

    return sugestoes
