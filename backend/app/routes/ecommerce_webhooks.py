import hashlib
import hmac
import json
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.db.session import SessionLocal
from app.idempotency_models import IdempotencyKey
from app.models import Cliente, User
from app.pedido_models import Pedido, PedidoItem
from app.produtos_models import Produto


router = APIRouter(prefix="/webhooks", tags=["ecommerce-webhooks"])


def _get_signature_config() -> tuple[str, bool]:
    secret = (os.getenv("PAGARME_WEBHOOK_SECRET", "") or "").strip()
    validate_raw = (os.getenv("PAGARME_WEBHOOK_VALIDATE_SIGNATURE", "false") or "").strip().lower()
    validate = validate_raw in {"1", "true", "yes", "on"}
    return secret, validate


def _find_tenant_id(payload: dict, request: Request) -> str:
    candidates = [
        payload.get("tenant_id"),
        payload.get("tenantId"),
        (payload.get("metadata") or {}).get("tenant_id"),
        (payload.get("metadata") or {}).get("tenantId"),
        ((payload.get("data") or {}).get("metadata") or {}).get("tenant_id"),
        ((payload.get("data") or {}).get("metadata") or {}).get("tenantId"),
        request.headers.get("X-Tenant-ID"),
    ]

    for value in candidates:
        if not value:
            continue
        try:
            return str(UUID(str(value)))
        except Exception:
            continue

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="tenant_id obrigatório (payload metadata.tenant_id ou header X-Tenant-ID)",
    )


def _extract_event_info(payload: dict, raw_body: bytes) -> tuple[str, str, str]:
    event_type = str(payload.get("type") or payload.get("event") or "unknown")

    event_id = (
        payload.get("id")
        or (payload.get("data") or {}).get("id")
        or (payload.get("data") or {}).get("event_id")
    )

    if not event_id:
        event_id = hashlib.sha256(raw_body).hexdigest()

    request_hash = hashlib.sha256(raw_body).hexdigest()
    return str(event_id), event_type, request_hash


def _validate_optional_signature(raw_body: bytes, request: Request) -> str:
    secret, validate_signature = _get_signature_config()

    if not validate_signature:
        return "skipped_by_config"

    if not secret:
        return "skipped_not_configured"

    signature_header = (
        request.headers.get("X-Hub-Signature")
        or request.headers.get("X-PagarMe-Signature")
        or ""
    ).strip()

    if not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura do webhook ausente")

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=")[-1].strip()

    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura do webhook inválida")

    return "validated"


def _map_payment_status(payload: dict) -> str | None:
    status_value = (
        payload.get("status")
        or (payload.get("data") or {}).get("status")
        or (payload.get("payment") or {}).get("status")
    )

    if not status_value:
        return None

    raw = str(status_value).strip().lower()
    mapping = {
        "paid": "aprovado",
        "authorized": "pendente",
        "processing": "pendente",
        "pending": "pendente",
        "waiting_payment": "pendente",
        "refused": "recusado",
        "failed": "recusado",
        "canceled": "cancelado",
        "cancelled": "cancelado",
        "chargedback": "cancelado",
    }
    return mapping.get(raw)


def _find_pedido_id(payload: dict) -> str | None:
    return (
        payload.get("pedido_id")
        or (payload.get("metadata") or {}).get("pedido_id")
        or ((payload.get("data") or {}).get("metadata") or {}).get("pedido_id")
    )


def _extrair_pagamento_do_webhook(payload: dict) -> tuple:
    """
    Extrai payment_method e installments do payload do Pagar.me.
    Suporta tanto o webhook real (com charges[]) quanto simulações com metadata.

    Returns:
        tuple: (payment_method: str, installments: int)
        payment_method values: "pix", "credit_card", "debit_card", "boleto"
    """
    data = payload.get("data") or {}
    metadata = payload.get("metadata") or data.get("metadata") or {}
    charges = data.get("charges") or payload.get("charges") or []

    payment_method = None
    installments = 1

    # 1. Estrutura real do Pagar.me: data.charges[0]
    if charges and isinstance(charges, list):
        charge = charges[0]
        if isinstance(charge, dict):
            payment_method = charge.get("payment_method")
            last_tx = charge.get("last_transaction") or {}
            if isinstance(last_tx, dict):
                try:
                    installments = int(last_tx.get("installments") or 1)
                except (TypeError, ValueError):
                    installments = 1

    # 2. Fallback: metadata / campos raiz (webhook simulado ou campos customizados)
    if not payment_method:
        payment_method = (
            metadata.get("payment_method")
            or metadata.get("metodo_pagamento")
            or payload.get("payment_method")
            or payload.get("metodo_pagamento")
        )

    if installments == 1:
        try:
            raw = (
                metadata.get("installments")
                or metadata.get("parcelas")
                or payload.get("installments")
                or payload.get("parcelas")
                or 1
            )
            installments = max(1, int(raw))
        except (TypeError, ValueError):
            installments = 1

    return str(payment_method or "pix").strip().lower(), installments


def _mapear_forma_pagamento_ecommerce(
    payment_method: str,
    installments: int,
    tenant_id: str,
    db,
) -> tuple:
    """
    Mapeia o payment_method do Pagar.me para o FormaPagamento cadastrado no sistema.
    Prioriza: tipo exato → nome contendo a variação → qualquer do tipo → PIX.

    Returns:
        tuple: (forma_pagamento_nome: str, parcelas: int)
    """
    from app.financeiro_models import FormaPagamento
    from sqlalchemy import func as sa_func

    tipo_map = {
        "pix": "pix",
        "credit_card": "cartao_credito",
        "debit_card": "cartao_debito",
        "boleto": "boleto",
        "bank_slip": "boleto",
        "transfer": "transferencia",
        "voucher": "cartao_credito",
    }
    tipo = tipo_map.get(payment_method, "pix")

    base_query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.tipo == tipo,
        FormaPagamento.ativo == True,
    )

    forma = None
    if tipo == "cartao_credito":
        if installments > 1:
            # Preferir a forma que contenha "parcela" no nome
            forma = base_query.filter(
                sa_func.lower(FormaPagamento.nome).like("%parcela%")
            ).first()
        else:
            # Preferir a forma que contenha "vista" no nome
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
        # Fallback final: qualquer forma de PIX ativa
        forma = db.query(FormaPagamento).filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.tipo == "pix",
            FormaPagamento.ativo == True,
        ).first()

    if forma:
        return forma.nome, installments

    return "PIX", 1


def _processar_pos_venda_ecommerce(
    db,
    venda_row,
    vendedor,
    tenant_id: str,
    webhook_payload: dict,
) -> None:
    """
    Executa os efeitos colaterais pós-venda para pedidos do ecommerce, espelhando
    o que acontece quando uma venda é finalizada no PDV:

      1. Cria VendaPagamento com a forma correta (extraída do webhook Pagar.me)
      2. Gera DRE por competência (receita + CMV + desconto)
      3. Cria Contas a Receber
      4. Cria Contas a Pagar para taxas da operadora (ex: taxa PIX, taxa cartão)

    Erros em cada etapa são logados mas NÃO abortam o fluxo.
    """
    import logging
    log = logging.getLogger(__name__)

    from app.vendas_models import VendaPagamento

    payment_method, installments = _extrair_pagamento_do_webhook(webhook_payload)
    forma_pag_nome, parcelas = _mapear_forma_pagamento_ecommerce(
        payment_method, installments, tenant_id, db
    )

    log.info(
        f"💳 Ecommerce pós-venda: venda #{venda_row.id} | "
        f"pagamento='{payment_method}' ({installments}x) → forma='{forma_pag_nome}' x{parcelas}"
    )

    # ─── 1. VendaPagamento ────────────────────────────────────────────────────
    pagamento_obj = None
    try:
        pagamento_obj = VendaPagamento(
            venda_id=venda_row.id,
            tenant_id=tenant_id,
            forma_pagamento=forma_pag_nome,
            valor=venda_row.total,
            numero_parcelas=parcelas,
        )
        db.add(pagamento_obj)
        db.flush()
        log.info(f"  ✅ VendaPagamento criado: '{forma_pag_nome}' R$ {float(venda_row.total):.2f}")
    except Exception as e:
        log.error(f"  ❌ Erro ao criar VendaPagamento (ecommerce): {e}", exc_info=True)

    # ─── 2. DRE por competência ───────────────────────────────────────────────
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
                f"  ✅ DRE gerada: {resultado_dre['lancamentos_criados']} lançamentos, "
                f"receita R$ {resultado_dre.get('receita_gerada', 0):.2f}"
            )
        else:
            log.info(f"  ℹ️  DRE: {resultado_dre.get('message')}")
    except Exception as e:
        log.error(f"  ❌ Erro ao gerar DRE (ecommerce): {e}", exc_info=True)

    # ─── 3. Contas a Receber ──────────────────────────────────────────────────
    try:
        from app.financeiro import ContasReceberService
        ContasReceberService.criar_de_venda(
            venda=venda_row,
            pagamentos=[{
                "forma_pagamento": forma_pag_nome,
                "valor": float(venda_row.total),
                "numero_parcelas": parcelas,
            }],
            user_id=vendedor.id,
            db=db,
        )
        log.info("  ✅ Contas a receber criadas")
    except Exception as e:
        log.error(f"  ❌ Erro ao criar contas a receber (ecommerce): {e}", exc_info=True)

    # ─── 4. Contas a Pagar — taxas da operadora (PIX/cartão) ─────────────────
    if pagamento_obj is not None:
        try:
            from app.vendas.service import processar_contas_pagar_taxas
            resultado_taxas = processar_contas_pagar_taxas(
                venda=venda_row,
                pagamentos=[pagamento_obj],
                user_id=vendedor.id,
                tenant_id=tenant_id,
                db=db,
            )
            if resultado_taxas.get("success") and resultado_taxas.get("total_contas", 0) > 0:
                log.info(
                    f"  ✅ Contas a pagar (taxas): {resultado_taxas['total_contas']} "
                    f"conta(s) | R$ {resultado_taxas['valor_total']:.2f}"
                )
            else:
                log.info(
                    f"  ℹ️  Taxas: {resultado_taxas.get('detalhes') or resultado_taxas.get('error', 'sem taxa configurada')}"
                )
        except Exception as e:
            log.error(f"  ❌ Erro ao criar contas a pagar taxas (ecommerce): {e}", exc_info=True)


def _integrar_venda_ao_motor(db, pedido: Pedido, webhook_payload: dict | None = None) -> int | None:
    from app.vendas.service import VendaService
    from app.vendas_models import Venda

    payload_data = webhook_payload or {}
    metadata = (payload_data.get("metadata") or {}) if isinstance(payload_data, dict) else {}
    nested_metadata = ((payload_data.get("data") or {}).get("metadata") or {}) if isinstance(payload_data, dict) else {}

    canal_origem = (
        metadata.get("canal")
        or nested_metadata.get("canal")
        or payload_data.get("canal")
        or "ecommerce"
    )

    entrega_mode = str(
        metadata.get("delivery_mode")
        or nested_metadata.get("delivery_mode")
        or payload_data.get("delivery_mode")
        or ""
    ).strip().lower()

    entregador_payload = (
        metadata.get("entregador_id")
        or nested_metadata.get("entregador_id")
        or payload_data.get("entregador_id")
    )

    endereco_entrega = (
        metadata.get("endereco_entrega")
        or nested_metadata.get("endereco_entrega")
        or payload_data.get("endereco_entrega")
    )

    tem_entrega_payload = (
        metadata.get("tem_entrega")
        if metadata.get("tem_entrega") is not None
        else nested_metadata.get("tem_entrega")
    )
    if tem_entrega_payload is None:
        tem_entrega_payload = payload_data.get("tem_entrega")

    if tem_entrega_payload is None:
        # Se o endereço for "RETIRADA NA LOJA" não é entrega, mesmo sem delivery_mode no payload
        if endereco_entrega and "retirada" in str(endereco_entrega).lower():
            tem_entrega = False
        else:
            tem_entrega = entrega_mode == "entrega"
    else:
        if isinstance(tem_entrega_payload, str):
            tem_entrega = tem_entrega_payload.strip().lower() in {"1", "true", "yes", "sim"}
        else:
            tem_entrega = bool(tem_entrega_payload)

    entregador_id = None
    if entregador_payload is not None:
        try:
            entregador_id = int(entregador_payload)
        except (TypeError, ValueError):
            entregador_id = None

    if tem_entrega and not entregador_id:
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
        if entregador_padrao:
            entregador_id = entregador_padrao.id

    integration_endpoint = "POST /api/ecommerce/integracao/venda"
    integration_key = f"ecommerce-venda:{pedido.pedido_id}"

    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == 0,
            IdempotencyKey.tenant_id == pedido.tenant_id,
            IdempotencyKey.endpoint == integration_endpoint,
            IdempotencyKey.chave_idempotencia == integration_key,
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

    itens = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.pedido_id).all()
    if not itens:
        return None

    primeiro_produto = (
        db.query(Produto)
        .filter(Produto.id == itens[0].produto_id, Produto.tenant_id == pedido.tenant_id)
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

    if not vendedor:
        vendedor = (
            db.query(User)
            .filter(User.tenant_id == pedido.tenant_id, User.is_active.is_(True))
            .order_by(User.is_admin.desc(), User.id.asc())
            .first()
        )

    if not vendedor:
        return None

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == pedido.tenant_id,
            Cliente.user_id == pedido.cliente_id,
        )
        .first()
    )

    if not cliente:
        usuario_cliente = (
            db.query(User)
            .filter(
                User.id == pedido.cliente_id,
                User.tenant_id == pedido.tenant_id,
            )
            .first()
        )
        if usuario_cliente:
            cliente = (
                db.query(Cliente)
                .filter(
                    Cliente.tenant_id == pedido.tenant_id,
                    Cliente.email == usuario_cliente.email,
                )
                .first()
            )

    cliente_id = cliente.id if cliente else None

    payload = {
        "cliente_id": cliente_id,
        "vendedor_id": vendedor.id,
        "funcionario_id": None,
        "itens": [
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
        ],
        "desconto_valor": 0,
        "desconto_percentual": 0,
        "observacoes": f"Pedido e-commerce {pedido.pedido_id}",
        "tem_entrega": tem_entrega,
        "taxa_entrega": 0,
        "percentual_taxa_loja": 100,
        "percentual_taxa_entregador": 0,
        "entregador_id": entregador_id,
        "loja_origem": "ecommerce",
        "endereco_entrega": endereco_entrega,
        "distancia_km": None,
        "valor_por_km": None,
        "observacoes_entrega": None,
        "canal": canal_origem,
        "tenant_id": str(pedido.tenant_id),
    }

    venda = VendaService.criar_venda(payload=payload, user_id=vendedor.id, db=db)
    venda_id = int(venda.get("id")) if venda.get("id") else None

    if venda_id:
        venda_row = db.query(Venda).filter(Venda.id == venda_id, Venda.tenant_id == pedido.tenant_id).first()
        if venda_row:
            venda_row.status = "finalizada"
            venda_row.data_finalizacao = datetime.utcnow()
            if venda_row.tem_entrega and not venda_row.status_entrega:
                venda_row.status_entrega = "pendente"
            # Repassa dados de retirada do ecommerce para a venda no PDV
            venda_row.tipo_retirada = pedido.tipo_retirada
            venda_row.palavra_chave_retirada = pedido.palavra_chave_retirada

            # ── Efeitos colaterais completos (espelha finalização do PDV) ───────
            _processar_pos_venda_ecommerce(
                db=db,
                venda_row=venda_row,
                vendedor=vendedor,
                tenant_id=str(pedido.tenant_id),
                webhook_payload=webhook_payload or {},
            )

    registry = IdempotencyKey(
        user_id=0,
        tenant_id=pedido.tenant_id,
        endpoint=integration_endpoint,
        chave_idempotencia=integration_key,
        request_hash=hashlib.sha256(integration_key.encode("utf-8")).hexdigest(),
        status="completed",
        response_status_code=200,
        response_body=json.dumps({"venda_id": venda_id}),
        completed_at=datetime.utcnow(),
    )
    db.add(registry)

    return venda_id


@router.post("/pagarme")
async def webhook_pagarme(request: Request):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON inválido")

    signature_status = _validate_optional_signature(raw_body, request)
    tenant_id = _find_tenant_id(payload, request)
    event_id, event_type, request_hash = _extract_event_info(payload, raw_body)

    db = SessionLocal()
    try:
        endpoint_name = "POST /api/webhooks/pagarme"
        key_name = f"pagarme:{event_id}"

        existing = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == 0,
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.endpoint == endpoint_name,
                IdempotencyKey.chave_idempotencia == key_name,
            )
            .first()
        )

        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflito de idempotência no webhook",
                )
            return {
                "status": "duplicate",
                "event_id": event_id,
                "event_type": event_type,
                "signature": signature_status,
            }

        registry = IdempotencyKey(
            user_id=0,
            tenant_id=tenant_id,
            endpoint=endpoint_name,
            chave_idempotencia=key_name,
            request_hash=request_hash,
            status="processing",
        )
        db.add(registry)
        db.flush()

        pedido_id = _find_pedido_id(payload)
        pedido_status = _map_payment_status(payload)

        updated = False
        venda_id = None
        if pedido_id and pedido_status:
            pedido = (
                db.query(Pedido)
                .filter(Pedido.pedido_id == pedido_id, Pedido.tenant_id == tenant_id)
                .first()
            )
            if pedido:
                pedido.status = pedido_status
                updated = True
                if pedido_status == "aprovado":
                    venda_id = _integrar_venda_ao_motor(db, pedido, payload)

        response = {
            "status": "processed",
            "event_id": event_id,
            "event_type": event_type,
            "signature": signature_status,
            "pedido_atualizado": updated,
            "venda_id": venda_id,
            "ready_for_provider_config": True,
        }

        registry.status = "completed"
        registry.response_status_code = 200
        registry.response_body = json.dumps(response)
        registry.completed_at = datetime.utcnow()
        db.commit()

        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar webhook Pagar.me: {exc}")
    finally:
        db.close()