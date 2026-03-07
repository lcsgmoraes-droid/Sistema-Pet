"""
Cliente para integração com a API de Conciliação da Stone.
Documentação: https://conciliacao.stone.com.br/reference

Fluxo de integração (Cliente Stone — programa API Conciliação):
  1. Solicitar consentimento → POST /v2/merchant/consents
  2. Stone envia e-mail ao lojista para aprovar
  3. Quando aprovado, Stone envia webhook para webhookUrl com username + senha criptografada
  4. Decriptar senha (AES-256-CBC, chave = client_secret[:32])
  5. Usar username + senha descriptografada para obter token de acesso
  6. Com o token, buscar arquivo de conciliação (XML) → GET /v2/merchant/{affiliationCode}/conciliation-file/{referenceDate}

Nota: Não há sandbox — a API usa produção diretamente.
"""

import httpx
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class StoneConciliationClient:
    """
    Cliente para a API de Conciliação Stone (conciliation.stone.com.br).
    As credenciais (client_id / client_secret) são as fornecidas pela Stone
    no programa API Conciliação.
    """

    BASE_URL = "https://conciliation.stone.com.br"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
    ):
        """
        Inicializa o cliente de Conciliação Stone.

        Args:
            client_id: Client ID fornecido pela Stone no programa API Conciliação.
            client_secret: Client Secret correspondente.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        # Preenchidos quando o consentimento é aceito (via webhook)
        self.conciliation_username: Optional[str] = None
        self.conciliation_password: Optional[str] = None  # senha já descriptografada

    # ---------------------------------------------------------------------------
    # Consentimento
    # ---------------------------------------------------------------------------

    async def solicitar_consentimento(
        self,
        documento: str,
        affiliation_code: str,
        webhook_url: str,
    ) -> Dict[str, Any]:
        """
        Passo 1 — Solicita consentimento do lojista para acessar dados de conciliação.
        A Stone envia um e-mail ao lojista (documento/CNPJ) para aprovação.
        Quando aprovado, a Stone faz POST na webhook_url com username + senha criptografada.

        Args:
            documento: CNPJ do lojista (com ou sem formatação).
            affiliation_code: Stone Code do estabelecimento (código de afiliação).
            webhook_url: URL pública deste sistema para receber a resposta do consentimento.
        """
        url = f"{self.BASE_URL}/v2/merchant/consents"
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "document": documento.replace(".", "").replace("/", "").replace("-", ""),
            "affiliationCode": affiliation_code,
            "webhookUrl": webhook_url,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
            if response.status_code == 201:
                logger.info(f"Consentimento solicitado para {documento}")
                return {"success": True, "message": "Consentimento solicitado. Aguarde aprovação do lojista via e-mail."}
            logger.error(f"Erro ao solicitar consentimento: {response.status_code} — {response.text}")
            return {"success": False, "message": response.text, "status_code": response.status_code}
        except Exception as exc:
            logger.error(f"Exceção ao solicitar consentimento: {exc}")
            return {"success": False, "message": str(exc)}

    # ---------------------------------------------------------------------------
    # Credenciais recebidas via webhook após consentimento aceito
    # ---------------------------------------------------------------------------

    @staticmethod
    def decriptar_senha(senha_enc_b64: str, client_secret: str) -> str:
        """
        Descriptografa a senha recebida no webhook de resposta de consentimento.
        A Stone criptografa com AES-256-CBC; a chave é client_secret[:32] (padded/truncated).

        Args:
            senha_enc_b64: Senha criptografada em Base64 (campo 'password' do webhook).
            client_secret: Client Secret desta aplicação.

        Returns:
            Senha em texto plano.
        """
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        chave = client_secret[:32].ljust(32, '\x00').encode('utf-8')
        dados = base64.b64decode(senha_enc_b64)
        # IV ocupa os primeiros 16 bytes
        iv = dados[:16]
        ciphertext = dados[16:]
        cipher = AES.new(chave, AES.MODE_CBC, iv)
        senha_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return senha_bytes.decode('utf-8')

    def definir_credenciais_consentimento(self, username: str, password_plain: str) -> None:
        """
        Armazena as credenciais recebidas após o consentimento ser aceito.
        Chamar este método após descriptografar a senha do webhook.
        """
        self.conciliation_username = username
        self.conciliation_password = password_plain
        self.access_token = None
        self.token_expires_at = None
        logger.info("Credenciais de conciliação atualizadas.")

    # ---------------------------------------------------------------------------
    # Token de acesso
    # ---------------------------------------------------------------------------

    async def _obter_token(self) -> str:
        """
        Obtém (ou reutiliza) o token de acesso usando username + senha via Basic Auth.
        Endpoint exato a ser confirmado com a Stone via suporte — usando /v2/token como estimativa.
        """
        if not self.conciliation_username or not self.conciliation_password:
            raise RuntimeError("Credenciais de conciliação não configuradas. Solicite o consentimento primeiro.")

        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token

        credentials = base64.b64encode(
            f"{self.conciliation_username}:{self.conciliation_password}".encode()
        ).decode()

        # NOTA: o endpoint exato de geração de token deve ser confirmado com a Stone.
        url = f"{self.BASE_URL}/v2/token"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Basic {credentials}"},
            )

        if response.status_code != 200:
            raise RuntimeError(f"Falha ao obter token Stone Conciliação: {response.status_code} — {response.text[:200]}")

        data = response.json()
        self.access_token = data.get("access_token") or data.get("token")
        expires_in = data.get("expires_in", 86400)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
        logger.info("Token Stone Conciliação obtido.")
        return self.access_token

    # ---------------------------------------------------------------------------
    # Extrato de Conciliação
    # ---------------------------------------------------------------------------

    async def obter_extrato(
        self,
        affiliation_code: str,
        reference_date: str,
        layout: str = "XML2_4",
    ) -> Dict[str, Any]:
        """
        Busca o arquivo de conciliação (XML) de um dia específico.

        Args:
            affiliation_code: Stone Code do estabelecimento (affiliationCode).
            reference_date: Data no formato YYYY-MM-DD. Só disponível D-1 (ontem).
            layout: 'XML2_2' ou 'XML2_4' (padrão: XML2_4 — mais completo).

        Returns:
            Dict com 'content' (XML em texto) ou 'error'.
        """
        token = await self._obter_token()
        url = f"{self.BASE_URL}/v2/merchant/{affiliation_code}/conciliation-file/{reference_date}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept-Encoding": "gzip",
            "x-user-type": "client",
        }
        params = {"layout": layout}
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                logger.info(f"Extrato Stone obtido: {affiliation_code} {reference_date}")
                return {"success": True, "content": response.text, "layout": layout}
            logger.error(f"Erro ao buscar extrato: {response.status_code} — {response.text[:200]}")
            return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as exc:
            logger.error(f"Exceção ao buscar extrato: {exc}")
            return {"success": False, "error": str(exc)}
