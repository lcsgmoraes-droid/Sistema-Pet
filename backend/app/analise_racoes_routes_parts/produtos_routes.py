# -*- coding: utf-8 -*-
"""Rota de produtos para comparacao de racoes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analise_racoes_filters import (
    _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario,
    aplicar_filtros,
)
from app.analise_racoes_schemas import FiltrosAnalise
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Marca, Produto

router = APIRouter()


@router.post("/produtos-comparacao")
async def obter_produtos_para_comparacao(
    filtros: FiltrosAnalise,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Busca produtos filtrados para comparação detalhada

    Retorna lista completa de produtos que atendem aos filtros,
    com todos os campos para análise de margem, ROI e rentabilidade.

    Este endpoint é otimizado para a tabela dinâmica de comparação.
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Query base com joins
    query = (
        db.query(Produto)
        .join(Marca, Produto.marca_id == Marca.id, isouter=True)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            _produto_eh_racao_expr(),
        )
    )

    # Aplicar filtros
    query = aplicar_filtros(query, filtros)

    # Ordenar por nome
    query = query.order_by(Produto.nome)

    # Limite de segurança (máximo 500 produtos)
    query = query.limit(500)

    # Executar query
    produtos = query.all()

    # Formatar resultado
    resultado = []
    for produto in produtos:
        resultado.append(
            {
                "id": produto.id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "marca": {
                    "id": produto.marca.id if produto.marca else None,
                    "nome": produto.marca.nome if produto.marca else None,
                },
                "classificacao_racao": produto.classificacao_racao,
                "porte_animal": produto.porte_animal or [],
                "fase_publico": produto.fase_publico or [],
                "tipo_tratamento": produto.tipo_tratamento or [],
                "sabor_proteina": produto.sabor_proteina,
                "peso_embalagem": float(produto.peso_embalagem)
                if produto.peso_embalagem
                else None,
                "preco_custo": float(produto.preco_custo)
                if produto.preco_custo
                else 0.0,
                "preco_venda": float(produto.preco_venda)
                if produto.preco_venda
                else 0.0,
                "estoque_atual": produto.estoque_atual or 0,
                "estoque_minimo": produto.estoque_minimo or 0,
                "especies_indicadas": produto.especies_indicadas,
                "linha_racao_id": produto.linha_racao_id,
            }
        )

    return resultado
