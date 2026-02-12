"""
Rotas FastAPI - Configuração Tributária e Cálculo de Impostos
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import date

from app.auth import get_current_user_and_tenant
from app.db import get_session as get_db
from app.ia.aba7_tributacao import CalculadoraTributaria
from app.ia.aba7_extrato_models import ConfiguracaoTributaria


router = APIRouter(prefix="/api/tributacao", tags=["Tributação e Impostos"])


# ===== SCHEMAS =====

class ConfigTributariaSchema(BaseModel):
    regime: str  # 'simples_nacional', 'lucro_presumido', 'lucro_real', 'mei'
    
    # Simples Nacional
    anexo_simples: Optional[str] = None
    faixa_simples: Optional[str] = None
    aliquota_efetiva_simples: Optional[float] = None
    
    # Lucro Presumido
    presuncao_lucro_percentual: Optional[float] = None
    aliquota_irpj: Optional[float] = None
    aliquota_adicional_irpj: Optional[float] = None
    aliquota_csll: Optional[float] = None
    aliquota_pis: Optional[float] = None
    aliquota_cofins: Optional[float] = None
    
    # ICMS/ISS
    estado: Optional[str] = None
    aliquota_icms: Optional[float] = None
    incluir_icms_dre: Optional[bool] = True
    aliquota_iss: Optional[float] = None
    incluir_iss_dre: Optional[bool] = False


class CalculoImpostosRequest(BaseModel):
    receita_bruta: float
    receita_liquida: float
    lucro_operacional: float


class EstimarRegimeRequest(BaseModel):
    receita_bruta_mensal: float
    lucro_operacional_mensal: float


class ConfigTributariaResponse(BaseModel):
    id: int
    usuario_id: int
    regime: str
    anexo_simples: Optional[str]
    faixa_simples: Optional[str]
    aliquota_efetiva_simples: Optional[float]
    presuncao_lucro_percentual: Optional[float]
    aliquota_irpj: Optional[float]
    aliquota_csll: Optional[float]
    aliquota_pis: Optional[float]
    aliquota_cofins: Optional[float]
    estado: Optional[str]
    aliquota_icms: Optional[float]
    incluir_icms_dre: bool
    aliquota_iss: Optional[float]
    incluir_iss_dre: bool
    
    model_config = {"from_attributes": True}


# ===== ENDPOINTS =====

@router.get("/configuracao", response_model=Optional[ConfigTributariaResponse])
def obter_configuracao(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """Busca configuração tributária do usuário atual"""
    current_user, tenant_id = user_and_tenant
    calculadora = CalculadoraTributaria(db)
    config = calculadora.obter_configuracao(tenant_id)
    
    if not config:
        return None
    
    return config


@router.post("/configuracao", response_model=ConfigTributariaResponse)
def salvar_configuracao(
    dados: ConfigTributariaSchema,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """
    Cria ou atualiza configuração tributária
    
    Regimes suportados:
    - simples_nacional: Alíquota única progressiva (4% a 19%)
    - lucro_presumido: PIS, COFINS, IRPJ, CSLL separados
    - lucro_real: Impostos sobre lucro efetivo
    - mei: Valor fixo mensal (R$ 67-71)
    """
    current_user, tenant_id = user_and_tenant
    calculadora = CalculadoraTributaria(db)
    
    config = calculadora.salvar_configuracao(
        tenant_id=tenant_id,
        regime=dados.regime,
        anexo_simples=dados.anexo_simples,
        faixa_simples=dados.faixa_simples,
        aliquota_efetiva_simples=dados.aliquota_efetiva_simples,
        presuncao_lucro_percentual=dados.presuncao_lucro_percentual,
        aliquota_irpj=dados.aliquota_irpj,
        aliquota_adicional_irpj=dados.aliquota_adicional_irpj,
        aliquota_csll=dados.aliquota_csll,
        aliquota_pis=dados.aliquota_pis,
        aliquota_cofins=dados.aliquota_cofins,
        estado=dados.estado,
        aliquota_icms=dados.aliquota_icms,
        incluir_icms_dre=dados.incluir_icms_dre,
        aliquota_iss=dados.aliquota_iss,
        incluir_iss_dre=dados.incluir_iss_dre
    )
    
    return config


@router.post("/calcular")
def calcular_impostos(
    dados: CalculoImpostosRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """
    Calcula impostos baseado no regime configurado
    
    Returns:
        {
            'impostos': 850.50,
            'detalhamento': {
                'simples_nacional': 850.50  # ou 'pis', 'cofins', 'irpj', etc
            },
            'aliquota_efetiva': 8.5,
            'regime': 'simples_nacional'
        }
    """
    current_user, tenant_id = user_and_tenant
    calculadora = CalculadoraTributaria(db)
    
    resultado = calculadora.calcular_impostos(
        tenant_id=tenant_id,
        receita_bruta=dados.receita_bruta,
        receita_liquida=dados.receita_liquida,
        lucro_operacional=dados.lucro_operacional
    )
    
    return resultado


@router.post("/estimar-melhor-regime")
def estimar_melhor_regime(
    dados: EstimarRegimeRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """
    Compara todos os regimes e sugere o mais econômico
    
    Returns:
        {
            'simples_nacional': {'impostos': 1000, 'aliquota': 8.5},
            'lucro_presumido': {'impostos': 1200, 'aliquota': 10.2},
            'lucro_real': {'impostos': 800, 'aliquota': 6.8},
            'recomendacao': 'lucro_real',
            'economia_mensal_estimada': 200,
            'economia_anual_estimada': 2400
        }
    """
    current_user, tenant_id = user_and_tenant
    calculadora = CalculadoraTributaria(db)
    
    resultado = calculadora.estimar_economia_regime(
        tenant_id=tenant_id,
        receita_bruta=dados.receita_bruta_mensal,
        lucro_operacional=dados.lucro_operacional_mensal
    )
    
    return resultado


@router.get("/regimes-disponiveis")
def listar_regimes():
    """Lista todos os regimes tributários disponíveis com descrições"""
    return {
        "regimes": [
            {
                "id": "simples_nacional",
                "nome": "Simples Nacional",
                "descricao": "Regime simplificado com alíquota única progressiva",
                "aliquota_media": "4% a 19% (Anexo I - Comércio)",
                "limite_faturamento": "R$ 4.8 milhões/ano",
                "vantagens": [
                    "Tributação unificada (8 impostos em 1 guia)",
                    "Alíquotas progressivas",
                    "Simplificação burocrática"
                ]
            },
            {
                "id": "lucro_presumido",
                "nome": "Lucro Presumido",
                "descricao": "Impostos calculados sobre percentual presumido da receita",
                "aliquota_media": "~13.33% (8% presunção + tributos)",
                "limite_faturamento": "R$ 78 milhões/ano",
                "vantagens": [
                    "Bom para margens altas",
                    "Menos burocracia que Lucro Real",
                    "Sem obrigatoriedade de escrituração contábil completa"
                ]
            },
            {
                "id": "lucro_real",
                "nome": "Lucro Real",
                "descricao": "Impostos calculados sobre lucro efetivo",
                "aliquota_media": "Variável (depende da margem)",
                "limite_faturamento": "Sem limite",
                "vantagens": [
                    "Ideal para margens baixas ou prejuízo",
                    "Tributação sobre lucro real",
                    "Compensa prejuízos fiscais"
                ]
            },
            {
                "id": "mei",
                "nome": "MEI",
                "descricao": "Microempreendedor Individual",
                "aliquota_media": "Valor fixo mensal (R$ 67-71)",
                "limite_faturamento": "R$ 81 mil/ano",
                "vantagens": [
                    "Valor fixo muito baixo",
                    "Máxima simplificação",
                    "Sem contabilidade obrigatória"
                ]
            }
        ]
    }


@router.get("/anexos-simples")
def listar_anexos_simples():
    """Lista anexos do Simples Nacional com faixas e alíquotas"""
    return {
        "anexos": {
            "Anexo I": {
                "atividade": "Comércio",
                "descricao": "Revenda de mercadorias",
                "faixas": [
                    {"limite": 180000, "aliquota": 4.00},
                    {"limite": 360000, "aliquota": 7.30},
                    {"limite": 720000, "aliquota": 9.50},
                    {"limite": 1800000, "aliquota": 10.70},
                    {"limite": 3600000, "aliquota": 14.30},
                    {"limite": 4800000, "aliquota": 19.00}
                ]
            },
            "Anexo III": {
                "atividade": "Serviços (maioria)",
                "descricao": "Prestação de serviços",
                "faixas": [
                    {"limite": 180000, "aliquota": 6.00},
                    {"limite": 360000, "aliquota": 11.20},
                    {"limite": 720000, "aliquota": 13.50},
                    {"limite": 1800000, "aliquota": 16.00},
                    {"limite": 3600000, "aliquota": 21.00},
                    {"limite": 4800000, "aliquota": 33.00}
                ]
            },
            "Anexo V": {
                "atividade": "Serviços especializados",
                "descricao": "Auditoria, jornalismo, tecnologia",
                "faixas": [
                    {"limite": 180000, "aliquota": 15.50},
                    {"limite": 360000, "aliquota": 18.00},
                    {"limite": 720000, "aliquota": 19.50},
                    {"limite": 1800000, "aliquota": 20.50},
                    {"limite": 3600000, "aliquota": 23.00},
                    {"limite": 4800000, "aliquota": 30.50}
                ]
            }
        }
    }
