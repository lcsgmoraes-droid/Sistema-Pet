"""Piloto manual de um item. Nenhuma leitura remota ou sincronizacao automatica.

O chamador serializa mutacoes pelo config da empresa. A tentativa e persistida
antes da rede: um processo interrompido permanece incerto e nao pode ser repetido
automaticamente. Um HTTP 202 nunca e prova de publicacao.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from hmac import compare_digest
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ifood_catalog_models import (
    IfoodCatalogConfirmation as Confirmation,
    IfoodCatalogLink as Link,
    IfoodCatalogSubmission as Submission,
    IfoodStockSyncState as StockState,
)
from app.produtos_catalogo_models import Produto
from app.integrations.ifood.catalog import build_catalog_item
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.management import product_identifier
from app.integrations.ifood.pricing import aware, resolve_ifood_prices

SNAPSHOT_FIELDS = (
    "codigo",
    "nome",
    "codigo_barras",
    "gtin_ean",
    "preco_venda",
    "preco_custo",
    "preco_ifood",
    "preco_ifood_promo",
    "preco_ifood_promo_inicio",
    "preco_ifood_promo_fim",
    "anunciar_ifood",
    "ifood_pausado",
    "estoque_atual",
    "descricao_curta",
    "descricao_completa",
    "imagem_principal",
    "unidade",
    "tipo_produto",
    "tipo_kit",
    "e_granel",
    "ativo",
    "situacao",
    "is_sellable",
    "categoria_id",
    "marca_id",
    "departamento_id",
    "subcategoria",
)
MESSAGES = {
    "accepted": "Recebido pelo iFood; publicacao ainda depende de conferencia no Portal.",
    "sending": "Envio iniciado. Confira o Portal antes de qualquer nova tentativa.",
    "uncertain": "Resultado incerto. Confira o Portal antes de qualquer nova tentativa.",
    "error": "O iFood recusou a operacao. Nenhuma publicacao foi confirmada.",
}


def now():
    return datetime.now(timezone.utc)


def _iso(value):
    return _utc(value).isoformat() if value else None


def _utc(value):
    # Datas destas tabelas sao sempre UTC; SQLite perde o offset nos testes.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _scope(db, tenant_id, merchant_id):
    return db.query(Link).filter(
        Link.tenant_id == tenant_id, Link.merchant_id == merchant_id
    )


def _link(db, tenant_id, merchant_id, product_id):
    return (
        _scope(db, tenant_id, merchant_id).filter(Link.product_id == product_id).first()
    )


def valid_barcode(value):
    """Este piloto usa apenas EAN-8/13 verificado, sem fallback silencioso de SKU."""
    text = str(value or "").strip()
    if len(text) not in (8, 13) or not text.isascii() or not text.isdigit():
        return False
    check = sum(
        int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(text[:-1]))
    )
    return (10 - check % 10) % 10 == int(text[-1])


def identifier_counts(db, tenant_id):
    products = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.deleted_at.is_(None))
        .all()
    )
    return Counter(product_identifier(product).casefold() for product in products)


def _issue(code, message, kind="blocking"):
    return {"code": code, "message": message, "kind": kind}


def _identity_issues(db, tenant_id, product):
    barcode = product_identifier(product)
    issues = []
    if not valid_barcode(barcode):
        issues.append(
            _issue(
                "invalid_barcode",
                "Informe e confira um EAN-8 ou EAN-13 valido para este piloto.",
            )
        )
    if identifier_counts(db, tenant_id)[barcode.casefold()] > 1:
        issues.append(
            _issue(
                "duplicate_barcode",
                "Outro produto da empresa usa este mesmo identificador; resolva a duplicidade antes de vincular ou enviar.",
            )
        )
    return issues


def _last_rows(db, tenant_id, link_ids, model):
    result = {}
    for offset in range(0, len(link_ids), 1000):
        rows = (
            db.query(model)
            .filter(
                model.tenant_id == tenant_id,
                model.link_id.in_(link_ids[offset : offset + 1000]),
            )
            .order_by(model.id.desc())
            .all()
        )
        for row in rows:
            result.setdefault(row.link_id, row)
    return result


def submission_view(row):
    if not row:
        return None
    source = getattr(row, "source", None) or "manual"
    mode = getattr(row, "provider_mode", None) or (
        "local_simulator" if source == "auto_stock" else "ifood_api"
    )
    return {
        "id": row.id,
        "request_key": row.request_key,
        "operation": row.operation,
        "source": source,
        "provider_mode": mode,
        "fields": row.fields,
        "status": row.status,
        "created_at": _iso(row.created_at),
        "finished_at": _iso(row.finished_at),
        "http_status": row.http_status,
        "provider_request_id": row.provider_request_id,
        "error_code": row.error_code,
        "message": (
            "Ensaio com simulador local em DEV; este registro nao comprova recebimento ou aplicacao no iFood real."
            if mode == "local_simulator"
            else MESSAGES[row.status]
        ),
        "payload_hash": row.payload_hash,
    }


def confirmation_view(row):
    if not row:
        return None
    return {
        "id": row.id,
        "kind": row.kind,
        "present": row.present,
        "portal_active": row.portal_active,
        "barcode": row.barcode,
        "price": str(row.price) if row.price is not None else None,
        "stock": str(row.stock) if row.stock is not None else None,
        "confirmed_at": _iso(row.confirmed_at),
        "actor_id": row.actor_id,
    }


def _stock_state(db, tenant_id, link):
    if not link:
        return None
    return (
        db.query(StockState)
        .filter(
            StockState.tenant_id == tenant_id,
            StockState.merchant_id == link.merchant_id,
            StockState.link_id == link.id,
        )
        .populate_existing()
        .first()
    )


def _confirmation_context(
    tenant_id, product, link, submission, confirmation, state, automatic
):
    if not link:
        return None
    frame = {
        "tenant": str(tenant_id),
        "product": product.id,
        "barcode": product_identifier(product),
        "link": [link.id, link.merchant_id, link.barcode, link.mode, link.revision],
        "submission": None
        if submission is None
        else [
            submission.id,
            submission.request_key,
            submission.status,
            _iso(submission.created_at),
            _iso(submission.finished_at),
            submission.source,
            submission.provider_mode,
        ],
        "confirmation_id": confirmation.id if confirmation else None,
        "state": None
        if state is None
        else [
            state.id,
            state.provider_mode,
            state.link_revision,
            state.status,
            state.desired_stock,
            state.last_accepted_stock,
            state.last_request_key,
            state.last_confirmation_id,
            state.failure_count,
            state.error_code,
            _iso(state.next_attempt_at),
        ],
        "automatic": automatic,
    }
    return sha256(
        json.dumps(frame, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _observation_inflight(submission, state):
    return bool(
        (submission and submission.status in {"sending", "uncertain"})
        or (submission and submission.http_status == 429)
        or (state and state.status in {"sending", "uncertain", "backoff"})
    )


def portal_observation_reason(confirmation):
    """Gate factual separado da referencia do estoque e do aceite da API."""
    if not confirmation or confirmation.kind != "observation":
        return None
    if not confirmation.present:
        return "portal_item_not_found"
    if confirmation.portal_active is False:
        return "portal_item_inactive"
    if confirmation.portal_active is None:
        return "portal_activity_unknown"
    return None


OBSERVATION_MESSAGES = {
    "portal_item_not_found": "Produto nao localizado na ultima conferencia do Portal. Novos envios automaticos aguardam uma conferencia de produto localizado e ativo.",
    "portal_item_inactive": "Item inativo na ultima conferencia do Portal. A conferencia nao reativa o item; novos envios automaticos aguardam uma conferencia ativa.",
    "portal_activity_unknown": "Disponibilidade no Portal nao conferida. Novos envios automaticos aguardam uma conferencia explicita de item ativo.",
}


def summaries(db, tenant_id, merchant_id, product_ids):
    if not merchant_id or not product_ids:
        return {}
    links = []
    ids = list(product_ids)
    for offset in range(0, len(ids), 1000):
        links.extend(
            _scope(db, tenant_id, merchant_id)
            .filter(Link.product_id.in_(ids[offset : offset + 1000]))
            .all()
        )
    keys = [link.id for link in links]
    submissions = _last_rows(db, tenant_id, keys, Submission)
    confirmations = _last_rows(db, tenant_id, keys, Confirmation)
    from app.ifood_catalog_models import IfoodStockSyncState
    from .stock_sync import enabled_for, state_view

    stock_states = _last_rows(db, tenant_id, keys, IfoodStockSyncState)
    return {
        link.product_id: {
            "link": link_view(link, link.barcode),
            "last_submission": submission_view(submissions.get(link.id)),
            "last_confirmation": confirmation_view(confirmations.get(link.id)),
            "stock_sync": {
                **state_view(stock_states[link.id]),
                "enabled": enabled_for(tenant_id, merchant_id, link.product_id),
                "observation_block_reason": portal_observation_reason(
                    confirmations.get(link.id)
                ),
            }
            if link.id in stock_states
            else None,
        }
        for link in links
    }


def link_view(link, barcode):
    if not link:
        return None
    return {
        "id": link.id,
        "mode": link.mode,
        "barcode": link.barcode,
        "revision": link.revision,
        "portal_checked_at": _iso(link.portal_checked_at),
        "portal_checked_by": link.portal_checked_by,
        "stale": link.barcode != barcode,
    }


def saved_snapshot(product):
    result = {}
    for field in SNAPSHOT_FIELDS:
        value = getattr(product, field, None)
        if isinstance(value, datetime):
            value = aware(value).isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        result[field] = value
    return result


def publication_view(
    db, tenant_id, config, product, *, can_edit, write_enabled, credentials
):
    merchant = config.merchant_id if config else None
    barcode = product_identifier(product)
    link = _link(db, tenant_id, merchant, product.id) if merchant else None
    submission = (
        _last_rows(db, tenant_id, [link.id], Submission).get(link.id) if link else None
    )
    confirmation = (
        _last_rows(db, tenant_id, [link.id], Confirmation).get(link.id)
        if link
        else None
    )
    pending = _identity_issues(db, tenant_id, product)
    from .stock_sync import enabled_for, stock_sync_view

    automatic_stock = enabled_for(tenant_id, merchant, product.id)
    stock_sync = stock_sync_view(db, tenant_id, merchant, product.id)
    state = _stock_state(db, tenant_id, link)
    receipt_only = automatic_stock or state is not None
    observation_busy = receipt_only and _observation_inflight(submission, state)
    observation_reason = portal_observation_reason(confirmation)
    if receipt_only and observation_reason:
        pending.append(
            _issue(observation_reason, OBSERVATION_MESSAGES[observation_reason])
        )
    if (
        receipt_only
        and confirmation
        and confirmation.kind == "observation"
        and confirmation.present
        and confirmation.portal_active is True
        and confirmation.stock is not None
        and state
        and state.last_accepted_stock is not None
        and confirmation.stock != state.last_accepted_stock
    ):
        pending.append(
            _issue(
                "portal_stock_divergent",
                "O estoque observado no Portal difere do ultimo saldo aceito. Registrar a conferencia nao reenviou estoque nem alterou a referencia da fila.",
                "warning",
            )
        )
    if observation_busy:
        pending.append(
            _issue(
                "portal_observation_wait",
                "Ha um envio em andamento, incerto ou limitado. Aguarde ou resolva a conciliacao operacional antes de registrar esta conferencia.",
                "warning",
            )
        )
    if automatic_stock:
        pending.append(
            _issue(
                "automatic_stock_active",
                "O piloto automatico de estoque esta ativo. Envios manuais e alteracoes do vinculo estao bloqueados; a conferencia do resultado continua disponivel quando nao houver envio pendente.",
            )
        )
    if not merchant:
        pending.append(
            _issue(
                "merchant_missing",
                "Configure a loja iFood antes de conferir o vinculo.",
            )
        )
    if not link:
        pending.append(
            _issue(
                "link_missing",
                "Confira no Portal se este EAN ja existe ou se e um produto novo e registre o vinculo.",
            )
        )
    elif link.barcode != barcode:
        pending.append(
            _issue(
                "barcode_changed",
                "O identificador mudou. Confira novamente o Portal e refaca o vinculo.",
            )
        )
    if submission and submission.status in {"sending", "accepted", "uncertain"}:
        if (
            not confirmation
            or confirmation.confirmed_at is None
            or _utc(confirmation.confirmed_at) <= _utc(submission.created_at)
        ):
            pending.append(
                _issue(
                    "portal_confirmation_required",
                    "Ha um envio sem conferencia posterior no Portal; confira antes de enviar novamente.",
                )
            )
        if now() < _utc(submission.created_at) + timedelta(minutes=35):
            pending.append(
                _issue(
                    "ingestion_window",
                    "Aguarde 35 minutos desde o ultimo envio deste produto para respeitar a janela de atualizacao.",
                )
            )
    if (
        submission
        and submission.error_code == "rate_limited"
        and now() < _utc(submission.created_at) + timedelta(minutes=35)
    ):
        pending.append(
            _issue(
                "ingestion_window",
                "O iFood limitou os envios; aguarde a proxima janela de 35 minutos.",
            )
        )
    if not write_enabled:
        pending.append(
            _issue(
                "write_disabled",
                "Envios ao iFood estao desabilitados no servidor.",
                "warning",
            )
        )
    if not credentials:
        pending.append(
            _issue(
                "credentials_missing",
                "Credenciais iFood nao configuradas no servidor.",
                "warning",
            )
        )
    if not config or not config.active:
        pending.append(
            _issue(
                "integration_inactive", "A integracao da loja esta inativa.", "warning"
            )
        )
    return {
        "product_id": product.id,
        "merchant_id": merchant,
        "barcode": barcode,
        "snapshot_saved": saved_snapshot(product),
        "link": link_view(link, barcode),
        "confirmation_context_token": _confirmation_context(
            tenant_id, product, link, submission, confirmation, state, automatic_stock
        ),
        "capabilities": {
            "can_link": bool(can_edit and merchant and not automatic_stock),
            "can_prepare": bool(can_edit),
            "can_send": bool(
                can_edit
                and write_enabled
                and credentials
                and config
                and config.active
                and not any(p["kind"] == "blocking" for p in pending)
            ),
            "can_confirm": bool(
                can_edit and link and link.barcode == barcode and not observation_busy
            ),
            "write_enabled": bool(write_enabled),
            "credentials_configured": bool(credentials),
        },
        "pending": pending,
        "last_submission": submission_view(submission),
        "last_confirmation": confirmation_view(confirmation),
        "stock_sync": stock_sync,
    }


def _check_declared_identity(db, tenant_id, config, product, merchant_id, barcode):
    if not config or not config.merchant_id or config.merchant_id != str(merchant_id):
        raise HTTPException(
            409, "A loja iFood mudou. Reabra a conferencia para a loja atual."
        )
    if barcode != product_identifier(product):
        raise HTTPException(
            409, "O EAN informado difere do cadastro salvo. Confira novamente."
        )
    issues = _identity_issues(db, tenant_id, product)
    if issues:
        raise HTTPException(409, issues[0]["message"])


def record_link(db, tenant_id, config, product, data, actor_id):
    _guard_manual_stock_sync(tenant_id, config, product)
    _check_declared_identity(
        db, tenant_id, config, product, data["merchant_id"], data["barcode"]
    )
    if not data.get("portal_checked"):
        raise HTTPException(422, "Confirme a conferencia do EAN no Portal do Parceiro.")
    link = _link(db, tenant_id, config.merchant_id, product.id)
    if link:
        previous = _last_rows(db, tenant_id, [link.id], Submission).get(link.id)
        latest_confirmation = _last_rows(db, tenant_id, [link.id], Confirmation).get(
            link.id
        )
        if (
            previous
            and previous.status in {"sending", "accepted", "uncertain"}
            and (
                not latest_confirmation
                or _utc(latest_confirmation.confirmed_at) <= _utc(previous.created_at)
            )
        ):
            raise HTTPException(
                409,
                "Confira o resultado do ultimo envio no Portal antes de alterar o vinculo.",
            )
        link.revision += 1
    else:
        link = Link(
            tenant_id=tenant_id,
            merchant_id=config.merchant_id,
            product_id=product.id,
            revision=1,
        )
        db.add(link)
    link.barcode = data["barcode"]
    link.mode = data["mode"]
    link.portal_checked_at = now()
    link.portal_checked_by = actor_id
    db.flush()
    _add_confirmation(
        db,
        tenant_id,
        link,
        data,
        actor_id,
        kind="link",
        present=link.mode == "existing",
    )
    return link


def _add_confirmation(db, tenant_id, link, data, actor_id, *, kind, present):
    db.add(
        Confirmation(
            tenant_id=tenant_id,
            link_id=link.id,
            barcode=link.barcode,
            kind=kind,
            present=present,
            portal_active=data.get("portal_active") if present else None,
            price=data.get("price") if present else None,
            stock=data.get("stock") if present else None,
            actor_id=actor_id,
            confirmed_at=now(),
        )
    )
    db.flush()


def confirm_portal(db, tenant_id, config, product, data, actor_id):
    from .stock_sync import enabled_for

    _check_declared_identity(
        db, tenant_id, config, product, data["merchant_id"], data["barcode"]
    )
    link = _link(db, tenant_id, config.merchant_id, product.id)
    if not link or link.barcode != data["barcode"]:
        raise HTTPException(
            409, "Confira o vinculo atual antes de registrar o resultado do Portal."
        )
    automatic = enabled_for(tenant_id, config.merchant_id, product.id)
    state = _stock_state(db, tenant_id, link)
    submission = _last_rows(db, tenant_id, [link.id], Submission).get(link.id)
    confirmation = _last_rows(db, tenant_id, [link.id], Confirmation).get(link.id)
    expected = _confirmation_context(
        tenant_id, product, link, submission, confirmation, state, automatic
    )
    supplied = data.get("confirmation_context_token")
    if not supplied or not compare_digest(supplied, expected):
        raise HTTPException(
            409,
            "O acompanhamento mudou. Atualize, confira o Portal e marque novamente a confirmacao.",
        )
    receipt_only = automatic or state is not None
    if receipt_only and _observation_inflight(submission, state):
        raise HTTPException(
            409,
            "Ha um envio em andamento, incerto ou limitado. A conferencia comum nao pode liberar sua repeticao.",
        )
    _add_confirmation(
        db,
        tenant_id,
        link,
        data,
        actor_id,
        kind="observation" if receipt_only else "portal",
        present=data["present"],
    )
    if not receipt_only:
        # A primeira referencia continua pelo fluxo manual legado, antes da
        # ativacao. Depois que existe fila, recibos nao sao revisao/rebaseline.
        link.mode = "existing" if data["present"] else "new"
        link.revision += 1
        link.portal_checked_at = now()
        link.portal_checked_by = actor_id


def _guard_manual_stock_sync(tenant_id, config, product):
    from .stock_sync import enabled_for

    if enabled_for(tenant_id, config.merchant_id if config else None, product.id):
        raise HTTPException(
            409,
            "Desative o piloto automatico de estoque antes de enviar manualmente ou alterar a conferencia deste vinculo.",
        )


def prepare(
    db,
    tenant_id,
    config,
    product,
    stock,
    operation,
    fields,
    *,
    can_edit,
    write_enabled,
    credentials,
    public_base_url,
):
    view = publication_view(
        db,
        tenant_id,
        config,
        product,
        can_edit=can_edit,
        write_enabled=write_enabled,
        credentials=credentials,
    )
    pending = list(view["pending"])
    selected = sorted(set(fields)) if operation == "update" else ["price", "stock"]
    link = view["link"]
    if link and not link["stale"]:
        if operation == "create" and link["mode"] != "new":
            pending.append(
                _issue(
                    "existing_item",
                    "Este EAN ja existe no Portal. Use a atualizacao parcial; nao crie outro anuncio.",
                )
            )
        if operation == "update" and link["mode"] != "existing":
            pending.append(
                _issue(
                    "new_item",
                    "A atualizacao parcial exige presenca conferida no Portal.",
                )
            )
    if operation == "update" and not selected:
        pending.append(
            _issue("fields_missing", "Escolha preco e/ou estoque para atualizar.")
        )
    if not product.anunciar_ifood:
        pending.append(
            _issue(
                "not_selected",
                "Selecione o produto para vender no iFood antes de enviar.",
            )
        )
    if (
        product.deleted_at
        or not product.ativo
        or not product.situacao
        or product.tipo_produto == "PAI"
        or not product.is_sellable
        or product.e_granel
        or str(product.tipo or "").lower() == "servico"
    ):
        pending.append(
            _issue(
                "not_sellable",
                "O produto nao esta apto para este piloto de itens embalados.",
            )
        )
    price = resolve_ifood_prices(
        product, float(config.default_markup_percent or 0) if config else 0, now()
    )["regular_price"]
    available = (
        max(0, float(stock) - float(config.stock_safety or 0))
        if stock is not None and config
        else stock
    )
    if product.ifood_pausado:
        available = 0
        if operation == "create":
            pending.append(
                _issue(
                    "paused",
                    "Produto pausado; revise a pausa antes de criar o anuncio.",
                )
            )
    if "stock" in selected and (
        available is None
        or not Decimal(str(available)).is_finite()
        or Decimal(str(available)) != Decimal(str(available)).to_integral_value()
    ):
        pending.append(
            _issue(
                "stock_invalid",
                "O estoque disponivel deste piloto precisa ser inteiro e conhecido.",
            )
        )
    if "price" in selected and (
        price is None or not Decimal(str(price)).is_finite() or price <= 0
    ):
        pending.append(
            _issue("price_invalid", "Informe um preco iFood valido maior que zero.")
        )
    payload = {"barcode": view["barcode"]}
    if operation == "create":
        product.ifood_available_stock = stock
        item = build_catalog_item(
            product,
            source="ifood",
            markup_percent=float(config.default_markup_percent or 0) if config else 0,
            stock_safety=float(config.stock_safety or 0) if config else 0,
            public_base_url=public_base_url,
        )
        pending.extend(_issue("product_incomplete", message) for message in item.errors)
        payload = item.payload
        if payload:
            payload["inventory"]["stock"] = (
                int(available)
                if available is not None and Decimal(str(available)).is_finite()
                else 0
            )
            if not payload["details"].get("imageUrl") or not payload["details"].get(
                "description"
            ):
                pending.append(
                    _issue(
                        "content_missing",
                        "Inclua foto HTTPS publica e descricao antes da criacao deste produto.",
                    )
                )
    else:
        if "price" in selected:
            payload["prices"] = {"price": price}  # Omissao preserva promocao remota.
        if "stock" in selected:
            payload["inventory"] = {
                "stock": int(available)
                if available is not None and Decimal(str(available)).is_finite()
                else 0
            }
        pending.append(
            _issue(
                "promotion_preserved",
                "A promocao remota sera preservada; a margem estimada do cadastro pode divergir do preco vigente no Portal.",
                "warning",
            )
        )
    eligible = bool(payload and not any(p["kind"] == "blocking" for p in pending))
    review_data = {
        "tenant": str(tenant_id),
        "merchant": view["merchant_id"],
        "product": product.id,
        "link_revision": link["revision"] if link else None,
        "operation": operation,
        "fields": selected,
        "payload": payload,
    }
    token = sha256(
        json.dumps(
            review_data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
    return {
        "dry_run": True,
        "eligible": eligible,
        "pending": pending,
        "operation": operation,
        "fields": selected,
        "payload": payload,
        "review_token": token,
        "reset_catalog": False,
        "publication": view,
    }


def send_prepared(
    db: Session,
    tenant_id,
    config,
    product,
    prepared,
    *,
    review_token,
    request_key,
    actor_id,
    client_factory,
):
    """Chamador ja verificou flags/permissao. Commit antes da rede e intencional."""
    existing = (
        db.query(Submission)
        .filter(
            Submission.tenant_id == tenant_id,
            Submission.merchant_id == config.merchant_id,
            Submission.request_key == request_key,
        )
        .first()
    )
    link = _link(db, tenant_id, config.merchant_id, product.id)
    if existing:
        if (
            not link
            or existing.link_id != link.id
            or existing.payload_hash != review_token
            or existing.operation != prepared["operation"]
            or existing.fields != prepared["fields"]
        ):
            raise HTTPException(
                409, "Esta chave de envio ja pertence a outra revisao ou produto."
            )
        return existing, True
    if prepared["review_token"] != review_token:
        raise HTTPException(
            409,
            "Preco, estoque ou vinculo mudou. Prepare e confira uma nova revisao antes de enviar.",
        )
    _guard_manual_stock_sync(tenant_id, config, product)
    if not prepared["eligible"]:
        raise HTTPException(
            409, "Resolva as pendencias e prepare novamente antes do envio."
        )
    payload = prepared["payload"]
    row = Submission(
        tenant_id=tenant_id,
        link_id=link.id,
        merchant_id=config.merchant_id,
        barcode=link.barcode,
        request_key=request_key,
        operation=prepared["operation"],
        fields=prepared["fields"],
        payload_hash=review_token,
        evidence={
            key: payload[key]
            for key in ("barcode", "prices", "inventory")
            if key in payload
        },
        status="sending",
        actor_id=actor_id,
        created_at=now(),
    )
    db.add(row)
    merchant_id = config.merchant_id
    method = "POST" if row.operation == "create" else "PATCH"
    db.commit()  # Uma falha de processo apos enviar nunca pode apagar a tentativa.
    try:
        with client_factory() as client:
            result = client.ingest_items(
                merchant_id, [payload], method=method, reset_catalog=False
            )
        row.http_status = result.get("status_code")
        row.status = "accepted" if row.http_status == 202 else "uncertain"
        if row.status == "uncertain":
            row.error_code = "unexpected_response"
        response = result.get("response")
        if isinstance(response, dict):
            try:
                row.provider_request_id = str(UUID(str(response.get("requestId"))))
            except (ValueError, TypeError, AttributeError):
                pass
    except IfoodClientError as exc:
        row.http_status = exc.status_code
        # 5xx/transporte podem ocorrer depois do processamento remoto.
        row.status = (
            "error" if exc.status_code and 400 <= exc.status_code < 500 else "uncertain"
        )
        row.error_code = (
            "rate_limited"
            if exc.status_code == 429
            else "provider_rejected"
            if row.status == "error"
            else "transport_uncertain"
        )
    except Exception:
        # Nao devolver nem persistir texto arbitrario/segredos de excecoes.
        row.status, row.error_code = "uncertain", "transport_uncertain"
    row.finished_at = now()
    db.commit()
    return row, False
