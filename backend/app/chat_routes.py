"""
Rotas API para Chat IA (ABA 6)
Endpoints para conversas e mensagens
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.db import get_session as get_db
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User, UserTenant, Role, RolePermission, Permission
from app.ia.aba6_chat_ia import (
    criar_conversa_service,
    listar_conversas_service,
    enviar_mensagem_service,
    deletar_conversa_service,
    ChatIAService
)
from app.ia.aba6_models import Conversa, MensagemChat


router = APIRouter(prefix="/chat", tags=["Chat IA"])


# ==================== SCHEMAS ====================

class ConversaResponse(BaseModel):
    id: int
    titulo: str | None
    criado_em: datetime
    atualizado_em: datetime
    finalizada: bool
    total_mensagens: int
    
    model_config = {"from_attributes": True}


class MensagemResponse(BaseModel):
    id: int
    tipo: str
    conteudo: str
    criado_em: datetime
    tokens_usados: int
    
    model_config = {"from_attributes": True}


class EnviarMensagemRequest(BaseModel):
    conversa_id: int
    mensagem: str


class ChatResponse(BaseModel):
    conversa_id: int
    mensagem_usuario: Dict[str, Any]
    mensagem_ia: Dict[str, Any]


# ==================== ENDPOINTS ====================

@router.post("/nova-conversa", response_model=ConversaResponse, status_code=status.HTTP_201_CREATED)
async def criar_nova_conversa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova conversa"""
    usuario_id = current_user.id
    
    conversa = criar_conversa_service(db, usuario_id)
    
    return ConversaResponse(
        id=conversa.id,
        titulo=conversa.titulo,
        criado_em=conversa.criado_em,
        atualizado_em=conversa.atualizado_em,
        finalizada=conversa.finalizada,
        total_mensagens=len(conversa.mensagens)
    )


@router.get("/conversas", response_model=List[ConversaResponse])
async def listar_conversas(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista conversas do usuário"""
    usuario_id = current_user.id
    
    conversas = listar_conversas_service(db, usuario_id, limit)
    
    return [
        ConversaResponse(
            id=c.id,
            titulo=c.titulo or "Nova conversa",
            criado_em=c.criado_em,
            atualizado_em=c.atualizado_em,
            finalizada=c.finalizada,
            total_mensagens=len(c.mensagens)
        )
        for c in conversas
    ]


@router.get("/conversa/{conversa_id}/mensagens", response_model=List[MensagemResponse])
async def obter_mensagens(
    conversa_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém mensagens de uma conversa"""
    usuario_id = current_user.id
    service = ChatIAService(db)
    
    # Verificar se conversa pertence ao usuário
    conversa = service.obter_conversa(conversa_id, usuario_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    mensagens = service.obter_historico(conversa_id)
    
    return [
        MensagemResponse(
            id=m.id,
            tipo=m.tipo,
            conteudo=m.conteudo,
            criado_em=m.criado_em,
            tokens_usados=m.tokens_usados or 0
        )
        for m in mensagens
    ]


@router.post("/enviar", response_model=ChatResponse)
async def enviar_mensagem(
    request: EnviarMensagemRequest,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """Envia mensagem e recebe resposta da IA com controle de permissões"""
    current_user, tenant_id = user_and_tenant
    usuario_id = current_user.id
    
    # Verificar se conversa existe e pertence ao usuário
    service = ChatIAService(db)
    conversa = service.obter_conversa(request.conversa_id, usuario_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Buscar permissões do usuário
    user_tenant = db.query(UserTenant).filter(
        UserTenant.user_id == usuario_id,
        UserTenant.tenant_id == tenant_id
    ).first()
    
    user_permissions = []
    role_name = None
    if user_tenant and user_tenant.role_id:
        role = db.query(Role).filter(Role.id == user_tenant.role_id).first()
        if role:
            role_name = role.name
            role_permissions = db.query(RolePermission).filter(
                RolePermission.role_id == role.id
            ).all()
            
            for rp in role_permissions:
                perm = db.query(Permission).filter(
                    Permission.id == rp.permission_id
                ).first()
                if perm:
                    user_permissions.append(perm.code)
    
    # Verificar se a mensagem solicita dados sensíveis (financeiros)
    mensagem_lower = request.mensagem.lower()
    palavras_sensiveis = [
        'faturamento', 'faturei', 'vendas totais', 'lucro', 'margem',
        'quanto vendi', 'total de vendas', 'receita', 'saldo', 
        'contas a pagar', 'contas a receber', 'dre', 'fluxo de caixa',
        'comissão', 'comissões', 'quanto ganhei', 'balanço', 'resultado'
    ]
    
    requer_financeiro = any(palavra in mensagem_lower for palavra in palavras_sensiveis)
    
    # Se solicita dados financeiros mas usuário não tem permissão
    if requer_financeiro:
        tem_permissao = (
            'relatorios.financeiro' in user_permissions or
            'relatorios.gerencial' in user_permissions or
            role_name == 'admin'
        )
        
        if not tem_permissao:
            # Retornar mensagem de permissão negada
            from app.ia.aba6_models import MensagemChat
            from datetime import datetime
            
            msg_usuario = {
                "id": 0,
                "tipo": "usuario",
                "conteudo": request.mensagem,
                "criado_em": datetime.now().isoformat()
            }
            
            msg_ia = {
                "id": 0,
                "tipo": "assistente",
                "conteudo": "🔒 Desculpe, você não tem permissão para acessar informações financeiras e gerenciais do sistema.\n\nPara consultar dados como faturamento, vendas totais, lucros, margens e relatórios financeiros, você precisa da role **Gerente** ou **Admin**.\n\nEntre em contato com seu gerente para solicitar acesso.",
                "criado_em": datetime.now().isoformat()
            }
            
            return ChatResponse(
                conversa_id=request.conversa_id,
                mensagem_usuario=msg_usuario,
                mensagem_ia=msg_ia
            )
    
    # Gerar resposta normalmente se tiver permissão
    resultado = enviar_mensagem_service(
        db,
        usuario_id,
        request.conversa_id,
        request.mensagem
    )
    
    return ChatResponse(
        conversa_id=resultado["conversa_id"],
        mensagem_usuario=resultado["mensagem_usuario"],
        mensagem_ia=resultado["mensagem_ia"]
    )


@router.delete("/conversa/{conversa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conversa(
    conversa_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deleta uma conversa"""
    usuario_id = current_user.id
    
    sucesso = deletar_conversa_service(db, conversa_id, usuario_id)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    return None


@router.get("/contexto-financeiro")
async def obter_contexto_financeiro(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém contexto financeiro do usuário (para debug)"""
    usuario_id = current_user.id
    
    service = ChatIAService(db)
    contexto = service.obter_contexto_financeiro(usuario_id)
    
    return contexto
