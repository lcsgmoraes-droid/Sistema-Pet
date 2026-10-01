import os
import subprocess
import sys
from pathlib import Path


def test_worker_carrega_registro_orm_antes_do_scheduler():
    backend_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite://")
    env.setdefault(
        "JWT_SECRET_KEY",
        "test-secret-key-min-32-chars-long-for-security",
    )
    codigo = """
import scripts.run_bling_worker
from app.estoque_models import AlertaEstoqueNegativo
from sqlalchemy.orm import configure_mappers

configure_mappers()

AlertaEstoqueNegativo(
    tenant_id="11111111-1111-4111-8111-111111111111",
    produto_id=1,
    produto_nome="Produto teste",
    estoque_anterior=0,
    quantidade_vendida=1,
    estoque_resultante=-1,
)
print("worker-model-registry-ok")
"""

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "worker-model-registry-ok" in resultado.stdout


def test_worker_configura_mapeamentos_antes_de_iniciar_jobs(monkeypatch):
    import scripts.run_bling_worker as worker

    chamadas = []

    class FakeScheduler:
        def start(self):
            chamadas.append("start")

        def shutdown(self):
            chamadas.append("shutdown")

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "configure_mappers", lambda: chamadas.append("mappers"))
    monkeypatch.setattr(worker, "BlingSyncScheduler", FakeScheduler)
    monkeypatch.setattr(worker, "_should_stop", True)
    monkeypatch.setattr(worker.signal, "signal", lambda *_args: None)

    worker.main()

    assert chamadas == ["mappers", "start", "shutdown"]
