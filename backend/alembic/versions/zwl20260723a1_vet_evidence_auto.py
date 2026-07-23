"""enable automatically eligible veterinary evidence

Revision ID: zwl20260723a1
Revises: zwk20260723a1
Create Date: 2026-07-23
"""

from alembic import op

revision = "zwl20260723a1"
down_revision = "zwk20260723a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE vet_conhecimento_fontes
        SET requer_revisao = FALSE
        WHERE codigo = 'pubmed'
        """)
    op.execute("""
        UPDATE vet_conhecimento_documentos
        SET status_revisao = 'auto_disponivel',
            motivo_revisao = 'Elegibilidade automatica pela fonte PubMed.'
        WHERE status_revisao = 'pendente'
        """)


def downgrade() -> None:
    op.execute("""
        UPDATE vet_conhecimento_documentos
        SET status_revisao = 'pendente',
            motivo_revisao = 'Aguardando revisao humana.'
        WHERE status_revisao = 'auto_disponivel'
        """)
    op.execute("""
        UPDATE vet_conhecimento_fontes
        SET requer_revisao = TRUE
        WHERE codigo = 'pubmed'
        """)
