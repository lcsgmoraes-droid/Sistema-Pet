from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.estoque_reserva_service import EstoqueReservaService
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao
from app.services.bling_flow_monitor_service import (
    abrir_incidente,
    registrar_evento,
    resolver_incidentes_relacionados,
)
from app.services.bling_nf.autocadastro import (
    _obter_usuario_padrao_tenant as _obter_usuario_padrao_tenant,
    criar_produto_automatico_do_bling as criar_produto_automatico_do_bling,
    criar_produto_automatico_do_bling_por_item as criar_produto_automatico_do_bling_por_item,
)
from app.services.bling_nf.common import (
    AUTO_CADASTRO_BING_TAG as AUTO_CADASTRO_BING_TAG,
    _text as _text,
)
from app.services.bling_nf.desvinculo import (
    _nf_cache_pertence_a_outro_pedido as _nf_cache_pertence_a_outro_pedido,
    _numero_nf_pedido as _numero_nf_pedido,
    _recarregar_pedido_e_itens_para_nf as _recarregar_pedido_e_itens_para_nf,
    _restaurar_lotes_consumidos as _restaurar_lotes_consumidos,
)
from app.services.bling_nf.estoque import (
    _consumir_movimentacoes_esperadas_lista as _consumir_movimentacoes_esperadas_lista,
    _normalizar_movimentacoes_legadas_para_nf as _normalizar_movimentacoes_legadas_para_nf,
    _sincronizar_cache_estoque_virtual as _sincronizar_cache_estoque_virtual,
    baixar_estoque_item_integrado as baixar_estoque_item_integrado,
    buscar_produto_do_item as buscar_produto_do_item,
    consumir_movimentacoes_esperadas as consumir_movimentacoes_esperadas,
    movimento_documentado_por_nf as movimento_documentado_por_nf,
    movimento_legado_pedido_para_nf as movimento_legado_pedido_para_nf,
    produto_ids_estoque_afetados as produto_ids_estoque_afetados,
    produto_usa_composicao_virtual as produto_usa_composicao_virtual,
)
from app.services.kit_estoque_service import KitEstoqueService
from app.utils.logger import logger


def desvincular_nf_de_pedido_incorreto(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str | None = None,
    nf_numero: str | None = None,
    pedido_bling_id_esperado: str | None = None,
) -> dict:
    from app.estoque.service import EstoqueService
    from app.integracao_bling_nf_routes import _remover_nf_do_pedido

    pedido, itens = _recarregar_pedido_e_itens_para_nf(db, pedido, itens)
    nf_id = _text(nf_id)
    nf_numero = _text(nf_numero) or _numero_nf_pedido(pedido, nf_id)
    pedido_bling_id_esperado = _text(pedido_bling_id_esperado)

    movimentos = (
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
    movimentos_nf = [
        mov
        for mov in movimentos
        if (
            movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id)
            or movimento_legado_pedido_para_nf(
                mov,
                pedido_bling_numero=pedido.pedido_bling_numero,
                nf_numero=nf_numero,
                nf_bling_id=nf_id,
            )
        )
    ]

    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)

    movimentos_cancelados = 0
    estornos_criados = 0
    itens_reabertos = 0
    lotes_restaurados = 0

    for movimentacao in movimentos_nf:
        lotes_restaurados += _restaurar_lotes_consumidos(db, movimentacao)

        user_id_movimentacao = (
            getattr(movimentacao, "user_id", None) or user_id_execucao
        )
        if not user_id_movimentacao:
            raise ValueError(
                f"Nenhum usuario valido disponivel para estornar a movimentacao {movimentacao.id} "
                f"do pedido {pedido.id}."
            )

        EstoqueService.estornar_estoque(
            produto_id=movimentacao.produto_id,
            quantidade=float(movimentacao.quantidade or 0),
            motivo="nf_vinculada_pedido_incorreto",
            referencia_id=pedido.id,
            referencia_tipo="pedido_integrado",
            user_id=user_id_movimentacao,
            db=db,
            tenant_id=pedido.tenant_id,
            documento=nf_numero or nf_id,
            observacao=(
                f"Estorno automatico por desvinculo da NF {nf_numero or nf_id} "
                f"do pedido incorreto {pedido.pedido_bling_numero or pedido.pedido_bling_id}"
            ),
        )
        for (
            kit_id,
            _estoque_virtual,
        ) in KitEstoqueService.recalcular_kits_que_usam_produto(
            db,
            movimentacao.produto_id,
        ).items():
            _sincronizar_cache_estoque_virtual(db, pedido.tenant_id, kit_id)

        movimentacao.status = "cancelado"
        observacao_original = (movimentacao.observacao or "").strip()
        complemento = (
            f"Desvinculada automaticamente da NF {nf_numero or nf_id} "
            f"(pedido correto {pedido_bling_id_esperado})"
            if pedido_bling_id_esperado
            else f"Desvinculada automaticamente da NF {nf_numero or nf_id}"
        )
        movimentacao.observacao = (
            f"{observacao_original} | {complemento}"
            if observacao_original and complemento not in observacao_original
            else complemento
        )
        db.add(movimentacao)
        movimentos_cancelados += 1
        estornos_criados += 1

    for item in itens:
        if getattr(item, "vendido_em", None):
            item.vendido_em = None
            db.add(item)
            itens_reabertos += 1

    vinculo_removido = _remover_nf_do_pedido(
        pedido,
        nf_id=nf_id,
        nf_numero=nf_numero,
    )
    db.add(pedido)

    return {
        "vinculo_removido": vinculo_removido,
        "movimentos_cancelados": movimentos_cancelados,
        "estornos_criados": estornos_criados,
        "itens_reabertos": itens_reabertos,
        "lotes_restaurados": lotes_restaurados,
        "nf_numero": nf_numero,
        "nf_bling_id": nf_id,
        "pedido_bling_id_esperado": pedido_bling_id_esperado,
    }


def _processar_nf_autorizada_legado(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str,
) -> str:
    pedido_bling_id = getattr(pedido, "pedido_bling_id", None)

    if pedido.status == "confirmado" and all(item.vendido_em for item in itens):
        return "venda_ja_confirmada"

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.now(timezone.utc)

    for item in itens:
        if item.vendido_em:
            continue

        EstoqueReservaService.confirmar_venda(db, item)

        try:
            from app.estoque.service import EstoqueService

            produto = buscar_produto_do_item(
                db=db,
                tenant_id=pedido.tenant_id,
                sku=item.sku,
            )

            if not produto:
                produto = criar_produto_automatico_do_bling(
                    db=db,
                    tenant_id=pedido.tenant_id,
                    sku=item.sku,
                )

            if produto:
                EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=float(item.quantidade),
                    motivo="venda_bling",
                    referencia_id=pedido.id,
                    referencia_tipo="pedido_integrado",
                    user_id=0,
                    db=db,
                    tenant_id=pedido.tenant_id,
                    documento=pedido.pedido_bling_numero,
                    observacao=f"Baixa automática via NF Bling #{nf_id}",
                )
            else:
                logger.warning(
                    f"⚠️  Produto com código/SKU '{item.sku}' não encontrado para baixa de estoque"
                )
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="runtime",
                    event_type="nf.baixa_estoque",
                    entity_type="nf",
                    status="error",
                    severity="critical",
                    message="Produto nao encontrado para baixa via NF",
                    error_message=f"SKU {item.sku} sem produto local",
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                )
                abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code="SKU_SEM_PRODUTO_LOCAL",
                    severity="critical",
                    title="SKU sem produto local",
                    message=f"O SKU '{item.sku}' nao foi encontrado ao processar a NF autorizada.",
                    suggested_action="Autocadastrar o produto pelo Bling e reconciliar a baixa pendente.",
                    auto_fixable=True,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                    details={"origem": "nf_autorizada"},
                    source="runtime",
                )

        except Exception as e:
            logger.warning(f"⚠️  Falha ao baixar estoque para SKU {item.sku}: {e}")
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="runtime",
                event_type="nf.baixa_estoque",
                entity_type="nf",
                status="error",
                severity="critical",
                message="Falha ao baixar estoque via NF autorizada",
                error_message=str(e),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
            )
            abrir_incidente(
                tenant_id=pedido.tenant_id,
                code="PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                severity="critical",
                title="Falha na baixa do estoque por NF",
                message=f"A NF autorizada nao conseguiu baixar o estoque do SKU '{item.sku}'.",
                suggested_action="Reconciliar o pedido confirmado e reaplicar a baixa faltante.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
                details={"erro": str(e)},
                source="runtime",
            )

    db.add(pedido)
    db.commit()
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="nf.processada",
        entity_type="nf",
        status="ok",
        severity="info",
        message="NF autorizada processada com reconciliacao de estoque",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
    )
    return "venda_confirmada"


def processar_nf_autorizada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str,
) -> str:
    pedido, itens = _recarregar_pedido_e_itens_para_nf(db, pedido, itens)
    pedido_bling_id = getattr(pedido, "pedido_bling_id", None)
    nf_numero = _numero_nf_pedido(pedido, nf_id)
    if not nf_numero and _text(nf_id):
        nf_numero = (
            db.query(BlingNotaFiscalCache.numero)
            .filter(
                BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
                BlingNotaFiscalCache.bling_id == _text(nf_id),
            )
            .order_by(
                BlingNotaFiscalCache.data_emissao.desc().nullslast(),
                BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
                BlingNotaFiscalCache.id.desc(),
            )
            .scalar()
        )
    pedido_ref_conflitante = _nf_cache_pertence_a_outro_pedido(
        db,
        tenant_id=pedido.tenant_id,
        nf_bling_id=nf_id,
        pedido_bling_id_atual=pedido_bling_id,
    )
    if pedido_ref_conflitante:
        resultado_desvinculo = desvincular_nf_de_pedido_incorreto(
            db=db,
            pedido=pedido,
            itens=itens,
            nf_id=nf_id,
            nf_numero=nf_numero,
            pedido_bling_id_esperado=pedido_ref_conflitante,
        )
        mensagem = (
            f"A NF {nf_numero or nf_id} pertence ao pedido Bling {pedido_ref_conflitante}, "
            f"nao ao pedido {pedido_bling_id}."
        )
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="runtime",
            event_type="nf.processada",
            entity_type="nf",
            status="error",
            severity="critical",
            message="Processamento da NF bloqueado por vinculo com outro pedido",
            error_message=mensagem,
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "nf_numero": nf_numero,
                "pedido_bling_id_esperado": pedido_ref_conflitante,
                "desvinculo": resultado_desvinculo,
            },
            auto_fix_applied=bool(
                resultado_desvinculo.get("vinculo_removido")
                or resultado_desvinculo.get("movimentos_cancelados")
            ),
        )
        resolver_incidentes_relacionados(
            db,
            tenant_id=pedido.tenant_id,
            codes=[
                "NF_VINCULADA_A_OUTRO_PEDIDO",
                "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
                "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
            ],
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            resolution_note="Vinculo incorreto da NF removido automaticamente.",
        )
        db.add(pedido)
        db.commit()
        return "nf_vinculada_outro_pedido"
    movimentos_existentes = (
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
    movimentos_nf_por_produto: dict[int, list[EstoqueMovimentacao]] = {}
    movimentos_legados_por_produto: dict[int, list[EstoqueMovimentacao]] = {}
    for mov in movimentos_existentes:
        produto_id_mov = getattr(mov, "produto_id", None)
        if not produto_id_mov:
            continue
        produto_id_int = int(produto_id_mov)
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id):
            movimentos_nf_por_produto.setdefault(produto_id_int, []).append(mov)
        elif movimento_legado_pedido_para_nf(
            mov,
            pedido_bling_numero=getattr(pedido, "pedido_bling_numero", None),
            nf_numero=nf_numero,
            nf_bling_id=nf_id,
        ):
            movimentos_legados_por_produto.setdefault(produto_id_int, []).append(mov)
    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)
    venda_ja_confirmada = pedido.status == "confirmado" and all(
        item.vendido_em for item in itens
    )
    itens_confirmados = 0
    baixas_criadas = 0
    baixas_normalizadas = 0
    houve_erros = False

    pedido.status = "confirmado"
    pedido.confirmado_em = pedido.confirmado_em or datetime.now(timezone.utc)

    for item in itens:
        try:
            produto = buscar_produto_do_item(
                db=db,
                tenant_id=pedido.tenant_id,
                sku=item.sku,
            )

            if not produto:
                produto = criar_produto_automatico_do_bling(
                    db=db,
                    tenant_id=pedido.tenant_id,
                    sku=item.sku,
                )

            if not produto:
                logger.warning(
                    f"Produto com codigo/SKU '{item.sku}' nao encontrado para baixa de estoque"
                )
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="runtime",
                    event_type="nf.baixa_estoque",
                    entity_type="nf",
                    status="error",
                    severity="critical",
                    message="Produto nao encontrado para baixa via NF",
                    error_message=f"SKU {item.sku} sem produto local",
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                )
                abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code="SKU_SEM_PRODUTO_LOCAL",
                    severity="critical",
                    title="SKU sem produto local",
                    message=f"O SKU '{item.sku}' nao foi encontrado ao processar a NF autorizada.",
                    suggested_action="Autocadastrar o produto pelo Bling e reconciliar a baixa pendente.",
                    auto_fixable=True,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                    details={"origem": "nf_autorizada"},
                    source="runtime",
                )
                houve_erros = True
                continue

            ids_esperados = produto_ids_estoque_afetados(db=db, produto=produto)
            movimentos_nf_existentes = _consumir_movimentacoes_esperadas_lista(
                ids_esperados,
                movimentos_nf_por_produto,
            )

            if movimentos_nf_existentes:
                if not item.vendido_em:
                    EstoqueReservaService.confirmar_venda(db, item)
                    itens_confirmados += 1
                continue

            movimentos_legados = _consumir_movimentacoes_esperadas_lista(
                ids_esperados,
                movimentos_legados_por_produto,
            )
            if movimentos_legados:
                baixas_normalizadas += _normalizar_movimentacoes_legadas_para_nf(
                    db,
                    movimentos_legados,
                    nf_numero=nf_numero,
                    nf_bling_id=nf_id,
                )
                if not item.vendido_em:
                    EstoqueReservaService.confirmar_venda(db, item)
                    itens_confirmados += 1
                continue

            resultado_baixa = baixar_estoque_item_integrado(
                db=db,
                tenant_id=pedido.tenant_id,
                produto=produto,
                quantidade=float(item.quantidade),
                motivo="venda_bling",
                referencia_id=pedido.id,
                referencia_tipo="pedido_integrado",
                user_id=user_id_execucao,
                documento=nf_numero,
                observacao=(
                    f"Baixa automatica via NF {nf_numero}"
                    if nf_numero
                    else f"Baixa automatica via NF Bling #{nf_id}"
                    if _text(nf_id)
                    else "Baixa automatica via NF autorizada do Bling"
                ),
            )
            movimentos_gerados = resultado_baixa.get("movimentos") or []
            if movimentos_gerados:
                for movimento in movimentos_gerados:
                    produto_id_mov = movimento.get("produto_id")
                    if produto_id_mov:
                        movimentos_nf_por_produto.setdefault(int(produto_id_mov), [])
                baixas_criadas += len(movimentos_gerados)
            else:
                baixas_criadas += 1

            if not item.vendido_em:
                EstoqueReservaService.confirmar_venda(db, item)
                itens_confirmados += 1

        except Exception as e:
            logger.warning(f"Falha ao baixar estoque para SKU {item.sku}: {e}")
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="runtime",
                event_type="nf.baixa_estoque",
                entity_type="nf",
                status="error",
                severity="critical",
                message="Falha ao baixar estoque via NF autorizada",
                error_message=str(e),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
            )
            abrir_incidente(
                tenant_id=pedido.tenant_id,
                code="PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                severity="critical",
                title="Falha na baixa do estoque por NF",
                message=f"A NF autorizada nao conseguiu baixar o estoque do SKU '{item.sku}'.",
                suggested_action="Reconciliar o pedido confirmado e reaplicar a baixa faltante.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
                details={"erro": str(e)},
                source="runtime",
            )
            houve_erros = True

    db.add(pedido)
    db.commit()
    incidentes_resolvidos = resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=[
            "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
            "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
            "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
        ],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
        resolution_note="Baixa de estoque reconciliada a partir da NF autorizada.",
    )
    if incidentes_resolvidos:
        db.commit()

    if (
        venda_ja_confirmada
        and itens_confirmados == 0
        and baixas_criadas == 0
        and baixas_normalizadas == 0
        and not houve_erros
    ):
        return "venda_ja_confirmada"

    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="nf.processada",
        entity_type="nf",
        status="ok",
        severity="info",
        message="NF autorizada processada com reconciliacao de estoque",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
    )
    return "venda_confirmada"


def processar_nf_cancelada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str | None = None,
) -> str:
    from app.estoque.service import EstoqueService

    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.now(timezone.utc)

    movimentos_ativos = (
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

    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)
    houve_estorno = False

    for movimentacao in movimentos_ativos:
        _restaurar_lotes_consumidos(db, movimentacao)

        user_id_movimentacao = (
            getattr(movimentacao, "user_id", None) or user_id_execucao
        )
        if not user_id_movimentacao:
            raise ValueError(
                f"Nenhum usuario valido disponivel para estornar a movimentacao de estoque do pedido {pedido.id}"
            )

        EstoqueService.estornar_estoque(
            produto_id=movimentacao.produto_id,
            quantidade=float(movimentacao.quantidade or 0),
            motivo="cancelamento_nf_bling",
            referencia_id=pedido.id,
            referencia_tipo="pedido_integrado",
            user_id=user_id_movimentacao,
            db=db,
            tenant_id=pedido.tenant_id,
            documento=pedido.pedido_bling_numero,
            observacao=(
                f"Estorno automatico por cancelamento da NF Bling #{nf_id or _numero_nf_pedido(pedido)}"
            ),
        )
        for (
            kit_id,
            _estoque_virtual,
        ) in KitEstoqueService.recalcular_kits_que_usam_produto(
            db,
            movimentacao.produto_id,
        ).items():
            _sincronizar_cache_estoque_virtual(db, pedido.tenant_id, kit_id)
        movimentacao.status = "cancelado"
        observacao_original = (movimentacao.observacao or "").strip()
        complemento = f"Cancelada pela NF Bling #{nf_id or _numero_nf_pedido(pedido)}"
        movimentacao.observacao = (
            f"{observacao_original} | {complemento}"
            if observacao_original and complemento not in observacao_original
            else complemento
        )
        db.add(movimentacao)
        houve_estorno = True

    for item in itens:
        item.vendido_em = None
        item.liberado_em = item.liberado_em or datetime.utcnow()
        db.add(item)

    db.add(pedido)
    db.commit()
    return "venda_cancelada_com_estorno" if houve_estorno else "venda_cancelada"
