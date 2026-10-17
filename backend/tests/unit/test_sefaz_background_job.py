import json
from datetime import datetime, timezone

import pytest

from app import main_background_jobs
from app.services.sefaz_sync_coordinator import sefaz_coordinator
from app.services.sefaz_tenant_config_service import SefazTenantConfigService


class _UmaIteracao:
    def __init__(self):
        self.parar = False

    def wait(self, segundos):
        if segundos == 600:
            self.parar = True

    def is_set(self):
        return self.parar


@pytest.mark.parametrize("habilitada", [False, True])
def test_scheduler_consulta_apenas_tenant_com_flag_ativa(
    tmp_path, monkeypatch, habilitada
):
    tenant_dir = tmp_path / "11111111-1111-4111-8111-111111111111"
    tenant_dir.mkdir()
    certificado = tenant_dir / "cert.pfx"
    certificado.write_bytes(b"certificado-de-teste")
    (tenant_dir / "config.json").write_text(
        json.dumps(
            {
                "importacao_automatica": habilitada,
                "enabled": True,
                "modo": "real",
                "cert_path": str(certificado),
                "ultimo_nsu": "000000000000000",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(SefazTenantConfigService, "BASE_DIR", tmp_path)
    monkeypatch.setattr(main_background_jobs, "_sefaz_sync_stop_event", _UmaIteracao())
    chamadas = []
    monkeypatch.setattr(
        sefaz_coordinator,
        "try_sync",
        lambda **kwargs: chamadas.append(kwargs) or {"status": "ok"},
    )

    main_background_jobs._loop_sefaz_sync()

    assert len(chamadas) == int(habilitada)


def test_scheduler_reprocessa_staging_local_durante_cooldown(tmp_path, monkeypatch):
    tenant_dir = tmp_path / "11111111-1111-4111-8111-111111111111"
    tenant_dir.mkdir()
    (tenant_dir / "config.json").write_text(
        json.dumps(
            {
                "importacao_automatica": True,
                "enabled": True,
                "modo": "real",
                "ultimo_sync_at": datetime.now(timezone.utc).isoformat(),
                "ultimo_sync_cstat": "137",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(SefazTenantConfigService, "BASE_DIR", tmp_path)
    monkeypatch.setattr(main_background_jobs, "_sefaz_sync_stop_event", _UmaIteracao())
    chamadas = []
    monkeypatch.setattr(
        sefaz_coordinator,
        "try_reprocess_local",
        lambda tenant_id, path: chamadas.append((tenant_id, path)),
    )
    monkeypatch.setattr(
        sefaz_coordinator,
        "try_sync",
        lambda **kwargs: pytest.fail("Nao deve consultar SEFAZ durante cooldown"),
    )

    main_background_jobs._loop_sefaz_sync()

    assert chamadas == [(tenant_dir.name, tenant_dir / "config.json")]
