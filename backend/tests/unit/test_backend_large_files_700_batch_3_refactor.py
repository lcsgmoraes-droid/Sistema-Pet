from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_3_cliente_info_pdv_stays_below_limit():
    target_files = [
        "app/cliente_info_pdv.py",
        "app/cliente_info_pdv_chat.py",
        "app/cliente_info_pdv_schemas.py",
    ]

    for relative_path in target_files:
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_3_cliente_info_pdv_includes_chat_router():
    source = read("app/cliente_info_pdv.py")

    assert "from app.cliente_info_pdv_chat import router as chat_router" in source
    assert "router.include_router(chat_router)" in source
    assert "from app.cliente_info_pdv_schemas import AlertasCarrinhoRequest" in source


def test_backend_large_files_700_batch_3_preserves_public_cliente_pdv_paths():
    from app.cliente_info_pdv import router

    route_paths = {route.path for route in router.routes}

    expected_paths = {
        "/clientes/{cliente_id}/alertas-carrinho",
        "/clientes/{cliente_id}/info-pdv",
        "/clientes/{cliente_id}/chat-pdv",
    }

    assert expected_paths <= route_paths


def test_backend_large_files_700_batch_3_chat_uses_shared_schema():
    source = read("app/cliente_info_pdv_chat.py")
    schemas = read("app/cliente_info_pdv_schemas.py")

    assert "from app.cliente_info_pdv_schemas import ChatPDVRequest" in source
    assert "class ChatPDVRequest" in schemas
    assert "class AlertasCarrinhoRequest" in schemas
