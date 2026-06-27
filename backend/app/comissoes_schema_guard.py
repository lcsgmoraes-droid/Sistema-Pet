"""Compatibilidade e saneamento do schema legado de configuracao de comissoes."""

from sqlalchemy import text

from .tenancy.context import get_current_tenant_id
from .tenancy.rls import sync_rls_tenant

_comissoes_schema_checked = False


def ensure_comissoes_config_schema(db) -> None:
    """Garante coluna tenant_id em comissoes_configuracao para compatibilidade."""
    global _comissoes_schema_checked
    if _comissoes_schema_checked:
        return

    tenant_id = get_current_tenant_id()
    if tenant_id:
        sync_rls_tenant(db, tenant_id)

    db.execute(
        text(
            "ALTER TABLE comissoes_configuracao ADD COLUMN IF NOT EXISTS tenant_id uuid"
        )
    )
    if tenant_id:
        db.execute(
            text("""
                UPDATE comissoes_configuracao cc
                SET tenant_id = c.tenant_id
                FROM clientes c
                WHERE cc.funcionario_id = c.id
                  AND c.tenant_id = :tenant_id
                  AND cc.tenant_id IS NULL
            """),
            {"tenant_id": str(tenant_id)},
        )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_comissoes_configuracao_tenant_id "
            "ON comissoes_configuracao (tenant_id)"
        )
    )
    db.commit()
    _comissoes_schema_checked = True
