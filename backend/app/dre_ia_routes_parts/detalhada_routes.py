from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session as get_db
from app.dre_ia_routes_parts.dependencies import _usuario_dre
from app.dre_ia_routes_parts.schemas import (
    AlocarDespesaRequest,
    CalcularDREDetalhadadRequest,
    DREDetalheResponse,
)
from app.models import User

router = APIRouter()


@router.post("/calcular-detalhado", response_model=DREDetalheResponse)
async def calcular_dre_detalhado(
    request: CalcularDREDetalhadadRequest,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Calcula DRE para UM CANAL específico

    Cada canal é calculado de forma independente:
    - Receitas: vendas daquele canal
    - Custos: CMV daquele canal
    - Despesas: específicas do canal + alíquota das despesas gerais
    """
    from app.ia.aba7_dre_detalhada_service import DREDetalhadaService

    service = DREDetalhadaService(db)
    dre = service.calcular_dre_por_canal(
        usuario_id=current_user.id,
        data_inicio=request.data_inicio,
        data_fim=request.data_fim,
        canal=request.canal,
    )

    return dre


@router.post("/consolidado")
async def calcular_dre_consolidado(
    request: dict,  # {data_inicio, data_fim, canais: [lista de canais]}
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Consolida DRE de múltiplos canais

    Resposta estruturada:
    {
        "receitas": {
            "detalhado": [
                {canal: 'loja_fisica', receita_bruta: 10000, receita_liquida: 9500},
                {canal: 'mercado_livre', receita_bruta: 5000, receita_liquida: 4750}
            ],
            "totais": {receita_bruta: 15000, receita_liquida: 14250}
        },
        "custos": {...},
        "despesas": {...},
        "consolidado": {
            lucro_liquido: 5000,
            margem_liquida_percent: 35.09,
            status: 'lucro'
        }
    }
    """
    from app.ia.aba7_dre_detalhada_service import DREDetalhadaService

    data_inicio = date.fromisoformat(request.get("data_inicio"))
    data_fim = date.fromisoformat(request.get("data_fim"))
    canais = request.get("canais", [])

    service = DREDetalhadaService(db)
    resultado = service.calcular_dre_consolidado(
        usuario_id=current_user.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        canais=canais,
    )

    return resultado


@router.post("/alocar-despesa")
async def alocar_despesa(
    request: AlocarDespesaRequest,
    current_user: User = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Define como uma despesa será alocada aos canais

    Exemplo 1 - Proporcional:
    {
        "categoria": "aluguel",
        "valor_total": 7000,
        "modo": "proporcional",
        "canais": ["loja_fisica", "mercado_livre"],
        "usar_faturamento": true
    }
    Será dividido proporcionalmente ao faturamento de cada canal

    Exemplo 2 - Manual:
    {
        "categoria": "marketing",
        "valor_total": 3000,
        "modo": "manual",
        "canais": ["mercado_livre", "shopee"],
        "alocacao_manual": {
            "mercado_livre": {"valor": 1500, "percentual": 50},
            "shopee": {"valor": 1500, "percentual": 50}
        }
    }
    """
    from app.ia.aba7_dre_detalhada_service import DREDetalhadaService

    service = DREDetalhadaService(db)
    alocacao = service.salvar_alocacao_despesa(
        usuario_id=current_user.id,
        data_inicio=request.data_inicio,
        data_fim=request.data_fim,
        categoria=request.categoria,
        valor_total=request.valor_total,
        modo=request.modo,
        canais=request.canais,
        alocacao_manual=request.alocacao_manual,
        usar_faturamento=request.usar_faturamento,
    )

    return {
        "id": alocacao.id,
        "mensagem": f"Despesa de {request.categoria} alocada com sucesso",
        "modo": request.modo,
        "canais": request.canais,
    }
