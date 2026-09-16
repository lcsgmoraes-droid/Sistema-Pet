from datetime import datetime, timedelta, timezone

import pytest

from app.intnfe.client import IntNFeError
from app.intnfe.environment import (
    DefaultSeriesInput,
    EnvironmentError,
    EnvironmentInput,
    configure_environment,
    save_default_series,
)
from app.intnfe.service import activate
from tests.unit import test_intnfe_activation as activation_fixtures

intnfe_db = activation_fixtures.intnfe_db
pilot = activation_fixtures.pilot


def _prepare(pilot):
    connection = activate(pilot.db, pilot.id, pilot.api)
    connection.certificado_valido_ate = datetime.now(timezone.utc) + timedelta(days=90)
    pilot.db.commit()
    return connection


def test_homologation_activation_reuses_existing_credentials(pilot):
    connection = _prepare(pilot)
    audits = []
    result = configure_environment(
        pilot.db,
        pilot.id,
        pilot.api,
        EnvironmentInput(
            ambiente_codigo=2,
            serie_nfe="003",
            serie_nfce="023",
            numero_inicial_nfe=4501,
            numero_inicial_nfce=101,
        ),
        lambda connection_id, event, values: audits.append(
            (connection_id, event, values)
        ),
    )
    assert result.habilitada is True
    assert result.ambiente == "homologacao"
    assert result.serie_nfe == "3"
    assert result.serie_nfce == "23"
    assert [item.model_dump() for item in result.configuracoes] == [
        {
            "ambiente_codigo": 2,
            "modelo": 55,
            "serie": "3",
            "numero_inicial": 4501,
        },
        {
            "ambiente_codigo": 2,
            "modelo": 65,
            "serie": "23",
            "numero_inicial": 101,
        },
    ]
    assert connection.production_client_id is None
    assert pilot.api.environment_activations == [("emitente-teste", 2)]
    assert audits[-1][1] == "emissao_direta_ativada"


@pytest.mark.parametrize("value", [True, "4501", 0, 1_000_000_000])
def test_sequence_start_requires_strict_valid_number(value):
    with pytest.raises(ValueError):
        EnvironmentInput(ambiente_codigo=2, numero_inicial_nfe=value)


def test_production_credentials_are_encrypted_and_not_regenerated(pilot):
    connection = _prepare(pilot)
    calls = []

    def create(_token, emitter_id):
        calls.append(emitter_id)
        return {
            "clientId": "cliente-producao",
            "clientSecret": "segredo-producao-ficticio",
        }

    pilot.api.create_production_credentials = create
    pilot.api.emitter_token = lambda client_id, secret: (
        "token-producao"
        if (client_id, secret) == ("cliente-producao", "segredo-producao-ficticio")
        else "token-homologacao"
    )
    request = EnvironmentInput(ambiente_codigo=1, serie_nfe="2", serie_nfce="1")
    configure_environment(pilot.db, pilot.id, pilot.api, request, lambda *_args: None)
    configure_environment(pilot.db, pilot.id, pilot.api, request, lambda *_args: None)
    pilot.db.refresh(connection)
    assert calls == ["emitente-teste"]
    assert connection.production_client_id == "cliente-producao"
    assert connection.production_client_secret == "segredo-producao-ficticio"
    assert (
        "segredo-producao-ficticio" not in connection.production_client_secret_encrypted
    )
    assert connection.emission_environment == 1
    assert pilot.api.environment_activations == [
        ("emitente-teste", 1),
        ("emitente-teste", 1),
    ]


def test_same_series_preserves_start_and_new_series_replaces_it(pilot):
    _prepare(pilot)

    def audit(*_args):
        return None

    configure_environment(
        pilot.db,
        pilot.id,
        pilot.api,
        EnvironmentInput(
            ambiente_codigo=2,
            serie_nfe="3",
            numero_inicial_nfe=4501,
        ),
        audit,
    )
    same = configure_environment(
        pilot.db,
        pilot.id,
        pilot.api,
        EnvironmentInput(
            ambiente_codigo=2,
            serie_nfe="3",
            numero_inicial_nfe=4510,
        ),
        audit,
    )
    assert (
        next(item for item in same.configuracoes if item.modelo == 55).numero_inicial
        == 4501
    )

    changed = configure_environment(
        pilot.db,
        pilot.id,
        pilot.api,
        EnvironmentInput(
            ambiente_codigo=2,
            serie_nfe="4",
            numero_inicial_nfe=1,
        ),
        audit,
    )
    saved = next(item for item in changed.configuracoes if item.modelo == 55)
    assert (saved.serie, saved.numero_inicial) == ("4", 1)


def test_default_series_is_saved_without_activating_environment(pilot):
    connection = _prepare(pilot)
    pilot.api.numbering = lambda *_args: [
        {
            "serie": "003",
            "modelo": 55,
            "ambienteCodigo": 1,
            "ultimoNumero": 1629,
            "proximoNumero": 1630,
        }
    ]
    audits = []

    result = save_default_series(
        pilot.db,
        pilot.id,
        pilot.api,
        DefaultSeriesInput(ambiente_codigo=1, modelo=55, serie="003"),
        lambda connection_id, event, values: audits.append(
            (connection_id, event, values)
        ),
    )

    assert connection.emission_enabled is False
    assert pilot.api.environment_activations == []
    assert connection.nfe_series == "1"
    saved = next(item for item in result.configuracoes if item.modelo == 55)
    assert (saved.ambiente_codigo, saved.serie, saved.numero_inicial) == (1, "3", 1630)
    assert audits[-1][1] == "serie_padrao_salva"


def test_default_series_updates_operational_series_only_for_current_environment(pilot):
    connection = _prepare(pilot)
    connection.emission_environment = 1
    pilot.db.commit()
    pilot.api.numbering = lambda *_args: [
        {
            "serie": "003",
            "modelo": 55,
            "ambienteCodigo": 1,
            "ultimoNumero": 1629,
            "proximoNumero": 1630,
        }
    ]

    save_default_series(
        pilot.db,
        pilot.id,
        pilot.api,
        DefaultSeriesInput(ambiente_codigo=1, modelo=55, serie="3"),
        lambda *_args: None,
    )

    assert connection.nfe_series == "3"


def test_default_series_must_exist_in_selected_model_and_environment(pilot):
    _prepare(pilot)
    pilot.api.numbering = lambda *_args: [
        {
            "serie": "1",
            "modelo": 65,
            "ambienteCodigo": 1,
            "ultimoNumero": 528,
            "proximoNumero": 529,
        }
    ]

    with pytest.raises(EnvironmentError, match="ainda não existe"):
        save_default_series(
            pilot.db,
            pilot.id,
            pilot.api,
            DefaultSeriesInput(ambiente_codigo=1, modelo=55, serie="1"),
            lambda *_args: None,
        )


def test_uncertain_activation_is_reconciled_with_remote_environment(pilot):
    connection = _prepare(pilot)
    pilot.api.activate_emitter_environment = lambda *_args: (_ for _ in ()).throw(
        IntNFeError("RespostaInvalida", uncertain=True)
    )
    pilot.api.emitter_environment = lambda *_args: {"ambienteAtivo": 2}

    result = configure_environment(
        pilot.db,
        pilot.id,
        pilot.api,
        EnvironmentInput(ambiente_codigo=2, serie_nfe="3", serie_nfce="23"),
        lambda *_args: None,
    )

    assert result.habilitada is True
    assert connection.emission_environment == 2


def test_environment_is_not_enabled_when_remote_activation_fails(pilot):
    connection = _prepare(pilot)
    pilot.api.activate_emitter_environment = lambda *_args: (_ for _ in ()).throw(
        IntNFeError("DadosRecusados", status=422)
    )

    with pytest.raises(EnvironmentError, match="ativar o ambiente"):
        configure_environment(
            pilot.db,
            pilot.id,
            pilot.api,
            EnvironmentInput(ambiente_codigo=2, serie_nfe="3", serie_nfce="23"),
            lambda *_args: None,
        )

    pilot.db.refresh(connection)
    assert connection.emission_enabled is False
