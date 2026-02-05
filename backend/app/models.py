"""
Modelos do Banco de Dados - Sistema Pet Shop Pro
SQLAlchemy ORM Models
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Float, Text, DateTime, Date, ForeignKey, JSON, DECIMAL, Numeric, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base
from app.base_models import BaseTenantModel
import sqlalchemy as sa


# ====================
# AUTENTICAÇÃO E USUÁRIOS
# ====================

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
    
    # LGPD Compliance
    consent_date = Column(DateTime(timezone=True), nullable=True)  # Data de aceite dos Termos
    
    # 2FA (Two-Factor Authentication)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32), nullable=True)
    backup_codes = Column(Text, nullable=True)  # JSON array
    
    # Password Reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # OAuth (futuro: Google, etc)
    oauth_provider = Column(String(50), nullable=True)  # 'google', None
    oauth_id = Column(String(255), nullable=True)
    
    # Configurações da loja
    nome_loja = Column(String(255), nullable=True)
    endereco_loja = Column(Text, nullable=True)
    telefone_loja = Column(String(50), nullable=True)
    
    # Configurações de comissão
    data_fechamento_comissao = Column(Integer, nullable=True)  # Dia do mês (1-31) para fechamento
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    # IA - Relacionamentos ABA 7 (Extrato Bancário com IA)
    # Usando strings para evitar problemas de importação circular
    padroes_categorizacao = relationship("PadraoCategoriacaoIA", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    lancamentos_importados = relationship("LancamentoImportado", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    arquivos_extrato = relationship("ArquivoExtratoImportado", back_populates="usuario", cascade="all, delete-orphan", lazy="dynamic")
    historico_dre = relationship("HistoricoAtualizacaoDRE", back_populates="usuario", foreign_keys="HistoricoAtualizacaoDRE.usuario_id", cascade="all, delete-orphan", lazy="dynamic")
    configuracao_tributaria = relationship("ConfiguracaoTributaria", back_populates="usuario", uselist=False, cascade="all, delete-orphan")


class UserSession(Base):  # Não usar BaseTenantModel - sessões não são tenant-specific
    """Sessões ativas de usuários (para logout remoto)"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_jti = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    
    # Informações do dispositivo
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)  # JSON com SO, navegador, etc
    
    # Controle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(255), nullable=True)
    
    # Relacionamento
    user = relationship("User", back_populates="sessions")


class AuditLog(BaseTenantModel):
    """Log de auditoria (LGPD - rastreabilidade)"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Ação
    action = Column(String(100), nullable=False, index=True)  # login, create_product, etc
    entity_type = Column(String(50), nullable=True, index=True)  # product, sale, client, etc
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

class Cliente(BaseTenantModel):
    """Cliente (tutor dos pets)"""
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Multi-tenant
    codigo = Column(String(20), nullable=True, index=True)  # Código único do cliente (ex: 9923)
    
    # Tipo de cadastro e pessoa
    tipo_cadastro = Column(String(50), nullable=False, default="cliente", index=True)  # cliente, fornecedor, veterinario
    tipo_pessoa = Column(String(2), nullable=False, default="PF", index=True)  # PF ou PJ
    
    # Dados pessoais (PF) / Nome Fantasia (PJ)
    nome = Column(String(255), nullable=False, index=True)
    cpf = Column(String(14), nullable=True, index=True)
    telefone = Column(String(50), nullable=True)
    celular = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Dados de Pessoa Jurídica
    cnpj = Column(String(18), nullable=True, index=True)
    inscricao_estadual = Column(String(20), nullable=True)
    razao_social = Column(String(255), nullable=True)
    nome_fantasia = Column(String(255), nullable=True)
    responsavel = Column(String(255), nullable=True)  # Nome do contato/responsável
    
    # Veterinário
    crmv = Column(String(20), nullable=True, index=True)  # Registro no CRMV
    
    # 🤝 SISTEMA DE PARCEIROS (comissões)
    # Permite que QUALQUER pessoa (cliente, veterinário, funcionário, fornecedor) seja parceiro
    parceiro_ativo = Column(Boolean, default=False, nullable=False, server_default='0')
    parceiro_desde = Column(DateTime(timezone=True), nullable=True)  # Data de ativação como parceiro
    parceiro_observacoes = Column(Text, nullable=True)  # Observações sobre o parceiro
    
    # 📅 CONFIGURAÇÃO DE ACERTO FINANCEIRO (fechamento periódico automático)
    parceiro_tipo_acerto = Column(String(20), nullable=False, default='mensal', server_default='mensal')  # mensal, quinzenal, semanal, manual
    parceiro_dia_acerto = Column(Integer, nullable=False, default=1, server_default='1')  # Dia do mês/semana para acerto
    parceiro_notificar = Column(Boolean, nullable=False, default=True, server_default='1')  # Enviar email de acerto?
    parceiro_email_principal = Column(String(255), nullable=True)  # Email principal para acerto (sobrepõe email do cadastro)
    parceiro_emails_copia = Column(Text, nullable=True)  # Emails adicionais separados por vírgula
    
    # 👔 RH - FUNCIONÁRIOS (novo)
    # TODO: Criar tabela Cargo antes de descomentar
    # cargo_id = Column(Integer, ForeignKey("cargos.id"), nullable=True, index=True)  # FK para tabela cargos
    cargo_id = Column(Integer, nullable=True, index=True)  # FK temporária sem constraint
    
    # 💰 CONFIGURAÇÃO DE COMISSÕES
    data_fechamento_comissao = Column(Integer, nullable=True)  # Dia do mês (1-31) para fechamento de comissão
    
    # Endereço
    cep = Column(String(10), nullable=True)
    endereco = Column(Text, nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    
    # Endereços de entrega (alternativos ao endereço principal)
    endereco_entrega = Column(Text, nullable=True)  # Endereço de entrega principal
    endereco_entrega_2 = Column(Text, nullable=True)  # Segundo endereço de entrega
    enderecos_adicionais = Column(JSON, nullable=True)  # Array de endereços adicionais com tipo, apelido, etc.
    
    # 🚚 ENTREGADOR (SPRINT 1)
    is_entregador = Column(Boolean, nullable=False, default=False)
    is_terceirizado = Column(Boolean, nullable=False, default=False)
    recebe_repasse = Column(Boolean, nullable=False, default=False)
    gera_conta_pagar = Column(Boolean, nullable=False, default=False)
    
    tipo_vinculo_entrega = Column(String(20), nullable=True)  # funcionario | terceirizado | eventual
    valor_padrao_entrega = Column(Numeric(10, 2), nullable=True)
    valor_por_km = Column(Numeric(10, 2), nullable=True)
    recebe_comissao_entrega = Column(Boolean, nullable=False, default=False)
    
    # 🚚 ENTREGADOR - SISTEMA COMPLETO (FASE 2)
    entregador_ativo = Column(Boolean, nullable=False, default=True)
    entregador_padrao = Column(Boolean, nullable=False, default=False)  # Pré-selecionado nas rotas
    controla_rh = Column(Boolean, nullable=False, default=False)
    gera_conta_pagar_custo_entrega = Column(Boolean, nullable=False, default=False)  # MATRIZ FINAL
    media_entregas_configurada = Column(Integer, nullable=True)
    media_entregas_real = Column(Integer, nullable=True)
    custo_rh_ajustado = Column(Numeric(10, 2), nullable=True)
    modelo_custo_entrega = Column(String(20), nullable=True)  # rateio_rh | taxa_fixa | por_km
    taxa_fixa_entrega = Column(Numeric(10, 2), nullable=True)
    valor_por_km_entrega = Column(Numeric(10, 2), nullable=True)
    moto_propria = Column(Boolean, nullable=False, default=True)
    
    # 📆 Acerto financeiro (ETAPA 4)
    tipo_acerto_entrega = Column(String(20), nullable=True)  # semanal | quinzenal | mensal
    dia_semana_acerto = Column(Integer, nullable=True)  # 1=segunda, 7=domingo (para semanal)
    dia_mes_acerto = Column(Integer, nullable=True)  # 1-28 (para mensal)
    data_ultimo_acerto = Column(Date, nullable=True)  # Controle interno
    
    # Outros
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    
    # 💰 Crédito de devoluções
    credito = Column(DECIMAL(10, 2), nullable=False, default=0.0, server_default='0.0')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    pets = relationship("Pet", back_populates="cliente", cascade="all, delete-orphan")


class Raca(BaseTenantModel):
    """Raças de animais"""
    __tablename__ = "racas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    especie = Column(String(50), nullable=False, index=True)  # Cão, Gato, Ave, etc
    ativo = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Pet(BaseTenantModel):
    """Pet (animal de estimação)"""
    __tablename__ = "pets"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Multi-tenant
    codigo = Column(String(50), unique=True, nullable=False, index=True)  # Código único do pet
    
    # Dados do pet
    nome = Column(String(255), nullable=False, index=True)
    especie = Column(String(50), nullable=False)  # cão, gato, coelho, etc
    raca = Column(String(100), nullable=True)
    sexo = Column(String(10), nullable=True)  # macho, fêmea
    castrado = Column(Boolean, default=False)
    
    # Características
    data_nascimento = Column(DateTime, nullable=True)
    idade_aproximada = Column(Integer, nullable=True)  # meses
    peso = Column(Float, nullable=True)  # kg
    cor = Column(String(100), nullable=True)  # cor/pelagem
    cor_pelagem = Column(String(100), nullable=True)  # mantido por compatibilidade
    porte = Column(String(20), nullable=True)  # mini, pequeno, médio, grande, gigante
    
    # Saúde
    microchip = Column(String(50), nullable=True)
    alergias = Column(Text, nullable=True)
    doencas_cronicas = Column(Text, nullable=True)
    medicamentos_continuos = Column(Text, nullable=True)
    historico_clinico = Column(Text, nullable=True)
    
    # Outros
    observacoes = Column(Text, nullable=True)
    foto_url = Column(String(500), nullable=True)  # URL da foto do pet
    ativo = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamento
    cliente = relationship("Cliente", back_populates="pets")


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Multi-tenant
    
    # Período do acerto
    data_acerto = Column(DateTime(timezone=True), nullable=False, index=True)  # Data de processamento
    periodo_inicio = Column(DateTime(timezone=True), nullable=False)  # Início do período calculado
    periodo_fim = Column(DateTime(timezone=True), nullable=False)  # Fim do período calculado
    tipo_acerto = Column(String(20), nullable=False)  # mensal, quinzenal, semanal, manual
    
    # Valores consolidados
    comissoes_fechadas = Column(Integer, nullable=False, default=0)  # Quantidade de comissões fechadas
    valor_bruto = Column(DECIMAL(10, 2), nullable=False, default=0.0)  # Soma de todas as comissões
    valor_compensado = Column(DECIMAL(10, 2), nullable=False, default=0.0)  # Total compensado com dívidas
    valor_liquido = Column(DECIMAL(10, 2), nullable=False, default=0.0)  # valor_bruto - valor_compensado
    
    # Status
    status = Column(String(20), nullable=False, default='processado', index=True)  # processado, erro, cancelado
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Multi-tenant
    
    # Identificação
    codigo = Column(String(50), nullable=False, unique=True, index=True)  # ACERTO_PARCEIRO, BOAS_VINDAS, etc
    nome = Column(String(255), nullable=False)  # Nome descritivo
    descricao = Column(Text, nullable=True)
    
    # Conteúdo
    assunto = Column(String(255), nullable=False)  # Assunto do email
    corpo_html = Column(Text, nullable=False)  # Corpo em HTML
    corpo_texto = Column(Text, nullable=True)  # Corpo em texto puro (fallback)
    
    # Metadados
    placeholders = Column(JSON, nullable=True)  # Array de placeholders disponíveis
    categoria = Column(String(50), nullable=True)  # financeiro, marketing, operacional, etc
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
    status = Column(String(20), nullable=False, default='pendente', index=True)  # pendente, enviado, erro, cancelado
    tentativas = Column(Integer, nullable=False, default=0)
    max_tentativas = Column(Integer, nullable=False, default=3)
    
    # Datas
    data_enfileiramento = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
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

from enum import Enum as PyEnum

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
    __tablename__ = 'tenants'
    
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
    status = Column(String(50), nullable=False, server_default='active')
    plan = Column(String(50), nullable=False, server_default='free')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships (Sprint 4 - WhatsApp)
    # TODO: Descomentar quando WhatsAppAgent estiver devidamente configurado
    # whatsapp_agents = relationship("WhatsAppAgent", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name})>"


class Role(BaseTenantModel):
    """Role (Função/Cargo) por tenant"""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class Permission(Base):
    """Permission (Permissão global do sistema)"""
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code={self.code})>"


class UserTenant(BaseTenantModel):
    """Vínculo User ↔ Tenant ↔ Role"""
    __tablename__ = 'user_tenants'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, server_default='true')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<UserTenant(user_id={self.user_id}, tenant_id={self.tenant_id}, role_id={self.role_id})>"


class RolePermission(BaseTenantModel):
    """Vínculo Role ↔ Permission por tenant"""
    __tablename__ = 'role_permissions'
    
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False, index=True)
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id}, tenant_id={self.tenant_id})>"


# ====================
# FEATURE FLAGS
# ====================

class FeatureFlag(BaseTenantModel):
    """
    Feature Flags por tenant para ativar/desativar funcionalidades.
    
    Permite controle granular de features experimentais ou em rollout gradual,
    garantindo que o sistema nunca dependa de features desligadas para funcionar.
    
    Exemplo: PDV_IA_OPORTUNIDADES pode ser ativada apenas para tenants específicos
    durante o período de testes, sem afetar os demais usuários.
    """
    __tablename__ = 'feature_flags'
    
    feature_key = Column(
        String(100), 
        nullable=False, 
        index=True,
        comment='Identificador único da feature (ex: PDV_IA_OPORTUNIDADES)'
    )
    enabled = Column(
        Boolean, 
        nullable=False, 
        server_default=sa.text('false'),
        comment='Status da feature: true=ativa, false=desligada'
    )
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'feature_key', name='uq_feature_flags_tenant_feature'),
        Index('ix_feature_flags_tenant_feature_lookup', 'tenant_id', 'feature_key', 'enabled'),
    )
    
    def __repr__(self):
        return f"<FeatureFlag(tenant_id={self.tenant_id}, feature_key={self.feature_key}, enabled={self.enabled})>"


# ====================
# CONFIGURAÇÃO DE ENTREGAS
# ====================

class ConfiguracaoEntrega(BaseTenantModel):
    """
    Configuração global de entregas por tenant.
    Um único registro por tenant.
    """
    __tablename__ = "configuracoes_entrega"
    
    # FK para o usuário que criou/gerencia a configuração
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Entregador padrão (FK para clientes.id que é Integer)
    entregador_padrao_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True)
    
    # Ponto inicial da rota (endereço detalhado da loja/empresa)
    logradouro = Column(String(300), nullable=True)  # Rua/Avenida
    cep = Column(String(9), nullable=True)  # 00000-000
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)  # UF
    
    # Relacionamento com o entregador padrão
    entregador_padrao = relationship("Cliente", foreign_keys=[entregador_padrao_id])
