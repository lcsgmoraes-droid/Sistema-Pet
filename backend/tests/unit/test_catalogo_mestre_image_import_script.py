import json

from app.scripts import run_catalogo_mestre_image_import


class _FakeSession:
    def rollback(self):
        pass

    def commit(self):
        pass

    def close(self):
        pass


def test_image_import_script_defaults_to_dry_run(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(run_catalogo_mestre_image_import, "SessionLocal", _FakeSession)
    monkeypatch.setattr(
        run_catalogo_mestre_image_import,
        "prepare_image_import",
        lambda *_args, **_kwargs: [],
    )

    code = run_catalogo_mestre_image_import.main(["--source-dir", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["dry_run"] is True
    assert payload["imagens_estagiadas"] == 0
    assert payload["imagens_publicadas"] == 0
    assert payload["produtos_criados"] == 0
    assert payload["cadastros_de_lojas_alterados"] == 0


def test_image_import_script_blocks_production_apply(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")

    code = run_catalogo_mestre_image_import.main(
        ["--source-dir", str(tmp_path), "--apply"]
    )
    payload = json.loads(capsys.readouterr().err)

    assert code == 1
    assert payload["dry_run"] is False
    assert "--allow-production-apply" in payload["error"]
