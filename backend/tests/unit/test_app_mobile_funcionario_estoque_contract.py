from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def extract_block(source: str, marker: str) -> str:
    assert marker in source, f"Marker not found: {marker}"
    start = source.index(marker)
    next_route = source.find("\n@router.", start + len(marker))
    if next_route == -1:
        return source[start:]
    return source[start:next_route]


def test_mobile_auth_exposes_funcionario_operational_profile():
    source = read_repo("backend/app/routes/ecommerce_auth.py")

    assert "is_funcionario" in source
    assert '"funcionario"' in source
    assert "perfil_operacional" in source
    assert "tipo_cadastro" in source


def test_employee_stock_routes_search_erp_products_not_public_app_catalog():
    source = read_repo("backend/app/routes/app_mobile_routes.py")

    assert '"/funcionario/estoque/produtos/buscar"' in source
    assert '"/funcionario/estoque/produtos/barcode/{barcode}"' in source
    assert '"/funcionario/estoque/balanco"' in source

    search_block = extract_block(source, "def buscar_produtos_funcionario_estoque")
    barcode_block = extract_block(source, "def buscar_produto_funcionario_barcode")

    for block in (search_block, barcode_block):
        assert "Produto.tenant_id == tenant_id" in block
        assert "Produto.ativo.is_(True)" in block
        assert "Produto.anunciar_app == True" not in block
        assert "Produto.is_sellable == True" not in block


def test_employee_stock_balance_uses_final_count_difference():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    block = extract_block(source, "def registrar_balanco_funcionario_estoque")

    assert "FuncionarioBalancoRequest" in source
    assert "saldo_final" in block
    assert "estoque_atual" in block
    assert "diferenca" in block
    assert 'motivo="balanco"' in block or "motivo='balanco'" in block
    assert "App funcionario - balanco por camera" in block
    assert "sem_alteracao" in block


def test_mobile_app_routes_employee_users_to_balance_screen():
    app_navigator = read_repo("app-mobile/src/navigation/AppNavigator.tsx")
    auth_store = read_repo("app-mobile/src/store/auth.store.ts")
    types_source = read_repo("app-mobile/src/types/index.ts")

    assert "FuncionarioNavigator" in app_navigator
    assert "is_funcionario" in app_navigator
    assert '"funcionario"' in types_source
    assert "is_funcionario" in auth_store


def test_mobile_employee_stock_service_and_screen_exist():
    service = read_repo("app-mobile/src/services/funcionarioEstoque.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioBalancoScreen.tsx")
    navigator = read_repo("app-mobile/src/navigation/FuncionarioNavigator.tsx")

    assert "/app/funcionario/estoque/produtos/barcode" in service
    assert "/app/funcionario/estoque/produtos/buscar" in service
    assert "/app/funcionario/estoque/balanco" in service
    assert "CameraView" in screen
    assert "saldoFinal" in screen
    assert "registrarBalancoFuncionario" in screen
    assert "historicoSessao" in screen
    assert "Lancamentos da sessao" in screen
    assert "FuncionarioBalanco" in navigator


def test_mobile_employee_stock_adjustment_hides_current_stock_and_uses_autocomplete():
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioBalancoScreen.tsx")

    assert "autocompleteProdutosTimer" in screen
    assert "buscarManual(false)" in screen
    assert 'placeholder="Buscar produto por nome, codigo ou barras"' in screen
    assert "setSaldoFinal(String(item.estoque_atual" not in screen
    assert "Estoque atual" not in screen
    assert "diferencaBox" not in screen


def test_employee_stock_search_ranks_full_phrase_before_loose_code_digits():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    search_block = extract_block(source, "def buscar_produtos_funcionario_estoque")

    assert "_produto_busca_filtros_funcionario(termo)" in search_block
    assert "_produto_busca_rank_funcionario(termo)" in search_block
    assert "_termo_parece_codigo_produto_funcionario" in source
    assert "_barcode_filters_for_produto(termo_digits)" not in search_block


def test_mobile_employee_stock_uses_keyboard_safe_scroll_and_product_images():
    service = read_repo("app-mobile/src/services/funcionarioEstoque.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioBalancoScreen.tsx")

    assert "resolveMediaUrl" in service
    assert "imagem_url: resolveMediaUrl" in service
    assert "KeyboardSafeScrollView" in screen
    assert "<KeyboardSafeScrollView" in screen
    assert "KeyboardAvoidingView" not in screen
    assert "Image" in screen
    assert "item.imagem_url" in screen
    assert "produto.imagem_url" in screen
    assert "produtoImagemWrap" in screen
