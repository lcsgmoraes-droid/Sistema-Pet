"""Read-only Financial V3 adapter. No operational or catalogue methods are used.

Reference: https://developer.ifood.com.br/pt-BR/docs/references (Financial v3.0).
Financial amount.value is BRL decimal text, unlike Virtual Bag centavos.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import logging
import re
import threading
import time
from urllib.parse import unquote, urlsplit
from uuid import UUID

import httpx

from app.integrations.ifood.client import IfoodClient, IfoodClientError

MAX_JSON_BYTES = 2_000_000
MAX_DOWNLOAD_BYTES = 8_000_000
# Exact sandbox host in Financial V3 Reference's download example. No wildcard,
# generic S3 host, production bucket, IP address, or caller-supplied allowlist.
STATEMENT_HOSTS = frozenset({"payout-platform-api-files-sandbox.s3.amazonaws.com"})
JOB_STATES = frozenset({"created", "enqueue", "processed", "error"})


def _merchant(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise IfoodClientError("Identificador da loja financeira invalido.") from None


def _competence(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise IfoodClientError("Competencia financeira invalida; use AAAA-MM.")
    try:
        date.fromisoformat(value + "-01")
    except ValueError:
        raise IfoodClientError(
            "Competencia financeira invalida; use AAAA-MM."
        ) from None
    return value


def _date(value):
    try:
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise IfoodClientError("Data financeira invalida.") from None


def _money(value):
    try:
        if value is None or isinstance(value, bool):
            raise ValueError
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) > Decimal("999999999999.99"):
            raise ValueError
        if result != result.quantize(Decimal("0.01")):
            raise ValueError
        return format(result.quantize(Decimal("0.01")), ".2f")
    except (ValueError, TypeError, InvalidOperation):
        raise IfoodClientError(
            "Valor financeiro invalido na resposta do iFood."
        ) from None


def _download_url(value):
    try:
        if not isinstance(value, str) or not value or len(value) > 12_000:
            raise ValueError
        if any(ord(char) < 33 or ord(char) == 127 for char in value):
            raise ValueError
        parts = urlsplit(value)
        path = unquote(parts.path)
        if (
            parts.scheme != "https"
            or parts.hostname not in STATEMENT_HOSTS
            or parts.username is not None
            or parts.password is not None
            or parts.port not in (None, 443)
            or parts.fragment
            or not path.startswith("/reconciliacao-externa/on-demand/")
            or not path.endswith((".csv", ".csv.gz"))
            or "\\" in path
            or any(part in (".", "..") for part in path.split("/"))
        ):
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise IfoodClientError(
            "Download bloqueado: endereco fora do host oficial de homologacao verificado."
        ) from None


class _PrivateDownloadLogs(logging.Filter):
    """HTTPX INFO messages contain the full signed URL; omit this thread only."""

    def __init__(self):
        super().__init__()
        self.thread_id = threading.get_ident()

    def filter(self, record):
        return record.thread != self.thread_id


class IfoodFinancialClient(IfoodClient):
    def __init__(self, **kwargs):
        # Separate downloader never inherits API Authorization headers or cookies.
        # Reuse only the injected test transport, not the API HTTP session.
        self._download_transport = kwargs.get("transport")
        self._download_timeout = max(1, kwargs.get("timeout_seconds", 15))
        super().__init__(**kwargs)

    def _financial_get(self, path, **kwargs):
        try:
            return self._request("GET", path, **kwargs)
        except IfoodClientError as exc:
            if exc.status_code != 401:
                raise
            self._token_expires_at = 0
            return self._request("GET", path, **kwargs)

    def _financial_body(self, response, *, accepted=(200,)):
        if (
            response.status_code not in accepted
            or len(response.content) > MAX_JSON_BYTES
        ):
            raise IfoodClientError("Resposta financeira invalida ou muito grande.")
        payload = self._json_response(response)
        if isinstance(payload, list) and len(payload) == 1:
            payload = payload[0]
        if not isinstance(payload, dict):
            raise IfoodClientError("Envelope financeiro invalido.")
        return payload

    def fetch_financial_pages(
        self, merchant_id: str, begin_date: date, end_date: date
    ) -> list[dict]:
        """Return only a complete bounded window. Caller commits after validation.

        This first release intentionally cannot request production Financial data.
        A 429 is surfaced without immediate retry; the user can retry later.
        """
        try:
            merchant_id = str(UUID(merchant_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise IfoodClientError(
                "Merchant ID invalido para a consulta financeira."
            ) from exc
        if end_date < begin_date or (end_date - begin_date).days >= 33:
            raise IfoodClientError(
                "Consulte um periodo de ate 33 dias, incluindo inicio e fim."
            )
        pages = []
        count = 0
        started = time.monotonic()
        for page in range(1, 101):
            if time.monotonic() - started > 60:
                raise IfoodClientError(
                    "Consulta financeira excedeu o tempo limite; nenhum dado parcial foi importado."
                )
            request = dict(
                headers={"x-request-homologation": "true"},
                params={
                    "beginDate": begin_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "page": page,
                    "size": 100,
                },
            )
            path = f"/financial/v3.0/merchants/{merchant_id}/financial-events"
            try:
                response = self._request("GET", path, **request)
            except IfoodClientError as exc:
                if exc.status_code != 401:
                    raise
                # Retry only this idempotent read, once, with renewed credentials.
                self._token_expires_at = 0
                response = self._request("GET", path, **request)
            if response.status_code != 200 or len(response.content) > 2_000_000:
                raise IfoodClientError(
                    "O iFood retornou uma pagina financeira invalida ou muito grande."
                )
            payload = self._json_response(response)
            # Reference schema is an object; its Example Value wraps exactly
            # one envelope in an array. Accept that documented variant only.
            if (
                isinstance(payload, list)
                and len(payload) == 1
                and isinstance(payload[0], dict)
            ):
                payload = payload[0]
            if (
                not isinstance(payload, dict)
                or type(payload.get("page")) is not int
                or payload["page"] != page
                or type(payload.get("hasNextPage")) is not bool
                or not isinstance(payload.get("financialEvents"), list)
            ):
                raise IfoodClientError(
                    "Paginacao financeira invalida; nenhum dado parcial foi importado."
                )
            count += len(payload["financialEvents"])
            if count > 10_000:
                raise IfoodClientError(
                    "A consulta financeira excedeu o limite; reduza o periodo."
                )
            pages.append(payload)
            if not payload["hasNextPage"]:
                return pages
            if not payload["financialEvents"]:
                raise IfoodClientError(
                    "Pagina financeira vazia com continuacao; consulte novamente mais tarde."
                )
        raise IfoodClientError(
            "A consulta financeira excedeu o limite de paginas; reduza o periodo."
        )

    def fetch_settlements(self, merchant_id, begin_date, end_date, basis="calculation"):
        """Validated provider envelope; no bank receipt or title/saldo mapping inferred.

        Keep documented grouped and direct-title variants. Caller must sanitize
        accountDetails before persistence/UI. Amounts remain signed BRL decimals.
        """
        merchant = _merchant(merchant_id)
        begin, end = _date(begin_date), _date(end_date)
        if (
            end < begin
            or (end - begin).days > 89
            or basis not in {"calculation", "payment"}
        ):
            raise IfoodClientError(
                "Consulte repasses por calculo ou pagamento em ate 90 dias."
            )
        prefix = "Calculation" if basis == "calculation" else "Payment"
        response = self._financial_get(
            f"/financial/v3.0/merchants/{merchant}/settlements",
            headers={"x-request-homologation": "true"},
            params={
                f"begin{prefix}Date": begin.isoformat(),
                f"end{prefix}Date": end.isoformat(),
            },
        )
        payload = self._financial_body(response)
        if (
            _merchant(payload.get("merchantId")) != merchant
            or _date(payload.get("beginDate")) != begin
            or _date(payload.get("endDate")) != end
            or not isinstance(payload.get("settlements"), list)
        ):
            raise IfoodClientError(
                "Resposta de repasses nao corresponde a loja e periodo consultados."
            )
        consolidated = payload.get("consolidatedMerchants", [])
        if not isinstance(consolidated, list) or any(
            _merchant(mid) != merchant for mid in consolidated
        ):
            raise IfoodClientError(
                "Repasse consolidado com outra loja exige conferencia separada."
            )
        payload["balance"] = _money(payload.get("balance"))
        count = 0
        for group in payload["settlements"]:
            if not isinstance(group, dict):
                raise IfoodClientError("Grupo de repasses invalido.")
            if "closingItems" in group:
                start = _date(group.get("startDateCalculation"))
                finish = _date(group.get("endDateCalculation"))
                if finish < start or not isinstance(group["closingItems"], list):
                    raise IfoodClientError("Periodo de apuracao do repasse invalido.")
                if "id" in group:
                    raise IfoodClientError(
                        "Resposta mistura grupo e titulo financeiro."
                    )
                items = group["closingItems"]
            else:
                items = [group]
            count += len(items)
            if count > 10_000:
                raise IfoodClientError(
                    "Consulta de repasses excedeu o limite; reduza o periodo."
                )
            for item in items:
                if not isinstance(item, dict) or any(
                    not isinstance(item.get(key), str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", item[key])
                    for key in ("id", "type", "status")
                ):
                    raise IfoodClientError(
                        "Titulo financeiro sem identificacao valida."
                    )
                item["amount"] = _money(item.get("amount"))
                if item.get("paymentDate") is not None:
                    _date(item["paymentDate"])
        return payload

    def create_reconciliation(self, merchant_id, competence):
        merchant, month = _merchant(merchant_id), _competence(competence)
        try:
            response = self._request(
                "POST",
                f"/financial/v3.0/merchants/{merchant}/reconciliation/on-demand",
                headers={"x-request-homologation": "true"},
                json={"competence": month},
            )
        except IfoodClientError as exc:
            if exc.status_code != 409:
                raise
            # Reference's conflict body need not contain a requestId. The caller
            # may reuse a previously persisted matching job; never invent an ID.
            return dict(
                merchant_id=merchant,
                competence=month,
                request_id=None,
                status="conflict",
                download_url=None,
            )
        body = self._financial_body(response, accepted=(200, 202))
        if (
            _merchant(body.get("merchantId")) != merchant
            or body.get("competence") != month
        ):
            raise IfoodClientError(
                "Arquivo solicitado nao corresponde a loja e competencia."
            )
        request_id = _merchant(body.get("requestId"))
        return dict(
            merchant_id=merchant,
            competence=month,
            request_id=request_id,
            status="created",
            download_url=None,
        )

    def get_reconciliation(self, merchant_id, request_id, competence):
        merchant, request_id, month = (
            _merchant(merchant_id),
            _merchant(request_id),
            _competence(competence),
        )
        response = self._financial_get(
            f"/financial/v3.0/merchants/{merchant}/reconciliation/on-demand/{request_id}",
            headers={"x-request-homologation": "true"},
        )
        body = self._financial_body(response, accepted=(200, 202))
        if (
            _merchant(body.get("merchantId")) != merchant
            or _merchant(body.get("id")) != request_id
            or body.get("competence") != month
            or body.get("status") not in JOB_STATES
        ):
            raise IfoodClientError(
                "Status do arquivo nao corresponde a solicitacao financeira."
            )
        url = None
        if body["status"] == "processed":
            urls = [body[key] for key in ("downloadPath", "filePath") if body.get(key)]
            if not urls or any(value != urls[0] for value in urls):
                raise IfoodClientError(
                    "Arquivo processado sem endereco de download inequivoco."
                )
            url = _download_url(urls[0])
        return dict(
            merchant_id=merchant,
            competence=month,
            request_id=request_id,
            status=body["status"],
            download_url=url,
        )

    def download_statement(self, url):
        """Private signed URL: no redirects, API auth, cookies, proxies or logs."""
        url = _download_url(url)
        private_logs = _PrivateDownloadLogs()
        http_logger = logging.getLogger("httpx")
        http_logger.addFilter(private_logs)
        try:
            with httpx.Client(
                transport=self._download_transport,
                timeout=self._download_timeout,
                follow_redirects=False,
                trust_env=False,
            ) as downloader:
                with downloader.stream(
                    "GET", url, headers={"Accept-Encoding": "identity"}
                ) as response:
                    if response.status_code != 200:
                        raise IfoodClientError(
                            "Nao foi possivel baixar o arquivo financeiro."
                        )
                    length = response.headers.get("Content-Length")
                    if length is not None and (
                        not length.isdigit() or int(length) > MAX_DOWNLOAD_BYTES
                    ):
                        raise IfoodClientError(
                            "Arquivo financeiro excede o limite de download."
                        )
                    content = bytearray()
                    chunks = (
                        [response.content]
                        if response.is_stream_consumed
                        else response.iter_raw(chunk_size=65_536)
                    )
                    for chunk in chunks:
                        if len(content) + len(chunk) > MAX_DOWNLOAD_BYTES:
                            raise IfoodClientError(
                                "Arquivo financeiro excede o limite de download."
                            )
                        content.extend(chunk)
                    if not content:
                        raise IfoodClientError(
                            "Arquivo financeiro vazio; nenhum extrato foi importado."
                        )
                    return bytes(content)
        except httpx.HTTPError:
            # Suppress exception chains containing the private signed URL.
            raise IfoodClientError(
                "Falha ao baixar o arquivo financeiro; tente novamente mais tarde."
            ) from None
        finally:
            http_logger.removeFilter(private_logs)
