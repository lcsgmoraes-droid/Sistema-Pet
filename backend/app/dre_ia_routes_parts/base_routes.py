from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session as get_db
from app.dre_ia_routes_parts.dependencies import _usuario_dre
from app.dre_ia_routes_parts.schemas import (
    CategoriaRentabilidade,
    CalcularDRERequest,
    DRECompleto,
    DREResumo,
    InsightDRE,
    ProdutoRentabilidade,
)
from app.ia.aba7_dre import DREService
from app.models import User

router = APIRouter()


@router.post("/calcular", response_model=DRECompleto)
async def calcular_dre(
    request: CalcularDRERequest,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Calcula DRE para um período"""
    usuario_id = current_user.id

    service = DREService(db)
    dre = service.calcular_dre_periodo(
        usuario_id, request.data_inicio, request.data_fim
    )

    return dre


@router.get("/canais")
async def listar_canais(current_user: User = Depends(get_current_user)):
    """Lista todos os canais disponíveis"""
    return {
        "canais": [
            {"key": "loja_fisica", "nome": "Loja Física"},
            {"key": "mercado_livre", "nome": "Mercado Livre"},
            {"key": "shopee", "nome": "Shopee"},
            {"key": "amazon", "nome": "Amazon"},
            {"key": "site", "nome": "Site Próprio"},
            {"key": "instagram", "nome": "Instagram/WhatsApp"},
        ]
    }


@router.get("/listar", response_model=List[DREResumo])
async def listar_dres(
    limit: int = Query(12, ge=1, le=100),
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Lista DREs calculados"""
    usuario_id = current_user.id

    service = DREService(db)
    dres = service.listar_dres(usuario_id, limit)

    return dres


@router.get("/{dre_id}", response_model=DRECompleto)
async def obter_dre(
    dre_id: int,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Obtém DRE completo"""
    usuario_id = current_user.id

    service = DREService(db)
    dre = service.obter_dre(dre_id, usuario_id)

    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")

    return dre


@router.get("/{dre_id}/produtos", response_model=List[ProdutoRentabilidade])
async def obter_produtos_rentabilidade(
    dre_id: int,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Obtém ranking de produtos por rentabilidade"""
    usuario_id = current_user.id

    service = DREService(db)
    produtos = service.obter_produtos_rentabilidade(dre_id, usuario_id)

    return produtos


@router.get("/{dre_id}/categorias", response_model=List[CategoriaRentabilidade])
async def obter_categorias_rentabilidade(
    dre_id: int,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Obtém análise por categoria"""
    usuario_id = current_user.id

    service = DREService(db)
    categorias = service.obter_categorias_rentabilidade(dre_id, usuario_id)

    return categorias


@router.get("/{dre_id}/insights", response_model=List[InsightDRE])
async def obter_insights(
    dre_id: int,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Obtém insights automáticos"""
    usuario_id = current_user.id

    service = DREService(db)
    insights = service.obter_insights(dre_id, usuario_id)

    return insights


@router.get("/comparar/{dre1_id}/{dre2_id}")
async def comparar_periodos(
    dre1_id: int,
    dre2_id: int,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Compara dois períodos"""
    usuario_id = current_user.id

    service = DREService(db)
    comparacao = service.comparar_periodos(usuario_id, dre1_id, dre2_id)

    if not comparacao:
        raise HTTPException(status_code=404, detail="Um ou mais DREs não encontrados")

    return comparacao


@router.get("/indices-mercado")
async def obter_indices_mercado(
    setor: str = Query("pet_shop", description="Setor a consultar"),
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Obtém índices de mercado (benchmarks) para comparação"""
    from app.ia.aba7_models import IndicesMercado

    indices = (
        db.query(IndicesMercado)
        .filter(IndicesMercado.setor == setor, IndicesMercado.ativo.is_(True))
        .first()
    )

    if not indices:
        raise HTTPException(
            status_code=404,
            detail=f"Índices de mercado não encontrados para o setor '{setor}'. Execute o script criar_indices_mercado.py",
        )

    return {
        "setor": indices.setor,
        "descricao": indices.descricao,
        "benchmarks": {
            "cmv": {
                "min": indices.cmv_ideal_min,
                "max": indices.cmv_ideal_max,
                "descricao": "Custo de Mercadorias Vendidas (% da receita)",
            },
            "margem_bruta": {
                "min": indices.margem_bruta_ideal_min,
                "max": indices.margem_bruta_ideal_max,
                "descricao": "Margem Bruta (%)",
            },
            "margem_liquida": {
                "min": indices.margem_liquida_ideal_min,
                "max": indices.margem_liquida_ideal_max,
                "descricao": "Margem Líquida (%)",
            },
            "despesas_admin": {
                "max": indices.despesas_admin_ideal_max,
                "descricao": "Despesas Administrativas (% da receita)",
            },
            "despesas_vendas": {
                "max": indices.despesas_vendas_ideal_max,
                "descricao": "Despesas de Vendas (% da receita)",
            },
            "despesas_totais": {
                "max": indices.despesas_totais_ideal_max,
                "descricao": "Despesas Operacionais Totais (% da receita)",
            },
            "impostos": {
                "min": indices.impostos_ideal_min,
                "max": indices.impostos_ideal_max,
                "descricao": "Impostos (% da receita)",
            },
        },
        "fonte": indices.fonte,
        "ano_referencia": indices.referencia_ano,
    }


@router.get("/setores-disponiveis")
async def listar_setores(
    current_user: User = Depends(_usuario_dre), db: Session = Depends(get_db)
):
    """Lista setores disponíveis com índices de mercado"""
    from app.ia.aba7_models import IndicesMercado

    setores = db.query(IndicesMercado).filter(IndicesMercado.ativo.is_(True)).all()

    return {
        "setores": [
            {"key": s.setor, "nome": s.descricao, "ano_referencia": s.referencia_ano}
            for s in setores
        ]
    }


@router.post("/calcular-mes-atual", response_model=DRECompleto)
async def calcular_mes_atual(
    current_user: User = Depends(_usuario_dre), db: Session = Depends(get_db)
):
    """Calcula DRE do mês atual (atalho)"""
    from datetime import date

    usuario_id = current_user.id
    hoje = date.today()
    data_inicio = hoje.replace(day=1)
    data_fim = hoje

    service = DREService(db)
    dre = service.calcular_dre_periodo(usuario_id, data_inicio, data_fim)

    return dre


@router.post("/calcular-mes-passado", response_model=DRECompleto)
async def calcular_mes_passado(
    current_user: User = Depends(_usuario_dre), db: Session = Depends(get_db)
):
    """Calcula DRE do mês passado completo (atalho)"""
    from datetime import date
    from dateutil.relativedelta import relativedelta

    usuario_id = current_user.id
    hoje = date.today()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - relativedelta(days=1)
    primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

    service = DREService(db)
    dre = service.calcular_dre_periodo(
        usuario_id, primeiro_dia_mes_passado, ultimo_dia_mes_passado
    )

    return dre
