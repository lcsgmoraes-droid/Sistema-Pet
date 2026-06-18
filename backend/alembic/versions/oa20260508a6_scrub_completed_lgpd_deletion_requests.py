"""scrub completed LGPD deletion request PII

Revision ID: oa20260508a6
Revises: nz20260508a5
Create Date: 2026-05-08 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "oa20260508a6"
down_revision = "nz20260508a5"
branch_labels = None
depends_on = None


SCRUB_NOTE = (
    "Solicitacao de exclusao concluida; dados pessoais do titular foram anonimizados."
)


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    request_columns = _columns("data_subject_requests")
    if request_columns:
        assignments = []
        if "requester_name" in request_columns:
            assignments.append(
                "requester_name = 'Titular anonimizado #' || COALESCE(subject_id, CAST(id AS TEXT))"
            )
        if "requester_email" in request_columns:
            assignments.append("requester_email = NULL")
        if "requester_phone" in request_columns:
            assignments.append("requester_phone = NULL")
        if "details" in request_columns:
            assignments.append("details = :scrub_note")
        if "request_payload" in request_columns:
            assignments.append("request_payload = NULL")
        if "resolution_notes" in request_columns:
            assignments.append("resolution_notes = :scrub_note")
        if "updated_at" in request_columns:
            assignments.append("updated_at = CURRENT_TIMESTAMP")

        if assignments:
            op.execute(
                sa.text(
                    f"""
                    UPDATE data_subject_requests
                    SET {", ".join(assignments)}
                    WHERE request_type = 'deletion'
                      AND status = 'completed'
                      AND subject_type = 'customer'
                    """
                ).bindparams(scrub_note=SCRUB_NOTE)
            )

    legacy_columns = _columns("data_deletion_requests")
    if legacy_columns:
        assignments = []
        if "reason" in legacy_columns:
            assignments.append("reason = :scrub_note")
        if "contact_phone" in legacy_columns:
            assignments.append("contact_phone = NULL")
        if "contact_email" in legacy_columns:
            assignments.append("contact_email = NULL")
        if "extra_metadata" in legacy_columns:
            assignments.append("extra_metadata = NULL")

        if assignments:
            op.execute(
                sa.text(
                    f"""
                    UPDATE data_deletion_requests
                    SET {", ".join(assignments)}
                    WHERE status = 'completed'
                      AND subject_type = 'customer'
                    """
                ).bindparams(scrub_note=SCRUB_NOTE)
            )


def downgrade() -> None:
    # Personal data removed by this migration cannot be reconstructed safely.
    pass
