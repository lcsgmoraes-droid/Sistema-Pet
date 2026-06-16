"""create dre classificacao rules

Revision ID: oz20260525a1
Revises: oy20260521a2
Create Date: 2026-05-25 10:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "oz20260525a1"
down_revision: Union[str, Sequence[str], None] = "oy20260521a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _uuid_type():
    if _dialect_name() == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _json_type():
    if _dialect_name() == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _drop_column_once(table_name: str, column_name: str) -> None:
    if column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def _create_index_once(
    name: str, table_name: str, columns: list[str], **kwargs
) -> None:
    if _has_table(table_name) and name not in _indexes(table_name):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_once(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


def _create_regras_table() -> None:
    if _has_table("regras_classificacao_dre"):
        return

    op.create_table(
        "regras_classificacao_dre",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "tenant_id",
            _uuid_type(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo_regra", sa.String(50), nullable=False),
        sa.Column("origem", sa.String(50), nullable=False, server_default="SISTEMA"),
        sa.Column("criterios", _json_type(), nullable=False),
        sa.Column(
            "dre_subcategoria_id",
            sa.Integer(),
            sa.ForeignKey("dre_subcategorias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canal", sa.String(50), nullable=True),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("confianca", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "aplicacoes_sucesso", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "aplicacoes_rejeitadas", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "sugerir_apenas", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("criado_por_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_historico_table() -> None:
    if _has_table("historico_classificacao_dre"):
        return

    op.create_table(
        "historico_classificacao_dre",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "tenant_id",
            _uuid_type(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("tipo_lancamento", sa.String(20), nullable=False),
        sa.Column("lancamento_id", sa.Integer(), nullable=False),
        sa.Column(
            "dre_subcategoria_id",
            sa.Integer(),
            sa.ForeignKey("dre_subcategorias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canal", sa.String(50), nullable=True),
        sa.Column("forma_classificacao", sa.String(50), nullable=False),
        sa.Column(
            "regra_aplicada_id",
            sa.Integer(),
            sa.ForeignKey("regras_classificacao_dre.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("beneficiario", sa.String(255), nullable=True),
        sa.Column("tipo_documento", sa.String(50), nullable=True),
        sa.Column("valor", sa.BigInteger(), nullable=False),
        sa.Column(
            "usuario_aceitou", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("classificado_por_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def _backfill_beneficiarios() -> None:
    if _dialect_name() != "postgresql":
        return

    contas_pagar_cols = _columns("contas_pagar")
    clientes_cols = _columns("clientes")
    if {"fornecedor_id", "beneficiario", "tenant_id"}.issubset(contas_pagar_cols) and {
        "id",
        "nome",
        "tenant_id",
    }.issubset(clientes_cols):
        op.execute(
            """
            UPDATE contas_pagar cp
               SET beneficiario = c.nome
              FROM clientes c
             WHERE cp.fornecedor_id = c.id
               AND cp.tenant_id = c.tenant_id
               AND cp.beneficiario IS NULL
            """
        )

    contas_receber_cols = _columns("contas_receber")
    if {"cliente_id", "beneficiario", "tenant_id"}.issubset(contas_receber_cols) and {
        "id",
        "nome",
        "tenant_id",
    }.issubset(clientes_cols):
        op.execute(
            """
            UPDATE contas_receber cr
               SET beneficiario = c.nome
              FROM clientes c
             WHERE cr.cliente_id = c.id
               AND cr.tenant_id = c.tenant_id
               AND cr.beneficiario IS NULL
            """
        )

    if {"afeta_dre", "nota_entrada_id"}.issubset(contas_pagar_cols):
        op.execute(
            "UPDATE contas_pagar SET afeta_dre = FALSE WHERE nota_entrada_id IS NOT NULL"
        )


def upgrade() -> None:
    _add_column_once(
        "contas_pagar", sa.Column("beneficiario", sa.String(255), nullable=True)
    )
    _add_column_once(
        "contas_pagar", sa.Column("tipo_documento", sa.String(50), nullable=True)
    )
    _add_column_once(
        "contas_pagar",
        sa.Column("afeta_dre", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _add_column_once(
        "contas_receber", sa.Column("beneficiario", sa.String(255), nullable=True)
    )
    _add_column_once(
        "contas_receber", sa.Column("tipo_documento", sa.String(50), nullable=True)
    )

    _create_index_once(
        "idx_contas_pagar_beneficiario", "contas_pagar", ["tenant_id", "beneficiario"]
    )
    _create_index_once(
        "idx_contas_pagar_tipo_documento",
        "contas_pagar",
        ["tenant_id", "tipo_documento"],
    )
    _create_index_once(
        "idx_contas_pagar_afeta_dre", "contas_pagar", ["tenant_id", "afeta_dre"]
    )
    _create_index_once(
        "idx_contas_receber_beneficiario",
        "contas_receber",
        ["tenant_id", "beneficiario"],
    )
    _create_index_once(
        "idx_contas_receber_tipo_documento",
        "contas_receber",
        ["tenant_id", "tipo_documento"],
    )

    _create_regras_table()
    _create_historico_table()

    _create_index_once(
        "idx_regras_classificacao_tenant", "regras_classificacao_dre", ["tenant_id"]
    )
    _create_index_once(
        "idx_regras_classificacao_tipo",
        "regras_classificacao_dre",
        ["tenant_id", "tipo_regra"],
    )
    _create_index_once(
        "idx_regras_classificacao_ativo",
        "regras_classificacao_dre",
        ["tenant_id", "ativo"],
    )
    _create_index_once(
        "idx_regras_classificacao_subcategoria",
        "regras_classificacao_dre",
        ["dre_subcategoria_id"],
    )
    if _dialect_name() == "postgresql":
        _create_index_once(
            "idx_regras_classificacao_criterios",
            "regras_classificacao_dre",
            ["criterios"],
            postgresql_using="gin",
        )
    else:
        _create_index_once(
            "idx_regras_classificacao_criterios",
            "regras_classificacao_dre",
            ["criterios"],
        )

    _create_index_once(
        "idx_historico_classificacao_tenant",
        "historico_classificacao_dre",
        ["tenant_id"],
    )
    _create_index_once(
        "idx_historico_classificacao_lancamento",
        "historico_classificacao_dre",
        ["tenant_id", "tipo_lancamento", "lancamento_id"],
    )
    _create_index_once(
        "idx_historico_classificacao_subcategoria",
        "historico_classificacao_dre",
        ["dre_subcategoria_id"],
    )
    _create_index_once(
        "idx_historico_classificacao_regra",
        "historico_classificacao_dre",
        ["regra_aplicada_id"],
    )
    _create_index_once(
        "idx_historico_classificacao_forma",
        "historico_classificacao_dre",
        ["tenant_id", "forma_classificacao"],
    )

    _backfill_beneficiarios()


def downgrade() -> None:
    if _has_table("historico_classificacao_dre"):
        op.drop_table("historico_classificacao_dre")
    if _has_table("regras_classificacao_dre"):
        op.drop_table("regras_classificacao_dre")

    _drop_index_once("idx_contas_receber_tipo_documento", "contas_receber")
    _drop_index_once("idx_contas_receber_beneficiario", "contas_receber")
    _drop_index_once("idx_contas_pagar_afeta_dre", "contas_pagar")
    _drop_index_once("idx_contas_pagar_tipo_documento", "contas_pagar")
    _drop_index_once("idx_contas_pagar_beneficiario", "contas_pagar")

    _drop_column_once("contas_receber", "tipo_documento")
    _drop_column_once("contas_receber", "beneficiario")
    _drop_column_once("contas_pagar", "afeta_dre")
    _drop_column_once("contas_pagar", "tipo_documento")
    _drop_column_once("contas_pagar", "beneficiario")
