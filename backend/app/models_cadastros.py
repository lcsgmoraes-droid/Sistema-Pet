"""Modelos de cadastros centrais extraidos de app.models."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    DECIMAL,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
# ====================
# CADASTROS
# ====================


class FornecedorGrupo(BaseTenantModel):
    """Grupo comercial de fornecedores com CNPJs separados."""

    __tablename__ = "fornecedor_grupos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_fornecedor_grupos_tenant_nome"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    fornecedor_principal_id = Column(Integer, nullable=True, index=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fornecedores = relationship(
        "Cliente",
        back_populates="fornecedor_grupo",
        foreign_keys="Cliente.fornecedor_grupo_id",
    )


class Cliente(BaseTenantModel):
    """Cliente (tutor dos pets)"""

    __tablename__ = "clientes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_clientes_tenant_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )  # Multi-tenant
    codigo = Column(
        String(20), nullable=True, index=True
    )  # Código único do cliente por tenant (ex: 9923)

    # Tipo de cadastro e pessoa
    tipo_cadastro = Column(
        String(50), nullable=False, default="cliente", index=True
    )  # cliente, fornecedor, veterinario
    tipo_pessoa = Column(
        String(2), nullable=False, default="PF", index=True
    )  # PF ou PJ
    fornecedor_grupo_id = Column(
        Integer,
        ForeignKey("fornecedor_grupos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Dados pessoais (PF) / Nome Fantasia (PJ)
    nome = Column(String(255), nullable=False, index=True)
    cpf = Column(String(14), nullable=True, index=True)
    telefone = Column(String(50), nullable=True)
    celular = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    data_nascimento = Column(
        DateTime, nullable=True
    )  # Aniversário do cliente (usado em campanhas)

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
    parceiro_ativo = Column(Boolean, default=False, nullable=False, server_default="0")
    parceiro_desde = Column(
        DateTime(timezone=True), nullable=True
    )  # Data de ativação como parceiro
    parceiro_observacoes = Column(Text, nullable=True)  # Observações sobre o parceiro

    # 📅 CONFIGURAÇÃO DE ACERTO FINANCEIRO (fechamento periódico automático)
    parceiro_tipo_acerto = Column(
        String(20), nullable=False, default="mensal", server_default="mensal"
    )  # mensal, quinzenal, semanal, manual
    parceiro_dia_acerto = Column(
        Integer, nullable=False, default=1, server_default="1"
    )  # Dia do mês/semana para acerto
    parceiro_notificar = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )  # Enviar email de acerto?
    parceiro_email_principal = Column(
        String(255), nullable=True
    )  # Email principal para acerto (sobrepõe email do cadastro)
    parceiro_emails_copia = Column(
        Text, nullable=True
    )  # Emails adicionais separados por vírgula

    # 👔 RH - FUNCIONÁRIOS (novo)
    # cargo_id = Column(Integer, ForeignKey("cargos.id"), nullable=True, index=True)  # FK para tabela cargos
    cargo_id = Column(
        Integer, nullable=True, index=True
    )  # FK temporária sem constraint (tabela cargos não existe ainda)
    salario_base_override = Column(Numeric(10, 2), nullable=True)
    liquido_combinado = Column(Numeric(10, 2), nullable=True)
    complemento_modo = Column(
        String(20), nullable=False, default="automatico", server_default="automatico"
    )
    complemento_fixo_valor = Column(
        Numeric(10, 2), nullable=False, default=0, server_default="0"
    )
    remuneracao_observacoes = Column(Text, nullable=True)

    # 💰 CONFIGURAÇÃO DE COMISSÕES
    data_fechamento_comissao = Column(
        Integer, nullable=True
    )  # Dia do mês (1-31) para fechamento de comissão

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
    enderecos_adicionais = Column(
        JSON, nullable=True
    )  # Array de endereços adicionais com tipo, apelido, etc.

    # 🚚 ENTREGADOR (SPRINT 1)
    is_entregador = Column(Boolean, nullable=False, default=False)
    is_terceirizado = Column(Boolean, nullable=False, default=False)
    recebe_repasse = Column(Boolean, nullable=False, default=False)
    gera_conta_pagar = Column(Boolean, nullable=False, default=False)

    tipo_vinculo_entrega = Column(
        String(20), nullable=True
    )  # funcionario | terceirizado | eventual
    valor_padrao_entrega = Column(Numeric(10, 2), nullable=True)
    valor_por_km = Column(Numeric(10, 2), nullable=True)
    recebe_comissao_entrega = Column(Boolean, nullable=False, default=False)

    # 🚚 ENTREGADOR - SISTEMA COMPLETO (FASE 2)
    entregador_ativo = Column(Boolean, nullable=False, default=True)
    entregador_padrao = Column(
        Boolean, nullable=False, default=False
    )  # Pré-selecionado nas rotas
    controla_rh = Column(Boolean, nullable=False, default=False)
    gera_conta_pagar_custo_entrega = Column(
        Boolean, nullable=False, default=False
    )  # MATRIZ FINAL
    media_entregas_configurada = Column(Integer, nullable=True)
    media_entregas_real = Column(Integer, nullable=True)
    custo_rh_ajustado = Column(Numeric(10, 2), nullable=True)
    modelo_custo_entrega = Column(
        String(20), nullable=True
    )  # rateio_rh | taxa_fixa | por_km
    taxa_fixa_entrega = Column(Numeric(10, 2), nullable=True)
    valor_por_km_entrega = Column(Numeric(10, 2), nullable=True)
    moto_propria = Column(Boolean, nullable=False, default=True)

    # 📆 Acerto financeiro (ETAPA 4)
    tipo_acerto_entrega = Column(
        String(20), nullable=True
    )  # semanal | quinzenal | mensal
    dia_semana_acerto = Column(
        Integer, nullable=True
    )  # 1=segunda, 7=domingo (para semanal)
    dia_mes_acerto = Column(Integer, nullable=True)  # 1-28 (para mensal)
    data_ultimo_acerto = Column(Date, nullable=True)  # Controle interno

    # 📊 DRE - Controle de classificação (NOVO)
    # Para fornecedores de produtos (revenda/estoque) que não impactam DRE diretamente
    controla_dre = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )  # True = vai para DRE, False = não classifica (produtos p/ revenda)

    # Outros
    observacoes = Column(Text, nullable=True)
    alertas_pdv = Column(JSON, nullable=True)
    ativo = Column(Boolean, default=True)

    # 💰 Crédito de devoluções
    credito = Column(DECIMAL(10, 2), nullable=False, default=0.0, server_default="0.0")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    fornecedor_grupo = relationship(
        "FornecedorGrupo",
        back_populates="fornecedores",
        foreign_keys=[fornecedor_grupo_id],
    )

    @property
    def fornecedor_grupo_nome(self):
        return self.fornecedor_grupo.nome if self.fornecedor_grupo else None

    pets = relationship("Pet", back_populates="cliente", cascade="all, delete-orphan")


class Especie(BaseTenantModel):
    """Espécies de animais (Cão, Gato, Ave, etc.)"""

    __tablename__ = "especies"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(
        String(100), nullable=False, index=True
    )  # Cão, Gato, Ave, Réptil, etc
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    racas = relationship(
        "Raca", back_populates="especie_obj", cascade="all, delete-orphan"
    )


class Raca(BaseTenantModel):
    """Raças de animais"""

    __tablename__ = "racas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    especie = Column(
        String(50), nullable=True, index=True
    )  # compatibilidade com schema legado
    especie_id = Column(Integer, ForeignKey("especies.id"), nullable=False, index=True)
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    especie_obj = relationship("Especie", back_populates="racas")


class Pet(BaseTenantModel):
    """Pet (animal de estimação)"""

    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )  # Multi-tenant
    codigo = Column(String(50), nullable=False, index=True)  # Código único por tenant

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
    alergias_lista = Column(JSON, nullable=True)
    doencas_cronicas = Column(Text, nullable=True)
    condicoes_cronicas_lista = Column(JSON, nullable=True)
    medicamentos_continuos = Column(Text, nullable=True)
    medicamentos_continuos_lista = Column(JSON, nullable=True)
    restricoes_alimentares_lista = Column(JSON, nullable=True)
    historico_clinico = Column(Text, nullable=True)
    tipo_sanguineo = Column(String(20), nullable=True)
    pedigree_registro = Column(String(100), nullable=True)
    castrado_data = Column(Date, nullable=True)

    # Outros
    observacoes = Column(Text, nullable=True)
    foto_url = Column(String(500), nullable=True)  # URL da foto do pet
    ativo = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamento
    cliente = relationship("Cliente", back_populates="pets")
