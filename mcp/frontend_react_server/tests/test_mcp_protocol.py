from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


SERVER_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_mcp_responds_over_stdio_protocol(tmp_path: Path):
    async def run_client() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "frontend_react_mcp.main"],
            cwd=SERVER_ROOT,
            env={
                "PYTHONIOENCODING": "utf-8",
                "SISTEMA_PET_FRONT_MCP_AUDIT_LOG": str(tmp_path / "frontend-audit.jsonl"),
            },
        )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=15),
            ) as session:
                initialize_result = await session.initialize()
                assert initialize_result.serverInfo.name == "sistema-pet-frontend-react"

                tools_result = await session.list_tools()
                tool_names = {tool.name for tool in tools_result.tools}
                assert "front_status" in tool_names
                assert "front_http_check" in tool_names

                call_result = await session.call_tool("front_status", {})
                assert call_result.isError is False
                payload = json.loads(call_result.content[0].text)
                assert payload["check"] == "front_status"
                assert "frontend_exists" in payload["details"]

    anyio.run(run_client)
