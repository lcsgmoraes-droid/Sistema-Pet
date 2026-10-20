"""Prévia e aplicação pontual de contas '(sistema antigo)' fora da DRE.

Exemplo (a partir de backend/):
  python -m app.scripts.retirar_sistema_antigo_dre --tenant-id UUID

Depois de conferir a prévia, repetir com --apply --plano-hash HASH.
Em produção, obter autorização do Lucas antes de executar no servidor.
O relatório JSON contém as flags anteriores para auditoria e reversão.
"""

from __future__ import annotations

import argparse
import json

from app.db import SessionLocal
from app.financeiro.sistema_antigo_sem_dre import retirar_sistema_antigo_dre
from app.scripts.sanear_baixas_historicas_contas_pagar import (
    PRODUCTION_ENVS,
    _environment_name,
    _fail,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True, help="UUID conferido do tenant.")
    parser.add_argument(
        "--tenant-nome", default="Tecno Agropet", help="Nome exato esperado."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Grava; o padrão é somente prévia."
    )
    parser.add_argument("--plano-hash", help="Hash da prévia que foi conferida.")
    parser.add_argument("--allow-production-apply", action="store_true")
    args = parser.parse_args(argv)
    if args.apply and not args.plano_hash:
        return _fail("--apply exige --plano-hash da prévia.", dry_run=False)
    if (
        args.apply
        and _environment_name() in PRODUCTION_ENVS
        and not args.allow_production_apply
    ):
        return _fail(
            "Aplicação em produção exige --allow-production-apply.", dry_run=False
        )
    with SessionLocal() as db:
        try:
            report = retirar_sistema_antigo_dre(
                db,
                tenant_id=args.tenant_id,
                tenant_nome=args.tenant_nome,
                apply_changes=args.apply,
                plano_hash=args.plano_hash,
            )
        except Exception as exc:
            return _fail(str(exc), dry_run=not args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
