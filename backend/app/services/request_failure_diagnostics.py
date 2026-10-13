"""Safe exception fingerprints without messages, locals, SQL or absolute paths."""

import re


CANCELLATION_CODES = frozenset({"client_disconnected", "request_cancelled"})
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.<>-]")


def exception_diagnostics(exc: BaseException) -> dict:
    message = str(exc)
    code = "unhandled_exception"
    if type(exc).__name__ == "CancelledError":
        code = "request_cancelled"
    elif message == "No response returned.":
        code = "asgi_no_response"
    elif message.startswith("Unexpected message received:"):
        code = "asgi_unexpected_message"
    elif message.startswith("[ORM FAIL-FAST]"):
        code = "tenant_context_missing"
    elif message.startswith("[ORM TENANT GUARD]"):
        code = "tenant_insert_guard"
    elif type(exc).__name__ == "InvalidRequestError":
        code = "orm_invalid_request"
        if "mappers failed to initialize" in message:
            code = "orm_mapper_initialization"
        elif "provisioning a new connection" in message:
            code = "orm_session_concurrent_use"
        elif "Closure variable" in message:
            code = "orm_query_configuration"
    elif message in {
        "dictionary changed size during iteration",
        "Set changed size during iteration",
    }:
        code = "shared_collection_changed"

    origins = []
    traceback = exc.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame.f_code
        filename = frame.co_filename.replace("\\", "/").rsplit("/", 1)[-1]
        filename = _SAFE_NAME.sub("_", filename)[:100]
        function = _SAFE_NAME.sub("_", frame.co_name)[:100]
        origins.append(f"{filename}:{function}:{traceback.tb_lineno}")
        traceback = traceback.tb_next
    return {"diagnostic_code": code, "exception_origin": origins[-8:]}


def event_diagnostic_code(event: dict) -> str:
    code = str(event.get("diagnostic_code") or "")
    if code:
        return code
    if event.get("exception_type") and event.get("status_code") is None:
        return "legacy_unknown_status"
    if int(event.get("status_code") or 0) >= 500:
        return "http_server_error"
    return "slow_request"
