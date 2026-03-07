"""
Cliente para integração com Stone Connect via API Pagar.me
Documentação: https://connect-stone.stone.com.br/reference/

Stone Connect usa a API do Pagar.me com:
- Autenticação Basic Auth: base64(sk_*:)  (senha vazia)
- Header obrigatório: ServiceRefererName
- Base URL: https://api.pagar.me/core/v5/
- Split OBRIGATÓRIO em todos os pedidos desde fevereiro/2026
"""

import httpx
import base64
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class PagarmeConnectClient:
    """
    Cliente para Stone Connect via API Pagar.me.
    Usado para criar pedidos em terminais POS (maquininhas Stone).
    """

    BASE_URL = "https://api.pagar.me/core/v5"
    SERVICE_REFERER_NAME = "698babbf7ef14a04992e3e0a"

    def __init__(self, secret_key: str):
        """
        Args:
            secret_key: Chave secreta do Pagar.me (formato sk_*).
                        Obtida em https://id.pagar.me/ → Desenvolvimento → Chaves
        """
        self.secret_key = secret_key

    def _headers(self) -> Dict[str, str]:
        """Monta os headers de autenticação. Senha é sempre vazia."""
        credentials = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "ServiceRefererName": self.SERVICE_REFERER_NAME,
        }

    # ---------------------------------------------------------------------------
    # Alias para manter compatibilidade com código que usava StoneAPIClient
    # ---------------------------------------------------------------------------

    @classmethod
    def from_legacy_config(cls, client_id: str, client_secret: str, merchant_id: str, sandbox: bool = False) -> "PagarmeConnectClient":
        """Cria instância usando a secret_key armazenada no campo client_id do StoneConfig."""
        return cls(secret_key=client_id)

    # ---------------------------------------------------------------------------
    # Requisições HTTP
    # ---------------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=json,
                params=params,
            )
        logger.info(f"Pagar.me {method} {path} → {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"Pagar.me erro: {response.text[:500]}")
            response.raise_for_status()
        return response.json()

    # ---------------------------------------------------------------------------
    # Pedidos POS (maquininha)
    # ---------------------------------------------------------------------------

    async def criar_pedido_pos(
        self,
        items: List[Dict],
        customer: Dict,
        serial_number: str,
        split_rules: Optional[List[Dict]] = None,
        payment_setup: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Cria um pedido para ser pago na maquininha (POS).

        Parâmetros
        ----------
        items : lista de {"amount": int_centavos, "description": str, "quantity": int, "code": str}
        customer : {"name": str, "email": str, "type": "individual", "document": str}
        serial_number : número de série da maquininha (terminal_serial_number)
        split_rules : lista de splits — OBRIGATÓRIO desde fev/2026 se o account tiver subcontas.
            Formato: {"amount": int, "recipient_id": "rp_XXX", "type": "flat",
                      "options": {"liable": true, "charge_remainder_fee": true, "charge_processing_fee": true}}
        payment_setup : (fluxo Pagamento Direto) define a forma de pagamento na criação.
            Se omitido, usa fluxo Listagem (cliente escolhe na maquininha).
        """
        body: Dict[str, Any] = {
            "closed": False,
            "items": items,
            "customer": customer,
            "poi_payment_settings": {
                "terminal_serial_number": serial_number,
            },
        }
        if payment_setup:
            body["poi_payment_settings"]["payment_setup"] = payment_setup
        if split_rules:
            body["payment_setup"] = {"split": split_rules}
        if metadata:
            body["metadata"] = metadata

        result = await self._request("POST", "/orders", json=body)
        logger.info(f"Pedido POS criado: {result.get('id')}")
        return result

    async def obter_pedido(self, order_id: str) -> Dict[str, Any]:
        """Consulta status atualizado de um pedido."""
        return await self._request("GET", f"/orders/{order_id}")

    async def cancelar_pedido(self, order_id: str) -> Dict[str, Any]:
        """Cancela um pedido aberto."""
        return await self._request("DELETE", f"/orders/{order_id}")

    # ---------------------------------------------------------------------------
    # Webhook
    # ---------------------------------------------------------------------------

    @staticmethod
    def validar_webhook_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
        """
        Valida o header X-Hub-Signature do webhook Pagar.me (HMAC-SHA256).
        A Stone envia `sha256=<hex>` no header.
        """
        import hmac
        import hashlib
        expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Alias de compatibilidade — código antigo referenciava StoneAPIClient
# ---------------------------------------------------------------------------
StoneAPIClient = PagarmeConnectClient
