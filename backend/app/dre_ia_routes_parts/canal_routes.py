from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.dre_ia_routes_parts.dependencies import _usuario_dre
from app.dre_ia_routes_parts.schemas import (
    CalcularDRECanalRequest,
    CalcularDREConsolidadoRequest,
)

router = APIRouter()


@router.get("/canais")
def listar_canais_disponiveis(
    db: Session = Depends(get_db),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todos os canais de venda disponíveis

    Returns:
        {
            'loja_fisica': 'Loja Física (PDV)',
            'mercado_livre': 'Mercado Livre',
            'shopee': 'Shopee',
            'amazon': 'Amazon',
            ...
        }
    """
    from app.ia.aba7_dre_canal import DRECanalService

    service = DRECanalService(db)
    return service.listar_canais_disponiveis()


@router.post("/calcular-por-canal")
def calcular_dre_por_canal(
    dados: CalcularDRECanalRequest,
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Calcula DRE de um canal específico

    Canais disponíveis:
    - loja_fisica: Vendas no PDV da loja
    - mercado_livre: Vendas no Mercado Livre
    - shopee: Vendas na Shopee
    - amazon: Vendas na Amazon
    - site: Site próprio
    - instagram: Instagram/WhatsApp
    """
    from app.ia.aba7_dre_canal import DRECanalService

    service = DRECanalService(db)

    # Validar canal
    if dados.canal not in service.CANAIS_DISPONIVEIS:
        raise HTTPException(
            status_code=400,
            detail=f"Canal inválido. Canais disponíveis: {list(service.CANAIS_DISPONIVEIS.keys())}",
        )

    dre = service.calcular_dre_por_canal(
        usuario_id=current_user.id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        canal=dados.canal,
    )

    return dre


@router.post("/calcular-consolidado")
def calcular_dre_consolidado_canais(
    dados: CalcularDREConsolidadoRequest,
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Calcula DRE consolidado de múltiplos canais

    Exemplo:
    - Apenas ML: canais = ["mercado_livre"]
    - ML + Shopee: canais = ["mercado_livre", "shopee"]
    - Todos: canais = ["loja_fisica", "mercado_livre", "shopee", "amazon"]

    O sistema soma automaticamente as receitas, custos e despesas de cada canal.
    """
    from app.ia.aba7_dre_canal import DRECanalService

    service = DRECanalService(db)

    # Validar canais
    for canal in dados.canais:
        if canal not in service.CANAIS_DISPONIVEIS:
            raise HTTPException(
                status_code=400,
                detail=f"Canal inválido: {canal}. Canais disponíveis: {list(service.CANAIS_DISPONIVEIS.keys())}",
            )

    if not dados.canais:
        raise HTTPException(
            status_code=400, detail="É necessário informar pelo menos 1 canal"
        )

    dre = service.calcular_dre_consolidado(
        usuario_id=current_user.id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        canais=dados.canais,
    )

    return dre


@router.get("/listar-por-canal")
def listar_dres_por_canal(
    data_inicio: date = Query(..., description="Data início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data fim (YYYY-MM-DD)"),
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Lista DREs calculados de todos os canais em um período

    Retorna um objeto com DRE de cada canal (ou null se não calculado):
    {
        'loja_fisica': {...},
        'mercado_livre': {...},
        'shopee': null,
        'amazon': null
    }
    """
    from app.ia.aba7_dre_canal import DRECanalService

    service = DRECanalService(db)
    dres = service.listar_dres_por_canal(
        usuario_id=current_user.id, data_inicio=data_inicio, data_fim=data_fim
    )

    return dres
