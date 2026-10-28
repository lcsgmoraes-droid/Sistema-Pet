"""Fila de kits com JSON real do PostgreSQL, sem chamadas ao Bling.

Usa somente o banco local descartavel e o schema aleatorio do fixture pg_engine.
SQLite nao reproduz a falta de operador de igualdade do tipo PostgreSQL JSON.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import produto_identidade_models as _produto_identidade_models  # noqa: F401
from app.bling_estoque_sync import sincronizar_bling_background
from app.estoque_reserva_service import EstoqueReservaService
from app.models import Tenant, User
from app.produtos_models import (
    Produto,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
    ProdutoKitComponente,
)
from app.services import bling_sync_queue
from app.services.bling_sync_service import BlingSyncService
from app.services.bling_sync_stock import enfileirar_kits_dependentes
from app.tenancy.context import tenant_context
from tests.integration.test_ifood_pdv_pilot_postgres import pg_engine  # noqa: F401


@pytest.fixture()
def caso(request, monkeypatch):
    engine = request.getfixturevalue("pg_engine")
    tenant = uuid4()
    monkeypatch.setattr(
        bling_sync_queue,
        "BlingAPI",
        MagicMock(side_effect=AssertionError("Este teste nao pode chamar o Bling")),
    )
    with tenant_context(tenant), Session(engine, expire_on_commit=False) as db:
        # Confirma que o ensaio usa a coluna JSON real que causou a falha.
        assert (
            db.scalar(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name='produtos' "
                    "AND column_name='variation_attributes'"
                )
            )
            == "json"
        )
        db.add(
            Tenant(id=str(tenant), name="QA kits Bling", name_normalized=str(tenant))
        )
        user = User(tenant_id=tenant, nome="QA", email=f"{tenant}@qa.invalid")
        db.add(user)
        db.flush()
        tubo = Produto(
            tenant_id=tenant,
            user_id=user.id,
            codigo="4000-1",
            nome="Tubo QA",
            tipo_produto="VARIACAO",
            estoque_atual=50,
            variation_attributes={"embalagem": "tubo"},
        )
        pacote = Produto(
            tenant_id=tenant,
            user_id=user.id,
            codigo="4000-4",
            nome="Pacote QA",
            tipo_produto="VARIACAO",
            tipo_kit="VIRTUAL",
            variation_attributes={"embalagem": "pacote"},
        )
        caixa = Produto(
            tenant_id=tenant,
            user_id=user.id,
            codigo="4000-24",
            nome="Caixa QA",
            tipo_produto="KIT",
            tipo_kit="VIRTUAL",
            variation_attributes={"embalagem": "caixa"},
        )
        simples = Produto(
            tenant_id=tenant,
            user_id=user.id,
            codigo="SIMPLES-QA",
            nome="Simples QA",
            tipo_produto="SIMPLES",
            estoque_atual=7,
        )
        db.add_all([tubo, pacote, caixa, simples])
        db.flush()
        for kit, quantidade in [(pacote, 4), (caixa, 24)]:
            db.add(
                ProdutoKitComponente(
                    tenant_id=tenant,
                    kit_id=kit.id,
                    produto_componente_id=tubo.id,
                    quantidade=quantidade,
                )
            )
        for produto in [pacote, caixa, simples]:
            db.add(
                ProdutoBlingSync(
                    tenant_id=tenant,
                    produto_id=produto.id,
                    bling_produto_id=str(100000 + produto.id),
                    sincronizar=True,
                )
            )
        db.commit()
        monkeypatch.setattr(
            EstoqueReservaService,
            "mapa_reservas_ativas_por_produto",
            staticmethod(lambda _db, _tenant: {tubo.id: 3}),
        )
        yield SimpleNamespace(
            db=db,
            engine=engine,
            tubo=tubo,
            pacote=pacote,
            caixa=caixa,
            simples=simples,
        )
        db.rollback()


def _filas(db):
    return {
        fila.produto_id: float(fila.estoque_novo)
        for fila in db.query(ProdutoBlingSyncQueue).all()
    }


def test_consulta_real_enfileira_dois_kits_com_atributos_json(caso):
    resultados = enfileirar_kits_dependentes(
        caso.db,
        caso.tubo.id,
        enfileirar=BlingSyncService.queue_product_sync,
    )
    assert {item["produto_id"] for item in resultados} == {
        caso.pacote.id,
        caso.caixa.id,
    }
    assert _filas(caso.db) == {caso.pacote.id: 11, caso.caixa.id: 1}


def test_commit_confirma_novo_saldo_e_filas_dos_dois_kits(caso):
    caso.tubo.estoque_atual = 26
    sincronizar_bling_background(caso.tubo.id, 26, "venda", db=caso.db)
    assert _filas(caso.db) == {}
    caso.db.commit()
    with Session(caso.engine) as leitura:
        assert leitura.get(Produto, caso.tubo.id).estoque_atual == 26
        assert _filas(leitura) == {caso.pacote.id: 5, caso.caixa.id: 0}


def test_rollback_nao_publica_filas_nem_altera_saldo(caso):
    caso.tubo.estoque_atual = 26
    sincronizar_bling_background(caso.tubo.id, 26, "venda", db=caso.db)
    caso.db.rollback()
    caso.db.commit()
    with Session(caso.engine) as leitura:
        assert leitura.get(Produto, caso.tubo.id).estoque_atual == 50
        assert _filas(leitura) == {}


def test_sessao_propria_preserva_fila_de_produto_sem_kits(caso, monkeypatch):
    monkeypatch.setattr(bling_sync_queue, "SessionLocal", lambda: Session(caso.engine))
    BlingSyncService.queue_product_sync_background(caso.simples.id, 7, "ajuste")
    with Session(caso.engine) as leitura:
        assert _filas(leitura) == {caso.simples.id: 7}
