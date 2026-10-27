"""Livro-razao das mensagens de WhatsApp (uma linha por mensagem, por loja).

Base para conferir o que a Meta cobra e repassar o custo para cada loja. Ao
contrario de `whatsapp_ia_messages` (o chat), aqui ficam o estado de entrega, a
categoria de cobranca, a janela de 24 horas e o motivo de cada falha.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)

from app.base_models import BaseTenantModel

DIRECAO_ENVIADA = "enviada"
DIRECAO_RECEBIDA = "recebida"

# Quem/o que gerou a mensagem enviada.
ORIGEM_IA = "ia"
ORIGEM_ATENDENTE = "atendente"
ORIGEM_SISTEMA = "sistema"  # avisos automaticos (espera, entrega...)
ORIGEM_AUTOMACAO = "automacao"  # modelos disparados por gatilho (Etapa 7)
ORIGEM_TUTOR = "tutor"  # mensagem recebida
ORIGEM_DESCONHECIDA = "desconhecida"  # estado chegou sem registro de envio

ESTADO_ENVIADA = "enviada"
ESTADO_ENTREGUE = "entregue"
ESTADO_LIDA = "lida"
ESTADO_FALHOU = "falhou"
ESTADO_RECEBIDA = "recebida"


class WhatsAppLedger(BaseTenantModel):
    __tablename__ = "whatsapp_ledger"
    __table_args__ = (
        Index(
            "ux_whatsapp_ledger_tenant_wa_message",
            "tenant_id",
            "wa_message_id",
            unique=True,
            postgresql_where=text("wa_message_id IS NOT NULL"),
            sqlite_where=text("wa_message_id IS NOT NULL"),
        ),
        Index("ix_whatsapp_ledger_tenant_data", "tenant_id", "ocorrido_em"),
        Index("ix_whatsapp_ledger_sessao", "tenant_id", "session_id"),
    )

    direcao = Column(String(10), nullable=False)
    origem = Column(String(20), nullable=False)
    # meta_cloud | 360dialog | waha
    provedor = Column(String(20), nullable=False)
    session_id = Column(String(64), nullable=True)
    message_id = Column(
        String(64), nullable=True
    )  # linha do chat (whatsapp_ia_messages)
    wa_message_id = Column(String(255), nullable=True)  # ID da mensagem na Meta
    telefone = Column(String(40), nullable=True)
    # "texto", "imagem" ou "modelo"
    tipo_conteudo = Column(
        String(20), nullable=False, default="texto", server_default="texto"
    )
    template_nome = Column(String(120), nullable=True)
    # categoria do modelo escolhida por nos: marketing | utility | authentication
    template_categoria = Column(String(20), nullable=True)
    # Dentro das 24h depois da ultima mensagem do tutor (so enviadas).
    janela_24h = Column(Boolean, nullable=True)

    estado = Column(String(12), nullable=False)
    ocorrido_em = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
    lido_em = Column(DateTime(timezone=True), nullable=True)
    falhou_em = Column(DateTime(timezone=True), nullable=True)
    erro_codigo = Column(String(20), nullable=True)
    erro_mensagem = Column(String(300), nullable=True)

    # Cobranca informada pela Meta no aviso de estado.
    cobravel = Column(Boolean, nullable=True)
    categoria_cobranca = Column(String(30), nullable=True)
    modelo_de_preco = Column(String(30), nullable=True)
    # Preenchidos depois, na conferencia com a tabela de precos / relatorio da Meta.
    # Em reais, com fracao de centavo (tarifa vigente x mensagem cobravel).
    custo_estimado = Column(Numeric(14, 6), nullable=True)
    moeda = Column(String(3), nullable=True)

    # Para a sessao e o card do CRM poderem ser ligados depois.
    lead_id = Column(Integer, nullable=True)
    observacao = Column(Text, nullable=True)
