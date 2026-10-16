"""Audit helpers for the final PostgreSQL RLS ratchet."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


INTENTIONALLY_GLOBAL_NO_RLS_TABLES = frozenset(
    {
        "bling_company_tenant_links",
        "bling_pedido_webhook_events",
        "campaign_event_queue",
        "ecommerceai_connection_requests",
        "ecommerceai_connections",
        "notification_queue",
        "ops_alerts",
        "ops_error_events",
        "ops_journey_events",
        "ops_tenant_onboarding_notes",
        "oferta_publicacao_tokens",
        "rotas_entrega_rastreio_tokens",
        "tenant_login_names",
        "user_sessions",
    }
)

# Historicos (TenantScoped, nao BaseTenantModel) cuja visibilidade de leitura
# segue o registro-pai (cliente/pet/produto) no grupo comercial — ver
# app/tenancy/filters.py::_tenant_scoped_read_filter e _PAI_DO_HISTORICO. Uma
# politica RLS simples (tenant_id = current) nao consegue expressar "visivel
# tambem se o pai for visivel para este tenant no grupo", entao a protecao e
# feita no filtro de leitura automatico da aplicacao, nao no Postgres.
# produto_identidades_historico_alteracoes segue o mesmo mixin porque rastreia
# a ProdutoIdentidade, que por natureza e compartilhada entre as lojas do
# grupo (nao pertence a um unico tenant).
INTENTIONALLY_TENANT_SCOPED_NO_RLS_TABLES = frozenset(
    {
        "clientes_historico_alteracoes",
        "pets_historico_alteracoes",
        "pets_registros_clinicos",
        "produto_identidades_historico_alteracoes",
        "produtos_historico_alteracoes",
    }
)

ALL_INTENTIONAL_NO_RLS_TABLES = frozenset(
    INTENTIONALLY_GLOBAL_NO_RLS_TABLES | INTENTIONALLY_TENANT_SCOPED_NO_RLS_TABLES
)


TENANT_ID_TABLES_WITHOUT_RLS_SQL = text(
    """
    SELECT c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relname NOT LIKE 'pg_%'
      AND c.relname NOT LIKE 'sql_%'
      AND EXISTS (
          SELECT 1
          FROM information_schema.columns col
          WHERE col.table_schema = 'public'
            AND col.table_name = c.relname
            AND col.column_name = 'tenant_id'
      )
      AND NOT c.relrowsecurity
    ORDER BY c.relname
    """
)


def tenant_id_tables_without_rls(db: Session) -> list[str]:
    rows = db.execute(TENANT_ID_TABLES_WITHOUT_RLS_SQL).all()
    return [str(row[0]) for row in rows]


def unexpected_tenant_id_tables_without_rls(db: Session) -> list[str]:
    tables = set(tenant_id_tables_without_rls(db))
    return sorted(tables - ALL_INTENTIONAL_NO_RLS_TABLES)


def assert_no_unexpected_no_rls_tables(db: Session) -> list[str]:
    unexpected = unexpected_tenant_id_tables_without_rls(db)
    if unexpected:
        allowed = ", ".join(sorted(ALL_INTENTIONAL_NO_RLS_TABLES))
        found = ", ".join(unexpected)
        raise RuntimeError(
            "Unexpected tenant_id table(s) without PostgreSQL RLS: "
            f"{found}. Only intentional globals/app-filtered historicos may "
            f"remain without RLS: {allowed}."
        )
    return unexpected
