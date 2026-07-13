#!/usr/bin/env python3
"""Validate GitHub checks for a commit and write a safe release attestation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_REQUIRED_CHECKS = (
    "Quality Gate",
    "Tests & Quality",
    "Migration Smoke",
    "Fluxo unico safety",
    "Smoke test",
    "CodeQL (python)",
    "CodeQL (javascript-typescript)",
    "Trivy filesystem scan",
)
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def evaluate_checks(
    payload: dict[str, Any], required_checks: tuple[str, ...]
) -> tuple[str, list[dict[str, str | None]]]:
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        raise ValueError("Resposta do GitHub sem lista de checks")

    latest_by_name: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        name = str(run.get("name") or "")
        current = latest_by_name.get(name)
        if name in required_checks and (
            current is None or int(run.get("id") or 0) > int(current.get("id") or 0)
        ):
            latest_by_name[name] = run

    checks: list[dict[str, str | None]] = []
    all_passed = True
    for name in required_checks:
        run = latest_by_name.get(name)
        status = str(run.get("status") or "missing") if run else "missing"
        conclusion = str(run.get("conclusion") or "") or None if run else None
        passed = status == "completed" and conclusion == "success"
        all_passed = all_passed and passed
        checks.append(
            {
                "name": name,
                "status": status,
                "conclusion": conclusion,
            }
        )
    return ("passed" if all_passed else "failed"), checks


def fetch_check_runs(repository: str, commit_sha: str) -> dict[str, Any]:
    url = (
        f"https://api.github.com/repos/{repository}/commits/"
        f"{commit_sha}/check-runs?per_page=100"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "corepet-release-gate",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("RELEASE_GATE_GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed GitHub API
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"GitHub indisponivel para validar o gate: {type(exc).__name__}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub retornou um formato inesperado para os checks")
    return payload


def write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(evidence, output, ensure_ascii=False, separators=(",", ":"))
            output.write("\n")
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--required-check", action="append", dest="required_checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = args.repository.strip()
    commit_sha = args.commit.strip().lower()
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise SystemExit("Repositorio GitHub invalido")
    if not COMMIT_PATTERN.fullmatch(commit_sha):
        raise SystemExit("Commit Git invalido")

    required_checks = tuple(args.required_checks or DEFAULT_REQUIRED_CHECKS)
    try:
        payload = fetch_check_runs(repository, commit_sha)
    except RuntimeError as exc:
        print(str(exc))
        return 2
    status, checks = evaluate_checks(payload, required_checks)
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "repository": repository,
        "commit_sha": commit_sha,
        "checks_url": f"https://github.com/{repository}/commit/{commit_sha}/checks",
        "required_checks": checks,
    }
    write_evidence(args.output, evidence)

    if status != "passed":
        failed = [
            item["name"]
            for item in checks
            if item["status"] != "completed" or item["conclusion"] != "success"
        ]
        print(f"Gate de release reprovado: {', '.join(failed)}")
        return 1
    print(f"Gate de release aprovado para {commit_sha[:8]} ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
