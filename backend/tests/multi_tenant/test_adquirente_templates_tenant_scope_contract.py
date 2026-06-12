from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_seed_adquirentes_uses_selected_tenant_dependency():
    source = _source("app/admin_routes.py")

    assert "get_current_user_and_tenant" in source
    assert "Depends(get_current_user_and_tenant)" in source
    assert "from app.auth_routes_multitenant import get_current_user" not in source
    assert "Depends(get_current_user)" not in source
    assert "current_user.get('tenant_id')" not in source
    assert "criar_templates_adquirentes(db, tenant_id)" in source


def test_seed_adquirentes_matches_current_template_model_schema():
    source = _source("app/seed_adquirentes.py")

    assert '"nome": "STONE"' in source
    assert '"nome": "CIELO"' in source
    assert '"nome": "REDE"' in source
    assert source.count('"tipo_arquivo": "recebimentos"') == 3
    assert 'AdquirenteTemplate.nome == template_data["nome"]' in source
    assert 'AdquirenteTemplate.tipo_arquivo == template_data["tipo_arquivo"]' in source
    assert 'nome=template_data["nome"]' in source
    assert 'tipo_arquivo=template_data["tipo_arquivo"]' in source

    for stale_fragment in (
        "AdquirenteTemplate.adquirente",
        "AdquirenteTemplate.versao",
        "adquirente=template_data",
        "versao=template_data",
        "descricao=template_data",
    ):
        assert stale_fragment not in source
