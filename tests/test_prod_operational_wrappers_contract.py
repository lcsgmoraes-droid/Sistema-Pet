import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_status_wrapper_is_restricted_and_audited():
    installer = _read("scripts/install_prod_status_wrapper.sh")

    assert "/usr/local/sbin/petshop-status-producao" in installer
    assert "Este wrapper nao aceita argumentos." in installer
    assert "exec env -i" in installer
    assert "production.status" in installer
    assert "auditar_comando_producao.sh" in installer
    assert "-- bash scripts/prod_status.sh" in installer
    assert "NOPASSWD" in installer
    assert "visudo -cf" in installer


def test_production_status_checks_runtime_database_and_public_release():
    status = _read("scripts/prod_status.sh")

    assert "validate_deploy_target.py" in status
    assert "git status --porcelain" in status
    assert "postgres backend worker-bling nginx" in status
    assert "alembic current" in status
    assert "PUBLIC_HEALTH_URL" in status
    assert "PUBLIC_WATCHDOG_URL" in status
    assert "PUBLIC_RELEASE_URL" in status
    assert '[[ "$public_commit" == "$head_commit" ]]' in status
    assert "STATUS PRODUCAO: OK" in status


def test_every_deploy_repairs_all_restricted_wrappers():
    deploy = _read("scripts/deploy_producao_seguro.sh")

    for installer in (
        "install_prod_deploy_wrapper.sh",
        "install_prod_status_wrapper.sh",
        "install_prod_restore_smoke_wrapper.sh",
    ):
        assert installer in deploy

    assert deploy.index('mark_step "atualizar_codigo"') < deploy.index(
        'mark_step "instalar_wrappers_operacionais"'
    )


def test_status_scripts_are_versioned_as_executable():
    scripts = [
        "scripts/install_prod_status_wrapper.sh",
        "scripts/prod_status.sh",
    ]
    entries = subprocess.check_output(
        ["git", "ls-files", "--stage", *scripts],
        cwd=ROOT,
        text=True,
    ).splitlines()

    assert len(entries) == len(scripts)
    assert all(entry.startswith("100755 ") for entry in entries)
