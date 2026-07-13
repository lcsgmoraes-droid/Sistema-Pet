"""Read the safe release-gate evidence promoted by the production deploy."""

from __future__ import annotations

import json
import os
import re
from typing import Any


RELEASE_STATUS_PATH = os.getenv(
    "OPS_RELEASE_STATUS_PATH",
    os.path.join(os.getcwd(), "logs", "release_status.json"),
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _unavailable() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "commit_sha": None,
        "generated_at": None,
        "repository": None,
        "checks_url": None,
        "required_checks": [],
        "passed_checks": 0,
        "total_checks": 0,
    }


def summarize_release_status() -> dict[str, Any]:
    try:
        with open(RELEASE_STATUS_PATH, encoding="utf-8") as status_file:
            payload = json.load(status_file)
    except (OSError, json.JSONDecodeError):
        return _unavailable()
    if not isinstance(payload, dict):
        return _unavailable()

    commit_sha = str(payload.get("commit_sha") or "").lower()
    checks = payload.get("required_checks")
    repository = str(payload.get("repository") or "")
    if not COMMIT_PATTERN.fullmatch(commit_sha) or not isinstance(checks, list):
        return _unavailable()

    safe_checks = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        safe_checks.append(
            {
                "name": str(item.get("name") or ""),
                "status": str(item.get("status") or "missing"),
                "conclusion": str(item.get("conclusion") or "") or None,
            }
        )

    passed_checks = sum(
        item["status"] == "completed" and item["conclusion"] == "success"
        for item in safe_checks
    )
    raw_status = str(payload.get("status") or "unavailable")
    status = (
        "healthy"
        if raw_status == "passed" and passed_checks == len(safe_checks) and safe_checks
        else "failed"
    )
    return {
        "status": status,
        "commit_sha": commit_sha,
        "generated_at": payload.get("generated_at"),
        "repository": repository,
        "checks_url": payload.get("checks_url"),
        "required_checks": safe_checks,
        "passed_checks": passed_checks,
        "total_checks": len(safe_checks),
    }
