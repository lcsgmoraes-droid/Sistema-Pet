"""
Rotas para Fechamento Mensal do Simples Nacional
"""

from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.auth import get_current_user
from app.models import User
from app.db import get_session
from app.simples_nacional_models import SimplesNacionalMensal
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.ia.aba7_models import DREPeriodo
from app.financeiro_models import ContaPagar, CategoriaFinanceira
from app.services.fechamento_simples_service import fechar_simples_mensal
from sqlalchemy import func


router = APIRouter(prefix="/simples", tags=["Simples Nacional - Fechamento Mensal"])


# ============================================================================
# SCHEMAS
# ============================================================================

class FechamentoResponse(BaseModel):
    mes: int
    ano: int
    faturamento_sistema: float
    faturamento_contador: Optional[float] = None
    imposto_estimado: float
    imposto_real: Optional[float] = None
    aliquota_efetiva: Optional[float] = None  # percentual
    aliquota_sugerida: Optional[float] = None  # percentual
    fechado: bool = False


class FecharMesRequest(BaseModel):
    mes: int
    ano: int
    faturamento_contador: Optional[float] = None
    imposto_real: Optional[float] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/fechamento", response_model=FechamentoResponse)
def buscar_fechamento(
    mes: int,
    ano: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Busca os dados de fechamento do Simples Nacional para um mês específico.
    
    Retorna:
    - Faturamento do sistema (NFs autorizadas)
    - Faturamento informado pelo contador (se houver)
    - Imposto estimado (provisão do DRE)
    - Imposto real (DAS pago)
    - Alíquota efetiva calculada
    - Alíquota sugerida para próximo mês
    """
    
    tenant_id = current_user.tenant_id
    
    # Buscar ou criar registro mensal
    registro = (
        db.query(SimplesNacionalMensal)
        .filter(
            SimplesNacionalMensal.tenant_id == tenant_id,
            SimplesNacionalMensal.mes == mes,
            SimplesNacionalMensal.ano == ano
        )
        .first()
    )
    
    # Se não existe, cria temporariamente para visualização (sem commit)
    if not registro:
        # Buscar dados do DRE
        periodo_dre = (
            db.query(DREPeriodo)
            .filter(
                DREPeriodo.mes == mes,
                DREPeriodo.ano == ano
            )
            .first()
        )
        
        faturamento_sistema = float(periodo_dre.receita_bruta) if periodo_dre and periodo_dre.receita_bruta else 0.0
        imposto_estimado = float(periodo_dre.impostos) if periodo_dre and periodo_dre.impostos else 0.0
        
        # Buscar DAS pago
        categoria_das = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.tenant_id == tenant_id,
                CategoriaFinanceira.nome.ilike("%DAS%")
            )
            .first()
        )
        
        imposto_real = None
        if categoria_das:
            das_pago = (
                db.query(func.coalesce(func.sum(ContaPagar.valor_original), Decimal("0")))
                .filter(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.categoria_id == categoria_das.id,
                    extract('month', ContaPagar.data_emissao) == mes,
                    extract('year', ContaPagar.data_emissao) == ano,
                    ContaPagar.status == "Pago"
                )
                .scalar()
            )
            
            if das_pago and das_pago > 0:
                imposto_real = float(das_pago)
        
        return FechamentoResponse(
            mes=mes,
            ano=ano,
            faturamento_sistema=faturamento_sistema,
            faturamento_contador=None,
            imposto_estimado=imposto_estimado,
            imposto_real=imposto_real,
            aliquota_efetiva=None,
            aliquota_sugerida=None,
            fechado=False
        )
    
    # Retornar dados do registro existente
    aliquota_efetiva_pct = float(registro.aliquota_efetiva * 100) if registro.aliquota_efetiva else None
    aliquota_sugerida_pct = float(registro.aliquota_sugerida * 100) if registro.aliquota_sugerida else None
    
    return FechamentoResponse(
        mes=registro.mes,
        ano=registro.ano,
        faturamento_sistema=float(registro.faturamento_sistema or 0),
        faturamento_contador=float(registro.faturamento_contador) if registro.faturamento_contador else None,
        imposto_estimado=float(registro.imposto_estimado or 0),
        imposto_real=float(registro.imposto_real) if registro.imposto_real else None,
        aliquota_efetiva=aliquota_efetiva_pct,
        aliquota_sugerida=aliquota_sugerida_pct,
        fechado=registro.fechado
    )


@router.post("/fechar")
def fechar_mes(
    payload: FecharMesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Fecha o mês do Simples Nacional.
    
    - Calcula alíquota efetiva
    - Gera sugestão de alíquota para próximo mês
    - Atualiza configuração fiscal da empresa
    - Registra histórico
    """
    
    tenant_id = current_user.tenant_id
    
    # Verificar se Simples está ativo
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    if not config or not config.simples_ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simples Nacional não está ativo na configuração fiscal"
        )
    
    # Converter faturamento_contador e imposto_real para Decimal
    faturamento_contador_decimal = None
    if payload.faturamento_contador is not None:
        faturamento_contador_decimal = Decimal(str(payload.faturamento_contador))
    
    # Se imposto_real for informado, atualizar o registro antes de fechar
    if payload.imposto_real is not None:
        # Buscar ou criar registro
        registro = (
            db.query(SimplesNacionalMensal)
            .filter(
                SimplesNacionalMensal.tenant_id == tenant_id,
                SimplesNacionalMensal.mes == payload.mes,
                SimplesNacionalMensal.ano == payload.ano
            )
            .first()
        )
        
        if not registro:
            registro = SimplesNacionalMensal(
                tenant_id=tenant_id,
                mes=payload.mes,
                ano=payload.ano
            )
            db.add(registro)
        
        registro.imposto_real = Decimal(str(payload.imposto_real))
        db.commit()
    
    # Fechar mês
    resultado = fechar_simples_mensal(
        db=db,
        tenant_id=tenant_id,
        mes=payload.mes,
        ano=payload.ano,
        faturamento_contador=faturamento_contador_decimal
    )
    
    return resultado


@router.post("/reabrir")
def reabrir_mes(
    mes: int,
    ano: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Reabre um fechamento mensal para ajustes.
    """
    
    tenant_id = current_user.tenant_id
    
    from app.services.fechamento_simples_service import reabrir_simples_mensal
    
    resultado = reabrir_simples_mensal(
        db=db,
        tenant_id=tenant_id,
        mes=mes,
        ano=ano
    )
    
    if not resultado["sucesso"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resultado["motivo"]
        )
    
    return resultado
