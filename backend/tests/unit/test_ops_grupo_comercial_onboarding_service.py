import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

import app.services.ops_grupo_comercial_onboarding_service as onboarding_module
import app.services.tenant_provisioning_service as tenant_provisioning_service
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata (evita
# InvalidRequestError ao resolver relationship() por nome de outras classes,
# mesmo criando so um subconjunto de tabelas abaixo).
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialCodigo,
    GrupoComercialConvite,
    GrupoComercialMembro,
)
from app.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    Tenant,
    TenantLoginName,
    User,
    UserTenant,
)
from app.services.ops_grupo_comercial_onboarding_service import (
    OpsGrupoComercialOnboardingError,
    OpsLojaOnboarding,
    onboard_grupo_comercial,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant


def _contar(db, tabela: str, condicao: str = "1=1", **params) -> int:
    """Conta linhas via SQL bruto - tabelas multi-tenant (Tenant/User/...)
    bloqueiam consultas ORM sem contexto de tenant ativo (fail-fast do
    tenancy guard), e apos onboard_grupo_comercial() o contexto sempre
    termina limpo/restaurado para outro tenant, nunca o dos tenants criados."""
    return db.execute(text(f"SELECT count(*) FROM {tabela} WHERE {condicao}"), params).scalar_one()


def _campo_usuario(db, email: str, campo: str):
    return db.execute(
        text(f"SELECT {campo} FROM users WHERE email = :email"), {"email": email}
    ).scalar_one()


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/admin/grupos-comerciais/onboarding",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            TenantLoginName.__table__,
            User.__table__,
            Role.__table__,
            Permission.__table__,
            RolePermission.__table__,
            UserTenant.__table__,
            AuditLog.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialCodigo.__table__,
            GrupoComercialConvite.__table__,
        ],
    )
    session = Session(engine)

    monkeypatch.setattr(
        tenant_provisioning_service,
        "onboard_tenant_defaults",
        lambda **_kwargs: {"created": {}},
    )
    monkeypatch.setattr(onboarding_module, "send_email", lambda **_kwargs: True)
    monkeypatch.setenv("FRONTEND_URL", "https://app.exemplo.test")

    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def test_onboard_grupo_comercial_cria_grupo_unico_com_titular_responsavel_nas_n_lojas(
    db, monkeypatch
):
    emails_enviados = []
    monkeypatch.setattr(
        onboarding_module,
        "send_email",
        lambda **kwargs: emails_enviados.append(kwargs) or True,
    )

    resultado = onboard_grupo_comercial(
        db,
        request=_request(),
        titular_email="titular@example.com",
        titular_nome="Titular Onboarding",
        lojas=[
            OpsLojaOnboarding(nome_loja="Loja Centro"),
            OpsLojaOnboarding(nome_loja="Loja Sul"),
            OpsLojaOnboarding(nome_loja="Loja Norte"),
        ],
    )

    assert resultado.titular_email == "titular@example.com"
    assert len(resultado.lojas) == 3
    tenant_ids = {loja["tenant_id"] for loja in resultado.lojas}
    assert len(tenant_ids) == 3  # tres tenants distintos, nunca reaproveitados

    # um unico titular, reaproveitado nas tres lojas - onboarding assistido
    # nao cria um usuario por loja.
    assert _contar(db, "users", "email = :email", email="titular@example.com") == 1
    assert _campo_usuario(db, "titular@example.com", "reset_token") is not None

    membros = (
        db.query(GrupoComercialMembro)
        .filter(GrupoComercialMembro.grupo_id == resultado.grupo_id)
        .order_by(GrupoComercialMembro.id.asc())
        .all()
    )
    assert len(membros) == 3
    assert membros[0].papel == "responsavel"
    assert {m.empresa_id for m in membros} == tenant_ids
    assert all(m.papel == "membro" for m in membros[1:])
    assert all(m.status == "ativo" for m in membros)

    grupo = db.query(GrupoComercial).filter_by(id=resultado.grupo_id).one()
    assert grupo.status == "ativo"
    assert grupo.criado_por_empresa_id in tenant_ids

    assert len(emails_enviados) == 1
    assert emails_enviados[0]["to"] == "titular@example.com"


def test_onboard_grupo_comercial_recusa_email_ja_cadastrado_sem_provisionar_nada(
    db, monkeypatch
):
    # inserir um usuario exige contexto de tenant ativo (guard de insert);
    # ja a checagem de e-mail duplicado dentro de onboard_grupo_comercial usa
    # SELECT em "users", que esta na whitelist e nao exige contexto.
    outro_tenant = "66666666-6666-6666-6666-666666666666"
    set_current_tenant(outro_tenant)
    db.add(Tenant(id=outro_tenant, name="Outra Loja", name_normalized="outra loja"))
    db.add(
        User(
            email="ja-existe@example.com",
            hashed_password="hash",
            nome="Ja Existe",
            is_active=True,
            tenant_id=outro_tenant,
        )
    )
    db.commit()
    clear_current_tenant()

    monkeypatch.setattr(
        tenant_provisioning_service,
        "onboard_tenant_defaults",
        lambda **_kwargs: pytest.fail("nao deveria provisionar com e-mail duplicado"),
    )

    with pytest.raises(OpsGrupoComercialOnboardingError) as excinfo:
        onboard_grupo_comercial(
            db,
            request=_request(),
            titular_email="ja-existe@example.com",
            titular_nome="Ja Existe",
            lojas=[OpsLojaOnboarding(nome_loja="Loja Qualquer")],
        )

    assert excinfo.value.status_code == 409
    # so o tenant pre-existente da semente - nada novo foi provisionado.
    assert _contar(db, "tenants") == 1


def test_onboard_grupo_comercial_sem_lojas_e_rejeitado(db):
    with pytest.raises(OpsGrupoComercialOnboardingError) as excinfo:
        onboard_grupo_comercial(
            db,
            request=_request(),
            titular_email="sem-loja@example.com",
            titular_nome="Sem Loja",
            lojas=[],
        )
    assert excinfo.value.status_code == 400


def test_onboard_grupo_comercial_falha_na_primeira_loja_desfaz_tudo(db, monkeypatch):
    monkeypatch.setattr(
        tenant_provisioning_service,
        "onboard_tenant_defaults",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("template indisponivel")),
    )

    with pytest.raises(OpsGrupoComercialOnboardingError) as excinfo:
        onboard_grupo_comercial(
            db,
            request=_request(),
            titular_email="falha-primeira@example.com",
            titular_nome="Falha Primeira",
            lojas=[
                OpsLojaOnboarding(nome_loja="Loja Um"),
                OpsLojaOnboarding(nome_loja="Loja Dois"),
            ],
        )

    assert excinfo.value.status_code == 500
    assert _contar(db, "tenants") == 0
    assert _contar(db, "users", "email = :email", email="falha-primeira@example.com") == 0
    assert _contar(db, "grupos_comerciais") == 0


def test_onboard_grupo_comercial_falha_na_segunda_loja_desfaz_a_primeira_tambem(
    db, monkeypatch
):
    chamadas = {"n": 0}

    def onboard_intermitente(**_kwargs):
        chamadas["n"] += 1
        if chamadas["n"] >= 2:
            raise RuntimeError("template indisponivel na segunda loja")
        return {"created": {}}

    monkeypatch.setattr(
        tenant_provisioning_service, "onboard_tenant_defaults", onboard_intermitente
    )

    with pytest.raises(OpsGrupoComercialOnboardingError) as excinfo:
        onboard_grupo_comercial(
            db,
            request=_request(),
            titular_email="falha-segunda@example.com",
            titular_nome="Falha Segunda",
            lojas=[
                OpsLojaOnboarding(nome_loja="Loja Um"),
                OpsLojaOnboarding(nome_loja="Loja Dois"),
            ],
        )

    assert excinfo.value.status_code == 500
    # a primeira loja tinha sido provisionada com sucesso, mas tudo roda numa
    # unica transacao - a falha na segunda desfaz a primeira tambem.
    assert _contar(db, "tenants") == 0
    assert _contar(db, "grupos_comerciais") == 0
    assert _contar(db, "grupo_comercial_membros") == 0


def test_onboard_grupo_comercial_desfaz_tudo_se_email_de_senha_nao_enviar(db, monkeypatch):
    monkeypatch.setattr(onboarding_module, "send_email", lambda **_kwargs: False)

    with pytest.raises(OpsGrupoComercialOnboardingError) as excinfo:
        onboard_grupo_comercial(
            db,
            request=_request(),
            titular_email="sem-email@example.com",
            titular_nome="Sem Email",
            lojas=[OpsLojaOnboarding(nome_loja="Loja Unica")],
        )

    assert excinfo.value.status_code == 503
    assert _contar(db, "tenants") == 0
    assert _contar(db, "grupos_comerciais") == 0
