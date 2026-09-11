"""Sincroniza o cadastro fiscal permanente do CorePet com a IntNFe."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, ValidationError

from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.intnfe.client import IntNFeError
from app.intnfe.numbering import emitter_access
from app.intnfe.repository import get_tenant


class RemoteAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    codigoMunicipio: str | None = None
    uf: str | None = None
    cep: str | None = None


class RemoteFiscalProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    razaoSocial: str | None = None
    nomeFantasia: str | None = None
    inscricaoEstadual: str | None = None
    inscricaoEstadualSubstitutoTributario: str | None = None
    crt: str | None = None
    inscricaoMunicipal: str | None = None
    endereco: RemoteAddress | None = None
    telefone: str | None = None
    email: str | None = None
    rntrc: str | None = None
    atualizadoEm: datetime | None = None


class FiscalProfileView(BaseModel):
    pronto_para_sincronizar: bool
    sincronizado: bool
    pendencias: list[str]
    diferencas: list[str]
    atualizado_em: datetime | None = None
    mensagem: str


class FiscalProfileError(Exception):
    def __init__(self, code, message, *, status=409, correlation=None, refresh=True):
        super().__init__(message)
        self.code = code
        self.status = status
        self.correlation = correlation
        self.refresh = refresh


LABELS = {
    "razaoSocial": "razão social",
    "nomeFantasia": "nome fantasia",
    "inscricaoEstadual": "inscrição estadual",
    "crt": "regime tributário",
    "inscricaoMunicipal": "inscrição municipal",
    "endereco.logradouro": "logradouro",
    "endereco.numero": "número",
    "endereco.complemento": "complemento",
    "endereco.bairro": "bairro",
    "endereco.municipio": "município",
    "endereco.codigoMunicipio": "código IBGE do município",
    "endereco.uf": "UF",
    "endereco.cep": "CEP",
    "telefone": "telefone",
    "email": "e-mail",
}


def _text(value):
    result = str(value or "").strip()
    return result or None


def _digits(value):
    result = re.sub(r"\D", "", str(value or ""))
    return result or None


def _crt(config):
    if config is None:
        return None
    regime = str(config.regime_tributario or "").strip().casefold()
    if "excesso" in regime and "simples" in regime:
        return "2"
    if "simples" in regime or bool(config.simples_ativo):
        return "1"
    if regime:
        return "3"
    return None


def local_profile(db, tenant_id):
    tenant = get_tenant(db, tenant_id)
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    data = {
        "razaoSocial": _text(tenant.razao_social),
        "nomeFantasia": _text(tenant.name),
        "inscricaoEstadual": _text(tenant.inscricao_estadual),
        "crt": _crt(config),
        "inscricaoMunicipal": _text(tenant.inscricao_municipal),
        "endereco": {
            "logradouro": _text(tenant.endereco),
            "numero": _text(tenant.numero),
            "complemento": _text(tenant.complemento),
            "bairro": _text(tenant.bairro),
            "municipio": _text(tenant.cidade),
            "codigoMunicipio": _digits(getattr(tenant, "codigo_municipio", None)),
            "uf": (_text(tenant.uf) or "").upper() or None,
            "cep": _digits(tenant.cep),
        },
        "telefone": _digits(tenant.telefone),
        "email": _text(tenant.email_resposta) or _text(tenant.email),
    }
    pending = []
    required = (
        ("razaoSocial", data["razaoSocial"]),
        ("inscricaoEstadual", data["inscricaoEstadual"]),
        ("crt", data["crt"]),
        ("endereco.logradouro", data["endereco"]["logradouro"]),
        ("endereco.numero", data["endereco"]["numero"]),
        ("endereco.bairro", data["endereco"]["bairro"]),
        ("endereco.municipio", data["endereco"]["municipio"]),
        ("endereco.codigoMunicipio", data["endereco"]["codigoMunicipio"]),
        ("endereco.uf", data["endereco"]["uf"]),
        ("endereco.cep", data["endereco"]["cep"]),
    )
    for field, value in required:
        if not value:
            pending.append(f"Informe {LABELS[field]} nos dados da empresa.")
    if (
        data["endereco"]["codigoMunicipio"]
        and len(data["endereco"]["codigoMunicipio"]) != 7
    ):
        pending.append("O código IBGE do município deve ter 7 dígitos.")
    if data["endereco"]["uf"] and len(data["endereco"]["uf"]) != 2:
        pending.append("A UF deve ter 2 letras.")
    if data["endereco"]["cep"] and len(data["endereco"]["cep"]) != 8:
        pending.append("O CEP deve ter 8 dígitos.")
    return data, pending


def _remote(raw):
    if raw is None:
        return None
    try:
        return RemoteFiscalProfile.model_validate(raw)
    except (ValidationError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None


def _flatten(data):
    flat = {key: value for key, value in data.items() if key != "endereco"}
    flat.update({f"endereco.{key}": value for key, value in data["endereco"].items()})
    return flat


def _differences(local, remote):
    if remote is None:
        return [LABELS[key] for key, value in _flatten(local).items() if value]
    remote_data = remote.model_dump(
        exclude={"atualizadoEm", "rntrc", "inscricaoEstadualSubstitutoTributario"}
    )
    remote_data["endereco"] = (remote.endereco or RemoteAddress()).model_dump()
    return [
        LABELS[key]
        for key, value in _flatten(local).items()
        if value != _flatten(remote_data).get(key)
    ]


def _view(local, pending, remote, *, message=None):
    differences = _differences(local, remote) if not pending else []
    synced = not pending and remote is not None and not differences
    if message is None:
        if pending:
            message = "Complete os campos indicados para sincronizar com a IntNFe."
        elif synced:
            message = "Os dados fiscais do CorePet e da IntNFe estão sincronizados."
        else:
            message = "Existem dados prontos para sincronizar com a IntNFe."
    return FiscalProfileView(
        pronto_para_sincronizar=not pending,
        sincronizado=synced,
        pendencias=pending,
        diferencas=differences,
        atualizado_em=remote.atualizadoEm if remote else None,
        mensagem=message,
    )


def _provider_error(exc):
    if exc.uncertain:
        return FiscalProfileError(
            "ResultadoNaoConfirmado",
            "Os dados podem ter sido atualizados. Consulte antes de sincronizar novamente.",
            status=503,
            correlation=exc.correlation,
        )
    if exc.status == 422:
        return FiscalProfileError(
            "DadosFiscaisRecusados",
            "A IntNFe recusou um dado fiscal. Confira os campos da empresa.",
            status=422,
            correlation=exc.correlation,
            refresh=False,
        )
    if exc.status == 404:
        return FiscalProfileError(
            "EmitenteNaoEncontrado",
            "O emitente não foi encontrado. Consulte o vínculo.",
            status=404,
            correlation=exc.correlation,
        )
    return FiscalProfileError(
        exc.code,
        "Não foi possível sincronizar os dados fiscais. Tente novamente ou acione o suporte.",
        status=503,
        correlation=exc.correlation,
    )


def read_fiscal_profile(db, tenant_id, api):
    local, pending = local_profile(db, tenant_id)
    try:
        connection, token = emitter_access(db, tenant_id, api)
        remote = _remote(api.fiscal_registration(token, connection.emitente_id))
        return _view(local, pending, remote)
    except IntNFeError as exc:
        raise _provider_error(exc) from None


def sync_fiscal_profile(db, tenant_id, api, audit):
    attempted = False
    local, pending = local_profile(db, tenant_id)
    if pending:
        raise FiscalProfileError(
            "DadosFiscaisPendentes", " ".join(pending), status=422, refresh=False
        )
    try:
        connection, token = emitter_access(db, tenant_id, api)
        current = _remote(api.fiscal_registration(token, connection.emitente_id))
        differences = _differences(local, current)
        if not differences:
            return _view(local, pending, current)
        public_change = {"campos": differences}
        audit(connection.id, "solicitado", public_change)
        attempted = True
        confirmed = _remote(
            api.set_fiscal_registration(token, connection.emitente_id, local)
        )
        if confirmed is None or _differences(local, confirmed):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        audit(connection.id, "confirmado", public_change)
        return _view(
            local,
            pending,
            confirmed,
            message="Dados fiscais sincronizados automaticamente com a IntNFe.",
        )
    except FiscalProfileError:
        raise
    except IntNFeError as exc:
        if attempted and exc.status not in {401, 403, 404, 409, 422, 429}:
            exc.uncertain = True
        if attempted:
            audit(
                connection.id,
                "nao_confirmado" if exc.uncertain else "recusado",
                public_change,
                exc,
            )
        raise _provider_error(exc) from None
