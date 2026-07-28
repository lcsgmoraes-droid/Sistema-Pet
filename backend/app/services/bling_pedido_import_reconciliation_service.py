from __future__ import annotations

import os
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.pedido_integrado_models import PedidoIntegrado
from app.services.pedido_integrado_consolidation_service import (
    localizar_pedido_por_bling_id,
)
from app.tenancy.context import tenant_context
from app.utils.logger import logger


def _tenant_bling_configurado() -> UUID | None:
    raw = str(os.getenv("BLING_WEBHOOK_TENANT_ID") or "").strip()
    try:
        return UUID(raw) if raw else None
    except ValueError:
        return None


def _itens_resposta_bling(resposta: dict | None) -> list[dict]:
    data = (resposta or {}).get("data") if isinstance(resposta, dict) else None
    return [item for item in (data or []) if isinstance(item, dict)]


def reconciliar_importacao_pedidos_bling_recentes(
    db: Session,
    *,
    dias: int = 7,
    limite_paginas: int = 5,
    limite_por_pagina: int = 100,
) -> dict:
    """
    Reimporta pedidos alterados no Bling quando o webhook nao chegou.

    O processamento reaproveita o mesmo fluxo idempotente dos webhooks para
    manter reserva, NF e estoque com uma unica regra.
    """
    from app.bling_integration import BlingAPI
    from app.integracao_bling_pedido_routes import (
        _SITUACOES_PEDIDO_ATENDIDO,
        _SITUACOES_PEDIDO_CANCELADO,
        _situacao_codigo_bling,
        processar_pedido_bling_payload,
    )

    tenant_id = _tenant_bling_configurado()
    if not tenant_id:
        return {
            "success": False,
            "executada": False,
            "motivo": "bling_webhook_tenant_nao_configurado",
        }

    dias = max(min(int(dias or 1), 30), 1)
    limite_paginas = max(min(int(limite_paginas or 1), 20), 1)
    limite_por_pagina = max(min(int(limite_por_pagina or 1), 100), 1)
    agora = datetime.utcnow()
    data_inicial = (agora - timedelta(days=dias)).date().isoformat()
    data_final = (agora + timedelta(days=1)).date().isoformat()

    api = BlingAPI()
    avaliados = 0
    importados = 0
    atualizados = 0
    ignorados = 0
    erros: list[dict] = []

    with tenant_context(tenant_id):
        for pagina in range(1, limite_paginas + 1):
            resposta = api.listar_pedidos_vendas(
                data_alteracao_inicial=data_inicial,
                data_alteracao_final=data_final,
                pagina=pagina,
                limite=limite_por_pagina,
            )
            pedidos = _itens_resposta_bling(resposta)
            if not pedidos:
                break

            for resumo in pedidos:
                pedido_bling_id = str(resumo.get("id") or "").strip()
                if not pedido_bling_id:
                    continue
                avaliados += 1

                existente: PedidoIntegrado | None = localizar_pedido_por_bling_id(
                    db,
                    tenant_id=tenant_id,
                    pedido_bling_id=pedido_bling_id,
                    resolver_mescla=False,
                )
                situacao_id = _situacao_codigo_bling(resumo.get("situacao"))
                status_ja_conciliado = bool(
                    existente
                    and (
                        (
                            situacao_id in _SITUACOES_PEDIDO_ATENDIDO
                            and existente.status == "confirmado"
                        )
                        or (
                            situacao_id is not None
                            and situacao_id
                            not in (
                                _SITUACOES_PEDIDO_CANCELADO | _SITUACOES_PEDIDO_ATENDIDO
                            )
                            and existente.status == "aberto"
                        )
                    )
                )
                if status_ja_conciliado:
                    ignorados += 1
                    continue

                evento = "order.updated" if existente else "order.created"
                try:
                    resultado = processar_pedido_bling_payload(
                        {
                            "event": evento,
                            "date": agora.isoformat(),
                            "data": resumo,
                        },
                        db,
                    )
                    if resultado.get("status") == "erro":
                        erros.append(
                            {
                                "pedido_bling_id": pedido_bling_id,
                                "erro": resultado.get("motivo") or "erro_sem_detalhe",
                            }
                        )
                    elif existente:
                        atualizados += 1
                    else:
                        importados += 1
                except Exception as exc:
                    db.rollback()
                    logger.warning(
                        "[BLING PEDIDO IMPORT] Falha ao reconciliar pedido %s: %s",
                        pedido_bling_id,
                        exc,
                    )
                    erros.append(
                        {
                            "pedido_bling_id": pedido_bling_id,
                            "erro": str(exc),
                        }
                    )

            if len(pedidos) < limite_por_pagina:
                break

    return {
        "success": not erros,
        "executada": True,
        "tenant_id": str(tenant_id),
        "data_inicial": data_inicial,
        "data_final": data_final,
        "avaliados": avaliados,
        "importados": importados,
        "atualizados": atualizados,
        "ignorados": ignorados,
        "erros": erros,
    }
