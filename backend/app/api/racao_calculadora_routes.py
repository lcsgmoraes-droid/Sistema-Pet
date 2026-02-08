"""
Rotas para Calculadora de Ração
================================
Endpoints internos para cálculo de consumo de ração.

IMPORTANTE:
- Rotas INTERNAS (não expor publicamente)
- Fail-safe (nunca quebra o sistema)
- Multi-tenant preservado
- SEM integração com PDV (por enquanto)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any

from app.db import get_session
from app.auth import get_current_user
from app.produtos_models import Produto
from app.schemas.racao_calculadora import RacaoCalculadoraInput, RacaoCalculadoraOutput
from app.services.racao_calculadora_service import calcular_racao

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal/racao",
    tags=["Calculadora de Ração (Interno)"]
)


@router.post(
    "/calcular",
    response_model=RacaoCalculadoraOutput,
    summary="Calcular consumo de ração",
    description="""
    Calcula consumo diário, durabilidade do pacote e custos de alimentação.
    
    **Endpoint INTERNO** - Não integrado com PDV ainda.
    
    Retorna:
    - Consumo diário em gramas
    - Durabilidade do pacote em dias
    - Custos diário e mensal
    - Observações personalizadas
    - Contexto preparado para futura IA
    """
)
async def calcular_consumo_racao(
    payload: RacaoCalculadoraInput,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Endpoint para calcular consumo de ração.
    
    Args:
        payload: Dados do animal e da ração
        current_user: Usuário autenticado (multi-tenant)
        db: Sessão do banco (não usado ainda, mas preservado para tenant)
    
    Returns:
        RacaoCalculadoraOutput com todos os cálculos
    
    Raises:
        HTTPException 500: Em caso de erro inesperado (fail-safe)
    """
    try:
        # Log da requisição (preserva tenant_id para auditoria)
        tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
        user_id = current_user.id if hasattr(current_user, 'id') else None
        logger.info(
            f"Calculadora de ração chamada - Tenant: {tenant_id}, User: {user_id}, "
            f"Espécie: {payload.especie}, Peso: {payload.peso_kg}kg, Produto ID: {payload.produto_id}"
        )
        
        # 🔍 NOVO: Buscar produto se produto_id fornecido
        tabela_consumo_json = None
        peso_pacote_kg = payload.peso_pacote_kg
        preco_pacote = payload.preco_pacote
        
        if payload.produto_id:
            logger.info(f"🔍 Buscando produto ID {payload.produto_id} no banco...")
            produto = db.query(Produto).filter(
                Produto.id == payload.produto_id,
                Produto.tenant_id == tenant_id
            ).first()
            
            if not produto:
                logger.warning(f"⚠️ Produto ID {payload.produto_id} não encontrado")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produto ID {payload.produto_id} não encontrado"
                )
            
            # Extrair dados do produto
            if produto.peso_embalagem:
                peso_pacote_kg = produto.peso_embalagem
                logger.info(f"✅ Peso da embalagem do produto: {peso_pacote_kg}kg")
            
            if produto.preco_venda:
                preco_pacote = produto.preco_venda
                logger.info(f"✅ Preço do produto: R$ {preco_pacote}")
            
            if produto.tabela_consumo:
                tabela_consumo_json = produto.tabela_consumo
                logger.info(f"✅ Tabela de consumo encontrada (tamanho: {len(tabela_consumo_json)} chars)")
            else:
                logger.info("ℹ️ Produto não tem tabela de consumo cadastrada, usando cálculo genérico")
        
        # Validar peso_pacote_kg e preco_pacote
        if not peso_pacote_kg or peso_pacote_kg <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="peso_pacote_kg é obrigatório e deve ser maior que zero"
            )
        
        if preco_pacote is None or preco_pacote < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preco_pacote é obrigatório e não pode ser negativo"
            )
        
        # Atualizar payload com dados do produto
        payload_dict = payload.model_dump()
        payload_dict['peso_pacote_kg'] = peso_pacote_kg
        payload_dict['preco_pacote'] = preco_pacote
        
        # Chama o serviço de cálculo (fail-safe interno)
        # 🆕 PASSA A TABELA DE CONSUMO
        resultado = calcular_racao(payload_dict, tabela_consumo_json=tabela_consumo_json)
        
        # Valida se houve erro no cálculo
        if resultado.get("consumo_diario_gramas", 0) == 0:
            # Serviço retornou erro, mas ainda é válido (fail-safe)
            logger.warning(f"Cálculo retornou valores zero - possível erro de validação")
        
        # Log do resultado
        logger.info(
            f"Cálculo concluído - Consumo: {resultado.get('consumo_diario_gramas')}g/dia, "
            f"Custo mensal: R$ {resultado.get('custo_mensal')}"
        )
        
        return resultado
        
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
        
    except Exception as e:
        # FAIL-SAFE: Nunca quebra o sistema
        logger.error(f"Erro no endpoint de calculadora de ração: {e}", exc_info=True)
        
        # Retorna erro estruturado mas não quebra
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao calcular consumo de ração. Por favor, tente novamente.",
                "error": str(e),
                "fail_safe": True
            }
        )


@router.get(
    "/info",
    summary="Informações sobre a calculadora",
    description="Retorna informações sobre como usar a calculadora de ração"
)
async def info_calculadora(
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint informativo sobre a calculadora.
    
    Útil para documentação e onboarding de usuários.
    """
    return {
        "nome": "Calculadora de Ração",
        "versao": "1.0.0",
        "descricao": "Calcula consumo diário, durabilidade e custos de alimentação pet",
        "especies_suportadas": ["cao", "gato"],
        "fases_suportadas": ["filhote", "adulto", "idoso"],
        "portes_suportados": ["mini", "pequeno", "medio", "grande"],
        "tipos_racao_suportados": ["standard", "premium", "super_premium"],
        "status": {
            "integracao_pdv": False,
            "integracao_ia": False,
            "metricas": False,
            "automacoes": False
        },
        "exemplo_uso": {
            "especie": "cao",
            "peso_kg": 15.0,
            "fase": "adulto",
            "porte": "medio",
            "tipo_racao": "premium",
            "peso_pacote_kg": 10.5,
            "preco_pacote": 180.00
        }
    }
