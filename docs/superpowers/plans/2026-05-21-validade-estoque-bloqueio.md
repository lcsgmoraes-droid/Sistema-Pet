# Protecao de Estoque por Validade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build configurable stock protection for near-expiration lots, with vendable-stock blocking, reminders, supplier exchange, discard loss tracking, PDV alerting, and a first loss report.

**Architecture:** Keep expiration logic in a new focused backend module instead of growing `backend/app/estoque_routes.py`. Treat `Produto.estoque_atual` as vendable stock, keep lot traceability in `produto_lotes`, and persist each expiration block in a dedicated audit table so discard/exchange decisions do not double-decrease vendable stock.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, React/Vite, existing `api` client, existing Lembretes and ConfiguracaoEstoque pages.

---

## File Structure

- Create `backend/app/estoque_validade_models.py`: SQLAlchemy model for expiration blocks and decisions.
- Create `backend/app/estoque_validade_service.py`: pure service for config reading, block processing, actions, PDV alert payloads, and report rows.
- Create `backend/app/estoque_validade_routes.py`: authenticated API endpoints under `/estoque/validade`.
- Modify `backend/app/models.py`: add tenant-level configuration fields used by `/empresa/config-estoque`.
- Modify `backend/app/empresa_routes.py`: expose and persist expiration protection settings with stock config.
- Modify `backend/app/estoque/service.py`: ensure FIFO consumes only active sellable lots and keeps blocked/vencido lots out of sale.
- Modify `backend/app/main.py`: register the new router.
- Create `backend/alembic/versions/ox20260521a1_create_estoque_validade_bloqueios.py`: idempotent schema migration.
- Create `backend/tests/unit/test_estoque_validade_service.py`: service TDD coverage.
- Create `backend/tests/unit/test_estoque_validade_routes_contract.py`: endpoint contract and tenant protection coverage.
- Modify `backend/tests/unit/test_plano_basico_tenant_contract.py`: protect route registration/config contract.
- Modify `frontend/src/pages/configuracoes/ConfiguracaoEstoque.jsx`: add settings UI.
- Modify `frontend/src/pages/Lembretes.jsx`: add expiration pending cards and action handlers.
- Modify `frontend/src/components/pdv/PDVInfoBanners.jsx`: render product expiration alert in PDV.
- Modify `frontend/src/components/pdv/PDVMainArea.jsx`: fetch `/estoque/validade/pdv-alertas` for cart product IDs and pass alerts down.
- Modify `backend/app/routes/ecommerce_cart.py` and `backend/app/routes/ecommerce_public.py`: rely on `Produto.estoque_atual` as vendable stock and expose safe stock consistently.

## Task 1: Backend Schema And Model

**Files:**
- Create: `backend/app/estoque_validade_models.py`
- Create: `backend/alembic/versions/ox20260521a1_create_estoque_validade_bloqueios.py`
- Modify: `backend/app/models.py`

- [ ] **Step 1: Write the failing model/import test**

Add this test to `backend/tests/unit/test_estoque_validade_service.py`:

```python
from app.estoque_validade_models import EstoqueValidadeBloqueio


def test_validade_bloqueio_model_declares_statuses_and_quantities():
    campos = EstoqueValidadeBloqueio.__table__.columns

    assert "produto_id" in campos
    assert "lote_id" in campos
    assert "status" in campos
    assert "quantidade_bloqueada" in campos
    assert "quantidade_resolvida" in campos
    assert "custo_total_estimado" in campos
    assert "movimentacao_bloqueio_id" in campos
    assert "movimentacao_resolucao_id" in campos
```

- [ ] **Step 2: Run the test and verify RED**

Run: `pytest backend/tests/unit/test_estoque_validade_service.py::test_validade_bloqueio_model_declares_statuses_and_quantities -q`

Expected: fails with `ModuleNotFoundError: No module named 'app.estoque_validade_models'`.

- [ ] **Step 3: Create the model**

Create `backend/app/estoque_validade_models.py`:

```python
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class EstoqueValidadeBloqueio(BaseTenantModel):
    __tablename__ = "estoque_validade_bloqueios"
    __table_args__ = (
        Index("ix_estoque_validade_tenant_status", "tenant_id", "status"),
        Index("ix_estoque_validade_tenant_produto", "tenant_id", "produto_id"),
        Index("ix_estoque_validade_tenant_lote", "tenant_id", "lote_id"),
        Index("ix_estoque_validade_lote_status", "lote_id", "status"),
        {"extend_existing": True},
    )

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("produto_lotes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="pendente")
    origem = Column(String(30), nullable=False, default="rotina")
    data_referencia = Column(DateTime(timezone=True), nullable=False)
    data_validade = Column(DateTime(timezone=True), nullable=True)
    quantidade_bloqueada = Column(Float, nullable=False, default=0)
    quantidade_resolvida = Column(Float, nullable=False, default=0)
    custo_unitario = Column(Float, nullable=True)
    custo_total_estimado = Column(Float, nullable=False, default=0)
    movimentacao_bloqueio_id = Column(Integer, ForeignKey("estoque_movimentacoes.id"), nullable=True)
    movimentacao_resolucao_id = Column(Integer, ForeignKey("estoque_movimentacoes.id"), nullable=True)
    decidido_por_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    decisao = Column(String(30), nullable=True)
    observacao = Column(Text, nullable=True)

    produto = relationship("Produto")
    lote = relationship("ProdutoLote")
```

- [ ] **Step 4: Add tenant config columns**

In `backend/app/models.py`, inside `class Tenant`, after `permite_estoque_negativo`, add:

```python
    protecao_validade_ativa = Column(Boolean, nullable=False, server_default='false')
    dias_alerta_validade = Column(Integer, nullable=False, server_default='15')
    bloquear_validade_pdv = Column(Boolean, nullable=False, server_default='true')
    bloquear_validade_ecommerce = Column(Boolean, nullable=False, server_default='true')
    bloquear_validade_integracoes_online = Column(Boolean, nullable=False, server_default='false')
```

- [ ] **Step 5: Create the Alembic migration**

Create `backend/alembic/versions/ox20260521a1_create_estoque_validade_bloqueios.py`:

```python
"""create estoque validade bloqueios

Revision ID: ox20260521a1
Revises: ow20260518a1
Create Date: 2026-05-21 07:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ox20260521a1"
down_revision: Union[str, Sequence[str], None] = "ow20260518a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_once(name: str, table_name: str, columns: list[str]) -> None:
    if name not in _indexes(table_name):
        op.create_index(name, table_name, columns)


def upgrade() -> None:
    _add_column_once("tenants", sa.Column("protecao_validade_ativa", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_once("tenants", sa.Column("dias_alerta_validade", sa.Integer(), nullable=False, server_default="15"))
    _add_column_once("tenants", sa.Column("bloquear_validade_pdv", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_once("tenants", sa.Column("bloquear_validade_ecommerce", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_once("tenants", sa.Column("bloquear_validade_integracoes_online", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not _has_table("estoque_validade_bloqueios"):
        op.create_table(
            "estoque_validade_bloqueios",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
            sa.Column("lote_id", sa.Integer(), sa.ForeignKey("produto_lotes.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
            sa.Column("origem", sa.String(30), nullable=False, server_default="rotina"),
            sa.Column("data_referencia", sa.DateTime(timezone=True), nullable=False),
            sa.Column("data_validade", sa.DateTime(timezone=True), nullable=True),
            sa.Column("quantidade_bloqueada", sa.Float(), nullable=False, server_default="0"),
            sa.Column("quantidade_resolvida", sa.Float(), nullable=False, server_default="0"),
            sa.Column("custo_unitario", sa.Float(), nullable=True),
            sa.Column("custo_total_estimado", sa.Float(), nullable=False, server_default="0"),
            sa.Column("movimentacao_bloqueio_id", sa.Integer(), sa.ForeignKey("estoque_movimentacoes.id"), nullable=True),
            sa.Column("movimentacao_resolucao_id", sa.Integer(), sa.ForeignKey("estoque_movimentacoes.id"), nullable=True),
            sa.Column("decidido_por_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decisao", sa.String(30), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "lote_id", "status", name="uq_estoque_validade_lote_status"),
        )

    _create_index_once("ix_estoque_validade_tenant_status", "estoque_validade_bloqueios", ["tenant_id", "status"])
    _create_index_once("ix_estoque_validade_tenant_produto", "estoque_validade_bloqueios", ["tenant_id", "produto_id"])
    _create_index_once("ix_estoque_validade_tenant_lote", "estoque_validade_bloqueios", ["tenant_id", "lote_id"])


def downgrade() -> None:
    if _has_table("estoque_validade_bloqueios"):
        op.drop_table("estoque_validade_bloqueios")
```

- [ ] **Step 6: Run tests and migration smoke locally**

Run: `pytest backend/tests/unit/test_estoque_validade_service.py::test_validade_bloqueio_model_declares_statuses_and_quantities -q`

Expected: pass.

Run: `python -m compileall backend/app/estoque_validade_models.py backend/alembic/versions/ox20260521a1_create_estoque_validade_bloqueios.py`

Expected: both files compile.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/app/estoque_validade_models.py backend/app/models.py backend/alembic/versions/ox20260521a1_create_estoque_validade_bloqueios.py backend/tests/unit/test_estoque_validade_service.py
git commit -m "feat: cria base de bloqueio por validade"
```

## Task 2: Expiration Blocking Service

**Files:**
- Create: `backend/app/estoque_validade_service.py`
- Modify: `backend/tests/unit/test_estoque_validade_service.py`
- Modify: `backend/app/estoque/service.py`

- [ ] **Step 1: Write failing service tests**

Append to `backend/tests/unit/test_estoque_validade_service.py`:

```python
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.estoque_validade_service import EstoqueValidadeService


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index


def _produto(estoque=10):
    return SimpleNamespace(id=10, nome="Racao Teste", estoque_atual=float(estoque), preco_custo=8.5)


def _lote(validade, quantidade=3, status="ativo"):
    return SimpleNamespace(
        id=77,
        produto_id=10,
        nome_lote="L-VAL-1",
        data_validade=validade,
        quantidade_disponivel=float(quantidade),
        custo_unitario=7.0,
        status=status,
    )


def test_bloquear_lote_reduz_vendavel_e_marca_lote_como_bloqueado(monkeypatch):
    db = FakeDb()
    produto = _produto(estoque=10)
    lote = _lote(datetime(2026, 6, 5, tzinfo=timezone.utc), quantidade=3)

    bloqueio = EstoqueValidadeService.bloquear_lote(
        db=db,
        tenant_id="tenant-1",
        user_id=5,
        produto=produto,
        lote=lote,
        agora=datetime(2026, 5, 21, tzinfo=timezone.utc),
        origem="teste",
    )

    assert produto.estoque_atual == pytest.approx(7)
    assert lote.status == "bloqueado_validade"
    assert bloqueio.status == "pendente"
    assert bloqueio.quantidade_bloqueada == pytest.approx(3)
    assert bloqueio.custo_total_estimado == pytest.approx(21)


def test_descartar_bloqueio_nao_reduz_vendavel_duas_vezes():
    db = FakeDb()
    produto = _produto(estoque=7)
    lote = _lote(datetime(2026, 6, 5, tzinfo=timezone.utc), quantidade=3, status="bloqueado_validade")
    bloqueio = SimpleNamespace(
        id=99,
        produto=produto,
        lote=lote,
        produto_id=10,
        lote_id=77,
        status="pendente",
        quantidade_bloqueada=3.0,
        quantidade_resolvida=0.0,
        custo_unitario=7.0,
        custo_total_estimado=21.0,
        movimentacao_resolucao_id=None,
        decisao=None,
        decidido_por_user_id=None,
        decidido_em=None,
        observacao=None,
    )

    resolvido = EstoqueValidadeService.descartar_bloqueio(
        db=db,
        tenant_id="tenant-1",
        user_id=5,
        bloqueio=bloqueio,
        observacao="Produto vencido separado fisicamente",
        agora=datetime(2026, 5, 22, tzinfo=timezone.utc),
    )

    assert produto.estoque_atual == pytest.approx(7)
    assert lote.quantidade_disponivel == pytest.approx(0)
    assert lote.status == "descartado"
    assert resolvido.status == "descartado"
    assert resolvido.decisao == "descartado"
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest backend/tests/unit/test_estoque_validade_service.py -q`

Expected: fails because `app.estoque_validade_service` does not exist.

- [ ] **Step 3: Implement the service**

Create `backend/app/estoque_validade_service.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.estoque.service import EstoqueService
from app.estoque_validade_models import EstoqueValidadeBloqueio
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote


STATUS_ABERTOS = {"pendente"}
STATUS_BLOQUEADOS_LOTE = {"bloqueado_validade", "vencido_bloqueado"}


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _tenant_str(tenant_id) -> str:
    return str(tenant_id)


class EstoqueValidadeService:
    @staticmethod
    def bloquear_lote(
        *,
        db: Session,
        tenant_id: str,
        user_id: int | None,
        produto: Produto,
        lote: ProdutoLote,
        agora: datetime | None = None,
        origem: str = "rotina",
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        quantidade = max(float(getattr(lote, "quantidade_disponivel", 0) or 0), 0)
        quantidade_vendavel = max(float(getattr(produto, "estoque_atual", 0) or 0), 0)
        quantidade_bloquear = min(quantidade, quantidade_vendavel)
        custo_unitario = float(getattr(lote, "custo_unitario", None) or getattr(produto, "preco_custo", 0) or 0)

        produto.estoque_atual = quantidade_vendavel - quantidade_bloquear
        lote.status = "vencido_bloqueado" if getattr(lote, "data_validade", None) and lote.data_validade <= agora else "bloqueado_validade"

        user_id_mov = EstoqueService._resolver_user_id_operacao(db, _tenant_str(tenant_id), user_id)
        movimento = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo="saida",
            motivo="validade_bloqueio",
            quantidade=quantidade_bloquear,
            quantidade_anterior=quantidade_vendavel,
            quantidade_nova=produto.estoque_atual,
            custo_unitario=custo_unitario,
            valor_total=quantidade_bloquear * custo_unitario,
            lote_id=lote.id,
            referencia_id=lote.id,
            referencia_tipo="validade_lote",
            observacao=f"Lote {lote.nome_lote} retirado do estoque vendavel por validade",
            user_id=user_id_mov,
            tenant_id=tenant_id,
        )
        db.add(movimento)
        db.flush()

        bloqueio = EstoqueValidadeBloqueio(
            tenant_id=tenant_id,
            produto_id=produto.id,
            lote_id=lote.id,
            user_id=user_id_mov,
            status="pendente",
            origem=origem,
            data_referencia=agora,
            data_validade=getattr(lote, "data_validade", None),
            quantidade_bloqueada=quantidade_bloquear,
            quantidade_resolvida=0,
            custo_unitario=custo_unitario,
            custo_total_estimado=quantidade_bloquear * custo_unitario,
            movimentacao_bloqueio_id=movimento.id,
        )
        db.add(bloqueio)
        db.flush()
        return bloqueio

    @staticmethod
    def descartar_bloqueio(
        *,
        db: Session,
        tenant_id: str,
        user_id: int,
        bloqueio: EstoqueValidadeBloqueio,
        observacao: str | None = None,
        agora: datetime | None = None,
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        lote = bloqueio.lote
        produto = bloqueio.produto
        quantidade = float(bloqueio.quantidade_bloqueada or 0) - float(bloqueio.quantidade_resolvida or 0)
        custo_unitario = float(bloqueio.custo_unitario or getattr(produto, "preco_custo", 0) or 0)

        lote.quantidade_disponivel = max(float(getattr(lote, "quantidade_disponivel", 0) or 0) - quantidade, 0)
        lote.status = "descartado"

        user_id_mov = EstoqueService._resolver_user_id_operacao(db, _tenant_str(tenant_id), user_id)
        movimento = EstoqueMovimentacao(
            produto_id=bloqueio.produto_id,
            tipo="saida",
            motivo="validade_descarte",
            quantidade=quantidade,
            quantidade_anterior=float(getattr(produto, "estoque_atual", 0) or 0),
            quantidade_nova=float(getattr(produto, "estoque_atual", 0) or 0),
            custo_unitario=custo_unitario,
            valor_total=quantidade * custo_unitario,
            lote_id=bloqueio.lote_id,
            referencia_id=bloqueio.id,
            referencia_tipo="validade_bloqueio",
            observacao=observacao or "Descarte por validade",
            user_id=user_id_mov,
            tenant_id=tenant_id,
        )
        db.add(movimento)
        db.flush()

        bloqueio.status = "descartado"
        bloqueio.decisao = "descartado"
        bloqueio.quantidade_resolvida = float(bloqueio.quantidade_bloqueada or 0)
        bloqueio.movimentacao_resolucao_id = movimento.id
        bloqueio.decidido_por_user_id = user_id_mov
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio
```

- [ ] **Step 4: Add active-lot guard to FIFO if missing**

In `backend/app/estoque/service.py`, confirm `_consumir_lotes_fifo` filters `ProdutoLote.status == 'ativo'`. If it already does, add this regression test instead of changing production code:

```python
def test_fifo_de_lotes_consumiveis_usa_apenas_status_ativo():
    import inspect
    from app.estoque.service import EstoqueService

    source = inspect.getsource(EstoqueService._consumir_lotes_fifo)
    assert "ProdutoLote.status == 'ativo'" in source
```

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest backend/tests/unit/test_estoque_validade_service.py -q`

Expected: all tests pass.

Run: `python -m compileall backend/app/estoque_validade_service.py backend/app/estoque/service.py`

Expected: compile succeeds.

- [ ] **Step 6: Commit**

Run:

```powershell
git add backend/app/estoque_validade_service.py backend/app/estoque/service.py backend/tests/unit/test_estoque_validade_service.py
git commit -m "feat: adiciona servico de bloqueio por validade"
```

## Task 3: Processing, Actions, And Routes

**Files:**
- Create: `backend/app/estoque_validade_routes.py`
- Modify: `backend/app/estoque_validade_service.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/unit/test_estoque_validade_routes_contract.py`

- [ ] **Step 1: Write route contract tests**

Create `backend/tests/unit/test_estoque_validade_routes_contract.py`:

```python
import inspect

from app import estoque_validade_routes


def test_validade_routes_expose_processing_actions_and_report():
    routes = {(route.path, ",".join(sorted(route.methods))) for route in estoque_validade_routes.router.routes}

    assert ("/processar", "POST") in routes
    assert ("/pendencias", "GET") in routes
    assert ("/{bloqueio_id}/descartar", "POST") in routes
    assert ("/{bloqueio_id}/trocar-fornecedor", "POST") in routes
    assert ("/{bloqueio_id}/retornar-vendavel", "POST") in routes
    assert ("/pdv-alertas", "GET") in routes
    assert ("/relatorio-perdas", "GET") in routes


def test_validade_routes_use_selected_tenant_context():
    source = inspect.getsource(estoque_validade_routes)

    assert "Depends(get_current_user_and_tenant)" in source
    assert "tenant_id" in source
    assert "Depends(get_current_user)" not in source
```

- [ ] **Step 2: Run route tests and verify RED**

Run: `pytest backend/tests/unit/test_estoque_validade_routes_contract.py -q`

Expected: fails because `app.estoque_validade_routes` does not exist.

- [ ] **Step 3: Extend service with processing/query methods**

Add these methods to `EstoqueValidadeService`:

```python
    @staticmethod
    def processar_lotes_em_risco(*, db: Session, tenant, user_id: int | None, agora: datetime | None = None) -> dict:
        agora = agora or _agora_utc()
        if not bool(getattr(tenant, "protecao_validade_ativa", False)):
            return {"processados": 0, "bloqueios": []}

        from datetime import timedelta

        limite = agora + timedelta(days=int(getattr(tenant, "dias_alerta_validade", 15) or 15))
        lotes = (
            db.query(ProdutoLote)
            .join(Produto, Produto.id == ProdutoLote.produto_id)
            .filter(
                ProdutoLote.tenant_id == tenant.id,
                ProdutoLote.status == "ativo",
                ProdutoLote.quantidade_disponivel > 0,
                ProdutoLote.data_validade.isnot(None),
                ProdutoLote.data_validade <= limite,
                Produto.situacao.isnot(False),
            )
            .all()
        )

        bloqueios = []
        for lote in lotes:
            existente = (
                db.query(EstoqueValidadeBloqueio)
                .filter(
                    EstoqueValidadeBloqueio.tenant_id == tenant.id,
                    EstoqueValidadeBloqueio.lote_id == lote.id,
                    EstoqueValidadeBloqueio.status.in_(list(STATUS_ABERTOS)),
                )
                .first()
            )
            if existente:
                continue
            bloqueios.append(
                EstoqueValidadeService.bloquear_lote(
                    db=db,
                    tenant_id=tenant.id,
                    user_id=user_id,
                    produto=lote.produto,
                    lote=lote,
                    agora=agora,
                    origem="rotina",
                )
            )

        return {"processados": len(bloqueios), "bloqueios": bloqueios}

    @staticmethod
    def trocar_com_fornecedor(*, db: Session, tenant_id: str, user_id: int, bloqueio, observacao: str | None = None, agora: datetime | None = None):
        agora = agora or _agora_utc()
        lote = bloqueio.lote
        lote.quantidade_disponivel = 0
        lote.status = "trocado_fornecedor"
        bloqueio.status = "trocado_fornecedor"
        bloqueio.decisao = "trocado_fornecedor"
        bloqueio.quantidade_resolvida = float(bloqueio.quantidade_bloqueada or 0)
        bloqueio.decidido_por_user_id = user_id
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio

    @staticmethod
    def retornar_ao_vendavel(*, db: Session, tenant_id: str, user_id: int, bloqueio, observacao: str | None = None, agora: datetime | None = None):
        agora = agora or _agora_utc()
        produto = bloqueio.produto
        lote = bloqueio.lote
        quantidade = float(bloqueio.quantidade_bloqueada or 0) - float(bloqueio.quantidade_resolvida or 0)
        produto.estoque_atual = float(produto.estoque_atual or 0) + quantidade
        lote.status = "ativo"
        bloqueio.status = "retornado_vendavel"
        bloqueio.decisao = "retornado_vendavel"
        bloqueio.quantidade_resolvida = float(bloqueio.quantidade_bloqueada or 0)
        bloqueio.decidido_por_user_id = user_id
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio
```

- [ ] **Step 4: Create routes**

Create `backend/app/estoque_validade_routes.py`:

```python
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque_validade_models import EstoqueValidadeBloqueio
from app.estoque_validade_service import EstoqueValidadeService
from app.models import Tenant
from app.security.permissions_decorator import require_permission

router = APIRouter(prefix="/estoque/validade", tags=["Estoque - Validade"])


class DecisaoValidadePayload(BaseModel):
    observacao: Optional[str] = None


def _tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")
    return tenant


def _bloqueio(db: Session, tenant_id: str, bloqueio_id: int) -> EstoqueValidadeBloqueio:
    item = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(EstoqueValidadeBloqueio.id == bloqueio_id, EstoqueValidadeBloqueio.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Bloqueio de validade nao encontrado")
    return item


def _serializar(item: EstoqueValidadeBloqueio) -> dict:
    return {
        "id": item.id,
        "produto_id": item.produto_id,
        "produto_nome": item.produto.nome if item.produto else None,
        "lote_id": item.lote_id,
        "lote_nome": item.lote.nome_lote if item.lote else None,
        "status": item.status,
        "decisao": item.decisao,
        "data_validade": item.data_validade.isoformat() if item.data_validade else None,
        "quantidade_bloqueada": float(item.quantidade_bloqueada or 0),
        "quantidade_resolvida": float(item.quantidade_resolvida or 0),
        "custo_unitario": float(item.custo_unitario or 0),
        "custo_total_estimado": float(item.custo_total_estimado or 0),
        "observacao": item.observacao,
    }


@router.post("/processar")
@require_permission("produtos.editar")
def processar_validade(user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    current_user, tenant_id = user_and_tenant
    resultado = EstoqueValidadeService.processar_lotes_em_risco(
        db=db,
        tenant=_tenant(db, tenant_id),
        user_id=current_user.id,
    )
    db.commit()
    return {"processados": resultado["processados"], "bloqueios": [_serializar(item) for item in resultado["bloqueios"]]}


@router.get("/pendencias")
def listar_pendencias(user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    _current_user, tenant_id = user_and_tenant
    itens = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(EstoqueValidadeBloqueio.tenant_id == tenant_id, EstoqueValidadeBloqueio.status == "pendente")
        .order_by(EstoqueValidadeBloqueio.data_validade.asc())
        .all()
    )
    return {"total": len(itens), "items": [_serializar(item) for item in itens]}


@router.post("/{bloqueio_id}/descartar")
@require_permission("produtos.editar")
def descartar_bloqueio(bloqueio_id: int, payload: DecisaoValidadePayload, user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.descartar_bloqueio(db=db, tenant_id=tenant_id, user_id=current_user.id, bloqueio=_bloqueio(db, tenant_id, bloqueio_id), observacao=payload.observacao)
    db.commit()
    return _serializar(item)


@router.post("/{bloqueio_id}/trocar-fornecedor")
@require_permission("produtos.editar")
def trocar_fornecedor(bloqueio_id: int, payload: DecisaoValidadePayload, user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.trocar_com_fornecedor(db=db, tenant_id=tenant_id, user_id=current_user.id, bloqueio=_bloqueio(db, tenant_id, bloqueio_id), observacao=payload.observacao)
    db.commit()
    return _serializar(item)


@router.post("/{bloqueio_id}/retornar-vendavel")
@require_permission("produtos.editar")
def retornar_vendavel(bloqueio_id: int, payload: DecisaoValidadePayload, user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.retornar_ao_vendavel(db=db, tenant_id=tenant_id, user_id=current_user.id, bloqueio=_bloqueio(db, tenant_id, bloqueio_id), observacao=payload.observacao)
    db.commit()
    return _serializar(item)


@router.get("/pdv-alertas")
def alertas_pdv(produto_ids: list[int] = Query(default=[]), user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    _current_user, tenant_id = user_and_tenant
    if not produto_ids:
        return {"total": 0, "items": []}
    itens = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(EstoqueValidadeBloqueio.tenant_id == tenant_id, EstoqueValidadeBloqueio.status == "pendente", EstoqueValidadeBloqueio.produto_id.in_(produto_ids))
        .all()
    )
    return {"total": len(itens), "items": [_serializar(item) for item in itens]}


@router.get("/relatorio-perdas")
@require_permission("relatorios.gerencial")
def relatorio_perdas(data_inicio: Optional[datetime] = None, data_fim: Optional[datetime] = None, user_and_tenant=Depends(get_current_user_and_tenant), db: Session = Depends(get_session)):
    _current_user, tenant_id = user_and_tenant
    query = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(EstoqueValidadeBloqueio.tenant_id == tenant_id, EstoqueValidadeBloqueio.status.in_(["descartado", "trocado_fornecedor", "retornado_vendavel", "pendente"]))
    )
    if data_inicio:
        query = query.filter(EstoqueValidadeBloqueio.created_at >= data_inicio)
    if data_fim:
        query = query.filter(EstoqueValidadeBloqueio.created_at <= data_fim)
    itens = query.order_by(EstoqueValidadeBloqueio.created_at.desc()).all()
    perda_total = sum(float(item.custo_total_estimado or 0) for item in itens if item.status == "descartado")
    return {"total": len(itens), "perda_total": perda_total, "items": [_serializar(item) for item in itens]}
```

- [ ] **Step 5: Register router in main**

In `backend/app/main.py`, add import near estoque imports:

```python
from app.estoque_validade_routes import router as estoque_validade_router
```

Add include near `estoque_router`:

```python
app.include_router(estoque_validade_router, tags=["Estoque - Validade"])
```

- [ ] **Step 6: Run tests and compile**

Run: `pytest backend/tests/unit/test_estoque_validade_routes_contract.py backend/tests/unit/test_estoque_validade_service.py -q`

Expected: pass.

Run: `python -m compileall backend/app/estoque_validade_routes.py backend/app/estoque_validade_service.py backend/app/main.py`

Expected: compile succeeds.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/app/estoque_validade_routes.py backend/app/estoque_validade_service.py backend/app/main.py backend/tests/unit/test_estoque_validade_routes_contract.py
git commit -m "feat: expoe fluxo de validade do estoque"
```

## Task 4: Stock Configuration API And UI

**Files:**
- Modify: `backend/app/empresa_routes.py`
- Modify: `frontend/src/pages/configuracoes/ConfiguracaoEstoque.jsx`
- Modify: `backend/tests/unit/test_plano_basico_tenant_contract.py`

- [ ] **Step 1: Write failing backend contract test**

Append to `backend/tests/unit/test_plano_basico_tenant_contract.py`:

```python
def test_config_estoque_expoe_parametros_de_validade():
    source = _source("backend/app/empresa_routes.py")

    assert "protecao_validade_ativa" in source
    assert "dias_alerta_validade" in source
    assert "bloquear_validade_pdv" in source
    assert "bloquear_validade_ecommerce" in source
    assert "bloquear_validade_integracoes_online" in source
```

- [ ] **Step 2: Run the test and verify RED**

Run: `pytest backend/tests/unit/test_plano_basico_tenant_contract.py::test_config_estoque_expoe_parametros_de_validade -q`

Expected: fails because fields are not in `empresa_routes.py`.

- [ ] **Step 3: Extend config schemas and route**

In `backend/app/empresa_routes.py`, update `ConfigEstoqueResponse` and `ConfigEstoqueUpdate`:

```python
class ConfigEstoqueResponse(BaseModel):
    permite_estoque_negativo: bool
    protecao_validade_ativa: bool = False
    dias_alerta_validade: int = 15
    bloquear_validade_pdv: bool = True
    bloquear_validade_ecommerce: bool = True
    bloquear_validade_integracoes_online: bool = False

    class Config:
        from_attributes = True


class ConfigEstoqueUpdate(BaseModel):
    permite_estoque_negativo: bool
    protecao_validade_ativa: bool = False
    dias_alerta_validade: int = 15
    bloquear_validade_pdv: bool = True
    bloquear_validade_ecommerce: bool = True
    bloquear_validade_integracoes_online: bool = False
```

Update both response builders:

```python
return ConfigEstoqueResponse(
    permite_estoque_negativo=tenant.permite_estoque_negativo,
    protecao_validade_ativa=bool(getattr(tenant, "protecao_validade_ativa", False)),
    dias_alerta_validade=int(getattr(tenant, "dias_alerta_validade", 15) or 15),
    bloquear_validade_pdv=bool(getattr(tenant, "bloquear_validade_pdv", True)),
    bloquear_validade_ecommerce=bool(getattr(tenant, "bloquear_validade_ecommerce", True)),
    bloquear_validade_integracoes_online=bool(getattr(tenant, "bloquear_validade_integracoes_online", False)),
)
```

In the PUT handler, add:

```python
tenant.protecao_validade_ativa = bool(config.protecao_validade_ativa)
tenant.dias_alerta_validade = max(1, min(int(config.dias_alerta_validade or 15), 365))
tenant.bloquear_validade_pdv = bool(config.bloquear_validade_pdv)
tenant.bloquear_validade_ecommerce = bool(config.bloquear_validade_ecommerce)
tenant.bloquear_validade_integracoes_online = bool(config.bloquear_validade_integracoes_online)
```

- [ ] **Step 4: Update frontend config page**

In `frontend/src/pages/configuracoes/ConfiguracaoEstoque.jsx`, add state:

```javascript
const [protecaoValidadeAtiva, setProtecaoValidadeAtiva] = useState(false);
const [diasAlertaValidade, setDiasAlertaValidade] = useState(15);
const [bloquearValidadePdv, setBloquearValidadePdv] = useState(true);
const [bloquearValidadeEcommerce, setBloquearValidadeEcommerce] = useState(true);
const [bloquearValidadeIntegracoesOnline, setBloquearValidadeIntegracoesOnline] = useState(false);
```

When loading:

```javascript
setProtecaoValidadeAtiva(Boolean(res.data.protecao_validade_ativa));
setDiasAlertaValidade(Number(res.data.dias_alerta_validade || 15));
setBloquearValidadePdv(res.data.bloquear_validade_pdv !== false);
setBloquearValidadeEcommerce(res.data.bloquear_validade_ecommerce !== false);
setBloquearValidadeIntegracoesOnline(Boolean(res.data.bloquear_validade_integracoes_online));
```

When saving:

```javascript
await api.put("/empresa/config-estoque", {
  permite_estoque_negativo: permiteEstoqueNegativo,
  protecao_validade_ativa: protecaoValidadeAtiva,
  dias_alerta_validade: Math.max(1, Math.min(Number(diasAlertaValidade || 15), 365)),
  bloquear_validade_pdv: bloquearValidadePdv,
  bloquear_validade_ecommerce: bloquearValidadeEcommerce,
  bloquear_validade_integracoes_online: bloquearValidadeIntegracoesOnline,
});
```

Add a second card below stock negative control using compact labels:

```jsx
<div className="mt-6 rounded-lg bg-white p-6 shadow-md">
  <h2 className="mb-4 text-xl font-semibold text-gray-800">Protecao por validade</h2>
  <label className="mb-4 flex items-start gap-3 rounded-lg border border-gray-200 p-4">
    <input type="checkbox" checked={protecaoValidadeAtiva} onChange={(e) => setProtecaoValidadeAtiva(e.target.checked)} />
    <span>
      <span className="block font-semibold text-gray-900">Retirar da venda produtos perto do vencimento</span>
      <span className="block text-sm text-gray-600">O estoque fisico continua rastreado, mas o saldo vendavel fica protegido.</span>
    </span>
  </label>
  <label className="block text-sm font-medium text-gray-700">
    Dias antes do vencimento
    <input className="mt-1 w-full rounded-lg border px-3 py-2" min="1" max="365" type="number" value={diasAlertaValidade} onChange={(e) => setDiasAlertaValidade(e.target.value)} />
  </label>
  <div className="mt-4 grid gap-3 sm:grid-cols-3">
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={bloquearValidadePdv} onChange={(e) => setBloquearValidadePdv(e.target.checked)} /> PDV</label>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={bloquearValidadeEcommerce} onChange={(e) => setBloquearValidadeEcommerce(e.target.checked)} /> Ecommerce</label>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={bloquearValidadeIntegracoesOnline} onChange={(e) => setBloquearValidadeIntegracoesOnline(e.target.checked)} /> Integracoes online</label>
  </div>
</div>
```

- [ ] **Step 5: Run tests/build**

Run: `pytest backend/tests/unit/test_plano_basico_tenant_contract.py::test_config_estoque_expoe_parametros_de_validade -q`

Expected: pass.

Run: `npm --prefix frontend run build`

Expected: Vite production build succeeds.

- [ ] **Step 6: Commit**

Run:

```powershell
git add backend/app/empresa_routes.py frontend/src/pages/configuracoes/ConfiguracaoEstoque.jsx backend/tests/unit/test_plano_basico_tenant_contract.py
git commit -m "feat: parametriza protecao por validade"
```

## Task 5: Lembretes UI And PDV Alerts

**Files:**
- Modify: `frontend/src/pages/Lembretes.jsx`
- Modify: `frontend/src/components/pdv/PDVInfoBanners.jsx`
- Modify: `frontend/src/components/pdv/PDVMainArea.jsx`

- [ ] **Step 1: Add frontend utility test for alert message**

Create `frontend/src/components/pdv/pdvValidadeAlertUtils.js`:

```javascript
export function buildValidadePdvAlertText(alertas = []) {
  const total = Array.isArray(alertas) ? alertas.length : 0;
  if (total <= 0) return null;
  return total === 1
    ? "Conferir produtos com validade em risco. Existe lote retirado da venda aguardando decisao."
    : `Conferir produtos com validade em risco. Existem ${total} lotes retirados da venda aguardando decisao.`;
}
```

Create `frontend/src/components/pdv/pdvValidadeAlertUtils.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { buildValidadePdvAlertText } from "./pdvValidadeAlertUtils.js";

assert.equal(buildValidadePdvAlertText([]), null);
assert.equal(
  buildValidadePdvAlertText([{ id: 1 }]),
  "Conferir produtos com validade em risco. Existe lote retirado da venda aguardando decisao.",
);
assert.equal(
  buildValidadePdvAlertText([{ id: 1 }, { id: 2 }]),
  "Conferir produtos com validade em risco. Existem 2 lotes retirados da venda aguardando decisao.",
);
```

- [ ] **Step 2: Run utility test and verify RED/GREEN**

Run before creating the util file if possible: `node frontend/src/components/pdv/pdvValidadeAlertUtils.test.mjs`

Expected RED: import fails.

Create util file, then run again.

Expected GREEN: command exits 0.

- [ ] **Step 3: Add Lembretes section**

In `frontend/src/pages/Lembretes.jsx`, add state:

```javascript
const [validadePendencias, setValidadePendencias] = useState({ total: 0, items: [] });
```

Add loader:

```javascript
const carregarValidadePendencias = async () => {
  try {
    const res = await api.get("/estoque/validade/pendencias");
    setValidadePendencias({
      total: Number(res.data?.total || 0),
      items: Array.isArray(res.data?.items) ? res.data.items : [],
    });
  } catch {
    setValidadePendencias({ total: 0, items: [] });
  }
};
```

Call it in the existing `useEffect` with `carregarLembretes()`.

Add action handler:

```javascript
const decidirValidade = async (id, acao) => {
  const endpoint = {
    descartar: "descartar",
    trocar: "trocar-fornecedor",
    retornar: "retornar-vendavel",
  }[acao];
  if (!endpoint) return;
  try {
    await api.post(`/estoque/validade/${id}/${endpoint}`, { observacao: "" });
    toast.success("Pendencia de validade atualizada");
    carregarValidadePendencias();
  } catch (error) {
    toast.error(error.response?.data?.detail || "Erro ao atualizar validade");
  }
};
```

Render a compact section before recurring reminders:

```jsx
{validadePendencias.total > 0 && (
  <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
    <div className="mb-3 flex items-center justify-between gap-3">
      <div>
        <h2 className="text-base font-bold text-amber-900">Validade em risco</h2>
        <p className="text-sm text-amber-800">Produtos retirados do estoque vendavel aguardando decisao.</p>
      </div>
      <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-800">{validadePendencias.total}</span>
    </div>
    <div className="grid gap-3">
      {validadePendencias.items.map((item) => (
        <div key={item.id} className="rounded-lg border border-amber-200 bg-white p-3">
          <div className="font-semibold text-gray-900">{item.produto_nome}</div>
          <div className="text-sm text-gray-600">Lote {item.lote_nome || "-"} - {item.quantidade_bloqueada} un</div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="rounded bg-red-600 px-3 py-2 text-sm font-semibold text-white" onClick={() => decidirValidade(item.id, "descartar")}>Descartado</button>
            <button className="rounded bg-blue-600 px-3 py-2 text-sm font-semibold text-white" onClick={() => decidirValidade(item.id, "trocar")}>Trocado com fornecedor</button>
            <button className="rounded border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700" onClick={() => decidirValidade(item.id, "retornar")}>Retornar ao vendavel</button>
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 4: Render PDV banner**

In `frontend/src/components/pdv/PDVInfoBanners.jsx`, import util and add prop:

```javascript
import { buildValidadePdvAlertText } from "./pdvValidadeAlertUtils";
```

Update signature:

```javascript
export default function PDVInfoBanners({
  temCaixaAberto,
  modoVisualizacao,
  vendaAtual,
  validadeAlertas = [],
}) {
  const validadeAlertText = buildValidadePdvAlertText(validadeAlertas);
```

Render after caixa fechado:

```jsx
{validadeAlertText && !modoVisualizacao && (
  <div className="border-b border-amber-200 bg-amber-50 px-6 py-3">
    <div className="mx-auto flex max-w-5xl items-center justify-center">
      <div className="flex items-center gap-2 text-amber-900">
        <AlertCircle className="h-5 w-5" />
        <span className="text-sm font-semibold">{validadeAlertText}</span>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 5: Fetch PDV alerts in PDVMainArea**

In `frontend/src/components/pdv/PDVMainArea.jsx`, add state:

```javascript
const [validadeAlertas, setValidadeAlertas] = useState([]);
```

Add effect:

```javascript
useEffect(() => {
  const produtoIds = (vendaAtual?.itens || []).map((item) => item.produto_id).filter(Boolean);
  if (produtoIds.length === 0) {
    setValidadeAlertas([]);
    return;
  }
  api
    .get("/estoque/validade/pdv-alertas", { params: { produto_ids: produtoIds } })
    .then((res) => setValidadeAlertas(Array.isArray(res.data?.items) ? res.data.items : []))
    .catch(() => setValidadeAlertas([]));
}, [vendaAtual?.itens]);
```

Pass prop:

```jsx
<PDVInfoBanners
  temCaixaAberto={temCaixaAberto}
  modoVisualizacao={modoVisualizacao}
  vendaAtual={vendaAtual}
  validadeAlertas={validadeAlertas}
/>
```

- [ ] **Step 6: Run frontend checks**

Run: `node frontend/src/components/pdv/pdvValidadeAlertUtils.test.mjs`

Expected: exits 0.

Run: `npm --prefix frontend run build`

Expected: production build succeeds.

- [ ] **Step 7: Commit**

Run:

```powershell
git add frontend/src/pages/Lembretes.jsx frontend/src/components/pdv/PDVInfoBanners.jsx frontend/src/components/pdv/pdvValidadeAlertUtils.js frontend/src/components/pdv/pdvValidadeAlertUtils.test.mjs
git add frontend/src/components/pdv/PDVMainArea.jsx
git commit -m "feat: mostra alertas de validade em lembretes e pdv"
```

## Task 6: Ecommerce Safe Stock And Loss Report Contract

**Files:**
- Modify: `backend/app/routes/ecommerce_cart.py`
- Modify: `backend/app/routes/ecommerce_public.py`
- Modify: `backend/tests/unit/test_estoque_validade_routes_contract.py`

- [ ] **Step 1: Write contract test for report serialization**

Append to `backend/tests/unit/test_estoque_validade_routes_contract.py`:

```python
def test_serializar_validade_expoe_custo_para_relatorio():
    item = type("Bloqueio", (), {})()
    item.id = 1
    item.produto_id = 10
    item.produto = type("Produto", (), {"nome": "Racao"})()
    item.lote_id = 77
    item.lote = type("Lote", (), {"nome_lote": "L-1"})()
    item.status = "descartado"
    item.decisao = "descartado"
    item.data_validade = None
    item.quantidade_bloqueada = 3
    item.quantidade_resolvida = 3
    item.custo_unitario = 7
    item.custo_total_estimado = 21
    item.observacao = "vencido"

    payload = estoque_validade_routes._serializar(item)

    assert payload["status"] == "descartado"
    assert payload["custo_total_estimado"] == 21
    assert payload["quantidade_bloqueada"] == 3
```

- [ ] **Step 2: Run and verify GREEN**

Run: `pytest backend/tests/unit/test_estoque_validade_routes_contract.py -q`

Expected: pass after Task 3 serializer exists.

- [ ] **Step 3: Confirm ecommerce uses vendable stock**

In `backend/app/routes/ecommerce_cart.py`, keep stock checks on `Produto.estoque_atual` because Task 2 reduces it on block:

```python
estoque_disponivel = float(produto.estoque_atual or 0.0)
```

In `backend/app/routes/ecommerce_public.py`, keep catalog stock from `Produto.estoque_atual`:

```python
estoque_catalogo = func.coalesce(Produto.estoque_atual, 0)
```

If those lines already exist, add a source contract test instead of changing production files:

```python
def test_ecommerce_usa_estoque_atual_como_saldo_vendavel():
    cart = _source("backend/app/routes/ecommerce_cart.py")
    public = _source("backend/app/routes/ecommerce_public.py")

    assert "estoque_disponivel = float(produto.estoque_atual or 0.0)" in cart
    assert "estoque_catalogo = func.coalesce(Produto.estoque_atual, 0)" in public
```

- [ ] **Step 4: Run backend checks**

Run: `pytest backend/tests/unit/test_estoque_validade_routes_contract.py backend/tests/unit/test_plano_basico_tenant_contract.py -q`

Expected: pass.

Run: `python -m compileall backend/app/routes/ecommerce_cart.py backend/app/routes/ecommerce_public.py`

Expected: compile succeeds.

- [ ] **Step 5: Commit**

Run:

```powershell
git add backend/app/routes/ecommerce_cart.py backend/app/routes/ecommerce_public.py backend/tests/unit/test_estoque_validade_routes_contract.py backend/tests/unit/test_plano_basico_tenant_contract.py
git commit -m "feat: consolida estoque vendavel por validade"
```

## Task 7: Final Verification And PR Update

**Files:**
- Modify: `docs/superpowers/specs/2026-05-21-validade-estoque-bloqueio-design.md` only if implementation scope changes during execution.

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
pytest backend/tests/unit/test_estoque_validade_service.py backend/tests/unit/test_estoque_validade_routes_contract.py backend/tests/unit/test_plano_basico_tenant_contract.py -q
```

Expected: all pass.

- [ ] **Step 2: Run frontend checks**

Run:

```powershell
node frontend/src/components/pdv/pdvValidadeAlertUtils.test.mjs
npm --prefix frontend run build
```

Expected: util test exits 0 and Vite build succeeds.

- [ ] **Step 3: Run repository safety validation**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validar_fluxo.ps1 -PermitirAlteracoesLocais
```

Expected: `OK: Fluxo validado. Repositorio limpo para seguir trilho unico DEV -> PROD.`

- [ ] **Step 4: Finish branch**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "Implementa protecao de estoque por validade" -Push
```

Expected: branch pushed to origin.

- [ ] **Step 5: Update PR #182 and watch checks**

Run:

```powershell
gh pr view 182 --json url,state,headRefName,baseRefName
gh pr checks 182 --watch --interval 10
```

Expected: PR remains open, branch is `feat/20260521-0740-validade-estoque-bloqueio`, and all checks pass.

## Self-Review

- Spec coverage: config, automatic processing, reminders, PDV alert, ecommerce safe stock, discard, supplier exchange, return to vendable, and loss report are covered by Tasks 1-6.
- Scope choice: Bling/marketplace sync is prepared through safe vendable stock and config fields; channel-specific automation remains outside this MVP per design.
- Type consistency: status values used across plan are `pendente`, `descartado`, `trocado_fornecedor`, `retornado_vendavel`, `bloqueado_validade`, and `vencido_bloqueado`.
- Double-decrease guard: Task 2 discard keeps `Produto.estoque_atual` unchanged when the block already removed vendable stock.
