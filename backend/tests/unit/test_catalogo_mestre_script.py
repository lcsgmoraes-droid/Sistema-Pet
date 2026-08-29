import json

from app.scripts import run_catalogo_mestre_sync

SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"


class _FakeSession:
    def rollback(self):
        pass

    def commit(self):
        pass

    def close(self):
        pass


def test_catalogo_mestre_script_defaults_to_dry_run(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(run_catalogo_mestre_sync, "SessionLocal", _FakeSession)
    monkeypatch.setattr(
        run_catalogo_mestre_sync,
        "_resolve_source_tenant_id",
        lambda _db, _email: SOURCE_TENANT,
    )

    def fake_sync(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "dry_run": kwargs["dry_run"], "image_target": 5}

    monkeypatch.setattr(
        run_catalogo_mestre_sync, "sync_catalogo_mestre_from_tenant", fake_sync
    )

    code = run_catalogo_mestre_sync.main([])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["dry_run"] is True
    assert calls[0]["source_tenant_id"] == SOURCE_TENANT
    assert calls[0]["image_target"] == 5


def test_catalogo_mestre_script_blocks_production_apply(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = run_catalogo_mestre_sync.main(["--apply"])
    payload = json.loads(capsys.readouterr().err)

    assert code == 1
    assert payload["dry_run"] is False
    assert "--allow-production-apply" in payload["error"]


def test_catalogo_mestre_script_rejects_other_source(monkeypatch, capsys):
    code = run_catalogo_mestre_sync.main(["--source-email", "outra-loja@example.com"])
    payload = json.loads(capsys.readouterr().err)

    assert code == 1
    assert "somente o Atacadao" in payload["error"]
