from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.clientes.ranking_routes import (
    _montar_resultado_ranking,
    _validar_periodo,
    listar_ranking_clientes,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant


def _linha(cliente_id, nome, gasto, compras, ultima="2026-09-10T10:00:00"):
    return SimpleNamespace(
        cliente_id=cliente_id,
        codigo=str(cliente_id),
        nome=nome,
        telefone=None,
        celular="11999999999",
        total_gasto=gasto,
        total_compras=compras,
        ultima_compra=datetime.fromisoformat(ultima),
    )


def test_ranking_separa_lideres_por_valor_compras_e_quantidade():
    resultado = _montar_resultado_ranking(
        [
            _linha(1, "Ana", 1000, 2),
            _linha(2, "Bia", 800, 8),
            _linha(3, "Caio", 700, 4),
        ],
        {1: 5, 2: 12, 3: 30},
        ordenar_por="total_gasto",
        busca=None,
        pagina=1,
        por_pagina=50,
    )

    assert resultado["lideres"]["total_gasto"]["nome"] == "Ana"
    assert resultado["lideres"]["total_compras"]["nome"] == "Bia"
    assert resultado["lideres"]["total_itens"]["nome"] == "Caio"
    assert resultado["clientes"][0]["ticket_medio"] == 500
    assert resultado["clientes"][0]["posicoes"]["total_gasto"] == 1


def test_ranking_busca_sem_alterar_lideres_gerais():
    resultado = _montar_resultado_ranking(
        [_linha(1, "Ana", 1000, 2), _linha(2, "Bia", 800, 8)],
        {1: 5, 2: 12},
        ordenar_por="total_compras",
        busca="Ana",
        pagina=1,
        por_pagina=50,
    )

    assert [cliente["nome"] for cliente in resultado["clientes"]] == ["Ana"]
    assert resultado["lideres"]["total_compras"]["nome"] == "Bia"
    assert resultado["paginacao"]["total"] == 1


def test_ranking_rejeita_periodo_invertido():
    with pytest.raises(HTTPException) as exc_info:
        _validar_periodo(date(2026, 9, 10), date(2026, 9, 1))

    assert exc_info.value.status_code == 422


def test_clientes_router_expoe_ranking_antes_da_rota_de_detalhe():
    from app import clientes_routes
    from app.clientes.ranking_routes import router as ranking_router

    paths_clientes = [route.path for route in clientes_routes.router.routes]

    assert "/ranking-vendas" in {route.path for route in ranking_router.routes}
    assert paths_clientes.index("/clientes/ranking-vendas") < paths_clientes.index(
        "/clientes/{cliente_id}"
    )


def test_endpoint_calcula_vendas_e_itens_sem_duplicar_total():
    engine = create_engine("sqlite://")
    tenant_id = UUID("00000000-0000-0000-0000-000000000123")
    tenant_db = tenant_id.hex
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE clientes (id INTEGER PRIMARY KEY, tenant_id CHAR(36), "
                "codigo VARCHAR, nome VARCHAR, telefone VARCHAR, celular VARCHAR)"
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
                "CREATE TABLE venda_itens (id INTEGER PRIMARY KEY, tenant_id CHAR(36), "
                "venda_id INTEGER, quantidade NUMERIC)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO clientes VALUES "
                "(1, :tenant_id, '10001', 'Cliente Ranking', NULL, '11999999999')"
            ),
            {"tenant_id": tenant_db},
        )
        connection.execute(
            text(
                "INSERT INTO vendas VALUES "
                "(10, :tenant_id, 1, 100, 'finalizada', '2026-09-10 10:00:00')"
            ),
            {"tenant_id": tenant_db},
        )
        connection.execute(
            text(
                "INSERT INTO venda_itens VALUES "
                "(100, :tenant_id, 10, 2), (101, :tenant_id, 10, 5)"
            ),
            {"tenant_id": tenant_db},
        )

    set_current_tenant(tenant_id)
    try:
        with Session(engine) as db:
            resultado = listar_ranking_clientes.__wrapped__(
                data_inicio=date(2026, 9, 1),
                data_fim=date(2026, 9, 30),
                ordenar_por="total_gasto",
                busca=None,
                pagina=1,
                por_pagina=50,
                db=db,
                user_and_tenant=(SimpleNamespace(id=1), tenant_id),
            )
    finally:
        clear_current_tenant()
        engine.dispose()

    assert resultado["resumo"]["faturamento_clientes"] == 100
    assert resultado["resumo"]["total_compras"] == 1
    assert resultado["resumo"]["total_itens"] == 7
    assert resultado["clientes"][0]["total_gasto"] == 100
