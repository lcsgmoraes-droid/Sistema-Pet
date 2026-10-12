"""Remove pessoa_mestre: Pessoa passou a ser compartilhada pelo grupo
comercial inteiro via RLS (ver migrations zzzq20261005a1/zzzv20261005a1 e
app/tenancy/filters.py::pessoa_visivel_no_grupo) - um unico registro de
Cliente, visivel e editavel por qualquer loja do grupo, em vez de uma copia
por loja vinculada manualmente a uma "pessoa-mestre" separada. O mecanismo
de pessoa-mestre (so o titular do grupo, vinculo opcional) ficou orfo: 0
linhas em producao em pessoa_mestre e em clientes.pessoa_mestre_id. Removido
junto com o modelo `PessoaMestre`, o service e as rotas `/pessoa-mestre`.

Revision ID: zzzy20261009a1
Revises: zzzx20261007a1
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzy20261009a1"
down_revision = "zzzx20261007a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_clientes_pessoa_mestre", "clientes", type_="foreignkey"
    )
    op.drop_column("clientes", "pessoa_mestre_id")
    op.drop_table("pessoa_mestre")


def downgrade() -> None:
    # Remocao deliberada de feature sem uso (0 linhas em producao - mesmo
    # padrao ja usado em zzzd20260920a1 e zzzx20261007a1). Recria so a
    # estrutura; nao ha dado a restaurar.
    op.create_table(
        "pessoa_mestre",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("tipo_pessoa", sa.String(length=2), nullable=True),
        sa.Column("cpf", sa.String(length=14), nullable=True),
        sa.Column("cnpj", sa.String(length=18), nullable=True),
        sa.Column("inscricao_estadual", sa.String(length=20), nullable=True),
        sa.Column("razao_social", sa.String(length=255), nullable=True),
        sa.Column("nome_fantasia", sa.String(length=255), nullable=True),
        sa.Column("crmv", sa.String(length=20), nullable=True),
        sa.Column("data_nascimento", sa.DateTime(), nullable=True),
        sa.Column("telefone", sa.String(length=50), nullable=True),
        sa.Column("celular", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("cep", sa.String(length=10), nullable=True),
        sa.Column("endereco", sa.String(length=500), nullable=True),
        sa.Column("numero", sa.String(length=20), nullable=True),
        sa.Column("complemento", sa.String(length=100), nullable=True),
        sa.Column("bairro", sa.String(length=100), nullable=True),
        sa.Column("cidade", sa.String(length=100), nullable=True),
        sa.Column("estado", sa.String(length=2), nullable=True),
        sa.Column("codigo_municipio", sa.String(length=7), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "is_cliente", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_fornecedor", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_veterinario", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_funcionario", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.UniqueConstraint(
            "grupo_id", "cpf", name="uq_pessoa_mestre_grupo_cpf"
        ),
        sa.UniqueConstraint(
            "grupo_id", "cnpj", name="uq_pessoa_mestre_grupo_cnpj"
        ),
    )
    op.create_index("ix_pessoa_mestre_grupo_id", "pessoa_mestre", ["grupo_id"])
    op.create_index("ix_pessoa_mestre_cpf", "pessoa_mestre", ["cpf"])
    op.create_index("ix_pessoa_mestre_cnpj", "pessoa_mestre", ["cnpj"])

    op.add_column(
        "clientes", sa.Column("pessoa_mestre_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_clientes_pessoa_mestre",
        "clientes",
        "pessoa_mestre",
        ["pessoa_mestre_id"],
        ["id"],
        ondelete="SET NULL",
    )
