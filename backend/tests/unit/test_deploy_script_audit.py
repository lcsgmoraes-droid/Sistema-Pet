from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"
OPERATIONAL_WATCHDOG_DOCS = [
    ROOT / "docs" / "COREPET_DOMINIO_GO_LIVE.md",
    ROOT / "docs" / "GUIA_DEMO_VETERINARIO_CLINICA.md",
    ROOT / "docs" / "PRODUCAO_DEPLOY_SSH.md",
    ROOT / "docs" / "PRODUCAO_ROLLBACK_CHECKLIST.md",
    ROOT / "docs" / "SEGURANCA_ROTACAO_SSH_SECRETS.md",
]


def _deploy_script_text() -> str:
    return DEPLOY_SCRIPT.read_text(encoding="utf-8")


def test_deploy_script_audits_sensitive_steps():
    script = _deploy_script_text()

    assert "audit_step()" in script

    sensitive_steps = [
        "validar_repositorio",
        "atualizar_codigo",
        "instalar_disk_guard",
        "instalar_host_watchdog",
        "preparar_diretorios_persistentes",
        "build_frontend",
        "validar_compose",
        "build_backend",
        "subir_postgres",
        "migrar_banco",
        "subir_servicos",
        "publicar_frontend",
        "validar_watchdog",
        "validar_worker_bling",
        "validar_health_publico",
        "checar_estado_final",
        "disk_guard_final",
        "host_watchdog_final",
    ]

    for step in sensitive_steps:
        marker = f'mark_step "{step}"'
        start = script.index(marker)
        next_marker = script.find("\nmark_step ", start + len(marker))
        block = script[start : next_marker if next_marker != -1 else len(script)]
        assert "audit_step" in block, (
            f"Step {step} must emit a running deploy audit event"
        )


def test_deploy_step_audit_does_not_suppress_failure_trap():
    script = _deploy_script_text()

    assert 'if [[ "$status" == "success" || "$status" == "failed" ]]; then' in script
    assert "DEPLOY_EVENT_RECORDED=1" in script


def test_deploy_script_keeps_manual_ops_audit_log_restricted_to_backend_owner():
    script = _deploy_script_text()

    assert (
        'ops_command_audit_log_path="$APP_DIR/backend/logs/ops_command_events.jsonl"'
        in script
    )
    assert 'touch "$ops_command_audit_log_path"' in script
    assert 'chown 1000:1000 "$ops_command_audit_log_path"' in script
    assert 'chmod 0660 "$ops_command_audit_log_path"' in script
    assert 'chmod 0666 "$ops_command_audit_log_path"' not in script


def test_deploy_allows_runtime_to_rotate_bling_tokens_without_exposing_env():
    script = _deploy_script_text()

    assert 'runtime_env_path="$APP_DIR/.env"' in script
    assert 'chown 1000:1000 "$runtime_env_path"' in script
    assert 'chmod 0600 "$runtime_env_path"' in script
    assert 'chmod 0660 "$runtime_env_path"' not in script
    assert 'chmod 0666 "$runtime_env_path"' not in script


def test_operational_docs_use_the_public_watchdog_route():
    for doc_path in OPERATIONAL_WATCHDOG_DOCS:
        content = doc_path.read_text(encoding="utf-8")
        assert "/api/health/watchdog" not in content, doc_path
        assert "/health/watchdog" in content, doc_path
