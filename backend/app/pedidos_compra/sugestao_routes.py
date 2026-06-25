"""Rota de sugestao inteligente de pedidos de compra."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Cliente
from ..produtos_models import Marca, Produto, ProdutoFornecedor
from .sugestao import (
    JANELAS_GIRO_SUGESTAO,
    _calcular_dias_com_estoque,
    _calcular_planejamento_compra_sugestao,
    _calcular_tendencia_vendas_sugestao,
    _float_seguro_sugestao,
    _montar_item_sugestao_compra,
    _montar_resposta_sugestao_compra,
    _selecionar_produtos_fornecedor_sugestao,
)
from .sugestao_queries import (
    _agrupar_movimentacoes_estoque_periodo,
    _carregar_vendas_sugestao,
    _obter_estoque_atual_sugestao,
    _resolver_fornecedores_compra,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sugestao/{fornecedor_id}")
def sugerir_pedido_inteligente(
    fornecedor_id: int,
    periodo_dias: int = Query(
        default=90, ge=7, le=365, description="Período de análise (7-365 dias)"
    ),
    dias_cobertura: int = Query(
        default=30,
        ge=7,
        le=180,
        description="Dias de estoque que o pedido deve cobrir (7-180)",
    ),
    apenas_criticos: bool = Query(
        default=False, description="Apenas produtos críticos (estoque < 7 dias)"
    ),
    incluir_alerta: bool = Query(
        default=True, description="Incluir produtos em alerta"
    ),
    incluir_grupo_fornecedor: bool = Query(
        default=False,
        description="Incluir todos os CNPJs do grupo comercial do fornecedor",
    ),
    apenas_fornecedor_principal: bool = Query(
        default=False,
        description="Considerar apenas produtos cujo fornecedor principal esta no fornecedor/grupo selecionado",
    ),
    fornecedor_grupo_id: Optional[int] = Query(
        default=None,
        description="Grupo comercial de fornecedores para consolidar a sugestao",
    ),
    marca_ids: Optional[List[int]] = Query(
        default=None, description="Filtrar por marcas específicas"
    ),
    marca_ids_brackets: Optional[List[int]] = Query(default=None, alias="marca_ids[]"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    📊 Sugestão Inteligente de Pedido de Compra

    Analisa histórico de vendas, estoque atual e lead time do fornecedor
    para sugerir quantidade ideal a pedir de cada produto.

    Algoritmo:
    1. Calcula consumo médio diário baseado em vendas do período
    2. Verifica estoque atual e dias de cobertura restantes
    3. Considera lead time do fornecedor (prazo de entrega)
    4. Sugere quantidade para cobrir a cobertura escolhida, somando reposicao
       apenas quando o estoque atual nao cobre lead time + margem de seguranca.
    5. Prioriza produtos críticos (estoque baixo) e em alerta

    Parâmetros:
    - periodo_dias: Base de cálculo (30/60/90/180 dias)
    - dias_cobertura: Quantos dias de estoque o pedido deve garantir (15/30/45/60/90)
    - apenas_criticos: Filtrar apenas produtos com < 7 dias de estoque
    - incluir_alerta: Incluir produtos que atingiram estoque mínimo
    """
    user, tenant_id = user_and_tenant

    logger.info(
        f"💡 Gerando sugestão de pedido - Fornecedor: {fornecedor_id} | Período: {periodo_dias} dias"
    )

    # Validar fornecedor
    fornecedor = (
        db.query(Cliente)
        .filter(
            Cliente.id == fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
        )
        .first()
    )

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    # Data inicial para análise
    fornecedor_ids, fornecedor_grupo = _resolver_fornecedores_compra(
        db,
        tenant_id,
        fornecedor,
        incluir_grupo_fornecedor=incluir_grupo_fornecedor,
        fornecedor_grupo_id=fornecedor_grupo_id,
    )

    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=periodo_dias)

    marcas_filtro = marca_ids or marca_ids_brackets or []

    # Buscar produtos do fornecedor com relacionamento e marca
    produtos_fornecedor_query = (
        db.query(Produto, ProdutoFornecedor, Marca)
        .join(ProdutoFornecedor, Produto.id == ProdutoFornecedor.produto_id)
        .outerjoin(Marca, Produto.marca_id == Marca.id)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo,
            or_(
                Produto.participa_sugestao_compra,
                Produto.participa_sugestao_compra.is_(None),
            ),
            or_(Produto.e_granel.is_(False), Produto.e_granel.is_(None)),
            ~Produto.nome.ilike("%granel%"),
            ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids),
            ProdutoFornecedor.ativo,
        )
    )

    if apenas_fornecedor_principal:
        produtos_fornecedor_query = produtos_fornecedor_query.filter(
            or_(
                ProdutoFornecedor.e_principal,
                ProdutoFornecedor.fornecedor_id == Produto.fornecedor_id,
                Produto.fornecedor_id.is_(None),
            ),
        )

    if marcas_filtro:
        produtos_fornecedor_query = produtos_fornecedor_query.filter(
            Produto.marca_id.in_(marcas_filtro)
        )

    produtos_fornecedor_raw = produtos_fornecedor_query.all()
    fornecedores_por_id = {
        item.id: item.nome
        for item in db.query(Cliente.id, Cliente.nome)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.id.in_(fornecedor_ids),
        )
        .all()
    }

    produtos_fornecedor = _selecionar_produtos_fornecedor_sugestao(
        produtos_fornecedor_raw,
        fornecedor_id,
    )

    if not produtos_fornecedor:
        return {
            "fornecedor": {
                "id": fornecedor.id,
                "nome": fornecedor.nome,
                "ids_considerados": fornecedor_ids,
                "grupo": {
                    "id": fornecedor_grupo.id,
                    "nome": fornecedor_grupo.nome,
                }
                if fornecedor_grupo
                else None,
            },
            "periodo_dias": periodo_dias,
            "apenas_fornecedor_principal": apenas_fornecedor_principal,
            "sugestoes": [],
            "resumo": {
                "total_produtos": 0,
                "produtos_criticos": 0,
                "produtos_alerta": 0,
                "valor_total_estimado": 0,
            },
            "mensagem": "Nenhum produto vinculado a este fornecedor",
        }

    sugestoes = []
    total_criticos = 0
    total_alerta = 0
    valor_total = 0

    # Bulk queries de vendas — 2 queries no total em vez de N queries individuais
    ids_produtos = [p.id for p, _pf, _marca in produtos_fornecedor]
    vendas_por_produto = _carregar_vendas_sugestao(
        db,
        tenant_id,
        ids_produtos,
        periodo_dias,
        data_fim,
    )
    movimentacoes_por_produto = _agrupar_movimentacoes_estoque_periodo(
        db,
        tenant_id,
        ids_produtos,
        data_inicio,
        data_fim,
    )

    for produto, produto_fornecedor, marca in produtos_fornecedor:
        # Consumo no período — lookup em vez de query individual
        vendas_stats = vendas_por_produto.get(produto.id) or {
            "vendas_periodo": 0.0,
            "janelas": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
            "origens": [],
            "fontes": [],
            "granel_consumo": {},
        }
        vendas_periodo = _float_seguro_sugestao(vendas_stats.get("vendas_periodo"))
        vendas_janelas = vendas_stats.get("janelas") or {}
        vendas_30 = _float_seguro_sugestao(vendas_janelas.get("30"))

        # Consumo médio diário
        estoque_atual, estoque_info = _obter_estoque_atual_sugestao(
            db, produto, tenant_id
        )
        estoque_minimo = _float_seguro_sugestao(produto.estoque_minimo)
        cobertura_estoque = _calcular_dias_com_estoque(
            movimentacoes_por_produto.get(produto.id, []),
            estoque_atual,
            data_inicio,
            data_fim,
        )

        dias_com_estoque = _float_seguro_sugestao(cobertura_estoque["dias_com_estoque"])
        dias_sem_estoque = _float_seguro_sugestao(cobertura_estoque["dias_sem_estoque"])
        ruptura_ativa = bool(cobertura_estoque["ruptura_ativa"])
        teve_ruptura = bool(cobertura_estoque["teve_ruptura"])

        lead_time = produto_fornecedor.prazo_entrega or 7
        planejamento_compra = _calcular_planejamento_compra_sugestao(
            vendas_periodo=vendas_periodo,
            vendas_30=vendas_30,
            periodo_dias=periodo_dias,
            estoque_atual=estoque_atual,
            estoque_minimo=estoque_minimo,
            dias_com_estoque=dias_com_estoque,
            dias_cobertura=dias_cobertura,
            lead_time=lead_time,
            ruptura_ativa=ruptura_ativa,
            teve_ruptura=teve_ruptura,
        )

        consumo_observado = planejamento_compra["consumo_observado"]
        consumo_recente = planejamento_compra["consumo_recente"]
        quantidade_sugerida = planejamento_compra["quantidade_sugerida"]
        prioridade = planejamento_compra["prioridade"]

        if prioridade == "CR\u00cdTICO":
            total_criticos += 1
        elif prioridade == "ALERTA":
            total_alerta += 1

        tendencia = _calcular_tendencia_vendas_sugestao(
            periodo_dias,
            consumo_observado,
            consumo_recente,
        )

        # Preço unitário
        preco_unitario = _float_seguro_sugestao(
            produto_fornecedor.preco_custo
            if produto_fornecedor.preco_custo is not None
            else produto.preco_custo
        )
        valor_sugestao = quantidade_sugerida * preco_unitario

        # Aplicar filtros
        incluir_produto = True

        if apenas_criticos and prioridade != "CRÍTICO":
            incluir_produto = False

        if not incluir_alerta and prioridade == "ALERTA":
            incluir_produto = False

        # Adicionar à lista (mesmo com qtd 0 para visibilidade se estoque alto)
        if incluir_produto or quantidade_sugerida > 0:
            sugestao = _montar_item_sugestao_compra(
                produto=produto,
                produto_fornecedor=produto_fornecedor,
                marca=marca,
                fornecedor_grupo=fornecedor_grupo,
                fornecedores_por_id=fornecedores_por_id,
                estoque_info=estoque_info,
                vendas_stats=vendas_stats,
                vendas_janelas=vendas_janelas,
                vendas_periodo=vendas_periodo,
                estoque_atual=estoque_atual,
                estoque_minimo=estoque_minimo,
                dias_com_estoque=dias_com_estoque,
                dias_sem_estoque=dias_sem_estoque,
                teve_ruptura=teve_ruptura,
                ruptura_ativa=ruptura_ativa,
                lead_time=lead_time,
                dias_cobertura=dias_cobertura,
                planejamento=planejamento_compra,
                tendencia=tendencia,
                preco_unitario=preco_unitario,
                valor_sugestao=valor_sugestao,
            )
            sugestoes.append(sugestao)
            valor_total += valor_sugestao

    logger.info(
        f"✅ Sugestão gerada: {len(sugestoes)} produtos | {total_criticos} críticos | {total_alerta} em alerta"
    )

    return _montar_resposta_sugestao_compra(
        fornecedor=fornecedor,
        fornecedor_ids=fornecedor_ids,
        fornecedor_grupo=fornecedor_grupo,
        periodo_dias=periodo_dias,
        dias_cobertura=dias_cobertura,
        apenas_fornecedor_principal=apenas_fornecedor_principal,
        data_inicio=data_inicio,
        data_fim=data_fim,
        sugestoes=sugestoes,
        total_criticos=total_criticos,
        total_alerta=total_alerta,
        valor_total=valor_total,
    )
