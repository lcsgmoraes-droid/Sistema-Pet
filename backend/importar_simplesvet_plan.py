"""Plano imutavel e validacoes do importador SimplesVet.

Este modulo nao acessa o banco. Ele valida os CSVs, gera fingerprints e garante
que o ``apply`` use exatamente os mesmos arquivos aprovados no ``plan``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url


PLAN_VERSION = 1
PLAN_TTL = timedelta(hours=24)
PRODUCTION_ENVS = {"prod", "production"}
LOCAL_DATABASE_HOSTS = {"", "local", "localhost", "127.0.0.1", "::1"}

FILE_COLUMNS: dict[str, set[str]] = {
    "vet_especie.csv": {"esp_int_codigo", "esp_var_nome"},
    "vet_raca.csv": {
        "rac_int_codigo",
        "rac_var_nome",
        "esp_int_codigo",
        "esp_var_nome",
    },
    "glo_pessoa.csv": {"pes_int_codigo", "pes_var_chave", "pes_var_nome"},
    "glo_contato.csv": {"pes_int_codigo", "tco_var_nome", "con_var_contato"},
    "eco_marca.csv": {"mar_int_codigo", "mar_var_nome"},
    "eco_produto.csv": {"pro_int_codigo", "pro_var_chave", "pro_var_nome"},
    "vet_animal.csv": {
        "ani_int_codigo",
        "ani_var_chave",
        "ani_var_nome",
        "pes_int_codigo",
    },
    "eco_venda.csv": {
        "ven_int_codigo",
        "ven_var_chave",
        "ven_dec_bruto",
        "ven_dec_liquido",
        "ven_dat_data",
    },
    "eco_venda_produto.csv": {
        "ven_int_codigo",
        "pro_int_codigo",
        "vpr_dec_quantidade",
        "vpr_dec_preco",
    },
}

SCOPE_FILES: dict[str, tuple[str, ...]] = {
    "base": ("vet_especie.csv", "vet_raca.csv"),
    "catalog": (
        "glo_pessoa.csv",
        "glo_contato.csv",
        "eco_marca.csv",
        "eco_produto.csv",
    ),
    "pets": ("glo_pessoa.csv", "glo_contato.csv", "vet_animal.csv"),
    "sales": (
        "glo_pessoa.csv",
        "glo_contato.csv",
        "eco_marca.csv",
        "eco_produto.csv",
        "eco_venda.csv",
        "eco_venda_produto.csv",
    ),
    "all": tuple(FILE_COLUMNS),
}


class ImportPlanError(ValueError):
    """Falha fechada de validacao do plano de importacao."""


def environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return "development"


def database_identity(database_url: str) -> dict[str, Any]:
    url = make_url(database_url)
    identity = {
        "driver": url.drivername,
        "host": url.host or "local",
        "port": url.port,
        "database": url.database or "",
    }
    identity["fingerprint"] = _sha256_json(identity)
    return identity


def is_production(environment: str, database: dict[str, Any]) -> bool:
    database_name = str(database.get("database") or "").lower()
    driver = str(database.get("driver") or "").lower()
    host = str(database.get("host") or "").strip().lower()
    remote_database = (
        not driver.startswith("sqlite") and host not in LOCAL_DATABASE_HOSTS
    )
    return (
        environment.lower() in PRODUCTION_ENVS
        or "prod" in database_name
        or remote_database
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _inspect_csv(path: Path, required_columns: set[str]) -> tuple[list[str], int]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            headers = list(reader.fieldnames or [])
            missing = sorted(required_columns - set(headers))
            if missing:
                raise ImportPlanError(
                    f"{path.name}: colunas obrigatorias ausentes: {', '.join(missing)}"
                )
            rows = sum(1 for _row in reader)
    except UnicodeDecodeError as exc:
        raise ImportPlanError(f"{path.name}: arquivo nao esta em UTF-8.") from exc

    if rows == 0:
        raise ImportPlanError(f"{path.name}: arquivo sem registros.")
    return headers, rows


def build_source_manifest(source_dir: Path, scope: str) -> list[dict[str, Any]]:
    resolved = source_dir.expanduser().resolve()
    if scope not in SCOPE_FILES:
        raise ImportPlanError(f"Escopo desconhecido: {scope}")
    if not resolved.is_dir():
        raise ImportPlanError(f"Diretorio de dados nao encontrado: {resolved}")

    manifest = []
    for filename in SCOPE_FILES[scope]:
        path = resolved / filename
        if not path.is_file():
            raise ImportPlanError(f"Arquivo obrigatorio nao encontrado: {path}")
        headers, rows = _inspect_csv(path, FILE_COLUMNS[filename])
        manifest.append(
            {
                "name": filename,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
                "rows": rows,
                "headers": headers,
            }
        )
    return manifest


def _plan_material(payload: dict[str, Any]) -> dict[str, Any]:
    # O hash cobre todo o documento funcional. Assim, alterar resultado da
    # simulacao, validade, ambiente ou metadados do destino invalida o plano.
    return {key: value for key, value in payload.items() if key != "plan_id"}


def create_plan(
    *,
    database: dict[str, Any],
    environment: str,
    target: dict[str, Any],
    source_dir: Path,
    files: list[dict[str, Any]],
    scope: str,
    limit: int | None,
    stats: dict[str, Any],
    rejected: dict[str, int],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "version": PLAN_VERSION,
        "status": "simulation_approved",
        "created_at": now.isoformat(),
        "expires_at": (now + PLAN_TTL).isoformat(),
        "environment": environment,
        "database": database,
        "target": target,
        "source": {"directory": str(source_dir.resolve()), "files": files},
        "scope": scope,
        "limit": limit,
        "simulation": {"stats": stats, "rejected": rejected},
    }
    payload["plan_id"] = _sha256_json(_plan_material(payload))
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_plan(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ImportPlanError(f"Plano nao encontrado: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportPlanError(f"Plano invalido: {resolved}") from exc
    if not isinstance(payload, dict):
        raise ImportPlanError("Plano invalido: conteudo deve ser um objeto JSON.")
    return payload


def validate_plan(
    payload: dict[str, Any],
    *,
    database: dict[str, Any],
    confirm_tenant_id: str,
    confirm_plan_id: str,
) -> tuple[Path, list[dict[str, Any]]]:
    if payload.get("version") != PLAN_VERSION:
        raise ImportPlanError("Versao do plano nao suportada.")
    if payload.get("status") != "simulation_approved":
        raise ImportPlanError("O plano nao registra uma simulacao aprovada.")

    expected_plan_id = _sha256_json(_plan_material(payload))
    if payload.get("plan_id") != expected_plan_id:
        raise ImportPlanError("O plano foi alterado depois da simulacao.")
    if confirm_plan_id != expected_plan_id:
        raise ImportPlanError("A confirmacao do plan_id nao corresponde ao plano.")

    target_tenant_id = str(payload["target"]["tenant_id"])
    if confirm_tenant_id != target_tenant_id:
        raise ImportPlanError("A confirmacao da empresa nao corresponde ao plano.")
    if payload["database"].get("fingerprint") != database.get("fingerprint"):
        raise ImportPlanError("O plano foi criado para outro banco de dados.")

    try:
        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
    except (KeyError, ValueError) as exc:
        raise ImportPlanError("Plano sem validade reconhecivel.") from exc
    if datetime.now(timezone.utc) > expires_at:
        raise ImportPlanError("O plano expirou; gere uma nova simulacao.")

    source_dir = Path(payload["source"]["directory"]).resolve()
    current_files = build_source_manifest(source_dir, str(payload["scope"]))
    if current_files != payload["source"]["files"]:
        raise ImportPlanError("Os arquivos mudaram depois da simulacao.")
    return source_dir, current_files
