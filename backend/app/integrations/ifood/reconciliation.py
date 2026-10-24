"""Bounded on-demand request lifecycle. GET/status never calls the provider."""

from datetime import datetime, timedelta, timezone
import math

from app.ifood_payout_models import IfoodReconciliationJob
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.financial import (
    MODE,
    IfoodFinancialError,
    _actor,
    _iso,
    _scope,
)
from app.integrations.ifood.payouts import competence_period, import_statement


def _utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc)


def _job_query(db, tenant, merchant, competence, mode):
    return db.query(IfoodReconciliationJob).filter_by(
        tenant_id=tenant,
        merchant_id=merchant,
        mode=mode,
        competence=competence,
    )


def job_view(job, *, now=None):
    if job is None:
        return {"job": None, "imported": False}
    now = now or datetime.now(timezone.utc)
    delay = (
        max(0, math.ceil((_utc(job.next_check_at) - now).total_seconds()))
        if job.next_check_at
        else 0
    )
    return {
        "job": {
            "id": job.id,
            "status": job.status,
            "competence": job.competence,
            "last_checked_at": _iso(job.last_checked_at),
            "last_error": job.last_error,
            "next_retry_after_seconds": delay,
        },
        "imported": job.imported,
    }


def get_reconciliation_status(db, tenant_id, merchant_id, competence, mode=MODE):
    competence_period(competence)
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    return job_view(_job_query(db, tenant, merchant, competence, mode).first())


def advance_reconciliation(
    db, tenant_id, merchant_id, competence, actor_id, client, mode=MODE, *, now=None
):
    from app.integrations.ifood.financial_statement import (
        parse_statement,
        IfoodStatementError,
    )

    competence_period(competence)
    now = now or datetime.now(timezone.utc)
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode, lock=True)
    actor = _actor(actor_id)
    job = _job_query(db, tenant, merchant, competence, mode).first()
    if job is not None and (
        job.imported
        or job.status in {"error", "conflict"}
        or (job.next_check_at and _utc(job.next_check_at) > now)
    ):
        return job_view(job, now=now)

    def failed(error):
        # Backoff is evidence too: a 429, transient HTTP or invalid download
        # must not bypass the delay by rolling back the previous snapshot.
        job.attempts += 1
        job.last_checked_at = now
        delay = min(300, 5 * (2 ** min(job.attempts, 6)))
        if getattr(error, "status_code", None) == 429:
            delay = max(60, delay)
        job.next_check_at = now + timedelta(seconds=delay)
        job.last_error = "Não foi possível concluir esta consulta; evidência anterior preservada. Aguarde para tentar novamente."
        db.flush()
        return job_view(job, now=now)

    if job is None or not job.request_id:
        if job is None:
            job = IfoodReconciliationJob(
                tenant_id=tenant,
                merchant_id=merchant,
                mode=mode,
                competence=competence,
                request_id=None,
                status="created",
                attempts=0,
                imported=False,
                actor_id=actor,
            )
            db.add(job)
            db.flush()
        try:
            response = client.create_reconciliation(merchant, competence)
        except IfoodClientError as exc:
            return failed(exc)
        if (
            response.get("merchant_id") != merchant
            or response.get("competence") != competence
        ):
            return failed(
                IfoodFinancialError(
                    "Solicitação de conciliação pertence a outra loja ou competência."
                )
            )
        status = response.get("status")
        request_id = response.get("request_id")
        if status not in {"created", "conflict"} or (
            status == "created" and not request_id
        ):
            return failed(
                IfoodFinancialError("Resposta de solicitação de conciliação inválida.")
            )
        job.request_id = request_id
        job.status = status
        job.last_error = None
        job.last_checked_at = now
        job.next_check_at = now + timedelta(seconds=5)
        db.flush()
        return job_view(job, now=now)
    try:
        response = client.get_reconciliation(merchant, job.request_id, competence)
    except IfoodClientError as exc:
        return failed(exc)
    if (
        response.get("merchant_id") != merchant
        or response.get("competence") != competence
        or response.get("request_id") != job.request_id
    ):
        return failed(
            IfoodFinancialError(
                "Resultado de conciliação não corresponde à solicitação original."
            )
        )
    status = response.get("status")
    if status not in {"created", "enqueue", "processed", "error"}:
        return failed(
            IfoodFinancialError("Estado de conciliação ainda não reconhecido.")
        )
    # Preserve the previous status/snapshot if downloading or parsing fails.
    if status == "processed":
        if not response.get("download_url"):
            return failed(
                IfoodFinancialError(
                    "Arquivo processado sem endereço de download confirmado."
                )
            )
        try:
            content = client.download_statement(response["download_url"])
            parsed = parse_statement(content, merchant, competence)
        except (IfoodStatementError, IfoodClientError) as exc:
            return failed(exc)
        try:
            import_statement(db, tenant, merchant, competence, parsed, actor, mode)
        except IfoodFinancialError as exc:
            return failed(exc)
        job.imported = True
    job.status = status
    job.last_error = None
    job.attempts += 1
    job.last_checked_at = now
    delay = min(300, 5 * (2 ** min(job.attempts, 6)))
    job.next_check_at = now + timedelta(seconds=delay)
    db.flush()
    return job_view(job, now=now)
