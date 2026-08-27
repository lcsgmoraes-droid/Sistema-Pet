from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "zxf20260827a1_tenant_onboarding_follow_up.py"
)
MODEL = ROOT / "backend" / "app" / "models.py"


def test_onboarding_follow_up_migration_is_in_the_official_chain():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxf20260827a1"' in source
    assert 'down_revision = "zxe20260826a1"' in source
    assert "ck_tenants_onboarding_satisfaction" in source
    for column in (
        "onboarding_owner_name",
        "onboarding_unblocked_on",
        "onboarding_satisfaction",
        "onboarding_follow_up_updated_at",
    ):
        assert column in source
    assert source.count("op.add_column(") == 4


def test_tenant_model_matches_onboarding_follow_up_migration():
    source = MODEL.read_text(encoding="utf-8")

    for column in (
        "onboarding_owner_name",
        "onboarding_unblocked_on",
        "onboarding_satisfaction",
        "onboarding_follow_up_updated_at",
    ):
        assert column in source
    for value in ("not_collected", "satisfied", "neutral", "dissatisfied"):
        assert value in source
