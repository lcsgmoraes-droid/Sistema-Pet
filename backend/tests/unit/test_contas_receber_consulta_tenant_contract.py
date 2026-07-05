from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_listar_contas_receber_usa_tenant_e_busca_relacoes_no_tenant():
    source = _source("app/contas_receber_consulta_routes.py")
    listar = source.split("def listar_contas_receber(", 1)[1].split(
        "# ============================================================================",
        1,
    )[0]

    assert "tenant_id = user_and_tenant" in listar
    assert "ContaReceber.tenant_id == tenant_id" in listar
    assert "Venda.tenant_id == tenant_id" in listar
    assert "Cliente.tenant_id == tenant_id" in listar
    assert "ContaReceber.user_id == current_user.id" not in listar
    assert "Venda.user_id == current_user.id" not in listar


def test_buscar_conta_receber_exige_tenant_em_todas_as_relacoes():
    source = _source("app/contas_receber_consulta_routes.py")
    buscar = source.split("def buscar_conta_receber(", 1)[1].split(
        "# ============================================================================\n# REGISTRAR RECEBIMENTO",
        1,
    )[0]

    assert "tenant_id = user_and_tenant" in buscar
    assert "ContaReceber.tenant_id == tenant_id" in buscar
    assert "Cliente.tenant_id == tenant_id" in buscar
    assert "Venda.tenant_id == tenant_id" in buscar
    assert "ContaBancaria.tenant_id == tenant_id" in buscar


def test_dashboard_contas_receber_soma_apenas_tenant_atual():
    source = _source("app/contas_receber_consulta_routes.py")
    dashboard = source.split("def dashboard_contas_receber(", 1)[1].split(
        "# ============================================================================\n# PROCESSAR",
        1,
    )[0]

    assert "tenant_id = user_and_tenant" in dashboard
    assert dashboard.count("ContaReceber.tenant_id == tenant_id") >= 6
