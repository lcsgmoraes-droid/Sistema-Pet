from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PEDIDOS_COMPRA_ROUTES = BACKEND_ROOT / "app" / "pedidos_compra_routes.py"
RELATORIO_VENDAS_ROUTES = BACKEND_ROOT / "app" / "relatorio_vendas_routes.py"


def _route_function_source(source: str, function_name: str) -> str:
    markers = [f"def {function_name}(", f"async def {function_name}("]
    start = min(source.index(marker) for marker in markers if marker in source)
    next_route = source.find("\n@router.", start + 1)
    if next_route == -1:
        return source[start:]
    return source[start:next_route]


def test_pedido_email_route_has_no_returned_dead_success_block():
    source = PEDIDOS_COMPRA_ROUTES.read_text(encoding="utf-8")
    function_source = _route_function_source(source, "enviar_pedido")
    first_success_return = function_source.index(
        '"message": "Pedido enviado por e-mail com sucesso"'
    )

    assert (
        '"message": "Pedido enviado com sucesso"'
        not in function_source[first_success_return:]
    )


def test_pedido_excel_export_has_no_dead_legacy_workbook_block_after_streaming_return():
    source = PEDIDOS_COMPRA_ROUTES.read_text(encoding="utf-8")
    function_source = _route_function_source(source, "exportar_excel")
    streaming_return = function_source.index("return StreamingResponse(")

    assert "openpyxl.Workbook()" not in function_source[streaming_return:]
    assert "Biblioteca openpyxl" not in function_source[streaming_return:]


def test_pedido_pdf_export_has_no_dead_legacy_reportlab_block_after_streaming_return():
    source = PEDIDOS_COMPRA_ROUTES.read_text(encoding="utf-8")
    function_source = _route_function_source(source, "exportar_pdf")
    streaming_return = function_source.index("return StreamingResponse(")

    assert "SimpleDocTemplate(buffer" not in function_source[streaming_return:]
    assert "Biblioteca reportlab" not in function_source[streaming_return:]


def test_relatorio_vendas_pdf_does_not_catch_same_exception_twice_in_data_block():
    source = RELATORIO_VENDAS_ROUTES.read_text(encoding="utf-8")
    function_source = _route_function_source(source, "exportar_vendas_pdf")

    assert (
        'raise HTTPException(status_code=500, detail=f"Erro ao buscar dados: {str(e)}")\n'
        "    except Exception as e:" not in function_source
    )
