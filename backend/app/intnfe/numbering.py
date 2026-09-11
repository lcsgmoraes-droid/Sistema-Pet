"""Sequencias remotas: contexto da empresa, avanco e confirmacao por leitura."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.intnfe.client import IntNFeError
from app.intnfe.presentation import public_status
from app.intnfe.repository import ActivationError, get_connection, get_tenant
from app.intnfe.service import _find

Number = Annotated[int, Field(strict=True, ge=0, le=999_999_999)]
NextNumber = Annotated[int, Field(strict=True, ge=1, le=999_999_999)]


class NumberingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serie: str = Field(pattern=r"^[0-9]{1,3}$")
    ambiente_codigo: Literal[1, 2]
    modelo: Literal[55, 65] = 55
    proximo_numero: NextNumber
    ultimo_numero_consultado: Number

    @field_validator("ambiente_codigo", "modelo", mode="before")
    @classmethod
    def strict_codes(cls, value):
        if type(value) is not int:
            raise ValueError("Codigo deve ser inteiro.")
        return value

    @field_validator("serie")
    @classmethod
    def normalize_series(cls, value):
        if int(value) > 889:
            raise ValueError("Serie fora da faixa permitida.")
        return str(int(value))


class NumberingRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    serie: str = Field(pattern=r"^[0-9]{1,3}$")
    modelo: Literal[55, 65]
    ambienteCodigo: Literal[1, 2]
    ultimoNumero: Number
    proximoNumero: Annotated[int, Field(strict=True, ge=1, le=1_000_000_000)]
    atualizadoEm: datetime | None = None

    @field_validator("ambienteCodigo", "modelo", mode="before")
    @classmethod
    def strict_codes(cls, value):
        return NumberingInput.strict_codes(value)

    @field_validator("serie")
    @classmethod
    def normalize_series(cls, value):
        return NumberingInput.normalize_series(value)


class NumberingView(BaseModel):
    series: list[NumberingRow]


class NumberingUpdateView(NumberingView):
    mensagem: str


class NumberingError(Exception):
    def __init__(self, code, message, *, status=409, correlation=None, refresh=True):
        super().__init__(message)
        self.code = code
        self.status = status
        self.correlation = correlation
        self.refresh = refresh


def _rows(raw):
    try:
        if not isinstance(raw, list):
            raise ValueError
        rows = [NumberingRow.model_validate(item) for item in raw]
        keys = {(row.serie, row.modelo, row.ambienteCodigo) for row in rows}
        if len(keys) != len(rows) or any(
            row.proximoNumero != row.ultimoNumero + 1 for row in rows
        ):
            raise ValueError
        return rows
    except (ValidationError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None


def emitter_access(db, tenant_id, api):
    tenant = get_tenant(db, tenant_id)
    connection = get_connection(db, tenant_id)
    view = public_status(tenant, connection, api.integrador_id)
    if not view["pode_configurar_numeracao"]:
        raise ActivationError(
            "Conclua ou consulte o vínculo desta empresa antes de configurar a IntNFe."
        )
    token = api.integrator_token()
    existing = _find(api, token, connection.cnpj)
    if (
        not existing
        or existing.get("ativo") is not True
        or existing["tenantId"] != connection.emitente_id
        or existing["clientId"] != connection.client_id
    ):
        raise ActivationError(
            "O vínculo com o emissor mudou. Consulte o vínculo antes de continuar."
        )
    return connection, token


def _provider_error(exc):
    if exc.uncertain:
        return NumberingError(
            "ResultadoNaoConfirmado",
            "O ajuste pode ter sido aplicado. Consulte a numeração antes de tentar novamente.",
            status=503,
            correlation=exc.correlation,
        )
    if exc.code == "NumeracaoRetrocede":
        return NumberingError(
            exc.code,
            "O emissor não permite voltar ou repetir a numeração já alcançada. Consulte a sequência atual.",
            status=422,
            correlation=exc.correlation,
        )
    if exc.status == 404:
        return NumberingError(
            "EmitenteNaoEncontrado",
            "O emitente não foi encontrado na conta do integrador. Consulte o vínculo.",
            status=404,
            correlation=exc.correlation,
        )
    return NumberingError(
        exc.code,
        "Não foi possível confirmar a numeração. Consulte novamente ou acione o suporte.",
        status=503,
        correlation=exc.correlation,
    )


def read_numbering(db, tenant_id, api):
    try:
        connection, token = emitter_access(db, tenant_id, api)
        return NumberingView(series=_rows(api.numbering(token, connection.emitente_id)))
    except IntNFeError as exc:
        raise _provider_error(exc) from None


def advance_numbering(db, tenant_id, api, request, audit):
    attempted = False
    accepted = False
    try:
        connection, token = emitter_access(db, tenant_id, api)
        rows = _rows(api.numbering(token, connection.emitente_id))
        current = next(
            (
                row
                for row in rows
                if (row.serie, row.modelo, row.ambienteCodigo)
                == (request.serie, request.modelo, request.ambiente_codigo)
            ),
            None,
        )
        last = current.ultimoNumero if current else 0
        if last != request.ultimo_numero_consultado:
            raise NumberingError(
                "NumeracaoAlterada",
                "A sequência mudou desde a consulta. Atualize os números e revise o ajuste.",
            )
        new_last = request.proximo_numero - 1
        if new_last <= last:
            raise NumberingError(
                "NumeracaoRetrocede",
                "Escolha um próximo número maior que o atual. A numeração só pode avançar.",
                status=422,
            )
        body = {
            "serie": request.serie,
            "ultimoNumero": new_last,
            "ambienteCodigo": request.ambiente_codigo,
            "modelo": request.modelo,
        }
        audit(connection.id, "solicitado", last, body)
        attempted = True
        result = api.set_numbering(token, connection.emitente_id, body)
        accepted = True
        try:
            if not isinstance(result, dict):
                raise ValueError
            acknowledgement = NumberingRow.model_validate(
                {**result, "ultimoNumero": new_last}
            )
        except (ValidationError, ValueError, TypeError):
            raise IntNFeError("RespostaInvalida", uncertain=True) from None
        if (
            acknowledgement.serie != request.serie
            or acknowledgement.ambienteCodigo != request.ambiente_codigo
            or acknowledgement.modelo != request.modelo
            or acknowledgement.proximoNumero != request.proximo_numero
        ):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        # Leitura posterior e a fonte do que a interface exibe como confirmado.
        rows = _rows(api.numbering(token, connection.emitente_id))
        confirmed = next(
            (
                row
                for row in rows
                if (row.serie, row.modelo, row.ambienteCodigo)
                == (request.serie, request.modelo, request.ambiente_codigo)
            ),
            None,
        )
        if not confirmed or confirmed.ultimoNumero < new_last:
            raise IntNFeError("RespostaInvalida", uncertain=True)
        audit(connection.id, "confirmado", last, body)
        return NumberingUpdateView(
            series=rows,
            mensagem="Ajuste confirmado. A lista mostra a sequência atual do emissor.",
        )
    except IntNFeError as exc:
        # Uma falha na leitura posterior tambem deixa um PUT sem confirmacao local.
        if accepted or (
            attempted
            and exc.code != "NumeracaoRetrocede"
            and exc.status not in {401, 403, 404, 409, 422, 429}
        ):
            exc.uncertain = True
        if attempted:
            audit(
                connection.id,
                "nao_confirmado" if exc.uncertain else "recusado",
                last,
                body,
                exc,
            )
        raise _provider_error(exc) from None
