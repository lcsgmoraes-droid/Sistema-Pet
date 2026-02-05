"""
Cliente para integração com a API da Stone (Ton)
Documentação: https://docs.stone.com.br/

A Stone oferece APIs para:
- Pagamentos via PIX
- Pagamentos via Cartão (débito/crédito)
- Consulta de transações
- Webhooks para notificações
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class StoneAPIClient:
    """Cliente para integração com a API da Stone"""
    
    # URLs da API
    SANDBOX_URL = "https://payments.stone.com.br"
    PRODUCTION_URL = "https://payments.stone.com.br"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        merchant_id: str,
        sandbox: bool = True
    ):
        """
        Inicializa o cliente Stone
        
        Args:
            client_id: ID da aplicação Stone
            client_secret: Secret da aplicação Stone
            merchant_id: ID do estabelecimento (merchant)
            sandbox: Se True, usa ambiente de testes
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.merchant_id = merchant_id
        self.base_url = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def _get_access_token(self) -> str:
        """
        Obtém access token OAuth2
        Stone usa OAuth2 Client Credentials flow
        """
        # Verifica se já tem token válido
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return self.access_token
        
        # Solicita novo token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Erro ao obter token Stone: {response.text}")
                raise Exception(f"Falha na autenticação Stone: {response.status_code}")
            
            data = response.json()
            self.access_token = data["access_token"]
            
            # Token geralmente expira em 3600 segundos (1 hora)
            expires_in = data.get("expires_in", 3600)
            from datetime import timedelta
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            
            logger.info("Token Stone obtido com sucesso")
            return self.access_token
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[Any, Any]:
        """Faz requisição autenticada para a API Stone"""
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Método HTTP inválido: {method}")
            
            # Log para debug
            logger.info(f"Stone API {method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"Erro Stone API: {response.text}")
                response.raise_for_status()
            
            return response.json()
    
    # ==========================================
    # PAGAMENTOS PIX
    # ==========================================
    
    async def criar_pagamento_pix(
        self,
        amount: Decimal,
        description: str,
        external_id: str,
        customer_name: Optional[str] = None,
        customer_document: Optional[str] = None,
        customer_email: Optional[str] = None,
        expiration_minutes: int = 30
    ) -> Dict[Any, Any]:
        """
        Cria um pagamento via PIX
        
        Args:
            amount: Valor em reais (ex: 100.50)
            description: Descrição do pagamento
            external_id: ID único do seu sistema (evita duplicação)
            customer_name: Nome do cliente
            customer_document: CPF/CNPJ do cliente
            customer_email: Email do cliente
            expiration_minutes: Tempo para expirar o QR Code
            
        Returns:
            Dict com dados do pagamento incluindo QR Code
        """
        # Converte para centavos (Stone trabalha com centavos)
        amount_cents = int(amount * 100)
        
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_cents,
            "description": description,
            "external_id": external_id,
            "payment_method": "pix",
            "expiration_time": expiration_minutes
        }
        
        # Adiciona dados do cliente se fornecidos
        if customer_name or customer_document or customer_email:
            payload["customer"] = {}
            if customer_name:
                payload["customer"]["name"] = customer_name
            if customer_document:
                payload["customer"]["document"] = customer_document
            if customer_email:
                payload["customer"]["email"] = customer_email
        
        result = await self._make_request("POST", "/v1/payments", data=payload)
        
        logger.info(f"Pagamento PIX criado: {result.get('id')} - R$ {amount}")
        return result
    
    # ==========================================
    # PAGAMENTOS CARTÃO
    # ==========================================
    
    async def criar_pagamento_cartao(
        self,
        amount: Decimal,
        description: str,
        external_id: str,
        card_number: str,
        card_holder_name: str,
        card_expiration_date: str,  # MM/YY
        card_cvv: str,
        installments: int = 1,
        customer_name: Optional[str] = None,
        customer_document: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Cria um pagamento via cartão de crédito/débito
        
        Args:
            amount: Valor em reais
            description: Descrição do pagamento
            external_id: ID único do seu sistema
            card_number: Número do cartão (16 dígitos)
            card_holder_name: Nome impresso no cartão
            card_expiration_date: Data de expiração no formato MM/YY
            card_cvv: Código de segurança (3 ou 4 dígitos)
            installments: Número de parcelas (1 a 12)
            customer_name: Nome do cliente
            customer_document: CPF/CNPJ
            customer_email: Email
            
        Returns:
            Dict com dados da transação
        """
        amount_cents = int(amount * 100)
        
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_cents,
            "description": description,
            "external_id": external_id,
            "payment_method": "credit_card",
            "installments": installments,
            "card": {
                "number": card_number,
                "holder_name": card_holder_name,
                "expiration_date": card_expiration_date,
                "cvv": card_cvv
            }
        }
        
        # Adiciona dados do cliente
        if customer_name or customer_document or customer_email:
            payload["customer"] = {}
            if customer_name:
                payload["customer"]["name"] = customer_name
            if customer_document:
                payload["customer"]["document"] = customer_document
            if customer_email:
                payload["customer"]["email"] = customer_email
        
        result = await self._make_request("POST", "/v1/payments", data=payload)
        
        logger.info(f"Pagamento Cartão criado: {result.get('id')} - R$ {amount}")
        return result
    
    # ==========================================
    # CONSULTAS
    # ==========================================
    
    async def consultar_pagamento(self, payment_id: str) -> Dict[Any, Any]:
        """
        Consulta status de um pagamento
        
        Args:
            payment_id: ID do pagamento retornado pela Stone
            
        Returns:
            Dict com dados atualizados do pagamento
        """
        result = await self._make_request(
            "GET",
            f"/v1/payments/{payment_id}"
        )
        return result
    
    async def listar_pagamentos(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[Any, Any]]:
        """
        Lista pagamentos com filtros
        
        Args:
            start_date: Data inicial (formato: YYYY-MM-DD)
            end_date: Data final (formato: YYYY-MM-DD)
            status: Filtrar por status (pending, approved, cancelled, etc)
            limit: Quantidade de registros por página
            offset: Offset para paginação
            
        Returns:
            Lista de pagamentos
        """
        params = {
            "merchant_id": self.merchant_id,
            "limit": limit,
            "offset": offset
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if status:
            params["status"] = status
        
        result = await self._make_request(
            "GET",
            "/v1/payments",
            params=params
        )
        
        return result.get("payments", [])
    
    # ==========================================
    # CANCELAMENTOS E ESTORNOS
    # ==========================================
    
    async def cancelar_pagamento(
        self,
        payment_id: str,
        reason: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Cancela um pagamento pendente ou estorna um pagamento aprovado
        
        Args:
            payment_id: ID do pagamento
            reason: Motivo do cancelamento
            
        Returns:
            Dict com confirmação do cancelamento
        """
        payload = {}
        if reason:
            payload["reason"] = reason
        
        result = await self._make_request(
            "POST",
            f"/v1/payments/{payment_id}/cancel",
            data=payload
        )
        
        logger.info(f"Pagamento cancelado: {payment_id}")
        return result
    
    async def estornar_pagamento(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Estorna um pagamento (total ou parcial)
        
        Args:
            payment_id: ID do pagamento
            amount: Valor a estornar (None = estorno total)
            reason: Motivo do estorno
            
        Returns:
            Dict com confirmação do estorno
        """
        payload = {}
        
        if amount:
            payload["amount"] = int(amount * 100)  # Converte para centavos
        
        if reason:
            payload["reason"] = reason
        
        result = await self._make_request(
            "POST",
            f"/v1/payments/{payment_id}/refund",
            data=payload
        )
        
        logger.info(f"Pagamento estornado: {payment_id} - Valor: {amount or 'Total'}")
        return result
    
    # ==========================================
    # WEBHOOKS
    # ==========================================
    
    def validar_webhook_signature(
        self,
        payload: str,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Valida a assinatura de um webhook recebido da Stone
        
        Args:
            payload: Corpo da requisição (raw string)
            signature: Header X-Stone-Signature
            webhook_secret: Secret configurado no dashboard Stone
            
        Returns:
            True se a assinatura é válida
        """
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def processar_webhook(self, webhook_data: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Processa dados de um webhook recebido
        
        Args:
            webhook_data: Dados do webhook
            
        Returns:
            Dados processados
        """
        event_type = webhook_data.get("event")
        payment_data = webhook_data.get("payment", {})
        
        logger.info(f"Webhook Stone recebido: {event_type} - Payment ID: {payment_data.get('id')}")
        
        # Retorna os dados processados
        return {
            "event_type": event_type,
            "payment_id": payment_data.get("id"),
            "status": payment_data.get("status"),
            "amount": payment_data.get("amount", 0) / 100,  # Centavos para reais
            "processed_at": datetime.utcnow().isoformat()
        }
