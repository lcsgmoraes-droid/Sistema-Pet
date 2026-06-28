import inspect
import os
import re
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"

from app.api import racao_calculadora_routes
from app.auth.dependencies import get_current_user_and_tenant
from app.models import AssinaturaModulo, Tenant
from app.routes import modulos_routes


ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _frontend_route_source(*filenames: str) -> str:
    return "\n".join(_source(f"frontend/src/app/routes/{name}") for name in filenames)


def _assert_route_guarded_by_permission(
    source: str,
    path: str,
    component: str,
    permission: str,
) -> None:
    pattern = (
        rf'path="{re.escape(path)}"[\s\S]*?'
        rf'<ProtectedRoute permission="{re.escape(permission)}">[\s\S]*?'
        rf"<{re.escape(component)}\s*/>"
    )
    assert re.search(pattern, source)


def _depends_on_selected_tenant(func) -> bool:
    default = inspect.signature(func).parameters["user_and_tenant"].default
    return getattr(default, "dependency", None) is get_current_user_and_tenant


def test_basic_plan_route_files_use_selected_tenant_dependency():
    route_files = [
        "backend/app/clientes_routes.py",
        "backend/app/pets_routes.py",
        "backend/app/produtos_routes.py",
        "backend/app/produtos/atualizacao_lote_routes.py",
        "backend/app/produtos/cadastro_routes.py",
        "backend/app/produtos/codigo_sku_routes.py",
        "backend/app/produtos/estado_routes.py",
        "backend/app/produtos/listagem_routes.py",
        "backend/app/produtos/variacoes_fusao_routes.py",
        "backend/app/vendas_routes.py",
        "backend/app/vendas/cancelamento_routes.py",
        "backend/app/vendas/crud_routes.py",
        "backend/app/vendas/entrega_routes.py",
        "backend/app/vendas/finalizacao_routes.py",
        "backend/app/vendas/relatorios_routes.py",
        "backend/app/vendas/status_routes.py",
        "backend/app/financeiro_routes.py",
        "backend/app/financeiro/cliente_routes.py",
        "backend/app/financeiro/config_routes.py",
        "backend/app/financeiro/fluxo_caixa_routes.py",
        "backend/app/formas_pagamento_routes.py",
        "backend/app/usuarios_routes.py",
        "backend/app/categorias_routes.py",
        "backend/app/cadastros_routes.py",
        "backend/app/lembretes.py",
        "backend/app/chat_routes.py",
        "backend/app/opcoes_racao_routes.py",
        "backend/app/calculadora_racao.py",
        "backend/app/api/racao_calculadora_routes.py",
    ]

    offenders = [
        path for path in route_files if "Depends(get_current_user)" in _source(path)
    ]

    assert offenders == []


def test_config_estoque_expoe_parametros_de_validade():
    source = _source("backend/app/empresa_routes.py")

    assert "protecao_validade_ativa" in source
    assert "dias_alerta_validade" in source
    assert "bloquear_validade_pdv" in source
    assert "bloquear_validade_ecommerce" in source
    assert "bloquear_validade_integracoes_online" in source


def test_ecommerce_consulta_saldo_vendavel_oficial_do_produto():
    cart_source = _source("backend/app/routes/ecommerce_cart.py")
    public_source = _source("backend/app/routes/ecommerce_public.py")

    assert "produto.estoque_atual" in cart_source
    assert "Produto.estoque_atual" in public_source
    assert "quantidade_disponivel" not in cart_source


def test_racao_calculadora_uses_tenant_selected_in_token():
    assert _depends_on_selected_tenant(racao_calculadora_routes.calcular_consumo_racao)

    source = inspect.getsource(racao_calculadora_routes.calcular_consumo_racao)
    assert "current_user.tenant_id" not in source
    assert "current_user, tenant_id = user_and_tenant" in source


def test_racao_calculadora_info_also_requires_selected_tenant():
    default = (
        inspect.signature(racao_calculadora_routes.info_calculadora)
        .parameters["_user_and_tenant"]
        .default
    )

    assert getattr(default, "dependency", None) is get_current_user_and_tenant


class _FakeQuery:
    def __init__(self, model):
        self.model = model

    def filter(self, *criteria):
        self.criteria = criteria
        return self

    def first(self):
        if self.model is Tenant:
            return SimpleNamespace(
                id="tenant-selecionado",
                plan="basico",
                modulos_ativos='["campanhas"]',
            )
        return None

    def all(self):
        if self.model is AssinaturaModulo:
            return []
        return []


class _FakeDb:
    def query(self, model):
        return _FakeQuery(model)


TENANT_ALVO_MODULO = "11111111-1111-1111-1111-111111111111"


class _FakeAdminModuleQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *criteria):
        self.criteria = criteria
        return self

    def first(self):
        if self.model is Tenant:
            return self.db.tenant
        if self.model is AssinaturaModulo:
            return None
        return None


class _FakeAdminModuleDb:
    def __init__(self):
        self.tenant = SimpleNamespace(
            id=TENANT_ALVO_MODULO,
            plan="basico",
            modulos_ativos="[]",
        )
        self.added = []
        self.committed = False

    def query(self, model):
        return _FakeAdminModuleQuery(self, model)

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.committed = True


def test_modulos_status_uses_selected_tenant_not_user_home_tenant():
    user = SimpleNamespace(id=1, tenant_id="tenant-antigo")

    response = modulos_routes.get_modulos_status(
        user_and_tenant=(user, "tenant-selecionado"),
        db=_FakeDb(),
    )

    assert response["tenant_id"] == "tenant-selecionado"
    assert response["plano"] == "basico"
    assert response["modulos_ativos"] == ["campanhas"]
    assert "bling" in response["modulos_fora_oferta_publica"]
    assert "bling" not in response["modulos_beta"]
    assert response["trial_padrao"]["escopo"] == "basico_completo"
    assert response["trial_padrao"]["libera_premium_automaticamente"] is False
    assert response["assinatura"]["pagamento_integrado"] is False
    assert response["assinatura"]["contratacao"]["modelo"] == "manual_assistida"


def test_modulos_admin_activation_sets_target_tenant_context(monkeypatch):
    tenant_context_calls = []
    monkeypatch.setattr(
        modulos_routes,
        "set_current_tenant",
        lambda tenant_id: tenant_context_calls.append(str(tenant_id)),
        raising=False,
    )
    monkeypatch.setattr(
        modulos_routes, "get_current_tenant", lambda: None, raising=False
    )
    monkeypatch.setattr(
        modulos_routes,
        "clear_current_tenant",
        lambda: tenant_context_calls.append("cleared"),
        raising=False,
    )
    monkeypatch.setattr(modulos_routes, "log_business_event", lambda **_kwargs: None)

    db = _FakeAdminModuleDb()
    current_user = SimpleNamespace(id=7, is_superadmin=True, is_system_admin=False)

    response = modulos_routes.ativar_modulo(
        "campanhas",
        TENANT_ALVO_MODULO,
        current_user=current_user,
        db=db,
    )

    assert response == {
        "ok": True,
        "modulo": "campanhas",
        "tenant_id": TENANT_ALVO_MODULO,
    }
    assert tenant_context_calls == [TENANT_ALVO_MODULO]
    assert db.added[0].tenant_id == TENANT_ALVO_MODULO
    assert db.committed is True


def test_premium_routers_remain_gated_in_router_bootstrap():
    main_source = _source("backend/app/main_routers.py")
    required_gates = {
        "campaigns_router": "campanhas",
        "canal_descontos_router": "campanhas",
        "sefaz_router": "compras",
        "veterinario_router": "veterinario",
        "banho_tosa_router": "banho_tosa",
        "bling_sync_router": "bling",
        "nfe_router": "fiscal",
        "simples_router": "financeiro_erp",
        "auditoria_provisoes_router": "financeiro_erp",
        "contas_receber_router": "financeiro_erp",
        "chat_router": "financeiro_erp",
        "funcionarios_router": "rh",
    }

    for router_name, modulo in required_gates.items():
        pattern = (
            rf"app\.include_router\(\s*{router_name}\b"
            rf"[\s\S]*?dependencies=_module_dependencies\(\"{modulo}\"\)"
        )
        assert re.search(pattern, main_source), f"{router_name} sem gate {modulo}"


def test_rbac_admin_routes_require_user_management_permission():
    roles_source = _source("backend/app/roles_routes.py")
    permissions_source = _source("backend/app/permissions_routes.py")

    protected_role_routes = [
        '@router.get("", response_model=list[dict])\n@require_permission("usuarios.manage")',
        '@router.post("", response_model=dict)\n@require_permission("usuarios.manage")',
        '@router.put("/{role_id}", response_model=dict)\n@require_permission("usuarios.manage")',
        '@router.delete("/{role_id}", status_code=204)\n@require_permission("usuarios.manage")',
    ]

    for route in protected_role_routes:
        assert route in roles_source

    assert (
        '@router.get("/permissions", response_model=List[PermissionResponse])\n'
        '@require_permission("usuarios.manage")'
    ) in permissions_source


def test_racao_catalog_and_calculator_routes_require_product_permissions():
    opcoes_source = _source("backend/app/opcoes_racao_routes.py")
    calculadora_source = _source("backend/app/calculadora_racao.py")
    internal_source = _source("backend/app/api/racao_calculadora_routes.py")

    assert opcoes_source.count('@require_permission("produtos.visualizar")') >= 6
    assert opcoes_source.count('@require_permission("produtos.criar")') >= 6
    assert opcoes_source.count('@require_permission("produtos.editar")') >= 12

    for method, path, response_model in [
        ("get", "/calculadora-racao/opcoes", "RacoesCalculadoraOptionsResponse"),
        ("post", "/calculadora-racao", "ResultadoCalculoRacao"),
        ("post", "/comparar-racoes", "ComparativoRacoesResponse"),
    ]:
        pattern = (
            rf'@router\.{method}\(\s*"{re.escape(path)}"'
            rf"[\s\S]*?response_model={response_model}[\s\S]*?\)\s*"
            r'@require_permission\("produtos\.visualizar"\)'
        )
        assert re.search(pattern, calculadora_source)

    assert (
        '@require_permission("produtos.visualizar")\nasync def calcular_consumo_racao'
        in internal_source
    )


def test_product_auxiliary_catalog_routes_require_product_permissions():
    catalogos_source = _source("backend/app/produtos/catalogos_routes.py")

    protected_routes = [
        ("post", "/categorias", "produtos.criar"),
        ("get", "/categorias", "produtos.visualizar"),
        ("get", "/categorias/hierarquia", "produtos.visualizar"),
        ("get", "/categorias/{categoria_id}", "produtos.visualizar"),
        ("put", "/categorias/{categoria_id}", "produtos.editar"),
        ("delete", "/categorias/{categoria_id}", "produtos.editar"),
        ("post", "/marcas", "produtos.criar"),
        ("get", "/marcas", "produtos.visualizar"),
        ("get", "/marcas/{marca_id}", "produtos.visualizar"),
        ("put", "/marcas/{marca_id}", "produtos.editar"),
        ("delete", "/marcas/{marca_id}", "produtos.editar"),
        ("post", "/departamentos", "produtos.criar"),
        ("get", "/departamentos", "produtos.visualizar"),
        ("get", "/departamentos/{departamento_id}", "produtos.visualizar"),
        ("put", "/departamentos/{departamento_id}", "produtos.editar"),
        ("delete", "/departamentos/{departamento_id}", "produtos.editar"),
    ]

    for method, path, permission in protected_routes:
        pattern = (
            rf'@router\.{method}\(\s*"{re.escape(path)}"[\s\S]*?\)\s*'
            rf'@require_permission\("{permission}"\)'
        )
        assert re.search(pattern, catalogos_source)


def test_pet_quick_add_blocks_race_without_selected_species():
    pet_form_source = _source("frontend/src/pages/PetForm.jsx")
    quick_add_source = _source("frontend/src/components/QuickAddModal.jsx")

    assert "Escolha uma especie antes de cadastrar uma raca" in pet_form_source
    assert 'raca: ""' in pet_form_source
    assert "Selecione uma especie antes de cadastrar a raca" in quick_add_source
    assert "especie_id: especieIdNormalizado" in quick_add_source


def test_payment_and_operator_catalog_routes_require_sales_or_config_permissions():
    financeiro_source = _source("backend/app/financeiro/config_routes.py")
    operadoras_source = _source("backend/app/operadoras_routes.py")
    taxas_source = _source("backend/app/formas_pagamento_routes.py")

    def assert_route_requires(
        source: str, method: str, path: str, permission_pattern: str
    ) -> None:
        pattern = (
            rf'@router\.{method}\(\s*"{re.escape(path)}"[\s\S]*?\)\s*'
            rf"{permission_pattern}"
        )
        assert re.search(pattern, source)

    financeiro_routes = [
        (
            "get",
            "/formas-pagamento",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
        (
            "post",
            "/formas-pagamento",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "put",
            "/formas-pagamento/{forma_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "delete",
            "/formas-pagamento/{forma_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
    ]

    operadoras_routes = [
        (
            "get",
            "",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
        (
            "get",
            "/padrao",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
        (
            "get",
            "/{operadora_id}",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
        (
            "post",
            "",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "put",
            "/{operadora_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "delete",
            "/{operadora_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
    ]

    taxas_routes = [
        (
            "post",
            "/taxas",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "get",
            "/taxas/{forma_pagamento_id}",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
        (
            "put",
            "/taxas/{taxa_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "delete",
            "/taxas/{taxa_id}",
            r'@require_permission\("configuracoes\.editar"\)',
        ),
        (
            "post",
            "/analisar-venda",
            r'@require_any_permission\(\("vendas\.criar", "configuracoes\.editar"\)\)',
        ),
    ]

    for method, path, permission_pattern in financeiro_routes:
        assert_route_requires(financeiro_source, method, path, permission_pattern)

    for method, path, permission_pattern in operadoras_routes:
        assert_route_requires(operadoras_source, method, path, permission_pattern)

    for method, path, permission_pattern in taxas_routes:
        assert_route_requires(taxas_source, method, path, permission_pattern)

    assert "FormaPagamento.tenant_id == tenant_id" in taxas_source
    assert "FormaPagamentoTaxa.tenant_id == tenant_id" in taxas_source
    assert "ConfiguracaoImposto.tenant_id == tenant_id" in taxas_source


def test_company_configuration_routes_require_configuration_permissions():
    empresa_fiscal_source = _source("backend/app/api/v1/empresa_fiscal.py")
    empresa_routes_source = _source("backend/app/empresa_routes.py")
    empresa_config_source = _source("backend/app/empresa_config_routes.py")
    empresa_config_geral_migration = _source(
        "backend/alembic/versions/or20260515a9_create_empresa_config_geral.py"
    )
    settings_routes_source = _frontend_route_source("SettingsAdminRoutes.jsx")
    configuracoes_source = _source("frontend/src/pages/Configuracoes.jsx")

    assert (
        empresa_fiscal_source.count(
            '@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))'
        )
        >= 4
    )
    assert (
        empresa_routes_source.count(
            '@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))'
        )
        >= 4
    )
    assert (
        empresa_routes_source.count('@require_permission("configuracoes.editar")') >= 2
    )
    assert (
        "def _buscar_tenant_por_contexto(db: Session, tenant_id)"
        in empresa_routes_source
    )
    assert "Tenant.id == str(tenant_id)" in empresa_routes_source
    assert "Tenant.id == tenant_id" not in empresa_routes_source
    assert (
        empresa_config_source.count('@require_permission("configuracoes.editar")') >= 4
    )
    assert (
        'op.create_table(\n            "empresa_config_geral"'
        in empresa_config_geral_migration
    )
    assert "ix_empresa_config_geral_tenant_id" in empresa_config_geral_migration

    assert (
        'anyOfPermissions={["configuracoes.empresa", "configuracoes.editar"]}'
        in settings_routes_source
    )
    assert (
        '<ProtectedRoute permission="configuracoes.editar">' in settings_routes_source
    )
    assert 'path="admin/roles"' in settings_routes_source
    assert 'permission="usuarios.manage"' in settings_routes_source
    assert "card.modulo && !moduloAtivo(card.modulo)" in configuracoes_source


def test_protected_route_enforces_any_of_permissions():
    protected_route_source = _source("frontend/src/components/ProtectedRoute.jsx")

    assert (
        "permission || requiredPermissions || anyOfPermissions"
        in protected_route_source
    )


def test_basic_finance_sales_menu_matches_direct_route_permissions():
    layout_source = _source("frontend/src/components/Layout.jsx") + _source(
        "frontend/src/components/layout/menuConfig.js"
    )
    finance_routes_source = _frontend_route_source("FinanceRoutes.jsx")

    assert "const itemLiberadoPorPermissao = (item) => {" in layout_source
    assert (
        "if (item.anyOfPermissions) return hasAnyPermission(item.anyOfPermissions);"
        in layout_source
    )

    finance_menu_start = layout_source.index('path: "/financeiro"')
    finance_sales_start = layout_source.index(
        'path: "/financeiro/vendas"', finance_menu_start
    )
    finance_sales_end = layout_source.index(
        'path: "/financeiro/fluxo-caixa"', finance_sales_start
    )
    finance_sales_menu = layout_source[finance_sales_start:finance_sales_end]

    for permission in [
        "relatorios.financeiro",
        "financeiro.vendas",
        "clientes.visualizar",
        "vendas.criar",
    ]:
        assert f'"{permission}"' in finance_sales_menu

    finance_sales_route_start = finance_routes_source.index('path="financeiro/vendas"')
    finance_sales_route_end = finance_routes_source.index(
        "<VendasFinanceiro />", finance_sales_route_start
    )
    finance_sales_route = finance_routes_source[
        finance_sales_route_start:finance_sales_route_end
    ]

    for permission in [
        "relatorios.financeiro",
        "financeiro.vendas",
        "clientes.visualizar",
        "vendas.criar",
    ]:
        assert f'"{permission}"' in finance_sales_route


def test_financeiro_mixed_router_keeps_premium_endpoints_module_gated():
    financeiro_common_source = _source("backend/app/financeiro/common.py")
    financeiro_config_source = _source("backend/app/financeiro/config_routes.py")
    fluxo_caixa_source = _source("backend/app/financeiro/fluxo_caixa_routes.py")
    cliente_source = _source("backend/app/financeiro/cliente_routes.py")

    assert (
        'financeiro_erp_required = Depends(require_active_module("financeiro_erp"))'
        in financeiro_common_source
    )

    premium_functions = {
        "def listar_categorias(",
        "def criar_categoria(",
        "def atualizar_categoria(",
        "def desativar_categoria(",
    }

    for function_name in premium_functions:
        start = financeiro_config_source.index(function_name)
        end = financeiro_config_source.index("):", start)
        signature = financeiro_config_source[start:end]
        assert "_module_access: None = financeiro_erp_required" in signature

    fluxo_start = fluxo_caixa_source.index("def get_fluxo_caixa(")
    fluxo_end = fluxo_caixa_source.index("):", fluxo_start)
    fluxo_signature = fluxo_caixa_source[fluxo_start:fluxo_end]
    assert "_module_access: None = financeiro_erp_required" in fluxo_signature

    cliente_history_start = cliente_source.index(
        "def get_historico_financeiro_cliente("
    )
    cliente_history_end = cliente_source.index("):", cliente_history_start)
    cliente_history_signature = cliente_source[
        cliente_history_start:cliente_history_end
    ]
    assert (
        "_module_access: None = financeiro_erp_required"
        not in cliente_history_signature
    )


def test_cliente_financeiro_remains_basic_but_tenant_scoped():
    core_routes_source = _frontend_route_source("CoreProtectedRoutes.jsx")
    financeiro_source = _source("backend/app/financeiro/cliente_routes.py")

    _assert_route_guarded_by_permission(
        core_routes_source,
        "clientes/:clienteId/financeiro",
        "ClienteFinanceiro",
        "clientes.visualizar",
    )

    for function_name in [
        "def get_historico_financeiro_cliente(",
        "def get_resumo_financeiro_cliente(",
    ]:
        start = financeiro_source.index(function_name)
        end = financeiro_source.index("):", start)
        signature = financeiro_source[start:end]
        assert "_module_access: None = financeiro_erp_required" not in signature

    required_tenant_filters = [
        "Cliente.tenant_id == tenant_id",
        "Venda.tenant_id == tenant_id",
        "ContaReceber.tenant_id == tenant_id",
    ]

    for tenant_filter in required_tenant_filters:
        assert tenant_filter in financeiro_source


def test_rh_simulation_page_is_module_gated_on_direct_url():
    settings_routes_source = _frontend_route_source("SettingsAdminRoutes.jsx")

    assert 'path="simulacao-contratacao"' in settings_routes_source
    assert (
        re.search(
            r'path="simulacao-contratacao"[\s\S]*?'
            r'<ModuleGate modulo="rh">[\s\S]*?<SimulacaoContratacao\s*/>',
            settings_routes_source,
        )
        is not None
    )


def test_basic_direct_urls_apply_same_frontend_permissions_as_menu():
    core_routes_source = _frontend_route_source("CoreProtectedRoutes.jsx")
    product_routes_source = _frontend_route_source("ProductInventoryRoutes.jsx")
    catalog_routes_source = _frontend_route_source("CatalogAdminRoutes.jsx")
    sales_routes_source = _frontend_route_source("SalesMarketingRoutes.jsx")
    layout_source = _source("frontend/src/components/Layout.jsx") + _source(
        "frontend/src/components/layout/menuConfig.js"
    )

    expected_route_guards = [
        (core_routes_source, "pets", "GerenciamentoPets", "clientes.visualizar"),
        (core_routes_source, "pets/novo", "PetForm", "clientes.visualizar"),
        (core_routes_source, "pets/:petId", "PetDetalhes", "clientes.visualizar"),
        (core_routes_source, "pets/:petId/editar", "PetForm", "clientes.visualizar"),
        (
            product_routes_source,
            "produtos/:id/movimentacoes",
            "MovimentacoesProduto",
            "produtos.visualizar",
        ),
        (
            product_routes_source,
            "produtos/relatorio",
            "ProdutosRelatorio",
            "produtos.visualizar",
        ),
        (
            product_routes_source,
            "calculadora-racao",
            "CalculadoraRacao",
            "produtos.visualizar",
        ),
        (sales_routes_source, "meus-caixas", "MeusCaixas", "vendas.criar"),
        (
            catalog_routes_source,
            "cadastros/departamentos",
            "Departamentos",
            "cadastros.categorias_produtos",
        ),
        (
            catalog_routes_source,
            "cadastros/marcas",
            "Marcas",
            "cadastros.categorias_produtos",
        ),
        (
            catalog_routes_source,
            "cadastros/categorias",
            "Categorias",
            "cadastros.categorias_produtos",
        ),
        (
            catalog_routes_source,
            "cadastros/tipos-despesa",
            "TipoDespesa",
            "cadastros.categorias_financeiras",
        ),
        (
            catalog_routes_source,
            "cadastros/especies-racas",
            "EspeciesRacas",
            "cadastros.especies_racas",
        ),
    ]

    for source, path, component, permission in expected_route_guards:
        _assert_route_guarded_by_permission(source, path, component, permission)

    calculadora_menu_start = layout_source.index('path: "/calculadora-racao"')
    calculadora_menu_end = layout_source.index('path: "/pdv"', calculadora_menu_start)
    calculadora_menu = layout_source[calculadora_menu_start:calculadora_menu_end]
    assert 'permission: "produtos.visualizar"' in calculadora_menu


def test_financial_chat_ia_is_not_available_in_basic_without_premium_module():
    main_source = _source("backend/app/main_routers.py")
    delivery_ai_routes_source = _frontend_route_source("DeliveryAiRoutes.jsx")
    layout_source = _source("frontend/src/components/Layout.jsx") + _source(
        "frontend/src/components/layout/menuConfig.js"
    )
    modulo_bloqueado_source = _source("frontend/src/components/ModuloBloqueado.jsx")

    assert re.search(
        r"app\.include_router\(\s*chat_router[\s\S]*?"
        r'dependencies=_module_dependencies\("financeiro_erp"\)',
        main_source,
    )
    assert 'path="ia/chat"' in delivery_ai_routes_source
    assert (
        re.search(
            r'path="ia/chat"[\s\S]*?'
            r'<ModuleGate modulo="financeiro_erp">[\s\S]*?<ChatIA\s*/>',
            delivery_ai_routes_source,
        )
        is not None
    )

    chat_menu_start = layout_source.index('path: "/ia/chat"')
    chat_menu_end = layout_source.index('path: "/ia/fluxo-caixa"', chat_menu_start)
    chat_menu = layout_source[chat_menu_start:chat_menu_end]
    assert 'modulo: "financeiro_erp"' in chat_menu

    loading_gate_start = modulo_bloqueado_source.index("if (modulosAtivos === null)")
    loading_gate_end = modulo_bloqueado_source.index(
        "if (moduloAtivo(modulo))", loading_gate_start
    )
    loading_gate = modulo_bloqueado_source[loading_gate_start:loading_gate_end]
    assert "return children" not in loading_gate


def test_lembretes_use_selected_tenant_context():
    lembretes_source = _source("backend/app/lembretes.py")

    assert "Depends(get_current_user)" not in lembretes_source
    assert "Lembrete.tenant_id == tenant_id" in lembretes_source
    assert "Lembrete.user_id == current_user.id" not in lembretes_source


def test_chat_ia_conversation_history_uses_selected_tenant_context():
    chat_routes_source = _source("backend/app/chat_routes.py")
    chat_service_source = _source("backend/app/ia/aba6_chat_ia.py")

    assert (
        "listar_conversas_service(db, usuario_id, tenant_id, limit)"
        in chat_routes_source
    )
    assert (
        "service.obter_conversa(conversa_id, usuario_id, tenant_id)"
        in chat_routes_source
    )
    assert "service.obter_historico(conversa_id, tenant_id)" in chat_routes_source
    assert (
        "deletar_conversa_service(db, conversa_id, usuario_id, tenant_id)"
        in chat_routes_source
    )

    assert re.search(
        r"def listar_conversas\(\s*self,\s*usuario_id: int,\s*"
        r"tenant_id: Optional\[str\]",
        chat_service_source,
    )
    assert "Conversa.tenant_id == tenant_id_resolvido" in chat_service_source
    assert "MensagemChat.tenant_id == str(tenant_id)" in chat_service_source


def test_ia_fluxo_caixa_uses_selected_tenant_context():
    ia_routes_source = _source("backend/app/ia_routes.py")
    fluxo_source = _source("backend/app/ia/aba5_fluxo_caixa.py")
    chat_service_source = _source("backend/app/ia/aba6_chat_ia.py")

    assert (
        "calcular_indices_saude(usuario_id, db, tenant_id=tenant_id)"
        in ia_routes_source
    )
    assert (
        "obter_projecoes_proximos_dias(usuario_id, dias, db, tenant_id=tenant_id)"
        in ia_routes_source
    )
    assert (
        "projetar_fluxo_15_dias(usuario_id, db, tenant_id=tenant_id)"
        in ia_routes_source
    )
    assert (
        "simular_cenario(usuario_id, request.cenario, db, tenant_id=tenant_id)"
        in ia_routes_source
    )
    assert (
        "gerar_alertas_caixa(usuario_id, db, tenant_id=tenant_id)" in ia_routes_source
    )
    assert "tenant_id=tenant_id" in ia_routes_source

    assert re.search(
        r"def _resolve_tenant_id\(\s*usuario_id: int,\s*db: Session,\s*"
        r"tenant_id: Optional\[str\] = None",
        fluxo_source,
    )
    assert "FluxoCaixa.tenant_id == tenant_id_resolvido" in fluxo_source
    assert "IndicesSaudeCaixa.tenant_id == tenant_id_resolvido" in fluxo_source
    assert "ProjecaoFluxoCaixa.tenant_id == tenant_id_resolvido" in fluxo_source
    assert "tenant_id=tenant_id_resolvido" in fluxo_source

    assert re.search(
        r"calcular_indices_saude\(\s*usuario_id,\s*self\.db,\s*"
        r"tenant_id=tenant_id_resolvido",
        chat_service_source,
    )
    assert "tenant_id=tenant_id_resolvido" in chat_service_source
    assert re.search(
        r"gerar_alertas_caixa\(\s*usuario_id,\s*self\.db,\s*"
        r"tenant_id=tenant_id_resolvido",
        chat_service_source,
    )


def test_product_catalog_auxiliary_pages_are_basic_catalog_not_premium_modules():
    catalog_routes_source = _frontend_route_source("CatalogAdminRoutes.jsx")
    layout_source = _source("frontend/src/components/Layout.jsx") + _source(
        "frontend/src/components/layout/menuConfig.js"
    )

    _assert_route_guarded_by_permission(
        catalog_routes_source,
        "cadastros/departamentos",
        "Departamentos",
        "cadastros.categorias_produtos",
    )
    _assert_route_guarded_by_permission(
        catalog_routes_source,
        "cadastros/marcas",
        "Marcas",
        "cadastros.categorias_produtos",
    )
    _assert_route_guarded_by_permission(
        catalog_routes_source,
        "cadastros/categorias",
        "Categorias",
        "cadastros.categorias_produtos",
    )

    departamentos_menu_start = layout_source.index('path: "/cadastros/departamentos"')
    departamentos_menu_end = layout_source.index(
        'path: "/cadastros/marcas"', departamentos_menu_start
    )
    departamentos_menu = layout_source[departamentos_menu_start:departamentos_menu_end]
    marcas_menu_start = layout_source.index('path: "/cadastros/marcas"')
    marcas_menu_end = layout_source.index(
        'path: "/cadastros/categorias"', marcas_menu_start
    )
    marcas_menu = layout_source[marcas_menu_start:marcas_menu_end]

    assert 'modulo: "rh"' not in departamentos_menu
    assert "modulo:" not in marcas_menu
    assert 'permission: "cadastros.categorias_produtos"' in departamentos_menu
    assert 'permission: "cadastros.categorias_produtos"' in marcas_menu
