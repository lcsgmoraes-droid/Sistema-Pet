"""
Cliente para integração com a API de Conciliação da Stone
Documentação: https://conciliacao.stone.com.br/reference
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import base64

logger = logging.getLogger(__name__)


class StoneConciliationClient:
    """Cliente para API de Conciliação Stone"""
    
    # URLs da API de Conciliação
    SANDBOX_URL = "https://sandbox-conciliation.stone.com.br"
    PRODUCTION_URL = "https://conciliation.stone.com.br"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = True
    ):
        """
        Inicializa o cliente de Conciliação Stone
        
        Args:
            client_id: ID da aplicação (fornecido pela Stone)
            client_secret: Secret da aplicação (fornecido pela Stone)
            sandbox: Se True, usa ambiente de testes
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
    
    async def request_consent(
        self,
        document: str,
        affiliation_code: str,
        webhook_url: str
    ) -> Dict[str, Any]:
        """
        Solicita consentimento do lojista para acessar dados de conciliação
        
        Args:
            document: CNPJ do lojista (com ou sem formatação)
            affiliation_code: Stone Code do estabelecimento
            webhook_url: URL para receber notificação de aprovação/negação
            
        Returns:
            Dict com status da solicitação
        """
        url = f"{self.base_url}/v2/merchant/consents"
        
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "document": document.replace(".", "").replace("/", "").replace("-", ""),
            "affiliationCode": affiliation_code,
            "webhookUrl": webhook_url
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 201:
                    logger.info(f"Consentimento solicitado com sucesso para {document}")
                    return {
                        "success": True,
                        "message": "Consentimento solicitado. Aguarde aprovação do lojista via email.",
                        "status_code": 201
                    }
                else:
                    logger.error(f"Erro ao solicitar consentimento: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "message": f"Erro ao solicitar consentimento: {response.text}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Exceção ao solicitar consentimento: {str(e)}")
            return {
                "success": False,
                "message": f"Erro ao conectar com Stone: {str(e)}"
            }
    
    def set_credentials(self, username: str, password: str):
        """
        Define as credenciais recebidas via webhook após aprovação
        
        Args:
            username: Username fornecido pela Stone
            password: Password fornecido pela Stone
        """
        self.username = username
        self.password = password
        # Limpa token anterior
        self.access_token = None
        self.token_expires_at = None
        logger.info("Credenciais Stone atualizadas")
    
    async def _get_access_token(self) -> str:
        """
        Obtém access token usando username/password
        Token usa AES CBC PKCS5 (username + senha)
        """
        if not self.username or not self.password:
            raise Exception("Credenciais não configuradas. Solicite consentimento primeiro.")
        
        # Verifica se já tem token válido
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return self.access_token
        
        # Gera token usando Basic Auth
        credentials = f"{self.username}:{self.password}"
        credentials_b64 = base64.b64encode(credentials.encode()).decode()
        
        url = f"{self.base_url}/api/token"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Basic {credentials_b64}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Erro ao obter token Stone: {response.text}")
                raise Exception(f"Falha na autenticação Stone: {response.status_code}")
            
            data = response.json()
            self.access_token = data.get("access_token") or data.get("token")
            
            # Token válido por 24 horas
            expires_in = data.get("expires_in", 86400)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            
            logger.info("Token Stone obtido com sucesso")
            return self.access_token
    
    async def get_statement(
        self,
        stone_code: str,
        start_date: str,
        end_date: str,
        file_type: str = "json"
    ) -> Dict[str, Any]:
        """
        Busca extrato de transações Stone
        
        Args:
            stone_code: Código Stone do estabelecimento
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            file_type: Tipo do arquivo (json, csv, xml)
            
        Returns:
            Dict com dados do extrato ou arquivo
        """
        token = await self._get_access_token()
        
        url = f"{self.base_url}/api/v2/statement/{stone_code}"
        
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "fileType": file_type
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 200:
                    if file_type == "json":
                        return response.json()
                    else:
                        return {
                            "success": True,
                            "content": response.text,
                            "content_type": response.headers.get("content-type")
                        }
                else:
                    logger.error(f"Erro ao buscar extrato: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Erro ao buscar extrato: {response.text}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Exceção ao buscar extrato: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao conectar com Stone: {str(e)}"
            }
    
    async def get_transactions(
        self,
        stone_code: str,
        start_date: str,
        end_date: str
    ) -> list:
        """
        Busca e parseia transações do extrato Stone
        
        Returns:
            Lista de transações formatadas
        """
        statement = await self.get_statement(stone_code, start_date, end_date, "json")
        
        if not statement.get("success", True):
            return []
        
        # Parse das transações conforme layout Stone
        transactions = []
        
        # O formato exato depende do layout da Stone (2.2 ou 2.4)
        # Exemplo genérico:
        if "data" in statement:
            for item in statement.get("data", []):
                transactions.append({
                    "stone_id": item.get("stoneId"),
                    "nsu": item.get("nsu"),
                    "rrn": item.get("rrn"),
                    "authorization_code": item.get("authorizationCode"),
                    "amount": Decimal(str(item.get("amount", 0))) / 100,  # Centavos para reais
                    "net_amount": Decimal(str(item.get("netAmount", 0))) / 100,
                    "date": item.get("captureDate") or item.get("transactionDate"),
                    "brand": item.get("brand"),
                    "card_number": item.get("cardNumber"),
                    "installments": item.get("installments", 1),
                    "status": item.get("status")
                })
        
        return transactions
