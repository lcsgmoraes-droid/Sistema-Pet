"""
Bling OAuth2 - Callback e renovação automática de tokens
"""
import os
import base64
import logging
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/bling", tags=["Bling OAuth"])

# Onde ficam os .env (tenta os dois caminhos)
ENV_PATHS = [
    Path("/opt/petshop/.env"),
    Path(__file__).parent.parent.parent / ".env",
    Path(__file__).parent.parent / ".env",
]


def _get_env_path() -> Path:
    for p in ENV_PATHS:
        if p.exists():
            return p
    # fallback: raiz do projeto
    return Path(".env")


def _salvar_tokens(access_token: str, refresh_token: str):
    """Salva tokens no arquivo .env"""
    env_path = _get_env_path()
    logger.info(f"Salvando tokens em: {env_path}")

    if not env_path.exists():
        logger.warning(f"Arquivo .env não encontrado em {env_path}, criando...")
        env_path.write_text("")

    linhas = env_path.read_text(encoding="utf-8").splitlines()
    novas_linhas = []
    achou_access = False
    achou_refresh = False

    for linha in linhas:
        if linha.startswith("BLING_ACCESS_TOKEN="):
            novas_linhas.append(f"BLING_ACCESS_TOKEN={access_token}")
            achou_access = True
        elif linha.startswith("BLING_REFRESH_TOKEN="):
            novas_linhas.append(f"BLING_REFRESH_TOKEN={refresh_token}")
            achou_refresh = True
        else:
            novas_linhas.append(linha)

    if not achou_access:
        novas_linhas.append(f"BLING_ACCESS_TOKEN={access_token}")
    if not achou_refresh:
        novas_linhas.append(f"BLING_REFRESH_TOKEN={refresh_token}")

    env_path.write_text("\n".join(novas_linhas) + "\n", encoding="utf-8")

    # Atualizar variáveis de ambiente em memória para uso imediato
    os.environ["BLING_ACCESS_TOKEN"] = access_token
    os.environ["BLING_REFRESH_TOKEN"] = refresh_token

    logger.info("✅ Tokens Bling salvos com sucesso")


def _trocar_code_por_tokens(code: str, redirect_uri: str) -> dict:
    """Troca o authorization code pelos tokens de acesso"""
    client_id = os.getenv("BLING_CLIENT_ID", "").strip()
    client_secret = os.getenv("BLING_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise ValueError("BLING_CLIENT_ID ou BLING_CLIENT_SECRET não configurados")

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://www.bling.com.br/Api/v3/oauth/token",
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
        raise Exception(f"Erro Bling OAuth: {response.status_code} - {response.text}")

    return response.json()


@router.get("/callback", response_class=HTMLResponse)
async def bling_oauth_callback(request: Request, code: str = None, error: str = None, state: str = None):
    """
    Endpoint de callback OAuth do Bling.
    O Bling redireciona aqui após o usuário autorizar o aplicativo.
    """
    if error:
        logger.error(f"Bling OAuth erro: {error}")
        return HTMLResponse(content=_html_erro(f"Bling retornou erro: {error}"), status_code=400)

    if not code:
        return HTMLResponse(content=_html_erro("Código de autorização não recebido"), status_code=400)

    try:
        # Montar redirect_uri com base na request atual
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/auth/bling/callback"

        logger.info(f"Trocando code por tokens (redirect_uri={redirect_uri})")
        tokens = _trocar_code_por_tokens(code, redirect_uri)

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 21600)

        if not access_token or not refresh_token:
            raise Exception(f"Resposta inválida: {tokens}")

        _salvar_tokens(access_token, refresh_token)

        expira_em = datetime.now() + timedelta(seconds=expires_in)
        logger.info(f"✅ Bling OAuth concluído. Token expira em: {expira_em.strftime('%d/%m/%Y %H:%M')}")

        return HTMLResponse(content=_html_sucesso(expira_em, access_token))

    except Exception as e:
        logger.error(f"Erro no callback OAuth Bling: {e}")
        return HTMLResponse(content=_html_erro(str(e)), status_code=500)


@router.get("/link-autorizacao")
async def gerar_link_autorizacao(request: Request):
    """
    Retorna o link para o usuário autorizar o aplicativo no Bling.
    Acesse este endpoint para obter a URL de autorização.
    """
    client_id = os.getenv("BLING_CLIENT_ID", "").strip()
    if not client_id:
        return {"erro": "BLING_CLIENT_ID não configurado"}

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/auth/bling/callback"

    import secrets
    state = secrets.token_hex(16)

    auth_url = (
        f"https://www.bling.com.br/Api/v3/oauth/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        f"&state={state}"
    )

    return {
        "instrucao": "Acesse a URL abaixo no navegador para autorizar o Bling",
        "url_autorizacao": auth_url,
        "redirect_uri_configurado": redirect_uri,
        "importante": "O 'Link de redirecionamento' no cadastro do app Bling deve ser: " + redirect_uri,
    }


@router.get("/status-token")
async def status_token():
    """Verifica se o token está configurado e tenta uma chamada de teste"""
    token = os.getenv("BLING_ACCESS_TOKEN", "").strip()
    refresh = os.getenv("BLING_REFRESH_TOKEN", "").strip()

    if not token:
        return {"status": "sem_token", "mensagem": "BLING_ACCESS_TOKEN não configurado"}

    # Testar token fazendo uma chamada simples
    try:
        r = requests.get(
            "https://api.bling.com.br/Api/v3/situacoes/modulos",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "enable-jwt": "1"},
            timeout=10,
        )
        if r.status_code == 200:
            return {
                "status": "ok",
                "token_valido": True,
                "token_preview": token[:15] + "...",
                "refresh_token_configurado": bool(refresh),
            }
        elif r.status_code == 401:
            return {
                "status": "expirado",
                "token_valido": False,
                "mensagem": "Token expirado. Acesse GET /auth/bling/link-autorizacao para renovar.",
                "refresh_token_configurado": bool(refresh),
            }
        else:
            return {"status": "erro", "http_status": r.status_code, "detalhe": r.text[:200]}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}


def _html_sucesso(expira_em: datetime, token: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><title>Bling Autorizado</title>
    <style>body{{font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f9f0}}
    .box{{background:white;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center;max-width:480px}}
    h1{{color:#2e7d32;font-size:2em}}p{{color:#555;line-height:1.6}}
    .badge{{background:#e8f5e9;color:#2e7d32;padding:8px 16px;border-radius:20px;font-weight:bold;display:inline-block;margin:10px 0}}
    </style></head>
    <body><div class="box">
    <h1>✅ Bling Autorizado!</h1>
    <p>O token foi salvo com sucesso no sistema.</p>
    <div class="badge">Token expira em: {expira_em.strftime('%d/%m/%Y às %H:%M')}</div>
    <p style="margin-top:20px">Você já pode fechar esta janela.<br>O sistema vai renovar o token automaticamente.</p>
    </div></body></html>
    """


def _html_erro(mensagem: str) -> str:
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
    <h1>❌ Erro na autorização</h1>
    <div class="erro">{mensagem}</div>
    <p>Tente novamente acessando <strong>GET /auth/bling/link-autorizacao</strong></p>
    </div></body></html>
    """
