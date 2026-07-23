from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = ROOT / "frontend" / "package.json"
FRONTEND_INDEX_CSS = ROOT / "frontend" / "src" / "index.css"
FRONTEND_POSTCSS_CONFIG = ROOT / "frontend" / "postcss.config.js"


def _dependency_major_version(package: dict[str, object], name: str) -> int:
    dependencies = package.get("dependencies", {})
    dev_dependencies = package.get("devDependencies", {})
    version = {**dependencies, **dev_dependencies}[name]
    match = re.search(r"\d+", str(version))

    assert match is not None
    return int(match.group(0))


def test_frontend_visual_stack_stays_on_migrated_versions_only():
    package = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))

    assert _dependency_major_version(package, "react") == 18
    assert _dependency_major_version(package, "react-dom") == 18
    assert _dependency_major_version(package, "react-router-dom") == 7
    assert _dependency_major_version(package, "tailwindcss") == 3
    assert "@tailwindcss/postcss" not in package.get("devDependencies", {})


def test_tailwind_3_uses_stable_css_entrypoint_and_postcss_plugin():
    package = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))
    css_source = FRONTEND_INDEX_CSS.read_text(encoding="utf-8")
    postcss_source = FRONTEND_POSTCSS_CONFIG.read_text(encoding="utf-8")

    assert _dependency_major_version(package, "tailwindcss") == 3
    assert "@tailwind base;" in css_source
    assert "@tailwind components;" in css_source
    assert "@tailwind utilities;" in css_source
    assert '@import "tailwindcss";' not in css_source
    assert '@config "../tailwind.config.js";' not in css_source
    assert "tailwindcss: {}" in postcss_source
    assert "'@tailwindcss/postcss'" not in postcss_source
