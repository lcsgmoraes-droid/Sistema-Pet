import time

from sqlalchemy.orm import Session

from app.services.pedido_integrado_consolidation_service import pedido_esta_mesclado


def _routes_module():
    from app import integracao_bling_pedido_routes

    return integracao_bling_pedido_routes


def processar_pedido_bling_payload(body: dict, db: Session):
    """
    Processa webhooks de pedidos do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'order.created'|'order.updated'|'order.deleted', data: {...} }
    """
    routes = _routes_module()
    EstoqueReservaService = routes.EstoqueReservaService
    PedidoIntegrado = routes.PedidoIntegrado
    PedidoIntegradoItem = routes.PedidoIntegradoItem
    _SITUACOES_PEDIDO_ATENDIDO = routes._SITUACOES_PEDIDO_ATENDIDO
    _SITUACOES_PEDIDO_CANCELADO = routes._SITUACOES_PEDIDO_CANCELADO
    _cancelar_pedido = routes._cancelar_pedido
    _confirmar_pedido = routes._confirmar_pedido
    _consolidar_pedido_duplicado_por_numero_loja = (
        routes._consolidar_pedido_duplicado_por_numero_loja
    )
    _dict = routes._dict
    _montar_payload_pedido = routes._montar_payload_pedido
    _payload_principal = routes._payload_principal
    _primeiro_preenchido = routes._primeiro_preenchido
    _processar_nf_autorizada_vinculada_ao_pedido = (
        routes._processar_nf_autorizada_vinculada_ao_pedido
    )
    _resolver_canal_pedido = routes._resolver_canal_pedido
    _resumir_ultima_nf_do_pedido_bling = routes._resumir_ultima_nf_do_pedido_bling
    _resumir_ultima_nf_webhook = routes._resumir_ultima_nf_webhook
    _set_bling_request_tenant = routes._set_bling_request_tenant
    _sincronizar_nf_do_pedido = routes._sincronizar_nf_do_pedido
    _situacao_codigo_bling = routes._situacao_codigo_bling
    _texto = routes._texto
    _ultima_nf_payload_efetiva = routes._ultima_nf_payload_efetiva
    abrir_incidente = routes.abrir_incidente
    localizar_pedido_por_bling_id = routes.localizar_pedido_por_bling_id
    logger = routes.logger
    registrar_evento = routes.registrar_evento
    registrar_vinculo_nf_pedido = routes.registrar_vinculo_nf_pedido

    # Tenant fixo para webhooks (chamadas sem JWT)
    _tenant_uuid = _set_bling_request_tenant()

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "")  # ex: "order.created"
    event_date = body.get("date")
    data = body.get("data", body)  # fallback p/ payload legado sem envelope

    # ========================
    # EVENTO: NOTA FISCAL EMITIDA
    # Quando o Bling gera uma NF vinculada a um pedido de marketplace,
    # confirmar o pedido e baixar o estoque imediatamente.
    # ========================
    if (
        "notafiscal" in event.lower()
        or "nota_fiscal" in event.lower()
        or event.startswith("nfe.")
        or event.startswith("nfce.")
    ):
        nf_data = data or {}
        # O pedido pode vir na chave "pedido" ou "pedidoVenda" do payload da NF
        pedido_ref = nf_data.get("pedido") or nf_data.get("pedidoVenda") or {}
        pedido_numero_nf = str(
            pedido_ref.get("numero") or pedido_ref.get("id") or ""
        ).strip()
        nf_id_bling = str(nf_data.get("id") or "").strip()

        if pedido_numero_nf or nf_id_bling:
            pedido = None
            # Buscar pelo número do pedido Bling (campo pedido_bling_numero)
            if pedido_numero_nf:
                pedido = (
                    db.query(PedidoIntegrado)
                    .filter(PedidoIntegrado.pedido_bling_numero == pedido_numero_nf)
                    .first()
                )
            # Fallback: buscar pela chave do pedido se vier como ID
            if not pedido and pedido_numero_nf:
                pedido = localizar_pedido_por_bling_id(
                    db,
                    tenant_id=_tenant_uuid,
                    pedido_bling_id=pedido_numero_nf,
                )

            if pedido and pedido.status not in ("confirmado", "cancelado"):
                status_anterior = pedido.status
                nf_resumo = _resumir_ultima_nf_webhook(
                    {
                        **_dict(nf_data),
                        "id": nf_id_bling or _dict(nf_data).get("id"),
                    }
                )
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="webhook",
                    event_type=event or "nf.webhook",
                    entity_type="nf",
                    status="received",
                    severity="info",
                    message="Webhook de NF vinculado a pedido recebido no endpoint de pedidos",
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido.pedido_bling_id,
                    nf_bling_id=nf_id_bling,
                    payload=nf_data,
                    processed_at=event_date,
                )
                itens = (
                    db.query(PedidoIntegradoItem)
                    .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                    .all()
                )
                pedido.payload = _montar_payload_pedido(
                    webhook_data=_dict((pedido.payload or {})).get("webhook"),
                    pedido_completo=_payload_principal(pedido.payload),
                    payload_atual=pedido.payload,
                    ultima_nf=nf_resumo,
                )
                registrar_vinculo_nf_pedido(
                    pedido=pedido,
                    source="webhook",
                    nf_bling_id=nf_id_bling,
                    nf_numero=nf_resumo.get("numero"),
                    message="NF recebida no endpoint de pedidos e vinculada ao pedido local.",
                    payload={
                        "link_source": "pedido.webhook",
                        "pedido_status_antes": status_anterior,
                        "pedido_status_atual": pedido.status,
                    },
                    processed_at=event_date,
                    db=db,
                )
                if nf_id_bling and nf_id_bling not in {"0", "-1"}:
                    from app.services.bling_nf_service import processar_nf_autorizada

                    acao = processar_nf_autorizada(
                        db=db,
                        pedido=pedido,
                        itens=itens,
                        nf_id=nf_id_bling,
                    )
                    logger.info(
                        f"[BLING NF WEBHOOK] Pedido {pedido.pedido_bling_id} consolidado via NF ({event})"
                    )
                    return {"status": "ok", "acao": acao, "erros_estoque": []}

                _confirmar_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    motivo="pedido_com_nf_sem_id",
                    observacao=f"Pedido confirmado por evento NF sem identificador deterministico ({event})",
                    processed_at=event_date,
                    aplicar_baixa_estoque=False,
                )
                logger.warning(
                    f"[BLING NF WEBHOOK] Pedido {pedido.pedido_bling_id} recebeu evento NF sem id deterministico; estoque mantido aguardando reconciliação"
                )
                return {
                    "status": "ok",
                    "acao": "aguardando_nf_deterministica",
                    "erros_estoque": [],
                }

        if _tenant_uuid:
            registrar_evento(
                tenant_id=_tenant_uuid,
                source="webhook",
                event_type=event or "nf.webhook",
                entity_type="nf",
                status="warning",
                severity="high",
                message="Evento de NF recebido sem pedido correspondente no fluxo de pedidos",
                nf_bling_id=nf_id_bling,
                payload=nf_data,
                processed_at=event_date,
            )
        return {
            "status": "ignorado",
            "motivo": f"evento_nf_sem_pedido_correspondente ({event})",
        }

    pedido_bling_id = str(data.get("id", ""))
    if not pedido_bling_id or pedido_bling_id == "None":
        return {"status": "ignorado", "motivo": "sem_id"}

    if _tenant_uuid:
        registrar_evento(
            tenant_id=_tenant_uuid,
            source="webhook",
            event_type=event or "order.webhook",
            entity_type="pedido",
            status="received",
            severity="info",
            message="Webhook de pedido recebido; o sistema vai analisar o status e aplicar os proximos passos.",
            pedido_bling_id=pedido_bling_id,
            payload=data,
            processed_at=event_date,
        )

    # ========================
    # EVENTO: EXCLUÍDO
    # ========================
    if event.endswith(".deleted"):
        pedido_exato = localizar_pedido_por_bling_id(
            db,
            tenant_id=_tenant_uuid,
            pedido_bling_id=pedido_bling_id,
            resolver_mescla=False,
        )
        if pedido_exato and pedido_esta_mesclado(pedido_exato):
            return {"status": "ignorado", "motivo": "pedido_duplicado_mesclado"}

        pedido = localizar_pedido_por_bling_id(
            db,
            tenant_id=_tenant_uuid,
            pedido_bling_id=pedido_bling_id,
        )
        if pedido and pedido.status != "cancelado":
            itens = (
                db.query(PedidoIntegradoItem)
                .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                .all()
            )
            _cancelar_pedido(db=db, pedido=pedido, itens=itens, processed_at=event_date)

        return {"status": "ok", "acao": "cancelado"}

    # ========================
    # EVENTO: ATUALIZADO — checar situação no Bling
    # ========================
    if event.endswith(".updated"):
        situacao_id = _situacao_codigo_bling(data.get("situacao"))
        pedido_api = None
        situacao_id_api = None

        if (
            situacao_id
            and situacao_id
            in (_SITUACOES_PEDIDO_CANCELADO | _SITUACOES_PEDIDO_ATENDIDO)
        ) or not situacao_id:
            try:
                from app.bling_integration import BlingAPI

                pedido_api = BlingAPI().consultar_pedido(pedido_bling_id)
                situacao_id_api = _situacao_codigo_bling(pedido_api.get("situacao"))
            except Exception as e:
                logger.warning(
                    f"[BLING WEBHOOK] Falha ao consultar pedido {pedido_bling_id} na API: {e}"
                )

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_CANCELADO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = (
                    db.query(PedidoIntegradoItem)
                    .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                    .all()
                )
                _sincronizar_nf_do_pedido(
                    db=db,
                    pedido=pedido,
                    pedido_payload=pedido_api or data,
                    webhook_data=data,
                    processed_at=event_date,
                    source="webhook",
                    message="NF identificada no pedido atualizado e vinculada localmente.",
                    link_source="pedido.updated",
                )
                _cancelar_pedido(
                    db=db, pedido=pedido, itens=itens, processed_at=event_date
                )
                logger.info(
                    f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado (situacao_id={situacao_id})"
                )

            return {"status": "ok", "acao": "cancelado_por_situacao"}

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_ATENDIDO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = (
                    db.query(PedidoIntegradoItem)
                    .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                    .all()
                )
                resumo_nf = _sincronizar_nf_do_pedido(
                    db=db,
                    pedido=pedido,
                    pedido_payload=pedido_api or data,
                    webhook_data=data,
                    processed_at=event_date,
                    source="webhook",
                    message="NF identificada no pedido atualizado e vinculada localmente.",
                    link_source="pedido.updated",
                )
                acao_nf = _processar_nf_autorizada_vinculada_ao_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    resumo_nf=resumo_nf,
                )
                if acao_nf:
                    logger.info(
                        f"[BLING WEBHOOK] Pedido {pedido_bling_id} consolidado por NF autorizada vinculada ao pedido (situacao_id={situacao_id})"
                    )
                    return {"status": "ok", "acao": acao_nf, "erros_estoque": []}

                _confirmar_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    motivo="venda_bling_webhook",
                    observacao="Pedido atendido no Bling; venda aguardando NF",
                    processed_at=event_date,
                    aplicar_baixa_estoque=False,
                )
                logger.info(
                    f"[BLING WEBHOOK] Pedido {pedido_bling_id} confirmado sem baixa de estoque; aguardando NF (situacao_id={situacao_id})"
                )

            return {"status": "ok", "acao": "confirmado_por_situacao"}

        if situacao_id_api and situacao_id_api in _SITUACOES_PEDIDO_CANCELADO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = (
                    db.query(PedidoIntegradoItem)
                    .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                    .all()
                )
                _sincronizar_nf_do_pedido(
                    db=db,
                    pedido=pedido,
                    pedido_payload=pedido_api,
                    webhook_data=data,
                    processed_at=event_date,
                    source="webhook",
                    message="NF identificada via consulta da API do Bling e vinculada localmente.",
                    link_source="pedido.updated.api",
                )
                pedido.payload = _montar_payload_pedido(
                    webhook_data=data,
                    pedido_completo=pedido_api,
                    payload_atual=pedido.payload,
                    ultima_nf=_ultima_nf_payload_efetiva(pedido.payload) or None,
                )
                _cancelar_pedido(
                    db=db, pedido=pedido, itens=itens, processed_at=event_date
                )
                logger.info(
                    f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado via consulta API (situacao_id={situacao_id_api})"
                )

            return {"status": "ok", "acao": "cancelado_via_consulta_api"}

        if situacao_id_api and situacao_id_api in _SITUACOES_PEDIDO_ATENDIDO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = (
                    db.query(PedidoIntegradoItem)
                    .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                    .all()
                )
                resumo_nf = _sincronizar_nf_do_pedido(
                    db=db,
                    pedido=pedido,
                    pedido_payload=pedido_api,
                    webhook_data=data,
                    processed_at=event_date,
                    source="webhook",
                    message="NF identificada via consulta da API do Bling e vinculada localmente.",
                    link_source="pedido.updated.api",
                )
                acao_nf = _processar_nf_autorizada_vinculada_ao_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    resumo_nf=resumo_nf,
                )
                if acao_nf:
                    logger.info(
                        f"[BLING WEBHOOK] Pedido {pedido_bling_id} consolidado por NF autorizada vinculada via consulta API (situacao_id={situacao_id_api})"
                    )
                    return {"status": "ok", "acao": acao_nf, "erros_estoque": []}

                pedido.payload = _montar_payload_pedido(
                    webhook_data=data,
                    pedido_completo=pedido_api,
                    payload_atual=pedido.payload,
                    ultima_nf=_ultima_nf_payload_efetiva(pedido.payload) or None,
                )
                if pedido.status != "confirmado":
                    _confirmar_pedido(
                        db=db,
                        pedido=pedido,
                        itens=itens,
                        motivo="venda_bling_webhook",
                        observacao="Pedido atendido via API do Bling; venda aguardando NF",
                        processed_at=event_date,
                        aplicar_baixa_estoque=False,
                    )
                    logger.info(
                        f"[BLING WEBHOOK] Pedido {pedido_bling_id} confirmado via consulta API sem baixa; aguardando NF (situacao_id={situacao_id_api})"
                    )
                else:
                    db.add(pedido)
                    db.commit()

            return {"status": "ok", "acao": "confirmado_via_consulta_api"}

        return {"status": "ignorado", "motivo": "order_updated_sem_situacao_relevante"}

    # ========================
    # EVENTO: CRIADO
    # ========================
    # Idempotência
    existente = localizar_pedido_por_bling_id(
        db,
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        resolver_mescla=False,
    )
    if existente:
        motivo = (
            "pedido_ja_mesclado"
            if pedido_esta_mesclado(existente)
            else "pedido_ja_existe"
        )
        return {"status": "ignorado", "motivo": motivo}

    numero = data.get("numero")
    loja_data = data.get("loja", {}) if isinstance(data.get("loja"), dict) else {}
    loja_id = loja_data.get("id", 0)
    loja_nome = loja_data.get("nome", "")
    canal_bruto = loja_nome or (str(loja_id) if loja_id else "online")

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
            logger.warning(
                f"[BLING WEBHOOK] Pedido {pedido_bling_id}: itens vazios após 3 tentativas"
            )
            if _tenant_uuid:
                abrir_incidente(
                    tenant_id=_tenant_uuid,
                    code="PEDIDO_SEM_ITENS",
                    severity="high",
                    title="Pedido chegou sem itens",
                    message="O pedido foi criado no sistema, mas o Bling retornou a consulta sem itens.",
                    suggested_action="Reconsultar o pedido no Bling e recriar os itens/reservas.",
                    auto_fixable=True,
                    pedido_bling_id=pedido_bling_id,
                    details={"event": event},
                )
    except Exception as e:
        logger.warning(
            f"[BLING WEBHOOK] Falha ao buscar itens do pedido {pedido_bling_id}: {e}"
        )

    if not _tenant_uuid:
        logger.error(
            "[BLING WEBHOOK] BLING_WEBHOOK_TENANT_ID não configurado — pedido ignorado"
        )
        return {"status": "erro", "motivo": "tenant_nao_configurado"}

    # Verificar situação atual no Bling — se já cancelado, não criar como aberto
    situacao_id_criacao = _situacao_codigo_bling(
        pedido_completo.get("situacao") if pedido_completo else None
    )

    if situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_CANCELADO:
        logger.info(
            f"[BLING WEBHOOK] Pedido {pedido_bling_id} order.created mas já cancelado (situacao_id={situacao_id_criacao}) — ignorado"
        )
        return {"status": "ignorado", "motivo": "order_created_ja_cancelado"}

    status_inicial = (
        "confirmado"
        if (situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_ATENDIDO)
        else "aberto"
    )
    resumo_nf_pedido = _resumir_ultima_nf_do_pedido_bling(pedido_completo or data)
    payload_pedido = _montar_payload_pedido(
        webhook_data=data,
        pedido_completo=pedido_completo or data,
        ultima_nf=resumo_nf_pedido,
    )
    canal, _, _ = _resolver_canal_pedido(payload_pedido, canal_bruto)

    pedido_consolidado = _consolidar_pedido_duplicado_por_numero_loja(
        db,
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=numero,
        canal=canal,
        status_inicial=status_inicial,
        payload_pedido=payload_pedido,
        itens_bling=itens_bling,
        event=event,
        event_date=event_date,
    )
    if pedido_consolidado:
        if status_inicial == "confirmado" and pedido_consolidado.status not in (
            "confirmado",
            "cancelado",
        ):
            itens_salvos = (
                db.query(PedidoIntegradoItem)
                .filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido_consolidado.id
                )
                .all()
            )
            _confirmar_pedido(
                db=db,
                pedido=pedido_consolidado,
                itens=itens_salvos,
                motivo="venda_bling_webhook_duplicado",
                observacao="Pedido duplicado no Bling consolidado no pedido canonico; venda aguardando NF",
                processed_at=event_date,
                aplicar_baixa_estoque=False,
            )
        return {
            "status": "ok",
            "pedido_id": pedido_consolidado.id,
            "acao": "pedido_duplicado_mesclado",
        }

    pedido = PedidoIntegrado(
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=numero,
        canal=canal,
        status=status_inicial,
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload=payload_pedido,
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
            quantidade=quantidade,
        )

        try:
            EstoqueReservaService.reservar(db, item_pedido)
        except ValueError as e:
            # Produto não cadastrado no sistema ainda — salva o item sem reserva
            logger.warning(f"[BLING WEBHOOK] Reserva não criada para SKU {sku}: {e}")
            abrir_incidente(
                tenant_id=_tenant_uuid,
                code="SKU_SEM_PRODUTO_LOCAL",
                severity="critical",
                title="SKU sem produto local",
                message=f"O SKU '{sku}' nao foi encontrado ao criar a reserva do pedido.",
                suggested_action="Tentar autocadastro do produto e reconciliar o pedido.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
                sku=sku,
                details={"evento": event, "descricao": descricao},
            )

        db.add(item_pedido)

    db.commit()
    registrar_evento(
        tenant_id=_tenant_uuid,
        source="webhook",
        event_type=event or "order.created",
        entity_type="pedido",
        status="ok",
        severity="info",
        message="Pedido Bling criado/importado no sistema e pronto para acompanhar o fluxo de NF e estoque.",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        payload={
            "status_inicial": status_inicial,
            "itens_importados": len(itens_bling),
            "numero_pedido_loja": _texto(
                _primeiro_preenchido(
                    _payload_principal(payload_pedido).get("numeroPedidoLoja"),
                    _payload_principal(payload_pedido).get("numeroLoja"),
                )
            ),
        },
        processed_at=event_date,
    )

    # Se o pedido já nasceu "confirmado" (NF emitida no Bling antes do webhook order.updated),
    # deduzir estoque imediatamente — sem essa baixa, o estoque nunca seria ajustado.
    if status_inicial == "confirmado":
        if resumo_nf_pedido:
            registrar_vinculo_nf_pedido(
                pedido=pedido,
                source="webhook",
                nf_bling_id=resumo_nf_pedido.get("id"),
                nf_numero=resumo_nf_pedido.get("numero"),
                message="Pedido criado ja com NF no Bling; vinculo consolidado no primeiro processamento.",
                payload={
                    "link_source": "pedido.created",
                    "pedido_status_atual": pedido.status,
                },
                processed_at=event_date,
                db=db,
            )
        itens_salvos = (
            db.query(PedidoIntegradoItem)
            .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
            .all()
        )
        _confirmar_pedido(
            db=db,
            pedido=pedido,
            itens=itens_salvos,
            motivo="venda_bling_webhook",
            observacao="Pedido criado ja atendido no Bling; venda aguardando NF",
            processed_at=event_date,
            aplicar_baixa_estoque=False,
        )
        logger.info(
            f"[BLING WEBHOOK] Pedido {pedido_bling_id} (order.created ja Atendido) confirmado sem baixa; aguardando NF"
        )

    return {"status": "ok", "pedido_id": pedido.id}
