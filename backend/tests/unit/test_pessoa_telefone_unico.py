"""Telefone identifica uma pessoa no grupo, sem fundir ou reescrever legado."""

from types import SimpleNamespace
from contextlib import nullcontext
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import db as _db
from app import financeiro_models as _financeiro  # noqa: F401
from app import produtos_models as _produtos  # noqa: F401
from app.clientes import crud_routes as crud
from app.clientes.contatos import (
    salvar_contatos_adicionais,
    validar_contatos_adicionais,
)
from app.clientes.schemas import ClienteContatoInput
from app.clientes.duplicidades_routes import verificar_duplicata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Cliente, ClienteContato, FornecedorGrupo, PessoaMergeLog, User
from app.routes import ecommerce_auth_profiles as perfil
from app.routes import ecommerce_auth_cliente as cliente_app
from app.routes import ecommerce_auth_public as cadastro_publico
from app.scripts.seed_banho_tosa_ux_support import ensure_person
from app.services.pessoa_telefone import (
    CONSTRAINT_TELEFONE,
    PessoaTelefoneDuplicado,
    erro_telefone_duplicado,
    normalizar_telefone_pessoa,
    resolver_escopo_telefone_pessoa,
    telefone_pessoa_sql,
    validar_telefones_pessoa,
)
from app.tenancy.context import tenant_context


@pytest.fixture
def cadastro(tenant_context):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        FornecedorGrupo,
        Cliente,
        ClienteContato,
        GrupoComercial,
        GrupoComercialMembro,
        User,
        PessoaMergeLog,
    ):
        model.__table__.create(engine)
    tenant = uuid4()
    tenant_context(tenant)
    with Session(engine, expire_on_commit=False) as db:
        yield SimpleNamespace(db=db, tenant=tenant)
    engine.dispose()


def pessoa(c, **dados):
    registro = Cliente(
        tenant_id=dados.pop("tenant_id", c.tenant),
        user_id=1,
        nome=dados.pop("nome", "Pessoa QA"),
        **dados,
    )
    c.db.add(registro)
    c.db.flush()
    return registro


@pytest.mark.parametrize(
    "entrada,chave",
    [
        (None, None),
        ("", None),
        ("sem telefone", None),
        ("(18) 99740-1641", "18997401641"),
        ("+55 18 99740-1641", "18997401641"),
        ("0055 18 99740-1641", "18997401641"),
        ("+55 (18) 3224-1234", "1832241234"),
        ("0055 18 3224-1234", "1832241234"),
        ("(55) 3224-1234", "5532241234"),
        ("(55) 99740-1641", "55997401641"),
        ("123 / 456 ramal 2", "1234562"),
        ("١٢٣-123", "123"),
    ],
)
def test_chave_python_e_sqlite_equivalentes_sem_inferir_numero(
    cadastro, entrada, chave
):
    assert normalizar_telefone_pessoa(entrada) == chave
    assert cadastro.db.scalar(select(telefone_pessoa_sql(entrada))) == chave


@pytest.mark.parametrize("origem", ["telefone", "celular", "adicional"])
def test_numero_colide_cruzado_e_contato_usa_numero_real(cadastro, origem):
    c = cadastro
    dono = pessoa(c, **({origem: "(18) 99740-1641"} if origem != "adicional" else {}))
    if origem == "adicional":
        c.db.add(
            ClienteContato(
                tenant_id=c.tenant,
                cliente_id=dono.id,
                numero="(18) 99740-1641",
                numero_digitos="stale",
                vinculo="familiar",
            )
        )
        c.db.flush()
    with pytest.raises(PessoaTelefoneDuplicado) as erro:
        validar_telefones_pessoa(c.db, c.tenant, celular="+55 18 99740-1641")
    assert erro.value.status_code == 409
    assert erro.value.campo == "celular"
    assert erro.value.loc == ["body", "celular"]
    assert str(dono.id) not in erro.value.detail


def test_legado_preserva_chaves_e_permite_remover_sem_fundir(cadastro):
    c = cadastro
    atual = pessoa(c, telefone="18997401641")
    outra = pessoa(c, celular="+55 (18) 99740-1641")
    c.db.commit()
    validar_telefones_pessoa(c.db, c.tenant, pessoa_atual=atual)
    validar_telefones_pessoa(
        c.db, c.tenant, pessoa_atual=atual, telefone="+55 18 99740-1641"
    )
    validar_telefones_pessoa(c.db, c.tenant, pessoa_atual=atual, telefone=None)
    validar_telefones_pessoa(c.db, c.tenant, pessoa_atual=atual, celular="18997402222")
    assert c.db.query(Cliente).count() == 2
    assert atual.telefone == "18997401641"
    assert outra.merged_into_id is None


def test_inativo_retem_numero_alias_fundido_nao_reserva(cadastro):
    c = cadastro
    dono = pessoa(c, telefone="18997401641", ativo=False)
    c.db.commit()
    with pytest.raises(PessoaTelefoneDuplicado):
        validar_telefones_pessoa(c.db, c.tenant, telefone="18997401641")
    dono.merged_into_id = 987
    c.db.commit()
    validar_telefones_pessoa(c.db, c.tenant, telefone="18997401641")


def test_reenviar_contato_legado_preserva_id_e_nao_recria_reserva(cadastro):
    c = cadastro
    atual = pessoa(c, telefone="18997401641")
    contato = ClienteContato(
        tenant_id=c.tenant,
        cliente_id=atual.id,
        numero="(18) 99740-1641",
        numero_digitos="18997401641",
        vinculo="familiar",
    )
    c.db.add(contato)
    c.db.commit()
    identidade = contato.id
    validar_contatos_adicionais(
        c.db,
        c.tenant,
        atual.id,
        [ClienteContatoInput(numero="18 99740 1641", vinculo="mãe")],
        None,
        atual.telefone,
        pessoa_atual=atual,
    )
    salvar_contatos_adicionais(
        c.db,
        atual,
        [
            ClienteContatoInput(
                numero="18 99740 1641",
                vinculo="mãe",
            )
        ],
    )
    c.db.commit()
    assert c.db.query(ClienteContato).one().id == identidade
    assert c.db.query(ClienteContato).one().vinculo == "mãe"


def test_escopo_usa_todos_grupos_ativos_sem_bloquear_tenant_independente(cadastro):
    c = cadastro
    vizinha, independente = uuid4(), uuid4()
    for numero, membros in enumerate(((c.tenant,), (c.tenant, vizinha)), 1):
        grupo = GrupoComercial(
            nome=f"Grupo {numero}",
            criado_por_empresa_id=str(c.tenant),
            criado_por_usuario_id=1,
            status="ativo",
        )
        c.db.add(grupo)
        c.db.flush()
        for tenant in membros:
            c.db.add(
                GrupoComercialMembro(
                    grupo_id=grupo.id,
                    empresa_id=str(tenant),
                    status="ativo",
                    papel="responsavel" if tenant == c.tenant else "membro",
                )
            )
    with tenant_context(vizinha):
        pessoa(c, tenant_id=vizinha, telefone="18997401641")
    with tenant_context(independente):
        pessoa(c, tenant_id=independente, telefone="18997402222")
    c.db.commit()
    assert set(resolver_escopo_telefone_pessoa(c.db, c.tenant)) == {
        str(c.tenant),
        str(vizinha),
    }
    with pytest.raises(PessoaTelefoneDuplicado):
        validar_telefones_pessoa(c.db, c.tenant, telefone="18997401641")
    validar_telefones_pessoa(c.db, c.tenant, telefone="18997402222")


def test_parser_reconhece_so_constraint_dedicada_sem_ler_texto_pessoal():
    for codigo, constraint, esperado in (
        ("23505", CONSTRAINT_TELEFONE, True),
        ("23505", "uq_clientes_tenant_codigo", False),
        ("23503", CONSTRAINT_TELEFONE, False),
    ):
        erro = SimpleNamespace(
            orig=SimpleNamespace(
                pgcode=codigo, diag=SimpleNamespace(constraint_name=constraint)
            )
        )
        assert erro_telefone_duplicado(erro) is esperado
    assert not erro_telefone_duplicado(ValueError(CONSTRAINT_TELEFONE))


def test_precheck_adquire_lock_antes_de_ler_contatos_mesmo_sem_nova_chave():
    chamadas = []

    class Registro:
        tenant_id = uuid4()
        id = 1
        merged_into_id = None
        telefone = "18997401641"
        celular = None

        @property
        def contatos_adicionais(self):
            assert chamadas == ["lock"]
            return []

    db = SimpleNamespace(
        no_autoflush=nullcontext(),
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=lambda *_: chamadas.append("lock"),
    )
    validar_telefones_pessoa(db, Registro.tenant_id, pessoa_atual=Registro())
    assert chamadas == ["lock"]


def test_seed_banho_tosa_usa_telefones_distintos_e_reexecucao_preserva_pessoa(cadastro):
    c = cadastro
    dados = dict(tenant_id=str(c.tenant), user_id=1, tipo="cliente")
    primeiro = ensure_person(
        c.db, **dados, codigo="UX-BT-CLI-01", nome="Pessoa QA1", telefone="11900000003"
    )
    segundo = ensure_person(
        c.db, **dados, codigo="UX-BT-CLI-02", nome="Pessoa QA2", telefone="11900000004"
    )
    repetido = ensure_person(
        c.db,
        **dados,
        codigo="UX-BT-CLI-01",
        nome="Pessoa QA1 alterada",
        telefone="11900000003",
    )
    assert primeiro == repetido
    assert primeiro != segundo
    assert {row[0] for row in c.db.execute(select(Cliente.__table__.c.telefone))} == {
        "11900000003",
        "11900000004",
    }


def test_consulta_duplicata_detecta_ddi_campo_cruzado_e_inativo(cadastro):
    c = cadastro
    dono = pessoa(c, codigo="1848", celular="18997401641", ativo=False)
    c.db.commit()
    resultado = verificar_duplicata(
        telefone="+55 (18) 99740-1641",
        db=c.db,
        user_and_tenant=(SimpleNamespace(id=1), c.tenant),
    )
    assert resultado["duplicado"] is True
    assert resultado["cliente"]["id"] == dono.id
    assert resultado["cliente"]["codigo"] == "1848"


@pytest.mark.parametrize("metodo", ["post", "put"])
def test_api_pessoa_devolve_409_sem_criar_ou_alterar_cadastro(
    cadastro, monkeypatch, metodo
):
    c = cadastro
    pessoa(c, celular="18997401641")
    atual = pessoa(c, telefone="18997402222", is_cliente=True)
    c.db.commit()
    monkeypatch.setattr(crud, "gerar_codigo_cliente", lambda *_: "200")
    # A visibilidade de grupos/RLS é exercitada no PostgreSQL; esta fixture
    # SQLite evita o CAST UUID legado do helper de leitura de cadastro.
    monkeypatch.setattr(
        crud,
        "_obter_cliente_ou_404",
        lambda db, pessoa_id, _tenant: db.get(Cliente, pessoa_id),
    )
    app = FastAPI()
    app.include_router(crud.base_router, prefix="/clientes")
    app.include_router(crud.detail_router, prefix="/clientes")
    app.dependency_overrides[_db.get_session] = lambda: c.db
    app.dependency_overrides[crud.get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        c.tenant,
    )
    with TestClient(app) as client:
        if metodo == "post":
            resposta = client.post(
                "/clientes/",
                json={
                    "nome": "Nova pessoa",
                    "is_cliente": True,
                    "telefone": "+55 18 99740-1641",
                },
            )
        else:
            resposta = client.put(
                f"/clientes/{atual.id}", json={"telefone": "+55 18 99740-1641"}
            )
    assert resposta.status_code == 409
    assert isinstance(resposta.json()["detail"], str)
    assert c.db.query(Cliente).count() == 2
    assert atual.telefone == "18997402222"


@pytest.mark.parametrize("mudar_telefone", [True, False])
def test_api_perfil_nao_funde_nova_colisao_e_permite_nome_no_legado(
    cadastro, monkeypatch, mudar_telefone
):
    c = cadastro
    pessoa(c, telefone="18997401641")
    original = "18997402222" if mudar_telefone else "18997401641"
    atual = pessoa(c, telefone=original, nome="Pessoa Original")
    c.db.commit()
    user = SimpleNamespace(
        id=1,
        nome="Pessoa Original",
        telefone=original,
        cpf_cnpj=None,
        tenant_id=c.tenant,
    )
    monkeypatch.setattr(perfil, "_get_or_create_cliente_for_user", lambda *_: atual)
    monkeypatch.setattr(perfil, "_serialize_profile", lambda *_a, **_kw: {"ok": True})
    monkeypatch.setattr(c.db, "refresh", lambda *_: None)
    app = FastAPI()
    app.include_router(perfil.router)
    app.dependency_overrides[_db.get_session] = lambda: c.db
    app.dependency_overrides[perfil._get_current_ecommerce_user] = lambda: user
    dados = {"nome": "Pessoa Atualizada"}
    if mudar_telefone:
        dados["telefone"] = "+55 18 99740-1641"
    with TestClient(app) as client:
        resposta = client.put("/perfil", json=dados)
    assert resposta.status_code == (409 if mudar_telefone else 200)
    assert c.db.query(Cliente).count() == 2
    assert atual.merged_into_id is None
    assert atual.telefone == original
    assert user.telefone == original
    assert atual.nome == ("Pessoa Original" if mudar_telefone else "Pessoa Atualizada")


@pytest.mark.parametrize("conflito", [True, False])
def test_login_com_vinculo_explicito_nao_atribui_telefone_de_outra_pessoa(
    cadastro, monkeypatch, conflito
):
    c = cadastro
    monkeypatch.setattr(
        cliente_app, "_activate_user_tenant_context", lambda _: c.tenant
    )
    user = SimpleNamespace(
        id=1,
        tenant_id=c.tenant,
        nome="Pessoa QA",
        email="qa-phone@example.com",
        telefone="+55 18 99740-1641",
        cpf_cnpj=None,
        login_phone=None,
    )
    atual = pessoa(
        c, auth_user_id=user.id, email=user.email, is_cliente=True, codigo="1848"
    )
    if conflito:
        pessoa(c, telefone="18997401641")
    c.db.commit()
    resultado = cliente_app._get_or_create_cliente_for_user(c.db, user)
    c.db.commit()
    assert resultado.id == atual.id
    assert resultado.auth_user_id == user.id
    assert resultado.telefone == (None if conflito else user.telefone)
    assert resultado.merged_into_id is None
    assert c.db.query(Cliente).count() == (2 if conflito else 1)


@pytest.mark.parametrize("formato", ["+55 (18) 99740-1641", "0055 18 99740-1641"])
def test_login_sms_reusa_pessoa_do_mesmo_tenant_com_ddi_sem_criar_ou_fundir(
    cadastro, monkeypatch, formato
):
    c = cadastro
    monkeypatch.setattr(
        cliente_app, "_activate_user_tenant_context", lambda _: c.tenant
    )
    user = SimpleNamespace(
        id=1,
        tenant_id=c.tenant,
        nome="Pessoa QA",
        email=None,
        telefone=None,
        cpf_cnpj=None,
        login_phone="18997401641",
    )
    original = pessoa(c, telefone=formato, is_cliente=True, codigo="1848", ativo=True)
    c.db.commit()
    resultado = cliente_app._get_or_create_cliente_for_user(c.db, user)
    c.db.commit()
    assert resultado.id == original.id
    assert resultado.codigo == "1848"
    assert resultado.telefone == formato
    assert resultado.auth_user_id == user.id
    assert resultado.merged_into_id is None
    assert c.db.query(Cliente).count() == 1


def test_login_sms_ddi_nao_toma_cadastro_vinculado_a_outra_conta(cadastro, monkeypatch):
    c = cadastro
    monkeypatch.setattr(
        cliente_app, "_activate_user_tenant_context", lambda _: c.tenant
    )
    user = SimpleNamespace(
        id=1,
        tenant_id=c.tenant,
        nome="Pessoa QA",
        email=None,
        telefone=None,
        cpf_cnpj=None,
        login_phone="18997401641",
    )
    original = pessoa(
        c, telefone="0055 18 99740-1641", is_cliente=True, ativo=True, auth_user_id=2
    )
    c.db.commit()
    with pytest.raises(HTTPException) as erro:
        cliente_app._get_or_create_cliente_for_user(c.db, user)
    assert erro.value.status_code == 409
    assert original.auth_user_id == 2
    assert original.merged_into_id is None
    assert c.db.query(Cliente).count() == 1


def test_signup_com_duas_pessoas_legadas_nao_cria_user_nem_funde_historico(
    cadastro, monkeypatch
):
    c = cadastro
    cpf = "52998224725"
    primeiro = pessoa(
        c,
        nome="Primeira Pessoa QA",
        codigo="1848",
        telefone="18997401641",
        cpf=cpf,
        is_cliente=True,
        ativo=True,
    )
    segundo = pessoa(
        c,
        nome="Segunda Pessoa QA",
        codigo="1849",
        celular="+55 18 99740-1641",
        cpf=cpf,
        is_cliente=True,
        ativo=True,
    )
    c.db.commit()
    monkeypatch.setattr(
        cadastro_publico, "_extract_tenant_id_from_request", lambda _: c.tenant
    )
    app = FastAPI()
    app.include_router(cadastro_publico.router)
    app.dependency_overrides[_db.get_session] = lambda: c.db
    with TestClient(app) as client:
        resposta = client.post(
            "/registrar",
            json={
                "email": "qa-cadastro-duplicado@example.com",
                "password": "SenhaQA123!",
                "nome": "Nova Conta QA",
                "telefone": "0055 18 99740-1641",
                "cpf": cpf,
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
    assert resposta.status_code == 409
    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, str) and "ERP" in detalhe
    for dado in (
        primeiro.nome,
        segundo.nome,
        primeiro.codigo,
        segundo.codigo,
        cpf,
        "18997401641",
    ):
        assert dado not in detalhe
    assert c.db.query(User).count() == 0
    assert c.db.query(PessoaMergeLog).count() == 0
    assert c.db.query(Cliente).count() == 2
    assert primeiro.auth_user_id is segundo.auth_user_id is None
    assert primeiro.merged_into_id is segundo.merged_into_id is None
    assert primeiro.telefone == "18997401641"
    assert segundo.celular == "+55 18 99740-1641"
