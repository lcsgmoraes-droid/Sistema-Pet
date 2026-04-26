"""Modelos de templates de retorno do Banho & Tosa."""

from sqlalchemy import Boolean, Column, Index, String, Text, UniqueConstraint

from app.base_models import BaseTenantModel


class BanhoTosaRetornoTemplate(BaseTenantModel):
    __tablename__ = "banho_tosa_retorno_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", "canal", name="uq_bt_retorno_templates_nome_canal"),
        Index("ix_bt_retorno_templates_tipo_canal", "tenant_id", "tipo_retorno", "canal", "ativo"),
    )

    nome = Column(String(120), nullable=False, index=True)
    tipo_retorno = Column(String(40), nullable=False, default="todos", index=True)
    canal = Column(String(30), nullable=False, default="app", index=True)
    assunto = Column(String(180), nullable=False)
    mensagem = Column(Text, nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
