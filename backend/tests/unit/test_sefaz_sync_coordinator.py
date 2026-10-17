import json
import threading
from datetime import datetime, timedelta, timezone

import pytest

from app.services.sefaz_service import SefazConsumoIndevidoError, SefazService
from app.services.sefaz_sync_coordinator import SefazSyncCoordinator


class _FakeSession:
    def close(self):
        pass


@pytest.fixture(autouse=True)
def _retry_local_sem_pendencias(monkeypatch):
    from app import db as db_module
    from app.notas_entrada import sefaz_importer

    monkeypatch.setattr(db_module, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(
        sefaz_importer,
        "reprocessar_documentos_sefaz_pendentes",
        lambda db, tenant_id_str: {"importadas": 0, "duplicadas": 0, "erros": 0},
    )


def _cfg():
    return {
        "ultimo_nsu": "000000000000009",
        "importacao_intervalo_min": 15,
    }


def _resultado(ultimo_nsu, max_nsu, docs, c_stat="138"):
    return {
        "ultimo_nsu": ultimo_nsu,
        "max_nsu": max_nsu,
        "docs_list": docs,
        "c_stat": c_stat,
        "x_motivo": "ok",
    }


def test_salvar_configuracao_espera_envio_em_andamento():
    coordinator = SefazSyncCoordinator()
    configuracao_salva = threading.Event()
    falhas = []

    def salvar():
        try:
            with coordinator.email_and_config_guard():
                configuracao_salva.set()
        except Exception as exc:
            falhas.append(exc)

    with coordinator.email_guard():
        worker = threading.Thread(target=salvar)
        worker.start()
        assert not configuracao_salva.wait(0.1)

    worker.join(timeout=2)
    assert not worker.is_alive()
    assert not falhas
    assert configuracao_salva.is_set()


def test_erro_656_preserva_checkpoint(tmp_path, monkeypatch):
    from app.notas_entrada import sefaz_importer

    reprocessamentos = []
    monkeypatch.setattr(
        sefaz_importer,
        "reprocessar_documentos_sefaz_pendentes",
        lambda db, tenant_id_str: (
            reprocessamentos.append(tenant_id_str)
            or {"importadas": 1, "duplicadas": 0, "erros": 0}
        ),
    )

    def _rejeitar(_cls, config, ultimo_nsu):
        raise SefazConsumoIndevidoError(
            "cStat 656", "000000000000040", "000000000000050"
        )

    monkeypatch.setattr(SefazService, "sincronizar_nsu", classmethod(_rejeitar))
    path = tmp_path / "config.json"
    resultado = SefazSyncCoordinator()._execute("tenant", path, _cfg(), "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))

    assert resultado["status"] == "erro_656"
    assert salvo["ultimo_nsu"] == "000000000000009"
    assert salvo["ultimo_sync_ult_nsu_retorno"] == "000000000000040"
    assert salvo["ultimo_sync_max_nsu_retorno"] == "000000000000050"
    assert reprocessamentos == ["tenant"]


def test_falha_no_staging_nao_avanca_checkpoint(tmp_path, monkeypatch):
    from app import db as db_module
    from app.notas_entrada import sefaz_importer

    monkeypatch.setattr(db_module, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(
        SefazService,
        "sincronizar_nsu",
        classmethod(
            lambda _cls, config, ultimo_nsu: _resultado(
                "000000000000010",
                "000000000000020",
                [{"nsu": "000000000000010", "schema": "resNFe", "xml": "<resNFe/>"}],
            )
        ),
    )

    def _falhar_staging(db, tenant_id_str, docs):
        raise RuntimeError("banco indisponivel")

    monkeypatch.setattr(
        sefaz_importer, "importar_documentos_distribuicao", _falhar_staging
    )
    path = tmp_path / "config.json"
    resultado = SefazSyncCoordinator()._execute("tenant", path, _cfg(), "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))

    assert resultado["status"] == "error"
    assert salvo["ultimo_nsu"] == "000000000000009"
    assert salvo["ultimo_sync_max_nsu_retorno"] == "000000000000020"


@pytest.mark.parametrize(
    ("max_nsu", "docs", "c_stat", "espera_minutos"),
    [
        ("000000000000020", [{"nsu": "000000000000010"}], "138", 10),
        ("000000000000010", [{"nsu": "000000000000010"}], "138", 65),
        ("000000000000009", [], "137", 65),
    ],
)
def test_cadencia_por_backlog_e_max_nsu(
    tmp_path, monkeypatch, max_nsu, docs, c_stat, espera_minutos
):
    from app import db as db_module
    from app.notas_entrada import sefaz_importer

    monkeypatch.setattr(db_module, "SessionLocal", lambda: _FakeSession())
    ultimo_nsu = "000000000000010" if docs else "000000000000009"
    monkeypatch.setattr(
        SefazService,
        "sincronizar_nsu",
        classmethod(
            lambda _cls, config, ultimo_nsu: _resultado(
                "000000000000010" if docs else "000000000000009",
                max_nsu,
                docs,
                c_stat,
            )
        ),
    )
    monkeypatch.setattr(
        sefaz_importer,
        "importar_documentos_distribuicao",
        lambda db, tenant_id_str, documents: {
            "staging_salvo": True,
            "documentos_salvos": len(documents),
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
        },
    )
    path = tmp_path / "config.json"
    inicio = datetime.now(timezone.utc)
    resultado = SefazSyncCoordinator()._execute("tenant", path, _cfg(), "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))
    proximo = datetime.fromisoformat(salvo["_proximo_sync_permitido_at"])

    assert resultado["status"] == "ok"
    assert salvo["ultimo_nsu"] == ultimo_nsu
    assert inicio + timedelta(minutes=espera_minutos) <= proximo
    assert proximo <= datetime.now(timezone.utc) + timedelta(minutes=espera_minutos)


@pytest.mark.parametrize(
    ("novo_nsu", "max_nsu", "docs"),
    [
        ("000000000000008", "000000000000020", []),
        ("000000000000021", "000000000000020", []),
        ("NSU-invalidado", "000000000000020", []),
        ("000000000000010", "000000000000020", [{"nsu": "000000000000011"}]),
        ("000000000000010", "000000000000020", [{"nsu": ""}]),
    ],
)
def test_resposta_com_nsu_inconsistente_preserva_checkpoint(
    tmp_path, monkeypatch, novo_nsu, max_nsu, docs
):
    monkeypatch.setattr(
        SefazService,
        "sincronizar_nsu",
        classmethod(
            lambda _cls, config, ultimo_nsu: _resultado(novo_nsu, max_nsu, docs)
        ),
    )
    path = tmp_path / "config.json"
    resultado = SefazSyncCoordinator()._execute("tenant", path, _cfg(), "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))

    assert resultado["status"] == "error"
    assert salvo["ultimo_nsu"] == "000000000000009"
    assert not salvo.get("ultimo_max_nsu_confirmado")


@pytest.mark.parametrize(
    ("c_stat", "novo_nsu", "docs"),
    [
        ("138", "000000000000010", []),
        ("138", "000000000000011", [{"nsu": "000000000000010"}]),
        (
            "138",
            "000000000000012",
            [{"nsu": "000000000000010"}, {"nsu": "000000000000012"}],
        ),
        ("137", "000000000000010", []),
    ],
)
def test_resposta_parcial_nao_avanca_checkpoint(
    tmp_path, monkeypatch, c_stat, novo_nsu, docs
):
    monkeypatch.setattr(
        SefazService,
        "sincronizar_nsu",
        classmethod(
            lambda _cls, config, ultimo_nsu: _resultado(
                novo_nsu, "000000000000020", docs, c_stat
            )
        ),
    )
    path = tmp_path / "config.json"
    resultado = SefazSyncCoordinator()._execute("tenant", path, _cfg(), "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))

    assert resultado["status"] == "error"
    assert salvo["ultimo_nsu"] == "000000000000009"


def test_max_nsu_zero_nao_vira_max_confirmado(tmp_path, monkeypatch):
    config = _cfg()
    config["ultimo_nsu"] = "000000000000000"
    monkeypatch.setattr(
        SefazService,
        "sincronizar_nsu",
        classmethod(
            lambda _cls, config, ultimo_nsu: _resultado(
                "000000000000000", "000000000000000", [], "137"
            )
        ),
    )
    path = tmp_path / "config.json"
    resultado = SefazSyncCoordinator()._execute("tenant", path, config, "teste")
    salvo = json.loads(path.read_text(encoding="utf-8"))

    assert resultado["status"] == "ok"
    assert salvo["ultimo_max_nsu_confirmado"] is None


@pytest.mark.parametrize("reason", ["scheduler", "manual"])
def test_try_sync_recarrega_cursor_sob_lock(tmp_path, monkeypatch, reason):
    cert = tmp_path / "cert.pfx"
    cert.write_bytes(b"teste")
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "modo": "real",
                "importacao_automatica": True,
                "cert_path": str(cert),
                "ultimo_nsu": "000000000000020",
            }
        ),
        encoding="utf-8",
    )
    recebido = []
    coordinator = SefazSyncCoordinator()
    monkeypatch.setattr(
        coordinator,
        "_execute",
        lambda tenant, config_path, cfg, motivo: (
            recebido.append(cfg["ultimo_nsu"]) or {"status": "ok"}
        ),
    )

    result = coordinator.try_sync(
        "tenant", path, {**_cfg(), "enabled": True, "modo": "real"}, reason
    )

    assert result["status"] == "ok"
    assert recebido == ["000000000000020"]


def test_try_sync_revalida_cooldown_e_flag_sob_lock(tmp_path, monkeypatch):
    cert = tmp_path / "cert.pfx"
    cert.write_bytes(b"teste")
    path = tmp_path / "config.json"
    base = {
        "enabled": True,
        "modo": "real",
        "importacao_automatica": True,
        "cert_path": str(cert),
        "ultimo_nsu": "000000000000020",
    }
    path.write_text(
        json.dumps(
            {
                **base,
                "ultimo_sync_at": datetime.now(timezone.utc).isoformat(),
                "ultimo_sync_cstat": "137",
                "_proximo_sync_permitido_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    coordinator = SefazSyncCoordinator()
    monkeypatch.setattr(
        coordinator,
        "_execute",
        lambda *args: pytest.fail("Nao deve chamar SEFAZ em cooldown"),
    )
    assert (
        coordinator.try_sync("tenant", path, base, "scheduler")["status"] == "cooldown"
    )

    path.write_text(
        json.dumps({**base, "importacao_automatica": False}), encoding="utf-8"
    )
    assert (
        coordinator.try_sync("tenant", path, base, "scheduler")["status"] == "disabled"
    )
