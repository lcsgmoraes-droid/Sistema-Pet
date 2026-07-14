import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_continuity_scripts_are_versioned_as_executable():
    scripts = [
        "scripts/install_prod_restore_smoke_wrapper.sh",
        "scripts/install_ops_tls_monitor_cron.sh",
        "scripts/ops_continuity_event.sh",
        "scripts/prod_db_external_copy.sh",
        "scripts/ops_tls_probe.sh",
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
    external_copy = (ROOT / "scripts" / "prod_db_external_copy.sh").read_text(
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
    assert 'record_external_copy_event "ok"' in external_copy
    assert 'record_external_copy_event "failed"' in external_copy
    assert "head-object" in external_copy
    assert "Metadata.sha256" in external_copy
    assert "configuration file must belong to root" in external_copy
    assert "AWS_SECRET_ACCESS_KEY" not in event_writer
    assert "continuity_events.jsonl" in event_writer
    assert "backup_sha256" in event_writer
    assert "public_tables" in event_writer
    assert "external_copy:ok" in event_writer
    assert "POSTGRES_PASSWORD" not in event_writer
    assert "OPS_RUNTIME_UID:-1000" in event_writer
    assert "prod_db_backup.sh" in installer
    assert "prod_db_restore_smoke.sh" in installer
    assert "prod_db_external_copy.sh" in installer
    assert "backup-external.env" in installer
    assert 'if [[ -f "$EXTERNAL_COPY_CONFIG_FILE"' in installer
    assert "flock -n /tmp/petshop-ops-continuity.lock" in installer
    assert "install_ops_continuity_cron.sh" in deploy


def test_restore_smoke_owns_and_removes_its_temporary_volume():
    restore = (ROOT / "scripts" / "prod_db_restore_smoke.sh").read_text(
        encoding="utf-8"
    )
    disk_guard = (ROOT / "scripts" / "ops_disk_guard.sh").read_text(encoding="utf-8")

    assert "RESTORE_VOLUME_NAME" in restore
    assert "--label com.corepet.purpose=restore-smoke" in restore
    assert "type=volume,source=$RESTORE_VOLUME_NAME" in restore
    assert 'docker rm -f -v "$RESTORE_CONTAINER_NAME"' in restore
    assert 'docker volume rm -f "$RESTORE_VOLUME_NAME"' in restore
    assert 'docker volume inspect "$RESTORE_VOLUME_NAME"' in restore
    assert "restore_volume_removed=true" in restore
    assert "label=com.corepet.purpose=restore-smoke" in disk_guard
    assert 'docker volume rm "$volume_name"' in disk_guard


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


def test_ops_dashboard_exposes_automated_tls_expiry_status():
    probe = (ROOT / "scripts" / "ops_tls_probe.sh").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "install_ops_tls_monitor_cron.sh").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )
    service = (
        ROOT / "backend" / "app" / "services" / "ops_dashboard_service.py"
    ).read_text(encoding="utf-8")
    dashboard = (ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx").read_text(
        encoding="utf-8"
    )

    assert "ssl.create_default_context()" in probe
    assert "server_hostname=domain" in probe
    assert "tls_status.json" in probe
    assert "20 * * * *" in installer
    assert "flock -n /tmp/petshop-ops-tls-monitor.lock" in installer
    assert "timeout 45" in installer
    assert "install_ops_tls_monitor_cron.sh" in deploy
    assert '"tls": tls' in service
    assert "Certificado TLS" in dashboard


def test_deploy_validates_and_ops_exposes_release_gate_evidence():
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )
    service = (
        ROOT / "backend" / "app" / "services" / "ops_dashboard_service.py"
    ).read_text(encoding="utf-8")
    dashboard = (ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx").read_text(
        encoding="utf-8"
    )

    assert "validate_release_gate.py" in deploy
    assert 'mark_step "validar_release_gate"' in deploy
    assert "RELEASE_STATUS_NEXT_PATH" in deploy
    assert 'mv -f "$APP_DIR/$RELEASE_STATUS_NEXT_PATH"' in deploy
    assert '"release": release' in service
    assert "Versao e gate" in dashboard
    assert "Abrir evidencia no GitHub" in dashboard


def test_unlock_before_final_watchdog_preserves_release_candidate():
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )
    lock_cleanup = deploy.split("cleanup_deploy_lock() {", 1)[1].split("}", 1)[0]

    assert "RELEASE_STATUS_NEXT_PATH" not in lock_cleanup
    assert "cleanup_release_candidate()" in deploy
    assert "trap cleanup_on_exit EXIT" in deploy
    assert deploy.index(
        'cleanup_deploy_lock\nif [[ -f "$APP_DIR/scripts/ops_host_watchdog.sh"'
    ) < deploy.rindex('mv -f "$APP_DIR/$RELEASE_STATUS_NEXT_PATH"')
