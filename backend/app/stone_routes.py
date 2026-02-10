"""
Rotas para integração com Stone
Endpoints para processar pagamentos PIX e Cartão via Stone
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .stone_api_client import StoneAPIClient
from .stone_models import StoneTransaction, StoneTransactionLog, StoneConfig
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stone", tags=["Stone Payments"])


# ==========================================
# SCHEMAS PYDANTIC
# ==========================================

class StoneConfigSchema(BaseModel):
    """Schema para configuração Stone"""
    client_id: str
    client_secret: str
    merchant_id: str
    webhook_secret: Optional[str] = None
    sandbox: bool = True
    enable_pix: bool = True
    enable_credit_card: bool = True
    enable_debit_card: bool = False
    max_installments: int = 12
    webhook_url: Optional[str] = None


class CreatePixPaymentSchema(BaseModel):
    """Schema para criar pagamento PIX"""
    amount: Decimal = Field(..., gt=0, description="Valor em reais")
    description: str = Field(..., min_length=1, max_length=500)
    external_id: str = Field(..., description="ID único do seu sistema")
    customer_name: Optional[str] = None
    customer_document: Optional[str] = None
    customer_email: Optional[str] = None
    expiration_minutes: int = Field(default=30, ge=5, le=1440)
    venda_id: Optional[int] = None
    conta_receber_id: Optional[int] = None


class CreateCardPaymentSchema(BaseModel):
    """Schema para criar pagamento com cartão"""
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    external_id: str
    card_number: str = Field(..., min_length=13, max_length=19)
    card_holder_name: str
    card_expiration_date: str = Field(..., pattern=r"^\d{2}/\d{2}$")  # MM/YY
    card_cvv: str = Field(..., min_length=3, max_length=4)
    installments: int = Field(default=1, ge=1, le=12)
    customer_name: Optional[str] = None
    customer_document: Optional[str] = None
    customer_email: Optional[str] = None
    venda_id: Optional[int] = None
    conta_receber_id: Optional[int] = None


class CancelPaymentSchema(BaseModel):
    """Schema para cancelar pagamento"""
    reason: Optional[str] = None


class RefundPaymentSchema(BaseModel):
    """Schema para estornar pagamento"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Valor a estornar (null = total)")
    reason: Optional[str] = None


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def get_stone_client(db: Session, tenant_id: int) -> StoneAPIClient:
    """Obtém cliente Stone configurado para o tenant"""
    config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == tenant_id,
        StoneConfig.active == True
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração Stone não encontrada. Configure primeiro em /api/stone/config"
        )
    
    return StoneAPIClient(
        client_id=config.client_id,
        client_secret=config.client_secret,
        merchant_id=config.merchant_id,
        sandbox=config.sandbox
    )


def registrar_log(
    db: Session,
    transaction_id: int,
    event_type: str,
    event_source: str,
    description: str,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    webhook_data: Optional[dict] = None,
    error_details: Optional[dict] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None
):
    """Registra um log de evento"""
    log = StoneTransactionLog(
        transaction_id=transaction_id,
        event_type=event_type,
        event_source=event_source,
        description=description,
        old_status=old_status,
        new_status=new_status,
        webhook_data=webhook_data,
        error_details=error_details,
        user_id=user_id,
        tenant_id=tenant_id
    )
    db.add(log)
    db.commit()


# ==========================================
# CONFIGURAÇÃO
# ==========================================

@router.post("/config")
def configurar_stone(
    config_data: StoneConfigSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Configura credenciais Stone para o tenant
    
    **Importante:** Guarde suas credenciais com segurança!
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']
    
    # Verifica se já existe configuração
    existing_config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == tenant_id
    ).first()
    
    if existing_config:
        # Atualiza configuração existente
        for key, value in config_data.dict().items():
            setattr(existing_config, key, value)
        existing_config.updated_at = datetime.utcnow()
        config = existing_config
    else:
        # Cria nova configuração
        config = StoneConfig(
            **config_data.dict(),
            tenant_id=tenant_id,
            user_id=current_user['id']
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    
    logger.info(f"Configuração Stone criada/atualizada para tenant {tenant_id}")
    
    return {
        "success": True,
        "message": "Configuração Stone salva com sucesso",
        "config": config.to_dict()
    }


@router.get("/config")
def obter_config_stone(
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Retorna configuração Stone do tenant (sem expor secrets)"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == current_user['tenant_id']
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração Stone não encontrada"
        )
    
    return config.to_dict()


# ==========================================
# PAGAMENTOS PIX
# ==========================================

@router.post("/payments/pix")
async def criar_pagamento_pix(
    payment_data: CreatePixPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cria um pagamento via PIX
    
    Retorna QR Code e código Pix Copia e Cola para o cliente pagar
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']
    
    # Verifica se external_id já existe
    existing = db.query(StoneTransaction).filter(
        StoneTransaction.external_id == payment_data.external_id,
        StoneTransaction.tenant_id == tenant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pagamento com external_id '{payment_data.external_id}' já existe"
        )
    
    # Obtém cliente Stone
    stone_client = get_stone_client(db, tenant_id)
    
    try:
        # Cria pagamento na Stone
        stone_response = await stone_client.criar_pagamento_pix(
            amount=payment_data.amount,
            description=payment_data.description,
            external_id=payment_data.external_id,
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            expiration_minutes=payment_data.expiration_minutes
        )
        
        # Salva transação no banco
        transaction = StoneTransaction(
            stone_payment_id=stone_response['id'],
            external_id=payment_data.external_id,
            venda_id=payment_data.venda_id,
            conta_receber_id=payment_data.conta_receber_id,
            payment_method='pix',
            amount=payment_data.amount,
            description=payment_data.description,
            status='pending',
            stone_status=stone_response.get('status'),
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            pix_qr_code=stone_response.get('pix', {}).get('qr_code'),
            pix_qr_code_url=stone_response.get('pix', {}).get('qr_code_url'),
            pix_copy_paste=stone_response.get('pix', {}).get('copy_paste'),
            pix_expiration=datetime.utcnow() + timedelta(minutes=payment_data.expiration_minutes),
            stone_response=stone_response,
            tenant_id=tenant_id,
            user_id=current_user['id']
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # Registra log
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_created',
            event_source='manual',
            description=f'Pagamento PIX criado - R$ {payment_data.amount}',
            new_status='pending',
            user_id=current_user['id'],
            tenant_id=tenant_id
        )
        
        logger.info(f"Pagamento PIX criado: {transaction.id} - R$ {payment_data.amount}")
        
        return {
            "success": True,
            "message": "Pagamento PIX criado com sucesso",
            "transaction": transaction.to_dict(),
            "pix": {
                "qr_code": transaction.pix_qr_code,
                "qr_code_url": transaction.pix_qr_code_url,
                "copy_paste": transaction.pix_copy_paste,
                "expiration": transaction.pix_expiration.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar pagamento PIX: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar pagamento PIX: {str(e)}"
        )


# ==========================================
# PAGAMENTOS CARTÃO
# ==========================================

@router.post("/payments/card")
async def criar_pagamento_cartao(
    payment_data: CreateCardPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cria um pagamento via cartão de crédito/débito
    
    **Atenção:** Dados do cartão são sensíveis. Use HTTPS!
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']
    
    # Verifica se external_id já existe
    existing = db.query(StoneTransaction).filter(
        StoneTransaction.external_id == payment_data.external_id,
        StoneTransaction.tenant_id == tenant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pagamento com external_id '{payment_data.external_id}' já existe"
        )
    
    # Obtém cliente Stone
    stone_client = get_stone_client(db, tenant_id)
    
    try:
        # Cria pagamento na Stone
        stone_response = await stone_client.criar_pagamento_cartao(
            amount=payment_data.amount,
            description=payment_data.description,
            external_id=payment_data.external_id,
            card_number=payment_data.card_number,
            card_holder_name=payment_data.card_holder_name,
            card_expiration_date=payment_data.card_expiration_date,
            card_cvv=payment_data.card_cvv,
            installments=payment_data.installments,
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email
        )
        
        # Extrai dados do cartão (mascarados)
        card_data = stone_response.get('card', {})
        
        # Salva transação no banco
        transaction = StoneTransaction(
            stone_payment_id=stone_response['id'],
            external_id=payment_data.external_id,
            venda_id=payment_data.venda_id,
            conta_receber_id=payment_data.conta_receber_id,
            payment_method='credit_card',
            amount=payment_data.amount,
            description=payment_data.description,
            installments=payment_data.installments,
            status=stone_response.get('status', 'pending'),
            stone_status=stone_response.get('status'),
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            card_brand=card_data.get('brand'),
            card_last_digits=card_data.get('last_digits'),
            fee_amount=Decimal(stone_response.get('fee_amount', 0)) / 100,
            net_amount=Decimal(stone_response.get('net_amount', 0)) / 100,
            stone_response=stone_response,
            tenant_id=tenant_id,
            user_id=current_user['id']
        )
        
        # Se aprovado imediatamente, registra data de pagamento
        if stone_response.get('status') == 'approved':
            transaction.paid_at = datetime.utcnow()
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # Registra log
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_created',
            event_source='manual',
            description=f'Pagamento Cartão criado - R$ {payment_data.amount} - {payment_data.installments}x',
            new_status=transaction.status,
            user_id=current_user['id'],
            tenant_id=tenant_id
        )
        
        logger.info(f"Pagamento Cartão criado: {transaction.id} - R$ {payment_data.amount}")
        
        return {
            "success": True,
            "message": "Pagamento processado com sucesso",
            "transaction": transaction.to_dict(),
            "status": transaction.status
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar pagamento Cartão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar pagamento: {str(e)}"
        )


# ==========================================
# CONSULTAS
# ==========================================

@router.get("/payments/{transaction_id}")
async def consultar_pagamento(
    transaction_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Consulta status atualizado de um pagamento"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada"
        )
    
    # Consulta Stone para obter status atualizado
    stone_client = get_stone_client(db, current_user['tenant_id'])
    
    try:
        stone_response = await stone_client.consultar_pagamento(transaction.stone_payment_id)
        
        # Atualiza status se mudou
        old_status = transaction.status
        new_status = stone_response.get('status')
        
        if old_status != new_status:
            transaction.status = new_status
            transaction.stone_status = new_status
            transaction.stone_response = stone_response
            transaction.updated_at = datetime.utcnow()
            
            # Atualiza datas específicas
            if new_status == 'approved' and not transaction.paid_at:
                transaction.paid_at = datetime.utcnow()
            elif new_status == 'cancelled' and not transaction.cancelled_at:
                transaction.cancelled_at = datetime.utcnow()
            elif new_status == 'refunded' and not transaction.refunded_at:
                transaction.refunded_at = datetime.utcnow()
            
            db.commit()
            db.refresh(transaction)
            
            # Registra mudança de status
            registrar_log(
                db=db,
                transaction_id=transaction.id,
                event_type='status_change',
                event_source='api_call',
                description=f'Status atualizado via API',
                old_status=old_status,
                new_status=new_status,
                user_id=current_user['id'],
                tenant_id=current_user['tenant_id']
            )
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "stone_data": stone_response
        }
        
    except Exception as e:
        logger.error(f"Erro ao consultar pagamento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar pagamento: {str(e)}"
        )


@router.get("/payments")
def listar_pagamentos(
    status_filter: Optional[str] = None,
    payment_method: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Lista pagamentos com filtros"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    query = db.query(StoneTransaction).filter(
        StoneTransaction.tenant_id == current_user['tenant_id']
    )
    
    if status_filter:
        query = query.filter(StoneTransaction.status == status_filter)
    
    if payment_method:
        query = query.filter(StoneTransaction.payment_method == payment_method)
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(StoneTransaction.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(StoneTransaction.created_at <= end)
        except ValueError:
            pass
    
    total = query.count()
    transactions = query.order_by(StoneTransaction.created_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": [t.to_dict() for t in transactions]
    }


# ==========================================
# CANCELAMENTOS E ESTORNOS
# ==========================================

@router.post("/payments/{transaction_id}/cancel")
async def cancelar_pagamento(
    transaction_id: int,
    cancel_data: CancelPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Cancela um pagamento pendente"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    
    if transaction.status not in ['pending', 'processing']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível cancelar pagamento com status '{transaction.status}'"
        )
    
    stone_client = get_stone_client(db, current_user['tenant_id'])
    
    try:
        result = await stone_client.cancelar_pagamento(
            payment_id=transaction.stone_payment_id,
            reason=cancel_data.reason
        )
        
        old_status = transaction.status
        transaction.status = 'cancelled'
        transaction.cancelled_at = datetime.utcnow()
        transaction.updated_at = datetime.utcnow()
        db.commit()
        
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_cancelled',
            event_source='manual',
            description=cancel_data.reason or 'Pagamento cancelado',
            old_status=old_status,
            new_status='cancelled',
            user_id=current_user['id'],
            tenant_id=current_user['tenant_id']
        )
        
        return {"success": True, "message": "Pagamento cancelado com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao cancelar pagamento: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/payments/{transaction_id}/refund")
async def estornar_pagamento(
    transaction_id: int,
    refund_data: RefundPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Estorna um pagamento aprovado (total ou parcial)"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    
    if transaction.status != 'approved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apenas pagamentos aprovados podem ser estornados"
        )
    
    stone_client = get_stone_client(db, current_user['tenant_id'])
    
    try:
        result = await stone_client.estornar_pagamento(
            payment_id=transaction.stone_payment_id,
            amount=refund_data.amount,
            reason=refund_data.reason
        )
        
        old_status = transaction.status
        transaction.status = 'refunded'
        transaction.refunded_at = datetime.utcnow()
        transaction.updated_at = datetime.utcnow()
        db.commit()
        
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_refunded',
            event_source='manual',
            description=refund_data.reason or f'Estorno de R$ {refund_data.amount or transaction.amount}',
            old_status=old_status,
            new_status='refunded',
            user_id=current_user['id'],
            tenant_id=current_user['tenant_id']
        )
        
        return {"success": True, "message": "Pagamento estornado com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao estornar pagamento: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# WEBHOOK (Recebe notificações da Stone)
# ==========================================

@router.post("/webhook")
async def receber_webhook_stone(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    """
    Endpoint para receber webhooks da Stone
    
    Configure esta URL no dashboard da Stone:
    https://seu-dominio.com/api/stone/webhook
    """
    # Obtém dados do webhook
    body = await request.body()
    webhook_data = await request.json()
    
    # Obtém signature do header
    signature = request.headers.get('X-Stone-Signature', '')
    
    logger.info(f"Webhook Stone recebido: {webhook_data.get('event')}")
    
    # Identifica a transação
    payment_id = webhook_data.get('payment', {}).get('id')
    
    if not payment_id:
        logger.error("Webhook sem payment_id")
        return {"success": False, "error": "payment_id não encontrado"}
    
    # Busca transação
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.stone_payment_id == payment_id
    ).first()
    
    if not transaction:
        logger.warning(f"Transação não encontrada para payment_id: {payment_id}")
        return {"success": False, "error": "Transação não encontrada"}
    
    # TODO: Validar signature usando webhook_secret do tenant
    # config = db.query(StoneConfig).filter(StoneConfig.tenant_id == transaction.tenant_id).first()
    # if config and config.webhook_secret:
    #     if not StoneAPIClient.validar_webhook_signature(...):
    #         raise HTTPException(status_code=401, detail="Signature inválida")
    
    # Atualiza status
    old_status = transaction.status
    new_status = webhook_data.get('payment', {}).get('status')
    
    transaction.status = new_status
    transaction.stone_status = new_status
    transaction.last_webhook_at = datetime.utcnow()
    transaction.webhook_count += 1
    transaction.stone_response = webhook_data.get('payment')
    
    # Atualiza datas específicas
    if new_status == 'approved' and not transaction.paid_at:
        transaction.paid_at = datetime.utcnow()
    elif new_status == 'cancelled' and not transaction.cancelled_at:
        transaction.cancelled_at = datetime.utcnow()
    elif new_status == 'refunded' and not transaction.refunded_at:
        transaction.refunded_at = datetime.utcnow()
    
    db.commit()
    
    # Registra log do webhook
    registrar_log(
        db=db,
        transaction_id=transaction.id,
        event_type='webhook_received',
        event_source='stone_webhook',
        description=f"Webhook: {webhook_data.get('event')}",
        old_status=old_status,
        new_status=new_status,
        webhook_data=webhook_data,
        tenant_id=transaction.tenant_id
    )
    
    logger.info(f"Webhook processado: Transaction {transaction.id} - {old_status} -> {new_status}")
    
    return {"success": True, "message": "Webhook processado com sucesso"}
