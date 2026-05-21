from pathlib import Path
import importlib
import importlib.util
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_contexto_movimentacoes_fica_em_modulo_dedicado():
    spec = importlib.util.find_spec("app.estoque_movimentacoes_context")

    assert spec is not None

    module = importlib.import_module("app.estoque_movimentacoes_context")

    for nome in [
        "_texto_limpo",
        "_label_canal_movimentacao",
        "_numero_nf_pedido_integrado",
        "_numero_pedido_loja_integrado",
        "_contexto_venda_pedido_integrado",
        "_observacao_exibicao_movimentacao_bling",
        "_detalhar_reservas_ativas_produto",
    ]:
        assert hasattr(module, nome)


def test_estoque_routes_nao_define_mais_helpers_de_contexto_movimentacoes():
    source = _source("app/estoque_routes.py")

    for nome in [
        "_texto_limpo",
        "_label_canal_movimentacao",
        "_resumo_nf_pedido_integrado",
        "_numero_nf_pedido_integrado",
        "_numero_pedido_loja_integrado",
        "_contexto_venda_pedido_integrado",
        "_observacao_exibicao_movimentacao_bling",
        "_detalhar_reservas_ativas_produto",
    ]:
        assert f"def {nome}(" not in source


def test_router_de_consulta_importa_helpers_de_contexto_movimentacoes():
    source = _source("app/estoque_movimentacoes_consulta_routes.py")

    assert "from app.estoque_movimentacoes_context import (" in source
    assert "_contexto_venda_pedido_integrado" in source
    assert "_detalhar_reservas_ativas_produto" in source
