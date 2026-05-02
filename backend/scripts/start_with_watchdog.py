import os
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _log(message: str) -> None:
    print(f"[backend-watchdog] {message}", flush=True)


def _build_uvicorn_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        os.getenv("UVICORN_HOST", "0.0.0.0"),
        "--port",
        os.getenv("UVICORN_PORT", "8000"),
        "--workers",
        os.getenv("UVICORN_WORKERS", "4"),
        "--log-level",
        os.getenv("UVICORN_LOG_LEVEL", "info"),
        "--access-log",
    ]


def _health_ok(url: str, timeout_seconds: int) -> tuple[bool, str]:
    try:
        request = Request(url, headers={"User-Agent": "petshop-backend-watchdog"})
        with urlopen(request, timeout=timeout_seconds) as response:
            if 200 <= response.status < 300:
                return True, f"status={response.status}"
            return False, f"status={response.status}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _stop_process(process: subprocess.Popen, reason: str) -> None:
    _log(f"Stopping uvicorn pid={process.pid}. reason={reason}")
    try:
        process.terminate()
        process.wait(timeout=20)
        return
    except subprocess.TimeoutExpired:
        _log(f"Uvicorn pid={process.pid} did not stop gracefully; killing.")
        process.kill()
        process.wait(timeout=10)
    except Exception as exc:
        _log(f"Error while stopping uvicorn: {type(exc).__name__}: {exc}")


def main() -> int:
    watchdog_enabled = _env_bool("WATCHDOG_ENABLED", True)
    health_url = os.getenv("WATCHDOG_URL", "http://127.0.0.1:8000/health/watchdog")
    interval_seconds = _env_int("WATCHDOG_INTERVAL_SECONDS", 15)
    timeout_seconds = _env_int("WATCHDOG_TIMEOUT_SECONDS", 6)
    failure_threshold = _env_int("WATCHDOG_FAILURE_THRESHOLD", 4)
    startup_grace_seconds = _env_int("WATCHDOG_STARTUP_GRACE_SECONDS", 90)
    restart_delay_seconds = _env_int("WATCHDOG_RESTART_DELAY_SECONDS", 10)

    should_stop = False
    process: subprocess.Popen | None = None

    def _handle_signal(signum, _frame):
        nonlocal should_stop, process
        should_stop = True
        _log(f"Received signal {signum}; shutting down.")
        if process and process.poll() is None:
            _stop_process(process, f"signal {signum}")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    command = _build_uvicorn_command()

    while not should_stop:
        _log("Starting uvicorn: " + " ".join(command))
        process = subprocess.Popen(command)
        started_at = time.monotonic()
        consecutive_failures = 0

        while not should_stop:
            return_code = process.poll()
            if return_code is not None:
                _log(f"Uvicorn exited with code {return_code}.")
                break

            if not watchdog_enabled:
                time.sleep(interval_seconds)
                continue

            uptime_seconds = time.monotonic() - started_at
            if uptime_seconds < startup_grace_seconds:
                time.sleep(interval_seconds)
                continue

            ok, detail = _health_ok(health_url, timeout_seconds)
            if ok:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                _log(
                    "Health check failed "
                    f"({consecutive_failures}/{failure_threshold}): {detail}"
                )

            if consecutive_failures >= failure_threshold:
                _stop_process(process, "watchdog health failures")
                break

            time.sleep(interval_seconds)

        if should_stop:
            break

        time.sleep(restart_delay_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
