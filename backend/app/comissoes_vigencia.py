"""Regras imutáveis por versão, escolhidas pela inclusão técnica da venda."""

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    JSON,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.base_models import TenantScoped
from app.db import Base
from app.tenancy.context import get_current_tenant_id
from app.tenancy.rls import sync_rls_tenant
from app.utils.tenant_safe_sql import TenantSafeSQLError, execute_tenant_safe


class ComissaoConfiguracaoVersao(TenantScoped, Base):
    __tablename__ = "comissoes_configuracao_versoes"
    __table_args__ = (
        Index(
            "ix_comissao_versao_tenant_parceiro_escopo",
            "tenant_id",
            "funcionario_id",
            "tipo",
            "referencia_id",
            "vigente_desde",
        ),
    )

    id = Column(Integer, Identity(always=True), primary_key=True)
    # O vínculo atual permite que a fusão de pessoas transfira o histórico.
    funcionario_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    configuracao_id = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False)
    referencia_id = Column(Integer, nullable=False)
    vigente_desde = Column(DateTime(timezone=True), nullable=False)
    payload = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)


def bloquear_alteracao_comissao_por_tenant(db, tenant_id):
    """A fusão adquire este lock antes dos locks de pessoa; SQLite é só fixture."""
    if db.get_bind().dialect.name != "postgresql":
        return
    sync_rls_tenant(db, tenant_id)
    db.execute(
        text(
            "SELECT public.bloquear_vigencia_comissao_empresa(CAST(:tenant_id AS uuid), true)"
        ),
        {"tenant_id": str(tenant_id)},
    )


def normalizar_instante_utc(valor):
    """Âncora nova é UTC aware; valores sem tz só existem em fixtures SQLite."""
    if valor is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def carregar_configuracoes_vigentes(db, funcionario_id, criada_em, tenant_id=None):
    """Uma consulta por venda; ausência histórica nunca usa configuração atual."""
    tenant_id = tenant_id if tenant_id is not None else get_current_tenant_id()
    if tenant_id is None or tenant_id == "":
        raise TenantSafeSQLError(
            "tenant_id obrigatório para consultar vigência de comissão"
        )
    instante = normalizar_instante_utc(criada_em)
    # SQLite não adapta datetime aware em consultas textuais como PostgreSQL.
    if db.get_bind().dialect.name == "sqlite":
        instante = instante.replace(tzinfo=None)
    rows = execute_tenant_safe(
        db,
        """
        SELECT payload FROM (
            SELECT payload,
                   ROW_NUMBER() OVER (
                       PARTITION BY tipo, referencia_id
                       ORDER BY vigente_desde DESC, id DESC
                   ) AS ordem
            FROM comissoes_configuracao_versoes
            WHERE funcionario_id = :funcionario_id
              AND vigente_desde <= :criada_em
              AND {tenant_filter}
        ) historico
        WHERE ordem = 1
        """,
        {"funcionario_id": funcionario_id, "criada_em": instante},
        tenant_id=tenant_id,
    ).fetchall()
    resultado = {}
    for row in rows:
        payload = json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])
        # A fusão atualiza a FK sem reescrever o snapshot JSON original.
        payload["funcionario_id"] = funcionario_id
        resultado[(payload["tipo"], int(payload["referencia_id"]))] = payload
    return resultado
