from app.whatsapp import function_handlers as fh


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
