from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import dotenv_values

from app.utils.logger import logger


BLING_API_BASE_URL = "https://api.bling.com.br/Api/v3"
BLING_NFE_SERIE_PADRAO = 1
BLING_NFCE_SERIE_PADRAO = 3
TOKEN_CONTROL_FILE = Path("bling_token_control.json")
_BLING_RATE_LOCK = threading.Lock()
_BLING_LAST_REQUEST_AT = 0.0
_BLING_MIN_INTERVAL_SECONDS = 0.42
ENV_PATHS = [
    Path("/opt/petshop/.env"),
    Path(__file__).resolve().parents[2] / ".env",
    Path(__file__).resolve().parents[3] / ".env",
]


def _get_shared_env_path() -> Optional[Path]:
    for path in ENV_PATHS:
        if path.exists():
            return path
    return None


def _load_bling_runtime_config() -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = _get_shared_env_path()

    if env_path:
        try:
            values = {
                key: str(value)
                for key, value in dotenv_values(env_path).items()
                if value is not None
            }
        except Exception as error:
            logger.warning(
                f"Nao foi possivel reler configuracao compartilhada do Bling em {env_path}: {error}"
            )

    def pick(name: str, default: str = "") -> str:
        return (values.get(name) or os.getenv(name) or default).strip()

    return {
        "access_token": pick("BLING_ACCESS_TOKEN"),
        "refresh_token": pick("BLING_REFRESH_TOKEN"),
        "client_id": pick("BLING_CLIENT_ID"),
        "client_secret": pick("BLING_CLIENT_SECRET"),
        "enable_jwt": pick("BLING_ENABLE_JWT", "1"),
        "ambiente": pick("BLING_NFE_AMBIENTE", "rascunho"),
    }


def _aguardar_slot_bling() -> None:
    global _BLING_LAST_REQUEST_AT

    with _BLING_RATE_LOCK:
        now = time.monotonic()
        wait_for = _BLING_MIN_INTERVAL_SECONDS - (now - _BLING_LAST_REQUEST_AT)
        if wait_for > 0:
            time.sleep(wait_for)
            now = time.monotonic()
        _BLING_LAST_REQUEST_AT = now


def _tempo_espera_rate_limit_bling(response, tentativa: int) -> float:
    retry_after = None
    if response is not None:
        retry_after = getattr(response, "headers", {}).get("Retry-After")

    try:
        if retry_after:
            return min(max(float(retry_after), 1.0), 8.0)
    except (TypeError, ValueError):
        pass

    return min(1.2 + tentativa * 0.8, 5.0)


def _erro_rate_limit_bling(error: requests.exceptions.HTTPError) -> bool:
    response = getattr(error, "response", None)
    if response is not None and response.status_code == 429:
        return True

    mensagem = str(error)
    if response is not None:
        mensagem = f"{mensagem} {getattr(response, 'text', '')}"

    mensagem = mensagem.upper()
    return "TOO_MANY_REQUESTS" in mensagem or "429" in mensagem


def _montar_url_bling(base_url: str, endpoint: str) -> str:
    endpoint_limpo = str(endpoint or "").strip()
    partes = endpoint_limpo.split("/")
    endpoint_invalido = (
        not endpoint_limpo.startswith("/")
        or "://" in endpoint_limpo
        or "\\" in endpoint_limpo
        or any(parte == ".." for parte in partes)
    )
    if endpoint_invalido:
        raise ValueError("Endpoint Bling invalido")

    return f"{base_url.rstrip('/')}{endpoint_limpo}"


class BlingAPIBase:
    """Base compartilhada do cliente Bling: configuracao, token e request."""

    def __init__(self):
        runtime_config = _load_bling_runtime_config()
        self.base_url = BLING_API_BASE_URL
        self.access_token = runtime_config["access_token"]
        self.refresh_token = runtime_config["refresh_token"]
        self.client_id = runtime_config["client_id"]
        self.client_secret = runtime_config["client_secret"]
        self.enable_jwt = runtime_config["enable_jwt"]
        # Ambiente: 'rascunho', 'homologacao' ou 'producao'
        self.ambiente = runtime_config["ambiente"]

        if not self.access_token:
            raise ValueError("BLING_ACCESS_TOKEN não configurado no .env")

    def _verificar_e_renovar_token(self):
        """
        Verifica se o token está próximo de expirar e renova automaticamente
        Access Token expira em 6 horas
        Refresh Token expira em 60 dias (se não for usado)
        """
        try:
            # Ler arquivo de controle
            if TOKEN_CONTROL_FILE.exists():
                with open(TOKEN_CONTROL_FILE, "r") as f:
                    control_data = json.load(f)

                proxima_renovacao = datetime.fromisoformat(
                    control_data.get("proxima_renovacao", "2020-01-01")
                )

                # Se passou do horário de renovação OU se está perto de expirar (5 horas)
                agora = datetime.now()
                if (
                    agora >= proxima_renovacao
                    or (proxima_renovacao - agora).total_seconds() < 3600
                ):
                    logger.info(
                        "⏰ Token próximo de expirar. Renovando automaticamente..."
                    )
                    self._renovar_token_automatico()
            else:
                # Primeira vez - criar arquivo de controle
                self._salvar_controle_token()

        except Exception as e:
            logger.info(f"⚠️ Erro ao verificar expiração do token: {e}")

    def _salvar_controle_token(self):
        """Salva informações de controle do token"""
        try:
            agora = datetime.now()
            # Access token expira em 6 horas
            proxima_renovacao = agora + timedelta(
                hours=5, minutes=30
            )  # Renova 30 min antes

            control_data = {
                "ultima_renovacao": agora.isoformat(),
                "proxima_renovacao": proxima_renovacao.isoformat(),
                "renovacoes_automaticas": 1,
            }

            # Ler dados existentes se houver
            if TOKEN_CONTROL_FILE.exists():
                with open(TOKEN_CONTROL_FILE, "r") as f:
                    existing_data = json.load(f)
                control_data["renovacoes_automaticas"] = (
                    existing_data.get("renovacoes_automaticas", 0) + 1
                )

            with open(TOKEN_CONTROL_FILE, "w") as f:
                json.dump(control_data, f, indent=2)

            logger.info(
                f"✅ Controle de token atualizado. Próxima renovação: {proxima_renovacao.strftime('%d/%m/%Y %H:%M')}"
            )

        except Exception as e:
            logger.info(f"⚠️ Erro ao salvar controle do token: {e}")

    def _renovar_token_automatico(self):
        """Renova o token automaticamente"""
        try:
            tokens = self.renovar_access_token()
            self.access_token = tokens["access_token"]
            self._salvar_controle_token()
            logger.info("✅ Token renovado com sucesso automaticamente!")
            return True
        except Exception as e:
            logger.info(f"❌ ERRO ao renovar token automaticamente: {e}")
            logger.warning("⚠️ ATENÇÃO: Token do Bling pode estar expirado!")
            logger.info("💡 Solução: Reautentique no Bling via interface do sistema")
            return False

    def _get_headers(self) -> Dict:
        """Retorna headers com autenticação"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "enable-jwt": self.enable_jwt,
        }

    def _deve_renovar_token_apos_erro(
        self, error: requests.exceptions.HTTPError
    ) -> bool:
        response = getattr(error, "response", None)
        if response is None or response.status_code != 401:
            return False

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        error_data = payload.get("error") if isinstance(payload, dict) else {}
        error_type = str((error_data or {}).get("type") or "").strip().lower()
        mensagem = " ".join(
            str(parte or "").strip().lower()
            for parte in (
                error_type,
                (error_data or {}).get("message"),
                (error_data or {}).get("description"),
                getattr(response, "text", ""),
            )
            if str(parte or "").strip()
        )
        return "invalid_token" in mensagem or "unauthorized" in mensagem

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Faz requisição para API do Bling"""
        url = _montar_url_bling(self.base_url, endpoint)
        token_renovado = False

        for tentativa in range(5):
            headers = self._get_headers()

            try:
                _aguardar_slot_bling()

                if method == "GET":
                    response = requests.get(  # NOSONAR - endpoint validado por _montar_url_bling
                        url, headers=headers, params=data, timeout=30
                    )
                elif method == "POST":
                    response = requests.post(  # NOSONAR - endpoint validado por _montar_url_bling
                        url, headers=headers, json=data, timeout=30
                    )
                elif method == "PUT":
                    response = requests.put(  # NOSONAR - endpoint validado por _montar_url_bling
                        url, headers=headers, json=data, timeout=30
                    )
                elif method == "DELETE":
                    response = requests.delete(  # NOSONAR - endpoint validado por _montar_url_bling
                        url, headers=headers, timeout=30
                    )
                else:
                    raise ValueError(f"Método HTTP inválido: {method}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if _erro_rate_limit_bling(e) and tentativa < 4:
                    espera = _tempo_espera_rate_limit_bling(
                        getattr(e, "response", None), tentativa
                    )
                    logger.warning(
                        f"Bling rate limit em {endpoint}. Aguardando {espera:.1f}s antes de repetir ({tentativa + 1}/5).",
                    )
                    time.sleep(espera)
                    continue

                if not token_renovado and self._deve_renovar_token_apos_erro(e):
                    logger.warning(
                        f"Bling retornou token invalido ao consultar {endpoint}. Tentando renovar e repetir."
                    )
                    token_renovado = True
                    if self._renovar_token_automatico():
                        continue

                if _erro_rate_limit_bling(e):
                    raise Exception(
                        "Limite temporario de requisicoes do Bling atingido (HTTP 429). "
                        "Aguarde alguns segundos e tente emitir novamente."
                    )

                error_msg = f"Erro na API Bling: {e}"
                try:
                    error_data = e.response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {e.response.text}"
                raise Exception(error_msg)
            except Exception as e:
                raise Exception(f"Erro ao comunicar com Bling: {str(e)}")

        raise Exception(
            "Erro ao comunicar com Bling: tentativa de renovacao nao retornou resposta valida"
        )

    def validar_conexao(self) -> bool:
        """Testa se a conexão com Bling está funcionando"""
        try:
            # Tenta listar notas (limite 1 para ser rápido)
            self._request("GET", "/nfe", data={"limite": 1})
            return True
        except Exception:
            return False

    def renovar_access_token(self, refresh_token: str = None) -> Dict:
        """
        Renova o access token usando o refresh token

        Args:
            refresh_token: Token de renovação (se None, usa o do .env)

        Returns:
            Dict com novos tokens: {"access_token": "...", "refresh_token": "...", "expires_in": 21600}
        """
        import base64

        refresh = (
            refresh_token
            or self.refresh_token
            or _load_bling_runtime_config().get("refresh_token")
            or ""
        ).strip()
        if not refresh:
            raise ValueError("BLING_REFRESH_TOKEN não configurado")

        # Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
            "enable-jwt": self.enable_jwt,
        }

        data = {"grant_type": "refresh_token", "refresh_token": refresh}

        response = requests.post(
            "https://www.bling.com.br/Api/v3/oauth/token",
            headers=headers,
            data=data,
            timeout=30,
        )

        if response.status_code == 200:
            tokens = response.json()

            # Atualizar token na instância
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]

            # Atualizar .env e variáveis em memória
            try:
                from app.bling_oauth_routes import _salvar_tokens

                _salvar_tokens(tokens["access_token"], tokens["refresh_token"])
            except Exception as e:
                logger.info(f"⚠️ Não foi possível persistir tokens no .env: {e}")

            return tokens
        else:
            raise Exception(
                f"Erro ao renovar token: {response.status_code} - {response.text}"
            )
