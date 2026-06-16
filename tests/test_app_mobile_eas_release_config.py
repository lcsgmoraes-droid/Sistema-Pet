from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JSON = ROOT / "app-mobile" / "app.json"
ANDROID_BUILD_GRADLE = ROOT / "app-mobile" / "android" / "app" / "build.gradle"
ANDROID_MANIFEST = (
    ROOT / "app-mobile" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
)
ANDROID_MAIN_ACTIVITY = (
    ROOT
    / "app-mobile"
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "br"
    / "com"
    / "corepet"
    / "app"
    / "MainActivity.kt"
)
ANDROID_MAIN_APPLICATION = ANDROID_MAIN_ACTIVITY.with_name("MainApplication.kt")


def test_mobile_app_keeps_existing_eas_project_slug_for_updates():
    app_config = json.loads(APP_JSON.read_text(encoding="utf-8"))["expo"]

    assert app_config["name"] == "CorePet"
    assert app_config["slug"] == "petshop-app"
    assert (
        app_config["extra"]["eas"]["projectId"]
        == "158693e8-177c-4be6-8e2f-143d0d8260dd"
    )


def test_mobile_app_uses_corepet_native_identifiers_for_store_release():
    app_config = json.loads(APP_JSON.read_text(encoding="utf-8"))["expo"]

    assert app_config["android"]["package"] == "br.com.corepet.app"
    assert app_config["ios"]["bundleIdentifier"] == "br.com.corepet.app"


def test_android_native_project_uses_corepet_package_namespace():
    build_gradle = ANDROID_BUILD_GRADLE.read_text(encoding="utf-8")

    assert re.search(r"namespace ['\"]br\.com\.corepet\.app['\"]", build_gradle)
    assert re.search(r"applicationId ['\"]br\.com\.corepet\.app['\"]", build_gradle)
    assert ANDROID_MAIN_ACTIVITY.read_text(encoding="utf-8").startswith(
        "package br.com.corepet.app"
    )
    assert ANDROID_MAIN_APPLICATION.read_text(encoding="utf-8").startswith(
        "package br.com.corepet.app"
    )


def test_android_backup_remains_disabled_for_store_release():
    app_config = json.loads(APP_JSON.read_text(encoding="utf-8"))["expo"]
    manifest = ANDROID_MANIFEST.read_text(encoding="utf-8")

    assert app_config["android"]["allowBackup"] is False
    assert 'android:allowBackup="false"' in manifest
    assert "secure_store_backup_rules" not in manifest
    assert "secure_store_data_extraction_rules" not in manifest
