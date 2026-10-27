"""Cliente da API oficial do WhatsApp (Meta Cloud API) e traducao dos erros dela.

Cada loja usa o seu proprio numero e a sua propria conta do WhatsApp Business
(WABA) na Meta. O sistema guarda o token de acesso e o ID do numero, envia as
mensagens e recebe as respostas pelo webhook da loja.

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
A versao da API vem de `META_GRAPH_API_VERSION` (a Meta aposenta versoes antigas).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.utils.correlation import current_correlation_id

VERSAO_PADRAO_DA_API = "v26.0"
CAMPOS_DO_NUMERO = (
    "display_phone_number,verified_name,quality_rating,code_verification_status,"
    "platform_type,name_status"
)


def versao_da_api() -> str:
    return os.getenv("META_GRAPH_API_VERSION", "").strip() or VERSAO_PADRAO_DA_API


class MetaCloudError(Exception):
    """Falha ao falar com a Meta, ja com uma mensagem que a loja entende."""

    def __init__(
        self, mensagem: str, codigo: int | None = None, passo: str | None = None
    ):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        # Em qual passo do guia o problema costuma estar (ver pagina de apoio).
        self.passo = passo


def traduzir_erro_da_meta(status_http: int, corpo: Any) -> MetaCloudError:
    """Transforma a resposta de erro da Graph API em uma orientacao clara."""
    erro = (corpo or {}).get("error", {}) if isinstance(corpo, dict) else {}
    codigo = erro.get("code")
    texto = str(erro.get("message") or "")
    if codigo == 190 or status_http == 401:
        return MetaCloudError(
            "O token de acesso é inválido ou expirou. Gere um novo token permanente "
            "do usuário do sistema e cole aqui.",
            codigo,
            "token",
        )
    if codigo in (10, 200, 283) or status_http == 403:
        return MetaCloudError(
            "O token não tem permissão para esta conta do WhatsApp. Confira se o usuário "
            "do sistema recebeu a conta do WhatsApp e as permissões "
            "whatsapp_business_messaging e whatsapp_business_management.",
            codigo,
            "token",
        )
    if codigo == 100 or status_http == 404:
        return MetaCloudError(
            "A Meta não encontrou esse ID. Confira o ID do número de telefone e o ID da "
            "conta do WhatsApp (copie na tela de configuração da API do seu app).",
            codigo,
            "ids",
        )
    if codigo in (4, 17, 80007, 130429) or status_http == 429:
        return MetaCloudError(
            "A Meta limitou as consultas por alguns minutos. Tente de novo daqui a pouco.",
            codigo,
            None,
        )
    detalhe = f" ({texto})" if texto else ""
    return MetaCloudError(
        f"A Meta recusou a consulta{detalhe}. Confira os dados e tente de novo.",
        codigo,
        None,
    )


class MetaCloudClient:
    """Envio de mensagens e consultas na conta do WhatsApp de uma loja."""

    def __init__(
        self, access_token: str, phone_number_id: str, waba_id: str | None = None
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.waba_id = waba_id

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{versao_da_api()}"

    def _headers(self, referencia: str | None = None) -> dict[str, str]:
        correlacao = current_correlation_id(
            "integration.whatsapp.meta_cloud", reference=referencia
        )
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Correlation-ID": correlacao,
        }

    async def _pedir(
        self,
        metodo: str,
        caminho: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resposta = await http.request(
                    metodo,
                    f"{self.base_url}/{caminho}",
                    headers=self._headers(caminho),
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as erro:
            raise MetaCloudError(
                "Não foi possível falar com a Meta agora. Verifique a conexão do servidor "
                "e tente de novo."
            ) from erro
        try:
            corpo = resposta.json()
        except ValueError:
            corpo = {}
        if resposta.status_code >= 400:
            raise traduzir_erro_da_meta(resposta.status_code, corpo)
        return corpo

    # --- envio (mesma interface do cliente do 360dialog) -------------------

    async def _enviar(self, payload: dict, destino: str) -> dict[str, Any]:
        corpo = {"messaging_product": "whatsapp", "recipient_type": "individual"}
        corpo.update(payload)
        corpo["to"] = destino
        return await self._pedir("POST", f"{self.phone_number_id}/messages", json=corpo)

    async def send_text_message(self, to: str, message: str) -> dict[str, Any]:
        return await self._enviar({"type": "text", "text": {"body": message}}, to)

    async def send_image_message(
        self, to: str, image_url: str, caption: str | None = None
    ) -> dict[str, Any]:
        imagem: dict[str, Any] = {"link": image_url}
        if caption:
            imagem["caption"] = caption[:1024]
        return await self._enviar({"type": "image", "image": imagem}, to)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        parameters: list | None = None,
    ) -> dict[str, Any]:
        modelo: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if parameters:
            modelo["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in parameters
                    ],
                }
            ]
        return await self._enviar({"type": "template", "template": modelo}, to)

    # --- consultas usadas pelo guia de conexao -----------------------------

    async def consultar_numero(self) -> dict[str, Any]:
        """Dados do numero: nome verificado, qualidade, estado do codigo."""
        return await self._pedir(
            "GET", self.phone_number_id, params={"fields": CAMPOS_DO_NUMERO}
        )

    async def consultar_conta(self) -> dict[str, Any]:
        if not self.waba_id:
            raise MetaCloudError(
                "Informe o ID da conta do WhatsApp (WABA).", None, "ids"
            )
        return await self._pedir("GET", self.waba_id, params={"fields": "name"})

    async def apps_inscritos(self) -> list[dict[str, Any]]:
        """Apps que recebem os eventos desta conta (sem isso o webhook nao chega)."""
        if not self.waba_id:
            return []
        corpo = await self._pedir("GET", f"{self.waba_id}/subscribed_apps")
        return list(corpo.get("data") or [])

    async def inscrever_app(self) -> dict[str, Any]:
        """Faz o app receber os eventos da conta (equivale a assinar o webhook)."""
        if not self.waba_id:
            raise MetaCloudError(
                "Informe o ID da conta do WhatsApp (WABA).", None, "ids"
            )
        return await self._pedir("POST", f"{self.waba_id}/subscribed_apps")
