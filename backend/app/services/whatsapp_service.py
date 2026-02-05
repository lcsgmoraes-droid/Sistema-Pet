"""
ETAPA 10 - Service genérico de WhatsApp

Abstração para envio de mensagens WhatsApp.
Permite trocar provedor sem refatorar o sistema.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def enviar_whatsapp(telefone: str, mensagem: str) -> bool:
    """
    Envia mensagem via WhatsApp.
    
    TODO: Integrar com API real (WhatsApp Cloud API, Z-API, 360dialog, Twilio, etc.)
    
    Args:
        telefone: Número no formato +55DDNNNNNNNNN
        mensagem: Conteúdo da mensagem
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    # Mock: apenas loga a mensagem
    logger.info(f"[WHATSAPP] Para {telefone}:")
    logger.info(f"{mensagem}")
    logger.info("-" * 60)
    
    # TODO: Implementação real
    # Exemplo com Z-API:
    # response = requests.post(
    #     f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text",
    #     json={"phone": telefone, "message": mensagem}
    # )
    # return response.status_code == 200
    
    return True  # Mock sempre sucesso
