"""Helpers de payload, canal e serializacao de pedidos Bling."""

import re

from app.integracao_bling_nf_routes import (
    _consolidar_ultima_nf,
    _dict,
    _nf_id_valido,
    _normalizar_resumo_nf,
    _primeiro_preenchido,
    _texto,
)
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.utils.logger import logger

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
    elif any(
        chave in slug
        for chave in (" site ", " loja virtual ", " ecommerce ", " e commerce ")
    ):
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


def _montar_payload_pedido(
    webhook_data: dict | None,
    pedido_completo: dict | None,
    payload_atual: dict | None = None,
    ultima_nf: dict | None = None,
) -> dict:
    payload = dict(_dict(payload_atual))
    if isinstance(webhook_data, dict) and webhook_data:
        payload["webhook"] = webhook_data
    pedido_base = (
        pedido_completo
        if isinstance(pedido_completo, dict) and pedido_completo
        else _payload_principal(payload) or _dict(webhook_data)
    )
    payload["pedido"] = pedido_base
    if ultima_nf:
        payload["ultima_nf"] = _consolidar_ultima_nf(
            payload.get("ultima_nf"), ultima_nf
        )
    return payload


def _resumir_ultima_nf_webhook(nf_data: dict | None) -> dict:
    nf_data = _dict(nf_data)
    situacao_nf = _dict(nf_data.get("situacao"))
    return {
        "id": _texto(nf_data.get("id")),
        "numero": _texto(nf_data.get("numero")),
        "serie": _texto(nf_data.get("serie")),
        "data_emissao": _texto(
            _primeiro_preenchido(
                nf_data.get("dataEmissao"), nf_data.get("data_emissao")
            )
        ),
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
        "chave": _texto(
            _primeiro_preenchido(nf_data.get("chaveAcesso"), nf_data.get("chave"))
        ),
        "valor_total": _coerce_float(
            _primeiro_preenchido(
                nf_data.get("valorNota"),
                nf_data.get("valorTotalNf"),
                nf_data.get("valor_total"),
                nf_data.get("valorTotal"),
            )
        ),
    }


def _resumir_ultima_nf_do_pedido_bling(
    pedido_payload: dict | None, *, enriquecer_via_api: bool = True
) -> dict | None:
    pedido_payload = _dict(pedido_payload)
    nota_ref = _dict(
        _primeiro_preenchido(
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    nf_id = _nf_id_valido(
        _primeiro_preenchido(nota_ref.get("id"), nota_ref.get("nfe_id"))
    )

    resumo_payload = {**nota_ref}
    if nf_id:
        resumo_payload["id"] = nf_id
    else:
        resumo_payload.pop("id", None)
        resumo_payload.pop("nfe_id", None)

    resumo_nf = _normalizar_resumo_nf(_resumir_ultima_nf_webhook(resumo_payload))
    if not nf_id:
        return resumo_nf

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
            logger.warning(
                f"[BLING PEDIDO] Falha ao consultar NF {nf_id} vinculada ao pedido: {ultima_falha}"
            )
    except Exception as exc:
        logger.warning(
            f"[BLING PEDIDO] Falha ao enriquecer resumo da NF {nf_id}: {exc}"
        )

    return resumo_nf if resumo_nf.get("id") else None


def _pedido_tem_nf_deterministica(payload: dict | None) -> bool:
    payload = _dict(payload)
    ultima_nf = _ultima_nf_payload_efetiva(payload)
    nf_id = _texto(_primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id")))
    nf_numero = _texto(ultima_nf.get("numero"))
    return bool(nf_numero or (nf_id and nf_id not in {"0", "-1"}))


def _resolver_canal_pedido(payload: dict | None, canal_salvo: str | None):
    pedido_payload = _payload_principal(payload)
    marketplace = _dict(pedido_payload.get("marketplace"))
    loja = _dict(
        _primeiro_preenchido(
            pedido_payload.get("loja"), pedido_payload.get("lojaVirtual")
        )
    )
    numero_pedido_loja = _texto(
        _primeiro_preenchido(
            pedido_payload.get("numeroPedidoLoja"),
            pedido_payload.get("numeroLoja"),
            pedido_payload.get("numeroPedido"),
            pedido_payload.get("numero"),
        )
    )

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
    item = (
        _dict(item_payload.get("item"))
        if isinstance(item_payload, dict) and isinstance(item_payload.get("item"), dict)
        else _dict(item_payload)
    )
    produto = _dict(item.get("produto"))
    sku = _texto(
        _primeiro_preenchido(
            item.get("codigo"),
            item.get("sku"),
            produto.get("codigo"),
            produto.get("sku"),
        )
    )
    return {
        "sku": sku,
        "descricao": _texto(
            _primeiro_preenchido(
                item.get("descricao"), item.get("nome"), produto.get("nome")
            )
        ),
        "quantidade": _coerce_float(item.get("quantidade"), 0.0) or 0.0,
        "valor_unitario": _coerce_float(
            _primeiro_preenchido(
                item.get("valor"),
                item.get("valorUnitario"),
                item.get("preco"),
                item.get("precoUnitario"),
            )
        ),
        "desconto": _coerce_float(
            _primeiro_preenchido(item.get("desconto"), item.get("valorDesconto"))
        ),
        "total": _coerce_float(
            _primeiro_preenchido(item.get("total"), item.get("valorTotal"))
        ),
        "produto_bling_id": _texto(produto.get("id")),
    }


def _serializar_itens_pedido(
    pedido_payload: dict, itens_db: list[PedidoIntegradoItem]
) -> list[dict]:
    payload_itens = [
        _normalizar_item_payload(item) for item in (pedido_payload.get("itens") or [])
    ]
    usados: set[int] = set()
    itens_serializados = []

    for item_db in itens_db:
        idx_match = next(
            (
                idx
                for idx, item_payload in enumerate(payload_itens)
                if idx not in usados
                and (
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

        itens_serializados.append(
            {
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
            }
        )

    for idx, payload_item in enumerate(payload_itens):
        if idx in usados:
            continue
        itens_serializados.append(
            {
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
            }
        )

    return itens_serializados


def _acoes_operacionais_pedido(
    pedido: PedidoIntegrado, duplicidade: dict | None = None
) -> dict:
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
    contato = _dict(
        _primeiro_preenchido(
            pedido_payload.get("contato"), pedido_payload.get("cliente")
        )
    )
    loja = _dict(pedido_payload.get("loja"))
    ultima_nf = _ultima_nf_payload_efetiva(payload)
    situacao = _dict(pedido_payload.get("situacao"))
    canal, canal_label, canal_origem = _resolver_canal_pedido(payload, pedido.canal)
    duplicidade = _dict(duplicidade)

    return {
        "id": pedido.id,
        "pedido_bling_id": pedido.pedido_bling_id,
        "pedido_bling_numero": _texto(
            _primeiro_preenchido(
                pedido.pedido_bling_numero, pedido_payload.get("numero")
            )
        ),
        "numero_pedido_loja": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"), pedido_payload.get("numeroLoja")
            )
        ),
        "numero_pedido_canal": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoCanalVenda"),
                pedido_payload.get("numeroPedidoCanal"),
                pedido_payload.get("numeroPedidoMarketplace"),
                pedido_payload.get("numeroPedido"),
            )
        ),
        "canal": canal,
        "canal_label": canal_label,
        "canal_origem": canal_origem,
        "status": pedido.status,
        "criado_em": _dt_iso(pedido.criado_em),
        "expira_em": _dt_iso(pedido.expira_em),
        "confirmado_em": _dt_iso(pedido.confirmado_em),
        "cancelado_em": _dt_iso(pedido.cancelado_em),
        "data_pedido": _texto(
            _primeiro_preenchido(
                pedido_payload.get("data"),
                pedido_payload.get("dataPedido"),
                pedido_payload.get("dataSaida"),
            )
        ),
        "loja": {
            "id": loja.get("id"),
            "nome": _texto(loja.get("nome")),
        },
        "cliente": {
            "nome": _texto(
                _primeiro_preenchido(contato.get("nome"), contato.get("descricao"))
            ),
            "documento": _texto(
                _primeiro_preenchido(
                    contato.get("numeroDocumento"),
                    contato.get("cpfCnpj"),
                    contato.get("cpf"),
                    contato.get("cnpj"),
                )
            ),
            "email": _texto(contato.get("email")),
            "telefone": _texto(
                _primeiro_preenchido(contato.get("telefone"), contato.get("celular"))
            ),
        },
        "financeiro": {
            "total": _coerce_float(
                _primeiro_preenchido(
                    pedido_payload.get("total"), pedido_payload.get("valorTotal")
                )
            ),
            "desconto": _coerce_float(
                _primeiro_preenchido(
                    pedido_payload.get("desconto"), pedido_payload.get("valorDesconto")
                )
            ),
            "frete": _coerce_float(
                _primeiro_preenchido(
                    pedido_payload.get("frete"),
                    _dict(pedido_payload.get("transporte")).get("frete"),
                )
            ),
        },
        "situacao_bling": {
            "codigo": _situacao_codigo_bling(
                _primeiro_preenchido(situacao, pedido_payload.get("situacao"))
            ),
            "descricao": _texto(
                _primeiro_preenchido(
                    situacao.get("descricao"),
                    situacao.get("nome"),
                    situacao.get("descricaoInterna"),
                )
            ),
        },
        "nota_fiscal": {
            "id": _texto(
                _primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))
            ),
            "numero": _texto(ultima_nf.get("numero")),
            "serie": _texto(ultima_nf.get("serie")),
            "situacao": _texto(
                _primeiro_preenchido(ultima_nf.get("situacao"), ultima_nf.get("status"))
            ),
            "chave": _texto(
                _primeiro_preenchido(
                    ultima_nf.get("chaveAcesso"), ultima_nf.get("chave")
                )
            ),
        },
        "observacoes": _texto(
            _primeiro_preenchido(
                pedido_payload.get("observacoes"),
                pedido_payload.get("observacao"),
                pedido_payload.get("observacoesInternas"),
            )
        ),
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
