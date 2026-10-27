"""Exercise the actual production nginx locations against a compatible new build."""

from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=60, check=True
    ).stdout.strip()


def container_logs(container):
    return subprocess.run(
        ["docker", "logs", container],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
        check=False,
    ).stdout.strip()


def request(base, path):
    try:
        response = urlopen(base + path, timeout=3)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read().decode()


@pytest.fixture(scope="module")
def frontend_server(tmp_path_factory):
    if not shutil.which("docker"):
        pytest.skip("nginx integration requires Docker")
    try:
        docker("image", "inspect", "nginx:alpine")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("nginx:alpine is not available in the local Docker daemon")

    fixture = tmp_path_factory.mktemp("frontend-nginx")
    current, upcoming = fixture / "old", fixture / "new"
    for dist in (current, upcoming):
        (dist / "assets").mkdir(parents=True)
    (current / "index.html").write_text("OLD_HTML", encoding="utf-8")
    (current / "assets/old-page.js").write_text("export const version = 'old';")
    (current / "assets/old-page.css").write_text("body { color: blue; }")
    (current / "release-commit.txt").write_text("old-commit")
    (upcoming / "index.html").write_text("NEW_HTML", encoding="utf-8")
    (upcoming / "assets/new-page.js").write_text("export const version = 'new';")
    (upcoming / "release-commit.txt").write_text("new-commit")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/preserve_frontend_assets.py"),
            "--current-dist",
            str(current),
            "--next-dist",
            str(upcoming),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    config = fixture / "nginx.conf"
    config.write_text(
        "events {}\nhttp {\n"
        "include /etc/nginx/mime.types;\n"
        "map $remote_addr $client_ip { default $remote_addr; }\n"
        "limit_req_zone $binary_remote_addr zone=api_limit:1m rate=10r/s;\n"
        "limit_req_zone $binary_remote_addr zone=login_limit:1m rate=5r/s;\n"
        "upstream backend { server 127.0.0.1:9; }\n"
        "server { listen 80; include /etc/nginx/includes/app-server-locations.conf; }\n"
        "}\n",
        encoding="utf-8",
    )
    container = docker(
        "run",
        "--detach",
        "--publish",
        "127.0.0.1::80",
        "--volume",
        f"{upcoming}:/usr/share/nginx/html:ro",
        "--volume",
        f"{ROOT / 'nginx/includes'}:/etc/nginx/includes:ro",
        "--volume",
        f"{config}:/etc/nginx/nginx.conf:ro",
        "nginx:alpine",
    )
    try:
        address = ""
        for _ in range(30):
            try:
                address = docker("port", container, "80/tcp")
                if address:
                    break
            except subprocess.CalledProcessError:
                pass
            if docker("inspect", "--format", "{{.State.Status}}", container) in {
                "exited",
                "dead",
            }:
                pytest.fail("nginx exited before startup: " + container_logs(container))
            time.sleep(0.1)
        if not address:
            pytest.fail("nginx port unavailable: " + container_logs(container))
        base = "http://" + address
        for _ in range(30):
            try:
                if request(base, "/health")[0] == 200:
                    break
            except (OSError, URLError):
                pass
            time.sleep(0.1)
        else:
            pytest.fail("nginx did not start: " + container_logs(container))
        yield base
    finally:
        docker("rm", "--force", container)


def test_previous_release_modules_remain_available_after_publication(frontend_server):
    status, headers, body = request(frontend_server, "/assets/old-page.js")
    assert status == 200
    assert body == "export const version = 'old';"
    assert "javascript" in headers["Content-Type"]
    assert "immutable" in ", ".join(headers.get_all("Cache-Control", []))
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert request(frontend_server, "/assets/old-page.css")[0] == 200
    assert "'new'" in request(frontend_server, "/assets/new-page.js")[2]


def test_missing_asset_is_404_while_routes_receive_fresh_html(frontend_server):
    status, _, body = request(frontend_server, "/assets/missing-page.js")
    assert status == 404
    assert "NEW_HTML" not in body
    assert request(frontend_server, "/produtos/analise")[2] == "NEW_HTML"
    status, headers, body = request(frontend_server, "/index.html")
    assert status == 200 and body == "NEW_HTML"
    assert "no-store" in headers["Cache-Control"]
    status, headers, body = request(frontend_server, "/release-commit.txt")
    assert status == 200 and body == "new-commit"
    assert "no-store" in headers["Cache-Control"]
