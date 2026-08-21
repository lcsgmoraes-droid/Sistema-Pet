"""add inactive card operator presets for existing tenants

Revision ID: zws20260821a1
Revises: zwr20260821a1
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "zws20260821a1"
down_revision = "zwr20260821a1"
branch_labels = None
depends_on = None


OPERATOR_PRESETS = (
    ("Stone", "STONE", "#00A868"),
    ("Cielo", "CIELO", "#006CB7"),
    ("Rede", "REDE", "#EC7000"),
    ("Getnet", "GETNET", "#E30613"),
    ("PagBank", "PAGBANK", "#00A868"),
    ("Mercado Pago", "MERCADO_PAGO", "#009EE3"),
    ("SafraPay", "SAFRAPAY", "#B08D2F"),
    ("SumUp", "SUMUP", "#111827"),
    ("Ton", "TON", "#00D17A"),
)


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _set_rls(bind, table_names: list[str], *, enabled: bool) -> None:
    if bind.dialect.name != "postgresql":
        return
    for table_name in table_names:
        if enabled:
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        else:
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    if not {"operadoras_cartao", "users"}.issubset(tables):
        return

    rls_tables = [
        table_name
        for table_name in ("users", "user_tenants", "operadoras_cartao")
        if table_name in tables
    ]
    _set_rls(bind, rls_tables, enabled=False)

    membership_source = ""
    if "user_tenants" in tables:
        membership_source = """
            SELECT tenant_id, user_id, 1 AS priority
            FROM user_tenants
            WHERE COALESCE(is_active, true) = true
            UNION ALL
        """

    values_sql = ",\n".join(
        f"('{name}', '{code}', '{color}')" for name, code, color in OPERATOR_PRESETS
    )
    bind.execute(
        sa.text(
            f"""
            WITH user_candidates AS (
                {membership_source}
                SELECT tenant_id, id AS user_id, 2 AS priority
                FROM users
                WHERE tenant_id IS NOT NULL
            ), tenant_users AS (
                SELECT DISTINCT ON (tenant_id) tenant_id, user_id
                FROM user_candidates
                WHERE tenant_id IS NOT NULL
                ORDER BY tenant_id, priority, user_id
            ), presets(nome, codigo, cor) AS (
                VALUES {values_sql}
            )
            INSERT INTO operadoras_cartao (
                tenant_id, user_id, nome, codigo, max_parcelas, padrao, ativo,
                api_enabled, cor, icone, created_at, updated_at
            )
            SELECT
                tenant_users.tenant_id, tenant_users.user_id, presets.nome,
                presets.codigo, 12, false, false, false, presets.cor, '💳',
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM tenant_users
            CROSS JOIN presets
            WHERE NOT EXISTS (
                SELECT 1
                FROM operadoras_cartao existing
                WHERE existing.tenant_id = tenant_users.tenant_id
                  AND (
                      lower(COALESCE(existing.codigo, '')) = lower(presets.codigo)
                      OR lower(trim(existing.nome)) = lower(presets.nome)
                      OR lower(trim(existing.nome)) LIKE lower(presets.nome) || ' %'
                  )
            )
            """
        )
    )
    _set_rls(bind, rls_tables, enabled=True)


def downgrade() -> None:
    # Preserva os cadastros do tenant: depois do upgrade nao e possivel distinguir
    # com seguranca um preset ainda inativo de uma operadora editada pelo usuario.
    pass
