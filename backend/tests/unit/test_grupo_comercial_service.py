from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra Produto etc. no metadata,
# necessario pra resolver a FK de produto_origem_id mesmo so criando um
# subconjunto de tabelas abaixo (create_all so cria o que esta em `tables`,
# mas ainda precisa achar a tabela referenciada pra montar a FK).
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialCodigo,
    GrupoComercialConvite,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.grupo_comercial_service import GrupoComercialService
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
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialCodigo.__table__,
            GrupoComercialConvite.__table__,
            GrupoComercialEstoqueCompartilhado.__table__,
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
        "app.grupo_comercial_service.log_business_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "app.grupo_comercial_service.registrar_uso_funcionalidade",
        lambda *_args, **_kwargs: True,
    )
    try:
        yield session
    finally:
        session.close()


def test_codigo_permanece_no_mes_e_troca_na_competencia_seguinte(db):
    agosto = GrupoComercialService(db, agora=AGORA)
    primeiro = agosto.obter_codigo(EMPRESA_A, 10)
    repetido = agosto.obter_codigo(EMPRESA_A, 10)

    setembro = GrupoComercialService(
        db, agora=datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)
    ).obter_codigo(EMPRESA_A, 10)

    assert primeiro["codigo"] == repetido["codigo"]
    assert primeiro["competencia"] == "2026-08"
    assert setembro["competencia"] == "2026-09"
    assert setembro["codigo"] != primeiro["codigo"]


def test_convite_exige_aceite_e_adiciona_empresa_ao_grupo(db):
    service = GrupoComercialService(db, agora=AGORA)
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
    service = GrupoComercialService(db, agora=AGORA)
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
    service = GrupoComercialService(db, agora=AGORA)
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


def test_adicionar_loja_provisiona_tenant_e_anexa_como_membro(db, monkeypatch):
    """adicionar_loja (self-service e onboarding de ops) chama provision_tenant
    e anexa o resultado como membro comum — nunca como responsavel, mesmo
    sendo o mesmo usuario do responsavel do grupo."""
    from app import grupo_comercial_service as modulo

    nova_loja_id = "44444444-4444-4444-4444-444444444444"

    class _UsuarioFake:
        id = 10

    class _TenantFake:
        id = nova_loja_id
        name = "Loja Nova"

    class _ResultadoFake:
        tenant = _TenantFake()
        tenant_id = nova_loja_id
        user = _UsuarioFake()
        login_name = "loja-nova"

    chamadas = {}

    def _provision_tenant_fake(_db, **kwargs):
        chamadas.update(kwargs)
        return _ResultadoFake()

    monkeypatch.setattr(modulo, "provision_tenant", _provision_tenant_fake)

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Dono Unico")

    resultado = service.adicionar_loja(
        grupo_id=grupo["id"],
        usuario=_UsuarioFake(),
        nome_loja="Loja Nova",
        empresa_acionadora_id=EMPRESA_A,
        restore_tenant_id=EMPRESA_A,
    )

    assert resultado["tenant_id"] == nova_loja_id
    assert chamadas["user"] is not None  # reaproveitou o usuario logado, nao criou um novo
    assert chamadas["restore_tenant_id"] == EMPRESA_A

    membro_novo = (
        db.query(GrupoComercialMembro)
        .filter(GrupoComercialMembro.empresa_id == nova_loja_id)
        .one()
    )
    assert membro_novo.papel == "membro"  # nunca responsavel, mesmo sendo o mesmo dono
    assert membro_novo.status == "ativo"

    grupo_atualizado = db.query(GrupoComercial).filter_by(id=grupo["id"]).one()
    assert grupo_atualizado.versao_membros == 2


def test_adicionar_loja_exige_ser_responsavel_quando_acionada_por_empresa(db, monkeypatch):
    from app import grupo_comercial_service as modulo

    monkeypatch.setattr(
        modulo,
        "provision_tenant",
        lambda *_args, **_kwargs: pytest.fail("nao deveria provisionar sem autorizacao"),
    )

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Dono Unico")
    codigo_b = service.obter_codigo(EMPRESA_B, 20)["codigo"]
    convite = service.convidar(EMPRESA_A, 10, grupo["id"], codigo_b)
    service.responder_convite(EMPRESA_B, 20, convite["id"], aceitar=True)

    with pytest.raises(HTTPException) as sem_permissao:
        service.adicionar_loja(
            grupo_id=grupo["id"],
            usuario=None,
            nome_loja="Loja Indevida",
            empresa_acionadora_id=EMPRESA_B,  # membro comum, nao responsavel
        )
    assert sem_permissao.value.status_code == 403


def test_grupo_de_1_puro_se_fecha_ao_aceitar_convite_em_outro_grupo(db):
    """A empresa C tem seu proprio grupo-de-1 (so ela, responsavel). Ao
    aceitar um convite pra entrar no grupo da empresa A, o grupo-de-1 antigo
    deve fechar sozinho — deixa de aparecer no resumo dela e o status do
    grupo vira 'encerrado'."""
    service = GrupoComercialService(db, agora=AGORA)
    grupo_principal = service.criar_grupo(EMPRESA_A, 10, "Grupo Principal")
    grupo_solo_c = service.criar_grupo(EMPRESA_C, 30, "Grupo Solo da C")

    codigo_c = service.obter_codigo(EMPRESA_C, 30)["codigo"]
    convite = service.convidar(EMPRESA_A, 10, grupo_principal["id"], codigo_c)
    service.responder_convite(EMPRESA_C, 30, convite["id"], aceitar=True)

    grupo_solo_atualizado = (
        db.query(GrupoComercial).filter_by(id=grupo_solo_c["id"]).one()
    )
    assert grupo_solo_atualizado.status == "encerrado"

    membro_solo_antigo = (
        db.query(GrupoComercialMembro)
        .filter_by(grupo_id=grupo_solo_c["id"], empresa_id=EMPRESA_C)
        .one()
    )
    assert membro_solo_antigo.status == "removido"

    resumo_c = service.listar_resumo(EMPRESA_C, 30)
    grupos_ativos_c = {g["id"] for g in resumo_c["grupos"]}
    assert grupo_solo_c["id"] not in grupos_ativos_c
    assert grupo_principal["id"] in grupos_ativos_c


def test_grupo_com_outros_membros_nao_fecha_ao_empresa_entrar_em_outro_grupo(db):
    """Se a empresa que esta aceitando NAO e a unica no grupo antigo (tem
    outro membro ativo), o grupo antigo continua intacto — a regra so vale
    pra grupo-de-1 puro."""
    service = GrupoComercialService(db, agora=AGORA)
    grupo_dois_membros = service.criar_grupo(EMPRESA_B, 20, "Grupo com Dois")
    codigo_c = service.obter_codigo(EMPRESA_C, 30)["codigo"]
    convite_inicial = service.convidar(EMPRESA_B, 20, grupo_dois_membros["id"], codigo_c)
    service.responder_convite(EMPRESA_C, 30, convite_inicial["id"], aceitar=True)

    grupo_principal = service.criar_grupo(EMPRESA_A, 10, "Grupo Principal")
    codigo_c_novo = service.obter_codigo(EMPRESA_C, 30)["codigo"]
    convite_novo = service.convidar(EMPRESA_A, 10, grupo_principal["id"], codigo_c_novo)
    service.responder_convite(EMPRESA_C, 30, convite_novo["id"], aceitar=True)

    grupo_antigo_intacto = (
        db.query(GrupoComercial).filter_by(id=grupo_dois_membros["id"]).one()
    )
    assert grupo_antigo_intacto.status == "ativo"
    membro_b_no_grupo_antigo = (
        db.query(GrupoComercialMembro)
        .filter_by(grupo_id=grupo_dois_membros["id"], empresa_id=EMPRESA_B)
        .one()
    )
    assert membro_b_no_grupo_antigo.status == "ativo"
