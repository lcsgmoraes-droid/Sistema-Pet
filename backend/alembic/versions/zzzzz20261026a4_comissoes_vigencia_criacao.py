"""Vigência de comissão pela inclusão técnica da venda, sem alterar snapshots."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzz20261026a4"
down_revision = "zzzzz20261026a3"
branch_labels = None
depends_on = None


SERIALIZACAO_SQL = (
    """
    CREATE OR REPLACE FUNCTION public.bloquear_vigencia_comissao_empresa(
        empresa uuid, exclusivo boolean
    ) RETURNS void LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
    DECLARE chave bigint;
    BEGIN
        IF empresa IS NULL THEN
            RAISE EXCEPTION 'Tenant obrigatório para ordenar a vigência de comissão'
                USING ERRCODE = '42501';
        END IF;
        chave := hashtextextended('corepet:comissao:' || empresa::text, 0);
        IF exclusivo THEN
            PERFORM pg_advisory_xact_lock(chave);
        ELSE
            PERFORM pg_advisory_xact_lock_shared(chave);
        END IF;
    END;
    $$
    """,
    """
    CREATE OR REPLACE FUNCTION public.bloquear_alteracao_comissao() RETURNS trigger
    LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
    BEGIN
        PERFORM public.bloquear_vigencia_comissao_empresa(
            NULLIF(current_setting('app.tenant_id', true), '')::uuid, true
        );
        RETURN NULL;
    END;
    $$
    """,
    """
    CREATE OR REPLACE FUNCTION public.validar_empresa_regra_comissao() RETURNS trigger
    LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
    DECLARE empresa uuid := NULLIF(current_setting('app.tenant_id', true), '')::uuid;
    BEGIN
        IF TG_OP <> 'INSERT' AND OLD.tenant_id IS DISTINCT FROM empresa THEN
            RAISE EXCEPTION 'A regra de comissão deve pertencer ao tenant da transação'
                USING ERRCODE = '42501';
        END IF;
        IF TG_OP <> 'DELETE' AND NEW.tenant_id IS DISTINCT FROM empresa THEN
            RAISE EXCEPTION 'A regra de comissão deve pertencer ao tenant da transação'
                USING ERRCODE = '42501';
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
    END;
    $$
    """,
    "DROP TRIGGER IF EXISTS comissao_bloquear_alteracao ON public.comissoes_configuracao",
    """
    CREATE TRIGGER comissao_bloquear_alteracao
    BEFORE INSERT OR UPDATE OR DELETE ON public.comissoes_configuracao
    FOR EACH STATEMENT EXECUTE FUNCTION public.bloquear_alteracao_comissao()
    """,
    "DROP TRIGGER IF EXISTS comissao_validar_empresa ON public.comissoes_configuracao",
    """
    CREATE TRIGGER comissao_validar_empresa
    BEFORE INSERT OR UPDATE OR DELETE ON public.comissoes_configuracao
    FOR EACH ROW EXECUTE FUNCTION public.validar_empresa_regra_comissao()
    """,
)

ANCORA_SQL = """
    CREATE OR REPLACE FUNCTION public.proteger_ancora_comissao_venda() RETURNS trigger
    LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            PERFORM public.bloquear_vigencia_comissao_empresa(NEW.tenant_id, false);
            NEW.comissao_ancora_em := clock_timestamp();
        ELSIF NEW.comissao_ancora_em IS DISTINCT FROM OLD.comissao_ancora_em THEN
            RAISE EXCEPTION 'A inclusão técnica da venda para comissão é imutável'
                USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END;
    $$
"""


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
    # Antes dos locks de linha da configuração. Vendas seguem em paralelo,
    # mas nenhuma inclusão cruza uma alteração ainda sem commit.
    for sql in SERIALIZACAO_SQL:
        op.execute(sql)
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
    op.execute(ANCORA_SQL)
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
    op.execute(
        "DROP TRIGGER comissao_bloquear_alteracao ON public.comissoes_configuracao"
    )
    op.execute("DROP TRIGGER comissao_validar_empresa ON public.comissoes_configuracao")
    op.execute("DROP FUNCTION public.bloquear_alteracao_comissao()")
    op.execute("DROP FUNCTION public.validar_empresa_regra_comissao()")
    op.execute("DROP FUNCTION public.bloquear_vigencia_comissao_empresa(uuid, boolean)")
    op.drop_table("comissoes_configuracao_versoes")
    op.drop_column("vendas", "comissao_ancora_em")
