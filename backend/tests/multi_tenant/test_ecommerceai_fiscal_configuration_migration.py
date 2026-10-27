"""A configuração única começa desligada e não perde consentimentos em downgrade."""

from unittest.mock import Mock
import pytest
from tests.multi_tenant.rls_migration_helpers import load_migration, migration_path

PATH = migration_path("zzzzza20261027a1_fiscal_account_configuration.py")


def test_new_upload_and_revision_have_safe_server_defaults(monkeypatch):
    migration = load_migration(PATH)
    added = []
    alter = Mock()
    monkeypatch.setattr(
        migration["op"],
        "add_column",
        lambda table, column: added.append((table, column)),
    )
    monkeypatch.setattr(migration["op"], "alter_column", alter)
    migration["upgrade"]()
    assert migration["down_revision"] == "zzzzz20261027a1"
    assert [column.name for _, column in added] == [
        "upload_enabled",
        "configuration_version",
    ]
    assert (
        added[0][1].nullable is False and str(added[0][1].server_default.arg) == "false"
    )
    assert added[1][1].nullable is False and str(added[1][1].server_default.arg) == "1"
    assert str(alter.call_args.kwargs["server_default"]) == "false"


@pytest.mark.parametrize("history", [True, False])
def test_downgrade_preserves_upload_consent_and_configuration_history(
    monkeypatch, history
):
    migration = load_migration(PATH)
    bind = Mock()
    bind.execute.return_value.first.return_value = (1,) if history else None
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", Mock())
    monkeypatch.setattr(migration["op"], "alter_column", Mock())
    drop = Mock()
    monkeypatch.setattr(migration["op"], "drop_column", drop)
    if history:
        with pytest.raises(RuntimeError, match="preserve o histórico"):
            migration["downgrade"]()
        drop.assert_not_called()
    else:
        migration["downgrade"]()
        assert [call.args[1] for call in drop.call_args_list] == [
            "configuration_version",
            "upload_enabled",
        ]
