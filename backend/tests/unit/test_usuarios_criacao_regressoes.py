"""Fluxos de usuarios com transacoes reais em SQLite descartavel."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import usuarios_routes
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra as FKs no metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import (
    AppAccessProfile,
    AuditLog,
    Cliente,
    Role,
    Tenant,
    User,
    UserSession,
    UserTenant,
)
from app.services.app_access_profile_service import (
    build_available_profiles_for_clientes,
    list_explicit_app_access_profiles,
)
from app.tenancy import filters as tenant_filters
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.veterinario_models import VetPartnerLink


@pytest.fixture()
def cenario(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Role.__table__,
            UserTenant.__table__,
            Cliente.__table__,
            AppAccessProfile.__table__,
            AuditLog.__table__,
            GrupoComercialMembro.__table__,
        ],
    )
    tenant_id = uuid4()
    db = Session(engine)
    db.add(Tenant(id=str(tenant_id), name="Loja QA", name_normalized="loja qa"))
    db.execute(
        Role.__table__.insert(),
        [
            {"id": 10, "tenant_id": tenant_id, "name": "Administrador"},
            {"id": 20, "tenant_id": tenant_id, "name": "Vendedor"},
        ],
    )
    db.execute(
        User.__table__.insert(),
        [
            {
                "id": 1,
                "tenant_id": tenant_id,
                "nome": "Operador QA",
                "email": "operador@example.com",
            }
        ],
    )
    db.execute(
        UserTenant.__table__.insert(),
        [{"user_id": 1, "tenant_id": tenant_id, "role_id": 10, "is_active": True}],
    )
    db.commit()
    set_current_tenant(tenant_id)
    actor = db.query(User).filter(User.id == 1).one()

    # A geracao de codigo usa advisory lock e regex do PostgreSQL. Somente
    # essa dependencia de dialeto e substituida; usuarios, pessoas, perfis,
    # auditoria, constraints e commit/rollback usam as implementacoes reais.
    contador = iter(range(10000, 10100))
    monkeypatch.setattr(
        usuarios_routes, "gerar_codigo_cliente", lambda *_args: str(next(contador))
    )
    try:
        yield SimpleNamespace(db=db, tenant_id=tenant_id, actor=actor)
    finally:
        clear_current_tenant()
        db.close()
        engine.dispose()


def _payload(**alteracoes):
    dados = {
        "nome": "Pessoa QA",
        "login_phone": "11999990001",
        "password": "SenhaQA123",
        "role_id": 20,
        "app_access_profiles": ["funcionario", "gestor"],
    }
    dados.update(alteracoes)
    return usuarios_routes.UserCreate(**dados)


def _criar(cenario, payload):
    # A permissao do endpoint e coberta pelos testes de autorizacao; aqui
    # exercitamos o corpo real da rota, incluindo todas as suas transacoes.
    return usuarios_routes.criar_usuario.__wrapped__(
        payload=payload,
        db=cenario.db,
        user_and_tenant=(cenario.actor, cenario.tenant_id),
    )


def _pessoa_existente(cenario):
    pessoa = Cliente(
        tenant_id=cenario.tenant_id,
        user_id=cenario.actor.id,
        codigo="9000",
        nome="Pessoa existente",
        tipo_pessoa="PJ",
        is_cliente=True,
        is_fornecedor=True,
        is_funcionario=False,
        celular="11999998888",
        celular_whatsapp=True,
        ativo=True,
    )
    cenario.db.add(pessoa)
    cenario.db.commit()
    return pessoa


def _usuario_existente(cenario):
    """Massa anterior a operacao testada, independente da rota de criacao."""
    user, _role = usuarios_routes.create_tenant_user_account(
        cenario.db,
        tenant_id=cenario.tenant_id,
        username=None,
        email=None,
        login_phone="11999990001",
        password="SenhaQA123",
        role_id=20,
        nome="Usuario existente",
    )
    usuarios_routes._vincular_ou_criar_pessoa_para_usuario(
        cenario.db,
        actor=cenario.actor,
        tenant_id=cenario.tenant_id,
        user=user,
        pessoa_id=None,
        nome=user.nome,
        login_phone=user.login_phone,
        email=None,
    )
    cenario.db.commit()
    return user


@pytest.mark.parametrize("tipo_pessoa,whatsapp", [("PF", True), ("PJ", False)])
def test_criar_usuario_grava_uma_pessoa_com_dados_e_perfis(
    cenario, tipo_pessoa, whatsapp
):
    user = _criar(
        cenario,
        _payload(tipo_pessoa=tipo_pessoa, celular_whatsapp=whatsapp),
    )
    db = cenario.db
    db.expire_all()
    pessoas = db.query(Cliente).all()
    assert len(pessoas) == 1
    pessoa = pessoas[0]
    assert pessoa.auth_user_id == user.id
    assert pessoa.tipo_pessoa == tipo_pessoa
    assert pessoa.celular_whatsapp is whatsapp
    assert pessoa.nome == "Pessoa QA"
    assert pessoa.celular == user.login_phone == "11999990001"
    assert pessoa.is_funcionario is True
    assert pessoa.origem_cliente == "cadastro_usuario"
    assert db.query(UserTenant).filter(UserTenant.user_id == user.id).count() == 1
    perfis = db.query(AppAccessProfile).all()
    assert {perfil.profile_type for perfil in perfis} == {"funcionario", "gestor"}
    assert all(
        perfil.cliente_id == pessoa.id and perfil.user_id == user.id
        for perfil in perfis
    )
    evento = db.query(AuditLog).one()
    assert json.loads(evento.new_value)["metadata"]["pessoa_id"] == pessoa.id


def test_criar_usuario_vincula_pessoa_existente_sem_copiar_nem_sobrescrever(cenario):
    pessoa = _pessoa_existente(cenario)
    pessoa_id = pessoa.id
    user = _criar(cenario, _payload(pessoa_id=pessoa_id))
    cenario.db.expire_all()
    assert cenario.db.query(Cliente).count() == 1
    pessoa = cenario.db.query(Cliente).one()
    assert pessoa.id == pessoa_id
    assert pessoa.auth_user_id == user.id
    assert pessoa.nome == "Pessoa existente"
    assert pessoa.tipo_pessoa == "PJ"
    assert pessoa.celular == "11999998888"
    assert pessoa.celular_whatsapp is True
    assert pessoa.is_cliente is True
    assert pessoa.is_fornecedor is True
    assert pessoa.is_funcionario is False
    assert {p.profile_type for p in cenario.db.query(AppAccessProfile).all()} == {
        "funcionario",
        "gestor",
    }
    evento = cenario.db.query(AuditLog).one()
    assert json.loads(evento.new_value)["metadata"]["pessoa_id"] == pessoa_id


@pytest.mark.parametrize("usar_pessoa_existente", [False, True])
def test_falha_em_loja_adicional_reverte_usuario_pessoa_perfis_e_auditoria(
    cenario, usar_pessoa_existente
):
    pessoa = _pessoa_existente(cenario) if usar_pessoa_existente else None
    pessoa_id = pessoa.id if pessoa else None
    with pytest.raises(HTTPException) as erro:
        _criar(
            cenario,
            _payload(
                pessoa_id=pessoa_id,
                lojas_adicionais=[{"tenant_id": str(uuid4())}],
            ),
        )
    assert erro.value.status_code == 403
    db = cenario.db
    db.expire_all()
    assert db.query(User).count() == 1  # somente o operador preexistente
    assert db.query(UserTenant).count() == 1
    assert db.query(AppAccessProfile).count() == 0
    assert db.query(AuditLog).count() == 0
    assert db.query(Cliente).count() == int(usar_pessoa_existente)
    if usar_pessoa_existente:
        pessoa = db.query(Cliente).one()
        assert pessoa.id == pessoa_id
        assert pessoa.auth_user_id is None
        assert pessoa.nome == "Pessoa existente"
        assert pessoa.is_fornecedor is True


@pytest.mark.parametrize("autorizado", [True, False])
def test_listagem_serializa_liberacao_crediario_real(cenario, autorizado):
    user = _usuario_existente(cenario)
    vinculo = cenario.db.query(UserTenant).filter(UserTenant.user_id == user.id).one()
    vinculo.pode_liberar_venda_crediario_atrasado = autorizado
    cenario.db.commit()
    rows = usuarios_routes.listar_usuarios.__wrapped__(
        db=cenario.db, user_and_tenant=(cenario.actor, cenario.tenant_id)
    )
    resultado = next(row for row in rows if row["user_id"] == user.id)
    serializado = usuarios_routes.UsuarioListResponse.model_validate(
        resultado
    ).model_dump()
    assert serializado["pode_liberar_venda_crediario_atrasado"] is autorizado


def _master(cenario):
    user = _usuario_existente(cenario)
    user.master_grupo_id = 77
    cenario.db.commit()
    return user


@pytest.mark.parametrize("trocar_celular", [True, False])
def test_master_pode_salvar_credenciais_com_o_mesmo_perfil(
    cenario, monkeypatch, trocar_celular
):
    user = _master(cenario)
    revogacoes = []
    monkeypatch.setattr(
        usuarios_routes,
        "revoke_all_sessions",
        lambda **kwargs: revogacoes.append(kwargs) or 2,
    )
    celular = "11999990002" if trocar_celular else user.login_phone
    resultado = usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
        user_id=user.id,
        payload=usuarios_routes.UserCredentialsUpdate(login_phone=celular, role_id=20),
        db=cenario.db,
        user_and_tenant=(cenario.actor, cenario.tenant_id),
    )
    cenario.db.expire_all()
    atualizado = cenario.db.query(User).filter(User.id == user.id).one()
    assert atualizado.login_phone == celular
    assert atualizado.master_grupo_id == 77
    assert resultado["role_id"] == 20
    assert resultado["role_changed"] is False
    assert resultado["sessions_revoked"] == (2 if trocar_celular else 0)
    assert len(revogacoes) == int(trocar_celular)
    assert cenario.db.query(Cliente).count() == 1


def test_master_continua_impedido_de_trocar_perfil_sem_alterar_celular(cenario):
    user = _master(cenario)
    with pytest.raises(HTTPException) as erro:
        usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
            user_id=user.id,
            payload=usuarios_routes.UserCredentialsUpdate(
                login_phone="11999990002", role_id=10
            ),
            db=cenario.db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
    assert erro.value.status_code == 403
    cenario.db.expire_all()
    assert (
        cenario.db.query(User).filter(User.id == user.id).one().login_phone
        == "11999990001"
    )
    assert (
        cenario.db.query(UserTenant).filter(UserTenant.user_id == user.id).one().role_id
        == 20
    )


def test_perfil_app_desmarcado_nao_reaparece_ao_reabrir_nem_libera_gestor(cenario):
    user = _criar(cenario, _payload())
    db = cenario.db
    for selecionados in (["funcionario"], [], ["gestor", "funcionario"]):
        salvo = usuarios_routes.atualizar_perfis_app_usuario.__wrapped__(
            user_id=user.id,
            payload=usuarios_routes.PerfisAppUpdate(profiles=selecionados),
            db=db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
        db.expire_all()
        reaberto = usuarios_routes.listar_perfis_app_usuario.__wrapped__(
            user_id=user.id,
            db=db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
        assert set(reaberto["profiles"]) == set(salvo["profiles"]) == set(selecionados)
        # Desmarcar preserva o historico da concessao, com is_active=False.
        grants = (
            db.query(AppAccessProfile).filter(AppAccessProfile.user_id == user.id).all()
        )
        assert len(grants) == 2
        assert {grant.profile_type for grant in grants if grant.is_active} == set(
            selecionados
        )
        pessoas = db.query(Cliente).filter(Cliente.auth_user_id == user.id).all()
        ativos = list_explicit_app_access_profiles(
            db,
            tenant_id=cenario.tenant_id,
            user_id=user.id,
            cliente_ids=[pessoa.id for pessoa in pessoas],
        )
        disponiveis = build_available_profiles_for_clientes(
            user, pessoas, explicit_grants=ativos
        )
        assert ("gestor" in {perfil["type"] for perfil in disponiveis}) is (
            "gestor" in selecionados
        )


@pytest.fixture()
def loja_associada(cenario, monkeypatch):
    """Mesma regra de identidade global usada pelo PostgreSQL em producao.

    O SQLite normalmente usa um filtro simplificado (so tenant de origem).
    Habilitamos aqui o predicado real de leitura por UserTenant, mantendo
    consultas, transacoes e regras da rota sem substituicoes.
    """
    user = _usuario_existente(cenario)
    db = cenario.db
    Base.metadata.create_all(
        db.get_bind(),
        tables=[
            GrupoComercial.__table__,
            VetPartnerLink.__table__,
            UserSession.__table__,
        ],
    )
    destino_id = uuid4()
    db.execute(
        Tenant.__table__.insert(),
        [
            {
                "id": str(destino_id),
                "name": "Loja associada",
                "name_normalized": "loja associada",
            }
        ],
    )
    db.execute(
        Role.__table__.insert(),
        [
            {"id": 30, "tenant_id": destino_id, "name": "Administrador"},
            {"id": 40, "tenant_id": destino_id, "name": "Vendedor"},
        ],
    )
    db.execute(
        User.__table__.insert(),
        [
            {
                "id": 99,
                "tenant_id": destino_id,
                "nome": "Operador associado QA",
                "email": "associado@example.com",
            }
        ],
    )
    db.execute(
        UserTenant.__table__.insert(),
        [
            {
                "user_id": user.id,
                "tenant_id": destino_id,
                "role_id": 40,
                "is_active": True,
            },
            {"user_id": 99, "tenant_id": destino_id, "role_id": 30, "is_active": True},
        ],
    )
    db.commit()
    set_current_tenant(destino_id)
    monkeypatch.setattr(
        tenant_filters, "_supports_partner_read_filter", lambda _session: True
    )
    actor = db.query(User).filter(User.id == 99).one()
    return SimpleNamespace(
        db=db, tenant_id=destino_id, origem_id=cenario.tenant_id, actor=actor, user=user
    )


@pytest.mark.parametrize("alterar", [False, True])
def test_loja_associada_salva_credenciais_sem_duplicar_pessoa(loja_associada, alterar):
    cenario = loja_associada
    user = cenario.user
    celular = "11999990002" if alterar else user.login_phone
    role_id = 30 if alterar else 40
    resultado = usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
        user_id=user.id,
        payload=usuarios_routes.UserCredentialsUpdate(
            login_phone=celular, role_id=role_id
        ),
        db=cenario.db,
        user_and_tenant=(cenario.actor, cenario.tenant_id),
    )
    cenario.db.expire_all()
    atualizado = cenario.db.query(User).filter(User.id == user.id).one()
    assert atualizado.login_phone == celular
    assert atualizado.tenant_id == cenario.origem_id
    assert resultado["role_id"] == role_id
    assert resultado["role_changed"] is alterar
    vinculos = cenario.db.execute(
        select(UserTenant.__table__.c.tenant_id, UserTenant.__table__.c.role_id).where(
            UserTenant.__table__.c.user_id == user.id
        )
    ).all()
    assert dict(vinculos) == {cenario.origem_id: 20, cenario.tenant_id: role_id}
    pessoas = cenario.db.execute(
        select(Cliente.__table__.c.tenant_id, Cliente.__table__.c.auth_user_id)
    ).all()
    assert pessoas == [(cenario.origem_id, user.id)]


def test_loja_associada_recusa_role_da_origem_e_reverte_celular(loja_associada):
    cenario = loja_associada
    with pytest.raises(HTTPException) as erro:
        usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
            user_id=cenario.user.id,
            payload=usuarios_routes.UserCredentialsUpdate(
                login_phone="11999990002", role_id=20
            ),
            db=cenario.db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
    assert erro.value.status_code == 400
    cenario.db.expire_all()
    atualizado = cenario.db.query(User).filter(User.id == cenario.user.id).one()
    assert atualizado.login_phone == "11999990001"
    assert (
        cenario.db.query(UserTenant)
        .filter(UserTenant.user_id == atualizado.id)
        .one()
        .role_id
        == 40
    )
    assert (
        cenario.db.execute(
            select(func.count()).select_from(Cliente.__table__)
        ).scalar_one()
        == 1
    )


def test_loja_sem_vinculo_nao_altera_credenciais_nem_le_perfis(loja_associada):
    cenario = loja_associada
    vinculo = (
        cenario.db.query(UserTenant).filter(UserTenant.user_id == cenario.user.id).one()
    )
    cenario.db.delete(vinculo)
    cenario.db.commit()
    with pytest.raises(HTTPException) as erro:
        usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
            user_id=cenario.user.id,
            payload=usuarios_routes.UserCredentialsUpdate(
                login_phone="11999990002", role_id=40
            ),
            db=cenario.db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
    assert erro.value.status_code == 404
    with pytest.raises(HTTPException) as erro_perfis:
        usuarios_routes.listar_perfis_app_usuario.__wrapped__(
            user_id=cenario.user.id,
            db=cenario.db,
            user_and_tenant=(cenario.actor, cenario.tenant_id),
        )
    assert erro_perfis.value.status_code == 404
    celular = cenario.db.execute(
        select(User.__table__.c.login_phone).where(
            User.__table__.c.id == cenario.user.id
        )
    ).scalar_one()
    assert celular == "11999990001"


def test_administra_credenciais_de_usuario_inativo_sem_reativar(cenario):
    user = _usuario_existente(cenario)
    vinculo = cenario.db.query(UserTenant).filter(UserTenant.user_id == user.id).one()
    vinculo.is_active = False
    cenario.db.commit()
    resultado = usuarios_routes.atualizar_credenciais_usuario.__wrapped__(
        user_id=user.id,
        payload=usuarios_routes.UserCredentialsUpdate(
            login_phone=user.login_phone, role_id=20
        ),
        db=cenario.db,
        user_and_tenant=(cenario.actor, cenario.tenant_id),
    )
    assert resultado["status"] == "ok"
    cenario.db.expire_all()
    assert (
        cenario.db.query(UserTenant)
        .filter(UserTenant.user_id == user.id)
        .one()
        .is_active
        is False
    )
    assert cenario.db.query(Cliente).count() == 1
