"""Desativa envio por emissão e agendamentos avulsos, preservando o histórico."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzi20261019a1"
down_revision = "zzzzh20261019a1"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    postgres = conn.dialect.name == "postgresql"
    anterior = (
        conn.execute(sa.text("SELECT current_setting('app.tenant_id', true)")).scalar()
        if postgres
        else None
    )
    # O diretório de empresas é global; cada alteração abaixo continua passando
    # pelas políticas FORCE RLS, limitada explicitamente à empresa corrente.
    tenants = conn.execute(sa.text("SELECT id FROM tenants")).scalars().all()
    try:
        for tenant_id in tenants:
            params = {"tenant": str(tenant_id)}
            if postgres:
                conn.execute(
                    sa.text("SELECT set_config('app.tenant_id', :tenant, true)"),
                    params,
                )
            conn.execute(
                sa.text(
                    "UPDATE xml_contabilidade_config "
                    "SET envio_automatico = false, envio_automatico_desde = NULL "
                    "WHERE tenant_id = :tenant"
                ),
                params,
            )
            conn.execute(
                sa.text(
                    "UPDATE xml_contabilidade_envios "
                    "SET status = 'cancelado', ultimo_erro = "
                    "'O envio automático agora é somente mensal, do mês anterior completo. "
                    "Para outro período, crie um lote manual.' "
                    "WHERE tenant_id = :tenant "
                    "AND origem IN ('automatico', 'agendado') "
                    "AND status IN ('pendente', 'agendado')"
                ),
                params,
            )
    finally:
        if postgres:
            conn.execute(
                sa.text("SELECT set_config('app.tenant_id', :tenant, true)"),
                {"tenant": anterior or ""},
            )


def downgrade():
    # Não reativa envios antigos: um rollback jamais pode enviar notas sozinho.
    pass
