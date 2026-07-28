from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao


INCIDENTE_RETORNO_ESTOQUE_PENDENTE = "NF_CANCELADA_RETORNO_ESTOQUE_PENDENTE"
JUSTIFICATIVA_CANCELAMENTO_PADRAO = (
    "Pedido cancelado no marketplace antes da conclusao da entrega."
)


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nf_do_pedido(
    pedido: PedidoIntegrado,
    nf_contexto: dict | None = None,
) -> dict:
    if isinstance(nf_contexto, dict) and nf_contexto:
        return dict(nf_contexto)

    from app.services.bling_flow_monitor_diagnostics import _ultima_nf

    return _ultima_nf(getattr(pedido, "payload", None))


def _nf_cancelada(nf: dict | None) -> bool:
    nf = _dict(nf)
    situacao = nf.get("situacao_codigo")
    if situacao is None:
        situacao = nf.get("situacao") or nf.get("status")
    if isinstance(situacao, dict):
        situacao = situacao.get("id") or situacao.get("valor")
    try:
        if int(situacao) == 4:
            return True
    except (TypeError, ValueError):
        pass
    return "cancelad" in str(nf.get("situacao") or nf.get("status") or "").lower()


def _movimentos_saida_ativos(
    db: Session,
    pedido: PedidoIntegrado,
) -> list[EstoqueMovimentacao]:
    return (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )


def _atualizar_payload(
    pedido: PedidoIntegrado,
    *,
    chave: str,
    dados: dict,
) -> dict:
    payload = dict(_dict(getattr(pedido, "payload", None)))
    payload[chave] = dados
    pedido.payload = payload
    return dados


def solicitar_cancelamento_nf_bling(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    nf_contexto: dict | None = None,
    justificativa: str | None = None,
    automatico: bool = False,
    forcar: bool = False,
) -> dict:
    """Solicita o cancelamento fiscal, sem alterar o estoque local."""
    from app.bling_integration import BlingAPI
    from app.services.bling_flow_monitor_service import registrar_evento

    nf = _nf_do_pedido(pedido, nf_contexto)
    nf_id = _text(nf.get("id") or nf.get("nfe_id"))
    if not nf_id or nf_id in {"0", "-1"}:
        return {
            "success": False,
            "solicitada": False,
            "motivo": "pedido_sem_nf_vinculada",
        }
    if _nf_cancelada(nf):
        return {
            "success": True,
            "solicitada": False,
            "motivo": "nf_ja_cancelada",
            "nf_id": nf_id,
        }

    payload = _dict(getattr(pedido, "payload", None))
    estado_atual = _dict(payload.get("cancelamento_nf"))
    mesma_nf = _text(estado_atual.get("nf_id")) == nf_id
    if (
        not forcar
        and mesma_nf
        and estado_atual.get("status") in {"solicitado", "confirmado"}
    ):
        return {
            "success": True,
            "solicitada": False,
            "motivo": "solicitacao_ja_registrada",
            "nf_id": nf_id,
            "estado": estado_atual,
        }

    texto_justificativa = _text(justificativa) or JUSTIFICATIVA_CANCELAMENTO_PADRAO
    if len(texto_justificativa) < 15:
        raise ValueError("Justificativa deve ter no minimo 15 caracteres")

    tentativas = int(estado_atual.get("tentativas") or 0) + 1
    try:
        resultado = BlingAPI().cancelar_nfe(int(nf_id), texto_justificativa)
    except Exception as exc:
        estado = {
            "nf_id": nf_id,
            "nf_numero": _text(nf.get("numero")),
            "status": "erro",
            "automatico": automatico,
            "tentativas": tentativas,
            "justificativa": texto_justificativa,
            "ultima_tentativa_em": _agora_iso(),
            "erro": str(exc),
        }
        _atualizar_payload(pedido, chave="cancelamento_nf", dados=estado)
        db.add(pedido)
        db.flush()
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="runtime",
            event_type="invoice.cancellation.request_failed",
            entity_type="nf",
            status="error",
            severity="critical",
            message="Bling rejeitou ou nao recebeu a solicitacao de cancelamento da NF",
            pedido_integrado_id=pedido.id,
            pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
            nf_bling_id=nf_id,
            payload=estado,
            db=db,
        )
        if automatico:
            return {
                "success": False,
                "solicitada": False,
                "motivo": "falha_ao_solicitar",
                "nf_id": nf_id,
                "erro": str(exc),
            }
        raise

    estado = {
        "nf_id": nf_id,
        "nf_numero": _text(nf.get("numero")),
        "status": "solicitado",
        "automatico": automatico,
        "tentativas": tentativas,
        "justificativa": texto_justificativa,
        "ultima_tentativa_em": _agora_iso(),
        "erro": None,
    }
    _atualizar_payload(pedido, chave="cancelamento_nf", dados=estado)
    db.add(pedido)
    db.flush()
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="invoice.cancellation.requested",
        entity_type="nf",
        status="ok",
        severity="info",
        message="Cancelamento da NF solicitado ao Bling",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        payload={**estado, "resultado_bling": resultado},
        db=db,
    )
    return {
        "success": True,
        "solicitada": True,
        "nf_id": nf_id,
        "estado": estado,
        "resultado_bling": resultado,
    }


def registrar_nf_cancelada_aguardando_decisao(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str | None = None,
) -> str:
    """Confirma o cancelamento fiscal sem devolver produtos ao estoque."""
    from app.services.bling_flow_monitor_service import (
        abrir_incidente,
        registrar_evento,
        resolver_incidentes_relacionados,
    )
    from app.services.pedido_nf_reconciliation_service import (
        INCIDENTE_PEDIDO_CANCELADO_NF_ATIVA,
    )

    nf = _nf_do_pedido(pedido)
    nf_id = _text(nf_id) or _text(nf.get("id") or nf.get("nfe_id"))
    agora = _agora_iso()
    pedido.status = "cancelado"
    pedido.cancelado_em = getattr(pedido, "cancelado_em", None) or datetime.now(
        timezone.utc
    )

    cancelamento_atual = _dict(_dict(pedido.payload).get("cancelamento_nf"))
    _atualizar_payload(
        pedido,
        chave="cancelamento_nf",
        dados={
            **cancelamento_atual,
            "nf_id": nf_id,
            "nf_numero": _text(nf.get("numero"))
            or _text(cancelamento_atual.get("nf_numero")),
            "status": "confirmado",
            "confirmado_em": agora,
            "erro": None,
        },
    )
    resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=[INCIDENTE_PEDIDO_CANCELADO_NF_ATIVA],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        resolution_note=(
            "Cancelamento fiscal confirmado; decisao fisica do estoque separada."
        ),
    )

    movimentos_ativos = _movimentos_saida_ativos(db, pedido)
    retorno_atual = _dict(_dict(pedido.payload).get("retorno_estoque"))
    if retorno_atual.get("status") in {"retornado", "nao_retornado"}:
        db.add(pedido)
        db.commit()
        return f"nf_cancelada_estoque_{retorno_atual['status']}"

    if not movimentos_ativos:
        _atualizar_payload(
            pedido,
            chave="retorno_estoque",
            dados={
                "nf_id": nf_id,
                "status": "sem_movimento",
                "registrado_em": agora,
                "quantidade_movimentos": 0,
            },
        )
        for item in itens:
            if not getattr(item, "vendido_em", None):
                item.liberado_em = item.liberado_em or datetime.utcnow()
                db.add(item)
        db.add(pedido)
        db.commit()
        return "nf_cancelada_sem_movimento_estoque"

    detalhes = {
        "nf_id": nf_id,
        "nf_numero": _text(nf.get("numero")),
        "status": "pendente",
        "registrado_em": agora,
        "quantidade_movimentos": len(movimentos_ativos),
        "movimentos": [
            {
                "id": movimento.id,
                "produto_id": movimento.produto_id,
                "quantidade": float(movimento.quantidade or 0),
            }
            for movimento in movimentos_ativos
        ],
    }
    _atualizar_payload(pedido, chave="retorno_estoque", dados=detalhes)
    abrir_incidente(
        tenant_id=pedido.tenant_id,
        code=INCIDENTE_RETORNO_ESTOQUE_PENDENTE,
        severity="high",
        title="NF cancelada aguardando decisao de estoque",
        message=(
            "A NF foi cancelada, mas o retorno fisico dos produtos ainda nao foi "
            "confirmado."
        ),
        suggested_action=(
            "Conferir os produtos e escolher Voltar ao estoque ou Nao retornou."
        ),
        auto_fixable=False,
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        details=detalhes,
        source="runtime",
        db=db,
    )
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="inventory.return.awaiting_decision",
        entity_type="pedido",
        status="warning",
        severity="high",
        message="NF cancelada aguardando conferencia fisica do retorno",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        payload=detalhes,
        db=db,
    )
    db.add(pedido)
    db.commit()
    return "nf_cancelada_retorno_estoque_pendente"


def decidir_retorno_estoque(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    acao: str,
    motivo: str,
    user_id: int | None,
) -> dict:
    """Aplica uma unica decisao manual sobre o retorno fisico dos produtos."""
    from app.estoque.service import EstoqueService
    from app.services.bling_flow_monitor_service import (
        registrar_evento,
        resolver_incidentes_relacionados,
    )
    from app.services.bling_nf_service import (
        _obter_usuario_padrao_tenant,
        _restaurar_lotes_consumidos,
        _sincronizar_cache_estoque_virtual,
    )
    from app.services.kit_estoque_service import KitEstoqueService

    acao = str(acao or "").strip().lower()
    if acao not in {"retornar", "nao_retornar"}:
        raise ValueError("Acao de estoque invalida")
    motivo = str(motivo or "").strip()
    if len(motivo) < 5:
        raise ValueError("Informe um motivo com pelo menos 5 caracteres")

    retorno_atual = _dict(_dict(pedido.payload).get("retorno_estoque"))
    status_final = "retornado" if acao == "retornar" else "nao_retornado"
    if retorno_atual.get("status") in {"retornado", "nao_retornado"}:
        return {
            "success": True,
            "idempotente": True,
            "status": retorno_atual.get("status"),
            "movimentos_processados": 0,
        }
    if retorno_atual.get("status") != "pendente":
        raise ValueError("Este pedido nao possui retorno de estoque pendente")

    movimentos_ativos = _movimentos_saida_ativos(db, pedido)
    nf_id = _text(retorno_atual.get("nf_id"))
    processados = 0
    if acao == "retornar":
        usuario_padrao = _obter_usuario_padrao_tenant(
            db=db,
            tenant_id=pedido.tenant_id,
        )
        for movimentacao in movimentos_ativos:
            _restaurar_lotes_consumidos(db, movimentacao)
            user_id_movimentacao = (
                user_id
                or getattr(movimentacao, "user_id", None)
                or getattr(usuario_padrao, "id", None)
            )
            if not user_id_movimentacao:
                raise ValueError(
                    "Nenhum usuario valido disponivel para devolver o estoque"
                )
            EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo="retorno_confirmado_nf_cancelada",
                referencia_id=pedido.id,
                referencia_tipo="pedido_integrado",
                user_id=user_id_movimentacao,
                db=db,
                tenant_id=pedido.tenant_id,
                documento=getattr(pedido, "pedido_bling_numero", None),
                observacao=(
                    f"Retorno fisico confirmado da NF cancelada #{nf_id or ''}. "
                    f"Motivo: {motivo}"
                ),
            )
            for (
                kit_id,
                _estoque_virtual,
            ) in KitEstoqueService.recalcular_kits_que_usam_produto(
                db,
                movimentacao.produto_id,
            ).items():
                _sincronizar_cache_estoque_virtual(
                    db,
                    pedido.tenant_id,
                    kit_id,
                )
            movimentacao.status = "cancelado"
            observacao_original = (movimentacao.observacao or "").strip()
            complemento = (
                f"Retorno fisico confirmado apos NF cancelada. Motivo: {motivo}"
            )
            movimentacao.observacao = (
                f"{observacao_original} | {complemento}"
                if observacao_original
                else complemento
            )
            db.add(movimentacao)
            processados += 1
        for item in itens:
            item.vendido_em = None
            item.liberado_em = item.liberado_em or datetime.utcnow()
            db.add(item)
    else:
        for movimentacao in movimentos_ativos:
            observacao_original = (movimentacao.observacao or "").strip()
            complemento = (
                f"Saida mantida apos NF cancelada; produto nao retornou. Motivo: {motivo}"
            )
            movimentacao.observacao = (
                f"{observacao_original} | {complemento}"
                if observacao_original
                else complemento
            )
            db.add(movimentacao)
            processados += 1

    decisao = {
        **retorno_atual,
        "status": status_final,
        "decidido_em": _agora_iso(),
        "decidido_por": user_id,
        "motivo": motivo,
        "movimentos_processados": processados,
    }
    _atualizar_payload(pedido, chave="retorno_estoque", dados=decisao)
    resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=[INCIDENTE_RETORNO_ESTOQUE_PENDENTE],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        resolution_note=(
            "Produtos devolvidos ao estoque."
            if acao == "retornar"
            else f"Saida mantida; produto nao retornou. Motivo: {motivo}"
        ),
    )
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="manual",
        event_type=f"inventory.return.{status_final}",
        entity_type="pedido",
        status="ok",
        severity="info",
        message=(
            "Retorno fisico confirmado e estoque devolvido"
            if acao == "retornar"
            else "Pendencia encerrada sem devolucao ao estoque"
        ),
        pedido_integrado_id=pedido.id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
        nf_bling_id=nf_id,
        payload=decisao,
        db=db,
    )
    db.add(pedido)
    db.commit()
    return {
        "success": True,
        "idempotente": False,
        "status": status_final,
        "movimentos_processados": processados,
    }
