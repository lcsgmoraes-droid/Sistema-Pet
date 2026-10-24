"""Read-only Financial V3 adapter. No operational or catalogue methods are used.

Reference: https://developer.ifood.com.br/pt-BR/docs/references (Financial v3.0).
Financial amount.value is BRL decimal text, unlike Virtual Bag centavos.
"""

from datetime import date
import time
from uuid import UUID

from app.integrations.ifood.client import IfoodClient, IfoodClientError


class IfoodFinancialClient(IfoodClient):
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
