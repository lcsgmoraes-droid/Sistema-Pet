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
GENERATOR_PATH = ROOT / "scripts" / "gerar_seed_base_demo_marketing.py"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assert_true(GENERATOR_PATH.exists(), "Gerador de seed demo nao encontrado")

    sys.path.insert(0, str(ROOT / "scripts"))
    from gerar_seed_base_demo_marketing import build_seed_plan

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    plan = build_seed_plan(payload, tenant_slug="tenant_demo")

    assert_true(
        plan["metadata"]["seed_name"] == "marketing_base_demo",
        "Seed deve ter nome estavel",
    )
    assert_true(
        plan["metadata"]["tenant_slug"] == "tenant_demo",
        "Manifesto deve registrar o tenant alvo",
    )
    assert_true(
        plan["safety"]["mode"] == "dry_run_manifest",
        "Primeira versao deve ser manifesto sem gravar banco",
    )
    assert_true(
        "nao executar em producao" in plan["safety"]["warning"].lower(),
        "Manifesto deve avisar contra uso em producao",
    )

    sections = [action["section"] for action in plan["actions"]]
    assert_true(
        sections[:8]
        == [
            "empresa",
            "usuarios",
            "financeiro.bancos",
            "financeiro.formas_pagamento",
            "financeiro.categorias",
            "financeiro.impostos",
            "fornecedores",
            "clientes",
        ],
        "Seed deve respeitar ordem operacional antes de produtos/pets",
    )
    assert_true("produtos" in sections, "Seed deve incluir produtos")
    assert_true("pets" in sections, "Seed deve incluir pets")
    assert_true("servicos" in sections, "Seed deve incluir servicos")
    assert_true(
        plan["summary"]["total_actions"] == len(plan["actions"]),
        "Resumo deve bater com a lista de acoes",
    )
    assert_true(
        plan["summary"]["counts"]["produtos"] == 4,
        "Resumo deve contar produtos da base demo",
    )
    assert_true(
        all(action["operation"] == "upsert" for action in plan["actions"]),
        "Todas as acoes devem ser idempotentes",
    )
    assert_true(
        len({action["key"] for action in plan["actions"]}) == len(plan["actions"]),
        "Chaves do manifesto precisam ser unicas",
    )

    json_result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(json_result.returncode == 0, json_result.stderr or json_result.stdout)
    json_output = json.loads(json_result.stdout)
    assert_true(
        json_output["summary"]["counts"]["clientes"] == 3,
        "CLI JSON deve emitir resumo",
    )

    markdown_result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--format",
            "markdown",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(
        markdown_result.returncode == 0,
        markdown_result.stderr or markdown_result.stdout,
    )
    assert_true(
        "# Manifesto de seed demo" in markdown_result.stdout,
        "Markdown deve ter titulo",
    )
    assert_true(
        "Pet Feliz Demo" in markdown_result.stdout,
        "Markdown deve citar empresa demo",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        outside_manifest = Path(tmp_dir) / "manifesto.json"
        out_result = subprocess.run(
            [
                sys.executable,
                str(GENERATOR_PATH),
                "--json",
                str(DATA_PATH),
                "--tenant-slug",
                "tenant_demo",
                "--format",
                "json",
                "--out",
                str(outside_manifest),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert_true(
            out_result.returncode != 0,
            "Gerador nao deve aceitar caminho de saida controlado pela CLI",
        )
        assert_true(
            not outside_manifest.exists(),
            "Gerador nao deve criar arquivo fora do fluxo seguro",
        )

    print("Marketing demo seed plan contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
