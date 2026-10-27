"""Grupos de produtos reutilizáveis nos relatórios e na provisão de comissões."""

from sqlalchemy import Boolean, Column, JSON, String, UniqueConstraint

from app.base_models import BaseTenantModel


class ComissaoGrupoProdutos(BaseTenantModel):
    __tablename__ = "comissoes_grupos_produtos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_comissoes_grupos_tenant_nome"),
    )

    nome = Column(String(120), nullable=False)
    produto_ids = Column(JSON, nullable=False, default=list)
    ativo = Column(Boolean, nullable=False, default=True)
