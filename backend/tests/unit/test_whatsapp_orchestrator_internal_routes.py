import pytest
from fastapi import HTTPException

from app.api.whatsapp_orchestrator_internal_routes import (
    InternalIngestRequest,
    _build_message_content,
    _resolve_waha_media_url,
    _validate_internal_token,
)


def test_build_message_content_text_returns_plain_text():
    payload = InternalIngestRequest(
        phone="5511999999999", message_type="text", text="Ola"
    )

    assert _build_message_content(payload) == "Ola"


def test_build_message_content_audio_prefers_transcription():
    payload = InternalIngestRequest(
        phone="5511999999999",
        message_type="audio",
        transcription_text="quero racao renal",
        text="fallback",
    )

    assert _build_message_content(payload) == "[Audio do cliente] quero racao renal"


def test_build_message_content_image_with_caption_prefixes_marker():
    payload = InternalIngestRequest(
        phone="5511999999999",
        message_type="image",
        caption="serve para filhote?",
    )

    assert _build_message_content(payload).startswith("[Imagem recebida]")


def test_resolve_waha_media_url_replaces_localhost_with_internal_host(monkeypatch):
    monkeypatch.setenv("WAHA_BASE_URL", "http://waha:3000")

    resolved = _resolve_waha_media_url(
        "http://localhost:3000/api/files/default/message.oga"
    )

    assert resolved == "http://waha:3000/api/files/default/message.oga"


def test_resolve_waha_media_url_rejects_untrusted_url(monkeypatch):
    monkeypatch.setenv("WAHA_BASE_URL", "http://waha:3000")

    assert _resolve_waha_media_url("https://example.com/private") == ""


def test_validate_internal_token_rejects_invalid(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    with pytest.raises(HTTPException) as exc:
        _validate_internal_token("token-errado")

    assert exc.value.status_code == 401


def test_validate_internal_token_accepts_valid(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    _validate_internal_token("token-correto")


def test_internal_orchestrator_is_not_blocked_by_user_module_auth():
    from app.main import app

    ingest_route = next(
        route
        for route in app.routes
        if getattr(route, "path", None)
        == "/internal/whatsapp-orchestrator/{tenant_id}/ingest"
    )

    dependency_names = {
        getattr(dependency.call, "__name__", "")
        for dependency in ingest_route.dependant.dependencies
    }

    assert dependency_names == {"get_session"}


def test_internal_read_only_data_routes_are_registered():
    from app.main import app

    paths = set(app.openapi()["paths"])

    assert "/internal/whatsapp-orchestrator/{tenant_id}/catalog-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/customer-context-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/store-context-data" in paths
