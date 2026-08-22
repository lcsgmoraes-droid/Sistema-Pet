from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoCodigo,
    EmpresaGrupoConvite,
    EmpresaGrupoMembro,
)
from app.empresa_grupo_service import EmpresaGrupoService
from app.models import Tenant


AGORA = datetime(2026, 8, 22, 15, 0, tzinfo=timezone.utc)
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"
EMPRESA_C = "33333333-3333-3333-3333-333333333333"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            EmpresaGrupo.__table__,
            EmpresaGrupoMembro.__table__,
            EmpresaGrupoCodigo.__table__,
            EmpresaGrupoConvite.__table__,
        ],
    )
    session = Session(engine)
    session.add_all(
        [
            Tenant(id=EMPRESA_A, name="Loja A", name_normalized="loja a"),
            Tenant(id=EMPRESA_B, name="Loja B", name_normalized="loja b"),
            Tenant(id=EMPRESA_C, name="Loja C", name_normalized="loja c"),
        ]
    )
    session.commit()
    monkeypatch.setattr(
        "app.empresa_grupo_service.log_business_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "app.empresa_grupo_service.registrar_uso_funcionalidade",
        lambda *_args, **_kwargs: True,
    )
    try:
        yield session
    finally:
        session.close()


def test_codigo_permanece_no_mes_e_troca_na_competencia_seguinte(db):
    agosto = EmpresaGrupoService(db, agora=AGORA)
    primeiro = agosto.obter_codigo(EMPRESA_A, 10)
    repetido = agosto.obter_codigo(EMPRESA_A, 10)

    setembro = EmpresaGrupoService(
        db, agora=datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)
    ).obter_codigo(EMPRESA_A, 10)

    assert primeiro["codigo"] == repetido["codigo"]
    assert primeiro["competencia"] == "2026-08"
    assert setembro["competencia"] == "2026-09"
    assert setembro["codigo"] != primeiro["codigo"]


def test_convite_exige_aceite_e_adiciona_empresa_ao_grupo(db):
    service = EmpresaGrupoService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Centro")
    codigo_b = service.obter_codigo(EMPRESA_B, 20)["codigo"]

    convite = service.convidar(EMPRESA_A, 10, grupo["id"], codigo_b)
    resumo_antes = service.listar_resumo(EMPRESA_B, 20)

    assert convite["empresa_nome"] == "Loja B"
    assert resumo_antes["grupos"] == []
    assert resumo_antes["convites_pendentes"][0]["grupo_nome"] == "Grupo Centro"

    resposta = service.responder_convite(EMPRESA_B, 20, convite["id"], aceitar=True)
    resumo_depois = service.listar_resumo(EMPRESA_A, 10)

    assert resposta["status"] == "aceito"
    assert {
        membro["empresa_nome"] for membro in resumo_depois["grupos"][0]["membros"]
    } == {"Loja A", "Loja B"}


def test_somente_responsavel_pode_convidar_e_destino_pode_responder(db):
    service = EmpresaGrupoService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Seguro")
    codigo_b = service.obter_codigo(EMPRESA_B, 20)["codigo"]
    convite = service.convidar(EMPRESA_A, 10, grupo["id"], codigo_b)

    with pytest.raises(HTTPException) as resposta_indevida:
        service.responder_convite(EMPRESA_C, 30, convite["id"], aceitar=True)
    assert resposta_indevida.value.status_code == 404

    service.responder_convite(EMPRESA_B, 20, convite["id"], aceitar=True)
    codigo_c = service.obter_codigo(EMPRESA_C, 30)["codigo"]

    with pytest.raises(HTTPException) as convite_indevido:
        service.convidar(EMPRESA_B, 20, grupo["id"], codigo_c)
    assert convite_indevido.value.status_code == 403


def test_responsavel_remove_membro_sem_poder_remover_a_si_mesmo(db):
    service = EmpresaGrupoService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Operação")
    codigo_b = service.obter_codigo(EMPRESA_B, 20)["codigo"]
    convite = service.convidar(EMPRESA_A, 10, grupo["id"], codigo_b)
    service.responder_convite(EMPRESA_B, 20, convite["id"], aceitar=True)

    service.remover_membro(EMPRESA_A, 10, grupo["id"], EMPRESA_B)
    resumo_b = service.listar_resumo(EMPRESA_B, 20)
    assert resumo_b["grupos"] == []

    with pytest.raises(HTTPException) as remover_responsavel:
        service.remover_membro(EMPRESA_A, 10, grupo["id"], EMPRESA_A)
    assert remover_responsavel.value.status_code == 400
