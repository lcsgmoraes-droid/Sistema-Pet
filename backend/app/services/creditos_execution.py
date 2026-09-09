"""Ponte entre a carteira e os endpoints legados, sem repetir chamadas pagas."""

import logging

from fastapi import HTTPException

from app.services import creditos_service
from app.services.creditos_catalog import CreditosError, get_creditos_mode

logger = logging.getLogger(__name__)


def creditos_http_error(exc: CreditosError) -> HTTPException:
    return HTTPException(exc.status_code, {"code": exc.code, "message": exc.message})


def pending_error(operation_id: str) -> HTTPException:
    return HTTPException(
        409,
        {
            "code": "credit_operation_pending",
            "operation_id": operation_id,
            "message": "A geracao esta em processamento ou aguardando confirmacao. Consulte o resultado sem gerar novamente.",
        },
    )


def begin_credit_operation(
    db, tenant_id, actor_user_id, operation_id, service_code, request_payload
):
    try:
        mode = get_creditos_mode(tenant_id)
        if mode == "off":
            if operation_id:
                raise HTTPException(
                    409,
                    "O modo da carteira mudou. Consulte a operacao anterior antes de continuar.",
                )
            return {"should_execute": True, "operation_id": None}
        if not operation_id:
            raise HTTPException(
                428,
                {
                    "code": "credit_quote_required",
                    "message": "Confira e confirme o orcamento antes de gerar com IA.",
                },
            )
        result = creditos_service.start_operation(
            db,
            tenant_id,
            actor_user_id,
            str(operation_id),
            service_code,
            request_payload,
        )
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc
    if not result["should_execute"] and result["status"] != "completed":
        if result["status"] == "failed":
            raise HTTPException(
                409,
                {
                    "code": "credit_operation_failed",
                    "message": "Esta geracao falhou. Para uma nova tentativa, confira um novo orcamento.",
                },
            )
        raise pending_error(str(operation_id))
    return result


def complete_credit_operation(
    db, tenant_id, actor_user_id, operation_id, result, usage
):
    if not operation_id:
        return result
    try:
        creditos_service.complete_operation(
            db,
            tenant_id,
            actor_user_id,
            str(operation_id),
            result_payload=result,
            usage_metadata=usage,
        )
    except Exception as exc:
        # Se gravar a conclusao falhar, nao soltar a reserva nem executar a IA de novo.
        db.rollback()
        logger.error("Conclusao de creditos pendente: %s", type(exc).__name__)
        raise pending_error(str(operation_id)) from exc
    return result


def fail_credit_operation(db, tenant_id, actor_user_id, operation_id, exc, usage):
    if not operation_id:
        return
    # Uma resposta recebida mas inutilizavel e falha do servico para o cliente.
    # Seu custo interno permanece registrado; nao presumimos reembolso do fornecedor.
    definite = bool(usage.get("response_received"))
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "status_code", None) in {400, 401, 403, 404, 422, 429}:
            definite = True
        current = current.__cause__
    try:
        creditos_service.fail_operation(
            db,
            tenant_id,
            actor_user_id,
            str(operation_id),
            failure_code="generation_failed"
            if definite
            else "provider_outcome_unknown",
            definite_failure=definite,
            usage_metadata=usage,
        )
    except Exception as persistence_error:
        db.rollback()
        logger.error(
            "Registro de falha de creditos pendente: %s",
            type(persistence_error).__name__,
        )
        raise pending_error(str(operation_id)) from persistence_error
    if not definite:
        raise pending_error(str(operation_id)) from exc
