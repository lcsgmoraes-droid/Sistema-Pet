from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JSON = ROOT / "app-mobile" / "app.json"


def test_mobile_app_keeps_existing_eas_project_slug_for_updates():
    app_config = json.loads(APP_JSON.read_text(encoding="utf-8"))["expo"]

    assert app_config["name"] == "CorePet"
    assert app_config["slug"] == "petshop-app"
    assert app_config["extra"]["eas"]["projectId"] == "158693e8-177c-4be6-8e2f-143d0d8260dd"
