from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


SERVER_ROOT = Path(__file__).resolve().parents[1]


def test_ops_mcp_responds_over_stdio_protocol(tmp_path: Path):
    async def run_client() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "ops_api_mcp.main"],
            cwd=SERVER_ROOT,
            env={
                "PYTHONIOENCODING": "utf-8",
                "SISTEMA_PET_MCP_AUDIT_LOG": str(tmp_path / "ops-audit.jsonl"),
                "SISTEMA_PET_FRONT_MCP_AUDIT_LOG": str(tmp_path / "frontend-audit.jsonl"),
                "SISTEMA_PET_MCP_ALLOW_PROD_ACTIONS": "false",
            },
        )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=15),
            ) as session:
                initialize_result = await session.initialize()
                assert initialize_result.serverInfo.name == "sistema-pet-ops-api"

                tools_result = await session.list_tools()
                tool_names = {tool.name for tool in tools_result.tools}
                assert "fluxo_check" in tool_names
                assert "fluxo_prod_up" in tool_names
                assert "mcp_audit_report" in tool_names

                call_result = await session.call_tool(
                    "fluxo_prod_up",
                    {"timeout_seconds": 1, "confirmacao": ""},
                )
                assert call_result.isError is False
                payload = json.loads(call_result.content[0].text)
                assert payload["ok"] is False
                assert payload["exit_code"] == 126
                assert "bloqueada" in payload["stderr"]

                audit_result = await session.call_tool("mcp_audit_report", {"limit": 5})
                assert audit_result.isError is False
                audit_payload = json.loads(audit_result.content[0].text)
                assert audit_payload["ok"] is True
                assert audit_payload["total_events"] >= 1
                assert audit_payload["recent_events"][0]["tool"] == "fluxo_prod_up"

    anyio.run(run_client)
