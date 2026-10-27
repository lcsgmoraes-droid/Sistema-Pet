"""Login do painel administrativo (adm.corepet.com.br).

Separado do login das lojas e mais rigido que o `/platform-auth` do OPS (que sera
aposentado). Reaproveita a tabela de administradores e as sessoes revogaveis, entao os
tokens daqui valem nas rotas `/admin/*` (`require_platform_admin`).

Regras de seguranca:
- nao existe cadastro: administradores sao criados pelo script `criar_admin_plataforma.py`;
- token de acesso curto (devolvido no corpo, guardado so na memoria do navegador) e renovacao
  por cookie HttpOnly + SameSite=Strict + Secure, com ROTACAO a cada renovacao;
- reuso de um cookie ja trocado revoga TODAS as sessoes da pessoa (indicio de roubo);
- sessao com validade absoluta (nao renova para sempre);
- cookies so aceitos de origens conhecidas (`ADM_ALLOWED_ORIGINS`) e com cabecalho proprio;
- erro de login generico, com custo de tempo igual para e-mail que nao existe;
- bloqueio por tentativas e limite por IP;
- trocar a senha revoga as outras sessoes; senha provisoria obriga a troca.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.core import ACCESS_TOKEN_EXPIRE_SECONDS, hash_password, verify_password
from app.config import settings
from app.db import get_session
from app.platform_auth import (
    PlatformAuthContext,
    _active_session,
    _aware,
    _credentials_error,
    _decode_platform_token,
    _is_locked,
    _register_failed_login,
    _token_pair,
    get_platform_auth_context,
)
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession
from app.security.client_ip import get_client_ip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/adm/auth", tags=["Painel administrativo - acesso"])

COOKIE_NAME = "adm_refresh"
COOKIE_PATH = "/adm/auth"
CABECALHO_DO_PAINEL = "x-corepet-adm"
JANELA_DE_RENOVACAO_SEGUNDOS = 10
SENHA_MINIMA = 12
SENHA_MAXIMA = 72
SENHAS_COMUNS = {
    "123456789012",
    "password1234",
    "senha1234567",
    "administrador",
    "corepet123456",
    "admin1234567",
}
# Hash fixo usado quando o e-mail nao existe, para gastar o mesmo tempo de uma conferencia real.
_HASH_FALSO = hash_password("senha-falsa-para-igualar-o-tempo")


def horas_de_sessao() -> int:
    try:
        return max(1, int(os.getenv("ADM_SESSION_HOURS", "8")))
    except ValueError:
        return 8


def origens_permitidas() -> set[str]:
    padrao = "http://localhost:5176,http://127.0.0.1:5176"
    bruto = os.getenv("ADM_ALLOWED_ORIGINS", padrao)
    return {item.strip().rstrip("/") for item in bruto.split(",") if item.strip()}


def _producao() -> bool:
    return str(settings.ENVIRONMENT or "").strip().lower() in {
        "production",
        "prod",
        "staging",
    }


def cookie_seguro(request: Request) -> bool:
    """Secure em producao/https; so fica de fora no desenvolvimento local em http."""
    if _producao():
        return True
    if os.getenv("ADM_COOKIE_SECURE", "").strip().lower() in {"1", "true", "sim"}:
        return True
    forwarded = (
        request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    )
    return request.url.scheme == "https" or forwarded == "https"


class LoginPedido(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TrocaDeSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=1, max_length=128)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def exigir_origem_do_painel(request: Request) -> None:
    """Protecao contra pedidos forjados: so o painel conhecido pode usar o cookie."""
    origem = (request.headers.get("origin") or "").strip().rstrip("/")
    if origem not in origens_permitidas() or not request.headers.get(
        CABECALHO_DO_PAINEL
    ):
        logger.warning("adm_auth_origem_recusada path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Origem não permitida")


def validar_nova_senha(nova: str, atual: str, email: str) -> str:
    """Politica de senha do painel. Devolve a mensagem de erro, ou '' se estiver boa."""
    if len(nova) < SENHA_MINIMA:
        return f"A nova senha precisa ter pelo menos {SENHA_MINIMA} caracteres."
    if len(nova.encode("utf-8")) > SENHA_MAXIMA:
        return f"A nova senha pode ter no máximo {SENHA_MAXIMA} caracteres."
    if nova == atual:
        return "A nova senha precisa ser diferente da atual."
    parte_do_email = email.split("@", 1)[0].lower()
    if len(parte_do_email) >= 4 and parte_do_email in nova.lower():
        return "A senha não pode conter o seu e-mail."
    if nova.lower() in SENHAS_COMUNS or len(set(nova)) < 5:
        return "Essa senha é fácil de adivinhar. Use uma frase longa ou letras, números e símbolos variados."
    if nova.isdigit():
        return "A senha não pode ter só números."
    if not (re.search(r"[A-Za-z]", nova) and re.search(r"\d|[^A-Za-z0-9]", nova)):
        return "Use letras e também números ou símbolos."
    return ""


def _dados_do_admin(admin: PlatformAdmin) -> dict:
    return {
        "id": admin.id,
        "nome": admin.name,
        "email": admin.email,
        "precisa_trocar_a_senha": bool(admin.must_change_password),
    }


def _definir_cookie(
    response: Response, request: Request, refresh_token: str, expira: datetime
) -> None:
    segundos = max(60, int((_aware(expira) - _agora()).total_seconds()))
    response.set_cookie(
        COOKIE_NAME,
        refresh_token,
        max_age=segundos,
        path=COOKIE_PATH,
        httponly=True,
        secure=cookie_seguro(request),
        samesite="strict",
    )


def _limpar_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=cookie_seguro(request),
        samesite="strict",
    )


def _nova_sessao(
    db: Session, admin: PlatformAdmin, request: Request, expira: datetime | None = None
) -> PlatformAdminSession:
    sessao = PlatformAdminSession(
        platform_admin_id=admin.id,
        token_jti=str(uuid.uuid4()),
        ip_address=get_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500],
        expires_at=expira or (_agora() + timedelta(hours=horas_de_sessao())),
    )
    db.add(sessao)
    db.flush()
    return sessao


def _resposta_de_sessao(
    admin: PlatformAdmin,
    sessao: PlatformAdminSession,
    request: Request,
    response: Response,
) -> dict:
    acesso, renovacao = _token_pair(admin.id, sessao)
    _definir_cookie(response, request, renovacao, sessao.expires_at)
    return {
        "access_token": acesso,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "admin": _dados_do_admin(admin),
    }


def _revogar(sessao: PlatformAdminSession, motivo: str) -> None:
    sessao.revoked = True
    sessao.revoked_at = _agora()
    sessao.revoke_reason = motivo


def _revogar_todas(
    db: Session, admin_id: int, motivo: str, exceto_id: int | None = None
) -> int:
    consulta = db.query(PlatformAdminSession).filter(
        PlatformAdminSession.platform_admin_id == admin_id,
        PlatformAdminSession.revoked.is_(False),
    )
    total = 0
    for sessao in consulta:
        if exceto_id is not None and sessao.id == exceto_id:
            continue
        _revogar(sessao, motivo)
        total += 1
    return total


@router.post("/login")
def entrar(
    dados: LoginPedido,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    exigir_origem_do_painel(request)
    email = dados.email.strip().lower()
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()

    senha_ok = verify_password(
        dados.password, admin.hashed_password if admin else _HASH_FALSO
    )
    if admin is not None and _is_locked(admin):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
        )
    if (
        admin is None
        or not senha_ok
        or not admin.is_active
        or not admin.painel_adm_ativo
    ):
        if admin is not None and not senha_ok:
            _register_failed_login(admin)
            db.commit()
        logger.warning("adm_login_falhou ip=%s", get_client_ip(request))
        # Mesma resposta para e-mail inexistente, senha errada e conta desativada.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = _agora()
    admin.last_login_ip = get_client_ip(request)
    sessao = _nova_sessao(db, admin, request)
    db.commit()
    logger.info("adm_login_ok admin_id=%s", admin.id)
    return _resposta_de_sessao(admin, sessao, request, response)


@router.post("/refresh")
def renovar(
    request: Request, response: Response, db: Session = Depends(get_session)
) -> dict:
    exigir_origem_do_painel(request)
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        raise _credentials_error("Sessão administrativa expirada")
    try:
        payload = _decode_platform_token(cookie, "refresh")
    except HTTPException:
        _limpar_cookie(response, request)
        raise

    sessao_antiga = (
        db.query(PlatformAdminSession)
        .filter(PlatformAdminSession.token_jti == str(payload["jti"]))
        .first()
    )
    if (
        sessao_antiga is not None
        and sessao_antiga.revoked
        and sessao_antiga.revoke_reason == "renovada"
    ):
        trocada_ha = (
            _agora() - _aware(sessao_antiga.revoked_at or _agora())
        ).total_seconds()
        if trocada_ha <= JANELA_DE_RENOVACAO_SEGUNDOS:
            # Duas abas renovando ao mesmo tempo: a outra ja trocou. Nao e roubo; o painel
            # tenta de novo e o navegador ja tem o cookie novo.
            raise HTTPException(
                status_code=409, detail="Renovação em andamento. Tente de novo."
            )
        # Um cookie que ja foi trocado ha tempo voltou a ser usado: alguem o copiou.
        _revogar_todas(db, sessao_antiga.platform_admin_id, "reuso de renovacao")
        db.commit()
        logger.warning(
            "adm_refresh_reutilizado admin_id=%s", sessao_antiga.platform_admin_id
        )
        raise _credentials_error(
            "Sessão administrativa revogada por segurança. Entre de novo."
        )

    try:
        admin, sessao_antiga = _active_session(db, payload)
    except HTTPException:
        _limpar_cookie(response, request)
        raise
    nova = _nova_sessao(db, admin, request, expira=sessao_antiga.expires_at)
    _revogar(sessao_antiga, "renovada")
    db.commit()
    return _resposta_de_sessao(admin, nova, request, response)


@router.get("/me")
def quem_sou(
    contexto: PlatformAuthContext = Depends(get_platform_auth_context),
) -> dict:
    admin = contexto.admin
    dados = _dados_do_admin(admin)
    dados["senha_alterada_em"] = (
        admin.password_changed_at.isoformat() if admin.password_changed_at else None
    )
    return dados


@router.post("/logout")
def sair(
    request: Request,
    response: Response,
    contexto: PlatformAuthContext = Depends(get_platform_auth_context),
    db: Session = Depends(get_session),
) -> dict:
    exigir_origem_do_painel(request)
    _revogar(contexto.session, "logout")
    db.commit()
    _limpar_cookie(response, request)
    return {"mensagem": "Sessão encerrada"}


@router.post("/change-password")
def trocar_senha(
    dados: TrocaDeSenha,
    request: Request,
    response: Response,
    contexto: PlatformAuthContext = Depends(get_platform_auth_context),
    db: Session = Depends(get_session),
) -> dict:
    exigir_origem_do_painel(request)
    admin = contexto.admin
    if _is_locked(admin):
        raise HTTPException(
            status_code=429, detail="Muitas tentativas. Aguarde e tente novamente."
        )
    if not verify_password(dados.senha_atual, admin.hashed_password):
        _register_failed_login(admin)
        db.commit()
        raise HTTPException(status_code=400, detail="A senha atual não confere.")
    erro = validar_nova_senha(dados.nova_senha, dados.senha_atual, admin.email)
    if erro:
        raise HTTPException(status_code=422, detail=erro)

    admin.hashed_password = hash_password(dados.nova_senha)
    admin.password_changed_at = _agora()
    admin.must_change_password = False
    admin.failed_login_attempts = 0
    admin.locked_until = None
    # Quem estiver logado em outro lugar com a senha antiga e desconectado.
    encerradas = _revogar_todas(
        db, admin.id, "senha alterada", exceto_id=contexto.session.id
    )
    nova = _nova_sessao(db, admin, request, expira=contexto.session.expires_at)
    _revogar(contexto.session, "renovada")
    db.commit()
    logger.info(
        "adm_senha_trocada admin_id=%s outras_sessoes_encerradas=%s",
        admin.id,
        encerradas,
    )
    resposta = _resposta_de_sessao(admin, nova, request, response)
    resposta["outras_sessoes_encerradas"] = encerradas
    return resposta
