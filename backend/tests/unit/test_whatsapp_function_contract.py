from app.whatsapp import function_handlers as fh
from app.whatsapp.tool_executor import _matches_relaxed_product_query
from types import SimpleNamespace


def test_execute_function_wraps_success_with_standard_contract(monkeypatch):
    def fake_ok(db, tenant_id, **kwargs):
        return {"found": 1, "produtos": [{"id": 1, "nome": "Racao"}]}

    monkeypatch.setitem(fh.FUNCTION_HANDLERS, "fake_ok", fake_ok)

    result = fh.execute_function("fake_ok", db=None, tenant_id=1)

    assert result["success"] is True
    assert result["error_code"] is None
    assert result["error"] is None
    assert result["data"]["found"] == 1


def test_execute_function_wraps_handler_error(monkeypatch):
    def fake_error(db, tenant_id, **kwargs):
        return {"error": "falha de negocio"}

    monkeypatch.setitem(fh.FUNCTION_HANDLERS, "fake_error", fake_error)

    result = fh.execute_function("fake_error", db=None, tenant_id=1)

    assert result["success"] is False
    assert result["error_code"] == "FUNCTION_EXECUTION_ERROR"
    assert result["data"] is None
    assert "falha" in result["error"]


def test_execute_function_returns_not_implemented_for_unknown_function():
    result = fh.execute_function("nao_existe", db=None, tenant_id=1)

    assert result["success"] is False
    assert result["error_code"] == "FUNCTION_NOT_IMPLEMENTED"
    assert result["data"] is None


def test_execute_function_wraps_unhandled_exception(monkeypatch):
    def fake_raise(db, tenant_id, **kwargs):
        raise RuntimeError("quebrou")

    monkeypatch.setitem(fh.FUNCTION_HANDLERS, "fake_raise", fake_raise)

    result = fh.execute_function("fake_raise", db=None, tenant_id=1)

    assert result["success"] is False
    assert result["error_code"] == "FUNCTION_EXECUTION_EXCEPTION"
    assert result["data"] is None
    assert "quebrou" in result["error"]


def test_buscar_produto_usa_busca_ranqueada_e_preserva_imagem(monkeypatch):
    captured = {}

    class FakeToolExecutor:
        def __init__(self, db, tenant_id):
            captured["db"] = db
            captured["tenant_id"] = tenant_id

        def execute_tool(self, tool_name, arguments):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            return {
                "success": True,
                "total": 1,
                "produtos": [
                    {
                        "id": "42",
                        "nome": "Ração Special Dog Gold 15kg",
                        "preco": 189.9,
                        "estoque": 12,
                        "descricao": "",
                        "imagem_url": "https://example.com/gold.webp",
                    }
                ],
            }

    monkeypatch.setattr(fh, "ToolExecutor", FakeToolExecutor)

    result = fh.buscar_produto(
        db="db-test",
        tenant_id="tenant-test",
        termo="ração gold",
        keywords=["adultos"],
        limit=5,
    )

    assert captured["tool_name"] == "buscar_produtos"
    assert captured["arguments"]["query"] == "ração gold adultos"
    assert result["found"] == 1
    assert result["produtos"][0]["imagem_url"].endswith("gold.webp")


def test_relaxed_product_match_tolerates_ocr_term_but_requires_weight():
    product_15kg = SimpleNamespace(
        nome="Racao Special Dog Gold Adultos 15kg",
        descricao_curta="Carne e frango",
        codigo="",
        codigo_barras="",
    )
    product_20kg = SimpleNamespace(
        nome="Racao Special Dog Gold Adultos 20kg",
        descricao_curta="Carne e frango",
        codigo="",
        codigo_barras="",
    )
    tokens = ["racao", "special", "dog", "gold", "performance", "15kg"]

    assert _matches_relaxed_product_query(product_15kg, tokens) is True
    assert _matches_relaxed_product_query(product_20kg, tokens) is False


def test_relaxed_product_match_prioritizes_line_over_flavor_words():
    correct_product = SimpleNamespace(
        nome="Racao Special Dog Gold Adultos 15kg",
        descricao_curta="",
        codigo="",
        codigo_barras="",
    )
    wrong_product = SimpleNamespace(
        nome="Racao Special Dog Junior 15kg",
        descricao_curta="Carne e frango",
        codigo="",
        codigo_barras="",
    )
    tokens = ["racao", "special", "dog", "gold", "carne", "frango", "15kg"]

    assert _matches_relaxed_product_query(correct_product, tokens) is True
    assert _matches_relaxed_product_query(wrong_product, tokens) is False


def test_relaxed_product_match_does_not_turn_golden_into_any_racao():
    product = SimpleNamespace(
        nome="Racao Special Dog Gold Adultos 15kg",
        descricao_curta="",
        codigo="",
        codigo_barras="",
    )

    assert _matches_relaxed_product_query(product, ["racao", "golden"]) is False
