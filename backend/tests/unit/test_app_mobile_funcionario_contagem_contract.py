from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def extract_block(source: str, marker: str) -> str:
    assert marker in source, f"Marker not found: {marker}"
    start = source.index(marker)
    next_route = source.find("\n@router.", start + len(marker))
    if next_route == -1:
        return source[start:]
    return source[start:next_route]


def test_employee_count_routes_save_without_stock_movement():
    source = read_repo("backend/app/routes/app_mobile_funcionario_contagem_routes.py")
    save_block = extract_block(source, "def criar_contagem_funcionario")

    assert '"/funcionario/contagens"' in source
    assert "FuncionarioContagemRequest" in source
    assert "FuncionarioContagem" in source
    assert "FuncionarioContagemItem" in source
    assert "Produto.tenant_id == tenant_id" in save_block
    assert "Produto.ativo.is_(True)" in save_block
    assert "EstoqueMovimentacao" not in save_block
    assert "sincronizar_bling_background" not in save_block
    assert "Produto.estoque_atual" not in save_block
    assert "estoque_atual =" not in save_block


def test_employee_count_exports_follow_value_checkboxes():
    source = read_repo("backend/app/routes/app_mobile_funcionario_contagem_routes.py")
    export_block = extract_block(source, "def exportar_contagem_funcionario")

    assert "_colunas_exportacao_contagem" in source
    assert "mostrar_custo" in export_block
    assert "mostrar_venda" in export_block
    assert "Custo unitario" in source
    assert "Total custo" in source
    assert "Venda unitaria" in source
    assert "Total venda" in source


def test_employee_count_delete_is_scoped_to_employee_and_tenant():
    source = read_repo("backend/app/routes/app_mobile_funcionario_contagem_routes.py")
    delete_block = extract_block(source, "def excluir_contagem_funcionario")

    assert "@router.delete(" in source
    assert '"/funcionario/contagens/{contagem_id}"' in source
    assert "_get_contagem_funcionario_or_404(" in delete_block
    assert "funcionario.id" in delete_block
    assert "tenant_id" in delete_block
    assert "db.delete(contagem)" in delete_block
    assert "db.commit()" in delete_block
    assert "EstoqueMovimentacao" not in delete_block
    assert "Produto.estoque_atual" not in delete_block


def test_employee_count_can_apply_saved_count_to_stock_once():
    source = read_repo("backend/app/routes/app_mobile_funcionario_contagem_routes.py")
    apply_block = extract_block(source, "def aplicar_contagem_estoque_funcionario")

    assert '"/funcionario/contagens/{contagem_id}/estoque"' in source
    assert "FuncionarioContagemAplicarEstoqueRequest" in source
    assert '"entrada"' in source
    assert '"balanco"' in source
    assert "_get_contagem_funcionario_or_404(" in apply_block
    assert "funcionario.id" in apply_block
    assert "tenant_id" in apply_block
    assert "contagem.status" in apply_block
    assert "entrada_aplicada" in apply_block
    assert "balanco_aplicado" in apply_block
    assert "Produto.tenant_id == tenant_id" in apply_block
    assert "Produto.ativo.is_(True)" in apply_block
    assert "_produto_permite_balanco_funcionario" in apply_block
    assert "modo == \"entrada\"" in apply_block
    assert "estoque_novo = estoque_atual + quantidade" in apply_block
    assert "estoque_novo = quantidade" in apply_block
    assert "EstoqueMovimentacao(" in apply_block
    assert 'motivo=modo' in apply_block
    assert "Produto.estoque_atual" not in apply_block
    assert "produto.estoque_atual = estoque_novo" in apply_block
    assert "sincronizar_bling_background" in apply_block


def test_employee_count_allows_optional_supplier_search():
    source = read_repo("backend/app/routes/app_mobile_funcionario_contagem_routes.py")
    supplier_block = extract_block(
        source, "def buscar_fornecedores_contagem_funcionario"
    )

    assert '"/funcionario/contagens/fornecedores/buscar"' in source
    assert "Cliente.tenant_id == tenant_id" in supplier_block
    assert "Cliente.tipo_cadastro" in supplier_block
    assert '"fornecedor"' in supplier_block or "'fornecedor'" in supplier_block
    assert "fornecedor_id" in source
    assert "fornecedor_nome_snapshot" in source


def test_employee_count_models_and_migration_are_registered():
    models = read_repo("backend/app/funcionario_contagem_models.py")
    produtos_models = read_repo("backend/app/produtos_models.py")
    db_base = read_repo("backend/app/db/base.py")
    migration_files = list(
        (REPO_ROOT / "backend/alembic/versions").glob("*funcionario_contagens*.py")
    )

    assert '__tablename__ = "funcionario_contagens"' in models
    assert '__tablename__ = "funcionario_contagem_itens"' in models
    assert "FuncionarioContagem" in produtos_models
    assert "FuncionarioContagemItem" in produtos_models
    assert "funcionario_contagem_models" in db_base
    assert migration_files, "Migration de funcionario_contagens nao encontrada"
    migration = migration_files[0].read_text(encoding="utf-8")
    assert "funcionario_contagens" in migration
    assert "funcionario_contagem_itens" in migration
    assert "apply_tenant_rls" in migration
    assert "FUNCIONARIO_CONTAGENS_RLS_TABLES" in migration


def test_mobile_employee_count_service_screen_and_navigation_exist():
    service = read_repo("app-mobile/src/services/funcionarioContagem.service.ts")
    screen = read_repo(
        "app-mobile/src/screens/funcionario/FuncionarioContagemScreen.tsx"
    )
    content = read_repo(
        "app-mobile/src/screens/funcionario/contagem/FuncionarioContagemContent.tsx"
    )
    scanner = read_repo(
        "app-mobile/src/screens/funcionario/contagem/FuncionarioContagemScanner.tsx"
    )
    mobile_screen_source = f"{screen}\n{content}\n{scanner}"
    navigator = read_repo("app-mobile/src/navigation/FuncionarioNavigator.tsx")
    home = read_repo("app-mobile/src/screens/funcionario/FuncionarioHomeScreen.tsx")
    types = read_repo("app-mobile/src/types/index.ts")
    route_types = read_repo("app-mobile/src/types/funcionarioNavigation.ts")

    assert "/app/funcionario/contagens" in service
    assert "/app/funcionario/contagens/fornecedores/buscar" in service
    assert "excluirContagemFuncionario" in service
    assert "api.delete(`/app/funcionario/contagens/${contagemId}`)" in service
    assert "aplicarContagemEstoqueFuncionario" in service
    assert "api.post(`/app/funcionario/contagens/${contagemId}/estoque`" in service
    assert "expo-file-system" in service
    assert 'Share } from "react-native"' in service
    assert "expo-sharing" not in service
    assert "CameraView" in scanner
    assert "salvarContagemFuncionario" in screen
    assert "baixarContagemFuncionario" in screen
    assert "mostrarCusto" in mobile_screen_source
    assert "mostrarVenda" in mobile_screen_source
    assert "fornecedor" in mobile_screen_source
    assert "Adicionar item" in mobile_screen_source
    assert "PDF" in mobile_screen_source
    assert "Excel" in mobile_screen_source
    assert "confirmarExcluirContagem" in mobile_screen_source
    assert "Excluir contagem" in mobile_screen_source
    assert "confirmarAplicarEstoque" in mobile_screen_source
    assert "Fazer entrada" in mobile_screen_source
    assert "Fazer balanco" in mobile_screen_source
    assert "FuncionarioContagem" in navigator
    assert "FuncionarioContagem" in route_types
    assert "Contagem" in home
    assert "FuncionarioContagem" in types
