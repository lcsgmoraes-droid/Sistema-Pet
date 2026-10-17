"""Intervalos, equipe e contratos das agendas em banco SQLite descartavel."""

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.banho_tosa_agenda_capacity import (
    montar_capacidade_dia,
    validar_capacidade_agenda,
)
from app.banho_tosa_agenda_slots import _ocupacao_recurso_no_slot, sugerir_slots_agenda
from app.banho_tosa_api import agenda_routes
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAgendamentoServico,
    BanhoTosaConfiguracao,
    BanhoTosaRecurso,
)
from app.banho_tosa_schemas import (
    BanhoTosaAgendamentoCreate,
    BanhoTosaAgendamentoStatusUpdate,
    BanhoTosaCapacidadeDiaResponse,
)
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra dependencias dos modelos
from app.models import Cliente, Pet, Tenant, User
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.veterinario_agendamentos import _garantir_sem_conflitos_agendamento
from app.veterinario_models import AgendamentoVet, ConsultorioVet
from app.veterinario_schemas import AgendamentoCreate, AgendamentoUpdate


@pytest.fixture()
def cenario():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Cliente.__table__,
            Pet.__table__,
            ConsultorioVet.__table__,
            AgendamentoVet.__table__,
            BanhoTosaAgendamento.__table__,
            BanhoTosaAgendamentoServico.__table__,
            BanhoTosaConfiguracao.__table__,
            BanhoTosaRecurso.__table__,
        ],
    )
    db = Session(engine)
    a, b = uuid4(), uuid4()
    for tid, offset in [(a, 0), (b, 10)]:
        db.execute(
            Tenant.__table__.insert(),
            {"id": str(tid), "name": str(tid), "name_normalized": str(tid)},
        )
        db.execute(
            User.__table__.insert(),
            {
                "id": offset + 1,
                "tenant_id": tid,
                "email": f"qa{offset}@example.invalid",
            },
        )
        db.execute(
            Cliente.__table__.insert(),
            [
                {
                    "id": offset + 1,
                    "tenant_id": tid,
                    "user_id": offset + 1,
                    "codigo": "TUTOR",
                    "nome": "Tutor QA",
                    "ativo": True,
                },
                {
                    "id": offset + 2,
                    "tenant_id": tid,
                    "user_id": offset + 1,
                    "codigo": "VET",
                    "nome": "Profissional QA",
                    "ativo": True,
                },
            ],
        )
        for numero in range(1, 5):
            db.execute(
                Pet.__table__.insert(),
                {
                    "id": offset + numero,
                    "tenant_id": tid,
                    "user_id": offset + 1,
                    "cliente_id": offset + 1,
                    "codigo": str(numero),
                    "nome": "Pet QA",
                    "especie": "Cachorro",
                },
            )
        db.execute(
            ConsultorioVet.__table__.insert(),
            {"id": offset + 1, "tenant_id": tid, "nome": "Sala QA", "ativo": True},
        )
        db.execute(
            BanhoTosaRecurso.__table__.insert(),
            [
                {
                    "id": offset + 1,
                    "tenant_id": tid,
                    "nome": "Recurso capacidade2",
                    "tipo": "banheira",
                    "capacidade_simultanea": 2,
                },
                {
                    "id": offset + 2,
                    "tenant_id": tid,
                    "nome": "Outro recurso",
                    "tipo": "mesa",
                    "capacidade_simultanea": 1,
                },
            ],
        )
    db.commit()
    set_current_tenant(a)
    try:
        yield SimpleNamespace(db=db, a=a, b=b)
    finally:
        db.close()
        clear_current_tenant()
        engine.dispose()


def _bt(
    c,
    *,
    numero=1,
    pet=1,
    recurso=1,
    inicio="2030-10-20T09:00",
    fim="2030-10-20T10:00",
    tenant=None,
    status="agendado",
):
    c.db.execute(
        BanhoTosaAgendamento.__table__.insert(),
        {
            "id": numero,
            "tenant_id": tenant or c.a,
            "pet_id": pet,
            "cliente_id": 1,
            "recurso_id": recurso,
            "data_hora_inicio": datetime.fromisoformat(inicio),
            "data_hora_fim_prevista": datetime.fromisoformat(fim),
            "status": status,
        },
    )
    c.db.commit()


def _capacidade(
    c, *, pet=3, recurso=1, inicio="2030-10-20T09:30", fim="2030-10-20T10:30", **kwargs
):
    return validar_capacidade_agenda(
        c.db,
        c.a,
        pet_id=pet,
        recurso_id=recurso,
        inicio=datetime.fromisoformat(inicio),
        fim=datetime.fromisoformat(fim),
        **kwargs,
    )


def test_capacidade_usa_pico_e_sugestao_nao_soma_reservas_adjacentes(cenario):
    c = cenario
    _bt(c)
    _bt(c, numero=2, pet=2, inicio="2030-10-20T10:00", fim="2030-10-20T11:00")
    assert _capacidade(c).id == 1
    itens = c.db.query(BanhoTosaAgendamento).all()
    assert (
        _ocupacao_recurso_no_slot(
            itens, 1, datetime(2030, 10, 20, 9, 30), datetime(2030, 10, 20, 10, 30)
        )
        == 1
    )


def test_capacidade_bloqueia_pico_real_e_ignora_outro_recurso(cenario):
    c = cenario
    _bt(c)
    _bt(c, numero=2, pet=2, inicio="2030-10-20T09:15", fim="2030-10-20T10:15")
    with pytest.raises(HTTPException) as exc:
        _capacidade(c)
    assert exc.value.status_code == 409
    assert _capacidade(c, recurso=2).id == 2


def test_edicao_ignora_proprio_agendamento_na_capacidade(cenario):
    c = cenario
    _bt(c, recurso=2)
    assert _capacidade(c, pet=1, recurso=2, ignorar_agendamento_id=1).id == 2
    with pytest.raises(HTTPException):
        _capacidade(c, pet=1, recurso=2)


@pytest.mark.parametrize(
    "status,outro_tenant",
    [("agendado", False), ("cancelado", False), ("agendado", True)],
)
def test_bt_vespera_ocupa_abertura_so_ativa_no_mesmo_tenant(
    cenario, status, outro_tenant
):
    c = cenario
    _bt(
        c,
        recurso=2,
        inicio="2030-10-19T23:00",
        fim="2030-10-20T09:00",
        status=status,
        tenant=c.b if outro_tenant else None,
    )
    slots = sugerir_slots_agenda(
        c.db, c.a, data_ref=date(2030, 10, 20), recurso_id=2, limit=50
    )
    horarios = {item["horario_inicio"].strftime("%H:%M") for item in slots}
    ativa = status == "agendado" and not outro_tenant
    assert ("08:00" not in horarios) == ativa
    assert "09:00" in horarios
    resumo = montar_capacidade_dia(c.db, c.a, date(2030, 10, 20))
    serializado = BanhoTosaCapacidadeDiaResponse.model_validate(resumo).model_dump(
        mode="json"
    )
    recurso = next(item for item in serializado["recursos"] if item["recurso_id"] == 2)
    assert serializado["total_agendamentos"] == int(ativa)
    if ativa:
        assert recurso["intervalos_ocupados"] == [
            {
                "data_hora_inicio": "2030-10-20T00:00:00",
                "data_hora_fim_prevista": "2030-10-20T09:00:00",
            }
        ]
        assert recurso["minutos_ocupados"] == 9 * 60
    else:
        assert recurso["intervalos_ocupados"] == []
    # Um payload legado sem o campo novo continua valido e recebe lista vazia.
    for item in serializado["recursos"]:
        item.pop("intervalos_ocupados")
    legado = BanhoTosaCapacidadeDiaResponse.model_validate(serializado)
    assert all(item.intervalos_ocupados == [] for item in legado.recursos)


def test_reserva_de_outro_tenant_nao_ocupa_recurso_da_loja(cenario):
    c = cenario
    _bt(c, tenant=c.b)
    assert _capacidade(c, recurso=1, pet=1).id == 1
    with pytest.raises(HTTPException) as exc:
        _capacidade(c, recurso=11)
    assert exc.value.status_code == 404


@pytest.mark.parametrize(
    "campo", ["profissional_principal_id", "banhista_id", "tosador_id"]
)
def test_equipe_de_outro_tenant_e_recusada_antes_de_gravar(cenario, campo):
    with pytest.raises(HTTPException) as exc:
        _capacidade(cenario, **{campo: 12})
    assert exc.value.status_code == 404
    assert cenario.db.query(BanhoTosaAgendamento).count() == 0


def _vet(c, inicio, duracao=30, status="agendado", tenant=None):
    c.db.execute(
        AgendamentoVet.__table__.insert(),
        {
            "id": 1,
            "tenant_id": tenant or c.a,
            "pet_id": 1,
            "cliente_id": 1,
            "user_id": 1,
            "veterinario_id": 2,
            "consultorio_id": 1,
            "data_hora": datetime.fromisoformat(inicio),
            "duracao_minutos": duracao,
            "status": status,
        },
    )
    c.db.commit()


def _conflito_vet(c, inicio, ignorar=None):
    return _garantir_sem_conflitos_agendamento(
        c.db,
        tenant_id=c.a,
        data_hora=datetime.fromisoformat(inicio),
        duracao_minutos=30,
        veterinario_id=2,
        consultorio_id=1,
        agendamento_id_ignorar=ignorar,
    )


@pytest.mark.parametrize(
    "duracao,novo", [(30, "2030-10-21T00:05"), (1500, "2030-10-21T12:00")]
)
def test_vet_bloqueia_conflito_que_comecou_em_dia_anterior(cenario, duracao, novo):
    _vet(cenario, "2030-10-20T23:50", duracao)
    with pytest.raises(HTTPException) as exc:
        _conflito_vet(cenario, novo)
    assert exc.value.status_code == 409


def test_vet_aceita_fronteira_adjacente_e_edicao_do_proprio_id(cenario):
    _vet(cenario, "2030-10-20T23:50")
    _conflito_vet(cenario, "2030-10-21T00:20")
    _conflito_vet(cenario, "2030-10-21T00:05", ignorar=1)


@pytest.mark.parametrize("outro_tenant", [False, True])
def test_vet_ignora_cancelada_ou_registro_de_outro_tenant(cenario, outro_tenant):
    _vet(
        cenario,
        "2030-10-20T23:50",
        status="agendado" if outro_tenant else "cancelado",
        tenant=cenario.b if outro_tenant else None,
    )
    _conflito_vet(cenario, "2030-10-21T00:05")


@pytest.mark.parametrize(
    "data_hora",
    ["2030-10-20T10:00", "2030-10-20T10:00:00Z", "2030-10-20T10:00:00-03:00"],
)
def test_schemas_preservam_horario_de_parede_novo_sem_reescrever_legado(data_hora):
    esperado = datetime(2030, 10, 20, 10)
    assert AgendamentoCreate(pet_id=1, data_hora=data_hora).data_hora == esperado
    assert AgendamentoUpdate(data_hora=data_hora).data_hora == esperado
    banho = BanhoTosaAgendamentoCreate(
        cliente_id=1,
        pet_id=1,
        data_hora_inicio=data_hora,
        data_hora_fim_prevista="2030-10-20T11:00",
    )
    assert banho.data_hora_inicio == esperado
    assert banho.data_hora_fim_prevista == datetime(2030, 10, 20, 11)
    assert AgendamentoUpdate(observacoes="QA").model_dump(exclude_unset=True) == {
        "observacoes": "QA"
    }


def test_vet_recusa_status_desconhecido_e_preserva_status_validos():
    with pytest.raises(ValidationError):
        AgendamentoUpdate(status="qualquer_coisa")
    assert AgendamentoUpdate(status="faltou").status == "faltou"


def test_bt_recusa_status_arbitrario_e_aceita_etapa_configurada(cenario, monkeypatch):
    c = cenario
    _bt(c)
    c.db.add(
        BanhoTosaConfiguracao(
            tenant_id=c.a,
            fluxo_etapas=["chegou", "customizado_qa", "pronto"],
            ativo=True,
        )
    )
    c.db.commit()
    monkeypatch.setattr(
        agenda_routes,
        "sincronizar_lembretes_agendamento_banho_tosa",
        lambda *_args, **_kwargs: None,
    )
    actor = c.db.query(User).filter(User.id == 1).one()
    with pytest.raises(HTTPException) as exc:
        agenda_routes.atualizar_status_agendamento(
            1,
            BanhoTosaAgendamentoStatusUpdate(status="qualquer_coisa"),
            db=c.db,
            current=(actor, c.a),
        )
    assert exc.value.status_code == 422
    c.db.expire_all()
    assert c.db.query(BanhoTosaAgendamento).one().status == "agendado"
    resultado = agenda_routes.atualizar_status_agendamento(
        1,
        BanhoTosaAgendamentoStatusUpdate(status="customizado_qa"),
        db=c.db,
        current=(actor, c.a),
    )
    assert resultado["status"] == "customizado_qa"
