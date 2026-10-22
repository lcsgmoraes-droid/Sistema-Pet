"""Amplia o telefone da conversa e do atendimento do WhatsApp para 40 caracteres.

Identificadores internos do WhatsApp (@lid) podem passar de 20 caracteres e
estouravam o campo, perdendo a mensagem do tutor.
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzk20261022a1"
down_revision = "zzzzj20261019a1"
branch_labels = None
depends_on = None

TABELAS = ("whatsapp_ia_sessions", "whatsapp_handoffs")


def upgrade():
    for tabela in TABELAS:
        op.alter_column(
            tabela,
            "phone_number",
            existing_type=sa.String(20),
            type_=sa.String(40),
            existing_nullable=False,
        )


def downgrade():
    # Reduzir volta ao limite antigo; falha se ja existirem valores maiores.
    for tabela in TABELAS:
        op.alter_column(
            tabela,
            "phone_number",
            existing_type=sa.String(40),
            type_=sa.String(20),
            existing_nullable=False,
        )
