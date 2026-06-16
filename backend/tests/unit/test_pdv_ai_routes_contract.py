import asyncio
from types import SimpleNamespace

from app import pdv_ai_routes


def test_pdv_ai_health_uses_authenticated_user_without_name_error():
    user = SimpleNamespace(id=42)

    result = asyncio.run(
        pdv_ai_routes.health_check(user_and_tenant=(user, "tenant-selecionado"))
    )

    assert result["status"] == "ok"
    assert result["tenant_id"] == user.id
