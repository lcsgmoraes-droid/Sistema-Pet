from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.inativos_routes import (
    _mensagem_sugerida,
    _montar_resultado_inativos,
    _telefone_preferencial,
    _validar_dias_sem_compra,
    listar_clientes_inativos,
    router as inativos_router,
)
from app.db import get_session
from app.tenancy.context import clear_current_tenant, set_current_tenant


def _linha(
    cliente_id,
    nome,
    ultima_compra,
    *,
    telefone=None,
    celular=None,
    total_gasto=0,
    total_compras=1,
):
    return SimpleNamespace(
        cliente_id=cliente_id,
        codigo=str(cliente_id),
        nome=nome,
        telefone=telefone,
        celular=celular,
        email=None,
        ultima_compra=datetime.fromisoformat(ultima_compra),
        total_gasto=total_gasto,
        total_compras=total_compras,
    )


def _criar_banco_inativos():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tenant_id = UUID("00000000-0000-0000-0000-000000000123")
    outro_tenant_id = UUID("00000000-0000-0000-0000-000000000456")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE clientes (id INTEGER PRIMARY KEY, tenant_id CHAR(36), "
                "codigo VARCHAR, nome VARCHAR, telefone VARCHAR, celular VARCHAR, "
                "email VARCHAR, tipo_cadastro VARCHAR, merged_into_id INTEGER, ativo BOOLEAN)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE vendas (id INTEGER PRIMARY KEY, tenant_id CHAR(36), "
                "cliente_id INTEGER, total NUMERIC, status VARCHAR, data_venda DATETIME)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO clientes VALUES "
                "(1, :tenant_id, '100', 'Cliente Inativo', NULL, '18999990000', "
                "NULL, 'cliente', NULL, 1), "
                "(2, :tenant_id, '200', 'Cliente Ativo', NULL, '18999990001', "
                "NULL, 'cliente', NULL, 1), "
                "(3, :outro_tenant_id, '300', 'Outro Tenant', NULL, '18999990002', "
                "NULL, 'cliente', NULL, 1)"
            ),
            {
                "tenant_id": tenant_id.hex,
                "outro_tenant_id": outro_tenant_id.hex,
            },
        )
        connection.execute(
            text(
                "INSERT INTO vendas VALUES "
                "(10, :tenant_id, 1, 100, 'finalizada', '2020-01-01 10:00:00'), "
                "(11, :tenant_id, 2, 200, 'finalizada', '2999-01-01 10:00:00'), "
                "(12, :outro_tenant_id, 3, 300, 'finalizada', '2020-01-01 10:00:00')"
            ),
            {
                "tenant_id": tenant_id.hex,
                "outro_tenant_id": outro_tenant_id.hex,
            },
        )
    return engine, tenant_id


def test_resultado_inativos_calcula_resumo_metricas_e_paginacao():
    resultado = _montar_resultado_inativos(
        [
            _linha(
                1,
                "Ana Silva",
                "2026-07-01T10:00:00",
                celular="18999990000",
                total_gasto=300,
                total_compras=3,
            ),
            _linha(2, "Bia Souza", "2026-06-01T10:00:00", total_gasto=50),
        ],
        hoje=date(2026, 9, 16),
        dias_sem_compra=30,
        pagina=1,
        por_pagina=10,
    )

    assert resultado["resumo"] == {
        "total_inativos": 2,
        "com_whatsapp": 1,
        "sem_whatsapp": 1,
    }
    assert resultado["clientes"][0]["dias_sem_comprar"] == 77
    assert resultado["clientes"][0]["ticket_medio"] == 100
    assert resultado["paginacao"]["total_paginas"] == 1


def test_mensagem_sugerida_usa_primeiro_nome_sem_enviar_nada():
    assert _mensagem_sugerida("Ana Maria").startswith("Olá, Ana!")


def test_telefone_preferencial_ignora_celular_invalido():
    assert _telefone_preferencial("(18) 3333-4444", "0") == "(18) 3333-4444"


def test_validacao_aceita_somente_prazos_disponiveis():
    assert _validar_dias_sem_compra(90) == 90


def test_clientes_router_expoe_inativos_antes_da_rota_de_detalhe():
    from app import clientes_routes
    from app.clientes.crud_routes import detail_router
    from app.clientes.inativos_routes import router as inativos_router

    routers_incluidos = [
        route.original_router
        for route in clientes_routes.router.routes
        if hasattr(route, "original_router")
    ]

    assert "/inativos" in {route.path for route in inativos_router.routes}
    assert routers_incluidos.index(inativos_router) < routers_incluidos.index(
        detail_router
    )


def test_endpoint_retorna_apenas_cliente_ativo_sem_compra_recente():
    engine, tenant_id = _criar_banco_inativos()

    set_current_tenant(tenant_id)
    try:
        with Session(engine) as db:
            resultado = listar_clientes_inativos.__wrapped__(
                dias_sem_compra=30,
                busca=None,
                pagina=1,
                por_pagina=25,
                db=db,
                user_and_tenant=(SimpleNamespace(id=1), tenant_id),
            )
    finally:
        clear_current_tenant()
        engine.dispose()

    assert resultado["resumo"]["total_inativos"] == 1
    assert [cliente["nome"] for cliente in resultado["clientes"]] == ["Cliente Inativo"]


def test_endpoint_http_converte_prazo_da_query_para_inteiro(monkeypatch):
    engine, tenant_id = _criar_banco_inativos()
    app = FastAPI()
    app.include_router(inativos_router, prefix="/clientes")

    def override_session():
        with Session(engine) as db:
            yield db

    async def override_user_and_tenant():
        return SimpleNamespace(id=1), tenant_id

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user_and_tenant] = override_user_and_tenant
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *_args, **_kwargs: None,
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/clientes/inativos",
                params={"dias_sem_compra": "90", "pagina": 1, "por_pagina": 25},
            )
    finally:
        clear_current_tenant()
        engine.dispose()

    assert response.status_code == 200, response.text
    assert response.json()["filtro"]["dias_sem_compra"] == 90
