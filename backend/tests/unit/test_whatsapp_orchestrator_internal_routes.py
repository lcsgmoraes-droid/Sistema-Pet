import pytest
from fastapi import HTTPException

from app.api.whatsapp_orchestrator_internal_routes import (
    InternalIngestRequest,
    _build_message_content,
    _validate_internal_token,
)


def test_build_message_content_text_returns_plain_text():
    payload = InternalIngestRequest(phone="5511999999999", message_type="text", text="Ola")

    assert _build_message_content(payload) == "Ola"


def test_build_message_content_audio_prefers_transcription():
    payload = InternalIngestRequest(
        phone="5511999999999",
        message_type="audio",
        transcription_text="quero racao renal",
        text="fallback",
    )

    assert _build_message_content(payload) == "quero racao renal"


def test_build_message_content_image_with_caption_prefixes_marker():
    payload = InternalIngestRequest(
        phone="5511999999999",
        message_type="image",
        caption="serve para filhote?",
    )

    assert _build_message_content(payload).startswith("[Imagem recebida]")


def test_validate_internal_token_rejects_invalid(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    with pytest.raises(HTTPException) as exc:
        _validate_internal_token("token-errado")

    assert exc.value.status_code == 401


def test_validate_internal_token_accepts_valid(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    _validate_internal_token("token-correto")
