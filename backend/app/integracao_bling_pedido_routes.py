import os
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db import get_session
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.bling_sync.routes_common import _upsert_sync_vinculo
from app.integracao_bling_nf_routes import (
    _dict,
    _nf_id_valido,
    _primeiro_preenchido,
    _texto,
)
from app.integracao_bling_pedido_payload import (
    _CANAL_LABELS,
    _LOJA_ID_CANAL_MAP,
    _acoes_operacionais_pedido,
    _coerce_float,
    _coerce_int,
    _dt_iso,
    _inferir_canal_por_loja_id,
    _inferir_canal_por_numero_pedido_loja,
    _montar_payload_pedido,
    _normalizar_canal,
    _normalizar_item_payload,
    _payload_principal,
    _pedido_tem_nf_deterministica,
    _resolver_canal_pedido,
    _resumir_ultima_nf_do_pedido_bling,
    _resumir_ultima_nf_webhook,
    _serializar_itens_pedido,
    _serializar_pedido_bling,
    _situacao_codigo_bling,
    _ultima_nf_payload_efetiva,
)
from app.integracao_bling_pedido_webhook_processor import (
    processar_pedido_bling_payload as _processar_pedido_bling_payload,
)
from app.integracao_bling_pedido_admin_routes import (
    cancelar_pedido_manual,
    confirmar_pedido_manual,
    consolidar_duplicidade_pedido,
    listar_pedidos_bling,
    reconciliar_duplicidades_pedidos_recentes,
    reconciliar_fluxo_pedido,
    reconciliar_status_pedidos_recentes,
    reprocessar_pedidos_sem_itens,
    router as pedidos_admin_router,
)
from app.services.bling_flow_monitor_service import (
    _nf_contexto_autorizado,
    abrir_incidente,
    registrar_evento,
    registrar_vinculo_nf_pedido,
)
from app.services.pedido_integrado_consolidation_service import (
    listar_pedidos_por_numero_loja,
    localizar_pedido_canonico_por_numero_loja,
    localizar_pedido_por_bling_id,
    loja_id_do_payload,
    marcar_payload_como_mesclado,
    numero_pedido_loja_do_payload,
    registrar_alias_bling_no_payload,
)
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(prefix="/integracoes/bling", tags=["Integração Bling - Pedido"])

__all__ = [
    "_CANAL_LABELS",
    "_LOJA_ID_CANAL_MAP",
    "_acoes_operacionais_pedido",
    "_coerce_float",
    "_coerce_int",
    "_dt_iso",
    "_inferir_canal_por_loja_id",
    "_inferir_canal_por_numero_pedido_loja",
    "_montar_payload_pedido",
    "_normalizar_canal",
    "_normalizar_item_payload",
    "_payload_principal",
    "_pedido_tem_nf_deterministica",
    "_resolver_canal_pedido",
    "_resumir_ultima_nf_do_pedido_bling",
    "_resumir_ultima_nf_webhook",
    "_serializar_itens_pedido",
    "_serializar_pedido_bling",
    "_situacao_codigo_bling",
    "_ultima_nf_payload_efetiva",
    "cancelar_pedido_manual",
    "confirmar_pedido_manual",
    "consolidar_duplicidade_pedido",
    "listar_pedidos_bling",
    "processar_pedido_bling_payload",
    "receber_pedido_bling",
    "reconciliar_duplicidades_pedidos_recentes",
    "reconciliar_fluxo_pedido",
    "reconciliar_status_pedidos_recentes",
    "reprocessar_pedidos_sem_itens",
    "router",
]


def _sincronizar_nf_do_pedido(
    *,
    db: Session,
    pedido: PedidoIntegrado,
    pedido_payload: dict | None,
    webhook_data: dict | None,
    processed_at,
    source: str,
    message: str,
    link_source: str,
    enriquecer_via_api: bool = True,
) -> dict | None:
    resumo_nf = _resumir_ultima_nf_do_pedido_bling(
        pedido_payload,
        enriquecer_via_api=enriquecer_via_api,
    )
    if not resumo_nf:
        return None

    payload_atual = _dict(pedido.payload)
    ultima_nf_atual = _ultima_nf_payload_efetiva(payload_atual)
    mesma_nf = _texto(ultima_nf_atual.get("id")) == _texto(
        resumo_nf.get("id")
    ) and _texto(ultima_nf_atual.get("numero")) == _texto(resumo_nf.get("numero"))

    pedido.payload = _montar_payload_pedido(
        webhook_data=webhook_data,
        pedido_completo=pedido_payload,
        payload_atual=pedido.payload,
        ultima_nf=resumo_nf,
    )
    db.add(pedido)

    if not mesma_nf:
        registrar_vinculo_nf_pedido(
            pedido=pedido,
            source=source,
            nf_bling_id=resumo_nf.get("id"),
            nf_numero=resumo_nf.get("numero"),
            message=message,
            payload={
                "link_source": link_source,
                "pedido_status_atual": pedido.status,
            },
            processed_at=processed_at,
            db=db,
        )

    return resumo_nf


def _processar_nf_autorizada_vinculada_ao_pedido(
    *,
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    resumo_nf: dict | None,
) -> str | None:
    resumo_nf = _dict(resumo_nf)
    nf_id = _nf_id_valido(
        _primeiro_preenchido(resumo_nf.get("id"), resumo_nf.get("nfe_id"))
    )
    if not nf_id or not _nf_contexto_autorizado(resumo_nf):
        return None

    from app.services.bling_nf_service import processar_nf_autorizada

    return processar_nf_autorizada(
        db=db,
        pedido=pedido,
        itens=itens,
        nf_id=nf_id,
    )


def _sincronizar_itens_pedido_integrado(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens_bling: list[dict] | None,
) -> int:
    itens_bling = itens_bling or []
    if not itens_bling:
        return 0

    itens_existentes = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )
    chaves_existentes: dict[tuple[str | None, int], int] = {}
    for item in itens_existentes:
        chave = (_texto(item.sku), int(float(item.quantidade or 0)))
        chaves_existentes[chave] = chaves_existentes.get(chave, 0) + 1

    criados = 0
    for item in itens_bling:
        item_normalizado = _normalizar_item_payload(item)
        sku = _texto(item_normalizado.get("sku"))
        quantidade = int(float(item_normalizado.get("quantidade") or 0))
        descricao = _texto(item_normalizado.get("descricao"))
        if not sku or quantidade <= 0:
            continue

        chave = (sku, quantidade)
        if chaves_existentes.get(chave, 0) > 0:
            chaves_existentes[chave] -= 1
            continue

        item_pedido = PedidoIntegradoItem(
            tenant_id=pedido.tenant_id,
            pedido_integrado_id=pedido.id,
            sku=sku,
            descricao=descricao,
            quantidade=quantidade,
        )
        try:
            if pedido.status not in {"cancelado", "expirado", "mesclado"}:
                EstoqueReservaService.reservar(db, item_pedido)
        except ValueError as e:
            logger.warning(
                f"[BLING WEBHOOK] Reserva nao criada para SKU {sku} em merge de duplicidade: {e}"
            )
        db.add(item_pedido)
        chaves_existentes[chave] = chaves_existentes.get(chave, 0) + 1
        criados += 1

    return criados


def _consolidar_pedido_duplicado_por_numero_loja(
    db: Session,
    *,
    tenant_id,
    pedido_bling_id: str,
    pedido_bling_numero,
    canal: str,
    status_inicial: str,
    payload_pedido: dict,
    itens_bling: list[dict] | None,
    event: str | None,
    event_date,
) -> PedidoIntegrado | None:
    numero_pedido_loja = numero_pedido_loja_do_payload(payload_pedido)
    if not numero_pedido_loja:
        return None

    loja_id = loja_id_do_payload(payload_pedido)
    candidatos = [
        pedido
        for pedido in listar_pedidos_por_numero_loja(
            db,
            tenant_id=tenant_id,
            numero_pedido_loja=numero_pedido_loja,
            loja_id=loja_id,
        )
        if _texto(pedido.pedido_bling_id) != _texto(pedido_bling_id)
    ]
    pedido_canonico = localizar_pedido_canonico_por_numero_loja(
        db,
        tenant_id=tenant_id,
        numero_pedido_loja=numero_pedido_loja,
        loja_id=loja_id,
    )
    if not pedido_canonico or int(pedido_canonico.id) not in {
        int(pedido.id) for pedido in candidatos
    }:
        return None

    payload_canonico = _montar_payload_pedido(
        webhook_data=_dict(payload_pedido).get("webhook"),
        pedido_completo=_payload_principal(payload_pedido),
        payload_atual=pedido_canonico.payload,
        ultima_nf=_dict(payload_pedido).get("ultima_nf"),
    )
    payload_canonico = registrar_alias_bling_no_payload(
        payload_canonico,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=_texto(pedido_bling_numero),
        numero_pedido_loja=numero_pedido_loja,
        loja_id=loja_id,
        merged_at=datetime.utcnow(),
    )
    pedido_canonico.payload = payload_canonico
    if (not pedido_canonico.canal or pedido_canonico.canal == "bling") and canal:
        pedido_canonico.canal = canal
    if not pedido_canonico.pedido_bling_numero and pedido_bling_numero:
        pedido_canonico.pedido_bling_numero = _texto(pedido_bling_numero)
    db.add(pedido_canonico)
    db.flush()

    pedido_duplicado = localizar_pedido_por_bling_id(
        db,
        tenant_id=tenant_id,
        pedido_bling_id=pedido_bling_id,
        resolver_mescla=False,
    )
    if not pedido_duplicado:
        payload_duplicado = marcar_payload_como_mesclado(
            payload_pedido,
            pedido_canonico=pedido_canonico,
            numero_pedido_loja=numero_pedido_loja,
            loja_id=loja_id,
            merged_at=datetime.utcnow(),
        )
        pedido_duplicado = PedidoIntegrado(
            tenant_id=tenant_id,
            pedido_bling_id=pedido_bling_id,
            pedido_bling_numero=_texto(pedido_bling_numero),
            canal=canal,
            status="mesclado",
            expira_em=pedido_canonico.expira_em,
            cancelado_em=datetime.utcnow(),
            payload=payload_duplicado,
        )
    else:
        pedido_duplicado.payload = marcar_payload_como_mesclado(
            pedido_duplicado.payload,
            pedido_canonico=pedido_canonico,
            numero_pedido_loja=numero_pedido_loja,
            loja_id=loja_id,
            merged_at=datetime.utcnow(),
        )
        pedido_duplicado.status = "mesclado"
        pedido_duplicado.cancelado_em = (
            pedido_duplicado.cancelado_em or datetime.utcnow()
        )
    db.add(pedido_duplicado)

    itens_criados = _sincronizar_itens_pedido_integrado(
        db,
        pedido=pedido_canonico,
        itens_bling=itens_bling,
    )
    db.commit()
    db.refresh(pedido_canonico)

    registrar_evento(
        tenant_id=tenant_id,
        source="runtime",
        event_type=event or "order.duplicate_merged",
        entity_type="pedido",
        status="warning",
        severity="high",
        message="Pedido duplicado no Bling foi consolidado pelo numero do pedido da loja.",
        pedido_integrado_id=pedido_canonico.id,
        pedido_bling_id=pedido_canonico.pedido_bling_id,
        payload={
            "pedido_bling_id_duplicado": pedido_bling_id,
            "pedido_bling_numero_duplicado": _texto(pedido_bling_numero),
            "numero_pedido_loja": numero_pedido_loja,
            "pedido_canonico_id": pedido_canonico.id,
            "pedido_canonico_bling_id": pedido_canonico.pedido_bling_id,
            "itens_incorporados": itens_criados,
            "status_inicial_duplicado": status_inicial,
        },
        processed_at=event_date,
        auto_fix_applied=True,
    )

    return pedido_canonico


def _resolver_produto_local(
    db: Session, pedido: PedidoIntegrado, item: PedidoIntegradoItem
):
    from app.services.bling_nf_service import (
        buscar_produto_do_item,
        criar_produto_automatico_do_bling,
    )

    produto = buscar_produto_do_item(
        db=db,
        tenant_id=pedido.tenant_id,
        sku=item.sku,
    )
    if produto:
        return produto

    return criar_produto_automatico_do_bling(
        db=db,
        tenant_id=pedido.tenant_id,
        sku=item.sku,
    )


def _mesmo_sku(sku_a: str | None, sku_b: str | None) -> bool:
    sku_a_limpo = _texto(sku_a)
    sku_b_limpo = _texto(sku_b)
    return bool(sku_a_limpo) and (sku_a_limpo or "").lower() == (
        sku_b_limpo or ""
    ).lower()


def _bling_produto_id_do_item_pedido(
    pedido: PedidoIntegrado, item: PedidoIntegradoItem
) -> str | None:
    pedido_payload = _payload_principal(_dict(getattr(pedido, "payload", None)))
    for raw_item in pedido_payload.get("itens") or []:
        item_payload = _normalizar_item_payload(raw_item)
        if _mesmo_sku(item_payload.get("sku"), item.sku):
            return _texto(item_payload.get("produto_bling_id"))
    return None


def _baixar_item_pedido(
    db: Session,
    pedido: PedidoIntegrado,
    item: PedidoIntegradoItem,
    *,
    motivo: str,
    observacao: str,
    user_id: int = 0,
) -> str | None:
    from app.services.bling_nf_service import (
        baixar_estoque_item_integrado,
        _obter_usuario_padrao_tenant,
    )

    produto = _resolver_produto_local(db=db, pedido=pedido, item=item)
    if not produto:
        return f"SKU '{item.sku}' nao encontrado"

    user_id_execucao = user_id or getattr(
        _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id), "id", None
    )
    if not user_id_execucao:
        return "Nenhum usuario valido encontrado para registrar a baixa automatica"

    bling_produto_id = _bling_produto_id_do_item_pedido(pedido, item)
    if bling_produto_id:
        try:
            _upsert_sync_vinculo(db, pedido.tenant_id, produto, bling_produto_id)
        except Exception as e:
            logger.warning(
                "[BLING PEDIDO] Nao foi possivel vincular SKU %s ao produto Bling %s: %s",
                item.sku,
                bling_produto_id,
                e,
            )

    baixar_estoque_item_integrado(
        db=db,
        tenant_id=pedido.tenant_id,
        produto=produto,
        quantidade=float(item.quantidade),
        motivo=motivo,
        referencia_id=pedido.id,
        referencia_tipo="pedido_integrado",
        user_id=user_id_execucao,
        documento=pedido.pedido_bling_numero,
        observacao=observacao,
    )
    return None


def _confirmar_pedido(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    *,
    motivo: str,
    observacao: str,
    user_id: int = 0,
    processed_at=None,
    aplicar_baixa_estoque: bool = False,
) -> list[str]:
    erros: list[str] = []

    if not aplicar_baixa_estoque:
        pedido.status = "confirmado"
        pedido.confirmado_em = pedido.confirmado_em or datetime.utcnow()
        db.add(pedido)
        db.commit()
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="runtime",
            event_type="pedido.confirmado",
            entity_type="pedido",
            status="ok",
            severity="info",
            message="Pedido confirmado no Bling; a venda aguardara a NF para consolidar o estoque.",
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            payload={
                "motivo": motivo,
                "observacao": observacao,
                "itens_total": len(itens),
                "erros_estoque": [],
                "baixa_estoque_status": "nf_pendente",
                "fonte_confirmacao": "pedido",
            },
            processed_at=processed_at,
        )
        return erros

    for item in itens:
        if item.vendido_em:
            continue

        try:
            erro = _baixar_item_pedido(
                db=db,
                pedido=pedido,
                item=item,
                motivo=motivo,
                observacao=observacao,
                user_id=user_id,
            )
            if erro:
                erros.append(erro)
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="runtime",
                    event_type="pedido.confirmacao.baixa",
                    entity_type="pedido",
                    status="error",
                    severity="critical",
                    message="Produto nao encontrado para baixa de estoque",
                    error_message=erro,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido.pedido_bling_id,
                    sku=item.sku,
                    processed_at=processed_at,
                )
                abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code="SKU_SEM_PRODUTO_LOCAL",
                    severity="critical",
                    title="SKU sem produto local",
                    message=f"O SKU '{item.sku}' nao foi encontrado durante a confirmacao do pedido.",
                    suggested_action="Tentar autocadastro do produto e reconciliar a baixa do pedido.",
                    auto_fixable=True,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido.pedido_bling_id,
                    sku=item.sku,
                    details={"motivo": motivo, "observacao": observacao},
                )
                continue

            EstoqueReservaService.confirmar_venda(db, item)
        except Exception as e:
            erros.append(f"SKU '{item.sku}': {str(e)[:80]}")
            logger.warning(f"[BLING PEDIDO] Erro ao baixar estoque SKU {item.sku}: {e}")
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="runtime",
                event_type="pedido.confirmacao.baixa",
                entity_type="pedido",
                status="error",
                severity="critical",
                message="Falha ao baixar estoque na confirmacao do pedido",
                error_message=str(e),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
                sku=item.sku,
                processed_at=processed_at,
            )
            abrir_incidente(
                tenant_id=pedido.tenant_id,
                code="PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                severity="critical",
                title="Falha na baixa do estoque",
                message=f"A confirmacao do pedido falhou ao baixar o estoque do SKU '{item.sku}'.",
                suggested_action="Reconciliar o pedido confirmado e reaplicar a baixa faltante.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
                sku=item.sku,
                details={"motivo": motivo, "erro": str(e)},
            )

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="pedido.confirmado",
        entity_type="pedido",
        status="ok" if not erros else "warning",
        severity="info" if not erros else "high",
        message=(
            "Pedido confirmado e todas as baixas de estoque foram aplicadas."
            if not erros
            else "Pedido confirmado, mas algumas baixas de estoque ficaram pendentes."
        ),
        error_message=", ".join(erros) if erros else None,
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        payload={
            "motivo": motivo,
            "observacao": observacao,
            "itens_total": len(itens),
            "erros_estoque": erros,
            "baixa_estoque_status": "ok" if not erros else "warning",
        },
        processed_at=processed_at,
    )
    return erros


def _cancelar_pedido(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    *,
    processed_at=None,
) -> None:
    for item in itens:
        if not item.liberado_em and not item.vendido_em:
            EstoqueReservaService.liberar(db, item)

    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="pedido.cancelado",
        entity_type="pedido",
        status="ok",
        severity="info",
        message="Pedido cancelado e reservas liberadas",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        processed_at=processed_at,
    )


router.include_router(pedidos_admin_router)


# Situações do pedido Bling — referência API v3
# https://developer.bling.com.br/referencia#/Pedidos%20de%20Venda/get_pedidos__idPedido_
_SITUACOES_PEDIDO_CANCELADO = {
    12,  # Cancelado
    13,  # Cancelado pelo comprador
    14,  # Cancelado por não pagamento
    15,  # Em cancelamento
}

_SITUACOES_PEDIDO_ATENDIDO = {
    9,  # Atendido (concluído/nota fiscal emitida)
}


def _bling_pedido_webhook_async_enabled() -> bool:
    raw = os.getenv("BLING_PEDIDO_WEBHOOK_ASYNC", "true")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


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


@router.post("/pedido", status_code=status.HTTP_202_ACCEPTED)
async def receber_pedido_bling(request: Request, db: Session = Depends(get_session)):
    """Recebe webhooks do Bling e enfileira o trabalho pesado fora da request."""
    _set_bling_request_tenant(request)
    body = await request.json()
    body = body if isinstance(body, dict) else {}

    if not _bling_pedido_webhook_async_enabled():
        return processar_pedido_bling_payload(body, db)

    try:
        from app.services.bling_pedido_webhook_queue_service import (
            enqueue_bling_pedido_webhook,
        )

        result = enqueue_bling_pedido_webhook(db, body)
        return {
            **result,
            "mode": "async_queue",
        }
    except Exception as exc:
        logger.exception(
            "[BLING WEBHOOK] Falha ao enfileirar webhook de pedido: %s", exc
        )
        try:
            db.rollback()
        except Exception:
            pass
        if str(
            os.getenv("BLING_PEDIDO_WEBHOOK_FALLBACK_SYNC", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}:
            return processar_pedido_bling_payload(body, db)
        raise HTTPException(
            status_code=503, detail="Fila de webhooks do Bling indisponivel"
        )


def processar_pedido_bling_payload(body: dict, db: Session):
    return _processar_pedido_bling_payload(body, db)
