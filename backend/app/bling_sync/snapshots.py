from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SNAPSHOT_STORAGE_DATA_DIR = Path("/app/data/bling_snapshots")
_SNAPSHOT_STORAGE_UPLOADS_DIR = Path("/app/uploads/bling_snapshots")
_SNAPSHOT_STORAGE_LOCAL_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "bling_snapshots"
)
_SNAPSHOT_FILE_NAMES = {
    "catalogo": "catalogo.json",
    "cobertura": "cobertura.json",
    "faltantes": "faltantes.json",
    "sem_vinculo": "sem_vinculo.json",
}


def _snapshot_storage_candidates() -> list[Path]:
    return [
        _SNAPSHOT_STORAGE_DATA_DIR,
        _SNAPSHOT_STORAGE_UPLOADS_DIR,
        _SNAPSHOT_STORAGE_LOCAL_DIR,
    ]


def _resolver_snapshot_storage_base() -> Path:
    vistos: set[str] = set()
    for candidato in _snapshot_storage_candidates():
        chave = str(candidato.resolve(strict=False))
        if chave in vistos:
            continue
        vistos.add(chave)

        try:
            candidato.mkdir(parents=True, exist_ok=True)
            teste = candidato / ".write_test"
            teste.write_text("ok", encoding="utf-8")
            teste.unlink(missing_ok=True)
            logger.info("Snapshots compartilhados do Bling em %s", candidato)
            return candidato
        except Exception as error:
            logger.warning(
                "Snapshot compartilhado indisponivel em %s: %s", candidato, error
            )

    logger.warning(
        "Nenhum diretorio de snapshot compartilhado ficou gravavel. Usando local %s",
        _SNAPSHOT_STORAGE_LOCAL_DIR,
    )
    return _SNAPSHOT_STORAGE_LOCAL_DIR


_SNAPSHOT_STORAGE_BASE = _resolver_snapshot_storage_base()


def _snapshot_tenant_dir_name(tenant_id: int) -> str:
    raw_tenant = str(tenant_id).strip()
    if not raw_tenant:
        raise ValueError("Tenant invalido para caminho de snapshot")
    digest = hashlib.sha256(raw_tenant.encode("utf-8")).hexdigest()[:32]
    return f"tenant_{digest}"


def _snapshot_file_path(snapshot_name: str, tenant_id: int) -> Path:
    snapshot_file_name = _SNAPSHOT_FILE_NAMES.get(snapshot_name)
    if snapshot_file_name is None:
        raise ValueError("Nome de snapshot invalido")

    return (
        _SNAPSHOT_STORAGE_BASE
        / _snapshot_tenant_dir_name(tenant_id)
        / snapshot_file_name
    )


def _read_shared_snapshot(snapshot_name: str, tenant_id: int) -> Optional[dict]:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Falha ao ler snapshot compartilhado", exc_info=True)
        return None

    if not isinstance(data, dict) or not isinstance(data.get("payload"), dict):
        return None
    return data


def _write_shared_snapshot(snapshot_name: str, tenant_id: int, payload: dict) -> None:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "ts_epoch": time.time(),
            "payload": payload,
        }
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, default=str, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(temp_path, path)
    except Exception:
        logger.warning("Falha ao gravar snapshot compartilhado", exc_info=True)


def _delete_shared_snapshot(snapshot_name: str, tenant_id: int) -> None:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except Exception as error:
        logger.warning(
            "Falha ao remover snapshot compartilhado %s do tenant %s: %s",
            snapshot_name,
            tenant_id,
            error,
        )


def _shared_snapshot_age_seconds(snapshot_record: Optional[dict]) -> int:
    if not snapshot_record:
        return 0

    try:
        ts_epoch = float(snapshot_record.get("ts_epoch") or 0)
    except Exception:
        ts_epoch = 0

    if ts_epoch <= 0:
        return 0
    return int(max(time.time() - ts_epoch, 0))
