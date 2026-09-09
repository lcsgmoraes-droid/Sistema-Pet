"""Carteira isolada em SQLite: sem banco configurado, rede ou provedor pago."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.creditos_models import CreditoLedgerEntry, CreditoOperation, CreditoWallet
from app.services import creditos_service as service
from app.services.creditos_catalog import CreditosError, get_catalog, get_creditos_mode
from app.tenancy.context import clear_current_tenant, tenant_context


TENANT_A = "b0f1840d-79b7-466d-8cf6-8ccf1ad9ef87"
TENANT_B = "f91b4604-6b14-4589-ac6b-242d0d5a58dc"
ACTOR = 1
SERVICE = "produto.descricao_fiscal"
PAYLOAD = {"nome": "Ração teste", "ean": "7890000000000"}


def _isolated_engine(path):
    metadata = MetaData()
    Table("tenants", metadata, Column("id", String(36), primary_key=True))
    Table("users", metadata, Column("id", Integer, primary_key=True))
    for model in (CreditoWallet, CreditoOperation, CreditoLedgerEntry):
        model.__table__.to_metadata(metadata)
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"timeout": 10, "check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            metadata.tables["tenants"].insert(), [{"id": TENANT_A}, {"id": TENANT_B}]
        )
        connection.execute(
            metadata.tables["users"].insert(), [{"id": ACTOR}, {"id": 2}]
        )
    return engine, metadata


@pytest.fixture
def db_case(tmp_path, monkeypatch):
    clear_current_tenant()
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    monkeypatch.setenv("COREPET_CREDITOS_TENANT_ALLOWLIST", f"{TENANT_A},{TENANT_B}")
    engine, metadata = _isolated_engine(tmp_path / "credits-only.sqlite")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db, factory, engine, metadata
    clear_current_tenant()
    engine.dispose()


def _seed(db_case, credits=500, tenant=TENANT_A):
    """Saldo exclusivamente de fixture; nenhuma API pública concede créditos."""
    _, _, engine, metadata = db_case
    with engine.begin() as connection:
        connection.execute(
            metadata.tables["creditos_wallets"].insert(),
            {
                "tenant_id": UUID(tenant),
                "available_credits": credits,
                "reserved_credits": 0,
                "version": 0,
            },
        )


def _quote(db, *, tenant=TENANT_A, actor=ACTOR, code=SERVICE, payload=None, key=None):
    return service.quote(
        db, tenant, actor, code, payload or PAYLOAD, idempotency_key=key or str(uuid4())
    )


def _start(db, quote, *, tenant=TENANT_A, actor=ACTOR, payload=None):
    return service.start_operation(
        db,
        tenant,
        actor,
        quote["operation_id"],
        quote["service_code"],
        payload or PAYLOAD,
    )


def _count(db_case, table):
    _, _, engine, metadata = db_case
    with engine.connect() as connection:
        return len(connection.execute(select(metadata.tables[table])).all())


def test_mode_requires_allowlist_and_invalid_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("COREPET_CREDITOS_MODE", raising=False)
    monkeypatch.delenv("COREPET_CREDITOS_TENANT_ALLOWLIST", raising=False)
    assert get_creditos_mode(TENANT_A) == "off"
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    assert get_creditos_mode(TENANT_A) == "off"
    monkeypatch.setenv("COREPET_CREDITOS_TENANT_ALLOWLIST", TENANT_A)
    assert get_creditos_mode(TENANT_A) == "enforced"
    assert get_creditos_mode(TENANT_B) == "off"
    monkeypatch.setenv("COREPET_CREDITOS_TENANT_ALLOWLIST", "*")
    with pytest.raises(CreditosError, match="lista de empresas"):
        get_creditos_mode(TENANT_A)
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "typo")
    with pytest.raises(CreditosError) as error:
        get_creditos_mode(TENANT_A)
    assert error.value.status_code == 503


def test_catalog_exposes_draft_not_provider_cost_or_checkout(db_case):
    catalog = get_catalog(TENANT_A)
    assert catalog["credit_unit_cents"] == 2
    assert catalog["checkout_enabled"] is False
    assert catalog["draft"] is True
    active = {row["service_code"]: row for row in catalog["services"] if row["enabled"]}
    assert active[SERVICE]["credits"] == 125
    assert active[SERVICE]["price_cents"] == 250
    assert active["oferta.imagem"]["credits"] == 150
    assert "estimated_cost" not in str(catalog)
    with pytest.raises(CreditosError) as error:
        _quote(db_case[0], code="produto.fiscal")
    assert error.value.code == "credit_service_disabled"


def test_quote_replay_payload_order_and_no_seed(db_case):
    db = db_case[0]
    key = str(uuid4())
    first = _quote(db, key=key)
    repeat = _quote(
        db, key=key, payload={"ean": PAYLOAD["ean"], "nome": PAYLOAD["nome"]}
    )
    assert first["operation_id"] == repeat["operation_id"]
    assert _count(db_case, "creditos_operations") == 1
    assert _count(db_case, "creditos_wallets") == 0
    assert _count(db_case, "creditos_ledger") == 0
    assert service.get_wallet(db, TENANT_A)["available_credits"] == 0
    assert _count(db_case, "creditos_wallets") == 0


@pytest.mark.parametrize("change", ["payload", "service", "actor"])
def test_quote_rejects_same_key_for_different_request(db_case, change):
    db = db_case[0]
    key = str(uuid4())
    _quote(db, key=key)
    kwargs = (
        {"payload": {"nome": "Outra ração"}}
        if change == "payload"
        else ({"code": "oferta.imagem"} if change == "service" else {"actor": 2})
    )
    with pytest.raises(CreditosError) as error:
        _quote(db, key=key, **kwargs)
    assert error.value.code == "idempotency_conflict"


def test_start_reserves_once_complete_captures_once_and_replays_result(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    assert _start(db, quoted)["should_execute"] is True
    assert _start(db, quoted)["should_execute"] is False
    assert service.get_wallet(db, TENANT_A)["available_credits"] == 375
    assert service.get_wallet(db, TENANT_A)["reserved_credits"] == 125
    first = service.complete_operation(
        db,
        TENANT_A,
        ACTOR,
        quoted["operation_id"],
        result_payload={"descricao": "resultado salvo"},
    )
    second = service.complete_operation(
        db,
        TENANT_A,
        ACTOR,
        quoted["operation_id"],
        result_payload={"descricao": "não substitui"},
    )
    assert (
        first["result_payload"]
        == second["result_payload"]
        == {"descricao": "resultado salvo"}
    )
    assert _start(db, quoted)["should_execute"] is False
    wallet = service.get_wallet(db, TENANT_A)
    assert (wallet["available_credits"], wallet["reserved_credits"]) == (375, 0)
    entries = service.get_ledger(db, TENANT_A)["items"]
    assert sorted(row["kind"] for row in entries) == ["capture", "reserve"]


def test_shadow_tracks_hypothetical_usage_without_wallet_or_debit(db_case, monkeypatch):
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "shadow")
    db = db_case[0]
    quoted = _quote(db)
    assert _start(db, quoted)["should_execute"] is True
    service.complete_operation(
        db, TENANT_A, ACTOR, quoted["operation_id"], result_payload={"ok": True}
    )
    assert _count(db_case, "creditos_wallets") == 0
    (entry,) = service.get_ledger(db, TENANT_A)["items"]
    assert entry["kind"] == "shadow_usage"
    assert entry["credits"] == 125
    assert entry["available_delta"] == entry["reserved_delta"] == 0
    assert entry["available_after"] is None


def test_definite_failure_releases_once_and_preserves_usage_cost(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    _start(db, quoted)
    failed = service.fail_operation(
        db,
        TENANT_A,
        ACTOR,
        quoted["operation_id"],
        failure_code="invalid_result",
        definite_failure=True,
        usage_metadata={"response_received": True, "input_tokens": 10},
    )
    service.fail_operation(
        db,
        TENANT_A,
        ACTOR,
        quoted["operation_id"],
        failure_code="invalid_result",
        definite_failure=True,
    )
    assert failed["status"] == "failed"
    assert failed["usage_metadata"]["input_tokens"] == 10
    assert _start(db, quoted)["should_execute"] is False
    wallet = service.get_wallet(db, TENANT_A)
    assert (wallet["available_credits"], wallet["reserved_credits"]) == (500, 0)
    assert _count(db_case, "creditos_ledger") == 2


def test_unknown_outcome_never_releases_or_reexecutes_until_reconciled(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    _start(db, quoted)
    pending = service.fail_operation(
        db, TENANT_A, ACTOR, quoted["operation_id"], failure_code="provider_timeout"
    )
    assert pending["status"] == "uncertain"
    assert _start(db, quoted)["should_execute"] is False
    assert service.get_wallet(db, TENANT_A)["reserved_credits"] == 125
    result = service.complete_operation(
        db, TENANT_A, ACTOR, quoted["operation_id"], result_payload={"ok": True}
    )
    assert result["status"] == "completed"
    assert service.get_wallet(db, TENANT_A)["reserved_credits"] == 0


def test_insufficient_balance_rolls_back_claim_without_creating_wallet(db_case):
    db = db_case[0]
    quoted = _quote(db)
    with pytest.raises(CreditosError) as error:
        _start(db, quoted)
    assert error.value.code == "insufficient_credits"
    assert error.value.status_code == 402
    assert (
        service.get_operation(db, TENANT_A, ACTOR, quoted["operation_id"])["status"]
        == "quoted"
    )
    assert (
        _count(db_case, "creditos_wallets") == _count(db_case, "creditos_ledger") == 0
    )


def test_expiry_mode_and_changed_payload_block_execution(db_case, monkeypatch):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    with pytest.raises(CreditosError) as error:
        _start(db, quoted, payload={"changed": True})
    assert error.value.code == "operation_payload_mismatch"
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "shadow")
    with pytest.raises(CreditosError) as error:
        _start(db, quoted)
    assert error.value.code == "credit_mode_changed"
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    with tenant_context(TENANT_A):
        db.execute(
            update(CreditoOperation)
            .where(CreditoOperation.id == quoted["operation_id"])
            .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
        db.commit()
    with pytest.raises(CreditosError) as error:
        _start(db, quoted)
    assert error.value.code == "quote_expired"
    assert service.get_wallet(db, TENANT_A)["available_credits"] == 500


def test_tenant_actor_and_context_isolation_with_uuid_object(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db, tenant=UUID(TENANT_A))
    for tenant, actor in ((TENANT_B, ACTOR), (TENANT_A, 2)):
        with pytest.raises(CreditosError) as error:
            service.get_operation(db, tenant, actor, quoted["operation_id"])
        assert error.value.code == "operation_not_found"
    assert service.get_wallet(db, TENANT_B)["available_credits"] == 0
    assert service.get_ledger(db, TENANT_B)["items"] == []
    with tenant_context(TENANT_B):
        with pytest.raises(CreditosError) as error:
            service.get_wallet(db, TENANT_A)
        assert error.value.code == "tenant_mismatch"


def test_metadata_allowlist_and_request_privacy(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    _start(db, quoted)
    result = service.complete_operation(
        db,
        TENANT_A,
        ACTOR,
        quoted["operation_id"],
        result_payload={"ok": True},
        usage_metadata={
            "provider": "openai",
            "model": "test-model",
            "provider_response_id": "resp_test",
            "input_tokens": 10,
            "web_search_calls": 1,
            "image_tokens": 5,
            "prompt": "raw secret prompt",
            "api_key": "sk-secret",
            "error": "raw exception",
            "provider_cost_cents": 1,
            "total_tokens": -1,
        },
    )
    usage = result["usage_metadata"]
    assert usage["input_tokens"] == 10
    assert usage["web_search_calls"] == 1
    assert usage["provider_cost_cents"] is None
    assert usage["provider_cost_status"] == "not_reconciled"
    assert not {"prompt", "api_key", "error", "total_tokens"} & usage.keys()
    _, _, engine, metadata = db_case
    with engine.connect() as connection:
        op_row = (
            connection.execute(select(metadata.tables["creditos_operations"]))
            .mappings()
            .one()
        )
    assert "Ração teste" not in str(op_row)
    assert len(op_row["request_fingerprint"]) == 64
    assert "usage" not in str(service.get_ledger(db, TENANT_A))


def test_oversized_or_non_json_payload_is_rejected(db_case):
    with pytest.raises(CreditosError) as error:
        _quote(db_case[0], payload={"value": "x" * (service.MAX_PAYLOAD_BYTES + 1)})
    assert error.value.status_code == 413
    with pytest.raises(CreditosError):
        _quote(db_case[0], payload={"bad": float("nan")})


def test_ledger_orm_immutable_and_database_no_negative(db_case):
    db = db_case[0]
    _seed(db_case)
    quoted = _quote(db)
    _start(db, quoted)
    with tenant_context(TENANT_A):
        entry = db.execute(select(CreditoLedgerEntry)).scalar_one()
        entry.title = "alterado"
        with pytest.raises(ValueError, match="imutável"):
            db.commit()
        db.rollback()
    _, _, engine, metadata = db_case
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                update(metadata.tables["creditos_wallets"]).values(available_credits=-1)
            )


@pytest.mark.parametrize("same_operation", [True, False])
def test_concurrent_starts_never_double_spend(db_case, same_operation):
    db, factory, _, _ = db_case
    _seed(db_case, credits=125)
    first = _quote(db)
    second = first if same_operation else _quote(db)
    db.rollback()  # leitura pós-cotação não segura transação durante workers
    barrier = Barrier(2)

    def run(quoted):
        clear_current_tenant()
        with factory() as worker_db:
            barrier.wait(timeout=5)
            try:
                return _start(worker_db, quoted)["should_execute"]
            except CreditosError as exc:
                assert exc.code == "insufficient_credits"
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, (first, second)))
    assert results.count(True) == 1
    wallet = service.get_wallet(db, TENANT_A)
    assert (wallet["available_credits"], wallet["reserved_credits"]) == (0, 125)
    assert _count(db_case, "creditos_ledger") == 1
