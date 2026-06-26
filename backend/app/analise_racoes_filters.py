"""Filtros e calculos puros da analise avancada de racoes."""

from sqlalchemy import and_, func, or_

from .analise_racoes_schemas import FiltrosAnalise
from .produtos_models import Produto


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _produto_eh_racao_expr():
    tipo_normalizado = func.lower(func.coalesce(Produto.tipo, ""))
    classificacao_normalizada = func.lower(
        func.coalesce(Produto.classificacao_racao, "")
    )
    return or_(
        tipo_normalizado.like("ra%"),
        and_(
            classificacao_normalizada != "",
            classificacao_normalizada != "nao",
        ),
    )


def aplicar_filtros(query, filtros: FiltrosAnalise):
    """Aplica filtros usando campos FK para tabelas dinâmicas"""

    if filtros.especies:
        # especies_indicadas é String ('dog', 'cat', 'both')
        query = query.filter(Produto.especies_indicadas.in_(filtros.especies))

    if filtros.linhas:
        # linha_racao_id é FK para tabela linhas_racao
        query = query.filter(Produto.linha_racao_id.in_(filtros.linhas))

    if filtros.portes:
        # porte_animal_id é FK para tabela portes_animal
        query = query.filter(Produto.porte_animal_id.in_(filtros.portes))

    if filtros.fases:
        # fase_publico_id é FK para tabela fases_publico
        query = query.filter(Produto.fase_publico_id.in_(filtros.fases))

    if filtros.tratamentos:
        # tipo_tratamento_id é FK para tabela tipos_tratamento
        query = query.filter(Produto.tipo_tratamento_id.in_(filtros.tratamentos))

    if filtros.sabores:
        query = query.filter(Produto.sabor_proteina.in_(filtros.sabores))

    if filtros.pesos:
        query = query.filter(Produto.peso_embalagem.in_(filtros.pesos))

    if filtros.marca_ids:
        query = query.filter(Produto.marca_id.in_(filtros.marca_ids))

    if filtros.categoria_ids:
        query = query.filter(Produto.categoria_id.in_(filtros.categoria_ids))

    # Filtros de margem
    if filtros.margem_min is not None:
        query = query.filter(
            ((Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100)
            >= filtros.margem_min
        )

    if filtros.margem_max is not None:
        query = query.filter(
            ((Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100)
            <= filtros.margem_max
        )

    # Filtros de preço
    if filtros.preco_min:
        query = query.filter(Produto.preco_venda >= filtros.preco_min)

    if filtros.preco_max:
        query = query.filter(Produto.preco_venda <= filtros.preco_max)

    return query


def calcular_margem(preco_venda, preco_custo) -> float:
    """Calcula margem percentual"""
    if not preco_venda or preco_venda == 0:
        return 0.0
    return float((preco_venda - preco_custo) / preco_venda * 100)


def calcular_preco_kg(preco_venda, peso_embalagem) -> float:
    """Calcula preço por kg"""
    if not peso_embalagem or peso_embalagem == 0:
        return float(preco_venda)
    return float(preco_venda / peso_embalagem)
