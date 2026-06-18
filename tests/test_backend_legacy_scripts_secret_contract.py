from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

LEGACY_ROOT_SCRIPTS = (
    "atualizar_template_stone.py",
    "corrigir_template_stone.py",
    "criar_admin_prod.py",
    "criar_banco_producao.py",
    "dar_full_permissoes.py",
    "importar_producao_lotes.py",
    "seed_opcoes_racao_standalone.py",
    "seed_templates.py",
    "temp_seed_prod.py",
    "testar_api_produtos.py",
)


def test_legacy_root_scripts_do_not_embed_known_credentials():
    forbidden_fragments = (
        "petshop_pass" + "_2026",
        "admin-dev" + "-token",
        "postgresql://postgres:" + "sua_senha",
        "password='postgres'",
        'password="postgres"',
        "'password': 'admin'",
        '"password": "postgres"',
        "'password': 'senha'",
        "$2b$12$" + "LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.6GZjMe/.hizq",
    )

    offenders: list[str] = []
    for script in LEGACY_ROOT_SCRIPTS:
        source = (BACKEND / script).read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in source:
                offenders.append(f"{script}: {fragment[:24]}")

    assert offenders == []
