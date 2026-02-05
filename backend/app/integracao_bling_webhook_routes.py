
from fastapi import APIRouter, Request
import json
import logging

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - Webhook"]
)

logger = logging.getLogger("bling_webhook")

@router.post("/webhook")
async def receber_webhook_bling(request: Request):
    payload = await request.json()

    logger.info("🔔 Webhook Bling recebido")
    logger.info(json.dumps(payload, indent=2, ensure_ascii=False))

    # ⚠️ IMPORTANTE:
    # Neste passo NÃO processamos nada.
    # Apenas confirmamos que o Bling consegue falar com o sistema.

    return {"status": "ok"}
