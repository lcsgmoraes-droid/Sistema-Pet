"""Pausa exclusiva do backfill de caixa, com Bash e serviços inteiramente falsos."""

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/deploy_producao_seguro.sh"
MIGRATION = "backend/alembic/versions/zzzk20261009a1_caixa_recebimentos.py"
MARKER = "writers_paused=zzzk20261009a1"


def _function(source, name):
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}$", source, re.M | re.S)
    assert match, name
    return match.group()


def _bash():
    if os.name == "nt":
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.is_file():
            return str(git_bash)
    executable = shutil.which("bash")
    if not executable:
        pytest.skip("Bash é necessário para o teste isolado do deploy.")
    return executable


def _run_fake_release(tmp_path, changed_files, failure="", previous_pause=False):
    source = SCRIPT.read_text(encoding="utf-8")
    marker = tmp_path / "deploy-marker"
    if not marker.exists():
        marker.write_text(MARKER if previous_pause else "", encoding="utf-8")
    for name in ("db", "backup"):
        (tmp_path / name).mkdir(exist_ok=True)
    pause_state = source[
        source.index('CAIXA_BACKFILL_LOCK_MARKER="') : source.index("\nlog() {")
    ]
    pause_start = source.index(
        'if [[ "$DEPLOY_WRITERS_PAUSED" == "1" ]] || requires_caixa_backfill_pause'
    )
    pause = source[
        pause_start : source.index('\nmark_step "backup_banco"', pause_start)
    ]
    operations = source[
        source.index('mark_step "backup_banco"') : source.index(
            'mark_step "publicar_frontend"'
        )
    ]
    skip_runtime_condition = next(
        line
        for line in source.splitlines()
        if line.startswith("if ! requires_runtime_deploy ")
    )
    functions = "\n".join(
        _function(source, name)
        for name in (
            "fail",
            "on_error",
            "cleanup_deploy_lock",
            "requires_runtime_deploy",
            "requires_caixa_backfill_pause",
        )
    )
    harness = f"""set -Eeuo pipefail
APP_DIR={shlex.quote(tmp_path.as_posix())}
DEPLOY_LOCK_FILE={shlex.quote(marker.as_posix())}
DEPLOY_OWNS_LOCK=1
DEPLOY_LOCK_HELD=1
DEPLOY_EVENT_RECORDED=0
CURRENT_STEP=test
COMPOSE_FILE=fake-compose.yml
db_backup_dir="$APP_DIR/db"
backup_dir="$APP_DIR/backup"
db_backup_file=""
changed_files={shlex.quote(changed_files)}
HEAD_BEFORE=same-commit
HEAD_AFTER=same-commit
runtime_release_mismatch=0
failure={shlex.quote(failure)}
record() {{ printf '%s\\n' "$*" >>"$APP_DIR/calls"; }}
mark_step() {{ CURRENT_STEP="$1"; record "step:$1"; }}
audit_step() {{ record "audit:$*"; }}
log() {{ record "log:$*"; }}
print_rollback_hint() {{ :; }}
write_deploy_event() {{ record "event:$*"; DEPLOY_EVENT_RECORDED=1; }}
flock() {{ :; }}
docker() {{
  record "docker:$*"
  case "$*" in
    *" stop "*) [[ "$failure" != stop ]] || return 7 ;;
    *" pg_dump "*) [[ "$failure" != backup ]] || return 7; printf 'fake-dump\\n' ;;
    *" alembic upgrade head"*) [[ "$failure" != migrate ]] || return 7 ;;
    *"check_rls_no_debt.py"*) [[ "$failure" != rls ]] || return 7 ;;
    *" up -d backend "*) [[ "$failure" != up ]] || return 7 ;;
  esac
  return 0
}}
{pause_state}
{functions}
exec 9>"$APP_DIR/mutex"
trap 'on_error $LINENO' ERR
trap cleanup_deploy_lock EXIT
record build_completed
[[ "$failure" != before_pause ]] || exit 8
{skip_runtime_condition}
  record runtime_skipped
  exit 0
fi
record postgres_ready
{pause}
{operations}
"""
    script = tmp_path / "fake-release.sh"
    script.write_text(harness, encoding="utf-8", newline="\n")
    result = subprocess.run(
        [_bash(), script.as_posix()],
        capture_output=True,
        text=True,
        timeout=15,
    )
    calls = (tmp_path / "calls").read_text(encoding="utf-8").splitlines()
    return result, marker, calls


def test_pause_real_script_is_between_ready_and_backup_and_resumes_after_rls():
    source = SCRIPT.read_text(encoding="utf-8")
    build = source.index('mark_step "build_backend"')
    ready = source.index('"Postgres"', build)
    pause = source.index(
        'if [[ "$DEPLOY_WRITERS_PAUSED" == "1" ]] || requires_caixa_backfill_pause',
        ready,
    )
    backup = source.index('mark_step "backup_banco"', pause)
    migrate = source.index('mark_step "migrar_banco"', backup)
    rls = source.index('mark_step "validar_rls_no_debt"', migrate)
    up = source.index("up -d backend worker-bling worker-catalogo", rls)
    reset = source.index("DEPLOY_WRITERS_PAUSED=0", up)
    assert build < ready < pause < backup < migrate < rls < up < reset
    assert "DEPLOY_WRITERS_PAUSED=1" in source[pause:backup]
    assert source.index("DEPLOY_WRITERS_PAUSED=1", pause) < source.index(
        " stop backend", pause
    )


def test_only_exact_caixa_migration_pauses_and_success_clears_marker(tmp_path):
    result, marker, calls = _run_fake_release(
        tmp_path, f"other.py\n{MIGRATION}\nREADME.md"
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    stop = next(
        i
        for i, call in enumerate(calls)
        if " stop backend worker-bling worker-catalogo" in call
    )
    dump = next(i for i, call in enumerate(calls) if " pg_dump " in call)
    migrate = next(i for i, call in enumerate(calls) if " alembic upgrade head" in call)
    rls = next(i for i, call in enumerate(calls) if "check_rls_no_debt.py" in call)
    up = next(
        i
        for i, call in enumerate(calls)
        if " up -d backend worker-bling worker-catalogo" in call
    )
    assert (
        calls.index("build_completed")
        < calls.index("postgres_ready")
        < stop
        < dump
        < migrate
        < rls
        < up
    )
    assert "postgres" not in calls[stop] and "nginx" not in calls[stop]
    assert not any(call.startswith("event:failed") for call in calls)


@pytest.mark.parametrize(
    "changed_files",
    ["", "backend/app/vendas_models.py", MIGRATION.replace("zzzk", "zzzl")],
)
def test_other_releases_do_not_pause_writers(tmp_path, changed_files):
    result, marker, calls = _run_fake_release(tmp_path, changed_files)
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert not any(" stop " in call for call in calls)


@pytest.mark.parametrize("failure", ["stop", "backup", "migrate", "rls", "up"])
def test_failure_while_paused_keeps_marker_and_records_recovery(tmp_path, failure):
    result, marker, calls = _run_fake_release(tmp_path, MIGRATION, failure=failure)
    assert result.returncode != 0
    assert marker.read_text(encoding="utf-8").strip() == MARKER
    recovery = next(call for call in calls if "Nao inicie codigo antigo" in call)
    assert recovery.startswith("event:failed")
    assert "migrations/RLS" in recovery and "subir_servicos" in recovery
    assert "preservado" in result.stderr
    up_calls = [call for call in calls if " up -d backend " in call]
    assert len(up_calls) == (1 if failure == "up" else 0)
    assert not any("reset --hard" in call for call in calls)


def test_previous_failed_pause_survives_failure_before_diff_pause(tmp_path):
    result, marker, calls = _run_fake_release(
        tmp_path, "", failure="before_pause", previous_pause=True
    )
    assert result.returncode == 8
    assert marker.read_text(encoding="utf-8").strip() == MARKER
    assert any("Nao inicie codigo antigo" in call for call in calls)
    assert not any(" stop " in call or " up -d " in call for call in calls)


def test_retry_same_commit_with_empty_diff_repeats_stop_and_completes_release(tmp_path):
    primeira, marker, _ = _run_fake_release(tmp_path, MIGRATION, failure="stop")
    assert primeira.returncode != 0 and marker.exists()
    segunda, marker, calls = _run_fake_release(tmp_path, "")
    assert segunda.returncode == 0, segunda.stderr
    assert not marker.exists()
    assert "runtime_skipped" not in calls
    stops = [i for i, call in enumerate(calls) if " stop backend " in call]
    assert len(stops) == 2
    dump = next(i for i, call in enumerate(calls) if " pg_dump " in call)
    up = next(i for i, call in enumerate(calls) if " up -d backend " in call)
    assert stops[1] < dump < up


@pytest.mark.parametrize("failure", ["stop", "migrate"])
def test_retry_empty_diff_failure_keeps_pause_instead_of_reporting_success(
    tmp_path, failure
):
    primeira, marker, _ = _run_fake_release(tmp_path, MIGRATION, failure="stop")
    assert primeira.returncode != 0 and marker.exists()
    segunda, marker, calls = _run_fake_release(tmp_path, "", failure=failure)
    assert segunda.returncode != 0
    assert marker.read_text(encoding="utf-8").strip() == MARKER
    assert "runtime_skipped" not in calls
    assert len([call for call in calls if " stop backend " in call]) == 2
    assert not any(" up -d backend " in call for call in calls)
