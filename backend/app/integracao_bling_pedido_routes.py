
import os
import re
import time
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.services.bling_flow_monitor_service import (
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
    pedido_esta_mesclado,
    registrar_alias_bling_no_payload,
)
from app.services.pedido_integrado_duplicate_review_service import (
    consolidar_duplicidades_seguras_pedido,
    mapear_duplicidade_por_pedido_ids,
    reconciliar_fluxo_pedido_integrado,
)
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - Pedido"]
)


_CANAL_LABELS = {
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
    "site": "Site",
    "app": "App",
    "whatsapp": "WhatsApp",
    "bling": "Bling",
    "online": "Online",
}

_LOJA_ID_CANAL_MAP = {
    "204647675": "mercado_livre",
    "205367939": "shopee",
    "205639810": "amazon",
}


def _coerce_int(valor, default: int | None = None) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def _coerce_float(valor, default: float | None = None) -> float | None:
    try:
        if valor is None or valor == "":
            return default
        return float(valor)
    except (TypeError, ValueError):
        return default


def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _primeiro_preenchido(*valores):
    for valor in valores:
        if valor is None:
            continue
        if isinstance(valor, str) and not valor.strip():
            continue
        return valor
    return None


def _dict(valor) -> dict:
    return valor if isinstance(valor, dict) else {}


def _dt_iso(dt):
    if not dt:
        return None
    s = dt.isoformat()
    return s if ("+" in s or s.endswith("Z")) else s + "+00:00"


def _situacao_codigo_bling(valor) -> int | None:
    if isinstance(valor, dict):
        return _coerce_int(_primeiro_preenchido(valor.get("id"), valor.get("valor")))
    return _coerce_int(valor)


def _normalizar_canal(valor):
    texto = _texto(valor) or "bling"
    slug = f" {re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()} "

    if " mercado livre " in slug or " mercadolivre " in slug or slug.strip() == "ml":
        canal = "mercado_livre"
    elif " shopee " in slug:
        canal = "shopee"
    elif " amazon " in slug:
        canal = "amazon"
    elif slug.strip() in {"app", "aplicativo"} or " aplicativo " in slug:
        canal = "app"
    elif " whatsapp " in slug:
        canal = "whatsapp"
    elif any(chave in slug for chave in (" site ", " loja virtual ", " ecommerce ", " e commerce ")):
        canal = "site"
    elif slug.strip() == "online":
        canal = "online"
    else:
        canal = "bling"

    return canal, _CANAL_LABELS.get(canal, texto), texto


def _inferir_canal_por_numero_pedido_loja(valor):
    texto = _texto(valor)
    if not texto:
        return None
    if re.fullmatch(r"\d{3}-\d{7}-\d{7}", texto):
        return "amazon"
    if texto.isdigit() and len(texto) >= 14:
        return "mercado_livre"
    if re.search(r"[A-Za-z]", texto) and re.search(r"\d", texto):
        return "shopee"
    return None


def _inferir_canal_por_loja_id(loja_id):
    return _LOJA_ID_CANAL_MAP.get(_texto(loja_id) or "")


def _payload_principal(payload: dict | None) -> dict:
    payload = _dict(payload)
    if isinstance(payload.get("pedido"), dict):
        return payload.get("pedido") or {}
    return payload


def _nf_id_valido(value) -> str | None:
    texto = _texto(value)
    if not texto or texto in {"0", "-1"}:
        return None
    return texto


def _normalizar_resumo_nf(resumo_nf: dict | None) -> dict | None:
    resumo_nf = dict(_dict(resumo_nf))
    if not resumo_nf:
        return None

    nf_id = _nf_id_valido(_primeiro_preenchido(resumo_nf.get("id"), resumo_nf.get("nfe_id")))
    if nf_id:
        if "id" in resumo_nf or "nfe_id" not in resumo_nf:
            resumo_nf["id"] = nf_id
        else:
            resumo_nf["nfe_id"] = nf_id
    else:
        resumo_nf.pop("id", None)
        resumo_nf.pop("nfe_id", None)

    possui_referencia_util = bool(
        nf_id
        or _texto(resumo_nf.get("numero"))
        or _texto(_primeiro_preenchido(resumo_nf.get("chaveAcesso"), resumo_nf.get("chave")))
        or _texto(_primeiro_preenchido(resumo_nf.get("situacao"), resumo_nf.get("status")))
        or _texto(_primeiro_preenchido(resumo_nf.get("data_emissao"), resumo_nf.get("dataEmissao")))
        or resumo_nf.get("valor_total") not in (None, "")
    )

    return resumo_nf if possui_referencia_util else None


def _ultima_nf_payload_efetiva(payload: dict | None) -> dict:
    payload = _dict(payload)
    pedido_payload = _payload_principal(payload)

    for candidato in (
        payload.get("ultima_nf"),
        pedido_payload.get("notaFiscal"),
        pedido_payload.get("nota"),
        pedido_payload.get("nfe"),
    ):
        resumo_nf = _normalizar_resumo_nf(candidato)
        if resumo_nf:
            return resumo_nf
    return {}


def _mesclar_ultima_nf(atual: dict | None, nova: dict | None) -> dict | None:
    atual = _normalizar_resumo_nf(atual) or {}
    nova = _normalizar_resumo_nf(nova) or {}
    if not atual and not nova:
        return None

    mesclada = dict(atual)
    for chave, valor in nova.items():
        if valor in (None, "", [], {}):
            continue
        mesclada[chave] = valor
    return mesclada


def _coerce_data_nf(value) -> datetime | None:
    texto = _texto(value)
    if not texto:
        return None
    texto = texto.replace("Z", "+00:00")
    try:
        if "T" not in texto and " " in texto:
            texto = texto.replace(" ", "T", 1)
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        try:
            return datetime.fromisoformat(texto.split("T")[0])
        except ValueError:
            return None


def _numero_nf_int(nf: dict | None) -> int | None:
    numero = _texto(_dict(nf).get("numero"))
    if not numero or not numero.isdigit():
        return None
    return int(numero)


def _nova_nf_deve_substituir(atual: dict | None, nova: dict | None) -> bool:
    atual = _normalizar_resumo_nf(atual) or {}
    nova = _normalizar_resumo_nf(nova) or {}
    if not atual:
        return True
    if not nova:
        return False

    atual_id = _nf_id_valido(_primeiro_preenchido(atual.get("id"), atual.get("nfe_id")))
    nova_id = _nf_id_valido(_primeiro_preenchido(nova.get("id"), nova.get("nfe_id")))
    atual_numero = _texto(atual.get("numero"))
    nova_numero = _texto(nova.get("numero"))

    if (atual_id and nova_id and atual_id == nova_id) or (atual_numero and nova_numero and atual_numero == nova_numero):
        return True

    atual_data = _coerce_data_nf(_primeiro_preenchido(atual.get("data_emissao"), atual.get("dataEmissao")))
    nova_data = _coerce_data_nf(_primeiro_preenchido(nova.get("data_emissao"), nova.get("dataEmissao")))
    if atual_data and nova_data and atual_data != nova_data:
        return nova_data > atual_data
    if nova_data and not atual_data:
        return True
    if atual_data and not nova_data:
        return False

    atual_numero_int = _numero_nf_int(atual)
    nova_numero_int = _numero_nf_int(nova)
    if atual_numero_int is not None and nova_numero_int is not None and atual_numero_int != nova_numero_int:
        return nova_numero_int > atual_numero_int

    return False


def _consolidar_ultima_nf(atual: dict | None, nova: dict | None) -> dict | None:
    if not atual and not nova:
        return None
    if _nova_nf_deve_substituir(atual, nova):
        return _mesclar_ultima_nf(atual, nova)
    return _mesclar_ultima_nf(nova, atual)


def _montar_payload_pedido(webhook_data: dict | None, pedido_completo: dict | None, payload_atual: dict | None = None, ultima_nf: dict | None = None) -> dict:
    payload = dict(_dict(payload_atual))
    if isinstance(webhook_data, dict) and webhook_data:
        payload["webhook"] = webhook_data
    pedido_base = pedido_completo if isinstance(pedido_completo, dict) and pedido_completo else _payload_principal(payload) or _dict(webhook_data)
    payload["pedido"] = pedido_base
    if ultima_nf:
        payload["ultima_nf"] = _consolidar_ultima_nf(payload.get("ultima_nf"), ultima_nf)
    return payload


def _resumir_ultima_nf_webhook(nf_data: dict | None) -> dict:
    nf_data = _dict(nf_data)
    situacao_nf = _dict(nf_data.get("situacao"))
    return {
        "id": _texto(nf_data.get("id")),
        "numero": _texto(nf_data.get("numero")),
        "serie": _texto(nf_data.get("serie")),
        "data_emissao": _texto(_primeiro_preenchido(nf_data.get("dataEmissao"), nf_data.get("data_emissao"))),
        "situacao": _texto(
            _primeiro_preenchido(
                situacao_nf.get("descricao"),
                situacao_nf.get("nome"),
                nf_data.get("status"),
            )
        ),
        "situacao_codigo": _situacao_codigo_bling(
            _primeiro_preenchido(
                situacao_nf.get("valor"),
                situacao_nf.get("id"),
                nf_data.get("situacao"),
            )
        ),
        "chave": _texto(_primeiro_preenchido(nf_data.get("chaveAcesso"), nf_data.get("chave"))),
        "valor_total": _coerce_float(
            _primeiro_preenchido(
                nf_data.get("valorNota"),
                nf_data.get("valorTotalNf"),
                nf_data.get("valor_total"),
                nf_data.get("valorTotal"),
            )
        ),
    }


def _resumir_ultima_nf_do_pedido_bling(pedido_payload: dict | None, *, enriquecer_via_api: bool = True) -> dict | None:
    pedido_payload = _dict(pedido_payload)
    nota_ref = _dict(
        _primeiro_preenchido(
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    nf_id = _texto(_primeiro_preenchido(nota_ref.get("id"), nota_ref.get("nfe_id")))
    if not nf_id:
        return None

    resumo_nf = _resumir_ultima_nf_webhook({**nota_ref, "id": nf_id})
    if resumo_nf.get("numero") and resumo_nf.get("valor_total") is not None:
        return resumo_nf

    if not enriquecer_via_api:
        return resumo_nf if resumo_nf.get("id") or resumo_nf.get("numero") else None

    try:
        from app.bling_integration import BlingAPI

        bling = BlingAPI()
        ultima_falha = None
        for consulta in (bling.consultar_nfe, bling.consultar_nfce):
            try:
                nf_completa = consulta(int(nf_id))
                return _resumir_ultima_nf_webhook({**_dict(nf_completa), "id": nf_id})
            except Exception as exc:
                ultima_falha = exc

        if ultima_falha:
            logger.warning(f"[BLING PEDIDO] Falha ao consultar NF {nf_id} vinculada ao pedido: {ultima_falha}")
    except Exception as exc:
        logger.warning(f"[BLING PEDIDO] Falha ao enriquecer resumo da NF {nf_id}: {exc}")

    return resumo_nf if resumo_nf.get("id") else None


def _pedido_tem_nf_deterministica(payload: dict | None) -> bool:
    payload = _dict(payload)
    ultima_nf = _ultima_nf_payload_efetiva(payload)
    nf_id = _texto(_primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id")))
    nf_numero = _texto(ultima_nf.get("numero"))
    return bool(nf_numero or (nf_id and nf_id not in {"0", "-1"}))


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
    mesma_nf = (
        _texto(ultima_nf_atual.get("id")) == _texto(resumo_nf.get("id"))
        and _texto(ultima_nf_atual.get("numero")) == _texto(resumo_nf.get("numero"))
    )

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


def _resolver_canal_pedido(payload: dict | None, canal_salvo: str | None):
    pedido_payload = _payload_principal(payload)
    marketplace = _dict(pedido_payload.get("marketplace"))
    loja = _dict(_primeiro_preenchido(pedido_payload.get("loja"), pedido_payload.get("lojaVirtual")))
    numero_pedido_loja = _texto(_primeiro_preenchido(
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedido"),
        pedido_payload.get("numero"),
    ))

    candidatos = [
        pedido_payload.get("canal"),
        pedido_payload.get("origem"),
        pedido_payload.get("tipoOrigem"),
        pedido_payload.get("origemLojaVirtual"),
        marketplace.get("nome"),
        marketplace.get("descricao"),
        loja.get("nome"),
        loja.get("descricao"),
        _inferir_canal_por_loja_id(loja.get("id")),
        _inferir_canal_por_numero_pedido_loja(numero_pedido_loja),
        canal_salvo,
    ]

    fallback = None
    for candidato in candidatos:
        texto = _texto(candidato)
        if not texto:
            continue
        normalizado = _normalizar_canal(texto)
        if fallback is None:
            fallback = normalizado
        if normalizado[0] != "bling":
            return normalizado

    return fallback or _normalizar_canal(canal_salvo)


def _normalizar_item_payload(item_payload: dict) -> dict:
    item = _dict(item_payload.get("item")) if isinstance(item_payload, dict) and isinstance(item_payload.get("item"), dict) else _dict(item_payload)
    produto = _dict(item.get("produto"))
    sku = _texto(_primeiro_preenchido(item.get("codigo"), item.get("sku"), produto.get("codigo"), produto.get("sku")))
    return {
        "sku": sku,
        "descricao": _texto(_primeiro_preenchido(item.get("descricao"), item.get("nome"), produto.get("nome"))),
        "quantidade": _coerce_float(item.get("quantidade"), 0.0) or 0.0,
        "valor_unitario": _coerce_float(_primeiro_preenchido(item.get("valor"), item.get("valorUnitario"), item.get("preco"), item.get("precoUnitario"))),
        "desconto": _coerce_float(_primeiro_preenchido(item.get("desconto"), item.get("valorDesconto"))),
        "total": _coerce_float(_primeiro_preenchido(item.get("total"), item.get("valorTotal"))),
        "produto_bling_id": _texto(produto.get("id")),
    }


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
            logger.warning(f"[BLING WEBHOOK] Reserva nao criada para SKU {sku} em merge de duplicidade: {e}")
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
    if not pedido_canonico or int(pedido_canonico.id) not in {int(pedido.id) for pedido in candidatos}:
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
        pedido_duplicado.cancelado_em = pedido_duplicado.cancelado_em or datetime.utcnow()
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


def _serializar_itens_pedido(pedido_payload: dict, itens_db: list[PedidoIntegradoItem]) -> list[dict]:
    payload_itens = [_normalizar_item_payload(item) for item in (pedido_payload.get("itens") or [])]
    usados: set[int] = set()
    itens_serializados = []

    for item_db in itens_db:
        idx_match = next(
            (
                idx for idx, item_payload in enumerate(payload_itens)
                if idx not in usados and (
                    (item_payload.get("sku") and item_payload.get("sku") == item_db.sku)
                    or (
                        item_payload.get("descricao")
                        and item_db.descricao
                        and item_payload.get("descricao") == item_db.descricao
                    )
                )
            ),
            None,
        )

        payload_item = payload_itens[idx_match] if idx_match is not None else {}
        if idx_match is not None:
            usados.add(idx_match)

        itens_serializados.append({
            "id": item_db.id,
            "sku": item_db.sku,
            "descricao": item_db.descricao or payload_item.get("descricao"),
            "quantidade": item_db.quantidade,
            "valor_unitario": payload_item.get("valor_unitario"),
            "desconto": payload_item.get("desconto"),
            "total": payload_item.get("total"),
            "produto_bling_id": payload_item.get("produto_bling_id"),
            "reservado_em": _dt_iso(item_db.reservado_em),
            "liberado_em": _dt_iso(item_db.liberado_em),
            "vendido_em": _dt_iso(item_db.vendido_em),
        })

    for idx, payload_item in enumerate(payload_itens):
        if idx in usados:
            continue
        itens_serializados.append({
            "id": None,
            "sku": payload_item.get("sku"),
            "descricao": payload_item.get("descricao"),
            "quantidade": payload_item.get("quantidade"),
            "valor_unitario": payload_item.get("valor_unitario"),
            "desconto": payload_item.get("desconto"),
            "total": payload_item.get("total"),
            "produto_bling_id": payload_item.get("produto_bling_id"),
            "reservado_em": None,
            "liberado_em": None,
            "vendido_em": None,
        })

    return itens_serializados


def _acoes_operacionais_pedido(pedido: PedidoIntegrado, duplicidade: dict | None = None) -> dict:
    duplicidade = _dict(duplicidade)
    pedido_atual_eh_canonico = bool(duplicidade.get("pedido_atual_eh_canonico"))
    pedidos_seguro_ids = duplicidade.get("pedidos_seguro_ids") or []
    pode_consolidar = bool(pedido_atual_eh_canonico and pedidos_seguro_ids)

    return {
        "pode_consolidar_duplicidade": pode_consolidar,
        "pode_reconciliar_fluxo": bool(getattr(pedido, "id", None)),
        "tem_revisao_manual_pendente": bool(duplicidade.get("requer_revisao_manual")),
    }


def _serializar_pedido_bling(
    pedido: PedidoIntegrado,
    itens_db: list[PedidoIntegradoItem],
    *,
    duplicidade: dict | None = None,
) -> dict:
    payload = _dict(pedido.payload)
    pedido_payload = _payload_principal(payload)
    contato = _dict(_primeiro_preenchido(pedido_payload.get("contato"), pedido_payload.get("cliente")))
    loja = _dict(pedido_payload.get("loja"))
    ultima_nf = _ultima_nf_payload_efetiva(payload)
    situacao = _dict(pedido_payload.get("situacao"))
    canal, canal_label, canal_origem = _resolver_canal_pedido(payload, pedido.canal)
    duplicidade = _dict(duplicidade)

    return {
        "id": pedido.id,
        "pedido_bling_id": pedido.pedido_bling_id,
        "pedido_bling_numero": _texto(_primeiro_preenchido(pedido.pedido_bling_numero, pedido_payload.get("numero"))),
        "numero_pedido_loja": _texto(_primeiro_preenchido(pedido_payload.get("numeroPedidoLoja"), pedido_payload.get("numeroLoja"))),
        "numero_pedido_canal": _texto(_primeiro_preenchido(
            pedido_payload.get("numeroPedidoCanalVenda"),
            pedido_payload.get("numeroPedidoCanal"),
            pedido_payload.get("numeroPedidoMarketplace"),
            pedido_payload.get("numeroPedido"),
        )),
        "canal": canal,
        "canal_label": canal_label,
        "canal_origem": canal_origem,
        "status": pedido.status,
        "criado_em": _dt_iso(pedido.criado_em),
        "expira_em": _dt_iso(pedido.expira_em),
        "confirmado_em": _dt_iso(pedido.confirmado_em),
        "cancelado_em": _dt_iso(pedido.cancelado_em),
        "data_pedido": _texto(_primeiro_preenchido(
            pedido_payload.get("data"),
            pedido_payload.get("dataPedido"),
            pedido_payload.get("dataSaida"),
        )),
        "loja": {
            "id": loja.get("id"),
            "nome": _texto(loja.get("nome")),
        },
        "cliente": {
            "nome": _texto(_primeiro_preenchido(contato.get("nome"), contato.get("descricao"))),
            "documento": _texto(_primeiro_preenchido(contato.get("numeroDocumento"), contato.get("cpfCnpj"), contato.get("cpf"), contato.get("cnpj"))),
            "email": _texto(contato.get("email")),
            "telefone": _texto(_primeiro_preenchido(contato.get("telefone"), contato.get("celular"))),
        },
        "financeiro": {
            "total": _coerce_float(_primeiro_preenchido(pedido_payload.get("total"), pedido_payload.get("valorTotal"))),
            "desconto": _coerce_float(_primeiro_preenchido(pedido_payload.get("desconto"), pedido_payload.get("valorDesconto"))),
            "frete": _coerce_float(_primeiro_preenchido(pedido_payload.get("frete"), _dict(pedido_payload.get("transporte")).get("frete"))),
        },
        "situacao_bling": {
            "codigo": _situacao_codigo_bling(_primeiro_preenchido(situacao, pedido_payload.get("situacao"))),
            "descricao": _texto(_primeiro_preenchido(situacao.get("descricao"), situacao.get("nome"), situacao.get("descricaoInterna"))),
        },
        "nota_fiscal": {
            "id": _texto(_primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))),
            "numero": _texto(ultima_nf.get("numero")),
            "serie": _texto(ultima_nf.get("serie")),
            "situacao": _texto(_primeiro_preenchido(ultima_nf.get("situacao"), ultima_nf.get("status"))),
            "chave": _texto(_primeiro_preenchido(ultima_nf.get("chaveAcesso"), ultima_nf.get("chave"))),
        },
        "observacoes": _texto(_primeiro_preenchido(pedido_payload.get("observacoes"), pedido_payload.get("observacao"), pedido_payload.get("observacoesInternas"))),
        "itens": _serializar_itens_pedido(pedido_payload, itens_db),
        "duplicidade": duplicidade
        or {
            "tem_duplicados": False,
            "pedido_atual_eh_canonico": True,
            "pedidos_duplicados": [],
            "pedidos_seguro_ids": [],
            "pedidos_bloqueados_ids": [],
            "bloqueios": [],
            "pode_consolidar_automaticamente": False,
            "requer_revisao_manual": False,
        },
        "acoes_disponiveis": _acoes_operacionais_pedido(pedido, duplicidade),
    }


def _resolver_produto_local(db: Session, pedido: PedidoIntegrado, item: PedidoIntegradoItem):
    from app.services.bling_nf_service import buscar_produto_do_item, criar_produto_automatico_do_bling

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


def _baixar_item_pedido(db: Session, pedido: PedidoIntegrado, item: PedidoIntegradoItem, *, motivo: str, observacao: str, user_id: int = 0) -> str | None:
    from app.services.bling_nf_service import baixar_estoque_item_integrado, _obter_usuario_padrao_tenant

    produto = _resolver_produto_local(db=db, pedido=pedido, item=item)
    if not produto:
        return f"SKU '{item.sku}' nao encontrado"

    user_id_execucao = user_id or getattr(_obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id), "id", None)
    if not user_id_execucao:
        return "Nenhum usuario valido encontrado para registrar a baixa automatica"

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


def _cancelar_pedido(db: Session, pedido: PedidoIntegrado, itens: list[PedidoIntegradoItem], *, processed_at=None) -> None:
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


# ============================================================
# GET /integracoes/bling/pedidos  — listagem com filtros
# ============================================================

@router.get("/pedidos")
def listar_pedidos_bling(
    status: Optional[str] = Query(None, description="aberto|confirmado|expirado|cancelado"),
    busca: Optional[str] = Query(None, description="Numero interno do pedido Bling ou ID do pedido"),
    pedido: Optional[str] = Query(None, alias="pedido", description="Alias legado para o filtro de busca"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    q = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.tenant_id == tenant_id,
        PedidoIntegrado.status != "mesclado",
    )

    if status:
        q = q.filter(PedidoIntegrado.status == status)

    busca_texto = str(busca or pedido or "").strip()
    if busca_texto:
        termo = f"%{busca_texto}%"
        q = q.filter(
            or_(
                PedidoIntegrado.pedido_bling_numero.ilike(termo),
                PedidoIntegrado.pedido_bling_id.ilike(termo),
            )
        )

    total = q.count()
    pedidos = (
        q.order_by(PedidoIntegrado.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    duplicidade_por_pedido = mapear_duplicidade_por_pedido_ids(
        db,
        tenant_id=tenant_id,
        pedido_ids=[int(p.id) for p in pedidos if getattr(p, "id", None)],
    )

    result = []
    for p in pedidos:
        itens = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == p.id
        ).all()
        try:
            result.append(
                _serializar_pedido_bling(
                    p,
                    itens,
                    duplicidade=duplicidade_por_pedido.get(int(p.id)),
                )
            )
        except Exception as exc:
            logger.exception(
                "[BLING PEDIDOS] Falha ao serializar pedido local id=%s bling_id=%s numero=%s: %s",
                getattr(p, "id", None),
                getattr(p, "pedido_bling_id", None),
                getattr(p, "pedido_bling_numero", None),
                exc,
            )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "pedidos": result,
    }


@router.post("/pedidos/reconciliar-status")
def reconciliar_status_pedidos_recentes(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    from app.services.pedido_status_reconciliation_service import (
        reconciliar_status_pedidos_recentes as _reconciliar_status_pedidos_recentes,
    )

    try:
        return _reconciliar_status_pedidos_recentes(
            db,
            tenant_id,
            dias=dias,
            limite_pedidos=limite,
        )
    except Exception as exc:
        logger.exception("[BLING PEDIDOS] Falha ao reconciliar status dos pedidos recentes: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar status dos pedidos: {exc}")


@router.post("/pedidos/reconciliar-duplicidades")
def reconciliar_duplicidades_pedidos_recentes(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    from app.services.pedido_duplicate_reconciliation_service import (
        reconciliar_duplicidades_recentes_pedido_loja as _reconciliar_duplicidades_recentes_pedido_loja,
    )

    try:
        return _reconciliar_duplicidades_recentes_pedido_loja(
            db,
            tenant_id,
            dias=dias,
            limite_grupos=limite,
        )
    except Exception as exc:
        logger.exception("[BLING PEDIDOS] Falha ao reconciliar duplicidades recentes dos pedidos: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar duplicidades dos pedidos: {exc}")


@router.post("/pedidos/{pedido_id}/consolidar-duplicidade")
def consolidar_duplicidade_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    try:
        resultado = consolidar_duplicidades_seguras_pedido(
            db,
            tenant_id=tenant_id,
            pedido_id=pedido_id,
        )
    except Exception as exc:
        logger.exception("[BLING PEDIDOS] Falha ao consolidar duplicidade do pedido %s: %s", pedido_id, exc)
        raise HTTPException(status_code=500, detail=f"Erro ao consolidar duplicidade: {exc}")

    if resultado.get("success"):
        return resultado

    motivo = resultado.get("motivo")
    if motivo == "pedido_nao_encontrado":
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if motivo == "pedido_sem_duplicidade":
        raise HTTPException(status_code=400, detail="Este pedido nao possui duplicidade ativa")
    if motivo in {"pedido_sem_duplicidade_canonica", "duplicidades_requerem_revisao_manual", "nenhuma_duplicidade_segura_aplicada"}:
        raise HTTPException(status_code=409, detail=resultado)

    raise HTTPException(status_code=400, detail=resultado)


@router.post("/pedidos/{pedido_id}/reconciliar-fluxo")
def reconciliar_fluxo_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    try:
        resultado = reconciliar_fluxo_pedido_integrado(
            db,
            tenant_id=tenant_id,
            pedido_id=pedido_id,
        )
    except Exception as exc:
        logger.exception("[BLING PEDIDOS] Falha ao reconciliar fluxo do pedido %s: %s", pedido_id, exc)
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar fluxo do pedido: {exc}")

    if resultado.get("success"):
        return resultado

    motivo = resultado.get("motivo")
    if motivo == "pedido_nao_encontrado":
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if motivo in {"pedido_sem_itens", "reconciliacao_sem_sucesso"}:
        raise HTTPException(status_code=409, detail=resultado)

    raise HTTPException(status_code=400, detail=resultado)


# ============================================================
# POST /integracoes/bling/pedidos/{id}/confirmar-manual
# ============================================================

@router.post("/pedidos/{pedido_id}/confirmar-manual")
def confirmar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    user = user_tenant[0]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ("aberto", "expirado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser confirmado manualmente",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    erros_estoque = _confirmar_pedido(
        db=db,
        pedido=pedido,
        itens=itens,
        motivo="venda_bling_manual",
        observacao="Confirmacao manual do pedido; venda aguardando NF",
        user_id=getattr(user, "id", 0),
        aplicar_baixa_estoque=False,
    )

    return {
        "status": "ok",
        "pedido_id": pedido.id,
        "erros_estoque": erros_estoque,
        "estoque_movimentado": False,
    }


# ============================================================
# POST /integracoes/bling/pedidos/{id}/cancelar
# ============================================================

@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status in ("confirmado", "cancelado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser cancelado",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    _cancelar_pedido(db=db, pedido=pedido, itens=itens)

    return {"status": "ok", "pedido_id": pedido.id}


# ============================================================
# POST /integracoes/bling/pedidos/reprocessar-sem-itens
# ============================================================

@router.post("/pedidos/reprocessar-sem-itens")
def reprocessar_pedidos_sem_itens(
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    """
    Re-busca os itens no Bling para pedidos que chegaram com 0 itens.
    Útil para corrigir pedidos que falharam na busca inicial de itens.
    """
    tenant_id = user_tenant[1]

    # Pedidos abertos sem nenhum item registrado
    subq_com_itens = (
        db.query(PedidoIntegradoItem.pedido_integrado_id)
        .distinct()
        .subquery()
    )
    pedidos_sem_itens = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.status.in_(["aberto", "expirado"]),
            PedidoIntegrado.id.notin_(subq_com_itens),
        )
        .limit(limite)
        .all()
    )

    if not pedidos_sem_itens:
        return {"reprocessados": 0, "message": "Nenhum pedido sem itens encontrado"}

    from app.bling_integration import BlingAPI
    _bling_api = BlingAPI()

    reprocessados = 0
    erros = []

    for pedido in pedidos_sem_itens:
        try:
            pedido_completo = _bling_api.consultar_pedido(pedido.pedido_bling_id)
            pedido.payload = _montar_payload_pedido(
                webhook_data=_dict((pedido.payload or {})).get("webhook"),
                pedido_completo=pedido_completo,
                payload_atual=pedido.payload,
            )
            db.add(pedido)
            itens_bling = pedido_completo.get("itens", [])
            if not itens_bling:
                db.commit()
                continue

            for item in itens_bling:
                sku = item.get("codigo") or item.get("sku")
                descricao = item.get("descricao")
                quantidade = int(float(item.get("quantidade", 0)))
                if not sku or quantidade <= 0:
                    continue
                item_pedido = PedidoIntegradoItem(
                    tenant_id=pedido.tenant_id,
                    pedido_integrado_id=pedido.id,
                    sku=sku,
                    descricao=descricao,
                    quantidade=quantidade,
                )
                try:
                    EstoqueReservaService.reservar(db, item_pedido)
                except ValueError:
                    pass
                db.add(item_pedido)

            db.commit()
            reprocessados += 1
        except Exception as e:
            erros.append({"pedido_bling_id": pedido.pedido_bling_id, "erro": str(e)[:120]})

    return {
        "reprocessados": reprocessados,
        "total_sem_itens": len(pedidos_sem_itens),
        "erros": erros,
    }


# Situações do pedido Bling — referência API v3
# https://developer.bling.com.br/referencia#/Pedidos%20de%20Venda/get_pedidos__idPedido_
_SITUACOES_PEDIDO_CANCELADO = {
    12,  # Cancelado
    13,  # Cancelado pelo comprador
    14,  # Cancelado por não pagamento
    15,  # Em cancelamento
}

_SITUACOES_PEDIDO_ATENDIDO = {
    9,   # Atendido (concluído/nota fiscal emitida)
}


@router.post("/pedido")
async def receber_pedido_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de pedidos do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'order.created'|'order.updated'|'order.deleted', data: {...} }
    """
    body = await request.json()

    # Tenant fixo para webhooks (chamadas sem JWT)
    _tenant_uuid = UUID(_BLING_WEBHOOK_TENANT_ID) if _BLING_WEBHOOK_TENANT_ID else None
    if _tenant_uuid:
        set_current_tenant(_tenant_uuid)

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "")  # ex: "order.created"
    event_date = body.get("date")
    data = body.get("data", body)  # fallback p/ payload legado sem envelope

    # ========================
    # EVENTO: NOTA FISCAL EMITIDA
    # Quando o Bling gera uma NF vinculada a um pedido de marketplace,
    # confirmar o pedido e baixar o estoque imediatamente.
    # ========================
    if "notafiscal" in event.lower() or "nota_fiscal" in event.lower() or event.startswith("nfe.") or event.startswith("nfce."):
        nf_data = data or {}
        # O pedido pode vir na chave "pedido" ou "pedidoVenda" do payload da NF
        pedido_ref = nf_data.get("pedido") or nf_data.get("pedidoVenda") or {}
        pedido_numero_nf = str(pedido_ref.get("numero") or pedido_ref.get("id") or "").strip()
        nf_id_bling = str(nf_data.get("id") or "").strip()

        if pedido_numero_nf or nf_id_bling:
            pedido = None
            # Buscar pelo número do pedido Bling (campo pedido_bling_numero)
            if pedido_numero_nf:
                pedido = db.query(PedidoIntegrado).filter(
                    PedidoIntegrado.pedido_bling_numero == pedido_numero_nf
                ).first()
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
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
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
                return {"status": "ok", "acao": "aguardando_nf_deterministica", "erros_estoque": []}

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
        return {"status": "ignorado", "motivo": f"evento_nf_sem_pedido_correspondente ({event})"}

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
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            _cancelar_pedido(db=db, pedido=pedido, itens=itens, processed_at=event_date)

        return {"status": "ok", "acao": "cancelado"}

    # ========================
    # EVENTO: ATUALIZADO — checar situação no Bling
    # ========================
    if event.endswith(".updated"):
        situacao_id = _situacao_codigo_bling(data.get("situacao"))
        pedido_api = None
        situacao_id_api = None

        if (situacao_id and situacao_id in (_SITUACOES_PEDIDO_CANCELADO | _SITUACOES_PEDIDO_ATENDIDO)) or not situacao_id:
            try:
                from app.bling_integration import BlingAPI

                pedido_api = BlingAPI().consultar_pedido(pedido_bling_id)
                situacao_id_api = _situacao_codigo_bling(pedido_api.get("situacao"))
            except Exception as e:
                logger.warning(f"[BLING WEBHOOK] Falha ao consultar pedido {pedido_bling_id} na API: {e}")

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_CANCELADO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
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
                _cancelar_pedido(db=db, pedido=pedido, itens=itens, processed_at=event_date)
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado (situacao_id={situacao_id})")

            return {"status": "ok", "acao": "cancelado_por_situacao"}

        if situacao_id and situacao_id in _SITUACOES_PEDIDO_ATENDIDO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
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
                erros_estoque = _confirmar_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    motivo="venda_bling_webhook",
                    observacao="Pedido atendido no Bling; venda aguardando NF",
                    processed_at=event_date,
                    aplicar_baixa_estoque=False,
                )
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} confirmado sem baixa de estoque; aguardando NF (situacao_id={situacao_id})")

            return {"status": "ok", "acao": "confirmado_por_situacao"}

        if situacao_id_api and situacao_id_api in _SITUACOES_PEDIDO_CANCELADO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status != "cancelado":
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
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
                _cancelar_pedido(db=db, pedido=pedido, itens=itens, processed_at=event_date)
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} cancelado via consulta API (situacao_id={situacao_id_api})")

            return {"status": "ok", "acao": "cancelado_via_consulta_api"}

        if situacao_id_api and situacao_id_api in _SITUACOES_PEDIDO_ATENDIDO:
            pedido = localizar_pedido_por_bling_id(
                db,
                tenant_id=_tenant_uuid,
                pedido_bling_id=pedido_bling_id,
            )
            if pedido and pedido.status not in ("confirmado", "cancelado"):
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
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
                erros_estoque = _confirmar_pedido(
                    db=db,
                    pedido=pedido,
                    itens=itens,
                    motivo="venda_bling_webhook",
                    observacao="Pedido atendido via API do Bling; venda aguardando NF",
                    processed_at=event_date,
                    aplicar_baixa_estoque=False,
                )
                logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} confirmado via consulta API sem baixa; aguardando NF (situacao_id={situacao_id_api})")

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
        motivo = "pedido_ja_mesclado" if pedido_esta_mesclado(existente) else "pedido_ja_existe"
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
            logger.warning(f"[BLING WEBHOOK] Pedido {pedido_bling_id}: itens vazios após 3 tentativas")
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
        logger.warning(f"[BLING WEBHOOK] Falha ao buscar itens do pedido {pedido_bling_id}: {e}")

    if not _tenant_uuid:
        logger.error("[BLING WEBHOOK] BLING_WEBHOOK_TENANT_ID não configurado — pedido ignorado")
        return {"status": "erro", "motivo": "tenant_nao_configurado"}

    # Verificar situação atual no Bling — se já cancelado, não criar como aberto
    situacao_id_criacao = _situacao_codigo_bling(pedido_completo.get("situacao") if pedido_completo else None)

    if situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_CANCELADO:
        logger.info(f"[BLING WEBHOOK] Pedido {pedido_bling_id} order.created mas já cancelado (situacao_id={situacao_id_criacao}) — ignorado")
        return {"status": "ignorado", "motivo": "order_created_ja_cancelado"}

    status_inicial = "confirmado" if (situacao_id_criacao and situacao_id_criacao in _SITUACOES_PEDIDO_ATENDIDO) else "aberto"
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
        if status_inicial == "confirmado" and pedido_consolidado.status not in ("confirmado", "cancelado"):
            itens_salvos = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido_consolidado.id
            ).all()
            _confirmar_pedido(
                db=db,
                pedido=pedido_consolidado,
                itens=itens_salvos,
                motivo="venda_bling_webhook_duplicado",
                observacao="Pedido duplicado no Bling consolidado no pedido canonico; venda aguardando NF",
                processed_at=event_date,
                aplicar_baixa_estoque=False,
            )
        return {"status": "ok", "pedido_id": pedido_consolidado.id, "acao": "pedido_duplicado_mesclado"}

    pedido = PedidoIntegrado(
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=numero,
        canal=canal,
        status=status_inicial,
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload=payload_pedido
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
            quantidade=quantidade
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
        itens_salvos = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == pedido.id
        ).all()
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
