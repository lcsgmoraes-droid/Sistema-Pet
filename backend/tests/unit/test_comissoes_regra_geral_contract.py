from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"


def _backend_source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def _frontend_source(relative_path: str) -> str:
    return (FRONTEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_backend_comissoes_aceita_regra_geral_e_usa_como_fallback():
    routes = _backend_source("app/comissoes_routes.py")
    service = _backend_source("app/comissoes_service.py")
    models = _backend_source("app/comissoes_models.py")

    assert "'geral'" in routes
    assert "Regra geral" in routes
    assert "referencia_id = 0" in routes
    assert "cc.tipo = 'geral'" in routes
    assert "tipo = 'geral'" in service
    assert "Config encontrada: REGRA GERAL" in service
    assert "Produto > Subcategoria > Categoria > Regra geral" in models
    assert "AND tipo = 'geral'" in models


def test_frontend_comissoes_exibe_opcao_de_regra_geral():
    page = _frontend_source("src/pages/Comissoes.jsx")

    assert "Regra geral" in page
    assert "Todos os produtos e categorias" in page
    assert "selecionarItem('geral', 0, 'Regra geral')" in page
    assert "temConfiguracao('geral', 0)" in page
    assert "Produto > Subcategoria > Categoria > Regra geral" in page


def test_frontend_comissoes_salva_dia_fechamento_em_pessoa_parceira():
    page = _frontend_source("src/pages/Comissoes.jsx")

    assert "api.put(`/clientes/${funcionarioSel}`" in page
    assert "api.put(`/funcionarios/${funcionarioSel}`" not in page


def test_backend_listagem_comissoes_mostra_todo_parceiro_ativo():
    routes = _backend_source("app/comissoes_routes.py")

    assert "WHERE c.parceiro_ativo = true" in routes
    assert "c.tipo_cadastro IN ('funcionario', 'veterinario', 'outro')" not in routes


def test_frontend_comissoes_nomeia_fluxo_como_parceiros():
    page = _frontend_source("src/pages/Comissoes.jsx")

    assert "Gerencie as comissões dos parceiros" in page
    assert "Lista de Parceiros" in page
    assert "Selecione um parceiro" in page
    assert "Digite o ID do parceiro de destino:" in page
    assert "Duplicar configuração para outro parceiro" in page
    assert "Gerencie as comissões dos funcionários" not in page
    assert "Lista de Funcionários" not in page
    assert "Digite o ID do funcionário de destino:" not in page
    assert "Duplicar configuração para outro funcionário" not in page
