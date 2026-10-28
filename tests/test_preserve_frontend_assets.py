import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "preserve_frontend_assets.py"
SPEC = importlib.util.spec_from_file_location("preserve_frontend_assets", SCRIPT)
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)
START = 1_800_000_000
DAY = assets.DAY_SECONDS


def build(parent, name, files):
    dist = parent / name
    dist.mkdir()
    (dist / "index.html").write_text(f"HTML {name}", encoding="utf-8")
    for asset_name, content in files.items():
        path = dist / "assets" / asset_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return dist


def manifest(dist):
    return json.loads((dist / assets.MANIFEST_NAME).read_text(encoding="utf-8"))


def test_bootstrap_preserves_old_assets_without_overwriting_new_build(tmp_path):
    current = build(
        tmp_path,
        "dist",
        {"page-old.js": "old JS", "shared.js": "old shared", "fonts/a.woff2": "font"},
    )
    old_file = current / "assets/page-old.js"
    os.utime(old_file, (1, 1))
    (current / ".env").write_text("private", encoding="utf-8")
    (current / "release-commit.txt").write_text("old commit", encoding="utf-8")
    upcoming = build(
        tmp_path, "dist.next", {"page-new.js": "new JS", "shared.js": "new shared"}
    )
    result = assets.preserve_assets(current, upcoming, now=START)

    assert result == {"current": 2, "preserved": 2, "expired": 0}
    assert old_file.read_text() == "old JS"
    assert (upcoming / "assets/page-old.js").read_text() == "old JS"
    assert (upcoming / "assets/fonts/a.woff2").read_text() == "font"
    assert (upcoming / "assets/shared.js").read_text() == "new shared"
    assert (upcoming / "index.html").read_text() == "HTML dist.next"
    assert not (upcoming / ".env").exists()
    assert not (upcoming / "release-commit.txt").exists()
    assert manifest(upcoming)["current"] == ["page-new.js", "shared.js"]
    assert manifest(upcoming)["retained"]["page-old.js"] == START + 7 * DAY
    assert not (current / assets.MANIFEST_NAME).exists()


def test_three_deploys_expire_orphans_without_renewing_their_deadline(tmp_path):
    first = build(tmp_path, "a", {"page-a.js": "a"})
    second = build(tmp_path, "b", {"page-b.js": "b"})
    assets.preserve_assets(first, second, now=START)
    third = build(tmp_path, "c", {"page-c.js": "c"})
    assets.preserve_assets(second, third, now=START + 3 * DAY)
    assert manifest(third)["retained"] == {
        "page-a.js": START + 7 * DAY,
        "page-b.js": START + 10 * DAY,
    }

    fourth = build(tmp_path, "d", {"page-d.js": "d"})
    result = assets.preserve_assets(third, fourth, now=START + 7 * DAY)
    assert result == {"current": 1, "preserved": 2, "expired": 1}
    assert not (fourth / "assets/page-a.js").exists()
    assert (fourth / "assets/page-b.js").read_text() == "b"
    assert (fourth / "assets/page-c.js").read_text() == "c"
    assert manifest(fourth)["retained"]["page-b.js"] == START + 10 * DAY
    # A rollback can still serve everything from the prior build.
    assert (third / "assets/page-a.js").read_text() == "a"
    assert (first / "assets/page-a.js").read_text() == "a"


def test_reused_asset_gets_a_new_retention_window_only_when_current_again(tmp_path):
    first = build(tmp_path, "a", {"shared.js": "shared", "a.js": "a"})
    second = build(tmp_path, "b", {"shared.js": "shared", "b.js": "b"})
    assets.preserve_assets(first, second, now=START)
    assert "shared.js" not in manifest(second)["retained"]
    third = build(tmp_path, "c", {"c.js": "c"})
    assets.preserve_assets(second, third, now=START + 8 * DAY)
    assert manifest(third)["retained"]["shared.js"] == START + 15 * DAY
    assert not (third / "assets/a.js").exists()


def test_first_deploy_without_previous_dist_still_records_current_assets(tmp_path):
    upcoming = build(tmp_path, "next", {"main.js": "main"})
    assert assets.preserve_assets(tmp_path / "missing", upcoming, now=START) == {
        "current": 1,
        "preserved": 0,
        "expired": 0,
    }
    assert manifest(upcoming) == {"version": 1, "current": ["main.js"], "retained": {}}


def test_does_not_inherit_html_maps_or_hidden_files_even_inside_assets(tmp_path):
    current = build(
        tmp_path,
        "old",
        {
            "main.js": "valid",
            "main.js.map": "sources",
            "index.html": "html",
            ".env": "secret",
            ".private/key.js": "secret",
            "nested/font.woff2": "font",
        },
    )
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    assets.preserve_assets(current, upcoming, now=START)
    assert sorted(manifest(upcoming)["retained"]) == ["main.js", "nested/font.woff2"]
    assert not (upcoming / "assets/.env").exists()
    assert not (upcoming / "assets/index.html").exists()
    assert not (upcoming / "assets/main.js.map").exists()


@pytest.mark.parametrize(
    "name",
    [
        "../outside.js",
        "/outside.js",
        "a/../../outside.js",
        r"..\outside.js",
        "C:/outside.js",
        "a//b.js",
    ],
)
def test_rejects_unsafe_metadata_paths_before_copying(tmp_path, name):
    current = build(tmp_path, "old", {"main.js": "old"})
    (current / assets.MANIFEST_NAME).write_text(
        json.dumps(
            {
                "version": 1,
                "current": [],
                "retained": {name: START + DAY},
            }
        )
    )
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    with pytest.raises(ValueError, match="Retencao"):
        assets.preserve_assets(current, upcoming, now=START)
    assert not (upcoming / "assets/main.js").exists()
    assert not (upcoming / assets.MANIFEST_NAME).exists()


@pytest.mark.parametrize("value", [0, -1, 91, True])
def test_rejects_unsafe_retention_days(tmp_path, value):
    current = build(tmp_path, "old", {"old.js": "old"})
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    with pytest.raises(ValueError, match="Retencao"):
        assets.preserve_assets(current, upcoming, keep_days=value, now=START)


def test_rejects_same_or_nested_builds(tmp_path):
    current = build(tmp_path, "current", {"old.js": "old"})
    with pytest.raises(ValueError, match="separados"):
        assets.preserve_assets(current, current, now=START)
    with pytest.raises(ValueError, match="separados"):
        assets.preserve_assets(current, current / "next", now=START)


def test_does_not_treat_previously_inherited_assets_as_current_on_repeat(tmp_path):
    current = build(tmp_path, "old", {"old.js": "old"})
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    assets.preserve_assets(current, upcoming, now=START)
    with pytest.raises(ValueError, match="build limpo"):
        assets.preserve_assets(current, upcoming, now=START + DAY)


def test_rejects_symlink_without_reading_or_copying_its_target(tmp_path):
    current = build(tmp_path, "old", {"old.js": "old"})
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    outside = tmp_path / "outside.js"
    outside.write_text("private", encoding="utf-8")
    try:
        (current / "assets/link.js").symlink_to(outside)
    except OSError:
        pytest.skip("sistema sem permissao para criar link simbolico")
    with pytest.raises(ValueError, match="links"):
        assets.preserve_assets(current, upcoming, now=START)
    assert not (upcoming / "assets/link.js").exists()
    assert outside.read_text() == "private"


def test_cli_runs_with_only_standard_library(tmp_path):
    current = build(tmp_path, "old", {"old.js": "old"})
    upcoming = build(tmp_path, "next", {"new.js": "new"})
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--current-dist",
            str(current),
            "--next-dist",
            str(upcoming),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["frontend_assets"]["preserved"] == 1
    assert (upcoming / "assets/old.js").read_text() == "old"


def test_deploy_preserves_assets_before_changing_active_runtime():
    script = (ROOT / "scripts/deploy_producao_seguro.sh").read_text(encoding="utf-8")
    preserve = script.index('python3 "$APP_DIR/scripts/preserve_frontend_assets.py"')
    build_end = script.index('[[ -s "$NEXT_RUNTIME_DIST/index.html" ]]')
    backend_build = script.index('mark_step "build_backend"')
    publish = script.index('mv "$NEXT_RUNTIME_DIST" "$RUNTIME_DIST"')
    assert build_end < preserve < backend_build < publish
    assert '--current-dist "$RUNTIME_DIST"' in script
    assert '--next-dist "$NEXT_RUNTIME_DIST"' in script
