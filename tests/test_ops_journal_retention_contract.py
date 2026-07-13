from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_journal_retention_is_bounded_and_installed_by_deploy():
    installer = (ROOT / "scripts" / "install_ops_journal_retention.sh").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )

    assert "SystemMaxUse=$SYSTEM_MAX_USE" in installer
    assert "SystemKeepFree=$SYSTEM_KEEP_FREE" in installer
    assert "MaxRetentionSec=$MAX_RETENTION" in installer
    assert "JOURNAL_SYSTEM_MAX_USE:-768M" in installer
    assert "JOURNAL_SYSTEM_KEEP_FREE:-3G" in installer
    assert "JOURNAL_MAX_RETENTION:-30day" in installer
    assert "install -o root -g root -m 0644" in installer
    assert "systemctl restart systemd-journald" in installer
    assert 'journalctl --vacuum-time="$MAX_RETENTION"' in installer
    assert "install_ops_journal_retention.sh" in deploy
    assert 'mark_step "instalar_retencao_journal"' in deploy


def test_journal_retention_rejects_unvalidated_values():
    installer = (ROOT / "scripts" / "install_ops_journal_retention.sh").read_text(
        encoding="utf-8"
    )

    assert '[[ ! "$SYSTEM_MAX_USE" =~ ^[0-9]+[KMG]$ ]]' in installer
    assert '[[ ! "$SYSTEM_KEEP_FREE" =~ ^[0-9]+[KMG]$ ]]' in installer
    assert '[[ ! "$MAX_RETENTION" =~ ^[0-9]+' in installer
