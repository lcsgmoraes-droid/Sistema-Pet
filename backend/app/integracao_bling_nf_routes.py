
import os
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy import not_, exists, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.services.bling_nf_service import processar_nf_autorizada, processar_nf_cancelada
from app.services.provisao_simples_service import gerar_provisao_simples_por_nf
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - NF"]
)

# Situações de NF no Bling (campo situacao é um número)
# 1=Pendente, 2=Emitida, 4=Cancelada, 5=Denegada, 9=Autorizado pelo SEFAZ
_NF_SITUACAO_AUTORIZADA = {2, 9}   # emitida ou autorizada
_NF_SITUACAO_CANCELADA  = {4, 5}   # cancelada ou denegada


def _obter_pedido_bling_id_por_nf(nf_id: str, situacao_num: int) -> str | None:
    pedido_bling_id = None

    try:
        from app.bling_integration import BlingAPI

        nf_completa = BlingAPI().consultar_nfe(int(nf_id))
        pedido_ref = (
            nf_completa.get("pedido")
            or nf_completa.get("pedidoCompra")
            or nf_completa.get("pedidoVenda")
        )
        if isinstance(pedido_ref, dict):
            pedido_bling_id = str(pedido_ref.get("id", ""))
        logger.info(f"[BLING NF] NF {nf_id} situacao={situacao_num} pedido_bling={pedido_bling_id}")
    except Exception as e:
        logger.warning(f"[BLING NF] Falha ao buscar NF {nf_id} na API: {e}")

    return pedido_bling_id or None


def _gerar_provisao_simples_se_aplicavel(db: Session, pedido: PedidoIntegrado, data: dict) -> None:
    try:
        valor_total_nf = data.get("valorTotalNf") or data.get("valor_total", 0)
        data_emissao = data.get("dataEmissao") or data.get("data_emissao")

        if not valor_total_nf or not data_emissao or not pedido.tenant_id:
            return

        if isinstance(data_emissao, str):
            from datetime import date

            data_emissao = date.fromisoformat(data_emissao.split("T")[0])

        resultado = gerar_provisao_simples_por_nf(
            db=db,
            tenant_id=pedido.tenant_id,
            valor_nf=Decimal(str(valor_total_nf)),
            data_emissao=data_emissao,
            usuario_id=pedido.usuario_id if hasattr(pedido, "usuario_id") else None,
        )

        if resultado.get("sucesso"):
            logger.info(
                f"✅ Provisão Simples: R$ {resultado['valor_provisao']:.2f} "
                f"(Período {resultado['mes']}/{resultado['ano']})"
            )
    except Exception as e:
        logger.info(f"⚠️  Erro ao gerar provisão Simples Nacional: {e}")
        import traceback

        traceback.print_exc()


@router.post("/nf")
async def receber_nf_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de NF-e e NF-e de consumidor do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'invoice.created'|'invoice.updated', data: {...} }
    O campo data.situacao é um NÚMERO: 2=Emitida, 9=Autorizada, 4=Cancelada.
    O payload do webhook NÃO inclui o pedido vinculado — precisa chamar a API.
    """
    body = await request.json()

    # Injetar tenant no contexto (webhook chega sem JWT)
    if _BLING_WEBHOOK_TENANT_ID:
        set_current_tenant(UUID(_BLING_WEBHOOK_TENANT_ID))

    # Desempacotar envelope Bling (v1)
    data   = body.get("data", body)  # fallback p/ payload legado

    nf_id = str(data.get("id", ""))
    if not nf_id or nf_id == "None":
        return {"status": "ignorado", "motivo": "sem_id"}

    situacao_num = data.get("situacao")
    try:
        situacao_num = int(situacao_num)
    except (TypeError, ValueError):
        situacao_num = 0

    # Ignorar eventos que não são emissão ou cancelamento
    if situacao_num not in _NF_SITUACAO_AUTORIZADA and situacao_num not in _NF_SITUACAO_CANCELADA:
        return {"status": "ignorado", "motivo": f"situacao_{situacao_num}_nao_tratada"}

    # Buscar NF completa na API do Bling para obter o pedido vinculado
    pedido_bling_id = _obter_pedido_bling_id_por_nf(nf_id=nf_id, situacao_num=situacao_num)

    if not pedido_bling_id:
        # NF sem pedido vinculado (ex: NF emitida manualmente fora do fluxo)
        return {"status": "ignorado", "motivo": "nf_sem_pedido_vinculado"}

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_bling_id
    ).first()

    if not pedido:
        return {"status": "ignorado", "motivo": "pedido_nao_encontrado_no_sistema"}

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    # ============================
    # NF EMITIDA / AUTORIZADA
    # ============================
    if situacao_num in _NF_SITUACAO_AUTORIZADA:
        acao = processar_nf_autorizada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        _gerar_provisao_simples_se_aplicavel(db=db, pedido=pedido, data=data)

        return {"status": "ok", "acao": acao}

    # ============================
    # NF CANCELADA
    # ============================
    if situacao_num in _NF_SITUACAO_CANCELADA:
        acao = processar_nf_cancelada(db=db, pedido=pedido, itens=itens)
        return {"status": "ok", "acao": acao}

    return {"status": "ignorado", "motivo": "status_nf_desconhecido"}


# ============================================================
# GET /integracoes/bling/nf/itens-sem-produto
# Itens de pedidos Bling cujo SKU não existe no cadastro local.
# Serve como painel de monitoramento para identificar SKUs órfãos.
# ============================================================

@router.get("/nf/itens-sem-produto")
def listar_itens_sem_produto(
    por_pagina: int = Query(50, ge=1, le=200),
    pagina: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna itens de pedidos integrados (Bling) cujo SKU não encontrou
    correspondência em nenhum produto cadastrado (codigo ou codigo_barras).
    Use este endpoint para identificar e corrigir desvinculações de estoque.
    """
    from app.produtos_models import Produto

    tenant_id = user_tenant[1]

    # Subquery: existe um produto com este SKU?
    produto_existe = exists().where(
        Produto.tenant_id == tenant_id,
        or_(
            Produto.codigo == PedidoIntegradoItem.sku,
            Produto.codigo_barras == PedidoIntegradoItem.sku,
        ),
    )

    # Todos os itens deste tenant cujo SKU não tem produto vinculado
    q = (
        db.query(PedidoIntegradoItem, PedidoIntegrado)
        .join(PedidoIntegrado, PedidoIntegrado.id == PedidoIntegradoItem.pedido_integrado_id)
        .filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            not_(produto_existe),
        )
        .order_by(PedidoIntegradoItem.reservado_em.desc())
    )

    total = q.count()
    rows = q.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    def _fmt(dt):
        if not dt:
            return None
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    items = [
        {
            "item_id": item.id,
            "sku": item.sku,
            "descricao": item.descricao,
            "quantidade": item.quantidade,
            "reservado_em": _fmt(item.reservado_em),
            "vendido_em": _fmt(item.vendido_em),
            "liberado_em": _fmt(item.liberado_em),
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "pedido_bling_id": pedido.pedido_bling_id,
            "pedido_status": pedido.status,
            "pedido_confirmado_em": _fmt(pedido.confirmado_em),
        }
        for item, pedido in rows
    ]

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "items": items,
    }
