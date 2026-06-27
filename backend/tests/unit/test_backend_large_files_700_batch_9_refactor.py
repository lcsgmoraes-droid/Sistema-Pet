from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "app/whatsapp/tools.py",
    "app/whatsapp/tool_definitions.py",
    "app/whatsapp/tool_executor.py",
    "app/whatsapp/tool_utils.py",
]


def _line_count(relative: str) -> int:
    return len((BACKEND_ROOT / relative).read_text(encoding="utf-8").splitlines())


def test_whatsapp_tools_batch_9_modules_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in TARGETS} == {
        relative: count
        for relative in TARGETS
        if (count := _line_count(relative)) <= 700
    }


def test_whatsapp_tools_facade_preserva_imports_publicos():
    from app.whatsapp import tool_definitions, tool_executor, tool_utils, tools

    assert tools.TOOLS_DEFINITIONS is tool_definitions.TOOLS_DEFINITIONS
    assert tools.ToolExecutor is tool_executor.ToolExecutor
    assert tools._normalize_text is tool_utils._normalize_text
    assert tools._only_digits is tool_utils._only_digits


def test_whatsapp_tools_definitions_preservam_tools_esperadas():
    from app.whatsapp.tools import TOOLS_DEFINITIONS

    names = {definition["function"]["name"] for definition in TOOLS_DEFINITIONS}

    assert names == {
        "buscar_produtos",
        "verificar_horarios_disponiveis",
        "buscar_status_pedido",
        "buscar_historico_compras",
        "obter_informacoes_loja",
        "criar_agendamento",
        "adicionar_ao_carrinho",
        "ver_carrinho",
        "calcular_frete",
        "finalizar_pedido",
    }


def test_whatsapp_tool_executor_preserva_dispatch_basico():
    from app.whatsapp.tools import ToolExecutor

    executor = ToolExecutor(db=object(), tenant_id="tenant-test")

    assert callable(executor.execute_tool)
    assert callable(executor._buscar_produtos)
    assert callable(executor._finalizar_pedido)
