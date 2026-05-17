from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any

from app.services.ops_alert_notifier import notify_ops_alerts


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_alert(label: str) -> dict[str, Any]:
    now = _utcnow_iso()
    safe_label = label.strip()[:80] or "manual"
    return {
        "alert_key": f"system:ops_notifier_test:{safe_label}",
        "scope": "system",
        "kind": "ops_notifier_test",
        "severity": "critical",
        "title": "Teste controlado de alerta Ops",
        "detail": f"Disparo controlado do notifier Ops ({safe_label}).",
        "action": "Confirmar recebimento no canal operacional e conferir deduplicacao local.",
        "latest_event_at": now,
        "occurrence_count": 1,
        "score": 999,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dispara um alerta Ops controlado para validar OPS_ALERT_WEBHOOK_URL sem expor o webhook.",
    )
    parser.add_argument(
        "--label",
        default="manual",
        help="Rotulo curto para identificar o teste no canal operacional.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not os.getenv("OPS_ALERT_WEBHOOK_URL", "").strip():
        print(
            "ERRO: OPS_ALERT_WEBHOOK_URL nao esta configurado no ambiente. "
            "Configure o secret no servidor antes do teste controlado.",
            file=sys.stderr,
        )
        return 2

    result = notify_ops_alerts([_build_alert(args.label)])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("sent") or result.get("status") == "no_eligible_alerts" else 1


if __name__ == "__main__":
    raise SystemExit(main())
