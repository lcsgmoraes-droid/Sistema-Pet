# -*- coding: utf-8 -*-
"""Rotas de segmentos, marcas e ranking de racoes."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.analise_racoes_filters import (
    _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario,
    aplicar_filtros,
    calcular_margem,
    calcular_preco_kg,
)
from app.analise_racoes_schemas import (
    AnaliseMargemSegmento,
    ComparacaoMarca,
    FiltrosAnalise,
    RankingProduto,
)
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Categoria, Marca, Produto
from app.vendas_models import Venda, VendaItem

router = APIRouter()


@router.post("/margem-por-segmento", response_model=List[AnaliseMargemSegmento])
async def analisar_margem_por_segmento(
    filtros: FiltrosAnalise,
    tipo_segmento: str = Query(
        "porte", description="porte, fase, sabor, linha, tratamento"
    ),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Análise de margem por segmento

    Agrupa produtos por tipo de segmento e calcula:
    - Margem média, mínima e máxima
    - Preço médio por kg
    - Total de produtos no segmento
    - Total vendido e faturamento (se filtro de data fornecido)
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Mapear tipo de segmento para campo
    campo_map = {
        "porte": Produto.porte_animal,
        "fase": Produto.fase_publico,
        "sabor": Produto.sabor_proteina,
        "linha": Produto.linha_racao,
        "tratamento": Produto.tipo_tratamento,
        "especie": Produto.especie_animal,
    }

    if tipo_segmento not in campo_map:
        raise HTTPException(400, "Tipo de segmento inválido")

    campo = campo_map[tipo_segmento]

    # Query base
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        _produto_eh_racao_expr(),
        campo.isnot(None),
    )

    # Aplicar filtros
    query = aplicar_filtros(query, filtros)

    produtos = query.all()

    # Agrupar por segmento
    segmentos_dict = {}

    for produto in produtos:
        valor_campo = getattr(
            produto,
            tipo_segmento
            + (
                "_animal"
                if tipo_segmento in ["porte", "especie"]
                else "_publico"
                if tipo_segmento == "fase"
                else "_proteina"
                if tipo_segmento == "sabor"
                else "_racao"
                if tipo_segmento == "linha"
                else "_tratamento"
            ),
        )

        # Se for JSONB (lista), iterar
        if isinstance(valor_campo, list):
            segmentos = valor_campo
        else:
            segmentos = [valor_campo] if valor_campo else []

        for segmento in segmentos:
            if not segmento:
                continue

            if segmento not in segmentos_dict:
                segmentos_dict[segmento] = {
                    "produtos": [],
                    "margens": [],
                    "precos_kg": [],
                }

            margem = calcular_margem(produto.preco_venda, produto.preco_custo)
            preco_kg = calcular_preco_kg(produto.preco_venda, produto.peso_embalagem)

            segmentos_dict[segmento]["produtos"].append(produto)
            segmentos_dict[segmento]["margens"].append(margem)
            segmentos_dict[segmento]["precos_kg"].append(preco_kg)

    # Calcular estatísticas
    resultados = []
    for segmento, dados in segmentos_dict.items():
        margens = dados["margens"]
        precos = dados["precos_kg"]

        resultado = AnaliseMargemSegmento(
            segmento=segmento,
            tipo_segmento=tipo_segmento,
            total_produtos=len(dados["produtos"]),
            margem_media=round(sum(margens) / len(margens), 2) if margens else 0,
            margem_minima=round(min(margens), 2) if margens else 0,
            margem_maxima=round(max(margens), 2) if margens else 0,
            preco_medio_kg=round(sum(precos) / len(precos), 2) if precos else 0,
            preco_minimo_kg=round(min(precos), 2) if precos else 0,
            preco_maximo_kg=round(max(precos), 2) if precos else 0,
        )

        # Se tiver filtro de data, calcular vendas
        if filtros.data_inicio and filtros.data_fim:
            dt_inicio = datetime.strptime(filtros.data_inicio, "%Y-%m-%d")
            dt_fim = datetime.strptime(filtros.data_fim, "%Y-%m-%d")

            produto_ids = [p.id for p in dados["produtos"]]

            vendas = (
                db.query(
                    func.sum(VendaItem.quantidade).label("total_vendido"),
                    func.sum(VendaItem.preco_unitario * VendaItem.quantidade).label(
                        "faturamento"
                    ),
                )
                .join(Venda, VendaItem.venda_id == Venda.id)
                .filter(
                    Venda.tenant_id == tenant_id,
                    VendaItem.produto_id.in_(produto_ids),
                    Venda.data_venda >= dt_inicio,
                    Venda.data_venda <= dt_fim,
                    Venda.status != "cancelada",
                )
                .first()
            )

            if vendas:
                resultado.total_vendido = int(vendas.total_vendido or 0)
                resultado.faturamento = float(vendas.faturamento or 0)

        resultados.append(resultado)

    # Ordenar por margem média decrescente
    resultados.sort(key=lambda x: x.margem_media, reverse=True)

    return resultados


@router.post("/comparacao-marcas", response_model=List[ComparacaoMarca])
async def comparar_marcas(
    filtros: FiltrosAnalise,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Comparação de preços e margens entre marcas

    Para cada marca, retorna:
    - Total de produtos
    - Preço médio por kg
    - Margem média
    - Produto mais barato e mais caro
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Query base
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        _produto_eh_racao_expr(),
        Produto.marca_id.isnot(None),
    )

    # Aplicar filtros
    query = aplicar_filtros(query, filtros)

    produtos = query.all()

    # Agrupar por marca
    marcas_dict = {}

    for produto in produtos:
        marca_id = produto.marca_id

        if marca_id not in marcas_dict:
            marca = db.query(Marca).filter(Marca.id == marca_id).first()
            marcas_dict[marca_id] = {
                "nome": marca.nome if marca else "Sem Marca",
                "produtos": [],
                "margens": [],
                "precos_kg": [],
            }

        margem = calcular_margem(produto.preco_venda, produto.preco_custo)
        preco_kg = calcular_preco_kg(produto.preco_venda, produto.peso_embalagem)

        marcas_dict[marca_id]["produtos"].append(produto)
        marcas_dict[marca_id]["margens"].append(margem)
        marcas_dict[marca_id]["precos_kg"].append((preco_kg, produto))

    # Calcular estatísticas
    resultados = []
    for marca_id, dados in marcas_dict.items():
        margens = dados["margens"]
        precos_kg = dados["precos_kg"]

        # Ordenar por preço/kg
        precos_kg.sort(key=lambda x: x[0])

        produto_barato = precos_kg[0][1] if precos_kg else None
        produto_caro = precos_kg[-1][1] if precos_kg else None

        resultado = ComparacaoMarca(
            marca_id=marca_id,
            marca_nome=dados["nome"],
            total_produtos=len(dados["produtos"]),
            preco_medio_kg=round(sum([p[0] for p in precos_kg]) / len(precos_kg), 2)
            if precos_kg
            else 0,
            margem_media=round(sum(margens) / len(margens), 2) if margens else 0,
            produto_mais_barato={
                "id": produto_barato.id,
                "nome": produto_barato.nome,
                "preco_kg": round(precos_kg[0][0], 2),
                "preco_venda": float(produto_barato.preco_venda),
            }
            if produto_barato
            else {},
            produto_mais_caro={
                "id": produto_caro.id,
                "nome": produto_caro.nome,
                "preco_kg": round(precos_kg[-1][0], 2),
                "preco_venda": float(produto_caro.preco_venda),
            }
            if produto_caro
            else {},
        )

        resultados.append(resultado)

    # Ordenar por preço médio/kg crescente
    resultados.sort(key=lambda x: x.preco_medio_kg)

    return resultados


@router.get("/ranking-vendas", response_model=List[RankingProduto])
async def obter_ranking_vendas(
    data_inicio: str = Query(..., description="Data início (YYYY-MM-DD)"),
    data_fim: str = Query(..., description="Data fim (YYYY-MM-DD)"),
    limite: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Ranking de produtos mais vendidos por categoria

    Retorna os produtos mais vendidos no período, incluindo:
    - Quantidade vendida
    - Faturamento
    - Margem média
    - Preço médio de venda
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")

    # Query de vendas
    ranking = (
        db.query(
            Produto.id,
            Produto.nome,
            Marca.nome.label("marca_nome"),
            Categoria.nome.label("categoria_nome"),
            func.sum(VendaItem.quantidade).label("quantidade_vendida"),
            func.sum(VendaItem.preco_unitario * VendaItem.quantidade).label(
                "faturamento"
            ),
            func.avg(
                (VendaItem.preco_unitario - Produto.preco_custo)
                / VendaItem.preco_unitario
                * 100
            ).label("margem_media"),
            func.avg(VendaItem.preco_unitario).label("preco_medio"),
        )
        .join(VendaItem, VendaItem.produto_id == Produto.id)
        .join(Venda, VendaItem.venda_id == Venda.id)
        .outerjoin(Marca, Produto.marca_id == Marca.id)
        .outerjoin(Categoria, Produto.categoria_id == Categoria.id)
        .filter(
            Venda.tenant_id == tenant_id,
            _produto_eh_racao_expr(),
            Venda.data_venda >= dt_inicio,
            Venda.data_venda <= dt_fim,
            Venda.status != "cancelada",
        )
        .group_by(Produto.id, Produto.nome, Marca.nome, Categoria.nome)
        .order_by(desc("quantidade_vendida"))
        .limit(limite)
        .all()
    )

    resultados = []
    for item in ranking:
        resultados.append(
            RankingProduto(
                produto_id=item.id,
                nome=item.nome,
                marca=item.marca_nome or "Sem Marca",
                categoria=item.categoria_nome or "Sem Categoria",
                quantidade_vendida=int(item.quantidade_vendida),
                faturamento=float(item.faturamento),
                margem_media=round(float(item.margem_media or 0), 2),
                preco_medio_venda=float(item.preco_medio),
            )
        )

    return resultados
