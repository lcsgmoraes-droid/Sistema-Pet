from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = ROOT / "backend" / "app" / "routers"


def test_relatorios_comissoes_logs_do_not_include_user_or_tenant_values():
    source = (ROUTERS_DIR / "relatorios_comissoes.py").read_text(encoding="utf-8")

    forbidden_fragments = [
        "current_user.email",
        "Tenant ID: {tenant_id}",
        "Query params: {params_dict}",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_whatsapp_websocket_logs_do_not_include_request_controlled_values():
    source = (ROUTERS_DIR / "whatsapp_websocket.py").read_text(encoding="utf-8")
    logger_lines = [line.strip() for line in source.splitlines() if "logger." in line]

    forbidden_fragments = [
        "logger.info(f",
        "logger.warning(f",
        "logger.error(f",
        "{agent_id}",
        "{session_id}",
        "{event}",
        "{e}",
    ]

    for fragment in forbidden_fragments:
        assert all(fragment not in line for line in logger_lines)
