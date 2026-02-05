# ============================================================================
# SPRINT 8: Segurança & Compliance
# Sistema de segurança, LGPD e proteção de dados
# ============================================================================

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hmac
import hashlib
import secrets
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from app.db import Base
from app.utils.logger import logger


def generate_uuid():
    """Gera UUID como string"""
    import uuid
    return str(uuid.uuid4())


# ============================================================================
# 1. HMAC Validation para Webhooks
# ============================================================================

class WebhookSignatureValidator:
    """Valida assinaturas HMAC de webhooks para segurança"""
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """
        Gera assinatura HMAC-SHA256 para payload
        
        Args:
            payload: Corpo da requisição (string JSON)
            secret: Chave secreta compartilhada
            
        Returns:
            Assinatura hexadecimal
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def validate_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Valida assinatura HMAC do webhook
        
        Args:
            payload: Corpo da requisição recebida
            signature: Assinatura recebida no header
            secret: Chave secreta compartilhada
            
        Returns:
            True se válida, False se inválida
        """
        expected_signature = WebhookSignatureValidator.generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """Gera secret aleatória para webhooks"""
        return secrets.token_urlsafe(32)


# ============================================================================
# 2. Rate Limiting
# ============================================================================

class RateLimiter:
    """
    Rate limiter para proteger contra abuse
    
    Limites:
    - Por IP: 100 requisições/minuto
    - Por usuário: 1000 requisições/hora
    - Por endpoint sensível: 10 requisições/minuto
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.limits = {
            "ip_per_minute": 100,
            "user_per_hour": 1000,
            "webhook_per_minute": 50,
            "ai_per_minute": 20
        }
    
    def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "ip_per_minute"
    ) -> tuple[bool, Optional[int]]:
        """
        Verifica se limite foi excedido
        
        Args:
            identifier: IP, user_id, etc
            limit_type: Tipo de limite a verificar
            
        Returns:
            (permitido: bool, retry_after: Optional[int segundos])
        """
        # TODO: Implementar com Redis para performance
        # Por enquanto, retorna sempre permitido
        return True, None
    
    def record_request(self, identifier: str, limit_type: str):
        """Registra requisição para contagem"""
        # TODO: Implementar registro no Redis
        pass


# ============================================================================
# 3. LGPD Compliance - Modelos
# ============================================================================

class DataPrivacyConsent(Base):
    """Registro de consentimento LGPD"""
    __tablename__ = "data_privacy_consents"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False)
    
    # Subject
    subject_type = Column(String(50), nullable=False)  # customer, user, contact
    subject_id = Column(String(255), nullable=False)  # ID do titular dos dados
    phone_number = Column(String(20))
    email = Column(String(255))
    
    # Consent
    consent_type = Column(String(100), nullable=False)  # whatsapp, marketing, analytics
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_text = Column(Text, nullable=False)  # Texto do termo aceito
    
    # Metadata
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime)
    revoke_reason = Column(Text)
    
    def __repr__(self):
        return f"<DataPrivacyConsent(subject={self.subject_type}:{self.subject_id}, type={self.consent_type})>"


class DataAccessLog(Base):
    """Log de acesso a dados sensíveis (LGPD Art. 37)"""
    __tablename__ = "data_access_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False)
    
    # Subject
    subject_type = Column(String(50), nullable=False)
    subject_id = Column(String(255), nullable=False)
    
    # Access Info
    accessed_by_user_id = Column(Integer)  # FK para users
    access_type = Column(String(50), nullable=False)  # read, write, delete, export
    resource_type = Column(String(100), nullable=False)  # customer, message, session
    resource_id = Column(String(255))
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    justification = Column(Text)  # Justificativa do acesso
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<DataAccessLog(user={self.user_id}, action={self.action}, resource={self.resource_type})>"


class DataDeletionRequest(Base):
    """Solicitações de exclusão de dados (Direito ao Esquecimento)"""
    __tablename__ = "data_deletion_requests"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False)
    
    # Subject
    subject_type = Column(String(50), nullable=False)
    subject_id = Column(String(255), nullable=False)
    
    # Request
    request_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(Text)
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected, completed
    
    # Processing
    processed_by_user_id = Column(Integer)  # FK para users
    processed_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    # Contact
    contact_phone = Column(String(20))
    contact_email = Column(String(255))
    
    # Extra metadata
    extra_metadata = Column(Text)  # JSON
    
    def __repr__(self):
        return f"<DataDeletionRequest(subject={self.subject_type}:{self.subject_id}, status={self.status})>"


# ============================================================================
# 4. Security Audit Log
# ============================================================================

class SecurityAuditLog(Base):
    """Log de eventos de segurança"""
    __tablename__ = "security_audit_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False)
    
    # Event
    event_type = Column(String(100), nullable=False)  # login, logout, failed_login, permission_denied, etc
    severity = Column(String(20), nullable=False, default="info")  # info, warning, error, critical
    
    # User/Actor
    user_id = Column(Integer)  # FK para users
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Resource
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    action = Column(String(100))
    
    # Details
    description = Column(Text, nullable=False)
    extra_data = Column(Text)  # JSON adicional (evita conflito com 'metadata' reservado)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SecurityAuditLog(type={self.event_type}, severity={self.severity})>"


# ============================================================================
# 5. LGPD Service
# ============================================================================

class LGPDService:
    """Serviço para compliance com LGPD"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    def record_consent(
        self,
        subject_type: str,
        subject_id: str,
        consent_type: str,
        consent_given: bool,
        consent_text: str,
        phone_number: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> DataPrivacyConsent:
        """Registra consentimento do titular"""
        
        consent = DataPrivacyConsent(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            phone_number=phone_number,
            consent_type=consent_type,
            consent_given=consent_given,
            consent_text=consent_text,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(consent)
        self.db.commit()
        
        return consent
    
    def check_consent(
        self,
        subject_id: str,
        consent_type: str
    ) -> bool:
        """Verifica se há consentimento válido"""
        
        consent = self.db.query(DataPrivacyConsent).filter(
            DataPrivacyConsent.tenant_id == self.tenant_id,
            DataPrivacyConsent.subject_id == subject_id,
            DataPrivacyConsent.consent_type == consent_type,
            DataPrivacyConsent.consent_given == True,
            DataPrivacyConsent.revoked_at.is_(None)
        ).first()
        
        return consent is not None
    
    def revoke_consent(
        self,
        subject_id: str,
        consent_type: str
    ) -> bool:
        """Revoga consentimento"""
        
        consents = self.db.query(DataPrivacyConsent).filter(
            DataPrivacyConsent.tenant_id == self.tenant_id,
            DataPrivacyConsent.subject_id == subject_id,
            DataPrivacyConsent.consent_type == consent_type,
            DataPrivacyConsent.revoked_at.is_(None)
        ).all()
        
        for consent in consents:
            consent.revoked_at = datetime.utcnow()
        
        self.db.commit()
        
        return len(consents) > 0
    
    def log_data_access(
        self,
        subject_type: str,
        subject_id: str,
        access_type: str,
        resource_type: str,
        resource_id: str,
        accessed_by_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        justification: Optional[str] = None
    ):
        """Registra acesso a dados sensíveis"""
        
        log = DataAccessLog(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            accessed_by_user_id=accessed_by_user_id,
            access_type=access_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            justification=justification
        )
        
        self.db.add(log)
        self.db.commit()
    
    def request_data_deletion(
        self,
        subject_type: str,
        subject_id: str,
        reason: str,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None
    ) -> DataDeletionRequest:
        """Cria solicitação de exclusão de dados"""
        
        request = DataDeletionRequest(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            contact_phone=contact_phone,
            contact_email=contact_email,
            reason=reason,
            status="pending"
        )
        
        self.db.add(request)
        self.db.commit()
        
        return request
    
    def process_deletion_request(
        self,
        request_id: int,
        approved: bool,
        processed_by_user_id: int,
        rejection_reason: Optional[str] = None
    ):
        """Processa solicitação de exclusão"""
        
        request = self.db.query(DataDeletionRequest).filter(
            DataDeletionRequest.id == request_id,
            DataDeletionRequest.tenant_id == self.tenant_id
        ).first()
        
        if not request:
            raise ValueError("Solicitação não encontrada")
        
        if approved:
            request.status = "approved"
            request.processed_by_user_id = processed_by_user_id
            request.processed_at = datetime.utcnow()
            # TODO: Executar exclusão dos dados
        else:
            request.status = "rejected"
            request.rejection_reason = rejection_reason
            request.processed_by_user_id = processed_by_user_id
            request.processed_at = datetime.utcnow()
        
        self.db.commit()
    
    def export_user_data(
        self,
        subject_id: str,
        subject_type: str = "customer"
    ) -> Dict[str, Any]:
        """
        Exporta todos os dados do titular (Direito à Portabilidade)
        
        Returns:
            Dicionário com todos os dados do usuário
        """
        # TODO: Coletar dados de todas as tabelas relevantes
        
        data = {
            "subject_id": subject_id,
            "subject_type": subject_type,
            "export_date": datetime.utcnow().isoformat(),
            "consents": [],
            "whatsapp_sessions": [],
            "whatsapp_messages": [],
            "note": "Exportação completa de dados conforme LGPD"
        }
        
        return data


# ============================================================================
# 6. Security Audit Service
# ============================================================================

class SecurityAuditService:
    """Serviço para auditoria de segurança"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Registra evento de segurança"""
        
        import json
        
        log = SecurityAuditLog(
            tenant_id=tenant_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            metadata=json.dumps(metadata) if metadata else None
        )
        
        self.db.add(log)
        self.db.commit()
        
        # Se crítico, enviar alerta
        if severity == "critical":
            self._send_security_alert(log)
    
    def _send_security_alert(self, log: SecurityAuditLog):
        """Envia alerta de segurança para administradores"""
        # TODO: Implementar envio de email/notificação
        logger.info(f"🚨 ALERTA DE SEGURANÇA: {log.event_type} - {log.description}")
