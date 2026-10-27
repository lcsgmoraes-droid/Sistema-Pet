"""Vigência de comissão pela inclusão técnica da venda, sem alterar snapshots."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzz20261026a4"
down_revision = "zzzzz20261026a3"
branch_labels = None
depends_on = None


def upgrade():
    # Fecha a janela entre fotografar o baseline e instalar o trigger. Escritas
    # aguardam o mesmo commit; nenhuma alteração de regra fica sem versão.
    op.execute("LOCK TABLE public.comissoes_configuracao IN SHARE ROW EXCLUSIVE MODE")
    # DEFAULT estável aproveita o fast default do PostgreSQL para as linhas
    # legadas. O instante de corte congela o baseline conhecido, sem reinterpretar
    # created_at/data_venda de importações nem inventar versões anteriores.
    op.add_column(
        "vendas",
        sa.Column(
            "comissao_ancora_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Inclusões futuras usam o instante efetivo do INSERT, não o início da transação.
    op.alter_column(
        "vendas",
        "comissao_ancora_em",
        server_default=sa.text("clock_timestamp()"),
    )
    op.create_table(
        "comissoes_configuracao_versoes",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "funcionario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False
        ),
        sa.Column("configuracao_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("referencia_id", sa.Integer(), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_comissao_versao_tenant_parceiro_escopo",
        "comissoes_configuracao_versoes",
        ["tenant_id", "funcionario_id", "tipo", "referencia_id", "vigente_desde"],
    )
    # A migração usa o papel administrativo; a aplicação continua sujeita a RLS.
    op.execute("SET LOCAL row_security = off")
    op.execute("""
        INSERT INTO comissoes_configuracao_versoes
            (tenant_id, funcionario_id, configuracao_id, tipo, referencia_id, vigente_desde, payload)
        SELECT tenant_id, funcionario_id, id, tipo, referencia_id,
               TIMESTAMPTZ '0001-01-01 00:00:00+00', to_jsonb(c)
        FROM comissoes_configuracao c
    """)
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=["comissoes_configuracao_versoes"],
        enable=True,
    )
    op.execute("SET LOCAL row_security = on")
    op.execute("""
        CREATE FUNCTION public.registrar_versao_comissao() RETURNS trigger
        LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
        DECLARE instante timestamptz := clock_timestamp();
        BEGIN
            IF TG_OP = 'UPDATE' AND
               (to_jsonb(NEW) - 'created_at' - 'updated_at') =
               (to_jsonb(OLD) - 'created_at' - 'updated_at') THEN
                RETURN NEW;
            END IF;
            IF TG_OP = 'DELETE' OR (
                TG_OP = 'UPDATE' AND
                (NEW.tenant_id, NEW.funcionario_id, NEW.tipo, NEW.referencia_id)
                IS DISTINCT FROM
                (OLD.tenant_id, OLD.funcionario_id, OLD.tipo, OLD.referencia_id)
            ) THEN
                INSERT INTO public.comissoes_configuracao_versoes
                    (tenant_id, funcionario_id, configuracao_id, tipo, referencia_id, vigente_desde, payload)
                VALUES (OLD.tenant_id, OLD.funcionario_id, OLD.id, OLD.tipo, OLD.referencia_id,
                        instante, jsonb_set(to_jsonb(OLD), '{ativo}', 'false'::jsonb));
            END IF;
            IF TG_OP <> 'DELETE' THEN
                INSERT INTO public.comissoes_configuracao_versoes
                    (tenant_id, funcionario_id, configuracao_id, tipo, referencia_id, vigente_desde, payload)
                VALUES (NEW.tenant_id, NEW.funcionario_id, NEW.id, NEW.tipo, NEW.referencia_id,
                        instante, to_jsonb(NEW));
                RETURN NEW;
            END IF;
            RETURN OLD;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER comissao_registrar_versao
        AFTER INSERT OR UPDATE OR DELETE ON public.comissoes_configuracao
        FOR EACH ROW EXECUTE FUNCTION public.registrar_versao_comissao()
    """)
    op.execute("""
        CREATE FUNCTION public.proteger_ancora_comissao_venda() RETURNS trigger
        LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                NEW.comissao_ancora_em := clock_timestamp();
            ELSIF NEW.comissao_ancora_em IS DISTINCT FROM OLD.comissao_ancora_em THEN
                RAISE EXCEPTION 'A inclusão técnica da venda para comissão é imutável'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER venda_proteger_ancora_comissao
        BEFORE INSERT OR UPDATE ON public.vendas
        FOR EACH ROW EXECUTE FUNCTION public.proteger_ancora_comissao_venda()
    """)


def downgrade():
    op.execute("SET LOCAL row_security = off")
    if (
        op.get_bind()
        .execute(
            sa.text("""
        SELECT 1 FROM comissoes_configuracao_versoes
        WHERE vigente_desde > TIMESTAMPTZ '0001-01-01 00:00:00+00' LIMIT 1
    """)
        )
        .first()
    ):
        raise RuntimeError(
            "Vigência de comissões possui histórico; downgrade exige plano de preservação."
        )
    # Somente uma instalação ainda sem alterações versionadas pode ser desfeita.
    op.execute("DROP TRIGGER venda_proteger_ancora_comissao ON public.vendas")
    op.execute("DROP FUNCTION public.proteger_ancora_comissao_venda()")
    op.execute(
        "DROP TRIGGER comissao_registrar_versao ON public.comissoes_configuracao"
    )
    op.execute("DROP FUNCTION public.registrar_versao_comissao()")
    op.drop_table("comissoes_configuracao_versoes")
    op.drop_column("vendas", "comissao_ancora_em")
