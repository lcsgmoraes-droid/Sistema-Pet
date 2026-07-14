import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops_deploy_backup_retention.sh"


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="teste funcional requer Bash Linux",
)
def test_retention_keeps_latest_deploys_and_ignores_other_backups(tmp_path):
    for day in range(1, 7):
        deploy = tmp_path / f"deploy_202607{day:02d}_120000"
        deploy.mkdir()
        (deploy / "head_before.txt").write_text(str(day), encoding="utf-8")

    protected = [
        tmp_path / "db",
        tmp_path / "manual",
        tmp_path / "deploy-invalido",
        tmp_path / "before_maiara_catalog.dump",
    ]
    for path in protected:
        if path.suffix:
            path.write_text("preservar", encoding="utf-8")
        else:
            path.mkdir()

    env = os.environ.copy()
    env["DEPLOY_BACKUP_ROOT"] = str(tmp_path)
    env["DEPLOY_BACKUP_KEEP"] = "3"
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    kept = sorted(path.name for path in tmp_path.glob("deploy_20*") if path.is_dir())
    assert kept == [
        "deploy_20260704_120000",
        "deploy_20260705_120000",
        "deploy_20260706_120000",
    ]
    assert all(path.exists() for path in protected)
    assert "deploy_backup_removed=3" in result.stdout


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="teste funcional requer Bash Linux",
)
def test_retention_rejects_unsafe_keep_value(tmp_path):
    env = os.environ.copy()
    env["DEPLOY_BACKUP_ROOT"] = str(tmp_path)
    env["DEPLOY_BACKUP_KEEP"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 2
    assert "maior ou igual a 2" in result.stderr


def test_production_deploy_runs_retention_after_successful_health():
    deploy = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )

    assert "prune_deploy_backup_history()" in deploy
    assert deploy.count("prune_deploy_backup_history") == 3
    assert 'bash "$APP_DIR/scripts/ops_deploy_backup_retention.sh"' in deploy
