"""Modelo de dados do CRM (etapa 1.4). Tudo por loja (tenant), com RLS.

"Loja" e o tenant: o isolamento entre lojas vem de `BaseTenantModel`. Regras de
negocio em docs/crm/CONTRATOS_CONCEITUAIS.md. Estas tabelas nao tem relacao com
`opportunities` (sugestoes de venda no PDV): aqui "oportunidade" e o motivo de
contato com o tutor dentro de um lead.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)

from app.base_models import BaseTenantModel

# Tipo da coluna do funil: define o que acontece ao mover o card para ela.
COLUNA_ENTRADA = "entrada"
COLUNA_ANDAMENTO = "andamento"
COLUNA_CONCLUIDO = "concluido"
COLUNA_ENCERRADO = "encerrado"
TIPOS_DE_COLUNA = (COLUNA_ENTRADA, COLUNA_ANDAMENTO, COLUNA_CONCLUIDO, COLUNA_ENCERRADO)

# Estado de uma oportunidade dentro do lead.
OPORTUNIDADE_ABERTA = "aberta"
OPORTUNIDADE_RESOLVIDA = "resolvida"
OPORTUNIDADE_DESCARTADA = "descartada"
ESTADOS_DE_OPORTUNIDADE = (
    OPORTUNIDADE_ABERTA,
    OPORTUNIDADE_RESOLVIDA,
    OPORTUNIDADE_DESCARTADA,
)

# Tipos de passo agendado e de acao registrada.
TIPOS_DE_PASSO = ("ligar", "mensagem", "visita", "oferecer", "outro")
TIPOS_DE_ACAO = ("ligacao", "mensagem", "visita", "atendimento", "observacao")


class CrmFunil(BaseTenantModel):
    """Funil (quadro) da loja. Hoje um por loja; a tabela ja permite mais."""

    __tablename__ = "crm_funis"
    __table_args__ = (
        Index(
            "uq_crm_funis_padrao",
            "tenant_id",
            unique=True,
            postgresql_where=text("padrao"),
        ),
    )

    nome = Column(String(80), nullable=False)
    padrao = Column(Boolean, nullable=False, default=False, server_default="false")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")


class CrmColuna(BaseTenantModel):
    """Coluna configuravel do funil (minimo 1 entrada e 1 concluido, maximo 8)."""

    __tablename__ = "crm_colunas"
    __table_args__ = (
        Index("ix_crm_colunas_funil_ordem", "tenant_id", "funil_id", "ordem"),
    )

    funil_id = Column(Integer, ForeignKey("crm_funis.id"), nullable=False)
    nome = Column(String(60), nullable=False)
    ordem = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False)
    # Colunas finais mostram so os ultimos N dias (vazio = mostra tudo).
    janela_dias = Column(Integer, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")


class CrmLead(BaseTenantModel):
    """Card do tutor na loja: contem as oportunidades e os ciclos.

    Um por tutor por loja, exceto cards separados (`separado_de_lead_id`).
    """

    __tablename__ = "crm_leads"
    __table_args__ = (
        Index("ix_crm_leads_coluna", "tenant_id", "coluna_id"),
        Index("ix_crm_leads_responsavel", "tenant_id", "responsavel_user_id"),
        # Um card "principal" por pessoa cadastrada e um por telefone sem cadastro.
        Index(
            "uq_crm_leads_cliente",
            "tenant_id",
            "cliente_id",
            unique=True,
            postgresql_where=text(
                "cliente_id IS NOT NULL AND separado_de_lead_id IS NULL"
            ),
        ),
        Index(
            "uq_crm_leads_telefone_sem_cadastro",
            "tenant_id",
            "telefone",
            unique=True,
            postgresql_where=text(
                "cliente_id IS NULL AND separado_de_lead_id IS NULL "
                "AND telefone IS NOT NULL"
            ),
        ),
    )

    funil_id = Column(Integer, ForeignKey("crm_funis.id"), nullable=False)
    coluna_id = Column(Integer, ForeignKey("crm_colunas.id"), nullable=False)
    # Pessoa cadastrada (tela Pessoas); vazio = lead sem cadastro.
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    telefone = Column(String(40), nullable=True)
    nome_exibicao = Column(String(200), nullable=True)
    origem = Column(
        String(40), nullable=False, default="manual", server_default="manual"
    )
    responsavel_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    valor_estimado = Column(Numeric(12, 2), nullable=True)
    ciclo_atual = Column(Integer, nullable=False, default=1, server_default="1")
    coluna_desde = Column(DateTime(timezone=True), nullable=True)
    ultimo_contato_em = Column(DateTime(timezone=True), nullable=True)
    motivo_perda = Column(String(200), nullable=True)
    separado_de_lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=True)


class CrmOportunidade(BaseTenantModel):
    """Motivo de contato dentro do lead (vacina, racao, sem comprar, aniversario...)."""

    __tablename__ = "crm_oportunidades"
    __table_args__ = (
        Index("ix_crm_oportunidades_lead", "tenant_id", "lead_id", "ciclo"),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    ciclo = Column(Integer, nullable=False, default=1, server_default="1")
    tipo = Column(String(40), nullable=False)
    detalhe = Column(String(300), nullable=True)
    estado = Column(
        String(20),
        nullable=False,
        default=OPORTUNIDADE_ABERTA,
        server_default=OPORTUNIDADE_ABERTA,
    )
    motivo = Column(String(200), nullable=True)
    # Sinal generico (ex.: "sem comprar") esmaece se houver um especifico aberto.
    generica = Column(Boolean, nullable=False, default=False, server_default="false")
    resolvida_em = Column(DateTime(timezone=True), nullable=True)


class CrmMovimentacao(BaseTenantModel):
    """Historico de cada mudanca de coluna (inclusive reaberturas e voltas)."""

    __tablename__ = "crm_movimentacoes"
    __table_args__ = (
        Index("ix_crm_movimentacoes_lead", "tenant_id", "lead_id", "created_at"),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    ciclo = Column(Integer, nullable=False, default=1, server_default="1")
    coluna_origem_id = Column(Integer, ForeignKey("crm_colunas.id"), nullable=True)
    coluna_destino_id = Column(Integer, ForeignKey("crm_colunas.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nota = Column(Text, nullable=True)


class CrmInteracao(BaseTenantModel):
    """Tudo que aconteceu com o tutor (mensagem, ligacao, compra, vacina, etapa)."""

    __tablename__ = "crm_interacoes"
    __table_args__ = (
        Index("ix_crm_interacoes_lead", "tenant_id", "lead_id", "ocorrida_em"),
        Index("ix_crm_interacoes_cliente", "tenant_id", "cliente_id", "ocorrida_em"),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    tipo = Column(String(40), nullable=False)
    resumo = Column(String(500), nullable=False)
    origem = Column(
        String(40), nullable=False, default="sistema", server_default="sistema"
    )
    ocorrida_em = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CrmAcao(BaseTenantModel):
    """O que o usuario fez com o tutor; atualiza o ultimo contato do lead."""

    __tablename__ = "crm_acoes"
    __table_args__ = (
        Index("ix_crm_acoes_lead", "tenant_id", "lead_id", "ocorrida_em"),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    observacao = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ocorrida_em = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CrmProximoPasso(BaseTenantModel):
    """O que sera feito e quando (amarelo se hoje ou sem passo, vermelho se atrasado)."""

    __tablename__ = "crm_proximos_passos"
    __table_args__ = (
        Index("ix_crm_proximos_passos_lead", "tenant_id", "lead_id", "concluido_em"),
        Index(
            "ix_crm_proximos_passos_agenda",
            "tenant_id",
            "responsavel_user_id",
            "agendado_para",
        ),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    descricao = Column(String(300), nullable=True)
    agendado_para = Column(DateTime(timezone=True), nullable=False)
    responsavel_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    concluido_em = Column(DateTime(timezone=True), nullable=True)


class CrmVinculoIgnorado(BaseTenantModel):
    """Pessoa cadastrada que o usuario pediu para nao sugerir mais como vinculo deste card."""

    __tablename__ = "crm_vinculos_ignorados"
    __table_args__ = (
        Index(
            "uq_crm_vinculos_ignorados",
            "tenant_id",
            "lead_id",
            "cliente_id",
            unique=True,
        ),
    )

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


TABELAS_DO_CRM = (
    CrmFunil.__tablename__,
    CrmColuna.__tablename__,
    CrmLead.__tablename__,
    CrmOportunidade.__tablename__,
    CrmMovimentacao.__tablename__,
    CrmInteracao.__tablename__,
    CrmAcao.__tablename__,
    CrmProximoPasso.__tablename__,
)
