import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_continuity_scripts_are_versioned_as_executable():
    scripts = [
        "scripts/install_prod_restore_smoke_wrapper.sh",
        "scripts/ops_continuity_event.sh",
        "scripts/prod_db_backup.sh",
        "scripts/prod_db_restore_smoke.sh",
    ]
    index_entries = subprocess.check_output(
        ["git", "ls-files", "--stage", *scripts],
        cwd=ROOT,
        text=True,
    ).splitlines()

    assert len(index_entries) == len(scripts)
    assert all(entry.startswith("100755 ") for entry in index_entries)


def test_restore_smoke_uses_restricted_root_owned_wrapper():
    installer = (ROOT / "scripts" / "install_prod_restore_smoke_wrapper.sh").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )
    guide = (ROOT / "docs" / "PRODUCAO_BACKUP_RESTORE_TESTE.md").read_text(
        encoding="utf-8"
    )

    wrapper_path = "/usr/local/sbin/petshop-restore-smoke-producao"
    assert "Este wrapper nao aceita argumentos." in installer
    assert "database.restore_smoke" in installer
    assert "auditar_comando_producao.sh" in installer
    assert "exec env -i" in installer
    assert "-- bash scripts/prod_db_restore_smoke.sh" in installer
    assert "NOPASSWD" in installer
    assert "visudo -cf" in installer
    assert "install_prod_restore_smoke_wrapper.sh" in deploy
    assert f"sudo -n {wrapper_path}" in guide


def test_backup_and_restore_publish_safe_continuity_events():
    backup = (ROOT / "scripts" / "prod_db_backup.sh").read_text(encoding="utf-8")
    restore = (ROOT / "scripts" / "prod_db_restore_smoke.sh").read_text(
        encoding="utf-8"
    )
    event_writer = (ROOT / "scripts" / "ops_continuity_event.sh").read_text(
        encoding="utf-8"
    )
    installer = (ROOT / "scripts" / "install_ops_continuity_cron.sh").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )

    assert 'record_backup_event "ok"' in backup
    assert 'record_restore_event "ok"' in restore
    assert 'record_backup_event "failed"' in backup
    assert 'record_restore_event "failed"' in restore
    assert "continuity_events.jsonl" in event_writer
    assert "backup_sha256" in event_writer
    assert "public_tables" in event_writer
    assert "external_copy:ok" in event_writer
    assert "POSTGRES_PASSWORD" not in event_writer
    assert "OPS_RUNTIME_UID:-1000" in event_writer
    assert "prod_db_backup.sh" in installer
    assert "prod_db_restore_smoke.sh" in installer
    assert "flock -n /tmp/petshop-ops-continuity.lock" in installer
    assert "install_ops_continuity_cron.sh" in deploy


def test_ops_dashboard_exposes_continuity_summary():
    service = (
        ROOT / "backend" / "app" / "services" / "ops_dashboard_service.py"
    ).read_text(encoding="utf-8")
    dashboard = (ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx").read_text(
        encoding="utf-8"
    )

    assert '"continuity": continuity' in service
    assert "function ContinuityPanel" in dashboard
    assert "RPO alvo" in dashboard
    assert "RTO alvo" in dashboard
