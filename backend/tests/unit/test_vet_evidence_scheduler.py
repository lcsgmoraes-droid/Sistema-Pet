from app import main_background_jobs
from app.services import vet_clinical_evidence, vet_regulatory_catalog_import


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_vet_evidence_sync_config_clamps_invalid_values(monkeypatch):
    monkeypatch.setenv("VET_EVIDENCE_SYNC_STARTUP_DELAY_SECONDS", "invalido")
    monkeypatch.setenv("VET_EVIDENCE_SYNC_INTERVAL_HOURS", "0")
    monkeypatch.setenv("VET_EVIDENCE_SYNC_LIMIT", "9999")

    startup_delay, interval_seconds, limit = (
        main_background_jobs._vet_evidence_sync_config()
    )

    assert startup_delay == 300
    assert interval_seconds == 60 * 60
    assert limit == 500


def test_vet_evidence_sync_commits_eligible_import(monkeypatch):
    session = _FakeSession()
    received = {}

    monkeypatch.setattr("app.db.SessionLocal", lambda: session)

    def _fake_sync(db, **kwargs):
        received.update(kwargs)
        return {"created": 2, "updated": 0, "unchanged": 3}

    monkeypatch.setattr(
        vet_clinical_evidence,
        "sync_pubmed_veterinary_evidence",
        _fake_sync,
    )

    result = main_background_jobs._run_vet_evidence_sync_once(25)

    assert result["created"] == 2
    assert received["dry_run"] is False
    assert received["limit"] == 25
    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_vet_evidence_sync_rolls_back_on_failure(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr("app.db.SessionLocal", lambda: session)

    def _failing_sync(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(
        vet_clinical_evidence,
        "sync_pubmed_veterinary_evidence",
        _failing_sync,
    )

    try:
        main_background_jobs._run_vet_evidence_sync_once(25)
    except RuntimeError:
        pass
    else:
        raise AssertionError("sync failure should be propagated to the loop")

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True


def test_vet_regulatory_sync_imports_both_official_sources(monkeypatch):
    session = _FakeSession()
    called = []
    monkeypatch.setattr("app.db.SessionLocal", lambda: session)
    monkeypatch.setattr(
        vet_regulatory_catalog_import,
        "import_dailymed_animal_labels",
        lambda _db, **_kwargs: (
            called.append("dailymed") or {"source": "dailymed", "created": 1}
        ),
    )
    monkeypatch.setattr(
        vet_regulatory_catalog_import,
        "import_vmd_authorised_products",
        lambda _db, **_kwargs: (
            called.append("vmd") or {"source": "vmd_uk", "created": 2}
        ),
    )

    result = main_background_jobs._run_vet_regulatory_sync_once()

    assert called == ["dailymed", "vmd"]
    assert [item["source"] for item in result] == ["dailymed", "vmd_uk"]
    assert session.committed is True
    assert session.closed is True
