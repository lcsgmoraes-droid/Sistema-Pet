"""Login do painel administrativo: cookie, bloqueio, rotacao, reuso e troca de senha."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import adm_auth
from app.auth.core import hash_password
from app.db import Base, get_session
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession
from app.services.auth_security import MAX_FAILED_LOGIN_ATTEMPTS

ORIGEM = "http://localhost:5176"
CABECALHOS = {"Origin": ORIGEM, "X-Corepet-Adm": "1"}
SENHA = "Frase-longa-de-teste-42"


@pytest.fixture()
def contexto():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[PlatformAdmin.__table__, PlatformAdminSession.__table__],
    )
    Sessao = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(adm_auth.router)

    @app.get("/admin/teste")
    def rota_protegida(admin=Depends(require_platform_admin)):
        return {"email": admin.email}

    def _db():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = _db
    db = Sessao()
    db.add(
        PlatformAdmin(
            email="ana@corepet.com.br",
            name="Ana",
            hashed_password=hash_password(SENHA),
            is_active=True,
            painel_adm_ativo=True,
        )
    )
    db.add(
        PlatformAdmin(
            email="antigo@corepet.com.br",  # administrador do OPS, sem acesso ao painel
            name="Antigo",
            hashed_password=hash_password(SENHA),
            is_active=True,
            painel_adm_ativo=False,
        )
    )
    db.commit()
    yield TestClient(app), db
    db.close()


def _entrar(cliente, email="ana@corepet.com.br", senha=SENHA):
    return cliente.post(
        "/adm/auth/login", json={"email": email, "password": senha}, headers=CABECALHOS
    )


def _cookie(resposta):
    return resposta.cookies.get(adm_auth.COOKIE_NAME)


def _auth(resposta):
    return {"Authorization": f"Bearer {resposta.json()['access_token']}", **CABECALHOS}


# --- login ------------------------------------------------------------------------


def test_login_devolve_token_curto_no_corpo_e_a_renovacao_so_no_cookie(contexto):
    cliente, _ = contexto

    r = _entrar(cliente)

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["access_token"] and "refresh_token" not in corpo
    assert corpo["admin"]["email"] == "ana@corepet.com.br"
    cabecalho = r.headers["set-cookie"].lower()
    assert "httponly" in cabecalho and "samesite=strict" in cabecalho
    assert f"path={adm_auth.COOKIE_PATH}" in cabecalho
    assert _cookie(r)


def test_cookie_ganha_secure_atras_de_https(contexto):
    cliente, _ = contexto

    r = cliente.post(
        "/adm/auth/login",
        json={"email": "ana@corepet.com.br", "password": SENHA},
        headers={**CABECALHOS, "X-Forwarded-Proto": "https"},
    )

    assert "secure" in r.headers["set-cookie"].lower()


def test_erro_de_login_e_igual_para_senha_errada_email_inexistente_e_sem_permissao(
    contexto,
):
    cliente, _ = contexto

    respostas = [
        _entrar(cliente, senha="errada"),
        _entrar(cliente, email="ninguem@corepet.com.br"),
        _entrar(cliente, email="antigo@corepet.com.br"),  # senha certa, mas sem painel
    ]

    assert {r.status_code for r in respostas} == {401}
    assert {r.json()["detail"] for r in respostas} == {"E-mail ou senha incorretos"}


def test_conta_desativada_nao_entra(contexto):
    cliente, db = contexto
    db.query(PlatformAdmin).filter_by(email="ana@corepet.com.br").update(
        {"is_active": False}
    )
    db.commit()

    assert _entrar(cliente).status_code == 401


def test_bloqueia_apos_varias_tentativas_erradas(contexto):
    cliente, _ = contexto

    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        assert _entrar(cliente, senha="errada").status_code == 401

    assert (
        _entrar(cliente).status_code == 429
    )  # nem a senha certa entra enquanto bloqueado


def test_login_exige_origem_conhecida_e_cabecalho_do_painel(contexto):
    cliente, _ = contexto
    corpo = {"email": "ana@corepet.com.br", "password": SENHA}

    sem_origem = cliente.post(
        "/adm/auth/login", json=corpo, headers={"X-Corepet-Adm": "1"}
    )
    outra = cliente.post(
        "/adm/auth/login",
        json=corpo,
        headers={"Origin": "https://malicioso.example", "X-Corepet-Adm": "1"},
    )
    sem_cabecalho = cliente.post(
        "/adm/auth/login", json=corpo, headers={"Origin": ORIGEM}
    )

    assert [sem_origem.status_code, outra.status_code, sem_cabecalho.status_code] == [
        403,
        403,
        403,
    ]


# --- sessao protegida -------------------------------------------------------------


def test_token_do_painel_vale_nas_rotas_administrativas_e_sem_token_nao(contexto):
    cliente, _ = contexto
    r = _entrar(cliente)

    assert cliente.get("/admin/teste", headers=_auth(r)).json() == {
        "email": "ana@corepet.com.br"
    }
    assert cliente.get("/admin/teste").status_code in (401, 403)


def test_logout_revoga_a_sessao_e_limpa_o_cookie(contexto):
    cliente, _ = contexto
    r = _entrar(cliente)

    saiu = cliente.post("/adm/auth/logout", headers=_auth(r))

    assert saiu.status_code == 200
    assert f"{adm_auth.COOKIE_NAME}=" in saiu.headers["set-cookie"]
    assert cliente.get("/adm/auth/me", headers=_auth(r)).status_code == 401


# --- renovacao com rotacao ----------------------------------------------------------


def test_renovar_troca_o_cookie_e_o_antigo_deixa_de_servir(contexto):
    cliente, db = contexto
    r = _entrar(cliente)
    antigo = _cookie(r)

    nova = cliente.post(
        "/adm/auth/refresh", headers=CABECALHOS, cookies={adm_auth.COOKIE_NAME: antigo}
    )

    assert nova.status_code == 200 and nova.json()["access_token"]
    assert _cookie(nova) and _cookie(nova) != antigo
    # Duas abas renovando ao mesmo tempo: nao e roubo, so pede para tentar de novo.
    de_novo = cliente.post(
        "/adm/auth/refresh", headers=CABECALHOS, cookies={adm_auth.COOKIE_NAME: antigo}
    )
    assert de_novo.status_code == 409


def test_cookie_antigo_reutilizado_depois_da_janela_encerra_todas_as_sessoes(contexto):
    cliente, db = contexto
    r = _entrar(cliente)
    antigo = _cookie(r)
    nova = cliente.post(
        "/adm/auth/refresh", headers=CABECALHOS, cookies={adm_auth.COOKIE_NAME: antigo}
    )
    ha_um_minuto = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.query(PlatformAdminSession).filter_by(revoke_reason="renovada").update(
        {"revoked_at": ha_um_minuto}
    )
    db.commit()

    roubo = cliente.post(
        "/adm/auth/refresh", headers=CABECALHOS, cookies={adm_auth.COOKIE_NAME: antigo}
    )

    assert roubo.status_code == 401
    # a sessao legitima nova tambem cai: quem copiou o cookie nao pode ficar com acesso
    assert (
        cliente.post(
            "/adm/auth/refresh",
            headers=CABECALHOS,
            cookies={adm_auth.COOKIE_NAME: _cookie(nova)},
        ).status_code
        == 401
    )
    assert len(db.query(PlatformAdminSession).filter_by(revoked=False).all()) == 0


def test_renovar_sem_cookie_ou_de_origem_estranha_e_recusado(contexto):
    cliente, _ = contexto
    r = _entrar(cliente)
    cookie = _cookie(r)
    cliente.cookies.clear()  # o navegador simulado guarda o cookie do login

    sem_cookie = cliente.post("/adm/auth/refresh", headers=CABECALHOS)
    outra_origem = cliente.post(
        "/adm/auth/refresh",
        headers={"Origin": "https://malicioso.example", "X-Corepet-Adm": "1"},
        cookies={adm_auth.COOKIE_NAME: cookie},
    )

    assert sem_cookie.status_code == 401 and outra_origem.status_code == 403


def test_a_sessao_renovada_nao_passa_da_validade_absoluta(contexto):
    cliente, db = contexto
    r = _entrar(cliente)
    original = db.query(PlatformAdminSession).one().expires_at

    cliente.post(
        "/adm/auth/refresh",
        headers=CABECALHOS,
        cookies={adm_auth.COOKIE_NAME: _cookie(r)},
    )

    validades = {s.expires_at for s in db.query(PlatformAdminSession)}
    assert validades == {original}


# --- troca de senha ----------------------------------------------------------------


def test_troca_de_senha_exige_a_atual_e_uma_senha_forte(contexto):
    cliente, _ = contexto
    r = _entrar(cliente)
    cabecalho = _auth(r)

    errada = cliente.post(
        "/adm/auth/change-password",
        json={"senha_atual": "x", "nova_senha": "Outra-frase-longa-77"},
        headers=cabecalho,
    )
    fraca = cliente.post(
        "/adm/auth/change-password",
        json={"senha_atual": SENHA, "nova_senha": "admin1"},
        headers=cabecalho,
    )
    igual = cliente.post(
        "/adm/auth/change-password",
        json={"senha_atual": SENHA, "nova_senha": SENHA},
        headers=cabecalho,
    )

    assert errada.status_code == 400
    assert fraca.status_code == 422 and "12" in fraca.json()["detail"]
    assert igual.status_code == 422


def test_trocar_a_senha_encerra_as_outras_sessoes_e_vale_no_proximo_login(contexto):
    cliente, db = contexto
    primeira = _entrar(cliente)
    segunda = _entrar(cliente)

    r = cliente.post(
        "/adm/auth/change-password",
        json={"senha_atual": SENHA, "nova_senha": "Nova-frase-segura-99"},
        headers=_auth(segunda),
    )

    assert r.status_code == 200 and r.json()["outras_sessoes_encerradas"] == 1
    assert cliente.get("/adm/auth/me", headers=_auth(primeira)).status_code == 401
    assert cliente.get("/adm/auth/me", headers=_auth(r)).status_code == 200
    assert _entrar(cliente, senha=SENHA).status_code == 401
    assert _entrar(cliente, senha="Nova-frase-segura-99").status_code == 200


def test_senha_provisoria_bloqueia_os_dados_ate_trocar(contexto):
    cliente, db = contexto
    db.query(PlatformAdmin).filter_by(email="ana@corepet.com.br").update(
        {"must_change_password": True}
    )
    db.commit()
    r = _entrar(cliente)
    assert r.json()["admin"]["precisa_trocar_a_senha"] is True

    bloqueado = cliente.get("/admin/teste", headers=_auth(r))
    troca = cliente.post(
        "/adm/auth/change-password",
        json={"senha_atual": SENHA, "nova_senha": "Nova-frase-segura-99"},
        headers=_auth(r),
    )
    liberado = cliente.get("/admin/teste", headers=_auth(troca))

    assert bloqueado.status_code == 403
    assert troca.status_code == 200 and liberado.status_code == 200


# --- politica de senha --------------------------------------------------------------


@pytest.mark.parametrize(
    "nova,esperado",
    [
        ("Curta-1", "pelo menos"),
        ("a" * 80, "no máximo"),
        ("analucia-corepet-26", "e-mail"),
        ("111111111111", "fácil de adivinhar"),
        ("123456789012", "fácil de adivinhar"),
        ("987654321098", "só números"),
        ("somenteletrasaqui", "números ou símbolos"),
        ("Frase-longa-de-teste-43", ""),
    ],
)
def test_politica_de_senha(nova, esperado):
    erro = adm_auth.validar_nova_senha(
        nova, "Outra-senha-atual", "analucia@corepet.com.br"
    )

    assert (esperado in erro) if esperado else (erro == "")


def test_nao_existe_rota_de_cadastro():
    caminhos = {r.path for r in adm_auth.router.routes}

    assert caminhos == {
        "/adm/auth/login",
        "/adm/auth/refresh",
        "/adm/auth/me",
        "/adm/auth/logout",
        "/adm/auth/change-password",
    }
