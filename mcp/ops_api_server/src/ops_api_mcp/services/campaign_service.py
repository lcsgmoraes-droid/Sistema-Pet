from __future__ import annotations

import json
from uuid import UUID

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.services.docker_service import DockerService


class CampaignService:
    _allowed_events = {
        "cpf_linked",
        "customer_registered",
        "daily_birthday_check",
        "drawing_execution",
        "monthly_ranking_recalc",
        "purchase_completed",
        "weekly_inactivity_check",
    }

    def __init__(self, config: ServerConfig, docker_service: DockerService) -> None:
        self.config = config
        self.docker_service = docker_service

    def logs(self, limit: int = 20) -> dict:
        bounded_limit = max(1, min(int(limit), 100))
        sql = (
            "SELECT id, campaign_id, event_type, evaluated, rewarded, errors, "
            "duration_ms, run_at AT TIME ZONE 'America/Sao_Paulo' AS run_at_brt "
            "FROM campaign_run_log "
            f"ORDER BY run_at DESC LIMIT {bounded_limit};"
        )
        return self._psql(sql)

    def queue_status(self) -> dict:
        sql = (
            "SELECT status, event_type, COUNT(*) as total, "
            "MAX(created_at AT TIME ZONE 'America/Sao_Paulo') as mais_recente "
            "FROM campaign_event_queue "
            "GROUP BY status, event_type "
            "ORDER BY status, total DESC;"
        )
        return self._psql(sql)

    def enqueue_test_event(
        self,
        event_type: str,
        payload_json: str = "{}",
        tenant_id: str = "",
    ) -> dict:
        if event_type not in self._allowed_events:
            return {
                "ok": False,
                "error": f"event_type '{event_type}' nao permitido. Use: {sorted(self._allowed_events)}",
            }

        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"payload_json invalido: {exc.msg}"}

        safe_payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(safe_payload_json) > 20000:
            return {"ok": False, "error": "payload_json grande demais para evento de teste"}

        safe_tenant_id = self._resolve_tenant_id(tenant_id)
        if isinstance(safe_tenant_id, dict):
            return safe_tenant_id

        sql = (
            "INSERT INTO campaign_event_queue "
            "(tenant_id, event_type, event_origin, payload, status) "
            "VALUES ("
            f"{self._sql_literal(safe_tenant_id)}::uuid, "
            f"{self._sql_literal(event_type)}, "
            "'system_scheduled', "
            f"{self._sql_literal(safe_payload_json)}::jsonb, "
            "'pending'"
            ") RETURNING id, tenant_id, event_type, status;"
        )
        return self._psql(sql)

    def _resolve_tenant_id(self, tenant_id: str) -> str | dict:
        if tenant_id:
            return self._validate_uuid(tenant_id)

        result = self._psql("SELECT id FROM tenants WHERE status='active' LIMIT 1;", extra_args=["-t"])
        if not result.get("ok") or not result.get("stdout", "").strip():
            return {"ok": False, "error": "Nenhum tenant ativo encontrado", **result}

        first_line = result["stdout"].strip().splitlines()[0].strip()
        return self._validate_uuid(first_line)

    def _validate_uuid(self, value: str) -> str | dict:
        try:
            return str(UUID(str(value).strip()))
        except ValueError:
            return {"ok": False, "error": "tenant_id invalido; informe um UUID valido"}

    def _psql(self, sql: str, extra_args: list[str] | None = None) -> dict:
        args = [
            "psql",
            "-U",
            self.config.dev_db_user,
            "-d",
            self.config.dev_db_name,
            *(extra_args or []),
            "-c",
            sql,
        ]
        return self.docker_service.exec(self.config.dev_postgres_container, args)

    def _sql_literal(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
