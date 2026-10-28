"""Contratos por pet, serviços e reservas de pacotes de banho e tosa.

Mantém os saldos existentes e copia a composição atual para cada contrato.
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzzd20261027a1"
down_revision = "zzzzzc20261027a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("banho_tosa_pacotes", sa.Column("servicos", sa.JSON(), nullable=True))
    for coluna in (
        sa.Column(
            "creditos_reservados", sa.Numeric(12, 3), nullable=False, server_default="0"
        ),
        sa.Column("servicos", sa.JSON(), nullable=True),
        sa.Column(
            "valor_pacote", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
    ):
        op.add_column("banho_tosa_pacote_creditos", coluna)
    op.add_column(
        "banho_tosa_agendamento_servicos",
        sa.Column(
            "pacote_credito_id",
            sa.Integer(),
            sa.ForeignKey("banho_tosa_pacote_creditos.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "banho_tosa_agendamento_servicos",
        sa.Column(
            "pacote_quantidade", sa.Numeric(12, 3), nullable=False, server_default="0"
        ),
    )
    for nome, tabela in (
        ("agendamento_id", "banho_tosa_agendamentos"),
        ("agendamento_servico_id", "banho_tosa_agendamento_servicos"),
        ("servico_id", "banho_tosa_servicos"),
    ):
        op.add_column(
            "banho_tosa_pacote_movimentos",
            sa.Column(nome, sa.Integer(), sa.ForeignKey(f"{tabela}.id"), nullable=True),
        )
    op.create_index(
        "ix_bt_movimentos_agendamento",
        "banho_tosa_pacote_movimentos",
        ["tenant_id", "agendamento_id"],
    )
    # Não apaga nem converte créditos expirados. O valor original passa a ser snapshot.
    op.execute(
        "UPDATE banho_tosa_pacote_creditos c SET valor_pacote = p.preco FROM banho_tosa_pacotes p WHERE p.id = c.pacote_id AND p.tenant_id = c.tenant_id"
    )
    op.execute(
        "UPDATE banho_tosa_pacotes SET servicos = json_build_array(json_build_object('servico_id', servico_id, 'quantidade_creditos', quantidade_creditos)) WHERE servico_id IS NOT NULL"
    )
    op.execute(
        "UPDATE banho_tosa_pacote_creditos c SET servicos = p.servicos FROM banho_tosa_pacotes p WHERE p.id = c.pacote_id AND p.tenant_id = c.tenant_id"
    )


def downgrade():
    op.drop_index(
        "ix_bt_movimentos_agendamento", table_name="banho_tosa_pacote_movimentos"
    )
    for nome in ("servico_id", "agendamento_servico_id", "agendamento_id"):
        op.drop_column("banho_tosa_pacote_movimentos", nome)
    for nome in ("pacote_quantidade", "pacote_credito_id"):
        op.drop_column("banho_tosa_agendamento_servicos", nome)
    for nome in ("valor_pacote", "servicos", "creditos_reservados"):
        op.drop_column("banho_tosa_pacote_creditos", nome)
    op.drop_column("banho_tosa_pacotes", "servicos")
