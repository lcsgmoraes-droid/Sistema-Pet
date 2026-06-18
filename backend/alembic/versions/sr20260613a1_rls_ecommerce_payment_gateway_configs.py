"""enable RLS on ecommerce payment gateway configs

Revision ID: sr20260613a1
Revises: sq20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "sr20260613a1"
down_revision = "sq20260613a1"
branch_labels = None
depends_on = None


PAYMENT_GATEWAY_CONFIGS_RLS_TABLE = "ecommerce_payment_gateway_configs"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
WEBHOOK_TOKEN_SETTING = "app.payment_webhook_token"
TENANT_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
WEBHOOK_TOKEN_GUARD = (
    "provider = 'mercadopago' "
    f"AND webhook_token = NULLIF(current_setting('{WEBHOOK_TOKEN_SETTING}', true), '')"
)

POLICY_NAMES = (
    "ecommerce_payment_gateway_configs_tenant_select",
    "ecommerce_payment_gateway_configs_webhook_select",
    "ecommerce_payment_gateway_configs_tenant_insert",
    "ecommerce_payment_gateway_configs_tenant_update",
    "ecommerce_payment_gateway_configs_tenant_delete",
)


def _is_postgresql_table_present() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return sa.inspect(bind).has_table(PAYMENT_GATEWAY_CONFIGS_RLS_TABLE)


def _drop_policies(policy_names: tuple[str, ...] = POLICY_NAMES) -> None:
    for policy_name in policy_names:
        op.execute(
            f"DROP POLICY IF EXISTS {policy_name} ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE}"
        )


def upgrade() -> None:
    if not _is_postgresql_table_present():
        return

    op.execute(
        f"ALTER TABLE {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        f"ALTER TABLE {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} FORCE ROW LEVEL SECURITY"
    )
    _drop_policies()

    op.execute(
        f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_select "
        f"ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} FOR SELECT USING ({TENANT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY ecommerce_payment_gateway_configs_webhook_select "
        f"ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} FOR SELECT USING ({WEBHOOK_TOKEN_GUARD})"
    )
    op.execute(
        f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_insert "
        f"ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} FOR INSERT WITH CHECK ({TENANT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_update "
        f"ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} "
        f"FOR UPDATE USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_delete "
        f"ON {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} FOR DELETE USING ({TENANT_GUARD})"
    )


def downgrade() -> None:
    if not _is_postgresql_table_present():
        return

    _drop_policies(tuple(reversed(POLICY_NAMES)))
    op.execute(
        f"ALTER TABLE {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} NO FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        f"ALTER TABLE {PAYMENT_GATEWAY_CONFIGS_RLS_TABLE} DISABLE ROW LEVEL SECURITY"
    )
