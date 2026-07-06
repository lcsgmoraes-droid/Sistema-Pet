from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = REPO_ROOT / "frontend" / "src"
BACKEND_ROOT = REPO_ROOT / "backend"


def _read(path: Path) -> str:
    assert path.exists(), f"Arquivo esperado nao existe: {path}"
    return path.read_text(encoding="utf-8")


def test_ajuste_saldo_bancario_fica_no_modulo_financeiro():
    lazy_pages = _read(FRONTEND_ROOT / "app" / "lazyPages.jsx")
    finance_routes = _read(FRONTEND_ROOT / "app" / "routes" / "FinanceRoutes.jsx")
    menu_config = _read(FRONTEND_ROOT / "components" / "layout" / "menuConfig.js")
    contas_bancarias = _read(FRONTEND_ROOT / "components" / "ContasBancarias.jsx")

    assert "AjusteSaldosBancarios" in lazy_pages
    assert "AjusteSaldosBancarios" in finance_routes
    assert 'path="financeiro/ajuste-saldos"' in finance_routes
    assert 'path: "/financeiro/ajuste-saldos"' in menu_config

    assert "Ajustar saldo" not in contas_bancarias
    assert "/ajustar-saldo" not in contas_bancarias


def test_tela_financeira_ajuste_saldos_expoe_fluxo_em_lote():
    source = _read(FRONTEND_ROOT / "pages" / "AjusteSaldosBancarios.jsx")
    currency_input = _read(FRONTEND_ROOT / "components" / "CurrencyInput.jsx")

    assert "Ajuste de saldos bancarios" in source
    assert 'api.get("/contas-bancarias?apenas_ativas=true")' in source
    assert "/ajustar-saldo" in source
    assert "novo_saldo" in source
    assert "descricao" in source
    assert "Ajustar todos" in source
    assert "Ajustar saldo" in source
    assert "saldoAtualSistema" in source
    assert "diferenca" in source
    assert "allowNegative" in source
    assert "allowNegative = false" in currency_input


def test_backend_ajuste_saldo_mantem_rastro_sem_dre():
    source = _read(BACKEND_ROOT / "app" / "contas_bancarias_routes.py")
    ajustar_saldo = source.split("def ajustar_saldo(", 1)[1].split(
        '@router.get("/{conta_id}/movimentacoes"',
        1,
    )[0]

    assert '@router.post("/{conta_id}/ajustar-saldo")' in source
    assert "ContaBancaria.tenant_id == tenant_id" in ajustar_saldo
    assert "MovimentacaoFinanceira(" in ajustar_saldo
    assert 'origem_tipo="ajuste_manual"' in ajustar_saldo
    assert 'status="realizado"' in ajustar_saldo
    assert "user_id=current_user.id" in ajustar_saldo
    assert "tenant_id=tenant_id" in ajustar_saldo
    assert "conta.saldo_atual = novo_saldo" in ajustar_saldo
    assert "atualizar_dre" not in ajustar_saldo
    assert "DRE" not in ajustar_saldo
