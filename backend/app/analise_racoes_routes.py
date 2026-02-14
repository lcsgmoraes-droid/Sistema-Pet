# -*- coding: utf-8 -*-
"""
Rotas de Análise Avançada de Rações
Dashboard dinâmico com filtros, gráficos e insights inteligentes

Versão: 1.0.0 (2026-02-14)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc, asc, distinct
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .produtos_models import Produto, Marca, Categoria
from .opcoes_racao_models import LinhaRacao, PorteAnimal, FasePublico, TipoTratamento, SaborProteina
from .vendas_models import VendaItem, Venda

router = APIRouter(prefix="/racoes/analises", tags=["Análises Rações"])


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


# ============================================================================
# SCHEMAS
# ============================================================================

from pydantic import BaseModel


class FiltrosAnalise(BaseModel):
    """Filtros dinâmicos para análises"""
    especies: Optional[List[str]] = None  # dog, cat, both
    linhas: Optional[List[int]] = None  # IDs da tabela linhas_racao
    portes: Optional[List[int]] = None  # IDs da tabela portes_animal
    fases: Optional[List[int]] = None  # IDs da tabela fases_publico
    tratamentos: Optional[List[int]] = None  # IDs da tabela tipos_tratamento
    sabores: Optional[List[str]] = None  # Strings de sabor_proteina
    pesos: Optional[List[float]] = None  # Valores em kg
    marca_ids: Optional[List[int]] = None
    categoria_ids: Optional[List[int]] = None
    margem_min: Optional[float] = None
    margem_max: Optional[float] = None
    preco_min: Optional[float] = None
    preco_max: Optional[float] = None
    data_inicio: Optional[str] = None  # Para vendas
    data_fim: Optional[str] = None


class AnaliseMargemSegmento(BaseModel):
    """Resultado de análise de margem por segmento"""
    segmento: str
    tipo_segmento: str  # "porte", "fase", "sabor", etc
    total_produtos: int
    margem_media: float
    margem_minima: float
    margem_maxima: float
    preco_medio_kg: float
    preco_minimo_kg: float
    preco_maximo_kg: float
    total_vendido: Optional[int] = 0
    faturamento: Optional[float] = 0.0


class ComparacaoMarca(BaseModel):
    """Comparação de preços entre marcas"""
    marca_id: int
    marca_nome: str
    total_produtos: int
    preco_medio_kg: float
    margem_media: float
    produto_mais_barato: Dict[str, Any]
    produto_mais_caro: Dict[str, Any]


class RankingProduto(BaseModel):
    """Produto no ranking de vendas"""
    produto_id: int
    nome: str
    marca: str
    categoria: str
    quantidade_vendida: int
    faturamento: float
    margem_media: float
    preco_medio_venda: float


class DashboardResumo(BaseModel):
    """Resumo geral do dashboard"""
    total_racoes: int
    total_classificadas: int
    percentual_classificadas: float
    marcas_cadastradas: int
    faturamento_periodo: float
    margem_media_geral: float
    produto_mais_vendido: Optional[Dict[str, Any]] = None
    segmento_mais_rentavel: Optional[Dict[str, Any]] = None


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

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
            ((Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100) >= filtros.margem_min
        )
    
    if filtros.margem_max is not None:
        query = query.filter(
            ((Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100) <= filtros.margem_max
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


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/resumo", response_model=DashboardResumo)
async def obter_resumo_dashboard(
    data_inicio: Optional[str] = Query(None, description="Data início para vendas (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data fim para vendas (YYYY-MM-DD)"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Resumo geral do dashboard de rações
    
    Retorna estatísticas gerais:
    - Total de rações cadastradas
    - Total classificadas
    - Faturamento do período
    - Margem média geral
    - Produto mais vendido
    - Segmento mais rentável
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Total de rações
    total_racoes = db.query(func.count(Produto.id)).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim'
    ).scalar() or 0
    
    # Total classificadas (com pelo menos um campo preenchido)
    total_classificadas = db.query(func.count(Produto.id)).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim',
        or_(
            Produto.porte_animal.isnot(None),
            Produto.fase_publico.isnot(None),
            Produto.sabor_proteina.isnot(None),
            Produto.peso_embalagem.isnot(None)
        )
    ).scalar() or 0
    
    percentual_classificadas = (total_classificadas / total_racoes * 100) if total_racoes > 0 else 0
    
    # Marcas cadastradas
    marcas_cadastradas = db.query(func.count(Marca.id.distinct())).join(
        Produto, Produto.marca_id == Marca.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim'
    ).scalar() or 0
    
    # Margem média geral
    query_margem = db.query(
        func.avg(
            (Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100
        )
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim',
        Produto.preco_venda > 0
    )
    margem_media = query_margem.scalar() or 0.0
    
    # Vendas do período (se especificado)
    faturamento_periodo = 0.0
    produto_mais_vendido = None
    
    if data_inicio and data_fim:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
        
        # Faturamento
        faturamento_periodo = db.query(
            func.sum(VendaItem.preco_unitario * VendaItem.quantidade)
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).join(
            Produto, VendaItem.produto_id == Produto.id
        ).filter(
            Venda.tenant_id == tenant_id,
            Produto.classificacao_racao == 'sim',
            Venda.data_venda >= dt_inicio,
            Venda.data_venda <= dt_fim,
            Venda.status != 'cancelada'
        ).scalar() or 0.0
        
        # Produto mais vendido
        mais_vendido = db.query(
            Produto.id,
            Produto.nome,
            func.sum(VendaItem.quantidade).label('total_vendido')
        ).join(
            VendaItem, VendaItem.produto_id == Produto.id
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).filter(
            Venda.tenant_id == tenant_id,
            Produto.classificacao_racao == 'sim',
            Venda.data_venda >= dt_inicio,
            Venda.data_venda <= dt_fim,
            Venda.status != 'cancelada'
        ).group_by(Produto.id, Produto.nome).order_by(desc('total_vendido')).first()
        
        if mais_vendido:
            produto_mais_vendido = {
                "id": mais_vendido.id,
                "nome": mais_vendido.nome,
                "quantidade": float(mais_vendido.total_vendido)
            }
    
    # Segmento mais rentável (por porte)
    segmento_rentavel = db.query(
        Produto.porte_animal,
        func.avg(
            (Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100
        ).label('margem_media')
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim',
        Produto.porte_animal.isnot(None),
        Produto.preco_venda > 0
    ).group_by(Produto.porte_animal).order_by(desc('margem_media')).first()
    
    segmento_mais_rentavel = None
    if segmento_rentavel and segmento_rentavel.porte_animal:
        segmento_mais_rentavel = {
            "segmento": str(segmento_rentavel.porte_animal),
            "margem_media": float(segmento_rentavel.margem_media)
        }
    
    return DashboardResumo(
        total_racoes=total_racoes,
        total_classificadas=total_classificadas,
        percentual_classificadas=round(percentual_classificadas, 2),
        marcas_cadastradas=marcas_cadastradas,
        faturamento_periodo=float(faturamento_periodo),
        margem_media_geral=round(float(margem_media), 2),
        produto_mais_vendido=produto_mais_vendido,
        segmento_mais_rentavel=segmento_mais_rentavel
    )


@router.post("/margem-por-segmento", response_model=List[AnaliseMargemSegmento])
async def analisar_margem_por_segmento(
    filtros: FiltrosAnalise,
    tipo_segmento: str = Query("porte", description="porte, fase, sabor, linha, tratamento"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
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
        "especie": Produto.especie_animal
    }
    
    if tipo_segmento not in campo_map:
        raise HTTPException(400, "Tipo de segmento inválido")
    
    campo = campo_map[tipo_segmento]
    
    # Query base
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim',
        campo.isnot(None)
    )
    
    # Aplicar filtros
    query = aplicar_filtros(query, filtros)
    
    produtos = query.all()
    
    # Agrupar por segmento
    segmentos_dict = {}
    
    for produto in produtos:
        valor_campo = getattr(produto, tipo_segmento + ("_animal" if tipo_segmento in ["porte", "especie"] else "_publico" if tipo_segmento == "fase" else "_proteina" if tipo_segmento == "sabor" else "_racao" if tipo_segmento == "linha" else "_tratamento"))
        
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
                    "precos_kg": []
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
            preco_maximo_kg=round(max(precos), 2) if precos else 0
        )
        
        # Se tiver filtro de data, calcular vendas
        if filtros.data_inicio and filtros.data_fim:
            dt_inicio = datetime.strptime(filtros.data_inicio, "%Y-%m-%d")
            dt_fim = datetime.strptime(filtros.data_fim, "%Y-%m-%d")
            
            produto_ids = [p.id for p in dados["produtos"]]
            
            vendas = db.query(
                func.sum(VendaItem.quantidade).label('total_vendido'),
                func.sum(VendaItem.preco_unitario * VendaItem.quantidade).label('faturamento')
            ).join(
                Venda, VendaItem.venda_id == Venda.id
            ).filter(
                Venda.tenant_id == tenant_id,
                VendaItem.produto_id.in_(produto_ids),
                Venda.data_venda >= dt_inicio,
                Venda.data_venda <= dt_fim,
                Venda.status != 'cancelada'
            ).first()
            
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
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
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
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim',
        Produto.marca_id.isnot(None)
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
                "precos_kg": []
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
            preco_medio_kg=round(sum([p[0] for p in precos_kg]) / len(precos_kg), 2) if precos_kg else 0,
            margem_media=round(sum(margens) / len(margens), 2) if margens else 0,
            produto_mais_barato={
                "id": produto_barato.id,
                "nome": produto_barato.nome,
                "preco_kg": round(precos_kg[0][0], 2),
                "preco_venda": float(produto_barato.preco_venda)
            } if produto_barato else {},
            produto_mais_caro={
                "id": produto_caro.id,
                "nome": produto_caro.nome,
                "preco_kg": round(precos_kg[-1][0], 2),
                "preco_venda": float(produto_caro.preco_venda)
            } if produto_caro else {}
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
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
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
    ranking = db.query(
        Produto.id,
        Produto.nome,
        Marca.nome.label('marca_nome'),
        Categoria.nome.label('categoria_nome'),
        func.sum(VendaItem.quantidade).label('quantidade_vendida'),
        func.sum(VendaItem.preco_unitario * VendaItem.quantidade).label('faturamento'),
        func.avg(
            (VendaItem.preco_unitario - Produto.preco_custo) / VendaItem.preco_unitario * 100
        ).label('margem_media'),
        func.avg(VendaItem.preco_unitario).label('preco_medio')
    ).join(
        VendaItem, VendaItem.produto_id == Produto.id
    ).join(
        Venda, VendaItem.venda_id == Venda.id
    ).outerjoin(
        Marca, Produto.marca_id == Marca.id
    ).outerjoin(
        Categoria, Produto.categoria_id == Categoria.id
    ).filter(
        Venda.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        Venda.data_venda >= dt_inicio,
        Venda.data_venda <= dt_fim,
        Venda.status != 'cancelada'
    ).group_by(
        Produto.id,
        Produto.nome,
        Marca.nome,
        Categoria.nome
    ).order_by(desc('quantidade_vendida')).limit(limite).all()
    
    resultados = []
    for item in ranking:
        resultados.append(RankingProduto(
            produto_id=item.id,
            nome=item.nome,
            marca=item.marca_nome or "Sem Marca",
            categoria=item.categoria_nome or "Sem Categoria",
            quantidade_vendida=int(item.quantidade_vendida),
            faturamento=float(item.faturamento),
            margem_media=round(float(item.margem_media or 0), 2),
            preco_medio_venda=float(item.preco_medio)
        ))
    
    return resultados


@router.get("/opcoes-filtros")
async def obter_opcoes_filtros(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Retorna todas as opções disponíveis para filtros
    
    Útil para popular dropdowns e checkboxes dinamicamente
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar valores únicos de cada campo JSONB
    from sqlalchemy import distinct, text
    
    # Marcas
    marcas = db.query(Marca.id, Marca.nome).join(
        Produto, Produto.marca_id == Marca.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim'
    ).distinct().all()
    
    # Categorias
    categorias = db.query(Categoria.id, Categoria.nome).join(
        Produto, Produto.categoria_id == Categoria.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim'
    ).distinct().all()
    
    # Sabores
    sabores = db.query(distinct(Produto.sabor_proteina)).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        Produto.sabor_proteina.isnot(None)
    ).all()
    
    # Para campos JSONB, precisamos fazer query diferente
    # Especies (usando especies_indicadas que é String: dog, cat, both)
    especies_result = db.query(distinct(Produto.especies_indicadas)).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        Produto.especies_indicadas.isnot(None)
    ).all()
    especies = [row[0] for row in especies_result if row[0]]
    
    # Linhas de ração (buscar da tabela linhas_racao)
    linhas = db.query(LinhaRacao.id, LinhaRacao.nome).join(
        Produto, Produto.linha_racao_id == LinhaRacao.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        LinhaRacao.ativo == True
    ).distinct().all()
    
    # Portes (buscar da tabela portes_animal via FK)
    portes = db.query(PorteAnimal.id, PorteAnimal.nome).join(
        Produto, Produto.porte_animal_id == PorteAnimal.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        PorteAnimal.ativo == True
    ).distinct().all()
    
    # Fases (buscar da tabela fases_publico via FK)
    fases = db.query(FasePublico.id, FasePublico.nome).join(
        Produto, Produto.fase_publico_id == FasePublico.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        FasePublico.ativo == True
    ).distinct().all()
    
    # Tratamentos (buscar da tabela tipos_tratamento via FK)
    tratamentos = db.query(TipoTratamento.id, TipoTratamento.nome).join(
        Produto, Produto.tipo_tratamento_id == TipoTratamento.id
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        TipoTratamento.ativo == True
    ).distinct().all()
    
    # Pesos (valores únicos de peso_embalagem)
    pesos_result = db.query(distinct(Produto.peso_embalagem)).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        Produto.peso_embalagem.isnot(None)
    ).order_by(Produto.peso_embalagem).all()
    pesos = [float(row[0]) for row in pesos_result if row[0]]
    
    return {
        "marcas": [{"id": m.id, "nome": m.nome} for m in marcas],
        "categorias": [{"id": c.id, "nome": c.nome} for c in categorias],
        "especies": sorted(list(set(especies))),
        "linhas": [{"id": l.id, "nome": l.nome} for l in linhas],
        "portes": [{"id": p.id, "nome": p.nome} for p in portes],
        "fases": [{"id": f.id, "nome": f.nome} for f in fases],
        "tratamentos": [{"id": t.id, "nome": t.nome} for t in tratamentos],
        "sabores": sorted([s[0] for s in sabores if s[0]]),
        "pesos": pesos  # Em kg
    }


@router.post("/produtos-comparacao")
async def obter_produtos_para_comparacao(
    filtros: FiltrosAnalise,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Busca produtos filtrados para comparação detalhada
    
    Retorna lista completa de produtos que atendem aos filtros,
    com todos os campos para análise de margem, ROI e rentabilidade.
    
    Este endpoint é otimizado para a tabela dinâmica de comparação.
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Query base com joins
    query = db.query(Produto).join(
        Marca, Produto.marca_id == Marca.id, isouter=True
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.classificacao_racao == 'sim'
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
        resultado.append({
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "marca": {
                "id": produto.marca.id if produto.marca else None,
                "nome": produto.marca.nome if produto.marca else None
            },
            "classificacao_racao": produto.classificacao_racao,
            "porte_animal": produto.porte_animal or [],
            "fase_publico": produto.fase_publico or [],
            "tipo_tratamento": produto.tipo_tratamento or [],
            "sabor_proteina": produto.sabor_proteina,
            "peso_embalagem": float(produto.peso_embalagem) if produto.peso_embalagem else None,
            "preco_custo": float(produto.preco_custo) if produto.preco_custo else 0.0,
            "preco_venda": float(produto.preco_venda) if produto.preco_venda else 0.0,
            "estoque_atual": produto.estoque_atual or 0,
            "estoque_minimo": produto.estoque_minimo or 0,
            "especies_indicadas": produto.especies_indicadas,
            "linha_racao_id": produto.linha_racao_id
        })
    
    return resultado
