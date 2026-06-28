from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Protocol

from gerar_seed_base_demo_marketing import build_seed_plan
from validar_base_demo_marketing import (
    load_payload,
    resolve_demo_json_path,
    validate_payload,
)


PRODUCTION_ENVIRONMENTS = {"prod", "production", "producao"}


class SeedRepository(Protocol):
    def upsert(self, action: dict) -> dict:
        """Apply one idempotent seed action."""


def normalize_environment(environment: str | None) -> str:
    return (environment or "development").strip().lower()


def assert_safe_seed_environment(
    environment: str | None, allow_production: bool = False
) -> None:
    normalized = normalize_environment(environment)
    if normalized in PRODUCTION_ENVIRONMENTS and not allow_production:
        raise ValueError(
            "Seed demo bloqueado em producao. Use apenas tenant/base de demonstracao."
        )


def _dry_run_result(action: dict) -> dict:
    return {
        "section": action["section"],
        "operation": action["operation"],
        "items": action["items"],
        "status": "would_upsert",
    }


def apply_seed_plan(
    plan: dict,
    repository: SeedRepository,
    dry_run: bool,
    environment: str | None,
    allow_production: bool = False,
) -> dict:
    assert_safe_seed_environment(
        environment=environment,
        allow_production=allow_production,
    )

    results = []
    for action in plan["actions"]:
        if dry_run:
            results.append(_dry_run_result(action))
        else:
            results.append(repository.upsert(action))

    return {
        "seed_name": plan["metadata"]["seed_name"],
        "tenant_slug": plan["metadata"]["tenant_slug"],
        "environment": normalize_environment(environment),
        "dry_run": dry_run,
        "total_actions": len(results),
        "results": results,
    }


class DryRunOnlyRepository:
    def upsert(self, action: dict) -> dict:
        raise RuntimeError(
            f"Repositorio real nao configurado para aplicar secao {action['section']}"
        )


def _load_plan(json_path: Path, tenant_slug: str) -> dict:
    resolved = resolve_demo_json_path(json_path)
    payload = load_payload(resolved)
    errors = validate_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return build_seed_plan(payload, tenant_slug=tenant_slug)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aplica ou simula o manifesto de seed da base demo de marketing."
    )
    parser.add_argument(
        "--json", required=True, type=Path, help="Caminho do JSON da base demo."
    )
    parser.add_argument(
        "--tenant-slug",
        default="tenant_demo",
        help="Identificador legivel do tenant/base demo alvo.",
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development",
        help="Ambiente de execucao usado para trava de seguranca.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula a aplicacao sem chamar repositorio de banco.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        print(
            "ERRO: esta etapa suporta apenas --dry-run; aplicacao real exige "
            "repositorio SQLAlchemy em uma proxima fatia.",
            file=sys.stderr,
        )
        return 1

    try:
        plan = _load_plan(args.json, tenant_slug=args.tenant_slug)
        result = apply_seed_plan(
            plan,
            repository=DryRunOnlyRepository(),
            dry_run=True,
            environment=args.environment,
        )
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
