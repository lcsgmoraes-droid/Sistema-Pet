"""O estorno da baixa nao pode deixar beneficios gastos parcialmente desfeitos."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.campaigns import baixa_lote_reversal as reversal
from app.campaigns import sale_return_service
from app.campaigns import loyalty_service
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    LoyaltyStamp,
)
from app.vendas_models import Venda, VendaBaixaLote


def credit(identifier, amount):
    return SimpleNamespace(id=identifier, amount=Decimal(amount))


def wallet(remaining=None, expired=None):
    return SimpleNamespace(
        remaining_by_credit={
            key: Decimal(value) for key, value in (remaining or {}).items()
        },
        expected_expiration_by_credit={
            key: Decimal(value) for key, value in (expired or {}).items()
        },
    )


def test_cashback_consumido_bloqueia_estorno_integral():
    root = credit(1, "10")
    with pytest.raises(HTTPException, match="cashback.*ja foi utilizado") as exc:
        reversal._cashback_plan(
            roots=[root], credits=[root], adjustments=[], wallet=wallet({1: "4"})
        )
    assert exc.value.status_code == 409


def test_cashback_restituido_revoga_o_lote_restaurado_sem_restutuir_a_venda():
    root, restored = credit(1, "10"), credit(2, "10")
    plan = reversal._cashback_plan(
        roots=[root], credits=[root, restored], adjustments=[], wallet=wallet({2: "10"})
    )
    assert plan == [(restored, Decimal("10.00"))]


def test_cashback_expirado_nao_e_classificado_como_consumo():
    root = credit(1, "10")
    assert (
        reversal._cashback_plan(
            roots=[root],
            credits=[root],
            adjustments=[],
            wallet=wallet(expired={1: "10"}),
        )
        == []
    )


def test_estorno_anterior_e_saldo_nao_geram_estorno_duplicado():
    root = credit(1, "10")
    assert reversal._cashback_plan(
        roots=[root],
        credits=[root],
        adjustments=[credit(20, "-6")],
        wallet=wallet({1: "4"}),
    ) == [(root, Decimal("4.00"))]


def test_cashback_restaurado_e_gasto_novamente_continua_bloqueado():
    root, restored = credit(1, "10"), credit(2, "10")
    with pytest.raises(HTTPException, match="cashback.*ja foi utilizado"):
        reversal._cashback_plan(
            roots=[root], credits=[root, restored], adjustments=[], wallet=wallet()
        )


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter_by(self, **values):
        self.rows = [
            row
            for row in self.rows
            if all(getattr(row, key, None) == value for key, value in values.items())
        ]
        return self

    def filter(self, *args):
        return self

    def populate_existing(self):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, event, stamps=()):
        self.tables = {
            Venda: [SimpleNamespace(id=99, tenant_id="tenant-a", cliente_id=42)],
            CampaignEventQueue: [event],
            CampaignExecution: [],
            LoyaltyStamp: list(stamps),
        }
        self.added = []

    def query(self, model):
        return FakeQuery(list(self.tables.get(model, [])))

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass

    def commit(self):
        raise AssertionError("O helper nao pode confirmar a transacao do chamador")


def pending_event(snapshot=True):
    payload = {"venda_id": 99, "customer_id": 42}
    if snapshot:
        payload["baixa_lote_beneficios_anteriores"] = {
            "cliente_id": 42,
            "carimbos_ativos_ids": [],
            "execucoes_ids": [],
            "cupons_ativos_ids": [],
            "notificacoes_ids": [],
        }
    return SimpleNamespace(
        id=7,
        tenant_id="tenant-a",
        event_type="purchase_completed",
        status="pending",
        payload=payload,
    )


def no_wallet_side_effects(monkeypatch):
    monkeypatch.setattr(reversal, "lock_cashback_customer", lambda *a, **k: None)
    monkeypatch.setattr(reversal, "get_cashback_wallet", lambda *a, **k: wallet())
    monkeypatch.setattr(reversal, "log_action", lambda **kwargs: None)


def test_evento_pendente_e_cancelado_na_mesma_transacao_sem_beneficios(monkeypatch):
    no_wallet_side_effects(monkeypatch)
    event = pending_event()
    db = FakeDb(event)
    result = reversal.estornar_beneficios_baixa_lote(
        db, "tenant-a", 99, 7, "Baixa incorreta"
    )
    assert event.status == "skipped"
    assert event.payload["baixa_lote_estornado"] is True
    assert result["cashback_estornado"] == "0.00"
    assert db.added == []


def test_evento_de_outra_venda_bloqueia_sem_cancelar_fila(monkeypatch):
    no_wallet_side_effects(monkeypatch)
    event = pending_event()
    event.payload["venda_id"] = 101
    with pytest.raises(HTTPException, match="evento.*nao corresponde"):
        reversal.estornar_beneficios_baixa_lote(
            FakeDb(event), "tenant-a", 99, 7, "Erro"
        )
    assert event.status == "pending"
    assert not event.payload.get("baixa_lote_estornado")


def test_legado_sem_snapshot_nao_apaga_carimbo_sem_prova(monkeypatch):
    no_wallet_side_effects(monkeypatch)
    event = pending_event(snapshot=False)
    stamp = SimpleNamespace(
        id=1, tenant_id="tenant-a", venda_id=99, is_manual=False, voided_at=None
    )
    with pytest.raises(HTTPException, match="estado anterior dos beneficios"):
        reversal.estornar_beneficios_baixa_lote(
            FakeDb(event, [stamp]), "tenant-a", 99, 7, "Erro"
        )
    assert stamp.voided_at is None
    assert event.status == "pending"


def test_baixa_parcial_sem_evento_nao_consulta_nem_reverte_beneficios():
    result = reversal.estornar_beneficios_baixa_lote(None, "tenant-a", 99, None, "Erro")
    assert result["evento_id"] is None
    assert result["carimbos_estornados"] == 0


@pytest.mark.parametrize("status", ["estornado", None])
def test_worker_nao_concede_beneficio_apos_estorno_de_venda_parcial(
    monkeypatch, status
):
    venda = SimpleNamespace(
        id=99, tenant_id="tenant-a", cliente_id=42, status="baixa_parcial"
    )
    lote = (
        SimpleNamespace(id=7, tenant_id="tenant-a", status=status) if status else None
    )

    class Db:
        def query(self, model):
            if model is Venda:
                return FakeQuery([venda])
            if model is VendaBaixaLote:
                return FakeQuery([lote] if lote else [])
            raise AssertionError(
                "Um lote estornado nao pode chegar ao calculo do beneficio"
            )

    assert (
        sale_return_service.prepare_purchase_event(
            Db(),
            tenant_id="tenant-a",
            payload={"venda_id": 99, "customer_id": 42, "baixa_lote_id": 7},
        )
        is None
    )


def test_worker_aceita_lote_confirmado_preservando_referencia_do_evento(monkeypatch):
    venda = SimpleNamespace(
        id=99,
        tenant_id="tenant-a",
        cliente_id=42,
        status="finalizada",
        total=Decimal("100"),
        canal="loja_fisica",
    )
    lote = SimpleNamespace(id=7, tenant_id="tenant-a", status="confirmado")

    class Db:
        def query(self, model):
            return FakeQuery([venda] if model is Venda else [lote])

    monkeypatch.setattr(
        sale_return_service, "remaining_sale_amount", lambda *a, **k: Decimal("100")
    )
    result = sale_return_service.prepare_purchase_event(
        Db(),
        tenant_id="tenant-a",
        payload={"venda_id": 99, "customer_id": 42, "baixa_lote_id": 7},
    )
    assert result["baixa_lote_id"] == 7
    assert result["venda_total"] == 100.0


@pytest.mark.parametrize("reward_type", ["brinde", "free_gift"])
def test_brinde_bloqueia_estorno_sem_alterar_evento(monkeypatch, reward_type):
    no_wallet_side_effects(monkeypatch)
    event = pending_event()
    db = FakeDb(event)
    db.tables[CampaignExecution] = [
        SimpleNamespace(
            id=21,
            tenant_id="tenant-a",
            source_event_id=7,
            customer_id=42,
            campaign_id=3,
            reward_type=reward_type,
            reward_meta={},
        )
    ]
    db.tables[Campaign] = [SimpleNamespace(id=3, tenant_id="tenant-a")]
    with pytest.raises(HTTPException, match="brinde exige conferencia") as exc:
        reversal.estornar_beneficios_baixa_lote(db, "tenant-a", 99, 7, "Erro")
    assert exc.value.status_code == 409
    assert event.status == "pending"
    assert db.added == []


def test_fidelidade_trava_cliente_antes_de_consultar_ou_alterar_carimbos(monkeypatch):
    sequence = []
    monkeypatch.setattr(
        loyalty_service,
        "lock_cashback_customer",
        lambda *a, **k: sequence.append(("cliente", k["tenant_id"], k["customer_id"])),
    )

    class Db:
        def query(self, *args):
            sequence.append("carimbos")
            raise RuntimeError("Leitura depois do lock")

    with pytest.raises(RuntimeError, match="depois do lock"):
        loyalty_service.sync_loyalty_stamps_for_sale(
            Db(),
            campaign=SimpleNamespace(id=3, tenant_id="tenant-a", params={}),
            customer_id=42,
            venda_id=99,
            venda_total=100,
        )
    assert sequence == [("cliente", "tenant-a", 42), "carimbos"]
