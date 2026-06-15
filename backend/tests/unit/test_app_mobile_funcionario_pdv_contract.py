import os
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

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
    assert '"/funcionario/pdv/formas-pagamento"' in source
    assert '"/funcionario/pdv/vendas/salvar"' in source
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


def test_funcionario_pdv_reuses_open_erp_cash_register_for_tenant():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    service = read_repo("backend/app/vendas/service.py")
    caixa_service = read_repo("backend/app/caixa/service.py")
    caixa_block = extract_block(source, "def obter_caixa_aberto_funcionario_pdv")
    finalizar_block = extract_block(source, "def finalizar_venda_funcionario_pdv")

    assert "def _obter_caixa_aberto_funcionario_pdv" in source
    helper_block = extract_block(source, "def _obter_caixa_aberto_funcionario_pdv")
    assert "Caixa.tenant_id == tenant_id" in helper_block
    assert 'Caixa.status == "aberto"' in helper_block
    assert "case((Caixa.usuario_id == current_user.id, 0), else_=1)" in helper_block

    assert "_obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)" in caixa_block
    assert "_obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)" in finalizar_block
    assert "caixa_id=caixa.id" in finalizar_block
    assert "permitir_caixa_tenant=True" in finalizar_block

    assert "caixa_id: Optional[int] = None" in service
    assert "permitir_caixa_tenant: bool = False" in service
    assert "CaixaService.validar_caixa_aberto(" in service
    assert "caixa_id=caixa_id" in service
    assert "permitir_caixa_tenant=permitir_caixa_tenant" in service

    assert "tenant_id: Optional[str] = None" in caixa_service
    assert "permitir_caixa_tenant: bool = False" in caixa_service
    assert "Caixa.id == caixa_id" in caixa_service
    assert "Caixa.tenant_id == tenant_id" in caixa_service


def test_funcionario_pdv_searches_sellable_erp_products_not_app_catalog():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    search_block = extract_block(source, "def buscar_produtos_funcionario_pdv")
    barcode_block = extract_block(source, "def buscar_produto_funcionario_pdv_barcode")

    for block in (search_block, barcode_block):
        assert "Produto.tenant_id == tenant_id" in block
        assert (
            "Produto.ativo.is_(True)" in block
            or "Produto.ativo == true()" in block
        )
        assert "Produto.tipo_produto.in_" in block
        assert "Produto.anunciar_app" not in block
        assert "Produto.is_sellable" not in block


def test_funcionario_pdv_searches_products_and_clients_like_web_pdv():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    product_block = extract_block(source, "def buscar_produtos_funcionario_pdv")
    barcode_block = extract_block(source, "def buscar_produto_funcionario_pdv_barcode")
    client_block = extract_block(source, "def buscar_clientes_funcionario_pdv")
    client_lookup_block = extract_block(source, "def _buscar_cliente_pdv_funcionario")
    serializer_block = extract_block(source, "def _serialize_funcionario_pdv_cliente")
    types = read_repo("app-mobile/src/types/index.ts")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    for field in [
        "Produto.nome.ilike",
        "Produto.codigo.ilike",
        "Produto.codigo_barras.ilike",
        "Produto.gtin_ean.ilike",
        "Produto.codigos_barras_alternativos.ilike",
    ]:
        assert field in source
    assert "_produto_busca_filtros_funcionario(termo)" in product_block
    assert "_produto_busca_rank_funcionario(termo)" in product_block
    assert "_barcode_filters_for_produto(barcode)" in barcode_block

    for field in [
        "Cliente.nome.ilike",
        "Cliente.telefone.ilike",
        "Cliente.celular.ilike",
        "Cliente.cpf.ilike",
        "Cliente.cnpj.ilike",
    ]:
        assert field in client_block

    assert 'Cliente.tipo_cadastro == "cliente"' not in client_block
    assert 'Cliente.tipo_cadastro == "cliente"' not in client_lookup_block
    for field in [
        "telefone_digits.ilike",
        "celular_digits.ilike",
        "cpf_digits.ilike",
        "cnpj_digits.ilike",
    ]:
        assert field in client_block
    assert '"tipo_cadastro": cliente.tipo_cadastro' in serializer_block
    assert "tipo_cadastro?: string | null" in types
    assert "tipo_cadastro: data.tipo_cadastro ?? null" in service

    assert "autocompleteProdutosTimer" in screen
    assert "autocompleteClientesTimer" in screen
    assert 'placeholder="Buscar produto por nome, codigo ou barras"' in screen
    assert 'placeholder="Buscar pessoa por nome ou telefone"' in screen
    assert "item.tipo_cadastro" in screen


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
    assert "beneficios_gerados" in backend
    assert "beneficios_gerados" in service
    assert "Beneficios que esta venda vai gerar" in screen


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


def test_funcionario_pdv_supports_credit_installments_from_erp_payment_rules():
    backend = read_repo("backend/app/routes/app_mobile_routes.py")
    types = read_repo("app-mobile/src/types/index.ts")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")
    finalizar_block = extract_block(backend, "def finalizar_venda_funcionario_pdv")

    assert "FuncionarioPdvFormaPagamentoResponse" in backend
    assert "FormaPagamento.tenant_id == tenant_id" in backend
    assert "FormaPagamento.ativo.is_(True)" in backend
    assert "numero_parcelas" in backend
    assert "numero_parcelas: number" in types
    assert "FuncionarioPdvFormaPagamentoOpcao" in types
    assert "/app/funcionario/pdv/formas-pagamento" in service
    assert "listarFormasPagamentoPdv" in service
    assert "parcelasCredito" in screen
    assert "numeroParcelas" in screen
    assert "setNumeroParcelas" in screen
    assert '"numero_parcelas": numero_parcelas' in finalizar_block
    assert '"numero_parcelas": 1' not in finalizar_block


def test_funcionario_pdv_collects_card_brand_nsu_and_erp_payment_rule():
    backend = read_repo("backend/app/routes/app_mobile_routes.py")
    types = read_repo("app-mobile/src/types/index.ts")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")
    formas_block = extract_block(backend, "def listar_formas_pagamento_funcionario_pdv")
    finalizar_block = extract_block(backend, "def finalizar_venda_funcionario_pdv")

    for field in ["bandeira", "operadora", "requer_nsu", "tipo_cartao", "split_parcelas"]:
        assert field in backend
        assert field in types
        assert field in service

    assert "forma_pagamento_id" in backend
    assert "forma_pagamento_id" in types
    assert "forma_pagamento_id" in screen
    assert '"requer_nsu": bool(forma.requer_nsu)' in formas_block
    assert '"bandeira": forma.bandeira' in formas_block
    assert '"operadora": forma.operadora' in formas_block
    assert '"forma_pagamento_id": dados.pagamento.forma_pagamento_id' in finalizar_block
    assert '"bandeira": dados.pagamento.bandeira' in finalizar_block
    assert '"nsu_cartao": dados.pagamento.nsu_cartao' in finalizar_block
    assert "formaPagamentoSelecionada" in screen
    assert "opcoesCartao" in screen
    assert "Bandeira/operadora" in screen
    assert "NSU" in screen
    assert "setNsuCartao" in screen


def test_funcionario_pdv_card_brand_is_explicit_and_nsu_optional():
    backend = read_repo("backend/app/routes/app_mobile_routes.py")
    resolver_block = extract_block(
        backend, "def _resolver_forma_pagamento_cartao_funcionario_pdv"
    )
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    assert "Informe o NSU do cartao" not in resolver_block
    assert "formaPagamentoSelecionada?.requer_nsu && !nsuCartao.trim()" not in screen
    assert "setFormaPagamentoIdSelecionada(opcoesCartao[0]?.id ?? null)" not in screen
    assert "Selecione a bandeira/operadora do cartao" in screen
    assert "NSU (opcional)" in screen


def test_funcionario_pdv_search_ranks_full_phrase_before_loose_code_digits():
    source = read_repo("backend/app/routes/app_mobile_routes.py")
    search_block = extract_block(source, "def buscar_produtos_funcionario_pdv")

    assert "_produto_busca_filtros_funcionario(termo)" in search_block
    assert "_produto_busca_rank_funcionario(termo)" in search_block
    assert "_termo_parece_codigo_produto_funcionario" in source
    assert "_barcode_filters_for_produto(termo_digits)" not in search_block


def test_funcionario_pdv_uses_keyboard_safe_scroll_and_product_images():
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    assert "resolveMediaUrl" in service
    assert "imagem_url: resolveMediaUrl" in service
    assert "KeyboardSafeScrollView" in screen
    assert "<KeyboardSafeScrollView" in screen
    assert "KeyboardAvoidingView" not in screen
    assert "Image" in screen
    assert "produto.imagem_url" in screen
    assert "item.produto.imagem_url" in screen
    assert "produtoImagemWrap" in screen


def test_funcionario_pdv_can_save_open_sale_for_cashier_checkout():
    backend = read_repo("backend/app/routes/app_mobile_routes.py")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")
    save_block = extract_block(backend, "def salvar_venda_funcionario_pdv")

    assert "FuncionarioPdvSalvarRequest" in backend
    assert "FuncionarioPdvSalvarResponse" in backend
    assert "VendaService.criar_venda" in save_block
    assert "VendaService.finalizar_venda" not in save_block
    assert '"status": "aberta"' in save_block
    assert '"canal": "app_funcionario"' in save_block
    assert "/app/funcionario/pdv/vendas/salvar" in service
    assert "salvarVendaPdv" in service
    assert "Salvar para o caixa" in screen
    assert "salvarAberta" in screen


def test_funcionario_pdv_shows_customer_details_like_web_pdv():
    types = read_repo("app-mobile/src/types/index.ts")
    service = read_repo("app-mobile/src/services/funcionarioPdv.service.ts")
    screen = read_repo("app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx")

    for field in [
        "email?: string | null",
        "endereco?: string | null",
        "credito?: number",
        "fidelidade",
        "cupons_disponiveis",
    ]:
        assert field in types
    for field in [
        "email: data.email ?? null",
        "endereco: data.endereco ?? null",
        "credito: Number(data.credito ?? 0)",
        "fidelidade: data.fidelidade ?? null",
        "cupons_disponiveis: data.cupons_disponiveis ?? []",
    ]:
        assert field in service
    assert "mostrarDetalhesCliente" in screen
    assert "Detalhes do cliente" in screen
    assert "Cartao fidelidade" in screen
    assert "Cupons disponiveis" in screen


def test_erp_recent_sales_highlights_employee_mobile_origin():
    sidebar = read_repo("frontend/src/components/pdv/PDVVendasRecentesSidebar.jsx")

    assert "app_funcionario" in sidebar
    assert "App Funcionario" in sidebar
    assert "Smartphone" in sidebar
    assert "Venda pelo app do funcionario" in sidebar
