from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, UploadFile

from app.models import Tenant


class SefazTenantConfigService:
    """Gerencia configuracao SEFAZ por tenant em arquivos locais."""

    BASE_DIR = Path(__file__).resolve().parents[2] / "secrets" / "sefaz"
    CONFIG_FILE = "config.json"

    @classmethod
    def _tenant_dir(cls, tenant_id: UUID) -> Path:
        tenant_dir = cls.BASE_DIR / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    @classmethod
    def _config_path(cls, tenant_id: UUID) -> Path:
        return cls._tenant_dir(tenant_id) / cls.CONFIG_FILE

    @classmethod
    def load_config(cls, tenant_id: UUID) -> dict[str, Any]:
        path = cls._config_path(tenant_id)
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Falha ao ler configuracao SEFAZ: {exc}") from exc

    @classmethod
    def save_config(cls, tenant_id: UUID, config: dict[str, Any]) -> dict[str, Any]:
        path = cls._config_path(tenant_id)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return config

    @staticmethod
    def sanitize_cnpj(cnpj: str | None) -> str:
        if not cnpj:
            return ""
        return "".join(ch for ch in str(cnpj) if ch.isdigit())

    @classmethod
    async def save_certificate(cls, tenant_id: UUID, upload: UploadFile) -> str:
        filename = upload.filename or "certificado.pfx"
        ext = Path(filename).suffix.lower()
        if ext != ".pfx":
            raise HTTPException(status_code=422, detail="Envie um certificado A1 com extensao .pfx")

        content = await upload.read()
        if not content:
            raise HTTPException(status_code=422, detail="Arquivo de certificado vazio")

        max_size_bytes = 5 * 1024 * 1024
        if len(content) > max_size_bytes:
            raise HTTPException(status_code=422, detail="Arquivo muito grande. Maximo permitido: 5MB")

        cert_name = f"cert_{secrets.token_hex(8)}.pfx"
        cert_path = cls._tenant_dir(tenant_id) / cert_name
        cert_path.write_bytes(content)
        return str(cert_path)

    @classmethod
    def build_default_config(cls, tenant: Tenant | None) -> dict[str, Any]:
        return {
            "enabled": False,
            "modo": "mock",
            "ambiente": "homologacao",
            "uf": (tenant.uf or "SP") if tenant else "SP",
            "cnpj": cls.sanitize_cnpj(tenant.cnpj if tenant else ""),
            "cert_path": "",
            "cert_password": "",
            "importacao_automatica": False,
            "importacao_intervalo_min": 15,
            "ultimo_nsu": "000000000000000",
        }

    @classmethod
    def merged_config(cls, tenant_id: UUID, tenant: Tenant | None) -> dict[str, Any]:
        data = cls.build_default_config(tenant)
        data.update(cls.load_config(tenant_id))
        data["cnpj"] = cls.sanitize_cnpj(data.get("cnpj"))
        if data.get("uf"):
            data["uf"] = str(data["uf"]).strip().upper()
        return data
