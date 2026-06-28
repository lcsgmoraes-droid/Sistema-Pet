from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    ROOT / "docs" / "marketing" / "base-demo" / "dados_base_demo_sistema_pet.json"
)
VALIDATOR_PATH = ROOT / "scripts" / "validar_base_demo_marketing.py"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assert_true(
        DATA_PATH.exists(), f"Arquivo de dados demo nao encontrado: {DATA_PATH}"
    )
    assert_true(
        VALIDATOR_PATH.exists(),
        f"Validador da base demo nao encontrado: {VALIDATOR_PATH}",
    )

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert_true(
        payload["metadata"]["nome"] == "Base Demo Sistema Pet",
        "Nome da base demo invalido",
    )
    assert_true(
        payload["empresa"]["nome_fantasia"] == "Pet Feliz Demo",
        "Empresa demo inesperada",
    )
    assert_true(len(payload["produtos"]) >= 4, "Base demo deve ter ao menos 4 produtos")
    assert_true(len(payload["clientes"]) >= 3, "Base demo deve ter ao menos 3 clientes")
    assert_true(len(payload["pets"]) >= 3, "Base demo deve ter ao menos 3 pets")
    assert_true(len(payload["servicos"]) >= 4, "Base demo deve ter ao menos 4 servicos")
    assert_true(
        payload["videos_prioritarios"][0]["titulo"] == "Estoque que some",
        "Primeiro video deve ser o estoque",
    )

    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--json", str(DATA_PATH), "--markdown"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    assert_true("Base demo validada" in result.stdout, "Saida nao confirmou validacao")
    assert_true("Pet Feliz Demo" in result.stdout, "Checklist nao cita a empresa demo")
    assert_true(
        "Estoque que some" in result.stdout, "Checklist nao cita o primeiro video"
    )
    assert_true(
        "Nenhum dado sensivel aparente" in result.stdout,
        "Checklist nao registra seguranca",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        outside_json = Path(tmp_dir) / "dados_base_demo_sistema_pet.json"
        outside_json.write_text(json.dumps(payload), encoding="utf-8")
        outside_result = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), "--json", str(outside_json)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert_true(
            outside_result.returncode != 0,
            "Validador deve recusar JSON fora do repositorio",
        )
        assert_true(
            "fora do repositorio" in outside_result.stderr,
            "Erro deve explicar restricao de caminho",
        )

    print("Marketing demo package contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
