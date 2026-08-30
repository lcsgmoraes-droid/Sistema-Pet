"""Inventaria ou estagia imagens locais nomeadas como ``EAN_NOME.ext``.

O padrao e dry-run. Mesmo com ``--apply``, as imagens permanecem protegidas,
inativas e pendentes de revisao; nenhum produto e criado e nenhuma loja muda.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.services.catalogo_mestre_image_import import (
    CandidateStageResult,
    DEFAULT_IMAGE_MAX_BYTES,
    DEFAULT_PROTECTED_STAGING_DIR,
    prepare_image_import,
    stage_image_import,
    stage_unmatched_candidate_import,
    summarize_image_import_plan,
)

PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida imagens EAN_NOME.ext e casa somente produtos existentes no "
            "catalogo mestre. O padrao apenas simula."
        )
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument(
        "--source-ref",
        default="fornecimento-manual",
        help="Identificador auditavel da pasta/lote de origem.",
    )
    parser.add_argument("--image-target", type=int, default=5)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_IMAGE_MAX_BYTES)
    parser.add_argument(
        "--staging-dir",
        default=os.getenv(
            "CATALOGO_MESTRE_IMAGE_STAGING_DIR",
            str(DEFAULT_PROTECTED_STAGING_DIR),
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copia para estagio protegido e cria registros inativos/pendentes.",
    )
    parser.add_argument(
        "--stage-unmatched-candidates",
        action="store_true",
        help=(
            "Preserva EANs sem produto em uma fila privada de identificacao. "
            "Nunca cria produto mestre."
        ),
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Trava tecnica adicional para permitir --apply em producao.",
    )
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _fail(message: str, dry_run: bool) -> int:
    print(
        json.dumps(
            {"ok": False, "dry_run": dry_run, "error": message},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply
    if (
        args.apply
        and _environment_name() in PRODUCTION_ENVS
        and not args.allow_production_apply
    ):
        return _fail(
            "Ambiente production/prod detectado; --apply bloqueado sem "
            "--allow-production-apply.",
            dry_run=False,
        )

    db = SessionLocal()
    try:
        plan = prepare_image_import(
            db,
            args.source_dir,
            image_target=args.image_target,
            max_bytes=args.max_bytes,
            lock_products=args.apply,
            include_unmatched_candidates=args.stage_unmatched_candidates,
        )
        staged = 0
        candidate_stage_result = CandidateStageResult()
        if args.apply:
            staged = stage_image_import(
                db,
                plan,
                source_ref=args.source_ref,
                staging_dir=args.staging_dir,
            )
            if args.stage_unmatched_candidates:
                candidate_stage_result = stage_unmatched_candidate_import(
                    db,
                    plan,
                    source_ref=args.source_ref,
                    staging_dir=args.staging_dir,
                )
            db.commit()
        else:
            db.rollback()
        result = summarize_image_import_plan(
            plan,
            dry_run=dry_run,
            staged_images=staged,
            stage_unmatched_candidates=args.stage_unmatched_candidates,
            candidate_stage_result=candidate_stage_result,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
