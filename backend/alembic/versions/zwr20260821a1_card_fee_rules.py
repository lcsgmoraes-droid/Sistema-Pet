"""centraliza taxas de cartao por operadora e bandeira

Revision ID: zwr20260821a1
Revises: zwt20260821a1
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwr20260821a1"
down_revision = "zwt20260821a1"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _columns(inspector, table_name: str) -> set[str]:
    if not _has_table(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _set_rls_for_backfill(bind, table_names: tuple[str, ...], *, enabled: bool) -> None:
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    for table_name in table_names:
        if table_name not in existing:
            continue
        if enabled:
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        else:
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def _normalize_brand(value) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "master": "mastercard",
        "master card": "mastercard",
        "american express": "amex",
        "outro": "outros",
        "": "outros",
    }
    return aliases.get(text, text)


def _modality(row) -> str:
    text = " ".join(
        str(row.get(field) or "") for field in ("tipo", "tipo_cartao", "nome")
    ).lower()
    if "credit" in text or "crédit" in text:
        return "credito"
    if "debit" in text or "débit" in text:
        return "debito"
    if "voucher" in text:
        return "voucher"
    return ""


def _insert_rule(bind, values: dict) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO operadoras_cartao_taxas (
                tenant_id, operadora_id, bandeira, modalidade, parcelas,
                taxa_percentual, taxa_fixa, prazo_recebimento_dias, ativo,
                user_id, created_at, updated_at
            ) VALUES (
                :tenant_id, :operadora_id, :bandeira, :modalidade, :parcelas,
                :taxa_percentual, :taxa_fixa, :prazo_recebimento_dias, true,
                :user_id, now(), now()
            )
            ON CONFLICT (tenant_id, operadora_id, bandeira, modalidade, parcelas)
            DO NOTHING
            """
        ),
        values,
    )


def _backfill_legacy_rules(bind, inspector) -> None:
    if _has_table(inspector, "formas_pagamento"):
        rows = bind.execute(
            sa.text(
                """
                SELECT id, tenant_id, user_id, nome, tipo, tipo_cartao, operadora_id,
                       bandeira, taxa_percentual, taxa_fixa, prazo_dias,
                       taxas_por_parcela, ativo
                FROM formas_pagamento
                WHERE operadora_id IS NOT NULL
                  AND COALESCE(ativo, true) = true
                ORDER BY id
                """
            )
        ).mappings()
        for row in rows:
            modality = _modality(row)
            if not modality:
                continue
            rules = {
                1: {
                    "taxa_percentual": row.get("taxa_percentual") or 0,
                    "taxa_fixa": row.get("taxa_fixa") or 0,
                }
            }
            raw = row.get("taxas_por_parcela")
            if raw:
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except (TypeError, ValueError):
                    parsed = {}
                if isinstance(parsed, dict):
                    for installment, configured in parsed.items():
                        try:
                            installment_number = int(installment)
                        except (TypeError, ValueError):
                            continue
                        if not 1 <= installment_number <= 24:
                            continue
                        if isinstance(configured, dict):
                            percent = configured.get(
                                "taxa_percentual", row.get("taxa_percentual") or 0
                            )
                            fixed = configured.get(
                                "taxa_fixa", row.get("taxa_fixa") or 0
                            )
                        else:
                            percent = configured
                            fixed = row.get("taxa_fixa") or 0
                        rules[installment_number] = {
                            "taxa_percentual": percent or 0,
                            "taxa_fixa": fixed or 0,
                        }

            for installment, configured in rules.items():
                _insert_rule(
                    bind,
                    {
                        "tenant_id": row["tenant_id"],
                        "operadora_id": row["operadora_id"],
                        "bandeira": _normalize_brand(row.get("bandeira")),
                        "modalidade": modality,
                        "parcelas": installment,
                        "taxa_percentual": configured["taxa_percentual"],
                        "taxa_fixa": configured["taxa_fixa"],
                        "prazo_recebimento_dias": row.get("prazo_dias") or 0,
                        "user_id": row["user_id"],
                    },
                )

    if _has_table(inspector, "operadoras_cartao"):
        operators = bind.execute(
            sa.text(
                """
                SELECT tenant_id, id, user_id, max_parcelas, taxa_debito,
                       taxa_credito_vista, taxa_credito_parcelado
                FROM operadoras_cartao
                WHERE COALESCE(ativo, true) = true
                """
            )
        ).mappings()
        for operator in operators:
            common = {
                "tenant_id": operator["tenant_id"],
                "operadora_id": operator["id"],
                "bandeira": "outros",
                "taxa_fixa": 0,
                "prazo_recebimento_dias": 0,
                "user_id": operator["user_id"],
            }
            if operator.get("taxa_debito") is not None:
                _insert_rule(
                    bind,
                    {
                        **common,
                        "modalidade": "debito",
                        "parcelas": 1,
                        "taxa_percentual": operator["taxa_debito"],
                    },
                )
            if operator.get("taxa_credito_vista") is not None:
                _insert_rule(
                    bind,
                    {
                        **common,
                        "modalidade": "credito",
                        "parcelas": 1,
                        "taxa_percentual": operator["taxa_credito_vista"],
                    },
                )
            if operator.get("taxa_credito_parcelado") is not None:
                for installment in range(
                    2, min(int(operator["max_parcelas"] or 12), 24) + 1
                ):
                    _insert_rule(
                        bind,
                        {
                            **common,
                            "modalidade": "credito",
                            "parcelas": installment,
                            "taxa_percentual": operator["taxa_credito_parcelado"],
                        },
                    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "operadoras_cartao"):
        op.create_table(
            "operadoras_cartao",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("codigo", sa.String(length=50), nullable=True),
            sa.Column(
                "max_parcelas", sa.Integer(), server_default="12", nullable=False
            ),
            sa.Column(
                "padrao", sa.Boolean(), server_default=sa.text("false"), nullable=False
            ),
            sa.Column(
                "ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False
            ),
            sa.Column("bandeira_padrao", sa.String(length=30), nullable=True),
            sa.Column("taxa_debito", sa.Numeric(5, 2), nullable=True),
            sa.Column("taxa_credito_vista", sa.Numeric(5, 2), nullable=True),
            sa.Column("taxa_credito_parcelado", sa.Numeric(5, 2), nullable=True),
            sa.Column(
                "api_enabled",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            sa.Column("api_endpoint", sa.String(length=255), nullable=True),
            sa.Column("api_token_encrypted", sa.Text(), nullable=True),
            sa.Column("cor", sa.String(length=7), nullable=True),
            sa.Column("icone", sa.String(length=50), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_operadoras_cartao_tenant_id", "operadoras_cartao", ["tenant_id"]
        )
        op.create_index("ix_operadoras_cartao_padrao", "operadoras_cartao", ["padrao"])
        op.create_index("ix_operadoras_cartao_ativo", "operadoras_cartao", ["ativo"])
        inspector = sa.inspect(bind)
    elif "bandeira_padrao" not in _columns(inspector, "operadoras_cartao"):
        op.add_column(
            "operadoras_cartao",
            sa.Column("bandeira_padrao", sa.String(length=30), nullable=True),
        )
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "operadoras_cartao_taxas"):
        op.create_table(
            "operadoras_cartao_taxas",
            sa.Column("operadora_id", sa.Integer(), nullable=False),
            sa.Column("bandeira", sa.String(length=30), nullable=False),
            sa.Column("modalidade", sa.String(length=20), nullable=False),
            sa.Column("parcelas", sa.Integer(), nullable=False),
            sa.Column(
                "taxa_percentual", sa.Numeric(7, 4), server_default="0", nullable=False
            ),
            sa.Column(
                "taxa_fixa", sa.Numeric(10, 2), server_default="0", nullable=False
            ),
            sa.Column(
                "prazo_recebimento_dias",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
            sa.Column(
                "ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
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
            sa.CheckConstraint(
                "parcelas >= 1 AND parcelas <= 24", name="ck_operadora_taxa_parcelas"
            ),
            sa.CheckConstraint(
                "taxa_percentual >= 0 AND taxa_percentual <= 100",
                name="ck_operadora_taxa_percentual",
            ),
            sa.ForeignKeyConstraint(
                ["operadora_id"], ["operadoras_cartao.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id",
                "operadora_id",
                "bandeira",
                "modalidade",
                "parcelas",
                name="uq_operadora_taxa_contexto",
            ),
        )
        op.create_index(
            "ix_operadoras_cartao_taxas_tenant_id",
            "operadoras_cartao_taxas",
            ["tenant_id"],
        )
        op.create_index(
            "ix_operadoras_cartao_taxas_operadora_id",
            "operadoras_cartao_taxas",
            ["operadora_id"],
        )
        op.create_index(
            "ix_operadoras_cartao_taxas_contexto",
            "operadoras_cartao_taxas",
            [
                "tenant_id",
                "operadora_id",
                "bandeira",
                "modalidade",
                "parcelas",
                "ativo",
            ],
        )
    payment_columns = _columns(sa.inspect(bind), "venda_pagamentos")
    additions = {
        "forma_pagamento_id": sa.Column(
            "forma_pagamento_id", sa.Integer(), nullable=True
        ),
        "modalidade_cartao": sa.Column(
            "modalidade_cartao", sa.String(length=20), nullable=True
        ),
        "taxa_cartao_regra_id": sa.Column(
            "taxa_cartao_regra_id", sa.Integer(), nullable=True
        ),
        "taxa_percentual_aplicada": sa.Column(
            "taxa_percentual_aplicada", sa.Numeric(7, 4), nullable=True
        ),
        "taxa_fixa_aplicada": sa.Column(
            "taxa_fixa_aplicada", sa.Numeric(10, 2), nullable=True
        ),
        "valor_taxa_prevista": sa.Column(
            "valor_taxa_prevista", sa.Numeric(10, 2), nullable=True
        ),
        "valor_liquido_previsto": sa.Column(
            "valor_liquido_previsto", sa.Numeric(10, 2), nullable=True
        ),
        "prazo_recebimento_dias": sa.Column(
            "prazo_recebimento_dias", sa.Integer(), nullable=True
        ),
        "data_recebimento_prevista": sa.Column(
            "data_recebimento_prevista", sa.Date(), nullable=True
        ),
    }
    for name, column in additions.items():
        if name not in payment_columns:
            op.add_column("venda_pagamentos", column)
    if "forma_pagamento_id" not in payment_columns:
        op.create_index(
            "ix_venda_pagamentos_forma_pagamento_id",
            "venda_pagamentos",
            ["forma_pagamento_id"],
        )
    if "taxa_cartao_regra_id" not in payment_columns:
        op.create_index(
            "ix_venda_pagamentos_taxa_cartao_regra_id",
            "venda_pagamentos",
            ["taxa_cartao_regra_id"],
        )

    source_tables = ("formas_pagamento", "operadoras_cartao")
    _set_rls_for_backfill(bind, source_tables, enabled=False)
    _backfill_legacy_rules(bind, sa.inspect(bind))
    _set_rls_for_backfill(bind, source_tables, enabled=True)
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("operadoras_cartao", "operadoras_cartao_taxas"),
        enable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    payment_columns = _columns(inspector, "venda_pagamentos")
    for index_name in (
        "ix_venda_pagamentos_taxa_cartao_regra_id",
        "ix_venda_pagamentos_forma_pagamento_id",
    ):
        indexes = {index["name"] for index in inspector.get_indexes("venda_pagamentos")}
        if index_name in indexes:
            op.drop_index(index_name, table_name="venda_pagamentos")
    for name in (
        "data_recebimento_prevista",
        "prazo_recebimento_dias",
        "valor_liquido_previsto",
        "valor_taxa_prevista",
        "taxa_fixa_aplicada",
        "taxa_percentual_aplicada",
        "taxa_cartao_regra_id",
        "modalidade_cartao",
        "forma_pagamento_id",
    ):
        if name in payment_columns:
            op.drop_column("venda_pagamentos", name)
    if _has_table(inspector, "operadoras_cartao_taxas"):
        op.drop_table("operadoras_cartao_taxas")
    if "bandeira_padrao" in _columns(sa.inspect(bind), "operadoras_cartao"):
        op.drop_column("operadoras_cartao", "bandeira_padrao")
