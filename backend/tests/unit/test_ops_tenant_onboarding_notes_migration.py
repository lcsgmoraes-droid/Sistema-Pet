from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    BACKEND_ROOT / "alembic/versions/zxg20260827a1_ops_tenant_onboarding_notes.py"
)


def test_onboarding_notes_migration_is_linear_and_reversible():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxg20260827a1"' in source
    assert 'down_revision = "zxf20260827a1"' in source
    assert "op.add_column(" in source
    assert '"tenants",' in source
    assert '"onboarding_next_contact_on"' in source
    assert "op.create_table(" in source
    assert '"ops_tenant_onboarding_notes",' in source
    assert 'ondelete="CASCADE"' in source
    assert 'ondelete="RESTRICT"' in source
    assert 'op.drop_table("ops_tenant_onboarding_notes")' in source
    assert 'op.drop_column("tenants", "onboarding_next_contact_on")' in source


def test_onboarding_notes_migration_limits_note_length_in_database():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "length(note) BETWEEN 3 AND 1000" in source
    assert "ck_ops_tenant_onboarding_notes_length" in source
