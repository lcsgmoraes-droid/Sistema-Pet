"""Integracao de pedidos ecommerce/app com venda ERP apos pagamento aprovado."""

import hashlib
import json
import logging
from datetime import datetime
from uuid import UUID

from app.idempotency_models import IdempotencyKey
from app.models import Cliente, User
from app.pedido_models import Pedido, PedidoItem
from app.produtos_models import Produto
from app.services.sales_channel import (
    benefit_channel_from_sales_channel,
    normalize_sales_channel,
)
from app.tenancy.context import set_current_tenant

from .ecommerce_webhooks_payment import (
    PAYMENT_METHODS_ONLINE_ACEITOS,
    _extrair_financeiro_gateway_online,
    _extrair_pagamento_do_webhook,
    _normalizar_payment_method_online,
)

log = logging.getLogger(__name__)


def _normalizar_canal_venda_online(canal: str | None) -> str:
    return normalize_sales_channel(canal)


def _resolver_status_entrega_online(
    *,
    tem_entrega: bool,
    tipo_retirada: str | None,
    canal_origem: str | None,
) -> str | None:
    canal = normalize_sales_channel(canal_origem)
    if canal not in {"app", "ecommerce"}:
        return None

    if tem_entrega:
        return "entregue"

    retirada = str(tipo_retirada or "").strip().lower()
    if retirada in {"proprio", "terceiro", "app_loja"}:
        return "pendente"

    return None


def _mapear_forma_pagamento_ecommerce(
    payment_method: str,
    installments: int,
    tenant_id: str,
    db,
) -> tuple:
    """Mapeia payment_method online para uma forma de pagamento ativa."""
    from app.financeiro_models import FormaPagamento
    from sqlalchemy import func as sa_func

    payment_method = _normalizar_payment_method_online(payment_method)
    tipo = PAYMENT_METHODS_ONLINE_ACEITOS[payment_method]

    base_query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.tipo == tipo,
        FormaPagamento.ativo.is_(True),
    )

    forma = None
    if tipo == "cartao_credito":
        if installments > 1:
            forma = base_query.filter(
                sa_func.lower(FormaPagamento.nome).like("%parcela%")
            ).first()
        else:
            forma = base_query.filter(
                sa_func.lower(FormaPagamento.nome).like("%vista%")
            ).first()
            if not forma:
                forma = base_query.filter(
                    ~sa_func.lower(FormaPagamento.nome).like("%parcela%")
                ).first()

    if not forma:
        forma = base_query.first()

    if not forma:
        forma = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.tenant_id == tenant_id,
                FormaPagamento.tipo == "pix",
                FormaPagamento.ativo.is_(True),
            )
            .first()
        )

    if forma:
        return forma.nome, installments

    return "PIX", 1


def _registrar_pagamento_ecommerce(
    db,
    venda_row,
    tenant_id: str,
    webhook_payload: dict,
):
    from app.vendas_models import VendaPagamento

    payment_method, installments = _extrair_pagamento_do_webhook(webhook_payload)
    payment_method = _normalizar_payment_method_online(payment_method)
    forma_pag_nome, parcelas = _mapear_forma_pagamento_ecommerce(
        payment_method, installments, tenant_id, db
    )
    gateway_financials = _extrair_financeiro_gateway_online(webhook_payload)

    log.info(
        "Ecommerce pos-venda: venda #%s | pagamento='%s' (%sx) -> forma='%s' x%s",
        venda_row.id,
        payment_method,
        installments,
        forma_pag_nome,
        parcelas,
    )

    pagamento_obj = VendaPagamento(
        venda_id=venda_row.id,
        tenant_id=tenant_id,
        forma_pagamento=forma_pag_nome,
        valor=venda_row.total,
        numero_parcelas=parcelas,
        numero_transacao=gateway_financials.get("gateway_payment_id"),
        gateway_provider=gateway_financials.get("gateway_provider"),
        gateway_payment_id=gateway_financials.get("gateway_payment_id"),
        gateway_fee_amount=gateway_financials.get("gateway_fee_amount"),
        gateway_net_amount=gateway_financials.get("gateway_net_amount"),
        gateway_gross_amount=gateway_financials.get("gateway_gross_amount"),
    )
    db.add(pagamento_obj)
    db.flush()
    venda_row.rentabilidade_snapshot = None
    venda_row.rentabilidade_snapshot_em = None
    log.info(
        "VendaPagamento ecommerce criado: '%s' R$ %.2f",
        forma_pag_nome,
        float(venda_row.total),
    )
    return pagamento_obj, forma_pag_nome, parcelas


def _gerar_dre_ecommerce(db, venda_row, vendedor, tenant_id: str) -> None:
    try:
        from app.vendas.service import gerar_dre_competencia_venda

        resultado_dre = gerar_dre_competencia_venda(
            venda_id=venda_row.id,
            user_id=vendedor.id,
            tenant_id=tenant_id,
            db=db,
        )
        if resultado_dre.get("success"):
            log.info(
                "DRE ecommerce gerada: %s lancamentos, receita R$ %.2f",
                resultado_dre["lancamentos_criados"],
                resultado_dre.get("receita_gerada", 0),
            )
        else:
            log.info("DRE ecommerce: %s", resultado_dre.get("message"))
    except Exception as exc:
        log.error("Erro ao gerar DRE ecommerce: %s", exc, exc_info=True)


def _criar_contas_receber_ecommerce(
    db, venda_row, vendedor, forma_pag_nome: str, parcelas: int
) -> None:
    try:
        from app.financeiro import ContasReceberService

        ContasReceberService.criar_de_venda(
            venda=venda_row,
            pagamentos=[
                {
                    "forma_pagamento": forma_pag_nome,
                    "valor": float(venda_row.total),
                    "numero_parcelas": parcelas,
                }
            ],
            user_id=vendedor.id,
            db=db,
        )
        log.info("Contas a receber ecommerce criadas")
    except Exception as exc:
        log.error("Erro ao criar contas a receber ecommerce: %s", exc, exc_info=True)


def _criar_contas_pagar_taxas_ecommerce(
    db, venda_row, vendedor, tenant_id: str, pagamento_obj
) -> None:
    if pagamento_obj is None:
        return
    try:
        from app.vendas.service import processar_contas_pagar_taxas

        resultado_taxas = processar_contas_pagar_taxas(
            venda=venda_row,
            pagamentos=[pagamento_obj],
            user_id=vendedor.id,
            tenant_id=tenant_id,
            db=db,
        )
        if (
            resultado_taxas.get("success")
            and resultado_taxas.get("total_contas", 0) > 0
        ):
            log.info(
                "Contas a pagar taxas ecommerce: %s conta(s) | R$ %.2f",
                resultado_taxas["total_contas"],
                resultado_taxas["valor_total"],
            )
        else:
            log.info(
                "Taxas ecommerce: %s",
                resultado_taxas.get("detalhes")
                or resultado_taxas.get("error", "sem taxa configurada"),
            )
    except Exception as exc:
        log.error(
            "Erro ao criar contas a pagar taxas ecommerce: %s", exc, exc_info=True
        )


def _processar_pos_venda_ecommerce(
    db,
    venda_row,
    vendedor,
    tenant_id: str,
    webhook_payload: dict,
) -> None:
    """
    Executa os efeitos colaterais pos-venda para pedidos do ecommerce.
    Erros em cada etapa sao logados mas nao abortam o webhook.
    """
    pagamento_obj = None
    forma_pag_nome = "PIX"
    parcelas = 1
    try:
        pagamento_obj, forma_pag_nome, parcelas = _registrar_pagamento_ecommerce(
            db, venda_row, tenant_id, webhook_payload
        )
    except Exception as exc:
        log.error("Erro ao criar VendaPagamento ecommerce: %s", exc, exc_info=True)

    _gerar_dre_ecommerce(db, venda_row, vendedor, tenant_id)
    _criar_contas_receber_ecommerce(db, venda_row, vendedor, forma_pag_nome, parcelas)
    _criar_contas_pagar_taxas_ecommerce(
        db, venda_row, vendedor, tenant_id, pagamento_obj
    )


def _payload_metadata(payload_data: dict) -> tuple[dict, dict]:
    metadata = (
        (payload_data.get("metadata") or {}) if isinstance(payload_data, dict) else {}
    )
    nested_metadata = (
        ((payload_data.get("data") or {}).get("metadata") or {})
        if isinstance(payload_data, dict)
        else {}
    )
    return metadata, nested_metadata


def _resolver_entrega_webhook(
    payload_data: dict, metadata: dict, nested_metadata: dict
) -> tuple[bool, int | None, str | None]:
    entrega_mode = (
        str(
            metadata.get("delivery_mode")
            or nested_metadata.get("delivery_mode")
            or payload_data.get("delivery_mode")
            or ""
        )
        .strip()
        .lower()
    )
    endereco_entrega = (
        metadata.get("endereco_entrega")
        or nested_metadata.get("endereco_entrega")
        or payload_data.get("endereco_entrega")
    )
    tem_entrega_payload = metadata.get("tem_entrega")
    if tem_entrega_payload is None:
        tem_entrega_payload = nested_metadata.get("tem_entrega")
    if tem_entrega_payload is None:
        tem_entrega_payload = payload_data.get("tem_entrega")

    if tem_entrega_payload is None:
        if endereco_entrega and "retirada" in str(endereco_entrega).lower():
            tem_entrega = False
        else:
            tem_entrega = entrega_mode == "entrega"
    elif isinstance(tem_entrega_payload, str):
        tem_entrega = tem_entrega_payload.strip().lower() in {"1", "true", "yes", "sim"}
    else:
        tem_entrega = bool(tem_entrega_payload)

    entregador_payload = (
        metadata.get("entregador_id")
        or nested_metadata.get("entregador_id")
        or payload_data.get("entregador_id")
    )
    entregador_id = None
    if entregador_payload is not None:
        try:
            entregador_id = int(entregador_payload)
        except (TypeError, ValueError):
            entregador_id = None
    return tem_entrega, entregador_id, endereco_entrega


def _resolver_entregador_padrao(db, pedido: Pedido, tem_entrega: bool, entregador_id):
    if not tem_entrega or entregador_id:
        return entregador_id
    entregador_padrao = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == pedido.tenant_id,
            Cliente.entregador_padrao.is_(True),
            Cliente.entregador_ativo.is_(True),
            Cliente.ativo.is_(True),
        )
        .order_by(Cliente.id.asc())
        .first()
    )
    return entregador_padrao.id if entregador_padrao else None


def _venda_integrada_existente(db, pedido: Pedido, endpoint: str, chave: str):
    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == 0,
            IdempotencyKey.tenant_id == pedido.tenant_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.chave_idempotencia == chave,
            IdempotencyKey.status == "completed",
        )
        .first()
    )
    if existing and existing.response_body:
        try:
            previous = json.loads(existing.response_body)
            return int(previous.get("venda_id")) if previous.get("venda_id") else None
        except Exception:
            return None
    return None


def _selecionar_vendedor_ecommerce(db, pedido: Pedido, itens):
    primeiro_produto = (
        db.query(Produto)
        .filter(
            Produto.id == itens[0].produto_id, Produto.tenant_id == pedido.tenant_id
        )
        .first()
    )

    vendedor = None
    if primeiro_produto and primeiro_produto.user_id:
        vendedor = (
            db.query(User)
            .filter(
                User.id == primeiro_produto.user_id,
                User.tenant_id == pedido.tenant_id,
                User.is_active.is_(True),
            )
            .first()
        )

    if vendedor:
        return vendedor

    return (
        db.query(User)
        .filter(User.tenant_id == pedido.tenant_id, User.is_active.is_(True))
        .order_by(User.is_admin.desc(), User.id.asc())
        .first()
    )


def _resolver_cliente_venda(db, pedido: Pedido):
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == pedido.tenant_id,
            Cliente.user_id == pedido.cliente_id,
        )
        .first()
    )
    if cliente:
        return cliente

    usuario_cliente = (
        db.query(User)
        .filter(User.id == pedido.cliente_id, User.tenant_id == pedido.tenant_id)
        .first()
    )
    if not usuario_cliente:
        return None

    return (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == pedido.tenant_id,
            Cliente.email == usuario_cliente.email,
        )
        .first()
    )


def _itens_payload_venda(itens) -> list[dict]:
    return [
        {
            "tipo": "produto",
            "produto_id": item.produto_id,
            "servico_descricao": None,
            "quantidade": float(item.quantidade or 0),
            "preco_unitario": float(item.preco_unitario or 0),
            "desconto_item": 0,
            "subtotal": float(item.subtotal or 0),
            "lote_id": None,
            "pet_id": None,
            "is_kit": None,
        }
        for item in itens
    ]


def _publicar_evento_campanha(
    db, pedido: Pedido, venda_row, venda_id: int, cliente_id, canal_origem
):
    if not venda_id or not cliente_id:
        return
    try:
        from app.campaigns.models import CampaignEventQueue, EventOriginEnum

        canal_campanha = benefit_channel_from_sales_channel(canal_origem)
        evento_campanha = CampaignEventQueue(
            tenant_id=pedido.tenant_id,
            event_type="purchase_completed",
            event_origin=EventOriginEnum.user_action,
            event_depth=0,
            payload={
                "customer_id": cliente_id,
                "venda_id": venda_id,
                "venda_total": float(venda_row.total) if venda_row else 0,
                "canal": canal_campanha,
            },
        )
        db.add(evento_campanha)
        log.info(
            "[Campanhas] purchase_completed publicado venda_id=%d cliente_id=%d canal=%s",
            venda_id,
            cliente_id,
            canal_campanha,
        )
    except Exception as exc:
        log.error("[Campanhas] Erro ao publicar purchase_completed webhook: %s", exc)


def _registrar_integracao_venda(
    db, pedido: Pedido, endpoint: str, chave: str, venda_id
):
    registry = IdempotencyKey(
        user_id=0,
        tenant_id=pedido.tenant_id,
        endpoint=endpoint,
        chave_idempotencia=chave,
        request_hash=hashlib.sha256(chave.encode("utf-8")).hexdigest(),
        status="completed",
        response_status_code=200,
        response_body=json.dumps({"venda_id": venda_id}),
        completed_at=datetime.utcnow(),
    )
    db.add(registry)


def _integrar_venda_ao_motor(
    db, pedido: Pedido, webhook_payload: dict | None = None
) -> int | None:
    from app.vendas.service import VendaService
    from app.vendas_models import Venda

    set_current_tenant(UUID(str(pedido.tenant_id)))

    payload_data = webhook_payload or {}
    metadata, nested_metadata = _payload_metadata(payload_data)

    canal_origem = normalize_sales_channel(
        metadata.get("canal")
        or nested_metadata.get("canal")
        or payload_data.get("canal")
        or getattr(pedido, "origem", None)
        or "ecommerce"
    )
    origem_label = "app" if canal_origem == "app" else "e-commerce"
    tem_entrega, entregador_id, endereco_entrega = _resolver_entrega_webhook(
        payload_data, metadata, nested_metadata
    )
    entregador_id = _resolver_entregador_padrao(db, pedido, tem_entrega, entregador_id)

    integration_endpoint = "POST /api/ecommerce/integracao/venda"
    integration_key = f"ecommerce-venda:{pedido.pedido_id}"
    venda_existente = _venda_integrada_existente(
        db, pedido, integration_endpoint, integration_key
    )
    if venda_existente:
        return venda_existente

    itens = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.pedido_id).all()
    if not itens:
        return None

    vendedor = _selecionar_vendedor_ecommerce(db, pedido, itens)
    if not vendedor:
        return None

    cliente = _resolver_cliente_venda(db, pedido)
    cliente_id = cliente.id if cliente else None
    payload = {
        "cliente_id": cliente_id,
        "vendedor_id": vendedor.id,
        "funcionario_id": None,
        "itens": _itens_payload_venda(itens),
        "desconto_valor": 0,
        "desconto_percentual": 0,
        "observacoes": f"Pedido {origem_label} {pedido.pedido_id}",
        "tem_entrega": tem_entrega,
        "taxa_entrega": 0,
        "percentual_taxa_loja": 100,
        "percentual_taxa_entregador": 0,
        "entregador_id": entregador_id,
        "loja_origem": canal_origem,
        "endereco_entrega": endereco_entrega,
        "distancia_km": None,
        "valor_por_km": None,
        "observacoes_entrega": None,
        "canal": canal_origem,
        "tenant_id": str(pedido.tenant_id),
    }

    venda = VendaService.criar_venda(payload=payload, user_id=vendedor.id, db=db)
    venda_id = int(venda.get("id")) if venda.get("id") else None
    venda_row = None

    if venda_id:
        venda_row = (
            db.query(Venda)
            .filter(Venda.id == venda_id, Venda.tenant_id == pedido.tenant_id)
            .first()
        )
        if venda_row:
            venda_row.status = "finalizada"
            venda_row.data_finalizacao = datetime.utcnow()
            venda_row.tipo_retirada = pedido.tipo_retirada
            venda_row.palavra_chave_retirada = pedido.palavra_chave_retirada
            venda_row.canal = canal_origem
            venda_row.loja_origem = canal_origem
            status_entrega_online = _resolver_status_entrega_online(
                tem_entrega=bool(venda_row.tem_entrega),
                tipo_retirada=venda_row.tipo_retirada,
                canal_origem=canal_origem,
            )
            if status_entrega_online and not venda_row.status_entrega:
                venda_row.status_entrega = status_entrega_online
                if status_entrega_online == "entregue":
                    venda_row.data_entrega = venda_row.data_entrega or datetime.utcnow()

            _processar_pos_venda_ecommerce(
                db=db,
                venda_row=venda_row,
                vendedor=vendedor,
                tenant_id=str(pedido.tenant_id),
                webhook_payload=webhook_payload or {},
            )

        _publicar_evento_campanha(
            db, pedido, venda_row, venda_id, cliente_id, canal_origem
        )

    _registrar_integracao_venda(
        db, pedido, integration_endpoint, integration_key, venda_id
    )
    return venda_id
