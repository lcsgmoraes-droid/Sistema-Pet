"""WhatsApp: campos da API oficial da Meta por loja

Revision ID: zzzzo20261026a1
Revises: zzzzn20261023a1
Create Date: 2026-10-26

Cada loja conecta o proprio numero pela API oficial (Meta Cloud API). O token e o
segredo do app ficam criptografados, em colunas separadas das credenciais do
provedor atual, para que testar o vinculo nao derrube quem ja esta em producao.
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzzo20261026a1"
down_revision = "zzzzn20261023a1"
branch_labels = None
depends_on = None

TABELA = "tenant_whatsapp_config"


def upgrade() -> None:
    op.add_column(TABELA, sa.Column("meta_waba_id", sa.String(40)))
    op.add_column(TABELA, sa.Column("meta_phone_number_id", sa.String(40)))
    op.add_column(TABELA, sa.Column("meta_access_token_encrypted", sa.Text()))
    op.add_column(TABELA, sa.Column("meta_app_secret_encrypted", sa.Text()))
    op.add_column(TABELA, sa.Column("meta_status", sa.String(20)))
    op.add_column(TABELA, sa.Column("meta_status_detalhe", sa.String(300)))
    op.add_column(TABELA, sa.Column("meta_verificado_em", sa.DateTime()))
    op.add_column(TABELA, sa.Column("meta_numero_exibicao", sa.String(40)))
    op.add_column(TABELA, sa.Column("meta_nome_verificado", sa.String(200)))
    op.add_column(TABELA, sa.Column("meta_qualidade", sa.String(20)))
    op.add_column(TABELA, sa.Column("meta_ultimo_webhook_em", sa.DateTime()))


def downgrade() -> None:
    for coluna in (
        "meta_ultimo_webhook_em",
        "meta_qualidade",
        "meta_nome_verificado",
        "meta_numero_exibicao",
        "meta_verificado_em",
        "meta_status_detalhe",
        "meta_status",
        "meta_app_secret_encrypted",
        "meta_access_token_encrypted",
        "meta_phone_number_id",
        "meta_waba_id",
    ):
        op.drop_column(TABELA, coluna)
