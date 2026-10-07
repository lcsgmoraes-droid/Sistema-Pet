"""Classificacao compartilhada das contas a pagar na DRE por competencia."""

from datetime import date
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dre_canais.base import _normalizar_texto_dre
from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro_models import CategoriaFinanceira, ContaPagar, TipoDespesa


_TIPOS_ESTOQUE = {
    "produto para revenda",
    "produtos para revenda",
    "fornecedor de produto para revenda",
}
_CATEGORIAS_ESTOQUE = _TIPOS_ESTOQUE | {
    "entrada de mercadoria",
    "entrada de mercadorias",
    "compra de mercadoria",
    "compras de mercadorias",
    "mercadoria para revenda",
    "mercadorias para revenda",
}


def filtros_contas_pagar_dre(tenant_id: str, inicio: date, fim: date) -> tuple:
    """Aplica a mesma competencia e elegibilidade a linha e ao detalhamento."""
    return (
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.data_emissao >= inicio,
        ContaPagar.data_emissao < fim,
        ContaPagar.status != "cancelado",
        ContaPagar.status != "parcelado",
        ContaPagar.afeta_dre.is_(True),
        ContaPagar.nota_entrada_id.is_(None),
    )


def ids_fretes_sobre_compras(db: Session, tenant_id: str) -> set[int]:
    """Considera todas as subcategorias homonimas do tenant, inclusive antigas."""
    return {
        subcategoria_id
        for (subcategoria_id,) in db.query(DRESubcategoria.id)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            func.trim(func.lower(DRESubcategoria.nome)) == "fretes sobre compras",
        )
        .all()
    }


def classificacoes_contas_pagar(
    db: Session, tenant_id: str, contas: Iterable[ContaPagar]
) -> tuple[dict[int, str], dict[int, CategoriaFinanceira]]:
    """Carrega apenas classificacoes do tenant, incluindo categorias ancestrais."""
    contas = list(contas)
    tipo_ids = {conta.tipo_despesa_id for conta in contas if conta.tipo_despesa_id}
    categoria_ids = {conta.categoria_id for conta in contas if conta.categoria_id}
    tipos = (
        {
            tipo.id: tipo.nome
            for tipo in db.query(TipoDespesa)
            .filter(TipoDespesa.tenant_id == tenant_id, TipoDespesa.id.in_(tipo_ids))
            .all()
        }
        if tipo_ids
        else {}
    )
    categorias = (
        {
            categoria.id: categoria
            for categoria in db.query(CategoriaFinanceira)
            .filter(CategoriaFinanceira.tenant_id == tenant_id)
            .all()
        }
        if categoria_ids
        else {}
    )
    return tipos, categorias


def eh_compra_estoque(
    conta: ContaPagar,
    tipos: dict[int, str],
    categorias: dict[int, CategoriaFinanceira],
) -> bool:
    """Compra de revenda entra no CMV ao vender, nao ao criar a obrigacao."""
    if conta.nota_entrada_id is not None:
        return True

    tipo_nome = _normalizar_texto_dre(tipos.get(conta.tipo_despesa_id))
    if tipo_nome == "frete de compra":
        return False
    if tipo_nome in _TIPOS_ESTOQUE:
        return True

    categoria_id = conta.categoria_id
    visitados = set()
    while categoria_id and categoria_id not in visitados:
        visitados.add(categoria_id)
        categoria = categorias.get(categoria_id)
        if categoria is None:
            break
        if _normalizar_texto_dre(categoria.nome) in _CATEGORIAS_ESTOQUE:
            return True
        categoria_id = categoria.categoria_pai_id
    return False
