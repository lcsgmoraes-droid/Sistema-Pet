from pathlib import Path

from app.whatsapp import processor


WHATSAPP_DIR = Path(__file__).resolve().parents[2] / "app" / "whatsapp"

PUBLIC_HELPERS = (
    "_catalog_followup_query",
    "_confirmation_reply",
    "_customer_benefits_response",
    "_delivery_status_response",
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
    assert (
        processor.MessageProcessor._handle_pending_checkout.__module__
        == "app.whatsapp.processor_checkout_flow"
    )
    assert (
        processor.MessageProcessor._handle_order_draft_flow.__module__
        == "app.whatsapp.processor_order_draft_flow"
    )
    assert (
        processor.MessageProcessor._handle_product_clarification.__module__
        == "app.whatsapp.processor_product_clarification_flow"
    )
    assert (
        processor.MessageProcessor._handle_real_operational_request.__module__
        == "app.whatsapp.processor_operational_flow"
    )
    assert (
        processor.MessageProcessor._process_with_ai.__module__
        == "app.whatsapp.processor_ai_flow"
    )
    assert (
        processor.MessageProcessor._execute_function.__module__
        == "app.whatsapp.processor_ai_flow"
    )
    assert (
        processor.MessageProcessor._send_response.__module__
        == "app.whatsapp.processor_response_flow"
    )
    assert (
        processor.MessageProcessor._transfer_to_human.__module__
        == "app.whatsapp.processor_response_flow"
    )


def test_processor_e_helpers_respeitam_limites_modulares():
    assert _line_count("processor.py") < 700
    assert _line_count("catalog_query_helpers.py") < 700
    assert _line_count("conversation_helpers.py") < 700
    assert _line_count("processor_checkout_support.py") < 400
    assert _line_count("processor_checkout_flow.py") < 900
    assert _line_count("processor_order_draft_flow.py") < 500
    assert _line_count("processor_product_clarification_flow.py") < 350
    assert _line_count("processor_operational_flow.py") < 150
    assert _line_count("processor_ai_flow.py") < 400
    assert _line_count("processor_response_flow.py") < 350
