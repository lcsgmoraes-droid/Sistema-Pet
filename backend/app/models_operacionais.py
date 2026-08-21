"""Modelos operacionais extraidos de app.models."""

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class FeatureFlag(BaseTenantModel):
    """
    Feature Flags por tenant para ativar/desativar funcionalidades.

    Permite controle granular de features experimentais ou em rollout gradual,
    garantindo que o sistema nunca dependa de features desligadas para funcionar.

    Exemplo: PDV_IA_OPORTUNIDADES pode ser ativada apenas para tenants específicos
    durante o período de testes, sem afetar os demais usuários.
    """

    __tablename__ = "feature_flags"

    feature_key = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Identificador único da feature (ex: PDV_IA_OPORTUNIDADES)",
    )
    enabled = Column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
        comment="Status da feature: true=ativa, false=desligada",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "feature_key", name="uq_feature_flags_tenant_feature"
        ),
        Index(
            "ix_feature_flags_tenant_feature_lookup",
            "tenant_id",
            "feature_key",
            "enabled",
        ),
    )

    def __repr__(self):
        return f"<FeatureFlag(tenant_id={self.tenant_id}, feature_key={self.feature_key}, enabled={self.enabled})>"


class ConfiguracaoEntrega(BaseTenantModel):
    """
    Configuração global de entregas por tenant.
    Um único registro por tenant.
    """

    __tablename__ = "configuracoes_entrega"

    # Usuario dono da configuracao (legacy schema exige NOT NULL)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Entregador padrão (FK para clientes.id que é Integer)
    entregador_padrao_id = Column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )

    # Ponto inicial da rota (endereço detalhado da loja/empresa)
    logradouro = Column(String(300), nullable=True)  # Rua/Avenida
    cep = Column(String(9), nullable=True)  # 00000-000
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)  # UF

    # Método de registro de km ao marcar entrega: "auto_rota" | "gps" | "manual"
    metodo_km_entrega = Column(
        String(20), nullable=False, default="auto_rota", server_default="auto_rota"
    )

    # Politica comercial compartilhada pelo app e ecommerce
    entrega_ativa = Column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    retirada_ativa = Column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    modalidade_cobranca = Column(
        String(20), nullable=False, default="fixa", server_default="fixa"
    )
    taxa_fixa = Column(DECIMAL(10, 2), nullable=False, default=0, server_default="0")
    valor_por_km_cobrado = Column(DECIMAL(10, 2), nullable=True)
    taxa_minima = Column(DECIMAL(10, 2), nullable=False, default=0, server_default="0")
    faixas_distancia = Column(
        JSON_DOCUMENT, nullable=False, default=list, server_default=sa.text("'[]'")
    )
    valor_km_excedente = Column(DECIMAL(10, 2), nullable=True)
    distancia_maxima_entrega_km = Column(DECIMAL(10, 2), nullable=True)
    frete_gratis_acima = Column(DECIMAL(10, 2), nullable=True)
    distancia_maxima_frete_gratis_km = Column(DECIMAL(10, 2), nullable=True)
    pedido_minimo = Column(
        DECIMAL(10, 2), nullable=False, default=0, server_default="0"
    )
    prazo_entrega_texto = Column(String(120), nullable=True)

    # Relacionamento com o entregador padrão
    entregador_padrao = relationship("Cliente", foreign_keys=[entregador_padrao_id])


class CreditoLog(BaseTenantModel):
    """Registro de cada movimentação de crédito de um cliente."""

    __tablename__ = "credito_logs"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(30), nullable=False, index=True)
    # tipos possíveis: 'adicao_manual', 'remocao_manual', 'uso_venda', 'troco', 'devolucao'
    valor = Column(DECIMAL(10, 2), nullable=False)  # sempre positivo
    saldo_anterior = Column(DECIMAL(10, 2), nullable=False)
    saldo_atual = Column(DECIMAL(10, 2), nullable=False)
    motivo = Column(Text, nullable=True)
    referencia_id = Column(Integer, nullable=True)  # venda_id ou outro id relacionado
    usuario_nome = Column(String(255), nullable=True)  # nome de quem fez a operação
