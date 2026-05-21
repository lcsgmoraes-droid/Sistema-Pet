"""
Helpers de contexto para consultas de movimentacoes de estoque.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.estoque_reserva_service import EstoqueReservaService
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import Produto


_NF_STATUS_AUTORIZADA_CODES = {2, 5, 9}

_CANAL_LABELS = {
    "full": "FULL (geral)",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
    "site": "Site",
    "app": "App",
    "whatsapp": "WhatsApp",
    "bling": "Bling",
    "online": "Online",
    "loja_fisica": "Loja Física",
    "transferencia_parceiro": "Transferencia Parceiro",
}


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _label_canal_movimentacao(canal: str | None) -> str | None:
    texto = _texto_limpo(canal)
    if not texto:
        return None
    return _CANAL_LABELS.get(texto, texto.replace("_", " ").title())


def _resumo_nf_pedido_integrado(pedido: PedidoIntegrado | None) -> dict:
    if not pedido or not isinstance(pedido.payload, dict):
        return {}

    payload = pedido.payload
    pedido_payload = payload.get("pedido") if isinstance(payload.get("pedido"), dict) else payload
    resumo_nf: dict = {}

    for candidato in (
        pedido_payload.get("notaFiscal"),
        pedido_payload.get("nota"),
        pedido_payload.get("nfe"),
        payload.get("ultima_nf"),
    ):
        if not isinstance(candidato, dict):
            continue
        for chave, valor in candidato.items():
            if valor in (None, "", [], {}):
                continue
            resumo_nf[chave] = valor

    return resumo_nf


def _numero_nf_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    return _texto_limpo(_resumo_nf_pedido_integrado(pedido).get("numero"))


def _numero_pedido_loja_integrado(pedido: PedidoIntegrado | None) -> str | None:
    payload_bruto = getattr(pedido, "payload", None)
    payload = payload_bruto if isinstance(payload_bruto, dict) else {}
    pedido_payload = payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    webhook_payload = payload.get("webhook") if isinstance(payload.get("webhook"), dict) else {}

    for candidato in (
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroPedido"),
        webhook_payload.get("numeroLoja"),
        webhook_payload.get("numeroPedidoLoja"),
        payload.get("numeroLoja"),
        payload.get("numeroPedidoLoja"),
    ):
        texto = _texto_limpo(candidato)
        if texto:
            return texto
    return None


def _nf_status_autorizado(*, situacao_codigo=None, situacao: str | None = None) -> bool:
    try:
        if situacao_codigo is not None and int(situacao_codigo) in _NF_STATUS_AUTORIZADA_CODES:
            return True
    except (TypeError, ValueError):
        pass

    texto = _texto_limpo(situacao)
    if not texto:
        return False

    texto_lower = texto.lower()
    return any(token in texto_lower for token in ("autoriz", "emitida", "emitido"))


def _registro_nf_compativel_com_pedido_integrado(
    pedido: PedidoIntegrado | None,
    registro: BlingNotaFiscalCache | None,
) -> bool:
    if not pedido or not registro:
        return False

    pedido_bling_id = _texto_limpo(getattr(pedido, "pedido_bling_id", None))
    numero_pedido_loja = _numero_pedido_loja_integrado(pedido)
    registro_pedido_bling_id = _texto_limpo(getattr(registro, "pedido_bling_id_ref", None))
    registro_numero_pedido_loja = _texto_limpo(getattr(registro, "numero_pedido_loja", None))

    if registro_pedido_bling_id and pedido_bling_id:
        return registro_pedido_bling_id == pedido_bling_id

    if registro_numero_pedido_loja and numero_pedido_loja:
        return registro_numero_pedido_loja == numero_pedido_loja

    return not registro_pedido_bling_id and not registro_numero_pedido_loja


def _buscar_cache_nf_por_id(
    db: Session,
    pedido: PedidoIntegrado | None,
    nf_id: str | None,
) -> BlingNotaFiscalCache | None:
    nf_id = _texto_limpo(nf_id)
    if not pedido or not nf_id or nf_id in {"0", "-1"}:
        return None

    query = db.query(BlingNotaFiscalCache).filter(
        BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
        BlingNotaFiscalCache.bling_id == nf_id,
    )
    if hasattr(query, "order_by"):
        query = query.order_by(
            BlingNotaFiscalCache.detalhada_em.desc().nullslast(),
            BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
            BlingNotaFiscalCache.id.desc(),
        )
    return query.first()


def _obter_cache_nf_pedido_integrado(
    db: Session,
    pedido: PedidoIntegrado | None,
    resumo_nf: dict,
) -> BlingNotaFiscalCache | None:
    if not pedido:
        return None

    nf_id = _texto_limpo(resumo_nf.get("id") or resumo_nf.get("nfe_id"))
    if nf_id and nf_id not in {"0", "-1"}:
        registro = _buscar_cache_nf_por_id(db, pedido, nf_id)
        if registro and _registro_nf_compativel_com_pedido_integrado(pedido, registro):
            return registro

    pedido_bling_id = _texto_limpo(getattr(pedido, "pedido_bling_id", None))
    if pedido_bling_id:
        query = db.query(BlingNotaFiscalCache).filter(
            BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
            BlingNotaFiscalCache.pedido_bling_id_ref == pedido_bling_id,
        )
        if hasattr(query, "order_by"):
            query = query.order_by(
                BlingNotaFiscalCache.data_emissao.desc().nullslast(),
                BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
                BlingNotaFiscalCache.id.desc(),
            )
        registro = query.first()
        if registro and _registro_nf_compativel_com_pedido_integrado(pedido, registro):
            return registro

    numero_pedido_loja = _numero_pedido_loja_integrado(pedido)
    if numero_pedido_loja:
        query = db.query(BlingNotaFiscalCache).filter(
            BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
            BlingNotaFiscalCache.numero_pedido_loja == numero_pedido_loja,
        )
        if hasattr(query, "order_by"):
            query = query.order_by(
                BlingNotaFiscalCache.data_emissao.desc().nullslast(),
                BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
                BlingNotaFiscalCache.id.desc(),
            )
        registro = query.first()
        if registro and _registro_nf_compativel_com_pedido_integrado(pedido, registro):
            return registro

    return None


def _contexto_nf_pedido_integrado(db: Session, pedido: PedidoIntegrado | None) -> dict:
    resumo_nf = dict(_resumo_nf_pedido_integrado(pedido))
    registro_resumo = _buscar_cache_nf_por_id(
        db,
        pedido,
        resumo_nf.get("id") or resumo_nf.get("nfe_id"),
    )
    if registro_resumo and not _registro_nf_compativel_com_pedido_integrado(pedido, registro_resumo):
        resumo_nf = {}
    registro = _obter_cache_nf_pedido_integrado(db, pedido, resumo_nf)

    if registro and (
        getattr(registro, "bling_id", None)
        or getattr(registro, "numero", None)
        or getattr(registro, "status", None)
    ):
        resumo_nf.setdefault("id", _texto_limpo(getattr(registro, "bling_id", None)))
        resumo_nf.setdefault("nfe_id", _texto_limpo(getattr(registro, "bling_id", None)))
        resumo_nf.setdefault("numero", _texto_limpo(getattr(registro, "numero", None)))
        resumo_nf.setdefault("serie", _texto_limpo(getattr(registro, "serie", None)))
        resumo_nf.setdefault("situacao", _texto_limpo(getattr(registro, "status", None)))
        resumo_nf.setdefault("status", _texto_limpo(getattr(registro, "status", None)))
        resumo_nf.setdefault("modelo", getattr(registro, "modelo", None))

    nf_id = _texto_limpo(resumo_nf.get("id") or resumo_nf.get("nfe_id"))
    nf_numero = _texto_limpo(resumo_nf.get("numero"))
    situacao_codigo = resumo_nf.get("situacao_codigo")
    situacao = _texto_limpo(
        resumo_nf.get("situacao")
        or resumo_nf.get("status")
    )

    return {
        "id": nf_id,
        "numero": nf_numero,
        "serie": _texto_limpo(resumo_nf.get("serie")),
        "situacao": situacao,
        "situacao_codigo": situacao_codigo,
        "autorizada": _nf_status_autorizado(
            situacao_codigo=situacao_codigo,
            situacao=situacao,
        ),
    }


def _canal_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    if not pedido:
        return None

    try:
        from app.integracao_bling_pedido_routes import _resolver_canal_pedido

        canal, _, _ = _resolver_canal_pedido(
            pedido.payload if isinstance(pedido.payload, dict) else {},
            getattr(pedido, "canal", None),
        )
        return _texto_limpo(canal)
    except Exception:
        return _texto_limpo(getattr(pedido, "canal", None))


def _observacao_exibicao_movimentacao_bling(
    *,
    canal: str | None,
    nf_numero: str | None,
    observacao_original: str | None,
) -> str | None:
    canal_label = _label_canal_movimentacao(canal)
    if nf_numero and canal_label:
        return f"Venda {canal_label} NF {nf_numero}"
    if nf_numero:
        return f"Venda NF {nf_numero}"
    if canal_label:
        return f"Venda {canal_label}"
    return _texto_limpo(observacao_original)


def _coerce_float_local(valor, default: float | None = None) -> float | None:
    try:
        if valor is None or valor == "":
            return default
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _valor_total_nf_pedido_integrado(pedido: PedidoIntegrado | None) -> float | None:
    resumo_nf = _resumo_nf_pedido_integrado(pedido)
    if not resumo_nf:
        return None

    totais_nf = resumo_nf.get("totais") if isinstance(resumo_nf.get("totais"), dict) else {}

    for candidato in (
        resumo_nf.get("valor_total"),
        resumo_nf.get("valorNota"),
        resumo_nf.get("valorNotaNf"),
        resumo_nf.get("valorTotalNf"),
        resumo_nf.get("valorTotal"),
        resumo_nf.get("total"),
        totais_nf.get("valorTotal"),
        totais_nf.get("valor_total"),
        totais_nf.get("total"),
    ):
        valor = _coerce_float_local(candidato)
        if valor and valor > 0:
            return valor
    return None


def _itens_nf_pedido_integrado(pedido: PedidoIntegrado | None) -> list[dict]:
    resumo_nf = _resumo_nf_pedido_integrado(pedido)
    if not resumo_nf:
        return []

    try:
        from app.nfe_routes import (
            _detalhe_nota_valido,
            _normalizar_item_nota,
            _obter_detalhe_nfe_cache,
        )
    except Exception:
        return []

    itens_resumo = resumo_nf.get("itens") if isinstance(resumo_nf.get("itens"), list) else []
    if itens_resumo:
        return [
            _normalizar_item_nota(item_nf)
            for item_nf in itens_resumo
            if isinstance(item_nf, dict)
        ]

    nf_id = _texto_limpo(resumo_nf.get("id") or resumo_nf.get("nfe_id"))
    if not nf_id:
        return []

    try:
        nf_id_int = int(nf_id)
    except (TypeError, ValueError):
        return []

    modelos_tentativa: list[int | None] = []
    for candidato in (
        resumo_nf.get("modelo"),
        resumo_nf.get("modeloDocumento"),
        resumo_nf.get("modelo_nf"),
    ):
        modelo = _coerce_float_local(candidato)
        if modelo in (55.0, 65.0):
            modelos_tentativa.append(int(modelo))
    modelos_tentativa.extend([55, 65, None])

    detalhe_nf = None
    modelos_consultados: set[str] = set()
    for modelo in modelos_tentativa:
        chave_modelo = str(modelo or "")
        if chave_modelo in modelos_consultados:
            continue
        modelos_consultados.add(chave_modelo)

        detalhe_nf = _obter_detalhe_nfe_cache(
            pedido.tenant_id,
            nf_id_int,
            modelo,
        )
        if _detalhe_nota_valido(detalhe_nf):
            break

    if not _detalhe_nota_valido(detalhe_nf):
        return []

    itens_cache = detalhe_nf.get("itens") if isinstance(detalhe_nf.get("itens"), list) else []
    return [
        _normalizar_item_nota(item_nf)
        for item_nf in itens_cache
        if isinstance(item_nf, dict)
    ]


def _preco_venda_nf_unitario_pedido_integrado(
    pedido: PedidoIntegrado | None,
    itens_relacionados: list[dict],
) -> float | None:
    itens_nf = _itens_nf_pedido_integrado(pedido)
    if not itens_nf:
        return None

    skus_relacionados = {
        _texto_limpo(item.get("sku"))
        for item in itens_relacionados
        if _texto_limpo(item.get("sku"))
    }

    itens_nf_relacionados = []
    for item_nf in itens_nf:
        codigo_nf = _texto_limpo(item_nf.get("codigo"))
        if skus_relacionados and codigo_nf and codigo_nf in skus_relacionados:
            itens_nf_relacionados.append(item_nf)

    if not itens_nf_relacionados and len(itens_nf) == 1 and len(itens_relacionados) == 1:
        itens_nf_relacionados = [itens_nf[0]]

    if not itens_nf_relacionados:
        return None

    quantidade_total = sum(
        _coerce_float_local(item_nf.get("quantidade"), 0.0) or 0.0
        for item_nf in itens_nf_relacionados
    )
    valor_total = sum(
        (
            _coerce_float_local(item_nf.get("valor_total"), None)
            if _coerce_float_local(item_nf.get("valor_total"), None) is not None
            else (
                (_coerce_float_local(item_nf.get("valor_unitario"), 0.0) or 0.0)
                * (_coerce_float_local(item_nf.get("quantidade"), 0.0) or 0.0)
            )
        )
        for item_nf in itens_nf_relacionados
    )

    if valor_total > 0 and quantidade_total > 0:
        return round(valor_total / quantidade_total, 2)

    for item_nf in itens_nf_relacionados:
        valor_unitario = _coerce_float_local(item_nf.get("valor_unitario"))
        if valor_unitario and valor_unitario > 0:
            return round(valor_unitario, 2)

    return None


def _itens_payload_pedido_integrado(pedido: PedidoIntegrado | None) -> list[dict]:
    if not pedido or not isinstance(pedido.payload, dict):
        return []

    try:
        from app.integracao_bling_pedido_routes import _normalizar_item_payload, _payload_principal

        pedido_payload = _payload_principal(pedido.payload)
        return [
            _normalizar_item_payload(item)
            for item in (pedido_payload.get("itens") or [])
            if isinstance(item, dict)
        ]
    except Exception:
        return []


def _itens_salvos_pedido_integrado(
    db: Session,
    pedido: PedidoIntegrado | None,
) -> list[dict]:
    if not pedido or not getattr(pedido, "id", None):
        return []

    try:
        linhas = (
            db.query(PedidoIntegradoItem)
            .filter(
                PedidoIntegradoItem.tenant_id == pedido.tenant_id,
                PedidoIntegradoItem.pedido_integrado_id == pedido.id,
            )
            .order_by(PedidoIntegradoItem.id.asc())
            .all()
        )
    except Exception:
        return []

    itens = []
    for item in linhas:
        sku = _texto_limpo(getattr(item, "sku", None))
        quantidade = _coerce_float_local(getattr(item, "quantidade", None), 0.0) or 0.0
        if not sku and quantidade <= 0:
            continue
        itens.append(
            {
                "sku": sku,
                "codigo": sku,
                "descricao": _texto_limpo(getattr(item, "descricao", None)),
                "quantidade": quantidade,
            }
        )
    return itens


def _valor_total_pedido_integrado(pedido: PedidoIntegrado | None) -> float | None:
    if not pedido or not isinstance(pedido.payload, dict):
        return None

    payload = pedido.payload
    pedido_payload = payload.get("pedido") if isinstance(payload.get("pedido"), dict) else payload
    financeiro = pedido_payload.get("financeiro") if isinstance(pedido_payload.get("financeiro"), dict) else {}

    valor_nf = _valor_total_nf_pedido_integrado(pedido)
    if valor_nf and valor_nf > 0:
        return valor_nf

    for candidato in (
        financeiro.get("total"),
        pedido_payload.get("total"),
        pedido_payload.get("valorTotal"),
        pedido_payload.get("valor_total"),
    ):
        valor = _coerce_float_local(candidato)
        if valor and valor > 0:
            return valor
    return None


def _contexto_venda_pedido_integrado(
    db: Session,
    pedido: PedidoIntegrado | None,
    produto_id: int,
) -> dict:
    nf_contexto = _contexto_nf_pedido_integrado(db, pedido)
    contexto = {
        "canal": _canal_pedido_integrado(pedido),
        "nf_id": nf_contexto.get("id"),
        "nf_numero": nf_contexto.get("numero"),
        "preco_venda_unitario": None,
    }
    if not pedido:
        return contexto

    if not nf_contexto.get("numero"):
        return contexto

    try:
        from app.services.bling_nf_service import produto_ids_estoque_afetados
    except Exception:
        return contexto

    itens_pedido = _itens_payload_pedido_integrado(pedido)
    if not itens_pedido:
        itens_pedido = _itens_salvos_pedido_integrado(db, pedido)

    if not itens_pedido:
        return contexto

    produtos_por_sku: dict[str, Produto | None] = {}
    itens_relacionados: list[dict] = []
    produto_id_int = int(produto_id)

    for item in itens_pedido:
        sku = _texto_limpo(item.get("sku"))
        if not sku:
            continue

        if sku not in produtos_por_sku:
            produtos_por_sku[sku] = (
                db.query(Produto)
                .filter(
                    Produto.tenant_id == pedido.tenant_id,
                    or_(Produto.codigo == sku, Produto.codigo_barras == sku),
                )
                .first()
            )

        produto_item = produtos_por_sku.get(sku)
        if not produto_item:
            continue

        if produto_id_int in produto_ids_estoque_afetados(db=db, produto=produto_item):
            itens_relacionados.append(item)

    if not itens_relacionados:
        return contexto

    quantidade_total = sum(float(item.get("quantidade") or 0) for item in itens_relacionados)
    preco_nf_unitario = _preco_venda_nf_unitario_pedido_integrado(pedido, itens_relacionados)
    if preco_nf_unitario and preco_nf_unitario > 0:
        contexto["preco_venda_unitario"] = preco_nf_unitario
        return contexto

    total_nf = _valor_total_nf_pedido_integrado(pedido)
    if len(itens_relacionados) == 1 and len(itens_pedido) == 1 and total_nf and quantidade_total > 0:
        contexto["preco_venda_unitario"] = round(total_nf / quantidade_total, 2)

    return contexto


def _detalhar_reservas_ativas_produto(
    db: Session,
    *,
    tenant_id,
    produto_id: int,
) -> list[dict]:
    linhas = (
        db.query(PedidoIntegradoItem, PedidoIntegrado)
        .join(PedidoIntegrado, PedidoIntegrado.id == PedidoIntegradoItem.pedido_integrado_id)
        .filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegradoItem.liberado_em.is_(None),
            PedidoIntegradoItem.vendido_em.is_(None),
        )
        .order_by(PedidoIntegrado.criado_em.desc(), PedidoIntegrado.id.desc())
        .all()
    )
    if not linhas:
        return []

    skus = list(
        dict.fromkeys(
            _texto_limpo(item.sku)
            for item, _pedido in linhas
            if _texto_limpo(item.sku)
        )
    )
    produtos_por_sku = EstoqueReservaService._produtos_por_sku(db, tenant_id, skus)
    kit_ids = list(
        dict.fromkeys(
            int(produto.id)
            for produto in produtos_por_sku.values()
            if getattr(produto, "id", None) and EstoqueReservaService._usa_composicao_virtual(produto)
        )
    )
    componentes_por_kit = EstoqueReservaService._componentes_por_kit(db, kit_ids)

    reservas_por_pedido: dict[int, dict] = {}
    alvo_id = int(produto_id)

    for item, pedido in linhas:
        sku = _texto_limpo(item.sku)
        if not sku:
            continue

        produto_item = produtos_por_sku.get(sku)
        if not produto_item or not getattr(produto_item, "id", None):
            continue

        detalhes_item: list[dict] = []
        quantidade_item = float(item.quantidade or 0)
        if quantidade_item <= 0:
            continue

        if EstoqueReservaService._usa_composicao_virtual(produto_item):
            for componente in componentes_por_kit.get(int(produto_item.id), []):
                if int(componente.produto_componente_id or 0) != alvo_id:
                    continue
                quantidade_reservada = quantidade_item * float(componente.quantidade or 0)
                if quantidade_reservada <= 0:
                    continue
                detalhes_item.append({
                    "item_id": item.id,
                    "sku": sku,
                    "descricao": item.descricao,
                    "quantidade_item": quantidade_item,
                    "quantidade_reservada_produto": quantidade_reservada,
                    "origem_reserva": "componente_kit_virtual",
                    "kit_origem_id": int(produto_item.id),
                    "kit_origem_sku": _texto_limpo(produto_item.codigo) or _texto_limpo(produto_item.codigo_barras),
                    "kit_origem_nome": _texto_limpo(produto_item.nome),
                })
        elif int(produto_item.id) == alvo_id:
            detalhes_item.append({
                "item_id": item.id,
                "sku": sku,
                "descricao": item.descricao,
                "quantidade_item": quantidade_item,
                "quantidade_reservada_produto": quantidade_item,
                "origem_reserva": "direta",
                "kit_origem_id": None,
                "kit_origem_sku": None,
                "kit_origem_nome": None,
            })

        if not detalhes_item:
            continue

        bucket = reservas_por_pedido.setdefault(
            int(pedido.id),
            {
                "pedido_integrado_id": int(pedido.id),
                "pedido_bling_id": _texto_limpo(pedido.pedido_bling_id),
                "pedido_bling_numero": _texto_limpo(pedido.pedido_bling_numero),
                "numero_pedido_loja": _numero_pedido_loja_integrado(pedido),
                "status": _texto_limpo(pedido.status),
                "canal": _canal_pedido_integrado(pedido),
                "canal_label": _label_canal_movimentacao(_canal_pedido_integrado(pedido)),
                "nf_numero": _numero_nf_pedido_integrado(pedido),
                "criado_em": pedido.criado_em.isoformat() if getattr(pedido, "criado_em", None) else None,
                "expira_em": pedido.expira_em.isoformat() if getattr(pedido, "expira_em", None) else None,
                "quantidade_reservada": 0.0,
                "itens": [],
            },
        )

        for detalhe in detalhes_item:
            bucket["quantidade_reservada"] += float(detalhe["quantidade_reservada_produto"])
            bucket["itens"].append(detalhe)

    return sorted(
        reservas_por_pedido.values(),
        key=lambda item: (
            -(item.get("quantidade_reservada") or 0),
            item.get("criado_em") or "",
            item.get("pedido_bling_numero") or "",
        ),
    )
