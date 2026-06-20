import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_MOBILE = ROOT / "app-mobile"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_android_push_build_has_firebase_configuration_contract():
    app_json = json.loads((APP_MOBILE / "app.json").read_text(encoding="utf-8"))
    package_json = json.loads((APP_MOBILE / "package.json").read_text(encoding="utf-8"))

    expo = app_json["expo"]
    android = expo["android"]
    assert android["package"] == "br.com.corepet.app"
    assert android["googleServicesFile"] == "./google-services.json"

    scripts = package_json["scripts"]
    assert scripts["prepare:firebase"] == "node scripts/prepare-google-services.js"
    assert scripts["eas-build-post-install"] == "npm run prepare:firebase"

    app_config = read("app-mobile/app.config.js")
    assert "process.env.GOOGLE_SERVICES_JSON" in app_config
    assert "googleServicesFile" in app_config

    prepare_script = read("app-mobile/scripts/prepare-google-services.js")
    assert "GOOGLE_SERVICES_JSON" in prepare_script
    assert "GOOGLE_SERVICES_JSON_BASE64" in prepare_script
    assert "br.com.corepet.app" in prepare_script
    assert "android/app/google-services.json" in prepare_script.replace("\\", "/")

    root_gradle = read("app-mobile/android/build.gradle")
    app_gradle = read("app-mobile/android/app/build.gradle")
    assert "com.google.gms:google-services" in root_gradle
    assert 'apply plugin: "com.google.gms.google-services"' in app_gradle
