"""
Bling OAuth2 - callback e renovacao automatica de tokens.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from html import escape
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration_parts.core import (
    BLING_OAUTH_TOKEN_URL,
    _bling_token_lock,
    _load_bling_runtime_config,
)
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.services.bling_connection_service import (
    load_bling_app_credentials,
    load_bling_credentials,
    save_bling_app_credentials,
    save_bling_tokens,
)
from app.services.bling_tenant_guard import (
    bling_tenant_id_configurado,
    tenant_pode_usar_bling_global,
)
from app.tenancy.context import get_current_tenant


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/bling", tags=["Bling OAuth"])
public_router = APIRouter(prefix="/auth/bling", tags=["Bling OAuth"])

OAUTH_STATE_TTL_SECONDS = 600


class BlingOAuthAppConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1, max_length=255)
    client_secret: str = Field(min_length=1, max_length=1000)

    @field_validator("client_id", "client_secret")
    @classmethod
    def strip_value(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Campo obrigatorio")
        return normalized


def _bling_redirect_uri(request: Request) -> str:
    configured_uri = os.getenv("BLING_REDIRECT_URI", "").strip()
    if configured_uri:
        return configured_uri

    public_base_url = (
        os.getenv("ECOMMERCE_PUBLIC_BASE_URL", "").strip()
        or os.getenv("FRONTEND_PUBLIC_BASE_URL", "").strip()
    )
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/api/auth/bling/callback"

    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/auth/bling/callback"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _encode_oauth_state(
    *, tenant_id: UUID | str | None = None, expires_in: int = OAUTH_STATE_TTL_SECONDS
) -> str:
    resolved_tenant = tenant_id or get_current_tenant()
    payload = {
        "exp": int(time.time()) + int(expires_in),
        "nonce": secrets.token_urlsafe(16),
        "purpose": "bling_oauth",
        "tenant_id": str(resolved_tenant) if resolved_tenant else None,
    }
    payload_raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    payload_part = _b64url_encode(payload_raw)
    signature = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def _decode_oauth_state(state: str | None) -> dict | None:
    raw = str(state or "").strip()
    if not raw or "." not in raw:
        return None

    payload_part, signature_part = raw.split(".", 1)
    expected = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        received = _b64url_decode(signature_part)
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except Exception:
        return None

    valid = (
        hmac.compare_digest(expected, received)
        and payload.get("purpose") == "bling_oauth"
        and int(payload.get("exp") or 0) >= int(time.time())
    )
    if not valid:
        return None
    try:
        payload["tenant_id"] = str(UUID(str(payload.get("tenant_id"))))
    except (TypeError, ValueError):
        return None
    return payload


def _validate_oauth_state(state: str | None) -> bool:
    return _decode_oauth_state(state) is not None


def _salvar_tokens(
    access_token: str,
    refresh_token: str,
    expires_in: int = 21600,
    *,
    tenant_id: UUID | str | None = None,
    increment_renewal: bool = False,
    db: Session | None = None,
    lock_held: bool = False,
):
    """Salva tokens criptografados no tenant correto."""
    resolved_tenant = tenant_id or get_current_tenant() or bling_tenant_id_configurado()
    if not resolved_tenant:
        raise RuntimeError("Tenant nao identificado para salvar tokens do Bling")

    if lock_held:
        save_bling_tokens(
            tenant_id=resolved_tenant,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            increment_renewal=increment_renewal,
            db=db,
        )
    else:
        with _bling_token_lock():
            save_bling_tokens(
                tenant_id=resolved_tenant,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                increment_renewal=increment_renewal,
                db=db,
            )

    logger.info("Tokens Bling salvos com seguranca para o tenant %s", resolved_tenant)


def _legacy_oauth_app_credentials(tenant_id: UUID | str) -> dict[str, str] | None:
    if not tenant_pode_usar_bling_global(tenant_id):
        return None
    client_id = os.getenv("BLING_CLIENT_ID", "").strip()
    client_secret = os.getenv("BLING_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "source": "legacy",
    }


def _oauth_app_credentials_for_tenant(
    tenant_id: UUID | str,
    *,
    db: Session | None = None,
) -> dict[str, str] | None:
    return load_bling_app_credentials(
        tenant_id, db=db
    ) or _legacy_oauth_app_credentials(tenant_id)


def _trocar_code_por_tokens(
    code: str,
    redirect_uri: str,
    *,
    tenant_id: UUID | str,
    db: Session | None = None,
) -> dict:
    """Troca o authorization code pelos tokens de acesso."""
    credentials = _oauth_app_credentials_for_tenant(tenant_id, db=db)
    if not credentials:
        raise RuntimeError(
            "Aplicativo OAuth do Bling nao configurado para esta empresa"
        )
    client_id = credentials["client_id"]
    client_secret = credentials["client_secret"]

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        BLING_OAUTH_TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
            "enable-jwt": "1",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Erro Bling OAuth: HTTP {response.status_code}")

    return response.json()


@public_router.get("/callback", response_class=HTMLResponse)
def bling_oauth_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_session),
):
    """
    Endpoint de callback OAuth do Bling.
    O Bling redireciona aqui apos o usuario autorizar o aplicativo.
    """
    if error:
        logger.error("Bling OAuth retornou erro no callback")
        return HTMLResponse(
            content=_html_erro("Bling retornou erro de autorizacao"),
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            content=_html_erro("Codigo de autorizacao nao recebido"),
            status_code=400,
        )

    state_payload = _decode_oauth_state(state)
    if not state_payload:
        return HTMLResponse(
            content=_html_erro("Estado de autorizacao invalido ou expirado"),
            status_code=400,
        )

    try:
        tenant_id = UUID(state_payload["tenant_id"])
        redirect_uri = _bling_redirect_uri(request)

        logger.info("Trocando code por tokens Bling")
        tokens = _trocar_code_por_tokens(
            code,
            redirect_uri,
            tenant_id=tenant_id,
            db=db,
        )

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 21600)

        if not access_token or not refresh_token:
            raise RuntimeError("Resposta invalida do Bling OAuth")

        _salvar_tokens(
            access_token,
            refresh_token,
            expires_in=expires_in,
            tenant_id=tenant_id,
            db=db,
        )

        expira_em = datetime.now() + timedelta(seconds=expires_in)
        logger.info("Bling OAuth concluido")

        return HTMLResponse(content=_html_sucesso(expira_em))

    except Exception:
        logger.exception("Erro no callback OAuth Bling")
        return HTMLResponse(
            content=_html_erro("Nao foi possivel concluir a autorizacao do Bling"),
            status_code=500,
        )


@router.get("/link-autorizacao")
def gerar_link_autorizacao(
    request: Request,
    redirect: Annotated[
        bool,
        Query(
            description="Quando true, redireciona direto para a autorizacao do Bling."
        ),
    ] = False,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Retorna o link para o usuario autorizar o aplicativo no Bling.
    Acesse este endpoint para obter a URL de autorizacao.
    """
    redirect_uri = _bling_redirect_uri(request)
    _current_user, tenant_id = user_and_tenant
    credentials = _oauth_app_credentials_for_tenant(tenant_id, db=db)
    if not credentials:
        return {
            "erro": "Configure o aplicativo OAuth do Bling para esta empresa",
            "redirect_uri_configurado": redirect_uri,
        }
    client_id = credentials["client_id"]
    state = _encode_oauth_state(tenant_id=tenant_id)

    auth_url = (
        "https://www.bling.com.br/Api/v3/oauth/authorize"
        "?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        f"&state={state}"
    )

    if redirect:
        return RedirectResponse(url=auth_url, status_code=307)

    return {
        "instrucao": "Acesse a URL abaixo no navegador para autorizar o Bling",
        "url_autorizacao": auth_url,
        "redirect_uri_configurado": redirect_uri,
        "importante": (
            "O 'Link de redirecionamento' no cadastro do app Bling deve ser: "
            + redirect_uri
        ),
    }


def _mask_client_id(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) <= 10:
        return f"{raw[:2]}...{raw[-2:]}"
    return f"{raw[:6]}...{raw[-4:]}"


@router.get("/configuracao")
def buscar_configuracao_oauth_bling(
    request: Request,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Informa se o tenant possui aplicativo OAuth sem expor o segredo."""
    current_user, tenant_id = user_and_tenant
    if not current_user.is_admin:
        return {
            "configured": bool(_oauth_app_credentials_for_tenant(tenant_id, db=db)),
            "can_manage": False,
            "redirect_uri": _bling_redirect_uri(request),
        }

    tenant_credentials = load_bling_app_credentials(tenant_id, db=db)
    effective_credentials = tenant_credentials or _legacy_oauth_app_credentials(
        tenant_id
    )
    return {
        "configured": bool(effective_credentials),
        "can_manage": True,
        "source": (effective_credentials or {}).get("source"),
        "client_id_preview": _mask_client_id(
            (effective_credentials or {}).get("client_id")
        ),
        "client_secret_configured": bool(
            (effective_credentials or {}).get("client_secret")
        ),
        "redirect_uri": _bling_redirect_uri(request),
    }


@router.put("/configuracao")
def salvar_configuracao_oauth_bling(
    body: BlingOAuthAppConfigUpdate,
    request: Request,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Salva as credenciais do aplicativo Bling somente para o tenant atual."""
    current_user, tenant_id = user_and_tenant
    if not current_user.is_admin:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente administradores podem configurar o aplicativo Bling.",
        )

    connection = save_bling_app_credentials(
        tenant_id=tenant_id,
        client_id=body.client_id,
        client_secret=body.client_secret,
        db=db,
    )
    return {
        "configured": True,
        "can_manage": True,
        "source": "tenant",
        "client_id_preview": _mask_client_id(connection.oauth_client_id),
        "client_secret_configured": bool(connection.oauth_client_secret),
        "redirect_uri": _bling_redirect_uri(request),
    }


@router.get("/status-token")
def status_token(user_and_tenant=Depends(get_current_user_and_tenant)):
    """Verifica se o token esta configurado e tenta uma chamada de teste."""
    _current_user, tenant_id = user_and_tenant
    credentials = load_bling_credentials(tenant_id)
    if not credentials:
        runtime_config = _load_bling_runtime_config()
        if runtime_config.get("source") != "legacy":
            return {
                "status": "sem_token",
                "mensagem": "Bling nao conectado para esta empresa",
            }
        credentials = runtime_config
    token = str(credentials.get("access_token") or "").strip()
    refresh = str(credentials.get("refresh_token") or "").strip()

    if not token:
        return {"status": "sem_token", "mensagem": "BLING_ACCESS_TOKEN nao configurado"}

    try:
        response = requests.get(
            "https://api.bling.com.br/Api/v3/situacoes/modulos",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "enable-jwt": "1",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return {
                "status": "ok",
                "token_valido": True,
                "refresh_token_configurado": bool(refresh),
            }
        if response.status_code == 401:
            return {
                "status": "expirado",
                "token_valido": False,
                "mensagem": (
                    "Token expirado. Acesse GET /auth/bling/link-autorizacao para "
                    "renovar."
                ),
                "refresh_token_configurado": bool(refresh),
            }
        return {
            "status": "erro",
            "http_status": response.status_code,
            "detalhe": response.text[:200],
        }
    except Exception as exc:
        return {"status": "erro", "mensagem": str(exc)}


def _html_sucesso(expira_em: datetime) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><title>Bling Autorizado</title>
    <style>body{{font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f9f0}}
    .box{{background:white;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center;max-width:480px}}
    h1{{color:#2e7d32;font-size:2em}}p{{color:#555;line-height:1.6}}
    .badge{{background:#e8f5e9;color:#2e7d32;padding:8px 16px;border-radius:20px;font-weight:bold;display:inline-block;margin:10px 0}}
    .btn{{display:inline-block;margin-top:14px;background:#1976d2;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:600}}
    </style></head>
    <body><div class="box">
    <h1>Bling Autorizado!</h1>
    <p>O token foi salvo com sucesso no sistema.</p>
    <div class="badge">Token expira em: {expira_em.strftime("%d/%m/%Y as %H:%M")}</div>
    <p style="margin-top:20px">Redirecionando para o sistema em <span id="contador">3</span> segundos...</p>
    <a class="btn" href="/configuracoes/integracoes">Voltar agora</a>
    </div>
    <script>
        (function() {{
            var segundos = 3;
            var el = document.getElementById('contador');
            var timer = setInterval(function() {{
                segundos -= 1;
                if (el && segundos >= 0) el.textContent = String(segundos);
                if (segundos <= 0) {{
                    clearInterval(timer);
                    window.location.href = '/configuracoes/integracoes';
                }}
            }}, 1000);
        }})();
    </script>
    </body></html>
    """


def _html_erro(mensagem: str) -> str:
    mensagem_segura = escape(mensagem, quote=True)
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><title>Erro OAuth Bling</title>
    <style>body{{font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#fff0f0}}
    .box{{background:white;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center;max-width:480px}}
    h1{{color:#c62828}}p{{color:#555}}
    .erro{{background:#ffebee;color:#c62828;padding:12px;border-radius:8px;font-family:monospace;font-size:.85em;margin:16px 0;word-break:break-all}}
    </style></head>
    <body><div class="box">
    <h1>Erro na autorizacao</h1>
    <div class="erro">{mensagem_segura}</div>
    <p>Tente novamente acessando <strong>GET /auth/bling/link-autorizacao</strong></p>
    </div></body></html>
    """
