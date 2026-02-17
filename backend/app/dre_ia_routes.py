"""
Rotas API para DRE Inteligente - ABA 7
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from io import BytesIO

from app.db import get_session as get_db
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.ia.aba7_dre import DREService
from app.ia.aba7_models import DREPeriodo, DREProduto, DREInsight

router = APIRouter(prefix="/ia/dre", tags=["IA - DRE Inteligente"])


# ==================== SCHEMAS ====================

class DREResumo(BaseModel):
    id: int
    data_inicio: date
    data_fim: date
    mes: Optional[int]
    ano: Optional[int]
    receita_liquida: float
    lucro_liquido: float
    margem_liquida_percent: float
    status: str
    score_saude: int
    
    model_config = {"from_attributes": True}


class DRECompleto(BaseModel):
    id: int
    data_inicio: date
    data_fim: date
    
    # Receitas
    receita_bruta: float
    deducoes_receita: float
    receita_liquida: float
    
    # Custos
    custo_produtos_vendidos: float
    lucro_bruto: float
    margem_bruta_percent: float
    
    # Despesas
    despesas_vendas: float
    despesas_administrativas: float
    despesas_financeiras: float
    outras_despesas: float
    total_despesas_operacionais: float
    
    # Resultados
    lucro_operacional: float
    margem_operacional_percent: float
    lucro_liquido: float
    margem_liquida_percent: float
    
    # Análises
    status: str
    score_saude: int
    
    model_config = {"from_attributes": True}


class ProdutoRentabilidade(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    categoria: str
    quantidade_vendida: int
    receita_total: float
    custo_total: float
    lucro_total: float
    margem_percent: float
    ranking_rentabilidade: int
    eh_lucrativo: bool
    recomendacao: Optional[str]
    
    model_config = {"from_attributes": True}


class CategoriaRentabilidade(BaseModel):
    id: int
    categoria_nome: str
    quantidade_vendida: int
    receita_total: float
    custo_total: float
    lucro_total: float
    margem_percent: float
    participacao_receita_percent: float
    eh_categoria_principal: bool
    
    model_config = {"from_attributes": True}


class InsightDRE(BaseModel):
    id: int
    tipo: str
    categoria: str
    titulo: str
    descricao: str
    impacto: str
    acao_sugerida: Optional[str]
    impacto_estimado: Optional[float]
    foi_lido: bool
    
    model_config = {"from_attributes": True}


class CalcularDRERequest(BaseModel):
    data_inicio: date
    data_fim: date


# ==================== ENDPOINTS ====================

@router.post("/calcular", response_model=DRECompleto)
async def calcular_dre(
    request: CalcularDRERequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calcula DRE para um período"""
    usuario_id = current_user.id
    
    service = DREService(db)
    dre = service.calcular_dre_periodo(
        usuario_id,
        request.data_inicio,
        request.data_fim
    )
    
    return dre


@router.get("/canais")
async def listar_canais(current_user: User = Depends(get_current_user)):
    """Lista todos os canais disponíveis"""
    return {
        'canais': [
            {'key': 'loja_fisica', 'nome': 'Loja Física'},
            {'key': 'mercado_livre', 'nome': 'Mercado Livre'},
            {'key': 'shopee', 'nome': 'Shopee'},
            {'key': 'amazon', 'nome': 'Amazon'},
            {'key': 'site', 'nome': 'Site Próprio'},
            {'key': 'instagram', 'nome': 'Instagram/WhatsApp'}
        ]
    }


@router.get("/listar", response_model=List[DREResumo])
async def listar_dres(
    limit: int = Query(12, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista DREs calculados"""
    usuario_id = current_user.id
    
    service = DREService(db)
    dres = service.listar_dres(usuario_id, limit)
    
    return dres


@router.get("/{dre_id}", response_model=DRECompleto)
async def obter_dre(
    dre_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém ranking de produtos por rentabilidade"""
    usuario_id = current_user.id
    
    service = DREService(db)
    produtos = service.obter_produtos_rentabilidade(dre_id, usuario_id)
    
    return produtos


@router.get("/{dre_id}/categorias", response_model=List[CategoriaRentabilidade])
async def obter_categorias_rentabilidade(
    dre_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém análise por categoria"""
    usuario_id = current_user.id
    
    service = DREService(db)
    categorias = service.obter_categorias_rentabilidade(dre_id, usuario_id)
    
    return categorias


@router.get("/{dre_id}/insights", response_model=List[InsightDRE])
async def obter_insights(
    dre_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    setor: str = Query('pet_shop', description="Setor a consultar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém índices de mercado (benchmarks) para comparação"""
    from app.ia.aba7_models import IndicesMercado
    
    indices = db.query(IndicesMercado).filter(
        IndicesMercado.setor == setor,
        IndicesMercado.ativo == True
    ).first()
    
    if not indices:
        raise HTTPException(
            status_code=404, 
            detail=f"Índices de mercado não encontrados para o setor '{setor}'. Execute o script criar_indices_mercado.py"
        )
    
    return {
        'setor': indices.setor,
        'descricao': indices.descricao,
        'benchmarks': {
            'cmv': {
                'min': indices.cmv_ideal_min,
                'max': indices.cmv_ideal_max,
                'descricao': 'Custo de Mercadorias Vendidas (% da receita)'
            },
            'margem_bruta': {
                'min': indices.margem_bruta_ideal_min,
                'max': indices.margem_bruta_ideal_max,
                'descricao': 'Margem Bruta (%)'
            },
            'margem_liquida': {
                'min': indices.margem_liquida_ideal_min,
                'max': indices.margem_liquida_ideal_max,
                'descricao': 'Margem Líquida (%)'
            },
            'despesas_admin': {
                'max': indices.despesas_admin_ideal_max,
                'descricao': 'Despesas Administrativas (% da receita)'
            },
            'despesas_vendas': {
                'max': indices.despesas_vendas_ideal_max,
                'descricao': 'Despesas de Vendas (% da receita)'
            },
            'despesas_totais': {
                'max': indices.despesas_totais_ideal_max,
                'descricao': 'Despesas Operacionais Totais (% da receita)'
            },
            'impostos': {
                'min': indices.impostos_ideal_min,
                'max': indices.impostos_ideal_max,
                'descricao': 'Impostos (% da receita)'
            }
        },
        'fonte': indices.fonte,
        'ano_referencia': indices.referencia_ano
    }


@router.get("/setores-disponiveis")
async def listar_setores(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista setores disponíveis com índices de mercado"""
    from app.ia.aba7_models import IndicesMercado
    
    setores = db.query(IndicesMercado).filter(
        IndicesMercado.ativo == True
    ).all()
    
    return {
        'setores': [
            {
                'key': s.setor,
                'nome': s.descricao,
                'ano_referencia': s.referencia_ano
            }
            for s in setores
        ]
    }


@router.post("/calcular-mes-atual", response_model=DRECompleto)
async def calcular_mes_atual(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calcula DRE do mês atual (atalho)"""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    usuario_id = current_user.id
    hoje = date.today()
    data_inicio = hoje.replace(day=1)
    data_fim = hoje
    
    service = DREService(db)
    dre = service.calcular_dre_periodo(usuario_id, data_inicio, data_fim)
    
    return dre


@router.post("/calcular-mes-passado", response_model=DRECompleto)
async def calcular_mes_passado(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        usuario_id,
        primeiro_dia_mes_passado,
        ultimo_dia_mes_passado
    )
    
    return dre


@router.get("/{dre_id}/anomalias")
def obter_anomalias_dre(
    dre_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna alertas de anomalias detectadas no DRE
    
    Anomalias são valores significativamente fora do padrão histórico:
    - Receita muito abaixo/acima da média
    - Custos anormalmente altos
    - Margens fora do esperado
    - Despesas fora do padrão
    """
    from app.ia.aba7_anomalias import DetectorAnomalias
    
    usuario_id = current_user.id
    
    # Verificar se DRE pertence ao usuário
    dre = db.query(DREPeriodo).filter(
        DREPeriodo.id == dre_id,
        DREPeriodo.usuario_id == usuario_id
    ).first()
    
    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")
    
    detector = DetectorAnomalias(db)
    alertas = detector.obter_alertas_ativos(usuario_id, dre_id)
    
    return {
        "dre_id": dre_id,
        "periodo": f"{dre.data_inicio} a {dre.data_fim}",
        "total_alertas": len(alertas),
        "alertas": alertas
    }


@router.post("/{dre_id}/recalcular-anomalias")
def recalcular_anomalias(
    dre_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Força recálculo de detecção de anomalias"""
    from app.ia.aba7_anomalias import DetectorAnomalias
    
    usuario_id = current_user.id
    
    # Verificar se DRE pertence ao usuário
    dre = db.query(DREPeriodo).filter(
        DREPeriodo.id == dre_id,
        DREPeriodo.usuario_id == usuario_id
    ).first()
    
    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")
    
    detector = DetectorAnomalias(db)
    anomalias = detector.detectar_anomalias_periodo(usuario_id, dre_id)
    
    return {
        "sucesso": True,
        "dre_id": dre_id,
        "anomalias_detectadas": len(anomalias),
        "anomalias": anomalias
    }


@router.get("/{dre_id}/exportar/pdf")
def exportar_dre_pdf(
    dre_id: int,
    incluir_produtos: bool = Query(True, description="Incluir análise de produtos"),
    incluir_categorias: bool = Query(True, description="Incluir análise de categorias"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporta DRE para PDF com formatação profissional
    
    Inclui:
    - Demonstração completa do resultado
    - Indicadores de performance
    - Score de saúde financeira
    - Top 10 produtos (opcional)
    - Análise por categoria (opcional)
    """
    from app.ia.aba7_exportador import ExportadorDRE
    
    usuario_id = current_user.id
    
    # Verificar se DRE pertence ao usuário
    dre = db.query(DREPeriodo).filter(
        DREPeriodo.id == dre_id,
        DREPeriodo.usuario_id == usuario_id
    ).first()
    
    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")
    
    exportador = ExportadorDRE(db)
    pdf_buffer = exportador.exportar_pdf(
        dre_periodo_id=dre_id,
        usuario_id=usuario_id,
        incluir_produtos=incluir_produtos,
        incluir_categorias=incluir_categorias
    )
    
    filename = f"DRE_{dre.data_inicio}_{dre.data_fim}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{dre_id}/exportar/excel")
def exportar_dre_excel(
    dre_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporta DRE para planilha Excel (.xlsx)
    
    Formato editável para análises personalizadas
    """
    from app.ia.aba7_exportador import ExportadorDRE
    
    usuario_id = current_user.id
    
    # Verificar se DRE pertence ao usuário
    dre = db.query(DREPeriodo).filter(
        DREPeriodo.id == dre_id,
        DREPeriodo.usuario_id == usuario_id
    ).first()
    
    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")
    
    exportador = ExportadorDRE(db)
    excel_buffer = exportador.exportar_excel(
        dre_periodo_id=dre_id,
        usuario_id=usuario_id
    )
    
    filename = f"DRE_{dre.data_inicio}_{dre.data_fim}.xlsx"
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== DRE POR CANAL ====================

@router.get("/canais")
def listar_canais_disponiveis():
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


class CalcularDRECanalRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canal: str  # 'loja_fisica', 'mercado_livre', etc
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
                "canal": "mercado_livre"
            }
        }
    }


class CalcularDREConsolidadoRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canais: List[str]  # ['loja_fisica', 'mercado_livre', 'shopee']
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
                "canais": ["mercado_livre", "shopee"]
            }
        }
    }


@router.post("/calcular-por-canal")
def calcular_dre_por_canal(
    dados: CalcularDRECanalRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
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
            detail=f"Canal inválido. Canais disponíveis: {list(service.CANAIS_DISPONIVEIS.keys())}"
        )
    
    dre = service.calcular_dre_por_canal(
        usuario_id=current_user.id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        canal=dados.canal
    )
    
    return dre


@router.post("/calcular-consolidado")
def calcular_dre_consolidado(
    dados: CalcularDREConsolidadoRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
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
                detail=f"Canal inválido: {canal}. Canais disponíveis: {list(service.CANAIS_DISPONIVEIS.keys())}"
            )
    
    if not dados.canais:
        raise HTTPException(status_code=400, detail="É necessário informar pelo menos 1 canal")
    
    dre = service.calcular_dre_consolidado(
        usuario_id=current_user.id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        canais=dados.canais
    )
    
    return dre


@router.get("/listar-por-canal")
def listar_dres_por_canal(
    data_inicio: date = Query(..., description="Data início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data fim (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        usuario_id=current_user.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    return dres


# ==================== DRE DETALHADA POR CANAL ====================
# Endpoints para nova funcionalidade: mostrar cada canal em linha separada

class CalcularDREDetalhadadRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canal: str  # 'loja_fisica', 'mercado_livre', etc


class DREDetalheResponse(BaseModel):
    """Uma linha de DRE (um canal específico)"""
    id: int
    canal: str
    receita_bruta: float
    receita_liquida: float
    custo_produtos_vendidos: float
    lucro_bruto: float
    total_despesas_operacionais: float
    lucro_operacional: float
    impostos: float
    lucro_liquido: float
    margem_liquida_percent: float
    status: str
    score_saude: float
    
    model_config = {"from_attributes": True}


@router.post("/calcular-detalhado", response_model=DREDetalheResponse)
async def calcular_dre_detalhado(
    request: CalcularDREDetalhadadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        canal=request.canal
    )
    
    return dre


@router.post("/consolidado")
async def calcular_dre_consolidado(
    request: dict,  # {data_inicio, data_fim, canais: [lista de canais]}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    
    data_inicio = date.fromisoformat(request.get('data_inicio'))
    data_fim = date.fromisoformat(request.get('data_fim'))
    canais = request.get('canais', [])
    
    service = DREDetalhadaService(db)
    resultado = service.calcular_dre_consolidado(
        usuario_id=current_user.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        canais=canais
    )
    
    return resultado


class AlocarDespesaRequest(BaseModel):
    data_inicio: date
    data_fim: date
    categoria: str  # 'aluguel', 'salário', 'internet', etc
    valor_total: float
    modo: str  # 'proporcional' ou 'manual'
    canais: List[str]
    usar_faturamento: bool = True
    alocacao_manual: Optional[dict] = None  # Se modo='manual'


@router.post("/alocar-despesa")
async def alocar_despesa(
    request: AlocarDespesaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        usar_faturamento=request.usar_faturamento
    )
    
    return {
        'id': alocacao.id,
        'mensagem': f'Despesa de {request.categoria} alocada com sucesso',
        'modo': request.modo,
        'canais': request.canais
    }
