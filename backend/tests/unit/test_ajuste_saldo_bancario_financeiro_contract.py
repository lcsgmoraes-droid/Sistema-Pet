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


def test_tela_bancos_expoe_previa_da_virada_historica():
    source = _read(FRONTEND_ROOT / "pages" / "BancosFinanceiro.jsx")

    assert "modalVirada" in source
    assert "abrirModalVirada" in source
    assert "preverViradaHistorica" in source
    assert "/virada-historica/previa" in source
    assert "Prever virada" in source
    assert "Virada historica" in source
    assert "Baixas historicas" in source
    assert "contas_receber_baixadas" in source
    assert "contas_pagar_baixadas" in source
    assert "saldo_bancario" in source


def test_tela_bancos_aplica_virada_historica_com_confirmacao_e_saldo_esperado():
    source = _read(FRONTEND_ROOT / "pages" / "BancosFinanceiro.jsx")

    assert "aplicarViradaHistorica" in source
    assert "/virada-historica/aplicar" in source
    assert "VIRADA_BANCARIA_HISTORICA" in source
    assert "expected_saldo_atual" in source
    assert "confirmacao" in source
    assert "baixar_historico" in source
    assert "ajustar_saldo" in source
    assert "Aplicar virada" in source


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


def test_backend_bancos_tem_previa_segura_da_virada_historica():
    source = _read(BACKEND_ROOT / "app" / "contas_bancarias_routes.py")

    assert '@router.get("/virada-historica/previa")' in source
    assert source.index('@router.get("/virada-historica/previa")') < source.index(
        '@router.get("/{conta_id}"'
    )

    previa = source.split("def prever_virada_bancaria_historica(", 1)[1].split(
        '@router.get("/{conta_id}"',
        1,
    )[0]
    assert "executar_virada_bancaria_historica" in previa
    assert "tenant_id=str(tenant_id)" in previa
    assert "apply_baixas=False" in previa
    assert "apply_saldo=False" in previa
    assert "confirm_token=None" in previa


def test_backend_bancos_aplica_virada_historica_com_travas_de_confirmacao():
    source = _read(BACKEND_ROOT / "app" / "contas_bancarias_routes.py")

    assert '@router.post("/virada-historica/aplicar")' in source
    assert source.index('@router.post("/virada-historica/aplicar")') < source.index(
        '@router.get("/{conta_id}"'
    )
    assert "CONFIRM_TOKEN_VIRADA_BANCARIA" in source

    apply_route = source.split("def aplicar_virada_bancaria_historica(", 1)[1].split(
        '@router.get("/{conta_id}"',
        1,
    )[0]
    assert "executar_virada_bancaria_historica" in apply_route
    assert "tenant_id=str(tenant_id)" in apply_route
    assert "apply_baixas=payload.baixar_historico" in apply_route
    assert "apply_saldo=payload.ajustar_saldo" in apply_route
    assert "expected_saldo_atual=payload.expected_saldo_atual" in apply_route
    assert "confirm_token=payload.confirmacao" in apply_route
    assert "HTTPException(status_code=400" in apply_route


def test_backend_bancos_audita_apply_da_virada_bancaria():
    source = _read(BACKEND_ROOT / "app" / "contas_bancarias_routes.py")
    apply_route = source.split("def aplicar_virada_bancaria_historica(", 1)[1].split(
        '@router.get("/{conta_id}"',
        1,
    )[0]

    assert "log_business_event" in source
    assert "build_bank_cutover_metadata" in source
    assert "current_user, tenant_id = user_and_tenant" in apply_route
    assert 'event="financeiro.virada_bancaria_historica_aplicada"' in apply_route
    assert 'entity_type="contas_bancarias"' in apply_route
    assert "entity_id=payload.conta_bancaria_id" in apply_route
    assert "user_id=current_user.id" in apply_route
    assert "tenant_id=tenant_id" in apply_route
    assert "metadata=build_bank_cutover_metadata(" in apply_route
    assert "commit=True" in apply_route
