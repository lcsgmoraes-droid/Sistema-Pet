
import os
import time
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - Pedido"]
)


# ============================================================
# GET /integracoes/bling/pedidos  — listagem com filtros
# ============================================================

@router.get("/pedidos")
def listar_pedidos_bling(
    status: Optional[str] = Query(None, description="aberto|confirmado|expirado|cancelado"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    q = db.query(PedidoIntegrado).filter(PedidoIntegrado.tenant_id == tenant_id)

    if status:
        q = q.filter(PedidoIntegrado.status == status)

    total = q.count()
    pedidos = (
        q.order_by(PedidoIntegrado.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    result = []
    for p in pedidos:
        itens = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == p.id
        ).all()

        def _dt(dt):
            if not dt: return None
            s = dt.isoformat()
            return s if ('+' in s or s.endswith('Z')) else s + '+00:00'

        result.append({
            "id": p.id,
            "pedido_bling_id": p.pedido_bling_id,
            "pedido_bling_numero": p.pedido_bling_numero,
            "canal": p.canal,
            "status": p.status,
            "criado_em": _dt(p.criado_em),
            "expira_em": _dt(p.expira_em),
            "confirmado_em": _dt(p.confirmado_em),
            "cancelado_em": _dt(p.cancelado_em),
            "itens": [
                {
                    "id": it.id,
                    "sku": it.sku,
                    "descricao": it.descricao,
                    "quantidade": it.quantidade,
                    "reservado_em": _dt(it.reservado_em),
                    "liberado_em": _dt(it.liberado_em),
                    "vendido_em": _dt(it.vendido_em),
                }
                for it in itens
            ],
        })

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "pedidos": result,
    }


# ============================================================
# POST /integracoes/bling/pedidos/{id}/confirmar-manual
# ============================================================

@router.post("/pedidos/{pedido_id}/confirmar-manual")
def confirmar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    user = user_tenant[0]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ("aberto", "expirado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser confirmado manualmente",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    erros_estoque = []
    for item in itens:
        if item.vendido_em:
            continue  # já confirmado

        EstoqueReservaService.confirmar_venda(db, item)

        # Baixar estoque real
        try:
            from app.estoque.service import EstoqueService
            from app.produtos_models import Produto

            produto = db.query(Produto).filter(
                Produto.codigo == item.sku,
                Produto.tenant_id == tenant_id,
            ).first()

            if produto:
                EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=float(item.quantidade),
                    motivo="venda_bling_manual",
                    referencia_id=pedido.id,
                    referencia_tipo="pedido_integrado",
                    user_id=getattr(user, "id", 0),
                    db=db,
                    tenant_id=tenant_id,
                    documento=pedido.pedido_bling_numero,
                    observacao=f"Baixa manual via tela Pedidos Bling",
                )
            else:
                erros_estoque.append(f"SKU '{item.sku}' não encontrado")
        except Exception as e:
            erros_estoque.append(f"SKU '{item.sku}': {str(e)[:80]}")
            logger.warning(f"[BLING MANUAL] Erro ao baixar estoque SKU {item.sku}: {e}")

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()

    return {
        "status": "ok",
        "pedido_id": pedido.id,
        "erros_estoque": erros_estoque,
    }


# ============================================================
# POST /integracoes/bling/pedidos/{id}/cancelar
# ============================================================

@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status in ("confirmado", "cancelado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser cancelado",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    for item in itens:
        if not item.liberado_em and not item.vendido_em:
            EstoqueReservaService.liberar(db, item)

    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()

    return {"status": "ok", "pedido_id": pedido.id}


# ============================================================
# POST /integracoes/bling/pedidos/reprocessar-sem-itens
# ============================================================

@router.post("/pedidos/reprocessar-sem-itens")
def reprocessar_pedidos_sem_itens(
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    """
    Re-busca os itens no Bling para pedidos que chegaram com 0 itens.
    Útil para corrigir pedidos que falharam na busca inicial de itens.
    """
    tenant_id = user_tenant[1]

    # Pedidos abertos sem nenhum item registrado
    subq_com_itens = (
        db.query(PedidoIntegradoItem.pedido_integrado_id)
        .distinct()
        .subquery()
    )
    pedidos_sem_itens = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.status.in_(["aberto", "expirado"]),
            PedidoIntegrado.id.notin_(subq_com_itens),
        )
        .limit(limite)
        .all()
    )

    if not pedidos_sem_itens:
        return {"reprocessados": 0, "message": "Nenhum pedido sem itens encontrado"}

    from app.bling_integration import BlingAPI
    _bling_api = BlingAPI()

    reprocessados = 0
    erros = []

    for pedido in pedidos_sem_itens:
        try:
            pedido_completo = _bling_api.consultar_pedido(pedido.pedido_bling_id)
            itens_bling = pedido_completo.get("itens", [])
            if not itens_bling:
                continue

            for item in itens_bling:
                sku = item.get("codigo") or item.get("sku")
                descricao = item.get("descricao")
                quantidade = int(float(item.get("quantidade", 0)))
                if not sku or quantidade <= 0:
                    continue
                item_pedido = PedidoIntegradoItem(
                    tenant_id=pedido.tenant_id,
                    pedido_integrado_id=pedido.id,
                    sku=sku,
                    descricao=descricao,
                    quantidade=quantidade,
                )
                try:
                    EstoqueReservaService.reservar(db, item_pedido)
                except ValueError:
                    pass
                db.add(item_pedido)

            db.commit()
            reprocessados += 1
        except Exception as e:
            erros.append({"pedido_bling_id": pedido.pedido_bling_id, "erro": str(e)[:120]})

    return {
        "reprocessados": reprocessados,
        "total_sem_itens": len(pedidos_sem_itens),
        "erros": erros,
    }


# Situações do pedido Bling — referência API v3
# https://developer.bling.com.br/referencia#/Pedidos%20de%20Venda/get_pedidos__idPedido_
_SITUACOES_PEDIDO_CANCELADO = {
    12,  # Cancelado
    13,  # Cancelado pelo comprador
    14,  # Cancelado por não pagamento
    15,  # Em cancelamento
}

_SITUACOES_PEDIDO_ATENDIDO = {
    9,   # Atendido (concluído/nota fiscal emitida)
}


@router.post("/pedido")
async def receber_pedido_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de pedidos do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'order.created'|'order.updated'|'order.deleted', data: {...} }
    """
    body = await request.json()

    # Tenant fixo para webhooks (chamadas sem JWT)
    _tenant_uuid = UUID(_BLING_WEBHOOK_TENANT_ID) if _BLING_WEBHOOK_TENANT_ID else None
    if _tenant_uuid:
        set_current_tenant(_tenant_uuid)

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "")  # ex: "order.created"
    data = body.get("data", body)  # fallback p/ payload legado sem envelope

    # ========================
    # EVENTO: NOTA FISCAL EMITIDA
    # Quando o Bling gera uma NF vinculada a um pedido de marketplace,
    # confirmar o pedido e baixar o estoque imediatamente.
    # ========================
    if "notafiscal" in event.lower() or "nota_fiscal" in event.lower() or event.startswith("nfe.") or event.startswith("nfce."):
        nf_data = data or {}
        # O pedido pode vir na chave "pedido" ou "pedidoVenda" do payload da NF
        pedido_ref = nf_data.get("pedido") or nf_data.get("pedidoVenda") or {}
        pedido_numero_nf = str(pedido_ref.get("numero") or pedido_ref.get("id") or "").strip()
        nf_id_bling = str(nf_data.get("id") or "").strip()

        if pedido_numero_nf or nf_id_bling:
            pedido = None
            # Buscar pelo número do pedido Bling (campo pedido_bling_numero)
            if pedido_numero_nf:
                pedido = db.query(PedidoIntegrado).filter(
                    PedidoIntegrado.pedido_bling_numero == pedido_numero_nf
                ).first()
            # Fallback: buscar pela chave do pedido se vier como ID
            if not pedido and pedido_numero_nf:
                pedido = db.query(PedidoIntegrado).filter(
                    PedidoIntegrado.pedido_bling_id == pedido_numero_nf
                ).first()

            if pedido and pedido.status not in ("confirmado", "cancelado"):
                tenant_id_nf = pedido.tenant_id
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
                for item in itens:
                    if item.vendido_em:
                        continue
                    EstoqueReservaService.confirmar_venda(db, item)
                    try:
                        from app.estoque.service import EstoqueService
                        from app.produtos_models import Produto
                        produto = db.query(Produto).filter(
                            Produto.codigo == item.sku,
                            Produto.tenant_id == tenant_id_nf,
                        ).first()
                        if produto:
                            EstoqueService.baixar_estoque(
                                produto_id=produto.id,
                                quantidade=float(item.quantidade),
                                motivo="venda_bling_nf",
                                referencia_id=pedido.id,
                                referencia_tipo="pedido_integrado",
                                user_id=0,
                                db=db,
                                tenant_id=tenant_id_nf,
                                documento=pedido.pedido_bling_numero,
                                observacao=f"Baixa automática — NF Bling emitida (evento {event})",
                            )
                        else:
                            logger.warning(
                                f"[BLING NF WEBHOOK] Produto não encontrado p/ baixa — SKU {item.sku}"
                            )
                    except Exception as _e:
                        logger.warning(
                            f"[BLING NF WEBHOOK] Erro ao baixar estoque SKU {item.sku}: {_e}"
                        )
                pedido.status = "confirmado"
                pedido.confirmado_em = datetime.utcnow()
                db.add(pedido)
                db.commit()
                logger.info(
                    f"[BLING NF WEBHOOK] Pedido {pedido.pedido_bling_id} confirmado via evento NF ({event})"
                )
                return {"status": "ok", "acao": "confirmado_por_nf"}

        return {"status": "ignorado", "motivo": f"evento_nf_sem_pedido_correspondente ({event})"}

    pedido_bling_id = str(data.get("id", ""))
    if not pedido_bling_id or pedido_bling_id == "None":
        return {"status": "ignorado", "motivo": "sem_id"}

    # ========================
    # EVENTO: EXCLUÍDO
    # ========================
    if event.endswith(".deleted"):
        pedido = db.query(PedidoIntegrado).filter(
            PedidoIntegrado.pedido_bling_id == pedido_bling_id
        ).first()
        if pedido and pedido.status not in ("confirmado", "cancelado"):
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            for item in itens:
                if not item.liberado_em and not item.vendido_em:
                    EstoqueReservaService.liberar(db, item)
            pedido.status = "cancelado"
            pedido.cancelado_em = datetime.utcnow()
            db.add(pedido)
            db.commit()
        return {"status": "ok", "acao": "cancelado"}

    # ========================
    # EVENTO: ATUALIZADO — checar situação no Bling
    # ========================
    if event.endswith(".updated"):
        situacao_raw = data.get("situacao")
        situacao_id = situacao_raw.get("id") if isinstance(situacao_raw, dict) else situacao_raw
        try:
            situacao_id = int(situacao_id) if situacao_id is not None else None
        except (ValueError, TypeError):
            situacao_id = None

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_CANCELADO:
            pedido = db.query(PedidoIntegrado).filter(
                PedidoIntegrado.pedido_bling_id == pedido_bling_id
            ).first()
            if pedido and pedido.status not in ("confirmado", "cancelado"):
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
                for item in itens:
                    if not item.liberado_em and not item.vendido_em:
                        EstoqueReservaService.liberar(db, item)
                pedido.status = "cancelado"
                pedido.cancelado_em = datetime.utcnow()
                db.add(pedido)
                db.commit()
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado (situacao_id={situacao_id})")
            return {"status": "ok", "acao": "cancelado_por_situacao"}

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_ATENDIDO:
            pedido = db.query(PedidoIntegrado).filter(
                PedidoIntegrado.pedido_bling_id == pedido_bling_id
            ).first()
            if pedido and pedido.status not in ("confirmado", "cancelado"):
                tenant_id = pedido.tenant_id
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
                for item in itens:
                    if item.vendido_em:
                        continue
                    EstoqueReservaService.confirmar_venda(db, item)
                    # Baixar estoque real
                    try:
                        from app.estoque.service import EstoqueService
                        from app.produtos_models import Produto
                        produto = db.query(Produto).filter(
                            Produto.codigo == item.sku,
                            Produto.tenant_id == tenant_id,
                        ).first()
                        if produto:
                            EstoqueService.baixar_estoque(
                                produto_id=produto.id,
                                quantidade=float(item.quantidade),
                                motivo="venda_bling_webhook",
                                referencia_id=pedido.id,
                                referencia_tipo="pedido_integrado",
                                user_id=0,
                                db=db,
                                tenant_id=tenant_id,
                                documento=pedido.pedido_bling_numero,
                                observacao="Baixa automática via webhook Bling (Atendido)",
                            )
                        else:
                            logger.warning(f"[BLING WEBHOOK] Produto não encontrado p/ baixa — SKU {item.sku}")
                    except Exception as e:
                        logger.warning(f"[BLING WEBHOOK] Erro ao baixar estoque SKU {item.sku}: {e}")
                pedido.status = "confirmado"
                pedido.confirmado_em = datetime.utcnow()
                db.add(pedido)
                db.commit()
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} confirmado e estoque baixado (situacao_id={situacao_id})")
            return {"status": "ok", "acao": "confirmado_por_situacao"}

        # updated sem situação relevante no payload — consultar API do Bling para verificar
        try:
            from app.bling_integration import BlingAPI
            pedido_api = BlingAPI().consultar_pedido(pedido_bling_id)
            situacao_api = pedido_api.get("situacao")
            situacao_id_api = situacao_api.get("id") if isinstance(situacao_api, dict) else situacao_api
            try:
                situacao_id_api = int(situacao_id_api) if situacao_id_api is not None else None
            except (ValueError, TypeError):
                situacao_id_api = None
        except Exception as e:
            logger.warning(f"[BLING WEBHOOK] Falha ao consultar pedido {pedido_bling_id} na API: {e}")
            situacao_id_api = None

        if situacao_id_api and situacao_id_api in _SITUACOES_PEDIDO_CANCELADO:
            pedido = db.query(PedidoIntegrado).filter(
                PedidoIntegrado.pedido_bling_id == pedido_bling_id
            ).first()
            if pedido and pedido.status not in ("confirmado", "cancelado"):
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
                for item in itens:
                    if not item.liberado_em and not item.vendido_em:
                        EstoqueReservaService.liberar(db, item)
                pedido.status = "cancelado"
                pedido.cancelado_em = datetime.utcnow()
                db.add(pedido)
                db.commit()
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado via consulta API (situacao_id={situacao_id_api})")
            return {"status": "ok", "acao": "cancelado_via_consulta_api"}

        return {"status": "ignorado", "motivo": "order_updated_sem_situacao_relevante"}

    # ========================
    # EVENTO: CRIADO
    # ========================
    # Idempotência
    existente = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_bling_id
    ).first()
    if existente:
        return {"status": "ignorado", "motivo": "pedido_ja_existe"}

    numero = data.get("numero")
    loja_data = data.get("loja", {}) if isinstance(data.get("loja"), dict) else {}
    loja_id = loja_data.get("id", 0)
    loja_nome = loja_data.get("nome", "")
    canal = loja_nome or (str(loja_id) if loja_id else "online")

    # O webhook NÃO inclui itens — buscar na API do Bling (com retry para evitar 0 itens)
    pedido_completo = {}
    itens_bling = []
    try:
        from app.bling_integration import BlingAPI
        _bling_api = BlingAPI()
        for _tentativa in range(3):
            try:
                pedido_completo = _bling_api.consultar_pedido(pedido_bling_id)
                itens_bling = pedido_completo.get("itens", [])
                if itens_bling:
                    break
                # Bling pode ainda não ter os itens indexados — aguardar e tentar de novo
                if _tentativa < 2:
                    time.sleep(2.0)
            except Exception as _e:
                if _tentativa == 2:
                    raise
                time.sleep(2.0)
        if not itens_bling:
            logger.warning(f"[BLING WEBHOOK] Pedido {pedido_bling_id}: itens vazios após 3 tentativas")
    except Exception as e:
        logger.warning(f"[BLING WEBHOOK] Falha ao buscar itens do pedido {pedido_bling_id}: {e}")

    if not _tenant_uuid:
        logger.error("[BLING WEBHOOK] BLING_WEBHOOK_TENANT_ID não configurado — pedido ignorado")
        return {"status": "erro", "motivo": "tenant_nao_configurado"}

    # Verificar situação atual no Bling — se já cancelado, não criar como aberto
    situacao_criacao = pedido_completo.get("situacao") if pedido_completo else None
    situacao_id_criacao = situacao_criacao.get("id") if isinstance(situacao_criacao, dict) else situacao_criacao
    try:
        situacao_id_criacao = int(situacao_id_criacao) if situacao_id_criacao is not None else None
    except (ValueError, TypeError):
        situacao_id_criacao = None

    if situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_CANCELADO:
        logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} order.created mas já cancelado (situacao_id={situacao_id_criacao}) — ignorado")
        return {"status": "ignorado", "motivo": "order_created_ja_cancelado"}

    status_inicial = "confirmado" if (situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_ATENDIDO) else "aberto"

    pedido = PedidoIntegrado(
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=numero,
        canal=canal,
        status=status_inicial,
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload=data
    )

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    for item in itens_bling:
        # Bling usa "codigo" como SKU no item de pedido
        sku = item.get("codigo") or item.get("sku")
        descricao = item.get("descricao")
        quantidade = int(float(item.get("quantidade", 0)))

        if not sku or quantidade <= 0:
            continue

        item_pedido = PedidoIntegradoItem(
            tenant_id=_tenant_uuid,
            pedido_integrado_id=pedido.id,
            sku=sku,
            descricao=descricao,
            quantidade=quantidade
        )

        try:
            EstoqueReservaService.reservar(db, item_pedido)
        except ValueError as e:
            # Produto não cadastrado no sistema ainda — salva o item sem reserva
            logger.warning(f"[BLING WEBHOOK] Reserva não criada para SKU {sku}: {e}")

        db.add(item_pedido)

    db.commit()

    # Se o pedido já nasceu "confirmado" (NF emitida no Bling antes do webhook order.updated),
    # deduzir estoque imediatamente — sem essa baixa, o estoque nunca seria ajustado.
    if status_inicial == "confirmado":
        itens_salvos = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == pedido.id
        ).all()
        for _item in itens_salvos:
            if _item.vendido_em:
                continue
            EstoqueReservaService.confirmar_venda(db, _item)
            try:
                from app.estoque.service import EstoqueService
                from app.produtos_models import Produto as _Produto
                _produto = db.query(_Produto).filter(
                    _Produto.codigo == _item.sku,
                    _Produto.tenant_id == _tenant_uuid,
                ).first()
                if _produto:
                    EstoqueService.baixar_estoque(
                        produto_id=_produto.id,
                        quantidade=float(_item.quantidade),
                        motivo="venda_bling_webhook",
                        referencia_id=pedido.id,
                        referencia_tipo="pedido_integrado",
                        user_id=0,
                        db=db,
                        tenant_id=_tenant_uuid,
                        documento=pedido.pedido_bling_numero,
                        observacao="Baixa automática order.created (já Atendido no Bling)",
                    )
                else:
                    logger.warning(
                        f"[BLING WEBHOOK] order.created confirmado — produto não encontrado p/ baixa, SKU {_item.sku}"
                    )
            except Exception as _e:
                logger.warning(
                    f"[BLING WEBHOOK] order.created confirmado — erro ao baixar estoque SKU {_item.sku}: {_e}"
                )
        pedido.confirmado_em = datetime.utcnow()
        db.add(pedido)
        db.commit()
        logger.info(
            f"[BLING WEBHOOK] Pedido {pedido_bling_id} (order.created já Atendido) — estoque baixado imediatamente"
        )

    return {"status": "ok", "pedido_id": pedido.id}
