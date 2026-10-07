from datetime import datetime, timezone
from uuid import UUID

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
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.grupo_comercial_service import GrupoComercialService
from app.models import Permission, Role, RolePermission, Tenant, User, UserTenant
from app.models_cadastros import Cliente
from app.pessoa_mestre_models import PessoaMestre
from app.tenancy.context import clear_tenant_context, set_tenant_context


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
            User.__table__,
            UserTenant.__table__,
            Role.__table__,
            RolePermission.__table__,
            Permission.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialEstoqueCompartilhado.__table__,
            Cliente.__table__,
            PessoaMestre.__table__,
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
    # Insert via Core (nao via `session.add`) de proposito: os guards de ORM
    # (app/database/orm_guards.py) exigem tenant_id no contexto pra qualquer
    # INSERT novo em tabela multi-tenant e sempre reescrevem o `id` pra
    # deixar o banco gerar - corretos em codigo de producao, mas atrapalham
    # so montar a massa de teste com ids fixos e prontos de antemao.
    session.execute(
        User.__table__.insert(),
        [
            {"id": 10, "tenant_id": UUID(EMPRESA_A), "email": "dono-a@teste.com", "nome": "Dono A"},
            {"id": 20, "tenant_id": UUID(EMPRESA_B), "email": "dono-b@teste.com", "nome": "Dono B"},
            {"id": 30, "tenant_id": UUID(EMPRESA_C), "email": "dono-c@teste.com", "nome": "Dono C"},
            {
                "id": 99,
                "tenant_id": UUID(EMPRESA_A),
                "email": "funcionaria-a@teste.com",
                "nome": "Funcionária A",
            },
        ],
    )
    session.commit()
    clear_tenant_context()
    monkeypatch.setattr(
        "app.grupo_comercial_service.log_business_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "app.grupo_comercial_service.registrar_uso_funcionalidade",
        lambda *_args, **_kwargs: True,
    )
    # gerar_codigo_cliente usa CAST(... AS BIGINT) + operador `~` (regex),
    # sintaxe Postgres - SQLite nao entende. So a codigo-geracao em si nao
    # e o que estes testes cobrem, entao troca por um contador simples.
    contador_codigo = {"n": 10000}

    def _codigo_fake(_db, _tipo_pessoa, _tenant_id):
        contador_codigo["n"] += 1
        return str(contador_codigo["n"])

    monkeypatch.setattr(
        "app.grupo_comercial_service.gerar_codigo_cliente", _codigo_fake
    )
    try:
        yield session
    finally:
        clear_tenant_context()
        session.close()


def _usuario(db, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).one()


def test_criar_grupo_marca_fundador_como_master(db):
    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(
        EMPRESA_A, 10, "Grupo Centro", titular_tipo_pessoa="PJ", titular_telefone="11988887777"
    )

    fundador = _usuario(db, 10)
    assert fundador.master_grupo_id == grupo["id"]
    assert grupo["sou_master"] is True

    set_tenant_context(UUID(EMPRESA_A))
    cliente_titular = db.query(Cliente).filter(Cliente.auth_user_id == 10).one()
    clear_tenant_context()
    assert cliente_titular.tipo_pessoa == "PJ"
    assert cliente_titular.celular == "11988887777"
    assert cliente_titular.is_funcionario is True
    assert cliente_titular.origem_cliente == "cadastro_grupo_comercial"
    assert cliente_titular.pessoa_mestre_id is not None
    mestre = db.query(PessoaMestre).filter(PessoaMestre.id == cliente_titular.pessoa_mestre_id).one()
    assert mestre.grupo_id == grupo["id"]


def test_usuario_sem_acesso_de_gestao_nao_ve_o_grupo_no_resumo(db):
    service = GrupoComercialService(db, agora=AGORA)
    service.criar_grupo(EMPRESA_A, 10, "Grupo Centro")

    resumo_funcionaria = service.listar_resumo(EMPRESA_A, _usuario(db, 99))
    assert resumo_funcionaria["grupos"] == []
    assert resumo_funcionaria["tem_grupo_sem_acesso"] is True

    resumo_master = service.listar_resumo(EMPRESA_A, _usuario(db, 10))
    assert len(resumo_master["grupos"]) == 1


def test_adicionar_loja_provisiona_tenant_e_anexa_como_membro(db, monkeypatch):
    """adicionar_loja (self-service e onboarding de ops) chama provision_tenant
    e anexa o resultado como membro comum — nunca como responsavel, mesmo
    sendo o mesmo usuario do responsavel do grupo."""
    from app import grupo_comercial_service as modulo

    nova_loja_id = "44444444-4444-4444-4444-444444444444"

    class _TenantFake:
        id = nova_loja_id
        name = "Loja Nova"

    def _resultado_fake(usuario):
        class _Resultado:
            tenant = _TenantFake()
            tenant_id = UUID(nova_loja_id)
            user = usuario
            login_name = "loja-nova"

        return _Resultado()

    chamadas = {}

    def _provision_tenant_fake(_db, **kwargs):
        chamadas.update(kwargs)
        return _resultado_fake(kwargs["user"])

    monkeypatch.setattr(modulo, "provision_tenant", _provision_tenant_fake)

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Dono Unico")
    master = _usuario(db, 10)

    resultado = service.adicionar_loja(
        grupo_id=grupo["id"],
        usuario=master,
        nome_loja="Loja Nova",
        empresa_acionadora_id=EMPRESA_A,
        restore_tenant_id=EMPRESA_A,
    )
    # restore_tenant_id acima e a string de teste (EMPRESA_A), nao um UUID
    # de verdade como seria em producao (vem do JWT) - limpa o contexto pra
    # nao atrapalhar o filtro automatico de tenant nas consultas abaixo.
    clear_tenant_context()

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

    # provision_tenant esta mockado (nao cria vinculo nenhum sozinho, ao
    # contrario do real) - _garantir_acesso_master precisa preencher essa
    # lacuna e dar acesso ao master mesmo ele sendo o proprio usuario que
    # adicionou a loja.
    vinculos_master = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == master.id, UserTenant.tenant_id == UUID(nova_loja_id))
        .all()
    )
    assert len(vinculos_master) == 1

    set_tenant_context(UUID(EMPRESA_A))
    cliente_loja_fundadora = db.query(Cliente).filter(Cliente.auth_user_id == master.id).one()
    clear_tenant_context()

    set_tenant_context(UUID(nova_loja_id))
    cliente_loja_nova = db.query(Cliente).filter(Cliente.auth_user_id == master.id).one()
    clear_tenant_context()

    assert cliente_loja_nova.pessoa_mestre_id is not None
    assert cliente_loja_nova.pessoa_mestre_id == cliente_loja_fundadora.pessoa_mestre_id


def test_adicionar_loja_exige_acesso_de_gestao_mesmo_sendo_empresa_responsavel(db, monkeypatch):
    """Antes, qualquer usuario com permissao generica de configuracoes na
    empresa responsavel conseguia adicionar loja. Agora precisa tambem ter
    acesso de gestao do grupo (ser o master)."""
    from app import grupo_comercial_service as modulo

    monkeypatch.setattr(
        modulo,
        "provision_tenant",
        lambda *_args, **_kwargs: pytest.fail("nao deveria provisionar sem autorizacao"),
    )

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Dono Unico")
    funcionaria = _usuario(db, 99)  # mesma empresa responsavel, sem acesso de gestao

    with pytest.raises(HTTPException) as sem_permissao:
        service.adicionar_loja(
            grupo_id=grupo["id"],
            usuario=funcionaria,
            nome_loja="Loja Indevida",
            empresa_acionadora_id=EMPRESA_A,
        )
    assert sem_permissao.value.status_code == 403


def test_responsavel_remove_membro_sem_poder_remover_a_si_mesmo(db, monkeypatch):
    from app import grupo_comercial_service as modulo

    membro_b_id = "66666666-6666-6666-6666-666666666666"

    def _provision_tenant_fake(_db, **kwargs):
        class _TenantFake:
            id = membro_b_id
            name = "Loja B"

        class _Resultado:
            tenant = _TenantFake()
            tenant_id = UUID(membro_b_id)
            user = kwargs["user"]
            login_name = "loja-b"

        return _Resultado()

    monkeypatch.setattr(modulo, "provision_tenant", _provision_tenant_fake)

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Operação")
    master = _usuario(db, 10)
    service.adicionar_loja(
        grupo_id=grupo["id"],
        usuario=master,
        nome_loja="Loja B",
        empresa_acionadora_id=EMPRESA_A,
        restore_tenant_id=EMPRESA_A,
    )

    service.remover_membro(EMPRESA_A, master, grupo["id"], membro_b_id)
    membro_removido = (
        db.query(GrupoComercialMembro)
        .filter_by(grupo_id=grupo["id"], empresa_id=membro_b_id)
        .one()
    )
    assert membro_removido.status == "removido"

    with pytest.raises(HTTPException) as remover_responsavel:
        service.remover_membro(EMPRESA_A, master, grupo["id"], EMPRESA_A)
    assert remover_responsavel.value.status_code == 400


def test_duas_lojas_adicionadas_em_chamadas_separadas_compartilham_pessoa_mestre(db, monkeypatch):
    """_pessoa_mestre_do_titular precisa achar a mestre de uma loja que ja
    existe, nao so reaproveitar algo que ainda esta em memoria no mesmo
    laco (caso onboard_grupo_comercial) - aqui cada adicionar_loja e uma
    chamada independente, simulando 'adicionar loja dias depois'."""
    from app import grupo_comercial_service as modulo

    loja_1_id = "77777777-7777-7777-7777-777777777771"
    loja_2_id = "77777777-7777-7777-7777-777777777772"

    def _fake_com_id(tenant_id_str):
        tenant_uuid = UUID(tenant_id_str)

        def _fake(_db, **kwargs):
            class _TenantFake:
                id = tenant_id_str
                name = "Loja"

            class _Resultado:
                tenant = _TenantFake()
                tenant_id = tenant_uuid
                user = kwargs["user"]
                login_name = "loja"

            return _Resultado()

        return _fake

    service = GrupoComercialService(db, agora=AGORA)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Duas Lojas Separadas")
    master = _usuario(db, 10)

    monkeypatch.setattr(modulo, "provision_tenant", _fake_com_id(loja_1_id))
    service.adicionar_loja(
        grupo_id=grupo["id"], usuario=master, nome_loja="Loja Um",
        empresa_acionadora_id=EMPRESA_A, restore_tenant_id=EMPRESA_A,
    )
    clear_tenant_context()

    monkeypatch.setattr(modulo, "provision_tenant", _fake_com_id(loja_2_id))
    service.adicionar_loja(
        grupo_id=grupo["id"], usuario=master, nome_loja="Loja Dois",
        empresa_acionadora_id=EMPRESA_A, restore_tenant_id=EMPRESA_A,
    )
    clear_tenant_context()

    set_tenant_context(UUID(loja_1_id))
    mestre_1 = db.query(Cliente).filter(Cliente.auth_user_id == master.id).one().pessoa_mestre_id
    clear_tenant_context()
    set_tenant_context(UUID(loja_2_id))
    mestre_2 = db.query(Cliente).filter(Cliente.auth_user_id == master.id).one().pessoa_mestre_id
    clear_tenant_context()

    assert mestre_1 is not None
    assert mestre_1 == mestre_2


def test_criar_cliente_titular_nao_duplica_se_ja_existir(db):
    """Guarda de defesa: chamar criar_grupo (ou o helper interno) duas vezes
    sobre o mesmo tenant/usuario nao pode violar a constraint unica de
    Cliente nem criar uma segunda Pessoa - cobre o caminho self-service de
    criar_grupo_empresa, que pode rodar sobre um tenant ja existente."""
    service = GrupoComercialService(db, agora=AGORA)
    master = _usuario(db, 10)
    grupo = service.criar_grupo(EMPRESA_A, 10, "Grupo Defesa Duplicata")

    # Chama o helper interno de novo, direto, simulando uma segunda passada
    # sobre o mesmo tenant/usuario. Chamada direta (sem passar por
    # criar_grupo/adicionar_loja) precisa do proprio contexto de tenant.
    set_tenant_context(UUID(EMPRESA_A))
    service._criar_cliente_titular(
        tenant_id=EMPRESA_A, usuario=master, grupo_id=grupo["id"],
        tipo_pessoa="PF", telefone=None, pessoa_mestre_id=None,
    )
    clear_tenant_context()

    set_tenant_context(UUID(EMPRESA_A))
    clientes = db.query(Cliente).filter(Cliente.auth_user_id == master.id).all()
    clear_tenant_context()
    assert len(clientes) == 1
