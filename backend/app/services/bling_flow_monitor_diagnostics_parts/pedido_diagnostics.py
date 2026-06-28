from __future__ import annotations

from app.services.bling_flow_monitor_diagnostics_parts.context import (
    _canal_pedido_integrado,
    _nf_autorizada,
    _nf_contexto_autorizado,
    _numero_pedido_loja_pedido,
    _pedido_total,
    _ultima_nf,
)
from app.services.bling_flow_monitor_diagnostics_parts.incident_builder import (
    _make_incident,
)
from app.services.bling_flow_monitor_diagnostics_parts.recent_nfs import (
    _nf_detectada_combina_com_pedido,
)
from app.services.bling_flow_monitor_utils import (
    _dict,
    _json_safe,
    _primeiro_preenchido,
    _text,
)


def diagnosticar_pedido_integrado(
    pedido,
    itens,
    payload: dict | None,
    *,
    movimentacoes_saida: int,
    movimentacoes_saida_nf: int | None = None,
    itens_sem_produto: list[dict] | None = None,
    itens_mapeados_por_barra: list[dict] | None = None,
    nf_detectada: dict | None = None,
    nfs_detectadas: list[dict] | None = None,
) -> list[dict]:
    itens_sem_produto = itens_sem_produto or []
    itens_mapeados_por_barra = itens_mapeados_por_barra or []
    incidentes: list[dict] = []
    nf = _ultima_nf(payload)
    nf_detectada = _dict(nf_detectada)
    nfs_detectadas = [
        _dict(item) for item in (nfs_detectadas or []) if isinstance(item, dict)
    ]
    nf_auditavel = nf
    if (
        not _nf_contexto_autorizado(nf)
        and len(nfs_detectadas) == 1
        and _nf_contexto_autorizado(nfs_detectadas[0])
    ):
        nf_auditavel = nfs_detectadas[0]
    nf_local_id = _text(nf.get("id"))
    nf_local_numero = _text(nf.get("numero"))
    movimentacoes_saida_nf = (
        movimentacoes_saida
        if movimentacoes_saida_nf is None
        else int(movimentacoes_saida_nf)
    )

    if not itens:
        incidentes.append(
            _make_incident(
                "PEDIDO_SEM_ITENS",
                severity="high",
                title="Pedido sem itens importados",
                message="O pedido foi registrado, mas nenhum item ficou salvo no sistema.",
                suggested_action="Reconsultar o pedido no Bling e recriar os itens/reservas.",
                auto_fixable=True,
                pedido=pedido,
                nf_bling_id=_text(nf.get("id")),
            )
        )

    for item_info in itens_sem_produto:
        sku = _text(item_info.get("sku"))
        incidentes.append(
            _make_incident(
                "SKU_SEM_PRODUTO_LOCAL",
                severity="critical",
                title="SKU sem produto local",
                message=f"O SKU '{sku}' do pedido nao foi encontrado no cadastro local.",
                suggested_action="Tentar autocadastro pelo Bling ou revisar o SKU do item.",
                auto_fixable=True,
                pedido=pedido,
                sku=sku,
                nf_bling_id=_text(nf.get("id")),
                details=item_info,
            )
        )

    for item_info in itens_mapeados_por_barra:
        sku = _text(item_info.get("sku"))
        incidentes.append(
            _make_incident(
                "SKU_MAPEADO_POR_CODIGO_BARRAS",
                severity="medium",
                title="SKU conciliado por codigo de barras",
                message=f"O item '{sku}' foi conciliado pelo codigo de barras, nao pelo SKU principal.",
                suggested_action="Revisar o padrao de SKU entre Bling e cadastro local para evitar divergencias.",
                auto_fixable=False,
                pedido=pedido,
                sku=sku,
                nf_bling_id=_text(nf.get("id")),
                details=item_info,
            )
        )

    itens_vendidos = [item for item in itens if getattr(item, "vendido_em", None)]

    if pedido.status == "confirmado" and _nf_contexto_autorizado(nf_auditavel):
        for item in itens:
            if not getattr(item, "vendido_em", None):
                incidentes.append(
                    _make_incident(
                        "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
                        severity="critical",
                        title="Pedido confirmado com item nao vendido",
                        message=f"O pedido esta confirmado, mas o item '{item.sku}' ainda nao foi consolidado como venda.",
                        suggested_action="Reconciliar o pedido confirmado e aplicar a baixa pendente.",
                        auto_fixable=True,
                        pedido=pedido,
                        sku=_text(item.sku),
                        nf_bling_id=_text(
                            _primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))
                        ),
                    )
                )

        if itens_vendidos and movimentacoes_saida_nf < len(itens_vendidos):
            incidentes.append(
                _make_incident(
                    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                    severity="critical",
                    title="Pedido confirmado sem baixa completa de estoque",
                    message=(
                        f"Existem {len(itens_vendidos)} item(ns) vendidos, mas apenas "
                        f"{movimentacoes_saida_nf} movimentacao(oes) de saida vinculada(s) a NF atual."
                    ),
                    suggested_action="Reconciliar as baixas pendentes do pedido confirmado.",
                    auto_fixable=True,
                    pedido=pedido,
                    nf_bling_id=_text(
                        _primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))
                    ),
                    details={
                        "nf_detectada": _json_safe(nf_auditavel),
                        "itens_vendidos": len(itens_vendidos),
                        "movimentacoes_saida": movimentacoes_saida,
                        "movimentacoes_saida_nf": movimentacoes_saida_nf,
                    },
                )
            )

    if pedido.status in {"cancelado", "expirado"}:
        for item in itens:
            if not getattr(item, "liberado_em", None) and not getattr(
                item, "vendido_em", None
            ):
                incidentes.append(
                    _make_incident(
                        "RESERVA_ATIVA_EM_PEDIDO_FINALIZADO",
                        severity="high",
                        title="Reserva ativa em pedido finalizado",
                        message=f"O item '{item.sku}' segue reservado em um pedido {pedido.status}.",
                        suggested_action="Liberar a reserva logica remanescente.",
                        auto_fixable=True,
                        pedido=pedido,
                        sku=_text(item.sku),
                        nf_bling_id=_text(nf.get("id")),
                    )
                )

    if pedido.status in {"aberto", "expirado"}:
        for item in itens_vendidos:
            incidentes.append(
                _make_incident(
                    "ITEM_VENDIDO_EM_PEDIDO_ABERTO",
                    severity="critical",
                    title="Item vendido em pedido ainda aberto",
                    message=f"O item '{item.sku}' aparece vendido, mas o pedido segue como {pedido.status}.",
                    suggested_action="Revisar o status do pedido e reconciliar a baixa aplicando o estado correto.",
                    auto_fixable=False,
                    pedido=pedido,
                    sku=_text(item.sku),
                    nf_bling_id=_text(nf.get("id")),
                )
            )

    if pedido.status in {"aberto", "expirado"} and nfs_detectadas:
        nfs_distintas = {
            (_text(item.get("id")) or "", _text(item.get("numero")) or ""): item
            for item in nfs_detectadas
        }
        nfs_encontradas = list(nfs_distintas.values())
        if len(nfs_encontradas) > 1:
            incidentes.append(
                _make_incident(
                    "NF_MULTIPLA_ENCONTRADA_POR_PEDIDO_LOJA",
                    severity="high",
                    title="Multiplas NFs encontradas para o mesmo pedido na loja",
                    message=(
                        "Foi encontrada mais de uma NF recente no Bling usando o mesmo numero do pedido na loja. "
                        "A conciliacao automatica foi bloqueada para evitar vinculo incorreto."
                    ),
                    suggested_action="Abrir o pedido e as NFs relacionadas para confirmar manualmente qual nota deve ser vinculada.",
                    auto_fixable=False,
                    pedido=pedido,
                    details={
                        "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
                        "nfs": _json_safe(nfs_encontradas),
                    },
                )
            )
        else:
            nf_detectada = nfs_encontradas[0]
            nf_detectada_id = _text(nf_detectada.get("id"))
            nf_detectada_numero = _text(nf_detectada.get("numero"))
            nf_ja_vinculada = bool(
                (nf_local_id and nf_detectada_id and nf_local_id == nf_detectada_id)
                or (
                    nf_local_numero
                    and nf_detectada_numero
                    and nf_local_numero == nf_detectada_numero
                )
            )

            if not nf_ja_vinculada:
                if _nf_detectada_combina_com_pedido(pedido, nf_detectada):
                    incidentes.append(
                        _make_incident(
                            "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
                            severity="critical",
                            title="NF encontrada no Bling mas ainda nao vinculada ao pedido",
                            message=(
                                "Foi encontrada uma NF recente no Bling com o mesmo numero do pedido na loja, "
                                "mas o pedido local ainda nao recebeu esse vinculo nem os efeitos de confirmacao."
                            ),
                            suggested_action="Vincular a NF detectada ao pedido e executar a reconciliacao automatica do estoque.",
                            auto_fixable=True,
                            pedido=pedido,
                            nf_bling_id=nf_detectada_id,
                            details={"nf_detectada": _json_safe(nf_detectada)},
                        )
                    )
                else:
                    incidentes.append(
                        _make_incident(
                            "NF_ENCONTRADA_COM_DIVERGENCIA_NO_PEDIDO",
                            severity="high",
                            title="NF encontrada com divergencia de contexto do pedido",
                            message=(
                                "Uma NF recente foi encontrada pelo numero do pedido na loja, mas ha divergencia "
                                "de canal ou total entre o pedido local e a nota detectada."
                            ),
                            suggested_action="Comparar o pedido e a NF antes de vincular manualmente.",
                            auto_fixable=False,
                            pedido=pedido,
                            nf_bling_id=nf_detectada_id,
                            details={
                                "numero_pedido_loja": _numero_pedido_loja_pedido(
                                    pedido
                                ),
                                "canal_pedido": _canal_pedido_integrado(pedido),
                                "total_pedido": _pedido_total(pedido),
                                "nf_detectada": _json_safe(nf_detectada),
                            },
                        )
                    )

    if _nf_autorizada(payload) and pedido.status != "confirmado":
        incidentes.append(
            _make_incident(
                "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
                severity="critical",
                title="NF autorizada sem confirmacao do pedido",
                message="Existe NF autorizada vinculada ao pedido, mas o pedido local ainda nao esta confirmado.",
                suggested_action="Reconciliar o pedido como confirmado e baixar o estoque pendente.",
                auto_fixable=True,
                pedido=pedido,
                nf_bling_id=_text(nf.get("id")),
                details={"nf": _json_safe(nf)},
            )
        )

    return incidentes
