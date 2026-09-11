"""CSC da NFC-e em homologacao, sem persistir nem devolver o segredo."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)

from app.intnfe.client import IntNFeError
from app.intnfe.numbering import emitter_access

CscId = Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")]


class CscInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ambiente_codigo: Literal[2]
    csc_id: CscId
    csc: SecretStr = Field(min_length=1, max_length=4096)
    csc_id_consultado: CscId | None = None
    confirmar_substituicao: bool = False

    @field_validator("ambiente_codigo", mode="before")
    @classmethod
    def strict_environment(cls, value):
        if type(value) is not int:
            raise ValueError("Codigo deve ser inteiro.")
        return value

    @field_validator("confirmar_substituicao", mode="before")
    @classmethod
    def strict_confirmation(cls, value):
        if type(value) is not bool:
            raise ValueError("Confirmacao deve ser booleana.")
        return value


class CscView(BaseModel):
    ambiente_codigo: Literal[2] = 2
    ambiente: Literal["homologacao"] = "homologacao"
    tem_csc: bool
    csc_id: str | None


class CscUpdateView(CscView):
    mensagem: str


class RemoteCsc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    temCsc: bool
    cscId: CscId | None = None

    @field_validator("temCsc", mode="before")
    @classmethod
    def strict_presence(cls, value):
        if type(value) is not bool:
            raise ValueError("Indicador deve ser booleano.")
        return value


class CscError(Exception):
    def __init__(self, code, message, *, status=409, correlation=None, refresh=True):
        super().__init__(message)
        self.code = code
        self.status = status
        self.correlation = correlation
        self.refresh = refresh


def _state(raw):
    try:
        state = RemoteCsc.model_validate(raw)
        if state.temCsc != bool(state.cscId):
            raise ValueError
        return state
    except (ValidationError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None


def _view(state, *, message=None):
    values = CscView(tem_csc=state.temCsc, csc_id=state.cscId).model_dump()
    if message is not None:
        return CscUpdateView(**values, mensagem=message)
    return CscView(**values)


def _provider_error(exc):
    if exc.uncertain:
        return CscError(
            "ResultadoNaoConfirmado",
            "O CSC pode ter sido gravado. Consulte a situação antes de tentar novamente.",
            status=503,
            correlation=exc.correlation,
        )
    if exc.status == 404:
        return CscError(
            "EmitenteNaoEncontrado",
            "O emitente não foi encontrado na conta do integrador. Consulte o vínculo.",
            status=404,
            correlation=exc.correlation,
        )
    if exc.code in {"CscInvalido", "DadosRecusados"}:
        return CscError(
            "CscInvalido",
            "A IntNFe recusou o ID ou o código. Confira os dados obtidos na SEFAZ.",
            status=422,
            correlation=exc.correlation,
        )
    return CscError(
        exc.code,
        "Não foi possível consultar ou salvar o CSC. Tente novamente ou acione o suporte.",
        status=503,
        correlation=exc.correlation,
    )


def read_csc(db, tenant_id, api):
    try:
        connection, token = emitter_access(db, tenant_id, api)
        return _view(_state(api.csc(token, connection.emitente_id)))
    except IntNFeError as exc:
        raise _provider_error(exc) from None


def save_csc(db, tenant_id, api, request, audit):
    attempted = False
    try:
        connection, token = emitter_access(db, tenant_id, api)
        current = _state(api.csc(token, connection.emitente_id))
        if current.cscId != request.csc_id_consultado:
            raise CscError(
                "CscAlterado",
                "O CSC mudou desde a consulta. Atualize a situação e revise antes de salvar.",
            )
        if current.temCsc and not request.confirmar_substituicao:
            raise CscError(
                "SubstituicaoNaoConfirmada",
                "Confirme a substituição do CSC já cadastrado.",
                status=422,
                refresh=False,
            )
        public_change = {
            "ambienteCodigo": 2,
            "cscId": request.csc_id,
            "substituiu": current.temCsc,
        }
        audit(connection.id, "solicitado", current.cscId, public_change)
        attempted = True
        api.set_csc(
            token,
            connection.emitente_id,
            {"cscId": request.csc_id, "csc": request.csc.get_secret_value()},
        )
        confirmed = _state(api.csc(token, connection.emitente_id))
        if not confirmed.temCsc or confirmed.cscId != request.csc_id:
            raise IntNFeError("RespostaInvalida", uncertain=True)
        audit(connection.id, "confirmado", current.cscId, public_change)
        return _view(
            confirmed,
            message="CSC de homologação salvo. A IntNFe confirmou o ID cadastrado.",
        )
    except CscError:
        raise
    except IntNFeError as exc:
        if attempted and exc.status not in {401, 403, 404, 409, 422, 429}:
            exc.uncertain = True
        if attempted:
            audit(
                connection.id,
                "nao_confirmado" if exc.uncertain else "recusado",
                current.cscId,
                public_change,
                exc,
            )
        raise _provider_error(exc) from None
