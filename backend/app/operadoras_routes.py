"""
ROTAS DE OPERADORAS DE CARTÃO
Gerenciamento de operadoras (Stone, Cielo, Rede, Getnet, Sumup, etc)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.operadoras_models import OperadoraCartao
from app.vendas_models import VendaPagamento

router = APIRouter(prefix="/operadoras-cartao", tags=["Operadoras de Cartão"])


# ============================================================================
# SCHEMAS
# ============================================================================

class OperadoraCartaoCreate(BaseModel):
    """Schema para criação de operadora"""
    nome: str = Field(..., min_length=1, max_length=100, description="Nome da operadora")
    codigo: Optional[str] = Field(None, max_length=50, description="Código da operadora (STONE, CIELO, etc)")
    max_parcelas: int = Field(12, ge=1, le=24, description="Máximo de parcelas permitidas (1-24)")
    padrao: bool = Field(False, description="Se é a operadora padrão do tenant")
    ativo: bool = Field(True, description="Se a operadora está ativa")
    
    # Taxas
    taxa_debito: Optional[float] = Field(None, ge=0, le=100, description="Taxa de débito (%)")
    taxa_credito_vista: Optional[float] = Field(None, ge=0, le=100, description="Taxa de crédito à vista (%)")
    taxa_credito_parcelado: Optional[float] = Field(None, ge=0, le=100, description="Taxa de crédito parcelado (%)")
    
    # API
    api_enabled: bool = Field(False, description="Se integração API está habilitada")
    api_endpoint: Optional[str] = Field(None, max_length=255, description="Endpoint da API")
    api_token_encrypted: Optional[str] = Field(None, description="Token criptografado da API")
    
    # UI
    cor: Optional[str] = Field(None, max_length=7, description="Cor hex (#RRGGBB)")
    icone: Optional[str] = Field(None, max_length=50, description="Nome do ícone Lucide")


class OperadoraCartaoUpdate(BaseModel):
    """Schema para atualização de operadora"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    codigo: Optional[str] = Field(None, max_length=50)
    max_parcelas: Optional[int] = Field(None, ge=1, le=24)
    padrao: Optional[bool] = None
    ativo: Optional[bool] = None
    taxa_debito: Optional[float] = Field(None, ge=0, le=100)
    taxa_credito_vista: Optional[float] = Field(None, ge=0, le=100)
    taxa_credito_parcelado: Optional[float] = Field(None, ge=0, le=100)
    api_enabled: Optional[bool] = None
    api_endpoint: Optional[str] = Field(None, max_length=255)
    api_token_encrypted: Optional[str] = None
    cor: Optional[str] = Field(None, max_length=7)
    icone: Optional[str] = Field(None, max_length=50)


class OperadoraCartaoResponse(BaseModel):
    """Schema de resposta de operadora"""
    id: int
    tenant_id: str
    nome: str
    codigo: Optional[str]
    max_parcelas: int
    padrao: bool
    ativo: bool
    taxa_debito: Optional[float]
    taxa_credito_vista: Optional[float]
    taxa_credito_parcelado: Optional[float]
    api_enabled: bool
    api_endpoint: Optional[str]
    cor: Optional[str]
    icone: Optional[str]
    user_id: int
    created_at: str
    updated_at: str
    
    model_config = {"from_attributes": True}


# ============================================================================
# VALIDAÇÕES (ALERTAS CRÍTICOS)
# ============================================================================

def validar_operadora_padrao_obrigatoria(
    db: Session,
    tenant_id: str,
    operadora_id: Optional[int] = None,
    nova_padrao: bool = False
) -> None:
    """
    ⚠️ ALERTA 2: Garante que sempre exista pelo menos 1 operadora padrão ativa
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        operadora_id: ID da operadora sendo modificada (None para novas)
        nova_padrao: Se está marcando como padrão
    
    Raises:
        HTTPException 400: Se tentativa deixar o tenant sem operadora padrão
    """
    # Se está marcando como padrão, tudo certo (sempre terá pelo menos 1)
    if nova_padrao:
        return
    
    # Conta quantas operadoras padrão ativas existem (excluindo a atual se for update)
    query = db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.tenant_id == tenant_id,
            OperadoraCartao.padrao == True,
            OperadoraCartao.ativo == True
        )
    )
    
    if operadora_id:
        query = query.filter(OperadoraCartao.id != operadora_id)
    
    total_padroes = query.count()
    
    if total_padroes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="❌ OPERADORA PADRÃO OBRIGATÓRIA: Não é possível desativar ou remover a única operadora padrão. "
                   "Marque outra operadora como padrão antes de desativar esta."
        )


def validar_vendas_vinculadas(db: Session, operadora_id: int) -> None:
    """
    ⚠️ ALERTA 3: Impede exclusão de operadora com vendas vinculadas
    
    Args:
        db: Sessão do banco
        operadora_id: ID da operadora
    
    Raises:
        HTTPException 400: Se existir vendas vinculadas à operadora
    """
    total_vendas = db.query(VendaPagamento).filter(
        VendaPagamento.operadora_id == operadora_id
    ).count()
    
    if total_vendas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"❌ OPERADORA COM VENDAS: Não é possível excluir operadora com {total_vendas} venda(s) vinculada(s). "
                   f"Desative a operadora ao invés de excluir para manter histórico."
        )


def desmarcar_outras_operadoras_padrao(db: Session, tenant_id: str, operadora_id: int) -> None:
    """
    Desmarca todas as outras operadoras como padrão quando uma é marcada como padrão
    Garante que apenas 1 operadora seja padrão por vez
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        operadora_id: ID da operadora sendo marcada como padrão
    """
    db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.tenant_id == tenant_id,
            OperadoraCartao.id != operadora_id
        )
    ).update({"padrao": False})
    db.commit()


# ============================================================================
# ROTAS
# ============================================================================

@router.get("", response_model=List[OperadoraCartaoResponse])
def listar_operadoras(
    apenas_ativas: bool = False,
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as operadoras de cartão do tenant
    
    Query Parameters:
        - apenas_ativas: Se True, retorna apenas operadoras ativas
    """
    current_user, tenant_id = current_user_tenant
    
    query = db.query(OperadoraCartao).filter(
        OperadoraCartao.tenant_id == tenant_id
    )
    
    if apenas_ativas:
        query = query.filter(OperadoraCartao.ativo == True)
    
    operadoras = query.order_by(
        OperadoraCartao.padrao.desc(),  # Padrão primeiro
        OperadoraCartao.nome.asc()
    ).all()
    
    return [op.to_dict() for op in operadoras]


@router.get("/padrao", response_model=OperadoraCartaoResponse)
def obter_operadora_padrao(
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """
    Retorna a operadora padrão do tenant
    
    Usado pelo PDV para pré-selecionar a operadora ao registrar venda com cartão
    """
    current_user, tenant_id = current_user_tenant
    
    operadora = db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.tenant_id == tenant_id,
            OperadoraCartao.padrao == True,
            OperadoraCartao.ativo == True
        )
    ).first()
    
    if not operadora:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="❌ Nenhuma operadora padrão encontrada. Configure uma operadora como padrão."
        )
    
    return operadora.to_dict()


@router.get("/{operadora_id}", response_model=OperadoraCartaoResponse)
def obter_operadora(
    operadora_id: int,
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """Retorna uma operadora específica"""
    current_user, tenant_id = current_user_tenant
    
    operadora = db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.id == operadora_id,
            OperadoraCartao.tenant_id == tenant_id
        )
    ).first()
    
    if not operadora:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="❌ Operadora não encontrada"
        )
    
    return operadora.to_dict()


@router.post("", response_model=OperadoraCartaoResponse, status_code=status.HTTP_201_CREATED)
def criar_operadora(
    operadora_data: OperadoraCartaoCreate,
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """
    Cria nova operadora de cartão
    
    Validações:
    - ⚠️ ALERTA 2: Se marcar como padrão, desmarca as outras
    """
    current_user, tenant_id = current_user_tenant
    
    # Se marcar como padrão, desmarca as outras
    if operadora_data.padrao:
        desmarcar_outras_operadoras_padrao(db, tenant_id, operadora_id=0)
    
    # Cria operadora
    nova_operadora = OperadoraCartao(
        tenant_id=tenant_id,
        user_id=current_user.id,
        **operadora_data.model_dump()
    )
    
    db.add(nova_operadora)
    db.commit()
    db.refresh(nova_operadora)
    
    return nova_operadora.to_dict()


@router.put("/{operadora_id}", response_model=OperadoraCartaoResponse)
def atualizar_operadora(
    operadora_id: int,
    operadora_data: OperadoraCartaoUpdate,
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """
    Atualiza operadora existente
    
    Validações:
    - ⚠️ ALERTA 2: Não permite desmarcar padrão se for a única
    - Se marcar como padrão, desmarca as outras
    """
    current_user, tenant_id = current_user_tenant
    
    # Busca operadora
    operadora = db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.id == operadora_id,
            OperadoraCartao.tenant_id == tenant_id
        )
    ).first()
    
    if not operadora:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="❌ Operadora não encontrada"
        )
    
    # Se está tentando desmarcar como padrão ou desativar, valida
    if (operadora_data.padrao is False or operadora_data.ativo is False) and operadora.padrao:
        validar_operadora_padrao_obrigatoria(db, tenant_id, operadora_id)
    
    # Se está marcando como padrão, desmarca as outras
    if operadora_data.padrao is True:
        desmarcar_outras_operadoras_padrao(db, tenant_id, operadora_id)
    
    # Atualiza campos
    update_data = operadora_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operadora, field, value)
    
    db.commit()
    db.refresh(operadora)
    
    return operadora.to_dict()


@router.delete("/{operadora_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_operadora(
    operadora_id: int,
    db: Session = Depends(get_session),
    current_user_tenant: tuple = Depends(get_current_user_and_tenant)
):
    """
    Exclui operadora (soft delete - apenas marca como inativa)
    
    Validações:
    - ⚠️ ALERTA 2: Não permite excluir se for a única operadora padrão ativa
    - ⚠️ ALERTA 3: Não permite excluir se tiver vendas vinculadas
    """
    current_user, tenant_id = current_user_tenant
    
    # Busca operadora
    operadora = db.query(OperadoraCartao).filter(
        and_(
            OperadoraCartao.id == operadora_id,
            OperadoraCartao.tenant_id == tenant_id
        )
    ).first()
    
    if not operadora:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="❌ Operadora não encontrada"
        )
    
    # ⚠️ ALERTA 3: Verifica se tem vendas vinculadas
    validar_vendas_vinculadas(db, operadora_id)
    
    # ⚠️ ALERTA 2: Valida se não é a única operadora padrão
    if operadora.padrao:
        validar_operadora_padrao_obrigatoria(db, tenant_id, operadora_id)
    
    # Soft delete: apenas marca como inativa
    operadora.ativo = False
    db.commit()
    
    return None
