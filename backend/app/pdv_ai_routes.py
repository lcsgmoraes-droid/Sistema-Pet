"""
PDV AI Assistant - Endpoints FastAPI

Expõe o sistema de IA contextual para PDV via REST API.

Endpoints:
- POST /api/pdv/ai/sugestoes - Sugestões para venda em andamento
- POST /api/pdv/ai/preview - Preview/simulação sem efeitos colaterais

REGRAS:
- IA NÃO executa ações
- IA NÃO altera vendas
- IA NÃO modifica estoque
- IA apenas SUGERE para o operador
- Máximo 3 sugestões
- Multi-tenant obrigatório
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
import logging

from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import User
from app.ai.pdv_assistant import PDVContext, ItemVendaPDV, PDVAIService
from app.ai.pdv_assistant.models import TipoPDVSugestao, PrioridadeSugestao


logger = logging.getLogger(__name__)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/pdv/ai",
    tags=["PDV - IA Contextual"],
    dependencies=[Depends(get_current_user)]
)


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class ItemVendaRequest(BaseModel):
    """Item de produto na venda em andamento"""
    produto_id: int = Field(..., gt=0, description="ID do produto")
    nome_produto: str = Field(..., min_length=1, max_length=200)
    quantidade: float = Field(..., gt=0)
    valor_unitario: float = Field(..., ge=0)
    valor_total: float = Field(..., ge=0)
    categoria: Optional[str] = Field(None, max_length=100)
    fabricante: Optional[str] = Field(None, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "produto_id": 101,
                "nome_produto": "Ração Premium 15kg",
                "quantidade": 1,
                "valor_unitario": 159.90,
                "valor_total": 159.90,
                "categoria": "Alimentação",
                "fabricante": "Royal Canin"
            }
        }


class SugestoesRequest(BaseModel):
    """Request para gerar sugestões de IA para venda em andamento"""
    venda_id: Optional[int] = Field(None, description="ID da venda (se existir)")
    cliente_id: Optional[int] = Field(None, gt=0, description="ID do cliente identificado")
    cliente_nome: Optional[str] = Field(None, max_length=200)
    itens: List[ItemVendaRequest] = Field(default_factory=list, description="Produtos já adicionados")
    total_parcial: float = Field(0.0, ge=0, description="Total acumulado da venda")
    vendedor_id: int = Field(..., gt=0, description="ID do vendedor")
    vendedor_nome: str = Field(..., min_length=1, max_length=200)
    contexto_extra: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")
    
    @validator('itens')
    def validar_itens(cls, v):
        """Valida lista de itens"""
        # Lista vazia é válida (início da venda)
        if len(v) > 100:
            raise ValueError("Máximo de 100 itens por venda")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "venda_id": 1234,
                "cliente_id": 50,
                "cliente_nome": "Maria Oliveira",
                "itens": [
                    {
                        "produto_id": 101,
                        "nome_produto": "Ração Premium 15kg",
                        "quantidade": 1,
                        "valor_unitario": 159.90,
                        "valor_total": 159.90,
                        "categoria": "Alimentação"
                    }
                ],
                "total_parcial": 159.90,
                "vendedor_id": 1,
                "vendedor_nome": "João Silva",
                "contexto_extra": {}
            }
        }


class PreviewRequest(BaseModel):
    """Request para preview/simulação sem efeitos colaterais"""
    cliente_id: Optional[int] = Field(None, gt=0)
    cliente_nome: Optional[str] = Field(None, max_length=200)
    itens: List[ItemVendaRequest] = Field(default_factory=list)
    vendedor_id: int = Field(..., gt=0)
    vendedor_nome: str = Field(..., min_length=1, max_length=200)
    
    class Config:
        json_schema_extra = {
            "example": {
                "cliente_id": 50,
                "cliente_nome": "Maria Oliveira",
                "itens": [
                    {
                        "produto_id": 101,
                        "nome_produto": "Ração Premium 15kg",
                        "quantidade": 1,
                        "valor_unitario": 159.90,
                        "valor_total": 159.90
                    }
                ],
                "vendedor_id": 1,
                "vendedor_nome": "João Silva"
            }
        }


class SugestaoResponse(BaseModel):
    """Sugestão da IA para o operador do PDV"""
    tipo: str = Field(..., description="Tipo da sugestão (cross_sell, kit, vip, etc)")
    prioridade: str = Field(..., description="Prioridade: alta, media, baixa")
    titulo: str = Field(..., description="Título curto da sugestão")
    mensagem_curta: str = Field(..., description="Mensagem principal (max 200 chars)")
    explicacao: Optional[str] = Field(None, description="Explicação detalhada (opcional)")
    origem: str = Field("insight", description="Origem: insight ou ai")
    confianca: float = Field(..., ge=0.0, le=1.0, description="Nível de confiança (0-1)")
    acionavel: bool = Field(False, description="Se tem ação que operador pode tomar")
    acao_sugerida: Optional[str] = Field(None, description="Ação recomendada")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "kit_vantajoso",
                "prioridade": "alta",
                "titulo": "Kit Mais Vantajoso",
                "mensagem_curta": "Kit Higiene Completa sai 12% mais barato.",
                "explicacao": "O cliente está comprando produtos que fazem parte do Kit Higiene Completa, que oferece 12% de desconto sobre o preço individual.",
                "origem": "insight",
                "confianca": 0.85,
                "acionavel": True,
                "acao_sugerida": "Sugerir kit ao cliente",
                "metadata": {
                    "insight_id": "abc123",
                    "kit_nome": "Kit Higiene Completa",
                    "economia_percentual": 12
                }
            }
        }


class SugestoesResponse(BaseModel):
    """Response com lista de sugestões"""
    sugestoes: List[SugestaoResponse] = Field(default_factory=list)
    quantidade: int = Field(0, description="Quantidade de sugestões retornadas")
    timestamp: datetime = Field(default_factory=datetime.now)
    processamento_ms: Optional[int] = Field(None, description="Tempo de processamento em ms")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sugestoes": [
                    {
                        "tipo": "cliente_vip",
                        "prioridade": "alta",
                        "titulo": "Cliente VIP",
                        "mensagem_curta": "Cliente VIP - 50 compras realizadas.",
                        "origem": "insight",
                        "confianca": 0.90,
                        "acionavel": True,
                        "acao_sugerida": "Oferecer atendimento premium"
                    }
                ],
                "quantidade": 1,
                "timestamp": "2026-01-25T14:30:00",
                "processamento_ms": 150
            }
        }


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def converter_item_request_para_pdv(item: ItemVendaRequest) -> ItemVendaPDV:
    """
    Converte ItemVendaRequest (Pydantic) para ItemVendaPDV (dataclass).
    """
    return ItemVendaPDV(
        produto_id=item.produto_id,
        nome_produto=item.nome_produto,
        quantidade=item.quantidade,
        valor_unitario=Decimal(str(item.valor_unitario)),
        valor_total=Decimal(str(item.valor_total)),
        categoria=item.categoria,
        fabricante=item.fabricante,
    )


def criar_pdv_context(
    request: SugestoesRequest,
    tenant_id: int
) -> PDVContext:
    """
    Cria PDVContext a partir do request.
    """
    itens_pdv = [
        converter_item_request_para_pdv(item)
        for item in request.itens
    ]
    
    return PDVContext(
        tenant_id=tenant_id,
        timestamp=datetime.now(),
        itens=itens_pdv,
        total_parcial=Decimal(str(request.total_parcial)),
        vendedor_id=request.vendedor_id,
        vendedor_nome=request.vendedor_nome,
        cliente_id=request.cliente_id,
        cliente_nome=request.cliente_nome,
        metadata=request.contexto_extra or {},
    )


def criar_pdv_context_preview(
    request: PreviewRequest,
    tenant_id: int
) -> PDVContext:
    """
    Cria PDVContext para preview/simulação.
    """
    itens_pdv = [
        converter_item_request_para_pdv(item)
        for item in request.itens
    ]
    
    # Calcular total
    total = sum(item.valor_total for item in itens_pdv)
    
    return PDVContext(
        tenant_id=tenant_id,
        timestamp=datetime.now(),
        itens=itens_pdv,
        total_parcial=total,
        vendedor_id=request.vendedor_id,
        vendedor_nome=request.vendedor_nome,
        cliente_id=request.cliente_id,
        cliente_nome=request.cliente_nome,
        metadata={"preview": True},
    )


def converter_sugestao_para_response(sugestao) -> SugestaoResponse:
    """
    Converte PDVSugestao (dataclass) para SugestaoResponse (Pydantic).
    """
    return SugestaoResponse(
        tipo=sugestao.tipo.value,
        prioridade=sugestao.prioridade.value,
        titulo=sugestao.titulo,
        mensagem_curta=sugestao.mensagem,
        explicacao=None,  # Pode ser expandido futuramente
        origem="insight",
        confianca=sugestao.confianca,
        acionavel=sugestao.acionavel,
        acao_sugerida=sugestao.acao_sugerida,
        metadata=sugestao.metadata,
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/sugestoes",
    response_model=SugestoesResponse,
    summary="Gerar sugestões IA para venda em andamento",
    description="""
    Retorna sugestões contextuais da IA baseadas na venda em andamento.
    
    **Características:**
    - Analisa produtos já adicionados
    - Considera cliente (se identificado)
    - Consome insights existentes
    - Máximo 3 sugestões
    - NÃO executa ações
    - NÃO altera venda
    
    **Tipos de sugestões:**
    - Cross-sell (produtos complementares)
    - Kit vantajoso (economia)
    - Cliente recorrente (padrão de compra)
    - Cliente inativo (oportunidade)
    - Cliente VIP (atendimento diferenciado)
    - Recompra (oportunidade)
    - Estoque crítico (aviso)
    - Produto popular (destaque)
    """,
    status_code=status.HTTP_200_OK,
)
async def gerar_sugestoes_pdv(
    request: SugestoesRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
) -> SugestoesResponse:
    """
    Gera sugestões da IA para uma venda em andamento.
    
    Args:
        request: Dados da venda em andamento
        db: Sessão do banco de dados
        current_user: Usuário autenticado (tenant)
    
    Returns:
        Lista de sugestões ordenadas por prioridade
    """
    inicio = datetime.now()
    
    try:
        logger.info(
            f"[PDV AI] Gerando sugestões para tenant={current_user.id}, "
            f"vendedor={request.vendedor_nome}, itens={len(request.itens)}"
        )
        
        # Criar contexto do PDV
        pdv_context = criar_pdv_context(request, current_user.id)
        
        # Criar serviço de IA
        service = PDVAIService(db=db, use_mock=True)
        
        # Gerar sugestões (async)
        sugestoes = await service.sugerir_para_pdv(pdv_context)
        
        # Converter para response
        sugestoes_response = [
            converter_sugestao_para_response(s)
            for s in sugestoes
        ]
        
        # Calcular tempo de processamento
        fim = datetime.now()
        tempo_ms = int((fim - inicio).total_seconds() * 1000)
        
        logger.info(
            f"[PDV AI] Geradas {len(sugestoes_response)} sugestões "
            f"em {tempo_ms}ms"
        )
        
        return SugestoesResponse(
            sugestoes=sugestoes_response,
            quantidade=len(sugestoes_response),
            timestamp=datetime.now(),
            processamento_ms=tempo_ms,
        )
        
    except ValueError as e:
        logger.error(f"[PDV AI] Erro de validação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
        
    except Exception as e:
        logger.error(
            f"[PDV AI] Erro ao gerar sugestões: {str(e)}",
            exc_info=True
        )
        # Retornar vazio em caso de erro (não quebrar o PDV)
        return SugestoesResponse(
            sugestoes=[],
            quantidade=0,
            timestamp=datetime.now(),
            processamento_ms=0,
        )


@router.post(
    "/preview",
    response_model=SugestoesResponse,
    summary="Preview de sugestões IA (simulação)",
    description="""
    Simula o que a IA sugeriria para uma combinação de produtos,
    SEM afetar vendas, estoque ou qualquer outro recurso.
    
    **Uso:**
    - Testar diferentes combinações de produtos
    - Ver sugestões antes de adicionar produtos
    - Demonstrações e treinamentos
    
    **Diferenças do /sugestoes:**
    - NÃO usa venda_id
    - NÃO valida estoque
    - Apenas simulação pura
    
    **Garantias:**
    - Zero efeitos colaterais
    - Sem persistência
    - Stateless
    """,
    status_code=status.HTTP_200_OK,
)
async def preview_sugestoes_pdv(
    request: PreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
) -> SugestoesResponse:
    """
    Gera preview de sugestões sem efeitos colaterais.
    
    Args:
        request: Dados da simulação
        db: Sessão do banco de dados
        current_user: Usuário autenticado (tenant)
    
    Returns:
        Lista de sugestões (simulação)
    """
    inicio = datetime.now()
    
    try:
        logger.info(
            f"[PDV AI Preview] Simulação para tenant={current_user.id}, "
            f"itens={len(request.itens)}"
        )
        
        # Criar contexto do PDV (preview)
        pdv_context = criar_pdv_context_preview(request, current_user.id)
        
        # Criar serviço de IA
        service = PDVAIService(db=db, use_mock=True)
        
        # Gerar sugestões (async)
        sugestoes = await service.sugerir_para_pdv(pdv_context)
        
        # Converter para response
        sugestoes_response = [
            converter_sugestao_para_response(s)
            for s in sugestoes
        ]
        
        # Calcular tempo de processamento
        fim = datetime.now()
        tempo_ms = int((fim - inicio).total_seconds() * 1000)
        
        logger.info(
            f"[PDV AI Preview] Simuladas {len(sugestoes_response)} sugestões "
            f"em {tempo_ms}ms"
        )
        
        return SugestoesResponse(
            sugestoes=sugestoes_response,
            quantidade=len(sugestoes_response),
            timestamp=datetime.now(),
            processamento_ms=tempo_ms,
        )
        
    except ValueError as e:
        logger.error(f"[PDV AI Preview] Erro de validação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
        
    except Exception as e:
        logger.error(
            f"[PDV AI Preview] Erro ao gerar preview: {str(e)}",
            exc_info=True
        )
        # Retornar vazio em caso de erro
        return SugestoesResponse(
            sugestoes=[],
            quantidade=0,
            timestamp=datetime.now(),
            processamento_ms=0,
        )


# ============================================================================
# ENDPOINT DE HEALTH CHECK (OPCIONAL)
# ============================================================================

@router.get(
    "/health",
    summary="Health check do PDV AI",
    status_code=status.HTTP_200_OK,
)
async def health_check(
    user_and_tenant = Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Verifica se o serviço de PDV AI está operacional.
    
    Returns:
        Status do serviço
    """
    return {
        "status": "ok",
        "service": "PDV AI Assistant",
        "version": "1.0.0",
        "tenant_id": current_user.id,
        "timestamp": datetime.now().isoformat(),
    }
