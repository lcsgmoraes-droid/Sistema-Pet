import pytest
from types import SimpleNamespace

from fastapi import HTTPException

from app.clientes.relatorio_routes import (
    _serializar_identidade_empresa,
    _validar_tipos_relatorio,
)


def test_relatorio_aceita_tipos_validos_sem_repeticao():
    assert _validar_tipos_relatorio(["Cliente", "cliente", "fornecedor"]) == [
        "cliente",
        "fornecedor",
    ]


def test_relatorio_rejeita_tipo_desconhecido():
    with pytest.raises(HTTPException) as exc_info:
        _validar_tipos_relatorio(["cliente", "desconhecido"])

    assert exc_info.value.status_code == 422


def test_relatorio_serializa_identidade_da_empresa_logada():
    tenant = SimpleNamespace(
        name="Pet Feliz",
        ecommerce_slug="pet-feliz",
        logo_url="/uploads/ecommerce/tenant/logo.png",
    )

    assert _serializar_identidade_empresa(tenant) == {
        "nome": "Pet Feliz",
        "slug": "pet-feliz",
        "logo_url": "/uploads/ecommerce/tenant/logo.png",
    }


def test_rota_de_relatorio_fica_antes_da_rota_de_detalhe():
    from app import clientes_routes
    from app.clientes.crud_routes import detail_router
    from app.clientes.relatorio_routes import router as relatorio_router

    routers_incluidos = [
        route.original_router
        for route in clientes_routes.router.routes
        if getattr(route, "original_router", None)
    ]
    paths_relatorio = [route.path for route in relatorio_router.routes]

    assert "/relatorio/pessoas" in paths_relatorio
    assert routers_incluidos.index(relatorio_router) < routers_incluidos.index(
        detail_router
    )
