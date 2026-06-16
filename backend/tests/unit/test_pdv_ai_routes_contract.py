import asyncio
import inspect
from types import SimpleNamespace

from app import pdv_ai_routes


def test_pdv_ai_health_uses_authenticated_user_without_name_error():
    user = SimpleNamespace(id=42)

    result = asyncio.run(
        pdv_ai_routes.health_check(user_and_tenant=(user, "tenant-selecionado"))
    )

    assert result["status"] == "ok"
    assert result["tenant_id"] == user.id


def test_pdv_ai_request_logs_do_not_include_user_controlled_identity():
    gerar_source = inspect.getsource(pdv_ai_routes.gerar_sugestoes_pdv)
    preview_source = inspect.getsource(pdv_ai_routes.preview_sugestoes_pdv)

    assert "tenant={current_user.id}" not in gerar_source
    assert "tenant={current_user.id}" not in preview_source
    assert "vendedor={request.vendedor_nome}" not in gerar_source
