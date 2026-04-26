"""Modelos de avaliacao/NPS do Banho & Tosa."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaAvaliacao(BaseTenantModel):
    __tablename__ = "banho_tosa_avaliacoes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "atendimento_id", "cliente_id", name="uq_bt_avaliacao_atendimento_cliente"),
        Index("ix_bt_avaliacoes_cliente_pet", "tenant_id", "cliente_id", "pet_id"),
    )

    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    nota_nps = Column(Integer, nullable=False)
    nota_servico = Column(Integer, nullable=True)
    comentario = Column(Text, nullable=True)
    origem = Column(String(30), nullable=False, default="app")

    atendimento = relationship("BanhoTosaAtendimento", back_populates="avaliacoes")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
