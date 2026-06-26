import os
from uuid import UUID

from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.services.bling_nf_service import (
    processar_nf_autorizada,
    processar_nf_cancelada,
    criar_produto_automatico_do_bling,
    AUTO_CADASTRO_BING_TAG,
    _nf_cache_pertence_a_outro_pedido,
)
from app.services.bling_flow_monitor_service import (
    abrir_incidente,
    registrar_evento,
    registrar_vinculo_nf_pedido,
    resolver_incidentes_relacionados,
)
from app.services.pedido_integrado_consolidation_service import (
    localizar_pedido_canonico_por_numero_loja,
    localizar_pedido_por_bling_id,
)
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")


def _bling_webhook_tenant_uuid() -> UUID | None:
    raw = os.getenv("BLING_WEBHOOK_TENANT_ID") or _BLING_WEBHOOK_TENANT_ID
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def _set_bling_request_tenant(request: Request | None = None) -> UUID | None:
    tenant_id = _bling_webhook_tenant_uuid()
    if tenant_id:
        set_current_tenant(tenant_id)
        if request is not None:
            request.state.tenant_id = str(tenant_id)
            request.state.tenant_source = "bling_webhook_env"
    return tenant_id


router = APIRouter(prefix="/integracoes/bling", tags=["Integração Bling - NF"])

# Situações de NF no Bling (campo situacao é um número)
# 1=Pendente, 2=Emitida DANFE, 4=Cancelada, 5=Autorizada, 9=Autorizada
_NF_SITUACAO_AUTORIZADA = {2, 5, 9}
_NF_SITUACAO_CANCELADA = {4}


from app.integracao_bling_nf_helpers import (
    _atualizar_cache_nota_webhook,
    _consolidar_ultima_nf,
    _dict,
    _executar_autocadastro_skus,
    _modelo_nota_bling,
    _nf_id_valido,
    _nf_webhook_autorizada,
    _nf_webhook_cancelada,
    _normalizar_resumo_nf,
    _primeiro_preenchido,
    _query_itens_sem_produto,
    _serializar_itens_sem_produto,
    _status_nota_webhook,
    _texto,
)
from app.integracao_bling_nf_pedidos import (
    _consultar_relacao_nf_bling,
    _extrair_numero_pedido_loja_nf,
    _gerar_provisao_simples_se_aplicavel,
    _localizar_pedido_local_por_numero_bling,
    _localizar_pedido_local_por_numero_loja,
    _loja_id_nf_payload,
    _registrar_nf_no_pedido,
    _remover_nf_do_pedido,
)


@router.post("/nf")
async def receber_nf_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de NF-e e NF-e de consumidor do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'invoice.created'|'invoice.updated', data: {...} }
    O campo data.situacao é um NÚMERO: 2=Emitida, 5/9=Autorizada, 4=Cancelada.
    O payload do webhook NÃO inclui o pedido vinculado — precisa chamar a API.
    """
    # Injetar tenant no contexto (webhook chega sem JWT)
    tenant_id_monitor = _set_bling_request_tenant(request)
    body = await request.json()

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "invoice.updated")
    event_date = body.get("date")
    data = body.get("data", body)  # fallback p/ payload legado

    nf_id = str(data.get("id", ""))
    if not nf_id or nf_id == "None":
        if tenant_id_monitor:
            registrar_evento(
                tenant_id=tenant_id_monitor,
                source="webhook",
                event_type=event or "invoice.updated",
                entity_type="nf",
                status="ignored",
                severity="warning",
                message="Webhook de NF ignorado porque chegou sem id da nota.",
                payload=_dict(data) or _dict(body),
                processed_at=event_date,
            )
        logger.info(f"[BLING NF] Webhook ignorado sem id. event={event}")
        return {"status": "ignorado", "motivo": "sem_id"}

    situacao_num = data.get("situacao")
    try:
        situacao_num = int(situacao_num)
    except (TypeError, ValueError):
        situacao_num = 0

    # Buscar NF completa na API do Bling para obter o pedido vinculado
    nf_relacao = _consultar_relacao_nf_bling(nf_id=nf_id, situacao_num=situacao_num)
    nf_dados = _dict(nf_relacao.get("nf_completa")) or _dict(data)
    pedido_ref_nf = _dict(
        _dict(nf_dados).get("pedido")
        or _dict(nf_dados).get("pedidoVenda")
        or _dict(nf_dados).get("pedidoCompra")
        or _dict(data).get("pedido")
        or _dict(data).get("pedidoVenda")
        or _dict(data).get("pedidoCompra")
    )
    pedido_bling_id = nf_relacao.get("pedido_bling_id") or _texto(
        pedido_ref_nf.get("id")
    )
    pedido_bling_numero = nf_relacao.get("pedido_bling_numero") or _texto(
        pedido_ref_nf.get("numero")
    )
    numero_pedido_loja = (
        nf_relacao.get("numero_pedido_loja")
        or _extrair_numero_pedido_loja_nf(nf_dados)
        or _extrair_numero_pedido_loja_nf(data)
    )
    nf_numero = str(_dict(nf_dados).get("numero") or "").strip() or None

    if tenant_id_monitor:
        _atualizar_cache_nota_webhook(
            db=db,
            tenant_id=tenant_id_monitor,
            nf_data=nf_dados,
            source="bling_webhook_nf",
        )

    if tenant_id_monitor:
        registrar_evento(
            tenant_id=tenant_id_monitor,
            source="webhook",
            event_type=event or "invoice.updated",
            entity_type="nf",
            status="received",
            severity="info",
            message="Webhook de NF recebido; o sistema vai localizar o pedido e atualizar o vinculo da nota.",
            pedido_bling_id=pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                **_dict(data),
                "status_nf": _status_nota_webhook(nf_dados, situacao_num),
                "nf_numero": nf_numero,
                "pedido_bling_numero": pedido_bling_numero,
                "numero_pedido_loja": numero_pedido_loja,
            },
            processed_at=event_date,
        )

    pedido = None
    if pedido_bling_id:
        pedido = localizar_pedido_por_bling_id(
            db,
            tenant_id=tenant_id_monitor,
            pedido_bling_id=pedido_bling_id,
        )
    if not pedido and tenant_id_monitor and pedido_bling_numero:
        pedido = _localizar_pedido_local_por_numero_bling(
            db,
            tenant_id=tenant_id_monitor,
            pedido_bling_numero=pedido_bling_numero,
        )
        if pedido:
            pedido_bling_id = pedido.pedido_bling_id
    if not pedido and tenant_id_monitor and numero_pedido_loja:
        pedido = _localizar_pedido_local_por_numero_loja(
            db,
            tenant_id=tenant_id_monitor,
            numero_pedido_loja=numero_pedido_loja,
            loja_id=_loja_id_nf_payload(nf_dados) or _loja_id_nf_payload(data),
        )
        if pedido:
            pedido_bling_id = pedido.pedido_bling_id

    if pedido:
        pedido_ref_conflitante = _nf_cache_pertence_a_outro_pedido(
            db,
            tenant_id=pedido.tenant_id,
            nf_bling_id=nf_id,
            pedido_bling_id_atual=pedido.pedido_bling_id,
        )
        if pedido_ref_conflitante and pedido_ref_conflitante != pedido.pedido_bling_id:
            pedido_correto = localizar_pedido_por_bling_id(
                db,
                tenant_id=pedido.tenant_id,
                pedido_bling_id=pedido_ref_conflitante,
            )
            if pedido_correto:
                pedido = pedido_correto
                pedido_bling_id = pedido_correto.pedido_bling_id
                pedido_bling_numero = pedido_correto.pedido_bling_numero
            else:
                if tenant_id_monitor:
                    abrir_incidente(
                        tenant_id=tenant_id_monitor,
                        code="NF_VINCULADA_A_OUTRO_PEDIDO",
                        severity="critical",
                        title="NF recebida com conflito de pedido",
                        message=(
                            f"A NF {nf_numero or nf_id} pertence ao pedido Bling {pedido_ref_conflitante}, "
                            f"mas o pedido local localizado foi {pedido.pedido_bling_id}."
                        ),
                        suggested_action="Importar o pedido correto antes de consolidar a NF localmente.",
                        auto_fixable=False,
                        pedido_integrado_id=pedido.id,
                        pedido_bling_id=pedido.pedido_bling_id,
                        nf_bling_id=nf_id,
                        details={
                            "nf_numero": nf_numero,
                            "pedido_bling_id_esperado": pedido_ref_conflitante,
                            "pedido_bling_numero": pedido_bling_numero,
                            "numero_pedido_loja": numero_pedido_loja,
                        },
                        source="runtime",
                    )
                return {
                    "status": "ok",
                    "acao": "nf_bloqueada_por_conflito_de_pedido",
                    "situacao": _status_nota_webhook(nf_dados, situacao_num),
                }

    if not pedido and not pedido_bling_id and not pedido_bling_numero:
        # NF sem pedido vinculado (ex: NF emitida manualmente fora do fluxo)
        if tenant_id_monitor:
            abrir_incidente(
                tenant_id=tenant_id_monitor,
                code="NF_SEM_PEDIDO_VINCULADO",
                severity="high",
                title="NF sem pedido vinculado",
                message="A NF recebida do Bling nao retornou nenhum pedido vinculado na consulta da API.",
                suggested_action="Revisar a origem da NF no Bling e vincular manualmente ao pedido correto, se existir.",
                auto_fixable=False,
                nf_bling_id=nf_id,
                details={
                    "situacao_num": situacao_num,
                    "nf_numero": nf_numero,
                    "pedido_bling_numero": pedido_bling_numero,
                    "numero_pedido_loja": numero_pedido_loja,
                },
                source="runtime",
            )
        return {
            "status": "ok",
            "acao": "nf_registrada_sem_pedido_vinculado",
            "situacao": _status_nota_webhook(nf_dados, situacao_num),
        }

    if not pedido:
        if tenant_id_monitor:
            abrir_incidente(
                tenant_id=tenant_id_monitor,
                code="NF_SEM_PEDIDO_LOCAL",
                severity="critical",
                title="NF vinculada a pedido inexistente localmente",
                message="A NF referencia um pedido do Bling que ainda nao existe ou nao foi encontrado no sistema.",
                suggested_action="Importar/reprocessar o pedido correspondente antes de consolidar a NF.",
                auto_fixable=False,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                details={
                    "situacao_num": situacao_num,
                    "nf_numero": nf_numero,
                    "pedido_bling_numero": pedido_bling_numero,
                    "numero_pedido_loja": numero_pedido_loja,
                },
                source="runtime",
            )
        return {
            "status": "ok",
            "acao": "nf_registrada_sem_pedido_local",
            "situacao": _status_nota_webhook(nf_dados, situacao_num),
        }

    if pedido.tenant_id != tenant_id_monitor:
        _atualizar_cache_nota_webhook(
            db=db,
            tenant_id=pedido.tenant_id,
            nf_data=nf_dados,
            source="bling_webhook_nf",
        )

    _registrar_nf_no_pedido(
        pedido=pedido,
        data=nf_dados,
        nf_id=nf_id,
        situacao_num=situacao_num,
    )
    registrar_vinculo_nf_pedido(
        pedido=pedido,
        source="webhook",
        nf_bling_id=nf_id,
        nf_numero=nf_numero,
        message="NF localizada no webhook e vinculada ao pedido correspondente.",
        payload={
            "link_source": "nf.webhook",
            "pedido_status_antes": pedido.status,
            "numero_pedido_loja": numero_pedido_loja,
        },
        processed_at=event_date,
        db=db,
    )
    resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=["NF_SEM_PEDIDO_VINCULADO", "NF_SEM_PEDIDO_LOCAL"],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=nf_id,
        resolution_note="NF vinculada posteriormente ao pedido correspondente.",
    )

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )

    # ============================
    # NF EMITIDA / AUTORIZADA
    # ============================
    if _nf_webhook_autorizada(nf_dados, situacao_num):
        acao = processar_nf_autorizada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        _gerar_provisao_simples_se_aplicavel(db=db, pedido=pedido, data=nf_dados)
        status_evento = (
            "ok" if acao in {"venda_confirmada", "venda_ja_confirmada"} else "error"
        )
        severidade_evento = "info" if status_evento == "ok" else "critical"
        if acao == "venda_confirmada":
            mensagem_evento = (
                "NF autorizada processada, pedido vinculado e estoque reconciliado."
            )
        elif acao == "venda_ja_confirmada":
            mensagem_evento = (
                "NF autorizada processada; o pedido ja estava conciliado anteriormente."
            )
        elif acao == "nf_vinculada_outro_pedido":
            mensagem_evento = "NF autorizada recebida; o vinculo incorreto foi removido automaticamente e a baixa ficou bloqueada neste pedido."
        else:
            mensagem_evento = "NF autorizada recebida, mas a conciliacao nao conseguiu concluir a baixa automaticamente."
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="webhook",
            event_type="invoice.authorized",
            entity_type="nf",
            status=status_evento,
            severity=severidade_evento,
            message=mensagem_evento,
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "acao": acao,
                "nf_numero": nf_numero,
                "numero_pedido_loja": numero_pedido_loja,
                "pedido_status_atual": pedido.status,
            },
            processed_at=event_date,
        )

        return {"status": "ok", "acao": acao}

    # ============================
    # NF CANCELADA
    # ============================
    if _nf_webhook_cancelada(nf_dados, situacao_num):
        acao = processar_nf_cancelada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="webhook",
            event_type="invoice.cancelled",
            entity_type="nf",
            status="ok",
            severity="info",
            message="NF cancelada processada e pedido atualizado conforme o evento recebido.",
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "acao": acao,
                "nf_numero": nf_numero,
                "numero_pedido_loja": numero_pedido_loja,
                "pedido_status_atual": pedido.status,
            },
            processed_at=event_date,
        )
        return {"status": "ok", "acao": acao}

    db.add(pedido)
    db.commit()

    status_nf = _status_nota_webhook(nf_dados, situacao_num) or "Pendente"
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="webhook",
        event_type="invoice.status_updated",
        entity_type="nf",
        status="ok",
        severity="info",
        message="Status da NF atualizado e vinculo com o pedido mantido no sistema.",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=nf_id,
        payload={
            "acao": "status_nf_atualizado",
            "status_nf": status_nf,
            "nf_numero": nf_numero,
            "numero_pedido_loja": numero_pedido_loja,
            "pedido_status_atual": pedido.status,
        },
        processed_at=event_date,
    )
    return {
        "status": "ok",
        "acao": "status_nf_atualizado",
        "situacao": status_nf,
    }


# ============================================================
# GET /integracoes/bling/nf/itens-sem-produto
# Itens de pedidos Bling cujo SKU não existe no cadastro local.
# Serve como painel de monitoramento para identificar SKUs órfãos.
# ============================================================


@router.get("/nf/itens-sem-produto")
def listar_itens_sem_produto(
    por_pagina: int = Query(50, ge=1, le=200),
    pagina: int = Query(1, ge=1),
    autocriar_automaticamente: bool = Query(True),
    max_skus_autocadastro: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna itens de pedidos integrados (Bling) cujo SKU não encontrou
    correspondência em nenhum produto cadastrado (codigo ou codigo_barras).
    Use este endpoint para identificar e corrigir desvinculações de estoque.
    """
    tenant_id = user_tenant[1]
    q = _query_itens_sem_produto(db=db, tenant_id=tenant_id)

    auto_cadastros_executados = 0
    auto_cadastros_falhas = 0

    if autocriar_automaticamente:
        candidatos = q.limit(max_skus_autocadastro * 4).all()
        auto_cadastros_executados, auto_cadastros_falhas = _executar_autocadastro_skus(
            db=db,
            tenant_id=tenant_id,
            rows=candidatos,
            max_skus_autocadastro=max_skus_autocadastro,
        )

        if auto_cadastros_executados > 0:
            q = _query_itens_sem_produto(db=db, tenant_id=tenant_id)

    total = q.count()
    rows = q.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    items = _serializar_itens_sem_produto(rows)

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "items": items,
        "autocriar_automaticamente": autocriar_automaticamente,
        "auto_cadastros_executados": auto_cadastros_executados,
        "auto_cadastros_falhas": auto_cadastros_falhas,
    }


@router.get("/nf/autocadastros-recentes")
def listar_autocadastros_recentes(
    horas: int = Query(24, ge=1, le=72),
    limite: int = Query(50, ge=1, le=200),
    resumo: bool = Query(False),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    from app.produtos_models import Produto

    tenant_id = user_tenant[1]
    dt_limite = datetime.now(timezone.utc) - timedelta(hours=horas)

    q = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.informacoes_adicionais_nf.isnot(None),
            Produto.informacoes_adicionais_nf.ilike(f"%{AUTO_CADASTRO_BING_TAG}%"),
            Produto.created_at >= dt_limite,
        )
        .order_by(Produto.created_at.desc())
    )

    total = q.count()
    if resumo:
        return {"total": total, "horas": horas}

    produtos = q.limit(limite).all()
    items = [
        {
            "produto_id": p.id,
            "codigo": p.codigo,
            "nome": p.nome,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in produtos
    ]

    return {
        "total": total,
        "horas": horas,
        "limite": limite,
        "items": items,
    }
