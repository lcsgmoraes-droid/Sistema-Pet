"""Regressão do estado financeiro exibido no histórico do cliente."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable

from app import caixa_models, produtos_models  # noqa: F401 - vínculos da Venda
from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.financeiro_routes import router as financeiro_router
from app.db import get_session
from app.financeiro_models import ContaReceber
from app.models import Cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda, VendaItem, VendaPagamento


def test_historico_compras_nao_exibe_divida_para_venda_cancelada():
    tenant_id = uuid4()
    usuario_id = 91
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        for modelo in (Cliente, Venda, VendaItem, VendaPagamento, ContaReceber):
            connection.execute(
                CreateTable(modelo.__table__, include_foreign_key_constraints=[])
            )

    set_current_tenant(tenant_id)
    cliente = Cliente(
        tenant_id=tenant_id,
        user_id=usuario_id,
        nome="Cliente do histórico",
    )
    cancelada = Venda(
        tenant_id=tenant_id,
        numero_venda="202610070019",
        vendedor_id=usuario_id,
        user_id=usuario_id,
        subtotal=Decimal("379.90"),
        total=Decimal("379.90"),
        status="cancelada",
        data_venda=datetime(2026, 10, 7, 10),
    )
    em_aberto = Venda(
        tenant_id=tenant_id,
        numero_venda="202610070020",
        vendedor_id=usuario_id,
        user_id=usuario_id,
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        status="finalizada",
        data_venda=datetime(2026, 10, 7, 11),
    )
    try:
        with Session(engine, expire_on_commit=False) as db:
            db.add(cliente)
            db.flush()
            cancelada.cliente_id = cliente.id
            em_aberto.cliente_id = cliente.id
            db.add_all([cancelada, em_aberto])
            db.commit()

        app = FastAPI()
        app.include_router(financeiro_router, prefix="/clientes")

        def override_session():
            with Session(engine) as db:
                yield db

        async def override_user_and_tenant():
            set_current_tenant(tenant_id)
            try:
                yield SimpleNamespace(id=usuario_id), tenant_id
            finally:
                clear_current_tenant()

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user_and_tenant] = (
            override_user_and_tenant
        )
        with TestClient(app) as client:
            resposta = client.get(f"/clientes/{cliente.id}/historico-compras")
    finally:
        clear_current_tenant()
        engine.dispose()

    assert resposta.status_code == 200, resposta.text
    vendas = {venda["numero_venda"]: venda for venda in resposta.json()["vendas"]}
    assert vendas["202610070019"]["status"] == "cancelada"
    assert vendas["202610070019"]["status_pagamento"] == "cancelado"
    assert vendas["202610070019"]["saldo_devedor"] == 0
    assert vendas["202610070020"]["status_pagamento"] == "em_aberto"
    assert vendas["202610070020"]["saldo_devedor"] == 100
