"""O cadastro de acesso/RH respeita a identidade cadastral sem alterar o login."""

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app import usuarios_routes as usuarios
from app.cargo_models import Cargo
from app.db import Base
from app.funcionarios import base_routes as funcionarios
from app.funcionarios.schemas import FuncionarioCreate, FuncionarioUpdate
from app.grupo_comercial_models import GrupoComercial
from app.models import (
    AppAccessProfile,
    AuditLog,
    Cliente,
    ClienteContato,
    User,
    UserTenant,
)
from app.services.pessoa_telefone import PessoaTelefoneDuplicado

pytest_plugins = ["tests.unit.test_usuarios_criacao_regressoes"]


@pytest.fixture
def caso(cenario):
    Base.metadata.create_all(
        cenario.db.bind,
        tables=[GrupoComercial.__table__, ClienteContato.__table__, Cargo.__table__],
    )
    cargo = Cargo(tenant_id=cenario.tenant_id, nome="Vendedor QA", salario_base=2000)
    pessoa = Cliente(
        tenant_id=cenario.tenant_id,
        user_id=cenario.actor.id,
        codigo="PESSOA-1",
        nome="Pessoa original",
        telefone="(11) 99999-0001",
        is_cliente=True,
        ativo=True,
    )
    cenario.db.add_all([cargo, pessoa])
    cenario.db.commit()
    cenario.pessoa_id = pessoa.id
    cenario.cargo_id = cargo.id
    return cenario


def payload_usuario(**extras):
    return usuarios.UserCreate(
        **{
            "nome": "Usuario QA",
            "login_phone": "11999990001",
            "password": "SenhaQA123",
            "role_id": 20,
            "app_access_profiles": ["funcionario"],
            **extras,
        }
    )


def criar_usuario(caso, **extras):
    return usuarios.criar_usuario.__wrapped__(
        payload=payload_usuario(**extras),
        db=caso.db,
        user_and_tenant=(caso.actor, caso.tenant_id),
    )


def erro_constraint_telefone():
    original = SimpleNamespace(
        sqlstate="23505",
        pgcode="23505",
        diag=SimpleNamespace(constraint_name="uq_pessoa_telefone_escopo"),
    )
    return IntegrityError("SQL privado", {"telefone": "numero privado"}, original)


def test_criar_usuario_com_pessoa_duplicada_reverte_conta_vinculo_e_perfis(caso):
    with pytest.raises(PessoaTelefoneDuplicado) as erro:
        criar_usuario(caso, app_access_profiles=["funcionario"])
    assert erro.value.status_code == 409
    assert caso.db.query(User).count() == 1
    assert caso.db.query(UserTenant).count() == 1
    assert caso.db.query(Cliente).count() == 1
    assert caso.db.query(AppAccessProfile).count() == 0
    assert caso.db.query(AuditLog).count() == 0
    assert caso.db.get(Cliente, caso.pessoa_id).auth_user_id is None


def test_criar_usuario_constraint_concorrente_retorna_409_sem_expor_sql(
    caso, monkeypatch
):
    def concorrer(*_a, **_k):
        raise erro_constraint_telefone()

    monkeypatch.setattr(usuarios, "_vincular_ou_criar_pessoa_para_usuario", concorrer)
    with pytest.raises(PessoaTelefoneDuplicado) as erro:
        criar_usuario(caso, login_phone="11999990002")
    assert erro.value.status_code == 409
    assert "privado" not in str(erro.value.detail)
    assert caso.db.query(User).count() == 1
    assert caso.db.query(UserTenant).count() == 1
    assert caso.db.query(Cliente).count() == 1


def test_usuario_numero_livre_cria_pessoa_com_login_normalizado(caso):
    user = criar_usuario(caso, login_phone="+55 (11) 99999-0002")
    pessoa = caso.db.query(Cliente).filter(Cliente.auth_user_id == user.id).one()
    assert user.login_phone == pessoa.celular == "11999990002"
    assert pessoa.telefone is None
    assert caso.db.query(Cliente).count() == 2


def test_vinculo_explicito_preserva_telefone_pessoa_sem_copiar_login(caso):
    pessoa = Cliente(
        tenant_id=caso.tenant_id,
        user_id=caso.actor.id,
        codigo="VINCULADA",
        nome="Pessoa selecionada",
        celular="11999990003",
        is_cliente=True,
        ativo=True,
    )
    caso.db.add(pessoa)
    caso.db.commit()
    pessoa_id = pessoa.id
    user = criar_usuario(caso, pessoa_id=pessoa_id)
    caso.db.refresh(pessoa)
    assert user.login_phone == "11999990001"
    assert pessoa.celular == "11999990003"
    assert pessoa.telefone is None
    assert pessoa.auth_user_id == user.id
    assert caso.db.query(Cliente).count() == 2
    assert caso.db.get(Cliente, caso.pessoa_id).auth_user_id is None


@pytest.mark.parametrize("campo", ["login_phone", "telefone"])
def test_recuperar_pessoa_operacional_valida_ambos_contatos_antes_de_criar(caso, campo):
    user = SimpleNamespace(
        id=700,
        login_phone="11999990001" if campo == "login_phone" else None,
        telefone="+55 (11) 99999-0001" if campo == "telefone" else None,
    )
    with pytest.raises(PessoaTelefoneDuplicado):
        usuarios._criar_pessoa_operacional_para_usuario(
            caso.db, actor=caso.actor, tenant_id=caso.tenant_id, user=user
        )
    assert not caso.db.new
    assert caso.db.query(Cliente).count() == 1


@pytest.mark.parametrize("erro_no_banco", [False, True])
def test_credenciais_rollback_conta_se_nova_pessoa_colidir(
    caso, monkeypatch, erro_no_banco
):
    user, _ = usuarios.create_tenant_user_account(
        caso.db,
        tenant_id=caso.tenant_id,
        username=None,
        email=None,
        login_phone="11999990002",
        password="SenhaQA123",
        role_id=20,
        nome="Usuario sem pessoa",
    )
    caso.db.commit()
    user_id = user.id
    if erro_no_banco:

        def concorrer(*_a, **_k):
            raise erro_constraint_telefone()

        monkeypatch.setattr(
            usuarios, "_criar_pessoa_operacional_para_usuario", concorrer
        )
    with pytest.raises(PessoaTelefoneDuplicado):
        usuarios.atualizar_credenciais_usuario.__wrapped__(
            user_id=user_id,
            payload=usuarios.UserCredentialsUpdate(login_phone="11999990001"),
            db=caso.db,
            user_and_tenant=(caso.actor, caso.tenant_id),
        )
    caso.db.expire_all()
    assert caso.db.get(User, user_id).login_phone == "11999990002"
    assert caso.db.query(Cliente).count() == 1
    assert caso.db.query(AuditLog).count() == 0


def test_criar_funcionario_rejeita_telefone_de_pessoa_antes_de_inserir(caso):
    with pytest.raises(PessoaTelefoneDuplicado):
        asyncio.run(
            funcionarios.criar_funcionario(
                FuncionarioCreate(
                    nome="Novo funcionario",
                    telefone="+55 (11) 99999-0001",
                    cargo_id=caso.cargo_id,
                ),
                caso.db,
                (caso.actor, caso.tenant_id),
            )
        )
    assert not caso.db.new
    assert caso.db.query(Cliente).count() == 1


def funcionario_existente(caso, *, telefone="11999990002"):
    funcionario = Cliente(
        tenant_id=caso.tenant_id,
        user_id=caso.actor.id,
        codigo="FUNCIONARIO",
        nome="Funcionario original",
        telefone=telefone,
        is_funcionario=True,
        cargo_id=caso.cargo_id,
        ativo=True,
    )
    caso.db.add(funcionario)
    caso.db.commit()
    return funcionario


def test_atualizar_funcionario_valida_antes_de_modificar_nome_e_telefone(caso):
    funcionario = funcionario_existente(caso)
    with pytest.raises(PessoaTelefoneDuplicado):
        asyncio.run(
            funcionarios.atualizar_funcionario(
                funcionario.id,
                FuncionarioUpdate(nome="Nome novo", telefone="11999990001"),
                caso.db,
                (caso.actor, caso.tenant_id),
            )
        )
    assert funcionario.nome == "Funcionario original"
    assert funcionario.telefone == "11999990002"
    assert not caso.db.dirty


@pytest.mark.parametrize("telefone", [None, "+55 (11) 99999-0001"])
def test_atualizar_funcionario_permite_limpeza_ou_mesma_chave_legada(caso, telefone):
    funcionario = funcionario_existente(caso, telefone="11999990001")
    resposta = asyncio.run(
        funcionarios.atualizar_funcionario(
            funcionario.id,
            FuncionarioUpdate(nome="Nome atualizado", telefone=telefone),
            caso.db,
            (caso.actor, caso.tenant_id),
        )
    )
    assert resposta.nome == "Nome atualizado"
    caso.db.refresh(funcionario)
    assert funcionario.telefone == telefone
    assert caso.db.query(Cliente).count() == 2
