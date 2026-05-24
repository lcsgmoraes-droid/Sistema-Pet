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


def test_funcionario_pdv_endpoints_exist():
    source = read_repo("backend/app/routes/app_mobile_routes.py")

    assert '"/funcionario/pdv/produtos/buscar"' in source
    assert '"/funcionario/pdv/produtos/barcode/{barcode}"' in source
    assert '"/funcionario/pdv/clientes/buscar"' in source
    assert '"/funcionario/pdv/caixa/aberto"' in source
    assert '"/funcionario/pdv/vendas/finalizar"' in source


def test_funcionario_pdv_delegates_to_official_sale_flow():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    block = extract_block(source, "def finalizar_venda_funcionario_pdv")

    assert "VendaService.criar_venda" in block
    assert "VendaService.finalizar_venda" in block
    assert "processar_comissoes_venda" in block
    assert '"funcionario_id": funcionario.id' in block
    assert '"vendedor_id": current_user.id' in block


def test_funcionario_pdv_does_not_manage_cash_register():
    source = read_repo("backend/app/routes/app_mobile_routes.py")

    assert '"/funcionario/pdv/caixa/abrir"' not in source
    assert '"/funcionario/pdv/caixa/fechar"' not in source
    assert "AbrirCaixaSchema" not in source
    assert "FecharCaixaSchema" not in source


def test_funcionario_pdv_searches_sellable_erp_products_not_app_catalog():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    search_block = extract_block(source, "def buscar_produtos_funcionario_pdv")
    barcode_block = extract_block(source, "def buscar_produto_funcionario_pdv_barcode")

    for block in (search_block, barcode_block):
        assert "Produto.tenant_id == tenant_id" in block
        assert "Produto.ativo == True" in block
        assert "Produto.tipo_produto.in_" in block
        assert "Produto.anunciar_app" not in block
        assert "Produto.is_sellable" not in block


def test_mobile_app_has_employee_pdv_navigation_service_and_screen():
    nav_types = read_repo("app-mobile/src/types/funcionarioNavigation.ts")
    navigator = read_repo("app-mobile/src/navigation/FuncionarioNavigator.tsx")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    assert "FuncionarioHome" in nav_types
    assert "FuncionarioPdv" in nav_types
    assert "FuncionarioHomeScreen" in navigator
    assert "FuncionarioPdvScreen" in navigator
    assert "/app/funcionario/pdv/produtos/barcode" in service
    assert "/app/funcionario/pdv/vendas/finalizar" in service
    assert "CameraView" in screen
    assert "finalizarVendaPdv" in screen


def test_funcionario_pdv_supports_campaign_benefits_preview_contract():
    backend = read_repo("backend/app/routes/app_mobile_routes.py")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    assert '"/funcionario/pdv/beneficios/preview"' in backend
    assert "preview_coupon_redemption" in backend
    assert "CashbackTransaction" in backend
    assert "FuncionarioPdvBeneficiosPreviewRequest" in backend
    assert "FuncionarioPdvBeneficiosPreviewResponse" in backend

    assert "/app/funcionario/pdv/beneficios/preview" in service
    assert "previewBeneficiosPdv" in service
    assert "beneficiosPreview" in screen
    assert "cupomCodigo" in screen
    assert "usarCashback" in screen


def test_funcionario_pdv_finalization_passes_coupon_and_cashback_to_official_sale_flow():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    block = extract_block(source, "def finalizar_venda_funcionario_pdv")

    assert "cupom_codigo" in block
    assert "desconto_cupom" in block
    assert "cashback_valor" in block
    assert '"cupom_code": beneficios["cupom_code"]' in block
    assert '"cupom_discount_applied": beneficios["desconto_cupom"]' in block
    assert '"forma_pagamento": "Cashback"' in block
    assert "cupom_code=beneficios[\"cupom_code\"]" in block
    assert "cupom_discount_applied=beneficios[\"desconto_cupom\"]" in block
