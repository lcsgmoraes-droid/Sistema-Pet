# ruff: noqa: F401
"""
Modelos do Banco de Dados - Sistema Pet Shop Pro
SQLAlchemy ORM Models
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Text,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    DECIMAL,
    Numeric,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base
from app.base_models import BaseTenantModel, TenantScoped
import sqlalchemy as sa


# ====================
# AUTENTICAÇÃO E USUÁRIOS
# ====================


from app.models_operacionais import ConfiguracaoEntrega, CreditoLog, FeatureFlag
from app.models_authz import (
    AppAccessProfile,
    Permission,
    Role,
    RolePermission,
    UserTenant,
)
from app.models_cadastros import (
    Cliente,
    Especie,
    FornecedorGrupo,
    Pet,
    Raca,
)


class User(BaseTenantModel):
    """Usuário do sistema (multi-tenant)"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable para OAuth
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Superusuário

    # Perfil
    nome = Column(String(255), nullable=True)
    telefone = Column(String(50), nullable=True)
    cpf_cnpj = Column(String(20), nullable=True)
    foto_url = Column(String(500), nullable=True)
    push_token = Column(
        String(500), nullable=True
    )  # Expo / FCM push token (App Mobile)
    vet_calendar_token = Column(String(255), nullable=True, unique=True, index=True)

    # LGPD Compliance
    consent_date = Column(
        DateTime(timezone=True), nullable=True
    )  # Data de aceite dos Termos
    consent_version = Column(String(50), nullable=True)
    privacy_version = Column(String(50), nullable=True)
    consent_ip = Column(String(50), nullable=True)
    consent_user_agent = Column(Text, nullable=True)

    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    email_verification_token_hash = Column(String(128), nullable=True, index=True)
    email_verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # 2FA (Two-Factor Authentication)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32), nullable=True)
    backup_codes = Column(Text, nullable=True)  # JSON array

    # Password Reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Login security
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # OAuth (futuro: Google, etc)
    oauth_provider = Column(String(50), nullable=True)  # 'google', None
    oauth_id = Column(String(255), nullable=True)

    # Configurações da loja
    nome_loja = Column(String(255), nullable=True)
    endereco_loja = Column(Text, nullable=True)
    telefone_loja = Column(String(50), nullable=True)

    # 🚚 Custo operacional de entregador (para contas a pagar)
    custo_operacional_tipo = Column(
        String(20), nullable=True
    )  # 'km_rodado', 'fixo', 'controla_rh'
    custo_operacional_valor = Column(
        DECIMAL(10, 2), nullable=True
    )  # Valor fixo por entrega ou valor por KM
    custo_operacional_controla_rh_id = Column(
        String(100), nullable=True
    )  # ID na API do Controla RH
    periodicidade_acerto_dias = Column(
        Integer, nullable=True, default=7
    )  # Dias para acerto (7=semanal, 15=quinzenal, 30=mensal)

    # Configurações de comissão
    data_fechamento_comissao = Column(
        Integer, nullable=True
    )  # Dia do mês (1-31) para fechamento

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    # IA - Relacionamentos ABA 7 (Extrato Bancário com IA)
    # DESABILITADO TEMPORARIAMENTE: aba7_extrato_models tem dependências circulares
    # Usando strings para evitar problemas de importação circular
    # padroes_categorizacao = relationship("PadraoCategoriacaoIA", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    # lancamentos_importados = relationship("LancamentoImportado", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    # arquivos_extrato = relationship("ArquivoExtratoImportado", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    # historico_dre = relationship("HistoricoAtualizacaoDRE", back_populates="usuario", foreign_keys="HistoricoAtualizacaoDRE.usuario_id", cascade="all, delete-orphan", lazy="dynamic")
    # configuracao_tributaria = relationship("ConfiguracaoTributaria", back_populates="usuario", uselist=False, cascade="all, delete-orphan")


class UserSession(Base):  # Não usar BaseTenantModel - sessões não são tenant-specific
    """Sessões ativas de usuários (para logout remoto)"""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    token_jti = Column(String(36), unique=True, index=True, nullable=False)  # UUID

    # Informações do dispositivo
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)  # JSON com SO, navegador, etc

    # Controle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(255), nullable=True)

    # Relacionamento
    user = relationship("User", back_populates="sessions")


class UserPushDevice(BaseTenantModel):
    """Dispositivo do app mobile autorizado a receber push."""

    __tablename__ = "user_push_devices"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "expo_push_token",
            name="uq_user_push_devices_tenant_user_token",
        ),
        Index(
            "ix_user_push_devices_tenant_user_enabled",
            "tenant_id",
            "user_id",
            "enabled",
        ),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expo_push_token = Column(String(500), nullable=False, index=True)
    platform = Column(String(20), nullable=True)
    device_name = Column(String(255), nullable=True)
    device_brand = Column(String(100), nullable=True)
    device_model = Column(String(150), nullable=True)
    os_name = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_ticket_id = Column(String(120), nullable=True)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")


class AppNotification(BaseTenantModel):
    """Notificacao persistida para a central do app mobile."""

    __tablename__ = "app_notifications"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "idempotency_key",
            name="uq_app_notifications_tenant_user_idem",
        ),
        Index(
            "ix_app_notifications_tenant_user_visible",
            "tenant_id",
            "user_id",
            "cleared_at",
            "created_at",
        ),
        Index(
            "ix_app_notifications_tenant_customer",
            "tenant_id",
            "customer_id",
            "created_at",
        ),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    source = Column(String(80), nullable=False, index=True)
    kind = Column(String(80), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(300), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    push_ticket_id = Column(String(120), nullable=True)
    push_error = Column(Text, nullable=True)

    user = relationship("User")


class AuditLog(BaseTenantModel):
    """Log de auditoria (LGPD - rastreabilidade)"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Ação
    action = Column(
        String(100), nullable=False, index=True
    )  # login, create_product, etc
    entity_type = Column(
        String(50), nullable=True, index=True
    )  # product, sale, client, etc
    entity_id = Column(Integer, nullable=True)

    # Detalhes
    old_value = Column(Text, nullable=True)  # JSON antes
    new_value = Column(Text, nullable=True)  # JSON depois
    details = Column(Text, nullable=True)

    # Contexto
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relacionamento
    user = relationship("User", back_populates="audit_logs")


# ====================
# CADASTROS
# ====================
# Modelos extraidos para app.models_cadastros e reexportados abaixo.

# ====================
# PRODUTOS E ESTOQUE
# ====================
# NOTA: Modelos de produtos movidos para produtos_models.py
# Importar de lá: Categoria, Marca, Departamento, Produto, ProdutoLote, etc.


# ====================
# PLACEHOLDER PARA PRÓXIMAS TABELAS
# ====================
# Serão adicionadas nas próximas fases:
# - Fornecedor
# - Estoque
# - MovimentacaoEstoque
# - Venda
# - ItemVenda
# - Pagamento
# - ContaPagar
# - ContaReceber
# - Comissao
# - Servico
# - Agendamento
# etc.


# ====================
# ACERTO FINANCEIRO DE PARCEIROS
# ====================


class AcertoParceiro(BaseTenantModel):
    """
    Registra eventos de acerto periódico de parceiros.
    Um acerto é uma consolidação automática de todas as comissões pendentes
    do parceiro em uma data configurada, com aplicação de compensação automática
    de dívidas e envio de notificação por email.
    """

    __tablename__ = "acertos_parceiro"

    id = Column(Integer, primary_key=True, index=True)
    parceiro_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )  # Multi-tenant

    # Período do acerto
    data_acerto = Column(
        DateTime(timezone=True), nullable=False, index=True
    )  # Data de processamento
    periodo_inicio = Column(
        DateTime(timezone=True), nullable=False
    )  # Início do período calculado
    periodo_fim = Column(
        DateTime(timezone=True), nullable=False
    )  # Fim do período calculado
    tipo_acerto = Column(
        String(20), nullable=False
    )  # mensal, quinzenal, semanal, manual

    # Valores consolidados
    comissoes_fechadas = Column(
        Integer, nullable=False, default=0
    )  # Quantidade de comissões fechadas
    valor_bruto = Column(
        DECIMAL(10, 2), nullable=False, default=0.0
    )  # Soma de todas as comissões
    valor_compensado = Column(
        DECIMAL(10, 2), nullable=False, default=0.0
    )  # Total compensado com dívidas
    valor_liquido = Column(
        DECIMAL(10, 2), nullable=False, default=0.0
    )  # valor_bruto - valor_compensado

    # Status
    status = Column(
        String(20), nullable=False, default="processado", index=True
    )  # processado, erro, cancelado
    observacoes = Column(Text, nullable=True)  # Detalhes do processamento

    # Rastreabilidade de email
    email_enviado = Column(Boolean, nullable=False, default=False)
    email_destinatarios = Column(Text, nullable=True)  # Emails separados por vírgula
    email_erro = Column(Text, nullable=True)  # Erro ao enviar email (se houver)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmailTemplate(BaseTenantModel):
    """
    Templates reutilizáveis de email para diferentes tipos de notificação.
    Suporta placeholders Mustache-style para substituição dinâmica.
    """

    __tablename__ = "emails_templates"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "codigo",
            name="uq_emails_templates_tenant_codigo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )  # Multi-tenant

    # Identificação
    codigo = Column(
        String(50), nullable=False, index=True
    )  # ACERTO_PARCEIRO, BOAS_VINDAS, etc
    nome = Column(String(255), nullable=False)  # Nome descritivo
    descricao = Column(Text, nullable=True)

    # Conteúdo
    assunto = Column(String(255), nullable=False)  # Assunto do email
    corpo_html = Column(Text, nullable=False)  # Corpo em HTML
    corpo_texto = Column(Text, nullable=True)  # Corpo em texto puro (fallback)

    # Metadados
    placeholders = Column(JSON, nullable=True)  # Array de placeholders disponíveis
    categoria = Column(
        String(50), nullable=True
    )  # financeiro, marketing, operacional, etc
    ativo = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmailEnvio(BaseTenantModel):
    """
    Controle de envio de emails com governança completa.
    Rastreamento de tentativas, erros e reenvios.
    """

    __tablename__ = "email_envios"

    id = Column(Integer, primary_key=True, index=True)
    parceiro_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    acerto_id = Column(Integer, ForeignKey("acertos_parceiro.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("emails_templates.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Destinatários
    destinatarios = Column(Text, nullable=False)  # Emails separados por vírgula
    assunto = Column(Text, nullable=False)

    # Corpo do email (já renderizado)
    corpo_html = Column(Text, nullable=False)
    corpo_texto = Column(Text, nullable=True)

    # Status e controle
    status = Column(
        String(20), nullable=False, default="pendente", index=True
    )  # pendente, enviado, erro, cancelado
    tentativas = Column(Integer, nullable=False, default=0)
    max_tentativas = Column(Integer, nullable=False, default=3)

    # Datas
    data_enfileiramento = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    data_envio = Column(DateTime(timezone=True), nullable=True, index=True)
    proxima_tentativa = Column(DateTime(timezone=True), nullable=True, index=True)

    # Erros
    ultimo_erro = Column(Text, nullable=True)
    historico_erros = Column(Text, nullable=True)  # JSON com histórico de tentativas

    # Metadados
    observacoes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ====================
# WHATSAPP CRM
# ====================


class DirecaoMensagem(str, PyEnum):
    """Direção da mensagem WhatsApp"""

    ENVIADA = "enviada"
    RECEBIDA = "recebida"


class StatusMensagem(str, PyEnum):
    """Status da mensagem WhatsApp"""

    ENVIADO = "enviado"
    LIDO = "lido"
    ERRO = "erro"
    RECEBIDO = "recebido"


# ====================
# WHATSAPP - MODELO ANTIGO (DESCONTINUADO)
# Comentado para evitar conflito com novos modelos em app/whatsapp/models.py
# ====================

# class WhatsAppMessage(BaseTenantModel):
#     """
#     Model para armazenar histórico de mensagens WhatsApp.
#     Integrado à Timeline Unificada do cliente.
#
#     Nota: Por enquanto, não usa API oficial do WhatsApp.
#     Serve como registro manual/mock das interações.
#     """
#     __tablename__ = "whatsapp_messages"

#     # Não redefinir id, já vem de BaseTenantModel
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Tornar nullable
#     cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
#     pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True)
#     telefone = Column(String(20), nullable=False, index=True)
#     direcao = Column(String(20), nullable=False)  # enviada | recebida
#     conteudo = Column(Text, nullable=False)
#     status = Column(String(20), nullable=False, default='enviado')  # enviado | lido | erro | recebido
#
#     # created_at já vem de BaseTenantModel como created_at
#
#     # Relationships
#     user = relationship("User")
#     cliente = relationship("Cliente")
#     pet = relationship("Pet")

#     def __repr__(self):
#         return f"<WhatsAppMessage(id={self.id}, cliente_id={self.cliente_id}, direcao={self.direcao})>"


# ====================
# MULTI-TENANT RBAC (Etapas A1-A5)
# ====================


class Tenant(Base):
    """Tenant (Empresa/Organização)"""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)  # Nome Fantasia
    razao_social = Column(String(255), nullable=True)
    cnpj = Column(String(18), nullable=True)
    inscricao_estadual = Column(String(50), nullable=True)
    inscricao_municipal = Column(String(50), nullable=True)
    endereco = Column(String(255), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    uf = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    site = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    banner_1_url = Column(String(500), nullable=True)
    banner_2_url = Column(String(500), nullable=True)
    banner_3_url = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, server_default="active")
    plan = Column(String(50), nullable=False, server_default="free")
    billing_status = Column(String(20), nullable=False, server_default="active")
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    subscription_activated_at = Column(DateTime(timezone=True), nullable=True)
    subscription_source = Column(String(50), nullable=False, server_default="manual")
    billing_provider_environment = Column(String(20), nullable=True)
    billing_provider_customer_id = Column(String(80), nullable=True, index=True)
    billing_provider_subscription_id = Column(String(80), nullable=True, index=True)
    billing_provider_payment_id = Column(String(80), nullable=True, index=True)
    billing_payment_status = Column(String(40), nullable=True)
    billing_type = Column(String(30), nullable=True)
    billing_next_due_date = Column(Date, nullable=True)
    billing_checkout_url = Column(String(500), nullable=True)

    # Configurações operacionais
    permite_estoque_negativo = Column(Boolean, nullable=False, server_default="false")
    protecao_validade_ativa = Column(Boolean, nullable=False, server_default="false")
    dias_alerta_validade = Column(Integer, nullable=False, server_default="15")
    bloquear_validade_pdv = Column(Boolean, nullable=False, server_default="true")
    bloquear_validade_ecommerce = Column(Boolean, nullable=False, server_default="true")
    bloquear_validade_integracoes_online = Column(
        Boolean, nullable=False, server_default="false"
    )
    ecommerce_slug = Column(String(80), nullable=True, unique=True, index=True)

    # Configurações da loja virtual
    ecommerce_ativo = Column(Boolean, nullable=False, server_default="true")
    ecommerce_descricao = Column(Text, nullable=True)
    ecommerce_horario_abertura = Column(String(5), nullable=True)  # ex.: "08:00"
    ecommerce_horario_fechamento = Column(String(5), nullable=True)  # ex.: "18:00"
    ecommerce_dias_funcionamento = Column(
        String(200), nullable=True
    )  # ex.: "seg,ter,qua,qui,sex"

    # Módulos premium ativos — JSON com lista de módulos contratados
    # Ex.: '["entregas", "campanhas"]'
    modulos_ativos = Column(Text, nullable=True)

    # Tipo de organização — usado pelo módulo veterinário multi-tenant
    # petshop | veterinary_clinic | grooming | hospital
    organization_type = Column(String(50), nullable=False, server_default="petshop")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships (Sprint 4 - WhatsApp)
    # TODO: Descomentar quando WhatsAppAgent estiver devidamente configurado
    # whatsapp_agents = relationship("WhatsAppAgent", back_populates="tenant")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name})>"


class AssinaturaModulo(TenantScoped, Base):
    """Assinaturas de módulos premium por tenant."""

    __tablename__ = "assinaturas_modulos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # tenant_id (UUID NOT NULL, indexado) vem do mixin TenantScoped → filtro global de tenant.
    modulo = Column(String(50), nullable=False)  # entregas, campanhas, whatsapp...
    status = Column(
        String(20), nullable=False, server_default="ativo"
    )  # ativo | cancelado | expirado
    valor_mensal = Column(Numeric(10, 2), nullable=True)
    data_inicio = Column(DateTime(timezone=True), nullable=True)
    data_fim = Column(DateTime(timezone=True), nullable=True)
    payment_id = Column(String(200), nullable=True)
    gateway = Column(String(50), nullable=True)  # mercadopago | pagarme | manual
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<AssinaturaModulo(tenant={self.tenant_id}, modulo={self.modulo}, status={self.status})>"


class EcommerceNotifyRequest(TenantScoped, Base):
    """Solicitações de aviso 'Avise-me quando chegar' do e-commerce."""

    __tablename__ = "ecommerce_notify_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # tenant_id (UUID NOT NULL, indexado) vem do mixin TenantScoped → filtro global de tenant.
    product_id = Column(Integer, nullable=False, index=True)
    product_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False)
    notified = Column(Boolean, nullable=False, server_default="false")
    notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<EcommerceNotifyRequest(id={self.id}, email={self.email}, product_id={self.product_id})>"


# ====================
# FEATURE FLAGS
# ====================


# ====================
# CONFIGURAÇÃO DE ENTREGAS
# ====================


# ====================
# HISTÓRICO DE CRÉDITO
# ====================
