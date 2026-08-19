import os
from pathlib import Path
import subprocess
import sys


def test_script_onboarding_registra_modelos_em_processo_limpo():
    backend_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./test.db")
    env.setdefault(
        "JWT_SECRET_KEY",
        "tenant-onboarding-test-secret-with-more-than-32-characters",
    )

    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import app.scripts.run_tenant_onboarding; "
                "from sqlalchemy.orm import configure_mappers; "
                "configure_mappers()"
            ),
        ],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
