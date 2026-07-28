from __future__ import annotations

from sqlalchemy.orm import Session

from app.pedido_integrado_models import PedidoIntegrado


INCIDENTE_PEDIDO_CANCELADO_NF_ATIVA = "PEDIDO_CANCELADO_COM_NF_ATIVA"


def processar_nf_vinculada_ao_pedido(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list,
    resumo_nf: dict | None,
) -> str | None:
    from app.services.bling_flow_monitor_diagnostics import _nf_contexto_autorizado
    from app.services.bling_flow_monitor_utils import _dict, _text
    from app.services.bling_nf_service import (
        processar_nf_autorizada,
        processar_nf_cancelada,
    )

    resumo = _dict(resumo_nf)
    nf_id = _text(resumo.get("id") or resumo.get("nfe_id"))
    if not nf_id or nf_id in {"0", "-1"}:
        return None

    situacao = resumo.get("situacao_codigo")
    if situacao is None:
        situacao = resumo.get("situacao") or resumo.get("status")
    if isinstance(situacao, dict):
        situacao = situacao.get("id") or situacao.get("valor")
    try:
        situacao_codigo = int(situacao)
    except (TypeError, ValueError):
        situacao_codigo = None
    situacao_texto = str(resumo.get("situacao") or resumo.get("status") or "").lower()

    if situacao_codigo == 4 or "cancelad" in situacao_texto:
        return processar_nf_cancelada(
            db=db,
            pedido=pedido,
            itens=itens,
            nf_id=nf_id,
        )
    if not _nf_contexto_autorizado(resumo):
        return None
    return processar_nf_autorizada(
        db=db,
        pedido=pedido,
        itens=itens,
        nf_id=nf_id,
    )


def preservar_pedido_cancelado_com_nf_ativa(
    db: Session,
    pedido: PedidoIntegrado,
    era_cancelado: bool,
) -> bool:
    if not era_cancelado:
        return False

    from datetime import datetime, timezone

    pedido.status = "cancelado"
    pedido.cancelado_em = getattr(pedido, "cancelado_em", None) or datetime.now(
        timezone.utc
    )
    return registrar_alerta_pedido_cancelado_com_nf_ativa(
        db,
        pedido=pedido,
        source="runtime",
    )


def registrar_alerta_pedido_cancelado_com_nf_ativa(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    nf_contexto: dict | None = None,
    source: str = "runtime",
    processed_at=None,
) -> bool:
    """Abre um alerta fiscal sem cancelar a NF automaticamente."""
    from app.services.bling_flow_monitor_diagnostics import (
        _nf_contexto_autorizado,
        _ultima_nf,
    )
    from app.services.bling_flow_monitor_service import (
        abrir_incidente,
        registrar_evento,
    )
    from app.services.bling_flow_monitor_utils import _dict, _text

    nf = _dict(nf_contexto) or _ultima_nf(getattr(pedido, "payload", None))
    if not _nf_contexto_autorizado(nf):
        return False

    nf_id = _text(nf.get("id") or nf.get("nfe_id"))
    nf_numero = _text(nf.get("numero"))
    details = {
        "nf_numero": nf_numero,
        "nf": nf,
        "regra_estoque": (
            "O estoque so volta depois que o cancelamento da NF for confirmado."
        ),
    }
    abrir_incidente(
        tenant_id=pedido.tenant_id,
        code=INCIDENTE_PEDIDO_CANCELADO_NF_ATIVA,
        severity="critical",
        title="Pedido cancelado com NF ainda ativa",
        message=(
            f"O pedido {getattr(pedido, 'pedido_bling_numero', None) or getattr(pedido, 'pedido_bling_id', None)} foi "
            f"cancelado, mas a NF {nf_numero or nf_id or 'vinculada'} continua autorizada."
        ),
        suggested_action=(
            "Cancelar a NF no Bling. O CorePet devolvera o estoque somente depois "
            "de receber a confirmacao fiscal do cancelamento."
        ),
        auto_fixable=False,
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        details=details,
        source=source,
        db=db,
    )
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source=source,
        event_type="order.cancelled.invoice_active",
        entity_type="pedido",
        status="warning",
        severity="critical",
        message="Pedido cancelado com NF autorizada ainda ativa",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        payload=details,
        processed_at=processed_at,
        db=db,
    )
    return True


def resolver_alerta_nf_cancelada(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    nf_id: str | None = None,
) -> int:
    from app.services.bling_flow_monitor_service import (
        resolver_incidentes_relacionados,
    )

    return resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=[INCIDENTE_PEDIDO_CANCELADO_NF_ATIVA],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        resolution_note=(
            "Cancelamento da NF confirmado; estoque reconciliado pelo CorePet."
        ),
    )


def reconciliar_pedido_cancelado_atualizado(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list,
    resumo_nf: dict | None,
    processed_at=None,
) -> str:
    acao_nf = processar_nf_vinculada_ao_pedido(
        db,
        pedido=pedido,
        itens=itens,
        resumo_nf=resumo_nf,
    )
    if pedido.status != "cancelado":
        from app.integracao_bling_pedido_routes import _cancelar_pedido

        _cancelar_pedido(
            db=db,
            pedido=pedido,
            itens=itens,
            processed_at=processed_at,
        )
    else:
        registrar_alerta_pedido_cancelado_com_nf_ativa(
            db,
            pedido=pedido,
            source="reconciliacao",
            processed_at=processed_at,
        )
        db.commit()
    return acao_nf or "pedido_cancelado"


def finalizar_importacao_pedido_cancelado(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list,
    resumo_nf: dict | None,
    processed_at=None,
) -> str:
    from app.services.bling_flow_monitor_service import registrar_vinculo_nf_pedido

    resumo_nf = resumo_nf or {}
    if resumo_nf:
        registrar_vinculo_nf_pedido(
            pedido=pedido,
            source="reconciliacao",
            nf_bling_id=resumo_nf.get("id"),
            nf_numero=resumo_nf.get("numero"),
            message="Pedido cancelado importado com NF vinculada.",
            payload={
                "link_source": "pedido.created.cancelado",
                "pedido_status_atual": pedido.status,
            },
            processed_at=processed_at,
            db=db,
        )
    acao_nf = processar_nf_vinculada_ao_pedido(
        db,
        pedido=pedido,
        itens=itens,
        resumo_nf=resumo_nf,
    )
    if not acao_nf:
        registrar_alerta_pedido_cancelado_com_nf_ativa(
            db,
            pedido=pedido,
            source="reconciliacao",
            processed_at=processed_at,
        )
        db.commit()
    return acao_nf or "pedido_cancelado_importado"


def resposta_importacao_pedido_cancelado(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    resumo_nf: dict | None,
    processed_at=None,
) -> dict:
    from app.pedido_integrado_item_models import PedidoIntegradoItem

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )
    acao = finalizar_importacao_pedido_cancelado(
        db,
        pedido=pedido,
        itens=itens,
        resumo_nf=resumo_nf,
        processed_at=processed_at,
    )
    return {"status": "ok", "pedido_id": pedido.id, "acao": acao}
