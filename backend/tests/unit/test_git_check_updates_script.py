from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "git_check_updates.ps1"


def _powershell_command() -> str:
    for candidate in ("pwsh", "powershell"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("PowerShell nao esta disponivel neste ambiente")


def test_git_check_updates_reports_branch_without_upstream(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_git = fake_bin / "fake_git.py"
    fake_git.write_text(
        textwrap.dedent(
            r"""
            from __future__ import annotations

            import sys

            args = sys.argv[1:]

            if args == ["rev-parse", "--is-inside-work-tree"]:
                print("true")
                raise SystemExit(0)

            if args == ["fetch", "--prune", "origin"]:
                raise SystemExit(0)

            if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
                print("feat/sem-upstream")
                raise SystemExit(0)

            if args == ["status", "--porcelain"]:
                raise SystemExit(0)

            if args == ["show-ref", "--verify", "--quiet", "refs/heads/main"]:
                raise SystemExit(0)

            if args == [
                "show-ref",
                "--verify",
                "--quiet",
                "refs/remotes/origin/main",
            ]:
                raise SystemExit(0)

            if args == ["rev-list", "--left-right", "--count", "main...origin/main"]:
                print("0 0")
                raise SystemExit(0)

            if args == [
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ]:
                print(
                    "fatal: no upstream configured for branch 'feat/sem-upstream'",
                    file=sys.stderr,
                )
                raise SystemExit(128)

            print(f"unexpected git args: {args}", file=sys.stderr)
            raise SystemExit(99)
            """
        ).lstrip(),
        encoding="utf-8",
    )

    if os.name == "nt":
        (fake_bin / "git.cmd").write_text(
            f'@echo off\r\n"{sys.executable}" "{fake_git}" %*\r\n',
            encoding="utf-8",
        )
    else:
        git_sh = fake_bin / "git"
        git_sh.write_text(
            f'#!/usr/bin/env sh\nexec "{sys.executable}" "{fake_git}" "$@"\n',
            encoding="utf-8",
        )
        git_sh.chmod(git_sh.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]

    completed = subprocess.run(
        [
            _powershell_command(),
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "Branch atual: ainda sem remoto configurado." in completed.stdout
    assert "Ao fechar a tarefa com git_finish_task.ps1 -Push" in completed.stdout
    assert "NativeCommandError" not in completed.stderr
