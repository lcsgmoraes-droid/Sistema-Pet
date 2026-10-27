"""O app e o gestor leem o mesmo carimbo da pessoa vinculada ao acesso."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CashbackTransaction,
    Coupon,
    CustomerRankHistory,
    LoyaltyStamp,
)
from app.models import Cliente, ClienteContato
from app.routes.ecommerce_auth_beneficios import meus_beneficios
from app.routes.ecommerce_auth_cliente import _get_or_create_cliente_for_user
from app.tenancy.context import clear_current_tenant, set_current_tenant
import pytest
from fastapi import HTTPException


def test_carimbo_manual_sem_compras_aparece_no_app_da_mesma_pessoa(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for modelo in (
            Cliente,
            Campaign,
            CampaignExecution,
            CashbackTransaction,
            Coupon,
            CustomerRankHistory,
            LoyaltyStamp,
        ):
            connection.execute(
                CreateTable(modelo.__table__, include_foreign_key_constraints=[])
            )
    tenant = uuid4()
    # PostgreSQL aceita UUID textual nativo; SQLite exige o objeto UUID no bind.
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_cliente._activate_user_tenant_context",
        lambda _: tenant,
    )
    user = SimpleNamespace(
        id=42,
        tenant_id=tenant,
        nome="Pessoa fictícia",
        email="pessoa-ficticia@example.test",
        cpf_cnpj=None,
        telefone=None,
    )
    set_current_tenant(tenant)
    try:
        with Session(engine) as db:
            cliente = Cliente(
                tenant_id=tenant,
                user_id=1,
                auth_user_id=user.id,
                nome=user.nome,
                codigo="2061",
                email=user.email,
                ativo=True,
            )
            db.add(cliente)
            db.execute(
                Campaign.__table__.insert().values(
                    id=101,
                    tenant_id=tenant,
                    name="Cartão de teste",
                    campaign_type=CampaignTypeEnum.loyalty_stamp,
                    status=CampaignStatusEnum.active,
                    params={"stamps_to_complete": 10},
                )
            )
            db.flush()
            db.execute(
                LoyaltyStamp.__table__.insert().values(
                    id=201,
                    tenant_id=tenant,
                    campaign_id=101,
                    customer_id=cliente.id,
                    stamp_index=1,
                    is_manual=True,
                    notes="Ajuste manual fictício",
                    created_at=datetime.now(timezone.utc),
                )
            )
            db.flush()
            resolvido = _get_or_create_cliente_for_user(db, user)
            gestor = summarize_loyalty_balances_for_customer(
                db, tenant_id=tenant, customer_id=cliente.id
            )
            app = meus_beneficios(current_user=user, db=db)
            assert resolvido.id == cliente.id
            assert gestor["total_carimbos"] == 1
            assert app["carimbos"]["total_geral"] == 1
            assert app["carimbos"]["carimbos_no_cartao"] == 1
            assert app["carimbos"]["carimbos_ativos_brutos"] == 1
            assert app["carimbos"]["meta"] == 10
            assert app["ranking"]["total_purchases"] == 0
    finally:
        clear_current_tenant()
        engine.dispose()


@pytest.mark.parametrize("vinculo_existente", [False, True])
def test_login_por_telefone_reusa_cadastro_sem_sobrescrever_vinculo(
    monkeypatch, vinculo_existente
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            CreateTable(Cliente.__table__, include_foreign_key_constraints=[])
        )
        connection.execute(
            CreateTable(ClienteContato.__table__, include_foreign_key_constraints=[])
        )
    tenant = uuid4()
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_cliente._activate_user_tenant_context",
        lambda _: tenant,
    )
    set_current_tenant(tenant)
    user = SimpleNamespace(
        id=84,
        tenant_id=tenant,
        nome="Pessoa fictícia",
        email=None,
        cpf_cnpj=None,
        telefone=None,
        login_phone="+5511988887777",
    )
    try:
        with Session(engine) as db:
            principal = Cliente(
                tenant_id=tenant,
                user_id=1,
                nome="Pessoa completa fictícia",
                codigo="2061",
                celular="(11) 98888-7777",
                ativo=True,
            )
            db.add(principal)
            duplicado = None
            if vinculo_existente:
                duplicado = Cliente(
                    tenant_id=tenant,
                    user_id=1,
                    auth_user_id=user.id,
                    nome="Pessoa fictícia",
                    codigo="10851",
                    ativo=True,
                )
                db.add(duplicado)
            db.flush()
            resultado = _get_or_create_cliente_for_user(db, user)
            db.flush()
            assert db.query(Cliente).count() == (2 if vinculo_existente else 1)
            if vinculo_existente:
                assert resultado.id == duplicado.id
                assert principal.auth_user_id is None
                assert duplicado.auth_user_id == user.id
            else:
                assert resultado.id == principal.id
                assert principal.auth_user_id == user.id
    finally:
        clear_current_tenant()
        engine.dispose()


def test_login_phone_nao_toma_cadastro_ligado_a_outra_conta(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            CreateTable(Cliente.__table__, include_foreign_key_constraints=[])
        )
    tenant = uuid4()
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_cliente._activate_user_tenant_context",
        lambda _: tenant,
    )
    set_current_tenant(tenant)
    user = SimpleNamespace(
        id=84,
        tenant_id=tenant,
        nome="Pessoa fictícia",
        email=None,
        cpf_cnpj=None,
        telefone=None,
        login_phone="+5511988887777",
    )
    try:
        with Session(engine) as db:
            cliente = Cliente(
                tenant_id=tenant,
                user_id=1,
                auth_user_id=99,
                nome="Pessoa fictícia",
                codigo="2061",
                celular="(11) 98888-7777",
                ativo=True,
            )
            db.add(cliente)
            db.flush()
            with pytest.raises(HTTPException) as erro:
                _get_or_create_cliente_for_user(db, user)
            assert erro.value.status_code == 409
            assert cliente.auth_user_id == 99
    finally:
        clear_current_tenant()
        engine.dispose()
