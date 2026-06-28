from pathlib import Path
import importlib
import os


os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]

TARGET_FILES = [
    "app/ia/aba6_chat_ia.py",
    "app/vendas/pos_processamento.py",
    "app/models.py",
    "app/campaigns/loyalty_service.py",
    "app/conciliacao_models.py",
    "app/comissoes_service.py",
    "app/routes/app_mobile_routes.py",
]

EXTRACTED_MODULES = [
    "app.ia.aba6_chat_ia_parts",
    "app.ia.aba6_chat_ia_parts.base",
    "app.ia.aba6_chat_ia_parts.contexto",
    "app.ia.aba6_chat_ia_parts.conversas",
    "app.ia.aba6_chat_ia_parts.mensagens",
    "app.ia.aba6_chat_ia_parts.metricas",
    "app.ia.aba6_chat_ia_parts.periodos",
    "app.ia.aba6_chat_ia_parts.respostas",
    "app.ia.aba6_chat_ia_parts.service",
    "app.ia.aba6_resposta_simples",
    "app.vendas.dre_pos_processamento",
    "app.models_authz",
    "app.models_operacionais",
    "app.campaigns.loyalty_rewards",
    "app.conciliacao_recebimento_models",
    "app.comissoes_config_service",
    "app.comissoes_geracao_service",
    "app.routes.app_mobile_rastreio_routes",
]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_backend_nao_tem_mais_arquivos_de_aplicacao_acima_de_1000_linhas():
    oversized = {}
    for path in (BACKEND_ROOT / "app").rglob("*.py"):
        relative = path.relative_to(BACKEND_ROOT).as_posix()
        if "__pycache__" in relative:
            continue
        line_count = _line_count(path)
        if line_count > 1000:
            oversized[relative] = line_count

    assert oversized == {}


def test_arquivos_backend_restantes_saem_da_faixa_acima_de_1000_linhas():
    oversized = {
        relative: _line_count(BACKEND_ROOT / relative)
        for relative in TARGET_FILES
        if _line_count(BACKEND_ROOT / relative) > 1000
    }

    assert oversized == {}


def test_modulos_extraidos_da_fatia_zero_backend_existentes():
    for module_name in EXTRACTED_MODULES:
        importlib.import_module(module_name)


def test_fachadas_publicas_preservam_funcoes_e_models_extraidos():
    from app import comissoes_config_service, comissoes_service
    from app import conciliacao_models, conciliacao_recebimento_models
    from app import models, models_operacionais
    from app.campaigns import loyalty_rewards, loyalty_service
    from app.vendas import dre_pos_processamento, pos_processamento

    assert (
        pos_processamento.gerar_dre_competencia_venda
        is dre_pos_processamento.gerar_dre_competencia_venda
    )
    assert (
        comissoes_service.buscar_configuracao_comissao
        is comissoes_config_service.buscar_configuracao_comissao
    )
    assert loyalty_service._give_loyalty_reward is loyalty_rewards._give_loyalty_reward
    assert models.FeatureFlag is models_operacionais.FeatureFlag
    assert (
        conciliacao_models.ConciliacaoRecebimento
        is conciliacao_recebimento_models.ConciliacaoRecebimento
    )


def test_app_mobile_inclui_subrouter_de_rastreio_extraido():
    from app.routes import app_mobile_routes

    route_signatures = {
        (route.path, tuple(sorted(route.methods)))
        for route in app_mobile_routes.router.routes
        if hasattr(route, "methods")
    }

    assert ("/app/pedidos/{pedido_id}/rastreio", ("GET",)) in route_signatures
