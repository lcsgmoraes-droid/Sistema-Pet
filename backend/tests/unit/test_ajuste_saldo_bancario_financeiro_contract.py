from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = REPO_ROOT / "frontend" / "src"
BACKEND_ROOT = REPO_ROOT / "backend"


def _read(path: Path) -> str:
    assert path.exists(), f"Arquivo esperado nao existe: {path}"
    return path.read_text(encoding="utf-8")


def test_bancos_fica_no_modulo_financeiro_com_extrato_e_modal():
    lazy_pages = _read(FRONTEND_ROOT / "app" / "lazyPages.jsx")
    finance_routes = _read(FRONTEND_ROOT / "app" / "routes" / "FinanceRoutes.jsx")
    menu_config = _read(FRONTEND_ROOT / "components" / "layout" / "menuConfig.js")
    contas_bancarias = _read(FRONTEND_ROOT / "components" / "ContasBancarias.jsx")
    bancos_page = _read(FRONTEND_ROOT / "pages" / "BancosFinanceiro.jsx")

    assert "BancosFinanceiro" in lazy_pages
    assert "BancosFinanceiro" in finance_routes
    assert 'path="financeiro/bancos"' in finance_routes
    assert 'path: "/financeiro/bancos"' in menu_config
    assert 'label: "Bancos"' in menu_config
    assert "Extrato" in bancos_page
    assert "modalAjuste" in bancos_page
    assert "/movimentacoes" in bancos_page
    assert "/ajustar-saldo" in bancos_page

    assert "Ajustar saldo" not in contas_bancarias
    assert "/ajustar-saldo" not in contas_bancarias


def test_tela_bancos_expoe_ajuste_por_modal_e_saldo_por_conta():
    source = _read(FRONTEND_ROOT / "pages" / "BancosFinanceiro.jsx")
    currency_input = _read(FRONTEND_ROOT / "components" / "CurrencyInput.jsx")

    assert 'title="Bancos"' in source
    assert 'api.get("/contas-bancarias?apenas_ativas=true")' in source
    assert "carregarMovimentacoes" in source
    assert "/movimentacoes" in source
    assert "/ajustar-saldo" in source
    assert "modalAjuste" in source
    assert "resetarModalAjuste" in source
    assert "resetarModalAjuste();" in source
    assert "novo_saldo" in source
    assert "descricao" in source
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
