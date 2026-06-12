from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _function_block(source: str, marker: str) -> str:
    assert marker in source, f"Marker not found: {marker}"
    start = source.index(marker)
    next_function = source.find("\ndef ", start + len(marker))
    if next_function == -1:
        return source[start:]
    return source[start:next_function]


def test_provisao_trabalhista_filtra_tenant_do_cargo_no_join_de_funcionarios():
    source = _source("backend/app/services/provisao_trabalhista_service.py")
    block = _function_block(source, "def gerar_provisao_trabalhista_mensal")

    assert "Cliente.tenant_id == tenant_id" in block
    assert "Cargo.tenant_id == tenant_id" in block


def test_provisao_beneficios_filtra_tenant_do_cargo_no_join_de_funcionarios():
    source = _source("backend/app/services/provisao_beneficios_service.py")
    block = _function_block(source, "def gerar_provisao_ferias_e_13_mensal")

    assert "Cliente.tenant_id == tenant_id" in block
    assert "Cargo.tenant_id == tenant_id" in block
