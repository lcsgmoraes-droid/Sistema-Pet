"""CSC da NFC-e por ambiente, sem persistir nem devolver o segredo."""

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
    ambiente_codigo: Literal[1, 2]
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


class CscEnvironmentView(BaseModel):
    ambiente_codigo: Literal[1, 2]
    ambiente: Literal["producao", "homologacao"]
    tem_csc: bool
    csc_id: str | None


class CscView(BaseModel):
    ambientes: list[CscEnvironmentView]


class CscUpdateView(CscView):
    mensagem: str


class RemoteCsc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    temCscHomologacao: bool
    cscIdHomologacao: CscId | None = None
    temCscProducao: bool
    cscIdProducao: CscId | None = None

    @field_validator("temCscHomologacao", "temCscProducao", mode="before")
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
        if state.temCscHomologacao != bool(state.cscIdHomologacao) or (
            state.temCscProducao != bool(state.cscIdProducao)
        ):
            raise ValueError
        return state
    except (ValidationError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None


def _environment(state, ambiente_codigo):
    if ambiente_codigo == 1:
        return CscEnvironmentView(
            ambiente_codigo=1,
            ambiente="producao",
            tem_csc=state.temCscProducao,
            csc_id=state.cscIdProducao,
        )
    return CscEnvironmentView(
        ambiente_codigo=2,
        ambiente="homologacao",
        tem_csc=state.temCscHomologacao,
        csc_id=state.cscIdHomologacao,
    )


def _view(state, *, message=None):
    values = CscView(
        ambientes=[_environment(state, 2), _environment(state, 1)]
    ).model_dump()
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
        current_environment = _environment(current, request.ambiente_codigo)
        other_environment = _environment(
            current, 1 if request.ambiente_codigo == 2 else 2
        )
        if current_environment.csc_id != request.csc_id_consultado:
            raise CscError(
                "CscAlterado",
                "O CSC mudou desde a consulta. Atualize a situação e revise antes de salvar.",
            )
        if current_environment.tem_csc and not request.confirmar_substituicao:
            raise CscError(
                "SubstituicaoNaoConfirmada",
                "Confirme a substituição do CSC já cadastrado.",
                status=422,
                refresh=False,
            )
        public_change = {
            "ambienteCodigo": request.ambiente_codigo,
            "cscId": request.csc_id,
            "substituiu": current_environment.tem_csc,
        }
        audit(connection.id, "solicitado", current_environment.csc_id, public_change)
        attempted = True
        api.set_csc(
            token,
            connection.emitente_id,
            {
                "cscId": request.csc_id,
                "csc": request.csc.get_secret_value(),
                "ambienteCodigo": request.ambiente_codigo,
            },
        )
        confirmed = _state(api.csc(token, connection.emitente_id))
        confirmed_environment = _environment(confirmed, request.ambiente_codigo)
        confirmed_other = _environment(
            confirmed, 1 if request.ambiente_codigo == 2 else 2
        )
        if (
            not confirmed_environment.tem_csc
            or confirmed_environment.csc_id != request.csc_id
            or confirmed_other != other_environment
        ):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        audit(connection.id, "confirmado", current_environment.csc_id, public_change)
        environment_name = "produção" if request.ambiente_codigo == 1 else "homologação"
        return _view(
            confirmed,
            message=f"CSC de {environment_name} salvo. A IntNFe confirmou o ID cadastrado.",
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
                current_environment.csc_id,
                public_change,
                exc,
            )
        raise _provider_error(exc) from None
