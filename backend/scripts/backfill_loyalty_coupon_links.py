from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.campaigns.coupon_service import backfill_coupon_redemptions_venda_ids
from app.campaigns.loyalty_service import backfill_loyalty_reward_consumption_meta
from app.db import SessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill seguro para fidelidade: "
            "preenche coupon_redemptions.venda_id quando houver uma unica venda candidata "
            "e congela reward_meta.consumed_stamps em execucoes antigas."
        )
    )
    parser.add_argument(
        "--tenant-id",
        dest="tenant_id",
        default=None,
        help="UUID do tenant. Se omitido, processa todos os tenants.",
    )
    parser.add_argument(
        "--window-hours",
        dest="window_hours",
        type=int,
        default=12,
        help="Janela de aproximacao para localizar a venda candidata do redemption.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tenant_id = UUID(args.tenant_id) if args.tenant_id else None

    db = SessionLocal()
    try:
        rewards_result = backfill_loyalty_reward_consumption_meta(
            db,
            tenant_id=tenant_id,
        )
        redemptions_result = backfill_coupon_redemptions_venda_ids(
            db,
            tenant_id=tenant_id,
            window_hours=args.window_hours,
        )
        db.commit()

        payload = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "loyalty_reward_meta": rewards_result,
            "coupon_redemptions": redemptions_result,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
