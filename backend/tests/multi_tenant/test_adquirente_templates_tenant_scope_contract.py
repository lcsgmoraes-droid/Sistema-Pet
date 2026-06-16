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

    assert "from app.financeiro_models import TemplateAdquirente" in source
    assert '"nome_adquirente": "STONE"' in source
    assert '"nome_adquirente": "CIELO"' in source
    assert '"nome_adquirente": "REDE"' in source
    assert source.count('"tipo_relatorio": "recebimentos"') == 3
    assert (
        'TemplateAdquirente.nome_adquirente == template_data["nome_adquirente"]'
        in source
    )
    assert (
        'TemplateAdquirente.tipo_relatorio == template_data["tipo_relatorio"]' in source
    )
    assert 'nome_adquirente=template_data["nome_adquirente"]' in source
    assert 'tipo_relatorio=template_data["tipo_relatorio"]' in source

    for stale_fragment in (
        "from app.conciliacao_models import AdquirenteTemplate",
        "AdquirenteTemplate.",
        'adquirente=template_data["adquirente"]',
        'versao=template_data["versao"]',
        'descricao=template_data["descricao"]',
        'nome=template_data["nome"]',
        'tipo_arquivo=template_data["tipo_arquivo"]',
    ):
        assert stale_fragment not in source
