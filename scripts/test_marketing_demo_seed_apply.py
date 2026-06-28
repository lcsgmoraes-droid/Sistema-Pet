from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    ROOT / "docs" / "marketing" / "base-demo" / "dados_base_demo_sistema_pet.json"
)
APPLIER_PATH = ROOT / "scripts" / "aplicar_seed_base_demo_marketing.py"


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def upsert(self, action: dict) -> dict:
        self.calls.append(action)
        return {
            "section": action["section"],
            "operation": action["operation"],
            "items": action["items"],
            "status": "applied",
        }


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assert_true(APPLIER_PATH.exists(), "Aplicador de seed demo nao encontrado")

    sys.path.insert(0, str(ROOT / "scripts"))
    from aplicar_seed_base_demo_marketing import (
        apply_seed_plan,
        assert_safe_seed_environment,
    )
    from gerar_seed_base_demo_marketing import build_seed_plan

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    plan = build_seed_plan(payload, tenant_slug="tenant_demo")

    dry_repo = RecordingRepository()
    dry_result = apply_seed_plan(
        plan,
        repository=dry_repo,
        dry_run=True,
        environment="development",
    )
    assert_true(dry_result["dry_run"] is True, "Dry-run deve ser explicito")
    assert_true(dry_result["total_actions"] == 14, "Dry-run deve cobrir manifesto")
    assert_true(dry_repo.calls == [], "Dry-run nao deve chamar repositorio")
    assert_true(
        all(item["status"] == "would_upsert" for item in dry_result["results"]),
        "Dry-run deve marcar acoes como simuladas",
    )

    apply_repo = RecordingRepository()
    apply_result = apply_seed_plan(
        plan,
        repository=apply_repo,
        dry_run=False,
        environment="development",
    )
    assert_true(apply_result["dry_run"] is False, "Apply deve registrar modo real")
    assert_true(len(apply_repo.calls) == 14, "Apply deve chamar repositorio")
    assert_true(
        [call["section"] for call in apply_repo.calls][:4]
        == [
            "empresa",
            "usuarios",
            "financeiro.bancos",
            "financeiro.formas_pagamento",
        ],
        "Apply deve preservar ordem operacional",
    )
    assert_true(
        all(item["status"] == "applied" for item in apply_result["results"]),
        "Apply deve devolver resultado do repositorio",
    )

    try:
        assert_safe_seed_environment("production", allow_production=False)
    except ValueError as exc:
        assert_true("producao" in str(exc).lower(), "Erro deve citar producao")
    else:
        raise AssertionError("Ambiente de producao deve ser bloqueado")

    cli_result = subprocess.run(
        [
            sys.executable,
            str(APPLIER_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(cli_result.returncode == 0, cli_result.stderr or cli_result.stdout)
    cli_payload = json.loads(cli_result.stdout)
    assert_true(cli_payload["dry_run"] is True, "CLI deve executar dry-run")
    assert_true(cli_payload["total_actions"] == 14, "CLI deve resumir acoes")

    print("Marketing demo seed apply contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
