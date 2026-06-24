from app.schedulers import bling_sync_scheduler as scheduler_module


class _FakeDB:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_reconciliar_status_pedidos_usa_janela_configurada(monkeypatch):
    db = _FakeDB()
    capturado = {}
    scheduler = scheduler_module.BlingSyncScheduler.__new__(
        scheduler_module.BlingSyncScheduler
    )
    scheduler._should_defer_secondary_job = lambda job_name: False

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(scheduler_module, "BLING_ORDER_STATUS_RECONCILE_DAYS", 90, raising=False)
    monkeypatch.setattr(scheduler_module, "BLING_ORDER_STATUS_RECONCILE_LIMIT", 17)
    monkeypatch.setattr(
        scheduler_module,
        "executar_reconciliacao_automatica_status_pedidos",
        lambda db_arg, **kwargs: capturado.update({"db": db_arg, **kwargs}) or {},
    )

    scheduler.reconciliar_status_pedidos()

    assert capturado["db"] is db
    assert capturado["dias"] == 90
    assert capturado["limite_pedidos_por_tenant"] == 17
    assert db.closed is True


def test_reconciliar_nfes_autorizadas_usa_janela_configurada(monkeypatch):
    db = _FakeDB()
    capturado = {}
    scheduler = scheduler_module.BlingSyncScheduler.__new__(
        scheduler_module.BlingSyncScheduler
    )

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(scheduler_module, "BLING_NFE_AUTH_RECONCILE_DAYS", 90, raising=False)
    monkeypatch.setattr(scheduler_module, "BLING_NFE_AUTH_RECONCILE_LIMIT", 140)
    monkeypatch.setattr(
        scheduler_module,
        "executar_reconciliacao_automatica_nfes_autorizadas",
        lambda db_arg, **kwargs: capturado.update({"db": db_arg, **kwargs}) or {},
    )

    scheduler.reconciliar_nfes_autorizadas()

    assert capturado["db"] is db
    assert capturado["dias"] == 90
    assert capturado["limite_notas_por_tenant"] == 140
    assert db.closed is True
