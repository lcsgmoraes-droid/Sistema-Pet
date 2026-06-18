from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = ROOT / "frontend" / "package.json"
FRONTEND_INDEX_CSS = ROOT / "frontend" / "src" / "index.css"


def _dependency_major_version(package: dict[str, object], name: str) -> int:
    dependencies = package.get("dependencies", {})
    dev_dependencies = package.get("devDependencies", {})
    version = {**dependencies, **dev_dependencies}[name]
    match = re.search(r"\d+", str(version))

    assert match is not None
    return int(match.group(0))


def test_tailwind_4_uses_v4_css_entrypoint_and_loads_legacy_js_config():
    package = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))
    css_source = FRONTEND_INDEX_CSS.read_text(encoding="utf-8")

    assert _dependency_major_version(package, "tailwindcss") >= 4
    assert '@import "tailwindcss";' in css_source
    assert '@config "../tailwind.config.js";' in css_source
    assert "@tailwind base;" not in css_source
    assert "@tailwind components;" not in css_source
    assert "@tailwind utilities;" not in css_source
