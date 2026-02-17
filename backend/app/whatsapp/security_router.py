# ============================================================================
# SPRINT 8: Security & LGPD Router
# Endpoints para gestão de segurança e compliance LGPD
# ============================================================================

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth.core import get_current_user
from app.models import User
from app.whatsapp.security import (
    LGPDService,
    SecurityAuditService,
    WebhookSignatureValidator,
    DataPrivacyConsent,
    DataDeletionRequest
)


router = APIRouter(prefix="/whatsapp/security", tags=["WhatsApp Security & LGPD"])


# ============================================================================
# Schemas
# ============================================================================

class ConsentRequest(BaseModel):
    subject_type: str = Field(..., description="Tipo: customer, user, contact")
    subject_id: str = Field(..., description="ID do titular")
    consent_type: str = Field(..., description="Tipo: whatsapp, marketing, analytics")
    consent_given: bool = Field(..., description="Consentimento dado?")
    consent_text: str = Field(..., description="Texto do termo")
    phone_number: Optional[str] = None


class ConsentCheckRequest(BaseModel):
    subject_id: str
    consent_type: str


class DataDeletionRequestCreate(BaseModel):
    subject_type: str = Field(..., description="Tipo: customer, user")
    subject_id: str = Field(..., description="ID do titular")
    reason: str = Field(..., description="Motivo da solicitação")
    phone_number: Optional[str] = None
    email: Optional[str] = None


class DataDeletionApproval(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


class DataExportRequest(BaseModel):
    subject_id: str
    subject_type: str = "customer"


# ============================================================================
# LGPD Endpoints
# ============================================================================

@router.post("/lgpd/consent")
def record_consent(
    consent_data: ConsentRequest,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    📝 **Registrar Consentimento LGPD**
    
    Registra consentimento explícito do titular dos dados conforme LGPD.
    
    **Tipos de consentimento:**
    - `whatsapp`: Uso do WhatsApp para comunicação
    - `marketing`: Envio de mensagens promocionais
    - `analytics`: Análise de dados para melhoria do serviço
    
    **Obrigatório por lei:** Art. 7º e 8º da LGPD
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    try:
        consent = lgpd_service.record_consent(
            subject_type=consent_data.subject_type,
            subject_id=consent_data.subject_id,
            consent_type=consent_data.consent_type,
            consent_given=consent_data.consent_given,
            consent_text=consent_data.consent_text,
            phone_number=consent_data.phone_number,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {
            "id": consent.id,
            "subject_id": consent.subject_id,
            "consent_type": consent.consent_type,
            "consent_given": consent.consent_given,
            "created_at": consent.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao registrar consentimento: {str(e)}")


@router.post("/lgpd/consent/check")
def check_consent(
    check_data: ConsentCheckRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    ✅ **Verificar Consentimento**
    
    Verifica se há consentimento válido e ativo para determinado tipo.
    
    **Retorna:**
    - `has_consent`: true/false
    - `consent_date`: Data do consentimento (se existir)
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    has_consent = lgpd_service.check_consent(
        subject_id=check_data.subject_id,
        consent_type=check_data.consent_type
    )
    
    return {
        "subject_id": check_data.subject_id,
        "consent_type": check_data.consent_type,
        "has_consent": has_consent
    }


@router.post("/lgpd/consent/revoke")
def revoke_consent(
    check_data: ConsentCheckRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    ❌ **Revogar Consentimento**
    
    Revoga consentimento previamente dado (Direito à Revogação - Art. 8º §5º).
    
    **Efeito:** O sistema deve parar imediatamente o processamento
    relacionado ao tipo de consentimento revogado.
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    revoked = lgpd_service.revoke_consent(
        subject_id=check_data.subject_id,
        consent_type=check_data.consent_type
    )
    
    if not revoked:
        raise HTTPException(404, "Consentimento não encontrado")
    
    return {
        "message": "Consentimento revogado com sucesso",
        "subject_id": check_data.subject_id,
        "consent_type": check_data.consent_type,
        "revoked_at": datetime.utcnow().isoformat()
    }


@router.post("/lgpd/deletion-request")
def request_data_deletion(
    deletion_data: DataDeletionRequestCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ **Solicitar Exclusão de Dados (Direito ao Esquecimento)**
    
    Cria solicitação de exclusão completa dos dados do titular.
    
    **LGPD Art. 18:** Direito à eliminação dos dados pessoais
    
    **Processo:**
    1. Solicitação criada com status `pending`
    2. Revisão por administrador
    3. Aprovação/Rejeição
    4. Exclusão efetiva (se aprovado)
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    try:
        request_obj = lgpd_service.request_data_deletion(
            subject_type=deletion_data.subject_type,
            subject_id=deletion_data.subject_id,
            reason=deletion_data.reason,
            contact_phone=deletion_data.phone_number,
            contact_email=deletion_data.email
        )
        
        return {
            "request_id": request_obj.id,
            "status": request_obj.status,
            "created_at": request_obj.request_date.isoformat(),
            "message": "Solicitação de exclusão criada. Será processada em até 15 dias."
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao criar solicitação: {str(e)}")


@router.get("/lgpd/deletion-requests")
def list_deletion_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    📋 **Listar Solicitações de Exclusão**
    
    Lista todas as solicitações de exclusão de dados.
    
    **Filtros:**
    - `status`: pending, approved, processing, completed, rejected
    """
    
    query = db.query(DataDeletionRequest).filter(
        DataDeletionRequest.tenant_id == str(current_user.tenant_id)
    )
    
    if status:
        query = query.filter(DataDeletionRequest.status == status)
    
    requests = query.order_by(DataDeletionRequest.created_at.desc()).all()
    
    return {
        "requests": [
            {
                "id": req.id,
                "subject_type": req.subject_type,
                "subject_id": req.subject_id,
                "status": req.status,
                "reason": req.reason,
                "created_at": req.created_at.isoformat(),
                "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                "completed_at": req.completed_at.isoformat() if req.completed_at else None
            }
            for req in requests
        ]
    }


@router.post("/lgpd/deletion-requests/{request_id}/approve")
def approve_deletion_request(
    request_id: str,
    approval: DataDeletionApproval,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    ✅/❌ **Aprovar/Rejeitar Solicitação de Exclusão**
    
    Processa solicitação de exclusão de dados.
    
    **Aprovação:** Inicia processo de exclusão permanente
    **Rejeição:** Requer justificativa (ex: obrigação legal de retenção)
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    try:
        lgpd_service.process_deletion_request(
            request_id=request_id,
            approved=approval.approved,
            approved_by=str(current_user.id),
            rejection_reason=approval.rejection_reason
        )
        
        return {
            "message": "Solicitação processada com sucesso",
            "request_id": request_id,
            "approved": approval.approved
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erro ao processar solicitação: {str(e)}")


@router.post("/lgpd/data-export")
def export_user_data(
    export_data: DataExportRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    📦 **Exportar Dados do Usuário (Direito à Portabilidade)**
    
    Exporta todos os dados pessoais do titular em formato estruturado.
    
    **LGPD Art. 18:** Direito à portabilidade dos dados
    
    **Inclui:**
    - Dados cadastrais
    - Histórico de conversas
    - Consentimentos
    - Logs de acesso
    """
    
    lgpd_service = LGPDService(db, str(current_user.tenant_id))
    
    try:
        data = lgpd_service.export_user_data(
            subject_id=export_data.subject_id,
            subject_type=export_data.subject_type
        )
        
        # Log access
        lgpd_service.log_data_access(
            subject_type=export_data.subject_type,
            subject_id=export_data.subject_id,
            accessed_by_user_id=current_user.id,
            access_type="export",
            resource_type=export_data.subject_type,
            resource_id=export_data.subject_id,
            justification="Exportação de dados solicitada pelo titular"
        )
        
        return data
    except Exception as e:
        raise HTTPException(500, f"Erro ao exportar dados: {str(e)}")


# ============================================================================
# Security Audit Endpoints
# ============================================================================

@router.get("/audit/logs")
def get_security_logs(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 **Logs de Auditoria de Segurança**
    
    Lista eventos de segurança registrados no sistema.
    
    **Filtros:**
    - `event_type`: login, logout, failed_login, permission_denied, etc
    - `severity`: info, warning, error, critical
    - `limit`: Máximo de registros (padrão: 100)
    """
    
    from app.whatsapp.security import SecurityAuditLog
    
    query = db.query(SecurityAuditLog).filter(
        SecurityAuditLog.tenant_id == str(current_user.tenant_id)
    )
    
    if event_type:
        query = query.filter(SecurityAuditLog.event_type == event_type)
    
    if severity:
        query = query.filter(SecurityAuditLog.severity == severity)
    
    logs = query.order_by(SecurityAuditLog.created_at.desc()).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "severity": log.severity,
                "description": log.description,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


@router.post("/webhook/validate-signature")
def validate_webhook_signature(
    payload: str,
    signature: str = Header(..., alias="X-Webhook-Signature"),
    secret: str = Header(..., alias="X-Webhook-Secret")
):
    """
    🔐 **Validar Assinatura de Webhook**
    
    Valida assinatura HMAC-SHA256 de webhook para garantir autenticidade.
    
    **Headers obrigatórios:**
    - `X-Webhook-Signature`: Assinatura HMAC do payload
    - `X-Webhook-Secret`: Secret compartilhado
    
    **Uso:** Chamar antes de processar webhooks externos
    """
    
    is_valid = WebhookSignatureValidator.validate_signature(
        payload=payload,
        signature=signature,
        secret=secret
    )
    
    if not is_valid:
        raise HTTPException(401, "Assinatura inválida")
    
    return {"valid": True, "message": "Assinatura válida"}


@router.post("/webhook/generate-secret")
def generate_webhook_secret(
    current_user: User = Depends(get_current_user)
):
    """
    🔑 **Gerar Secret para Webhook**
    
    Gera secret aleatória criptograficamente segura para webhooks.
    
    **Uso:** Compartilhar com serviço externo que enviará webhooks
    """
    
    secret = WebhookSignatureValidator.generate_webhook_secret()
    
    return {
        "secret": secret,
        "note": "Guarde este secret em local seguro. Não será possível recuperá-lo depois."
    }
