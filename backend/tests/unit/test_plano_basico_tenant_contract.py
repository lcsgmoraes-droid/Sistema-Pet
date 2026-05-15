import inspect
import os
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


def _depends_on_selected_tenant(func) -> bool:
    default = inspect.signature(func).parameters["user_and_tenant"].default
    return getattr(default, "dependency", None) is get_current_user_and_tenant


def test_basic_plan_route_files_use_selected_tenant_dependency():
    route_files = [
        "backend/app/clientes_routes.py",
        "backend/app/pets_routes.py",
        "backend/app/produtos_routes.py",
        "backend/app/vendas_routes.py",
        "backend/app/financeiro_routes.py",
        "backend/app/formas_pagamento_routes.py",
        "backend/app/usuarios_routes.py",
        "backend/app/categorias_routes.py",
        "backend/app/cadastros_routes.py",
        "backend/app/chat_routes.py",
        "backend/app/opcoes_racao_routes.py",
        "backend/app/calculadora_racao.py",
        "backend/app/api/racao_calculadora_routes.py",
    ]

    offenders = [
        path
        for path in route_files
        if "Depends(get_current_user)" in _source(path)
    ]

    assert offenders == []


def test_racao_calculadora_uses_tenant_selected_in_token():
    assert _depends_on_selected_tenant(racao_calculadora_routes.calcular_consumo_racao)

    source = inspect.getsource(racao_calculadora_routes.calcular_consumo_racao)
    assert "current_user.tenant_id" not in source
    assert "current_user, tenant_id = user_and_tenant" in source


def test_racao_calculadora_info_also_requires_selected_tenant():
    default = inspect.signature(racao_calculadora_routes.info_calculadora).parameters[
        "_user_and_tenant"
    ].default

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


def test_modulos_status_uses_selected_tenant_not_user_home_tenant():
    user = SimpleNamespace(id=1, tenant_id="tenant-antigo")

    response = modulos_routes.get_modulos_status(
        user_and_tenant=(user, "tenant-selecionado"),
        db=_FakeDb(),
    )

    assert response["tenant_id"] == "tenant-selecionado"
    assert response["plano"] == "basico"
    assert response["modulos_ativos"] == ["campanhas"]


def test_premium_routers_remain_gated_in_main():
    main_source = _source("backend/app/main.py")
    required_gates = {
        "campaigns_router": "campanhas",
        "canal_descontos_router": "campanhas",
        "veterinario_router": "veterinario",
        "banho_tosa_router": "banho_tosa",
        "bling_sync_router": "bling",
        "nfe_router": "fiscal",
        "simples_router": "financeiro_erp",
        "auditoria_provisoes_router": "financeiro_erp",
        "funcionarios_router": "rh",
    }

    for router_name, modulo in required_gates.items():
        assert router_name in main_source
        assert f'dependencies=_module_dependencies("{modulo}")' in main_source


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

    assert (
        '@router.get("/calculadora-racao/opcoes", response_model=RacoesCalculadoraOptionsResponse)\n'
        '@require_permission("produtos.visualizar")'
    ) in calculadora_source
    assert (
        '@router.post("/calculadora-racao", response_model=ResultadoCalculoRacao)\n'
        '@require_permission("produtos.visualizar")'
    ) in calculadora_source
    assert (
        '@router.post("/comparar-racoes", response_model=ComparativoRacoesResponse)\n'
        '@require_permission("produtos.visualizar")'
    ) in calculadora_source
    assert '@require_permission("produtos.visualizar")\nasync def calcular_consumo_racao' in internal_source


def test_product_auxiliary_catalog_routes_require_product_permissions():
    produtos_source = _source("backend/app/produtos_routes.py")

    protected_routes = [
        '@router.post("/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)\n@require_permission("produtos.criar")',
        '@router.get("/categorias", response_model=List[CategoriaResponse])\n@require_permission("produtos.visualizar")',
        '@router.get("/categorias/hierarquia", response_model=List[dict])\n@require_permission("produtos.visualizar")',
        '@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)\n@require_permission("produtos.visualizar")',
        '@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)\n@require_permission("produtos.editar")',
        '@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)\n@require_permission("produtos.editar")',
        '@router.post("/marcas", response_model=MarcaResponse, status_code=status.HTTP_201_CREATED)\n@require_permission("produtos.criar")',
        '@router.get("/marcas", response_model=List[MarcaResponse])\n@require_permission("produtos.visualizar")',
        '@router.get("/marcas/{marca_id}", response_model=MarcaResponse)\n@require_permission("produtos.visualizar")',
        '@router.put("/marcas/{marca_id}", response_model=MarcaResponse)\n@require_permission("produtos.editar")',
        '@router.delete("/marcas/{marca_id}", status_code=status.HTTP_204_NO_CONTENT)\n@require_permission("produtos.editar")',
        '@router.post("/departamentos", response_model=DepartamentoResponse, status_code=status.HTTP_201_CREATED)\n@require_permission("produtos.criar")',
        '@router.get("/departamentos", response_model=List[DepartamentoResponse])\n@require_permission("produtos.visualizar")',
        '@router.get("/departamentos/{departamento_id}", response_model=DepartamentoResponse)\n@require_permission("produtos.visualizar")',
        '@router.put("/departamentos/{departamento_id}", response_model=DepartamentoResponse)\n@require_permission("produtos.editar")',
        '@router.delete("/departamentos/{departamento_id}", status_code=status.HTTP_204_NO_CONTENT)\n@require_permission("produtos.editar")',
    ]

    for route in protected_routes:
        assert route in produtos_source


def test_pet_quick_add_blocks_race_without_selected_species():
    pet_form_source = _source("frontend/src/pages/PetForm.jsx")
    quick_add_source = _source("frontend/src/components/QuickAddModal.jsx")

    assert "Escolha uma especie antes de cadastrar uma raca" in pet_form_source
    assert "raca: ''" in pet_form_source
    assert "Selecione uma especie antes de cadastrar a raca" in quick_add_source
    assert "especie_id: especieIdNormalizado" in quick_add_source


def test_payment_and_operator_catalog_routes_require_sales_or_config_permissions():
    financeiro_source = _source("backend/app/financeiro_routes.py")
    operadoras_source = _source("backend/app/operadoras_routes.py")
    taxas_source = _source("backend/app/formas_pagamento_routes.py")

    financeiro_routes = [
        '@router.get("/formas-pagamento", response_model=List[FormaPagamentoResponse])\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
        '@router.post("/formas-pagamento", response_model=FormaPagamentoResponse, status_code=status.HTTP_201_CREATED)\n@require_permission("configuracoes.editar")',
        '@router.put("/formas-pagamento/{forma_id}", response_model=FormaPagamentoResponse)\n@require_permission("configuracoes.editar")',
        '@router.delete("/formas-pagamento/{forma_id}", status_code=status.HTTP_204_NO_CONTENT)\n@require_permission("configuracoes.editar")',
    ]

    operadoras_routes = [
        '@router.get("", response_model=List[OperadoraCartaoResponse])\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
        '@router.get("/padrao", response_model=OperadoraCartaoResponse)\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
        '@router.get("/{operadora_id}", response_model=OperadoraCartaoResponse)\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
        '@router.post("", response_model=OperadoraCartaoResponse, status_code=status.HTTP_201_CREATED)\n@require_permission("configuracoes.editar")',
        '@router.put("/{operadora_id}", response_model=OperadoraCartaoResponse)\n@require_permission("configuracoes.editar")',
        '@router.delete("/{operadora_id}", status_code=status.HTTP_204_NO_CONTENT)\n@require_permission("configuracoes.editar")',
    ]

    taxas_routes = [
        '@router.post("/taxas", response_model=FormaPagamentoTaxaResponse)\n@require_permission("configuracoes.editar")',
        '@router.get("/taxas/{forma_pagamento_id}", response_model=List[FormaPagamentoTaxaResponse])\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
        '@router.put("/taxas/{taxa_id}", response_model=FormaPagamentoTaxaResponse)\n@require_permission("configuracoes.editar")',
        '@router.delete("/taxas/{taxa_id}")\n@require_permission("configuracoes.editar")',
        '@router.post("/analisar-venda", response_model=AnaliseVendaResponse)\n@require_any_permission(("vendas.criar", "configuracoes.editar"))',
    ]

    for route in financeiro_routes:
        assert route in financeiro_source

    for route in operadoras_routes:
        assert route in operadoras_source

    for route in taxas_routes:
        assert route in taxas_source

    assert "FormaPagamento.tenant_id == tenant_id" in taxas_source
    assert "FormaPagamentoTaxa.tenant_id == tenant_id" in taxas_source
    assert "ConfiguracaoImposto.tenant_id == tenant_id" in taxas_source


def test_company_configuration_routes_require_configuration_permissions():
    empresa_fiscal_source = _source("backend/app/api/v1/empresa_fiscal.py")
    empresa_routes_source = _source("backend/app/empresa_routes.py")
    empresa_config_source = _source("backend/app/empresa_config_routes.py")
    app_source = _source("frontend/src/App.jsx")
    configuracoes_source = _source("frontend/src/pages/Configuracoes.jsx")

    assert empresa_fiscal_source.count(
        '@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))'
    ) >= 4
    assert empresa_routes_source.count(
        '@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))'
    ) >= 4
    assert empresa_routes_source.count('@require_permission("configuracoes.editar")') >= 2
    assert empresa_config_source.count('@require_permission("configuracoes.editar")') >= 4

    assert 'anyOfPermissions={["configuracoes.empresa", "configuracoes.editar"]}' in app_source
    assert '<ProtectedRoute permission="configuracoes.editar">' in app_source
    assert 'path="admin/roles"' in app_source
    assert 'permission="usuarios.manage"' in app_source
    assert 'card.modulo && !moduloAtivo(card.modulo)' in configuracoes_source


def test_product_departments_are_basic_catalog_not_rh_module():
    app_source = _source("frontend/src/App.jsx")
    layout_source = _source("frontend/src/components/Layout.jsx")

    assert 'path="cadastros/departamentos" element={<Departamentos />}' in app_source
    departamentos_menu_start = layout_source.index('path: "/cadastros/departamentos"')
    departamentos_menu_end = layout_source.index('path: "/cadastros/categorias"', departamentos_menu_start)
    departamentos_menu = layout_source[departamentos_menu_start:departamentos_menu_end]

    assert 'modulo: "rh"' not in departamentos_menu
    assert 'permission: "cadastros.categorias_produtos"' in departamentos_menu
