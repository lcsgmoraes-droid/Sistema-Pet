from pathlib import Path

from app.whatsapp import processor


WHATSAPP_DIR = Path(__file__).resolve().parents[2] / "app" / "whatsapp"

PUBLIC_HELPERS = (
    "_catalog_followup_query",
    "_confirmation_reply",
    "_extract_explicit_measurements",
    "_operational_handoff_reason",
    "_special_catalog_request_query",
)


def _line_count(filename: str) -> int:
    return len((WHATSAPP_DIR / filename).read_text(encoding="utf-8").splitlines())


def test_processor_preserva_fachada_publica():
    assert processor.MessageProcessor.__module__ == "app.whatsapp.processor"
    for helper_name in PUBLIC_HELPERS:
        assert callable(getattr(processor, helper_name))


def test_processor_e_helpers_respeitam_limites_modulares():
    assert _line_count("processor.py") < 3100
    assert _line_count("catalog_query_helpers.py") < 700
    assert _line_count("conversation_helpers.py") < 700
