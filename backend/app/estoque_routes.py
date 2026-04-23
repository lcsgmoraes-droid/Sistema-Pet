# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
ROTAS DE ESTOQUE - Sistema Pet Shop Pro
Gestão completa de estoque com sincronização Bling

Funcionalidades:
- Entrada manual de estoque
- Saída manual (perdas, avarias, ajustes)
- Transferências entre estoques
- Sincronização bidirecional com Bling
- Entrada por XML (NF-e fornecedor)
- Alertas e relatórios
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel, Field
from decimal import Decimal
import json
import io
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from .security.permissions_decorator import require_permission
from .estoque_reserva_service import EstoqueReservaService
from .pedido_integrado_item_models import PedidoIntegradoItem
from .nfe_cache_models import BlingNotaFiscalCache
from .produtos_models import (
    Produto, ProdutoLote, EstoqueMovimentacao, ProdutoKitComponente
)
from .financeiro_models import (
    CategoriaFinanceira,
    ContaReceber,
    ContaPagar,
    Recebimento,
    Pagamento,
    FormaPagamento,
)
from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .pedido_integrado_models import PedidoIntegrado
from .vendas_models import Venda
from .bling_estoque_sync import sincronizar_bling_background
from .estoque.service import EstoqueService
from .services.email_service import is_email_configured, send_email
import logging
logger = logging.getLogger(__name__)

try:
    import pdfplumber
except Exception:
    pdfplumber = None

router = APIRouter(prefix="/estoque", tags=["Estoque"])

_NF_STATUS_AUTORIZADA_CODES = {2, 5, 9}

_CANAL_LABELS = {
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

_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE = "transf_parceiro"
_MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO = "transf_exc"
_REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO = "transf_excl"
_MODO_BAIXA_TRANSFERENCIA_LABELS = {
    "recebimento": "Recebimento",
    "acerto": "Acerto / Compensacao",
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

    # NF sem referencia local ainda pode ser usada como fallback fraco.
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
        from .integracao_bling_pedido_routes import _resolver_canal_pedido

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
        from .nfe_routes import (
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
        from .integracao_bling_pedido_routes import _normalizar_item_payload, _payload_principal

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
        from .services.bling_nf_service import produto_ids_estoque_afetados
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

# ============================================================================
# SCHEMAS
# ============================================================================

class EntradaEstoqueRequest(BaseModel):
    """Entrada manual de estoque"""
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = None
    motivo: str = Field(default="compra")  # compra, devolucao, ajuste, transferencia
    documento: Optional[str] = None
    observacao: Optional[str] = None
    
    # Dados do lote (se aplicável)
    criar_lote: bool = False
    numero_lote: Optional[str] = None
    data_fabricacao: Optional[str] = None
    data_validade: Optional[str] = None
    
class SaidaEstoqueRequest(BaseModel):
    """Saída manual de estoque"""
    produto_id: int
    quantidade: float = Field(gt=0)
    motivo: str = Field(default="perda")  # perda, avaria, roubo, amostra, uso_interno, devolucao_fornecedor, ajuste
    documento: Optional[str] = None
    observacao: Optional[str] = None
    # Para KIT FÍSICO: se True, desmontou o kit e volta os componentes ao estoque
    retornar_componentes: bool = False


class TransferenciaParceiroItemRequest(BaseModel):
    """Item da transferencia de estoque para parceiro."""
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    valor_total: Optional[float] = Field(default=None, ge=0)


class TransferenciaParceiroRequest(BaseModel):
    """Transferencia de estoque para parceiro com ressarcimento pelo custo."""
    parceiro_id: int
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacao: Optional[str] = None
    itens: List[TransferenciaParceiroItemRequest] = Field(default_factory=list, min_items=1)


class TransferenciaParceiroEnviarEmailRequest(BaseModel):
    email: Optional[str] = None
    assunto: Optional[str] = None
    mensagem: Optional[str] = None


class TransferenciaParceiroCompensacaoContaRequest(BaseModel):
    conta_pagar_id: int
    valor_compensado: float = Field(gt=0)


class TransferenciaParceiroRecebimentoRequest(BaseModel):
    valor_recebido: float = Field(gt=0)
    data_recebimento: date = Field(default_factory=date.today)
    modo_baixa: str = Field(default="recebimento")
    forma_pagamento_id: Optional[int] = None
    compensacoes: List[TransferenciaParceiroCompensacaoContaRequest] = Field(default_factory=list)
    observacao: Optional[str] = None


class TransferenciaParceiroHistoricoMovItem(BaseModel):
    produto_id: int
    produto_nome: str
    codigo: Optional[str] = None
    quantidade: float = 0
    custo_unitario: float = 0
    valor_total: float = 0
    created_at: Optional[datetime] = None


class TransferenciaParceiroContaPagarCompensacaoItem(BaseModel):
    conta_pagar_id: int
    descricao: str
    documento: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_pago: float = 0
    saldo_aberto: float = 0
    observacoes: Optional[str] = None


class TransferenciaParceiroContaPagarCompensacaoResponse(BaseModel):
    items: List[TransferenciaParceiroContaPagarCompensacaoItem] = Field(default_factory=list)
    total: int = 0
    total_disponivel: float = 0


class TransferenciaParceiroPdfConsolidadoRequest(BaseModel):
    conta_receber_ids: List[int] = Field(default_factory=list)
    parceiro_id: Optional[int] = None
    status_filtro: Optional[str] = None
    busca: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None


class TransferenciaParceiroHistoricoItem(BaseModel):
    conta_receber_id: int
    documento: Optional[str] = None
    parceiro_id: Optional[int] = None
    parceiro_nome: str
    parceiro_codigo: Optional[str] = None
    parceiro_email: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_recebimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    modo_baixa: Optional[str] = None
    modo_baixa_label: Optional[str] = None
    forma_pagamento_id: Optional[int] = None
    forma_pagamento_nome: Optional[str] = None
    observacoes: Optional[str] = None
    itens: List[TransferenciaParceiroHistoricoMovItem] = Field(default_factory=list)


class TransferenciaParceiroHistoricoTotais(BaseModel):
    total_registros: int = 0
    valor_total: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    pendentes: int = 0
    recebidas: int = 0
    vencidas: int = 0


class TransferenciaParceiroHistoricoResponse(BaseModel):
    items: List[TransferenciaParceiroHistoricoItem] = Field(default_factory=list)
    totais: TransferenciaParceiroHistoricoTotais
    total: int
    page: int
    page_size: int
    pages: int


class SaidaFullNFItemRequest(BaseModel):
    """Item para baixa de estoque por NF de saida."""
    produto_id: Optional[int] = None
    sku: Optional[str] = None
    quantidade: float = Field(gt=0)


class SaidaFullNFRequest(BaseModel):
    """Baixa em lote de estoque vinculada a uma NF de saida."""
    numero_nf: str
    plataforma: Optional[str] = "full"
    observacao: Optional[str] = None
    itens: List[SaidaFullNFItemRequest]


def _parse_data_lote(valor: Optional[str]) -> Optional[datetime]:
    texto = str(valor or "").strip()
    if not texto:
        return None

    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.replace(" ", "T"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            dt = datetime.fromisoformat(candidato)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            continue

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    return None


def _obter_dre_subcategoria_receita_padrao(db: Session, tenant_id) -> int:
    subcategoria = db.query(DRESubcategoria).join(
        DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id
    ).filter(
        DRESubcategoria.tenant_id == str(tenant_id),
        DRECategoria.tenant_id == str(tenant_id),
        DRESubcategoria.ativo == True,
        DRECategoria.ativo == True,
        DRECategoria.natureza == NaturezaDRE.RECEITA,
    ).order_by(DRECategoria.ordem.asc(), DRESubcategoria.id.asc()).first()
    return subcategoria.id if subcategoria else 1


def _obter_ou_criar_categoria_financeira_transferencia(
    db: Session,
    *,
    tenant_id,
    user_id: int,
) -> CategoriaFinanceira:
    categoria = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == str(tenant_id),
        CategoriaFinanceira.nome == "Transferencia para Parceiro",
        CategoriaFinanceira.tipo == "receita",
    ).first()
    if categoria:
        return categoria

    categoria = CategoriaFinanceira(
        tenant_id=str(tenant_id),
        nome="Transferencia para Parceiro",
        tipo="receita",
        descricao="Ressarcimento de estoque transferido a parceiro sem gerar venda no PDV.",
        dre_subcategoria_id=_obter_dre_subcategoria_receita_padrao(db, tenant_id),
        ativo=True,
        user_id=user_id,
    )
    db.add(categoria)
    db.flush()
    return categoria


def _obter_ou_criar_forma_pagamento_acerto(
    db: Session,
    *,
    tenant_id,
    user_id: int,
) -> FormaPagamento:
    forma = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == str(tenant_id),
        FormaPagamento.nome.ilike("acerto%"),
    ).order_by(FormaPagamento.id.asc()).first()
    if forma:
        if forma.ativo is False:
            forma.ativo = True
            db.add(forma)
            db.flush()
        return forma

    forma = FormaPagamento(
        tenant_id=str(tenant_id),
        nome="Acerto",
        tipo="transferencia",
        taxa_percentual=0,
        taxa_fixa=0,
        prazo_dias=0,
        prazo_recebimento=0,
        ativo=True,
        permite_parcelamento=False,
        max_parcelas=1,
        parcelas_maximas=1,
        gera_contas_receber=False,
        split_parcelas=False,
        user_id=user_id,
    )
    db.add(forma)
    db.flush()
    return forma


def _gerar_codigo_transferencia_parceiro() -> str:
    return f"TRP-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _normalizar_modo_baixa_transferencia(valor: str | None) -> str:
    texto = _texto_limpo(valor)
    modo = (texto or "recebimento").strip().lower()
    if modo not in _MODO_BAIXA_TRANSFERENCIA_LABELS:
        raise HTTPException(
            status_code=400,
            detail="Modo de baixa invalido. Use recebimento ou acerto.",
        )
    return modo


def _label_modo_baixa_transferencia(valor: str | None) -> str | None:
    texto = _texto_limpo(valor)
    if not texto:
        return None
    return _MODO_BAIXA_TRANSFERENCIA_LABELS.get(texto, texto.replace("_", " ").title())


def _buscar_forma_pagamento_transferencia(
    db: Session,
    *,
    tenant_id,
    forma_pagamento_id: int,
) -> FormaPagamento:
    forma = db.query(FormaPagamento).filter(
        FormaPagamento.id == forma_pagamento_id,
        FormaPagamento.tenant_id == str(tenant_id),
    ).first()
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento nao encontrada")
    return forma


def _saldo_conta_receber(conta: ContaReceber) -> float:
    valor_original = float(conta.valor_original or 0)
    valor_recebido = float(conta.valor_recebido or 0)
    saldo = valor_original - valor_recebido
    return round(max(saldo, 0.0), 2)


def _saldo_conta_pagar(conta: ContaPagar) -> float:
    valor_final = float(conta.valor_final or 0)
    valor_pago = float(conta.valor_pago or 0)
    saldo = valor_final - valor_pago
    return round(max(saldo, 0.0), 2)


def _status_conta_pagar_compensacao(conta: ContaPagar) -> tuple[str, str]:
    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    saldo_aberto = _saldo_conta_pagar(conta)
    hoje = date.today()

    if status_atual in {"pago", "recebido"} or saldo_aberto <= 0:
        return "pago", "Paga"
    if status_atual in {"cancelado", "cancelada"}:
        return "cancelado", "Cancelada"
    if status_atual == "parcial":
        if conta.data_vencimento and conta.data_vencimento < hoje:
            return "vencido", "Vencida"
        return "parcial", "Parcial"
    if conta.data_vencimento and conta.data_vencimento < hoje:
        return "vencido", "Vencida"
    return "pendente", "Pendente"


def _status_transferencia_parceiro(conta: ContaReceber) -> tuple[str, str]:
    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    saldo_aberto = _saldo_conta_receber(conta)
    hoje = date.today()

    if status_atual in {"recebido", "pago"} or saldo_aberto <= 0:
        return "recebido", "Recebida"
    if status_atual in {"cancelado", "cancelada"}:
        return "cancelado", "Cancelada"
    if status_atual in {"parcial", "baixa_parcial"}:
        if conta.data_vencimento and conta.data_vencimento < hoje:
            return "vencido", "Vencida"
        return "parcial", "Parcial"
    if conta.data_vencimento and conta.data_vencimento < hoje:
        return "vencido", "Vencida"
    return "pendente", "Pendente"


def _buscar_conta_transferencia_parceiro(
    db: Session,
    tenant_id: int | str,
    conta_receber_id: int,
) -> ContaReceber:
    conta = db.query(ContaReceber).options(
        joinedload(ContaReceber.cliente),
    ).filter(
        ContaReceber.id == conta_receber_id,
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.canal == "transferencia_parceiro",
    ).first()

    if not conta:
        raise HTTPException(status_code=404, detail="Transferencia nao encontrada")

    return conta


def _buscar_transferencias_parceiro_filtradas(
    db: Session,
    *,
    tenant_id: int | str,
    parceiro_id: Optional[int] = None,
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    conta_receber_ids: Optional[list[int]] = None,
) -> list[ContaReceber]:
    termo_busca = (busca or "").strip()
    status_normalizado = (status_filtro or "").strip().lower()

    query = db.query(ContaReceber).options(
        joinedload(ContaReceber.cliente),
        joinedload(ContaReceber.recebimentos).joinedload(Recebimento.forma_pagamento),
    ).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.canal == "transferencia_parceiro",
    )

    if conta_receber_ids:
        query = query.filter(ContaReceber.id.in_(conta_receber_ids))

    if parceiro_id:
        query = query.filter(ContaReceber.cliente_id == parceiro_id)

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)

    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)

    if termo_busca:
        busca_pattern = f"%{termo_busca}%"
        query = query.outerjoin(Cliente, Cliente.id == ContaReceber.cliente_id).filter(
            or_(
                ContaReceber.documento.ilike(busca_pattern),
                ContaReceber.descricao.ilike(busca_pattern),
                ContaReceber.observacoes.ilike(busca_pattern),
                Cliente.nome.ilike(busca_pattern),
                Cliente.codigo.ilike(busca_pattern),
            )
        )

    contas = query.order_by(
        desc(ContaReceber.data_emissao),
        desc(ContaReceber.id),
    ).all()

    if not status_normalizado:
        return contas

    return [
        conta
        for conta in contas
        if _status_transferencia_parceiro(conta)[0] == status_normalizado
    ]


def _buscar_contas_pagar_compensacao_transferencia(
    db: Session,
    *,
    tenant_id: int | str,
    cliente_id: int | None,
) -> list[ContaPagar]:
    if not cliente_id:
        return []

    contas = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == str(tenant_id),
        ContaPagar.fornecedor_id == cliente_id,
        ContaPagar.status.notin_(["pago", "cancelado", "cancelada"]),
    ).order_by(
        ContaPagar.data_vencimento.asc(),
        ContaPagar.id.asc(),
    ).all()

    return [conta for conta in contas if _saldo_conta_pagar(conta) > 0.009]


def _formatar_resumo_compensacoes_transferencia(
    compensacoes_processadas: list[dict],
) -> str | None:
    if not compensacoes_processadas:
        return None

    partes = []
    for item in compensacoes_processadas:
        documento = _texto_limpo(item.get("documento")) or f"Conta #{item['conta_pagar_id']}"
        partes.append(f"{documento} (R$ {float(item['valor_compensado']):.2f})")

    return "Contas compensadas: " + ", ".join(partes)


def _aplicar_compensacoes_contas_pagar_transferencia(
    db: Session,
    *,
    conta_receber: ContaReceber,
    tenant_id: int | str,
    user_id: int,
    data_pagamento: date,
    forma_pagamento: FormaPagamento,
    compensacoes_payload: list[TransferenciaParceiroCompensacaoContaRequest],
) -> list[dict]:
    if not compensacoes_payload:
        return []

    cliente_id = getattr(conta_receber, "cliente_id", None)
    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Esta transferencia nao possui pessoa vinculada para compensacao.",
        )

    ids = [int(item.conta_pagar_id) for item in compensacoes_payload]
    contas = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == str(tenant_id),
        ContaPagar.fornecedor_id == cliente_id,
        ContaPagar.id.in_(ids),
    ).all()
    contas_por_id = {conta.id: conta for conta in contas}

    compensacoes_processadas: list[dict] = []
    documento_transferencia = _texto_limpo(conta_receber.documento) or f"TRP-{conta_receber.id:06d}"

    for item in compensacoes_payload:
        conta_pagar = contas_por_id.get(int(item.conta_pagar_id))
        if not conta_pagar:
            raise HTTPException(
                status_code=404,
                detail=f"Conta a pagar #{item.conta_pagar_id} nao encontrada para essa pessoa.",
            )

        saldo_aberto = _saldo_conta_pagar(conta_pagar)
        valor_compensado = round(float(item.valor_compensado or 0), 2)
        if valor_compensado <= 0:
            raise HTTPException(
                status_code=400,
                detail="Informe um valor de compensacao maior que zero.",
            )
        if valor_compensado - saldo_aberto > 0.01:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"O valor compensado ultrapassa o saldo da conta a pagar #{conta_pagar.id}. "
                    f"Saldo atual: R$ {saldo_aberto:.2f}"
                ),
            )

        novo_valor_pago = round(float(conta_pagar.valor_pago or 0) + valor_compensado, 2)
        conta_pagar.valor_pago = Decimal(str(novo_valor_pago))
        conta_pagar.status = (
            "pago"
            if abs(float(conta_pagar.valor_final or 0) - novo_valor_pago) < 0.01
            else "parcial"
        )
        if conta_pagar.status == "pago":
            conta_pagar.data_pagamento = data_pagamento

        documento_conta = _texto_limpo(conta_pagar.documento) or f"Conta #{conta_pagar.id}"
        observacao_pagamento = (
            f"Compensacao via transferencia {documento_transferencia} "
            f"(conta a receber #{conta_receber.id}) - R$ {valor_compensado:.2f}"
        )
        pagamento = Pagamento(
            conta_pagar_id=conta_pagar.id,
            forma_pagamento_id=forma_pagamento.id,
            valor_pago=Decimal(str(valor_compensado)),
            data_pagamento=data_pagamento,
            observacoes=observacao_pagamento,
            user_id=user_id,
            tenant_id=str(tenant_id),
        )
        db.add(pagamento)

        conta_pagar.observacoes = (
            f"{conta_pagar.observacoes}\n\n{observacao_pagamento}".strip()
            if conta_pagar.observacoes
            else observacao_pagamento
        )

        compensacoes_processadas.append(
            {
                "conta_pagar_id": conta_pagar.id,
                "documento": documento_conta,
                "descricao": conta_pagar.descricao,
                "valor_compensado": valor_compensado,
                "saldo_restante": _saldo_conta_pagar(conta_pagar),
                "status": conta_pagar.status,
            }
        )

    return compensacoes_processadas


def _obter_ultimo_recebimento_transferencia(conta: ContaReceber) -> Recebimento | None:
    recebimentos = list(getattr(conta, "recebimentos", None) or [])
    if not recebimentos:
        return None

    return max(
        recebimentos,
        key=lambda item: (
            item.data_recebimento or date.min,
            getattr(item, "created_at", None) or datetime.min,
            getattr(item, "id", 0) or 0,
        ),
    )


def _detectar_modo_baixa_transferencia(
    recebimento: Recebimento | None,
) -> tuple[str | None, str | None]:
    if not recebimento:
        return None, None

    forma_nome = _texto_limpo(
        getattr(getattr(recebimento, "forma_pagamento", None), "nome", None)
    )
    observacoes = (_texto_limpo(recebimento.observacoes) or "").lower()

    if (forma_nome and forma_nome.lower() == "acerto") or "acerto" in observacoes or "compens" in observacoes:
        return "acerto", _label_modo_baixa_transferencia("acerto")

    return "recebimento", _label_modo_baixa_transferencia("recebimento")


def _listar_itens_transferencia_parceiro(
    db: Session,
    tenant_id: int | str,
    conta_receber_id: int,
) -> list[TransferenciaParceiroHistoricoMovItem]:
    movimentacoes = db.query(EstoqueMovimentacao).options(
        joinedload(EstoqueMovimentacao.produto),
    ).filter(
        EstoqueMovimentacao.tenant_id == str(tenant_id),
        EstoqueMovimentacao.referencia_id == conta_receber_id,
        EstoqueMovimentacao.motivo.in_(
            [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
        ),
    ).order_by(
        EstoqueMovimentacao.created_at.asc(),
        EstoqueMovimentacao.id.asc(),
    ).all()

    itens: list[TransferenciaParceiroHistoricoMovItem] = []
    for mov in movimentacoes:
        itens.append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome if mov.produto else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    return itens


def _restaurar_lotes_consumidos_transferencia(
    db: Session,
    movimentacao: EstoqueMovimentacao,
) -> int:
    bruto = getattr(movimentacao, "lotes_consumidos", None)
    if not bruto:
        return 0

    try:
        lotes = json.loads(bruto) if isinstance(bruto, str) else bruto
    except Exception:
        lotes = []

    restaurados = 0
    for item_lote in lotes or []:
        lote_id = item_lote.get("lote_id")
        quantidade = float(item_lote.get("quantidade") or 0)
        if not lote_id or quantidade <= 0:
            continue

        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
        if not lote:
            continue

        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        if lote.quantidade_disponivel > 0:
            lote.status = "ativo"
        db.add(lote)
        restaurados += 1

    return restaurados


def _gerar_pdf_transferencia_parceiro_bytes(
    conta: ContaReceber,
    parceiro: Cliente | None,
    itens: list[TransferenciaParceiroHistoricoMovItem],
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab nao instalada. Execute: pip install reportlab",
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TransferenciaTitulo",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitulo_style = ParagraphStyle(
        "TransferenciaSubtitulo",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=14,
    )

    elements = [
        Paragraph("TRANSFERENCIA COM RESSARCIMENTO", titulo_style),
        Paragraph(
            "Documento operacional de saida de estoque pelo custo",
            subtitulo_style,
        ),
    ]

    parceiro_nome = parceiro.nome if parceiro else "Pessoa nao encontrada"
    status_resolvido, status_label = _status_transferencia_parceiro(conta)
    saldo_aberto = _saldo_conta_receber(conta)
    valor_original = float(conta.valor_original or 0)
    valor_recebido = float(conta.valor_recebido or 0)

    bloco_info = Table(
        [
            ["Documento", conta.documento or f"TRP-{conta.id:06d}", "Pessoa", parceiro_nome],
            ["Emissao", conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-", "Vencimento", conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "-"],
            ["Status", status_label, "Email", getattr(parceiro, "email", None) or "-"],
        ],
        colWidths=[26 * mm, 58 * mm, 22 * mm, 74 * mm],
    )
    bloco_info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(bloco_info)
    elements.append(Spacer(1, 8 * mm))

    tabela_itens = [["Codigo", "Produto", "Qtd", "Custo un.", "Total"]]
    for item in itens:
        tabela_itens.append(
            [
                item.codigo or "-",
                Paragraph(item.produto_nome, styles["BodyText"]),
                f"{float(item.quantidade or 0):.3f}".rstrip("0").rstrip("."),
                f"R$ {float(item.custo_unitario or 0):.2f}",
                f"R$ {float(item.valor_total or 0):.2f}",
            ]
        )

    tabela = Table(
        tabela_itens,
        colWidths=[22 * mm, 84 * mm, 18 * mm, 28 * mm, 28 * mm],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(tabela)
    elements.append(Spacer(1, 6 * mm))

    totais = Table(
        [
            ["Valor transferido", f"R$ {valor_original:.2f}"],
            ["Valor recebido", f"R$ {valor_recebido:.2f}"],
            ["Saldo em aberto", f"R$ {saldo_aberto:.2f}"],
        ],
        colWidths=[48 * mm, 38 * mm],
        hAlign="RIGHT",
    )
    totais.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#b45309") if status_resolvido != "recebido" else colors.HexColor("#047857")),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#94a3b8")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(totais)

    if conta.observacoes:
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph("<b>Observacoes</b>", styles["Heading4"]))
        elements.append(Paragraph((conta.observacoes or "").replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _gerar_pdf_transferencias_parceiro_consolidado_bytes(
    contas: list[ContaReceber],
    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]],
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab nao instalada. Execute: pip install reportlab",
        )

    if not contas:
        raise HTTPException(status_code=404, detail="Nenhuma transferencia encontrada para consolidar")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TransferenciaConsolidadaTitulo",
        parent=styles["Heading1"],
        fontSize=17,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitulo_style = ParagraphStyle(
        "TransferenciaConsolidadaSubtitulo",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    secao_style = ParagraphStyle(
        "TransferenciaConsolidadaSecao",
        parent=styles["Heading4"],
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
        spaceBefore=8,
    )

    pessoas = sorted(
        {
            (conta.cliente.nome if conta.cliente else "Pessoa nao encontrada")
            for conta in contas
        }
    )
    total_transferido = sum(float(conta.valor_original or 0) for conta in contas)
    total_recebido = sum(float(conta.valor_recebido or 0) for conta in contas)
    total_saldo = sum(_saldo_conta_receber(conta) for conta in contas)
    datas_emissao = [conta.data_emissao for conta in contas if conta.data_emissao]
    periodo_texto = "-"
    if datas_emissao:
        periodo_texto = (
            f"{min(datas_emissao).strftime('%d/%m/%Y')} ate "
            f"{max(datas_emissao).strftime('%d/%m/%Y')}"
        )

    elements = [
        Paragraph("TRANSFERENCIAS CONSOLIDADAS", titulo_style),
        Paragraph(
            "Relatorio unico para acerto por periodo ou selecao manual",
            subtitulo_style,
        ),
    ]

    resumo = Table(
        [
            ["Pessoas", ", ".join(pessoas[:4]) + ("..." if len(pessoas) > 4 else "")],
            ["Periodo", periodo_texto],
            ["Lancamentos", str(len(contas))],
            ["Valor transferido", f"R$ {total_transferido:.2f}"],
            ["Valor recebido", f"R$ {total_recebido:.2f}"],
            ["Saldo em aberto", f"R$ {total_saldo:.2f}"],
        ],
        colWidths=[34 * mm, 144 * mm],
    )
    resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(resumo)
    elements.append(Spacer(1, 5 * mm))

    tabela_documentos = [["Documento", "Pessoa", "Emissao", "Status", "Valor", "Saldo"]]
    for conta in contas:
        pessoa = conta.cliente.nome if conta.cliente else "Pessoa nao encontrada"
        status_label = _status_transferencia_parceiro(conta)[1]
        tabela_documentos.append(
            [
                conta.documento or f"TRP-{conta.id:06d}",
                Paragraph(pessoa, styles["BodyText"]),
                conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-",
                status_label,
                f"R$ {float(conta.valor_original or 0):.2f}",
                f"R$ {_saldo_conta_receber(conta):.2f}",
            ]
        )

    tabela_resumo = Table(
        tabela_documentos,
        colWidths=[28 * mm, 62 * mm, 22 * mm, 24 * mm, 28 * mm, 24 * mm],
        repeatRows=1,
    )
    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(tabela_resumo)
    elements.append(Spacer(1, 5 * mm))

    for conta in contas:
        parceiro_nome = conta.cliente.nome if conta.cliente else "Pessoa nao encontrada"
        documento = conta.documento or f"TRP-{conta.id:06d}"
        status_label = _status_transferencia_parceiro(conta)[1]
        elements.append(
            Paragraph(
                f"{documento} | {parceiro_nome} | {status_label}",
                secao_style,
            )
        )
        elementos_info = [
            f"Emissao: {conta.data_emissao.strftime('%d/%m/%Y') if conta.data_emissao else '-'}",
            f"Vencimento: {conta.data_vencimento.strftime('%d/%m/%Y') if conta.data_vencimento else '-'}",
            f"Valor: R$ {float(conta.valor_original or 0):.2f}",
            f"Recebido: R$ {float(conta.valor_recebido or 0):.2f}",
            f"Saldo: R$ {_saldo_conta_receber(conta):.2f}",
        ]
        elements.append(Paragraph(" | ".join(elementos_info), styles["BodyText"]))

        itens = itens_por_conta.get(conta.id, [])
        if itens:
            tabela_itens = [["Codigo", "Produto", "Qtd", "Custo", "Total"]]
            for item in itens:
                tabela_itens.append(
                    [
                        item.codigo or "-",
                        Paragraph(item.produto_nome, styles["BodyText"]),
                        f"{float(item.quantidade or 0):.3f}".rstrip("0").rstrip("."),
                        f"R$ {float(item.custo_unitario or 0):.2f}",
                        f"R$ {float(item.valor_total or 0):.2f}",
                    ]
                )
            tabela_itens_pdf = Table(
                tabela_itens,
                colWidths=[20 * mm, 88 * mm, 16 * mm, 24 * mm, 24 * mm],
                repeatRows=1,
            )
            tabela_itens_pdf.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            elements.append(Spacer(1, 2 * mm))
            elements.append(tabela_itens_pdf)

        if conta.observacoes:
            elements.append(Spacer(1, 2 * mm))
            elements.append(
                Paragraph(
                    f"<b>Observacoes:</b> {(conta.observacoes or '').replace(chr(10), '<br/>')}",
                    styles["BodyText"],
                )
            )
        elements.append(Spacer(1, 4 * mm))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _montar_email_transferencia_parceiro(
    conta: ContaReceber,
    parceiro: Cliente | None,
    itens: list[TransferenciaParceiroHistoricoMovItem],
    mensagem_extra: str | None = None,
) -> tuple[str, str, str]:
    def _formatar_quantidade_email(valor: float | int | None) -> str:
        texto = f"{float(valor or 0):.3f}"
        return texto.rstrip("0").rstrip(".")

    parceiro_nome = parceiro.nome if parceiro else "Pessoa nao encontrada"
    documento = conta.documento or f"TRP-{conta.id:06d}"
    status_label = _status_transferencia_parceiro(conta)[1]
    valor_original = float(conta.valor_original or 0)
    observacoes = (conta.observacoes or "").strip()
    mensagem_extra = (mensagem_extra or "").strip()

    itens_html = "".join(
        f"<tr>"
        f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;'>{item.produto_nome}</td>"
        f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>{_formatar_quantidade_email(item.quantidade)}"
        f"</td><td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>R$ {float(item.custo_unitario or 0):.2f}</td>"
        f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>R$ {float(item.valor_total or 0):.2f}</td>"
        f"</tr>"
        for item in itens
    )

    assunto = f"Transferencia {documento} - ressarcimento de estoque"
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#0f172a;max-width:720px;margin:0 auto;">
        <div style="background:#0f172a;color:#ffffff;padding:20px 24px;border-radius:12px 12px 0 0;">
          <h1 style="margin:0;font-size:22px;">Transferencia com ressarcimento</h1>
          <p style="margin:8px 0 0;opacity:0.9;">Documento {documento} • {parceiro_nome}</p>
        </div>
        <div style="border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;padding:24px;">
          <p>Ola,</p>
          <p>Segue em anexo o PDF da transferencia de estoque com ressarcimento pelo custo.</p>
          <ul>
            <li><strong>Status:</strong> {status_label}</li>
            <li><strong>Emissao:</strong> {conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-"}</li>
            <li><strong>Vencimento:</strong> {conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "-"}</li>
            <li><strong>Total:</strong> R$ {valor_original:.2f}</li>
          </ul>
          <table style="width:100%;border-collapse:collapse;margin-top:16px;">
            <thead>
              <tr style="background:#f8fafc;color:#334155;">
                <th style="padding:8px 10px;text-align:left;">Produto</th>
                <th style="padding:8px 10px;text-align:right;">Qtd</th>
                <th style="padding:8px 10px;text-align:right;">Custo un.</th>
                <th style="padding:8px 10px;text-align:right;">Total</th>
              </tr>
            </thead>
            <tbody>{itens_html}</tbody>
          </table>
          {f"<p style='margin-top:16px;'><strong>Observacoes:</strong><br/>{observacoes.replace(chr(10), '<br/>')}</p>" if observacoes else ""}
          {f"<p style='margin-top:16px;'>{mensagem_extra.replace(chr(10), '<br/>')}</p>" if mensagem_extra else ""}
          <p style="margin-top:20px;">Se precisar de qualquer ajuste, basta responder este e-mail.</p>
        </div>
      </body>
    </html>
    """

    linhas_itens = [
        f"- {item.produto_nome}: {_formatar_quantidade_email(item.quantidade)}"
        + f" x R$ {float(item.custo_unitario or 0):.2f} = R$ {float(item.valor_total or 0):.2f}"
        for item in itens
    ]
    text_body = (
        f"Transferencia com ressarcimento\n"
        f"Documento: {documento}\n"
        f"Pessoa: {parceiro_nome}\n"
        f"Status: {status_label}\n"
        f"Emissao: {conta.data_emissao.strftime('%d/%m/%Y') if conta.data_emissao else '-'}\n"
        f"Vencimento: {conta.data_vencimento.strftime('%d/%m/%Y') if conta.data_vencimento else '-'}\n"
        f"Total: R$ {valor_original:.2f}\n\n"
        f"Itens:\n" + "\n".join(linhas_itens)
    )
    if observacoes:
        text_body += f"\n\nObservacoes:\n{observacoes}"
    if mensagem_extra:
        text_body += f"\n\nMensagem:\n{mensagem_extra}"

    return assunto, html_body, text_body


def _resolver_valores_item_transferencia(
    produto: Produto,
    item: TransferenciaParceiroItemRequest,
) -> tuple[Decimal, Decimal]:
    quantidade = Decimal(str(float(item.quantidade or 0)))
    custo_padrao = Decimal(str(round(float(produto.preco_custo or 0), 2)))
    custo_informado = (
        Decimal(str(round(float(item.custo_unitario or 0), 2)))
        if item.custo_unitario is not None
        else None
    )
    total_informado = (
        Decimal(str(round(float(item.valor_total or 0), 2)))
        if item.valor_total is not None
        else None
    )

    if total_informado is not None:
        total_item = total_informado.quantize(Decimal("0.01"))
        custo_unitario = (
            (total_item / quantidade).quantize(Decimal("0.01"))
            if quantidade > 0
            else Decimal("0.00")
        )
    else:
        custo_unitario = (custo_informado if custo_informado is not None else custo_padrao).quantize(
            Decimal("0.01")
        )
        total_item = (custo_unitario * quantidade).quantize(Decimal("0.01"))

    if custo_unitario < 0 or total_item < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Os valores do item '{produto.nome}' nao podem ser negativos",
        )

    return custo_unitario, total_item


def _registrar_lote_entrada(
    *,
    db: Session,
    produto: Produto,
    quantidade: float,
    custo_unitario: Optional[float],
    numero_lote: Optional[str],
    data_fabricacao: Optional[str],
    data_validade: Optional[str],
) -> tuple[ProdutoLote | None, int | None]:
    lote = None
    lote_id = None
    if not (numero_lote or data_validade):
        return lote, lote_id

    nome_lote = numero_lote or f"{produto.sku or produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    produto.controle_lote = True

    lote = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto.id,
        ProdutoLote.nome_lote == nome_lote,
    ).first()

    data_val = _parse_data_lote(data_validade)
    data_fab = _parse_data_lote(data_fabricacao)

    if lote:
        lote.quantidade_inicial = float(lote.quantidade_inicial or 0) + quantidade
        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        lote.quantidade_reservada = float(lote.quantidade_reservada or 0)
        lote.data_fabricacao = data_fab or lote.data_fabricacao
        lote.data_validade = data_val or lote.data_validade
        if custo_unitario and custo_unitario > 0:
            lote.custo_unitario = custo_unitario
        lote.status = "ativo"
        logger.info(f"📦 Adicionado ao lote existente: {nome_lote} (+{quantidade})")
    else:
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            data_fabricacao=data_fab,
            data_validade=data_val,
            custo_unitario=custo_unitario or produto.preco_custo,
            ordem_entrada=int(datetime.now().timestamp()),
            status="ativo",
        )
        db.add(lote)
        db.flush()
        logger.info(f"📦 Lote criado: {nome_lote}")

    lote_id = lote.id
    return lote, lote_id


def _resolver_produto_full_nf(db: Session, tenant_id: int, item: SaidaFullNFItemRequest) -> Optional[Produto]:
    if item.produto_id:
        return db.query(Produto).filter(
            Produto.id == item.produto_id,
            Produto.tenant_id == tenant_id,
        ).first()

    if item.sku:
        filtros_sku = [Produto.codigo == item.sku]
        # Compatibilidade com modelos legados que ainda possam expor campo "sku".
        if hasattr(Produto, "sku"):
            filtros_sku.append(getattr(Produto, "sku") == item.sku)

        return db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            or_(*filtros_sku),
        ).first()

    return None


def _observacao_full_nf(numero_nf: str, plataforma: Optional[str], observacao: Optional[str]) -> str:
    base = f"Saida FULL por NF {numero_nf} | plataforma: {plataforma or 'full'}"
    if observacao:
        return f"{base} | {observacao}"
    return base


def _sku_produto(produto: Produto) -> Optional[str]:
    return getattr(produto, "sku", None) or getattr(produto, "codigo", None)


SKU_EXPLICITO_REGEX = re.compile(r"(?:SKU|C[ÓO]DIGO)\s*[:#-]?\s*([A-Z0-9._/-]+)", re.IGNORECASE)
QTD_EXPLICITA_REGEX = re.compile(r"(?:QTD|QUANTIDADE)\s*[:#-]?\s*(\d+(?:[\.,]\d+)?)", re.IGNORECASE)
SKU_QTD_LINHA_REGEX = re.compile(r"^([A-Za-z0-9._\-/]{3,})\s+(\d+(?:[\.,]\d+)?)$")


def _to_float_br(value: str) -> float:
    return float(value.replace(".", "").replace(",", ".")) if "," in value else float(value)


def _extrair_itens_full_pdf(texto: str) -> List[dict]:
    itens_por_sku = defaultdict(float)

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        if not linha:
            continue

        sku_match = SKU_EXPLICITO_REGEX.search(linha)
        qtd_match = QTD_EXPLICITA_REGEX.search(linha)
        if sku_match and qtd_match:
            sku = sku_match.group(1).strip()
            qtd = _to_float_br(qtd_match.group(1))
            if qtd > 0:
                itens_por_sku[sku] += qtd
            continue

        linha_match = SKU_QTD_LINHA_REGEX.match(linha)
        if linha_match:
            sku = linha_match.group(1).strip()
            qtd = _to_float_br(linha_match.group(2))
            if qtd > 0:
                itens_por_sku[sku] += qtd

    return [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]


def _xml_find_text(parent, path_ns: str, path_plain: str, ns: dict) -> Optional[str]:
    elem = parent.find(path_ns, ns)
    if elem is None:
        elem = parent.find(path_plain)
    if elem is None:
        return None
    return (elem.text or "").strip()


def _parse_saida_full_xml(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    inf_nfe = root.find('.//nfe:infNFe', ns)
    if inf_nfe is None:
        inf_nfe = root.find('.//infNFe')
    if inf_nfe is None:
        raise HTTPException(status_code=400, detail="XML invalido: tag infNFe nao encontrada")

    ide = inf_nfe.find('nfe:ide', ns)
    if ide is None:
        ide = inf_nfe.find('ide')
    if ide is None:
        raise HTTPException(status_code=400, detail="XML invalido: tag ide nao encontrada")

    numero_nf = _xml_find_text(ide, 'nfe:nNF', 'nNF', ns)
    if not numero_nf:
        raise HTTPException(status_code=400, detail="Numero da NF nao encontrado no XML")

    itens_por_sku = defaultdict(float)
    det_list = inf_nfe.findall('.//nfe:det', ns)
    if not det_list:
        det_list = inf_nfe.findall('.//det')

    for det in det_list:
        prod = det.find('nfe:prod', ns)
        if prod is None:
            prod = det.find('prod')
        if prod is None:
            continue

        sku = _xml_find_text(prod, 'nfe:cProd', 'cProd', ns)
        qcom = _xml_find_text(prod, 'nfe:qCom', 'qCom', ns)
        if not sku or not qcom:
            continue

        try:
            qtd = float(qcom.replace(',', '.'))
        except ValueError:
            continue

        if qtd > 0:
            itens_por_sku[sku] += qtd

    itens = [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]

    if not itens:
        raise HTTPException(status_code=400, detail="Nenhum item valido (cProd + qCom) foi encontrado no XML")

    return {
        "numero_nf": numero_nf,
        "total_itens": len(itens),
        "itens": itens,
    }


def _processar_item_saida_full_nf(
    db: Session,
    tenant_id: int,
    item: SaidaFullNFItemRequest,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user: User,
):
    produto = _resolver_produto_full_nf(db, tenant_id, item)
    if not produto:
        raise HTTPException(
            status_code=400,
            detail=f"Produto nao encontrado para item (produto_id={item.produto_id}, sku={item.sku})",
        )

    estoque_anterior = float(produto.estoque_atual or 0)
    if estoque_anterior < item.quantidade:
        sku_label = _sku_produto(produto) or 'sem-sku'
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                f"Disponivel: {estoque_anterior}, solicitado: {item.quantidade}"
            ),
        )

    produto.estoque_atual = estoque_anterior - item.quantidade

    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='saida',
        motivo='full_nfe_saida',
        quantidade=item.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=item.quantidade * float(produto.preco_custo or 0),
        documento=numero_nf,
        observacao=observacao_movimentacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    return {
        "produto_id": produto.id,
        "sku": _sku_produto(produto),
        "nome": produto.nome,
        "quantidade": item.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_novo": float(produto.estoque_atual or 0),
    }

class TransferenciaEstoqueRequest(BaseModel):
    """Transferência entre estoques"""
    produto_id: int
    quantidade: float = Field(gt=0)
    estoque_origem: str = Field(default="fisico")  # fisico, ecommerce, consignado
    estoque_destino: str
    motivo: Optional[str] = "transferencia"
    observacao: Optional[str] = None

class MovimentacaoResponse(BaseModel):
    id: int
    produto_id: int
    produto_nome: Optional[str]
    tipo: str
    motivo: Optional[str]
    quantidade: float
    quantidade_anterior: Optional[float]
    quantidade_nova: Optional[float]
    custo_unitario: Optional[float]
    valor_total: Optional[float]
    documento: Optional[str]
    observacao: Optional[str]
    user_id: int
    user_nome: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}

# ============================================================================
# ENTRADA DE ESTOQUE
# ============================================================================

@router.post("/entrada", status_code=status.HTTP_201_CREATED)
def entrada_estoque(
    entrada: EntradaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Entrada manual de estoque
    
    Motivos:
    - compra: Compra de fornecedor
    - devolucao: Devolução de cliente
    - ajuste: Ajuste positivo de inventário
    - transferencia: Transferência recebida
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📥 Entrada de estoque - Produto {entrada.produto_id}, Qtd: {entrada.quantidade}")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == entrada.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: PRODUTO PAI NÃO TEM ESTOQUE
    # ========================================
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Produto '{produto.nome}' possui variações. O estoque deve ser controlado nas variações individuais (cor, tamanho, etc.), não no produto pai."
        )
    
    # ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'VIRTUAL':
        raise HTTPException(
            status_code=400,
            detail=(
                f"❌ Não é possível movimentar estoque manualmente para KIT VIRTUAL. "
                f"O estoque deste kit ('{produto.nome}') é calculado automaticamente "
                f"com base nos componentes que o compõem. "
                f"Para aumentar o estoque, movimente os produtos componentes individualmente."
            )
        )
    
    estoque_anterior = produto.estoque_atual or 0

    # Controle de lotes: se informar lote ou validade, persiste no produto
    lote, lote_id = _registrar_lote_entrada(
        db=db,
        produto=produto,
        quantidade=entrada.quantidade,
        custo_unitario=entrada.custo_unitario,
        numero_lote=entrada.numero_lote,
        data_fabricacao=entrada.data_fabricacao,
        data_validade=entrada.data_validade,
    )
    
    # Atualizar estoque do produto
    produto.estoque_atual = estoque_anterior + entrada.quantidade
    
    # Buscar última entrada para comparação de preço
    ultima_entrada = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto.id,
        EstoqueMovimentacao.tipo == 'entrada',
        EstoqueMovimentacao.custo_unitario != None,
        EstoqueMovimentacao.id != None  # Excluir a entrada atual
    ).order_by(desc(EstoqueMovimentacao.created_at)).first()
    
    custo_anterior = ultima_entrada.custo_unitario if ultima_entrada else produto.preco_custo
    
    # Atualizar preco_custo APENAS se a entrada tiver custo definido
    if entrada.custo_unitario and entrada.custo_unitario > 0:
        produto.preco_custo = entrada.custo_unitario
        logger.info(f"💰 Preço de custo atualizado: R$ {custo_anterior or 0:.2f} → R$ {produto.preco_custo:.2f}")
    variacao_preco = None
    if custo_anterior and entrada.custo_unitario:
        if entrada.custo_unitario > custo_anterior:
            variacao_preco = 'aumento'
        elif entrada.custo_unitario < custo_anterior:
            variacao_preco = 'reducao'
        else:
            variacao_preco = 'estavel'
    
    logger.info(f"✅ Entrada registrada - Custo: R$ {entrada.custo_unitario or 0:.2f} (Anterior: R$ {custo_anterior or 0:.2f})")
    
    # Registrar movimentação
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='entrada',
        motivo=entrada.motivo,
        quantidade=entrada.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=entrada.custo_unitario,
        valor_total=entrada.quantidade * entrada.custo_unitario if entrada.custo_unitario else None,
        lote_id=lote_id,
        documento=entrada.documento,
        observacao=entrada.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    logger.info(f"✅ Entrada registrada - Estoque: {estoque_anterior} → {produto.estoque_atual}")
    
    # ========== AVISE-ME: notificar clientes se estoque voltou do zero ==========
    if estoque_anterior <= 0 and produto.estoque_atual > 0:
        try:
            from app.routes.ecommerce_notify_routes import notificar_clientes_estoque_disponivel
            notificar_clientes_estoque_disponivel(db, str(tenant_id), produto.id, produto.nome)
        except Exception as e_avise:
            logger.warning(f"[AVISE-ME] Erro ao notificar clientes: {e_avise}")

    # ========== SENSIBILIZAÇÃO: KIT FÍSICO - ENTRADA diminui componentes ==========
    # LÓGICA: Entrada no kit físico significa que os unitários foram consumidos para montar os kits
    # Exemplo: Entrada de 5 kits = os componentes DIMINUEM (foram usados para montar)
    componentes_sensibilizados = []
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
        from .produtos_models import ProdutoKitComponente
        
        # Buscar componentes do kit
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto.id
        ).all()
        
        logger.info(f"🧩 KIT FÍSICO - ENTRADA: Consumindo {len(componentes)} componentes do kit '{produto.nome}' (montando {entrada.quantidade} kits)")
        
        for comp in componentes:
            componente_produto = db.query(Produto).filter(
                Produto.id == comp.produto_componente_id
            ).first()
            
            if componente_produto:
                quantidade_componente = entrada.quantidade * comp.quantidade
                estoque_ant_comp = componente_produto.estoque_atual or 0
                
                # ⚠️ IMPORTANTE: DIMINUI os componentes (foram consumidos para montar os kits)
                componente_produto.estoque_atual = estoque_ant_comp - quantidade_componente
                
                # Registrar movimentação do componente como SAÍDA (consumo)
                mov_componente = EstoqueMovimentacao(
                    produto_id=componente_produto.id,
                    tipo='saida',
                    motivo='kit_fisico_montagem',
                    quantidade=quantidade_componente,
                    quantidade_anterior=estoque_ant_comp,
                    quantidade_nova=componente_produto.estoque_atual,
                    custo_unitario=componente_produto.preco_custo,
                    valor_total=quantidade_componente * (componente_produto.preco_custo or 0),
                    observacao=f"Consumo para montagem: componente usado para montar KIT FÍSICO '{produto.nome}' (montados {entrada.quantidade} kit(s))",
                    user_id=current_user.id, tenant_id=tenant_id
                )
                db.add(mov_componente)
                
                componentes_sensibilizados.append({
                    "id": componente_produto.id,
                    "nome": componente_produto.nome,
                    "quantidade": quantidade_componente,
                    "estoque_anterior": estoque_ant_comp,
                    "estoque_novo": componente_produto.estoque_atual
                })
                
                logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (-{quantidade_componente}) [consumido para montagem]")
        
        db.commit()
        logger.info(f"✅ KIT FÍSICO: {len(componentes_sensibilizados)} componentes consumidos na montagem")
    
    # Retornar dict incluindo informação de variação de preço
    response_data = {
        "id": movimentacao.id,
        "produto_id": movimentacao.produto_id,
        "produto_nome": produto.nome,
        "tipo": movimentacao.tipo,
        "motivo": movimentacao.motivo,
        "quantidade": movimentacao.quantidade,
        "custo_unitario": movimentacao.custo_unitario,
        "custo_anterior": custo_anterior,
        "variacao_preco": variacao_preco,
        "quantidade_anterior": movimentacao.quantidade_anterior,
        "quantidade_nova": movimentacao.quantidade_nova,
        "custo_unitario": movimentacao.custo_unitario,
        "valor_total": movimentacao.valor_total,
        "documento": movimentacao.documento,
        "observacao": movimentacao.observacao,
        "user_id": movimentacao.user_id,
        "user_nome": current_user.nome,
        "created_at": movimentacao.created_at,
        "componentes_sensibilizados": componentes_sensibilizados
    }
    
    # Sincronizar estoque com Bling automaticamente
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, "entrada_estoque")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada): {e_sync}")
    
    return response_data

# ============================================================================
# SAÍDA DE ESTOQUE
# ============================================================================

@router.post("/saida", status_code=status.HTTP_201_CREATED)
def saida_estoque(
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Saída manual de estoque
    
    Motivos:
    - perda: Vencimento, deterioração
    - avaria: Produto danificado
    - roubo: Roubo/furto
    - amostra: Amostra grátis
    - uso_interno: Uso da loja
    - devolucao_fornecedor: Devolução ao fornecedor
    - ajuste: Ajuste negativo de inventário
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📤 Saída de estoque - Produto {saida.produto_id}, Qtd: {saida.quantidade}")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == saida.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: PRODUTO PAI NÃO TEM ESTOQUE
    # ========================================
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Produto '{produto.nome}' possui variações. O estoque deve ser controlado nas variações individuais (cor, tamanho, etc.), não no produto pai."
        )
    
    # ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'VIRTUAL':
        raise HTTPException(
            status_code=400,
            detail=(
                f"❌ Não é possível movimentar estoque manualmente para KIT VIRTUAL. "
                f"O estoque deste kit ('{produto.nome}') é calculado automaticamente "
                f"com base nos componentes que o compõem. "
                f"Para reduzir o estoque, movimente os produtos componentes individualmente."
            )
        )
    
    estoque_anterior = produto.estoque_atual or 0
    
    # Validar estoque disponível
    if estoque_anterior < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. Disponível: {estoque_anterior}, Solicitado: {saida.quantidade}"
        )
    
    # Sistema FIFO: consumir lotes mais antigos (se existirem lotes ativos)
    lotes_consumidos = []
    lotes_ativos = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto.id,
        ProdutoLote.quantidade_disponivel > 0,
        ProdutoLote.status == 'ativo'
    ).order_by(ProdutoLote.ordem_entrada).all()
    
    if lotes_ativos:
        # Se tem lotes, usar FIFO
        quantidade_restante = saida.quantidade
        
        for lote in lotes_ativos:
            if quantidade_restante <= 0:
                break
            
            saldo_anterior = lote.quantidade_disponivel  # Guardar saldo antes de consumir
            qtd_consumir = min(lote.quantidade_disponivel, quantidade_restante)
            lote.quantidade_disponivel -= qtd_consumir
            quantidade_restante -= qtd_consumir
            
            if lote.quantidade_disponivel == 0:
                lote.status = 'esgotado'
            
            lotes_consumidos.append({
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade": qtd_consumir,
                "saldo_anterior": saldo_anterior  # Para mostrar (X/Y)
            })
            
            logger.info(f"📦 FIFO: Consumido lote {lote.nome_lote}: {qtd_consumir}")
        
        if quantidade_restante > 0:
            logger.warning(f"⚠️ Lotes insuficientes. Restante será deduzido do estoque geral: {quantidade_restante}")
    
    # Atualizar estoque do produto
    produto.estoque_atual = estoque_anterior - saida.quantidade
    
    # Registrar movimentação
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='saida',
        motivo=saida.motivo,
        quantidade=saida.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=saida.quantidade * (produto.preco_custo or 0),
        lotes_consumidos=json.dumps(lotes_consumidos) if lotes_consumidos else None,
        documento=saida.documento,
        observacao=saida.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    logger.info(f"✅ Saída registrada - Estoque: {estoque_anterior} → {produto.estoque_atual}")
    
    # Alerta se estoque baixo
    if produto.estoque_atual <= (produto.estoque_minimo or 0):
        logger.warning(f"⚠️ Estoque abaixo do mínimo! {produto.nome}: {produto.estoque_atual}")
    
    # ========== SENSIBILIZAÇÃO: KIT FÍSICO - SAÍDA pode retornar componentes ==========
    # LÓGICA: Saída no kit físico PODE retornar os componentes ao estoque (se desmontou o kit)
    # Exemplo: 
    # - Desmontou o kit: retornar_componentes=True → componentes AUMENTAM (voltam ao estoque)
    # - Perdeu/vendeu o kit: retornar_componentes=False → componentes NÃO mexem
    componentes_sensibilizados = []
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
        from .produtos_models import ProdutoKitComponente
        
        # Buscar componentes do kit
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto.id
        ).all()
        
        if saida.retornar_componentes:
            # CASO 1: Desmontou o kit - componentes VOLTAM ao estoque
            logger.info(f"🧩 KIT FÍSICO - DESMONTAGEM: Retornando {len(componentes)} componentes ao estoque (desmontando {saida.quantidade} kits)")
            
            for comp in componentes:
                componente_produto = db.query(Produto).filter(
                    Produto.id == comp.produto_componente_id
                ).first()
                
                if componente_produto:
                    quantidade_componente = saida.quantidade * comp.quantidade
                    estoque_ant_comp = componente_produto.estoque_atual or 0
                    
                    # ⚠️ IMPORTANTE: AUMENTA os componentes (voltam ao estoque após desmontagem)
                    componente_produto.estoque_atual = estoque_ant_comp + quantidade_componente
                    
                    # Registrar movimentação do componente como ENTRADA (devolução)
                    mov_componente = EstoqueMovimentacao(
                        produto_id=componente_produto.id,
                        tipo='entrada',
                        motivo='kit_fisico_desmontagem',
                        quantidade=quantidade_componente,
                        quantidade_anterior=estoque_ant_comp,
                        quantidade_nova=componente_produto.estoque_atual,
                        custo_unitario=componente_produto.preco_custo,
                        valor_total=quantidade_componente * (componente_produto.preco_custo or 0),
                        observacao=f"Desmontagem: componente retornado ao estoque após desmontar KIT FÍSICO '{produto.nome}' (desmontados {saida.quantidade} kit(s))",
                        user_id=current_user.id, tenant_id=tenant_id
                    )
                    db.add(mov_componente)
                    
                    componentes_sensibilizados.append({
                        "id": componente_produto.id,
                        "nome": componente_produto.nome,
                        "quantidade": quantidade_componente,
                        "estoque_anterior": estoque_ant_comp,
                        "estoque_novo": componente_produto.estoque_atual,
                        "acao": "retornado"
                    })
                    
                    logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (+{quantidade_componente}) [retornado ao estoque]")
            
            db.commit()
            logger.info(f"✅ KIT FÍSICO: {len(componentes_sensibilizados)} componentes retornados ao estoque")
        else:
            # CASO 2: NÃO desmontou - componentes NÃO mexem (perda, roubo, venda, etc)
            logger.info(f"🧩 KIT FÍSICO - SAÍDA SEM DESMONTAGEM: Componentes NÃO serão retornados ao estoque (perda/roubo/etc de {saida.quantidade} kits)")
            # Não faz nada com os componentes
    
    # Retornar dict
    response_data = {
        "id": movimentacao.id,
        "produto_id": movimentacao.produto_id,
        "produto_nome": produto.nome,
        "tipo": movimentacao.tipo,
        "motivo": movimentacao.motivo,
        "quantidade": movimentacao.quantidade,
        "quantidade_anterior": movimentacao.quantidade_anterior,
        "quantidade_nova": movimentacao.quantidade_nova,
        "custo_unitario": movimentacao.custo_unitario,
        "valor_total": movimentacao.valor_total,
        "documento": movimentacao.documento,
        "observacao": movimentacao.observacao,
        "user_id": movimentacao.user_id,
        "user_nome": current_user.nome,
        "created_at": movimentacao.created_at,
        "componentes_sensibilizados": componentes_sensibilizados if componentes_sensibilizados else None
    }
    
    # Sincronizar estoque com Bling automaticamente
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, "saida_estoque")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (saida): {e_sync}")
    
    return response_data


@router.post("/transferencia-parceiro", status_code=status.HTTP_201_CREATED)
@require_permission("produtos.editar")
def transferir_estoque_para_parceiro(
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Transfere estoque para um parceiro pelo custo.

    Regras:
    - baixa estoque via FIFO/lotes;
    - nao cria venda nem entra no faturamento do PDV;
    - gera um contas a receber separado para o ressarcimento do parceiro.
    """
    current_user, tenant_id = user_and_tenant

    parceiro = db.query(Cliente).filter(
        Cliente.id == payload.parceiro_id,
        Cliente.tenant_id == tenant_id,
        or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
    ).first()
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    quantidades_por_produto: dict[int, float] = defaultdict(float)
    for item in itens_validos:
        quantidades_por_produto[int(item.produto_id)] += float(item.quantidade or 0)

    codigo_transferencia = _texto_limpo(payload.documento) or _gerar_codigo_transferencia_parceiro()
    conta_existente = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento == codigo_transferencia,
    ).first()
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    itens_processados = []
    total_transferencia = Decimal("0")

    try:
        produtos_cache: dict[int, Produto] = {}

        for produto_id, quantidade in quantidades_por_produto.items():
            produto = db.query(Produto).filter(
                Produto.id == produto_id,
                Produto.tenant_id == tenant_id,
            ).first()
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto ID {produto_id} nao encontrado",
                )

            if produto.is_parent:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Produto '{produto.nome}' possui variacoes. "
                        "Selecione a variacao individual para transferir estoque."
                    ),
                )

            if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Produto '{produto.nome}' e um KIT VIRTUAL. "
                        "Use os componentes individuais na transferencia."
                    ),
                )

            estoque_atual = float(produto.estoque_atual or 0)
            if estoque_atual < quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Estoque insuficiente para '{produto.nome}'. "
                        f"Disponivel: {estoque_atual}, solicitado: {quantidade}"
                    ),
                )

            produtos_cache[produto.id] = produto

        for item in itens_validos:
            produto = produtos_cache.get(int(item.produto_id))
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto ID {item.produto_id} nao encontrado",
                )

            custo_unitario, total_item = _resolver_valores_item_transferencia(produto, item)
            total_transferencia += total_item

            itens_processados.append(
                {
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "codigo": getattr(produto, "codigo", None),
                    "codigo_barras": getattr(produto, "codigo_barras", None),
                    "quantidade": float(item.quantidade or 0),
                    "custo_unitario": float(custo_unitario),
                    "total_item": float(total_item),
                    "estoque_anterior": float(produto.estoque_atual or 0),
                }
            )

        if total_transferencia <= 0:
            raise HTTPException(
                status_code=400,
                detail="Informe ao menos um item com valor total maior que zero",
            )

        categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        dre_subcategoria_id = (
            categoria_financeira.dre_subcategoria_id
            or _obter_dre_subcategoria_receita_padrao(db, tenant_id)
        )

        observacoes_itens = "; ".join(
            f"{item['produto_nome']} x {item['quantidade']}"
            for item in itens_processados
        )
        observacoes_conta = observacoes_itens
        if payload.observacao:
            observacoes_conta = f"{payload.observacao}\n\nItens: {observacoes_itens}"

        conta_receber = ContaReceber(
            tenant_id=str(tenant_id),
            descricao=f"Transferencia para parceiro - {parceiro.nome}",
            cliente_id=parceiro.id,
            categoria_id=categoria_financeira.id,
            dre_subcategoria_id=dre_subcategoria_id,
            canal="transferencia_parceiro",
            valor_original=total_transferencia,
            valor_recebido=Decimal("0"),
            valor_final=total_transferencia,
            data_emissao=date.today(),
            data_vencimento=payload.data_vencimento or date.today(),
            status="pendente",
            documento=codigo_transferencia,
            observacoes=observacoes_conta,
            user_id=current_user.id,
        )
        db.add(conta_receber)
        db.flush()

        for item in itens_processados:
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta_receber.id}."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta_receber.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]

        db.commit()

        for item in itens_processados:
            try:
                sincronizar_bling_background(
                    item["produto_id"],
                    item["estoque_novo"],
                    "transferencia_parceiro",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta_receber.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta_receber.data_vencimento.isoformat() if conta_receber.data_vencimento else None,
            "total_ressarcimento": float(total_transferencia),
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao registrar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a transferencia para parceiro",
        )


@router.get(
    "/transferencia-parceiro/historico",
    response_model=TransferenciaParceiroHistoricoResponse,
)
@require_permission("produtos.visualizar")
def listar_transferencias_para_parceiro(
    page: int = 1,
    page_size: int = 20,
    parceiro_id: Optional[int] = None,
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Lista historico operacional e financeiro das transferencias para parceiro."""
    _current_user, tenant_id = user_and_tenant
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=parceiro_id,
        status_filtro=status_filtro,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    if not contas:
        return TransferenciaParceiroHistoricoResponse(
            items=[],
            totais=TransferenciaParceiroHistoricoTotais(),
            total=0,
            page=page,
            page_size=page_size,
            pages=0,
        )

    conta_ids = [conta.id for conta in contas]
    movimentacoes = db.query(EstoqueMovimentacao).options(
        joinedload(EstoqueMovimentacao.produto),
    ).filter(
        EstoqueMovimentacao.tenant_id == str(tenant_id),
        EstoqueMovimentacao.referencia_id.in_(conta_ids),
        EstoqueMovimentacao.motivo.in_(
            [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
        ),
    ).order_by(
        EstoqueMovimentacao.created_at.desc(),
        EstoqueMovimentacao.id.desc(),
    ).all()

    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]] = defaultdict(list)
    for mov in movimentacoes:
        if mov.referencia_id is None:
            continue
        itens_por_conta[int(mov.referencia_id)].append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome if mov.produto else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    registros_filtrados: list[TransferenciaParceiroHistoricoItem] = []
    totais = {
        "total_registros": 0,
        "valor_total": 0.0,
        "valor_recebido": 0.0,
        "saldo_aberto": 0.0,
        "pendentes": 0,
        "recebidas": 0,
        "vencidas": 0,
    }

    for conta in contas:
        status_resolvido, status_label = _status_transferencia_parceiro(conta)
        valor_original = float(conta.valor_original or 0)
        valor_recebido = float(conta.valor_recebido or 0)
        saldo_aberto = _saldo_conta_receber(conta)

        totais["total_registros"] += 1
        totais["valor_total"] += valor_original
        totais["valor_recebido"] += valor_recebido
        totais["saldo_aberto"] += saldo_aberto
        if status_resolvido == "recebido":
            totais["recebidas"] += 1
        elif status_resolvido == "vencido":
            totais["vencidas"] += 1
        elif status_resolvido != "cancelado":
            totais["pendentes"] += 1

        cliente = conta.cliente
        ultimo_recebimento = _obter_ultimo_recebimento_transferencia(conta)
        modo_baixa, modo_baixa_label = _detectar_modo_baixa_transferencia(ultimo_recebimento)
        forma_pagamento = getattr(ultimo_recebimento, "forma_pagamento", None) if ultimo_recebimento else None
        registros_filtrados.append(
            TransferenciaParceiroHistoricoItem(
                conta_receber_id=conta.id,
                documento=conta.documento,
                parceiro_id=cliente.id if cliente else None,
                parceiro_nome=cliente.nome if cliente else "Parceiro nao encontrado",
                parceiro_codigo=getattr(cliente, "codigo", None) if cliente else None,
                parceiro_email=getattr(cliente, "email", None) if cliente else None,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                data_recebimento=conta.data_recebimento,
                status=status_resolvido,
                status_label=status_label,
                valor_original=valor_original,
                valor_recebido=valor_recebido,
                saldo_aberto=saldo_aberto,
                modo_baixa=modo_baixa,
                modo_baixa_label=modo_baixa_label,
                forma_pagamento_id=getattr(ultimo_recebimento, "forma_pagamento_id", None),
                forma_pagamento_nome=_texto_limpo(getattr(forma_pagamento, "nome", None)),
                observacoes=conta.observacoes,
                itens=itens_por_conta.get(conta.id, []),
            )
        )

    total = len(registros_filtrados)
    pages = (total + page_size - 1) // page_size if total else 0
    offset = (page - 1) * page_size
    pagina_items = registros_filtrados[offset : offset + page_size]

    return TransferenciaParceiroHistoricoResponse(
        items=pagina_items,
        totais=TransferenciaParceiroHistoricoTotais(
            total_registros=int(totais["total_registros"]),
            valor_total=float(totais["valor_total"]),
            valor_recebido=float(totais["valor_recebido"]),
            saldo_aberto=float(totais["saldo_aberto"]),
            pendentes=int(totais["pendentes"]),
            recebidas=int(totais["recebidas"]),
            vencidas=int(totais["vencidas"]),
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/transferencia-parceiro/{conta_receber_id}/pdf")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencia_parceiro(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Gera PDF operacional da transferencia com ressarcimento."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(conta, parceiro, itens)
    nome_documento = (conta.documento or f"TRP-{conta.id:06d}").replace("/", "-")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencia_{nome_documento}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/pdf-consolidado")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencias_parceiro_consolidado(
    payload: TransferenciaParceiroPdfConsolidadoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Gera um PDF unico com varias transferencias selecionadas ou filtradas."""
    _current_user, tenant_id = user_and_tenant
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=payload.parceiro_id,
        status_filtro=payload.status_filtro,
        busca=payload.busca,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        conta_receber_ids=payload.conta_receber_ids or None,
    )

    if not contas:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma transferencia encontrada para gerar o PDF consolidado",
        )

    conta_ids = [conta.id for conta in contas]
    movimentacoes = db.query(EstoqueMovimentacao).options(
        joinedload(EstoqueMovimentacao.produto),
    ).filter(
        EstoqueMovimentacao.tenant_id == str(tenant_id),
        EstoqueMovimentacao.referencia_id.in_(conta_ids),
        EstoqueMovimentacao.motivo.in_(
            [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
        ),
    ).order_by(
        EstoqueMovimentacao.created_at.asc(),
        EstoqueMovimentacao.id.asc(),
    ).all()

    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]] = defaultdict(list)
    for mov in movimentacoes:
        if mov.referencia_id is None:
            continue
        itens_por_conta[int(mov.referencia_id)].append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome if mov.produto else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    pdf_bytes = _gerar_pdf_transferencias_parceiro_consolidado_bytes(contas, itens_por_conta)
    data_ref = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencias_consolidadas_{data_ref}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/enviar-email")
@require_permission("produtos.visualizar")
def enviar_email_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroEnviarEmailRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Envia por e-mail o PDF da transferencia usando o cadastro da pessoa."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    email_destino = _texto_limpo(payload.email) or _texto_limpo(getattr(parceiro, "email", None))

    if not email_destino:
        raise HTTPException(
            status_code=400,
            detail="A pessoa selecionada nao possui e-mail cadastrado",
        )

    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail nao esta configurado no servidor",
        )

    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(conta, parceiro, itens)
    assunto_padrao, html_body, text_body = _montar_email_transferencia_parceiro(
        conta,
        parceiro,
        itens,
        mensagem_extra=payload.mensagem,
    )

    enviado = send_email(
        to=email_destino,
        subject=_texto_limpo(payload.assunto) or assunto_padrao,
        html_body=html_body,
        text_body=text_body,
        attachments=[
            {
                "filename": f"transferencia_{(conta.documento or f'TRP-{conta.id:06d}').replace('/', '-')}.pdf",
                "content": pdf_bytes,
                "mime_subtype": "pdf",
            }
        ],
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail. Revise a configuracao SMTP.",
        )

    return {
        "sucesso": True,
        "email": email_destino,
        "documento": conta.documento or f"TRP-{conta.id:06d}",
    }


@router.get(
    "/transferencia-parceiro/{conta_receber_id}/contas-pagar-compensacao",
    response_model=TransferenciaParceiroContaPagarCompensacaoResponse,
)
@require_permission("produtos.visualizar")
def listar_contas_pagar_compensacao_transferencia(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Lista contas a pagar em aberto da mesma pessoa para realizar compensacao."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    contas = _buscar_contas_pagar_compensacao_transferencia(
        db,
        tenant_id=tenant_id,
        cliente_id=getattr(conta, "cliente_id", None),
    )

    items = []
    total_disponivel = 0.0
    for conta_pagar in contas:
        saldo_aberto = _saldo_conta_pagar(conta_pagar)
        status_conta, status_label = _status_conta_pagar_compensacao(conta_pagar)
        total_disponivel += saldo_aberto
        items.append(
            TransferenciaParceiroContaPagarCompensacaoItem(
                conta_pagar_id=conta_pagar.id,
                descricao=conta_pagar.descricao,
                documento=conta_pagar.documento,
                data_emissao=conta_pagar.data_emissao,
                data_vencimento=conta_pagar.data_vencimento,
                status=status_conta,
                status_label=status_label,
                valor_original=float(conta_pagar.valor_original or 0),
                valor_pago=float(conta_pagar.valor_pago or 0),
                saldo_aberto=saldo_aberto,
                observacoes=conta_pagar.observacoes,
            )
        )

    return TransferenciaParceiroContaPagarCompensacaoResponse(
        items=items,
        total=len(items),
        total_disponivel=round(total_disponivel, 2),
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/receber")
@require_permission("produtos.editar")
def registrar_recebimento_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRecebimentoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Registra baixa financeira de uma transferencia com ressarcimento."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    modo_baixa = _normalizar_modo_baixa_transferencia(payload.modo_baixa)
    compensacoes_payload = [
        item
        for item in (payload.compensacoes or [])
        if round(float(item.valor_compensado or 0), 2) > 0
    ]

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode receber baixa",
        )

    saldo_aberto = _saldo_conta_receber(conta)
    valor_recebido = round(float(payload.valor_recebido or 0), 2)

    if valor_recebido <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe um valor recebido maior que zero",
        )

    if valor_recebido - saldo_aberto > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"O valor recebido ultrapassa o saldo da transferencia. "
                f"Saldo atual: R$ {saldo_aberto:.2f}"
            ),
        )

    total_compensado = round(
        sum(float(item.valor_compensado or 0) for item in compensacoes_payload),
        2,
    )
    if compensacoes_payload and abs(total_compensado - valor_recebido) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                "O total compensado nas contas a pagar deve ser igual ao valor da baixa "
                "quando houver titulos selecionados para compensacao."
            ),
        )

    valor_recebido_total = round(float(conta.valor_recebido or 0) + valor_recebido, 2)
    conta.valor_recebido = Decimal(str(valor_recebido_total))
    conta.data_recebimento = payload.data_recebimento or date.today()
    conta.status = (
        "recebido"
        if abs(float(conta.valor_final or 0) - valor_recebido_total) < 0.01
        else "parcial"
    )

    forma_pagamento = None
    if modo_baixa == "acerto":
        forma_pagamento = _obter_ou_criar_forma_pagamento_acerto(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
    elif payload.forma_pagamento_id:
        forma_pagamento = _buscar_forma_pagamento_transferencia(
            db,
            tenant_id=tenant_id,
            forma_pagamento_id=payload.forma_pagamento_id,
        )

    if forma_pagamento:
        conta.forma_pagamento_id = forma_pagamento.id

    observacao_recebimento = _texto_limpo(payload.observacao)
    modo_label = _label_modo_baixa_transferencia(modo_baixa) or "Recebimento"
    compensacoes_processadas: list[dict] = []
    if modo_baixa == "acerto" and compensacoes_payload:
        compensacoes_processadas = _aplicar_compensacoes_contas_pagar_transferencia(
            db,
            conta_receber=conta,
            tenant_id=tenant_id,
            user_id=current_user.id,
            data_pagamento=conta.data_recebimento,
            forma_pagamento=forma_pagamento,
            compensacoes_payload=compensacoes_payload,
        )

    detalhe_forma = (
        f" | Forma: {forma_pagamento.nome}"
        if forma_pagamento and _texto_limpo(forma_pagamento.nome)
        else ""
    )
    detalhe_compensacao = ""
    resumo_compensacao = _formatar_resumo_compensacoes_transferencia(compensacoes_processadas)
    if resumo_compensacao:
        detalhe_compensacao = f" | {resumo_compensacao}"
    detalhe_observacao = f" - {observacao_recebimento}" if observacao_recebimento else ""
    historico = (
        f"{modo_label} {conta.data_recebimento.strftime('%d/%m/%Y')}: "
        f"R$ {valor_recebido:.2f}{detalhe_forma}{detalhe_compensacao}{detalhe_observacao}"
    )
    conta.observacoes = (
        f"{conta.observacoes}\n\n{historico}".strip()
        if conta.observacoes
        else historico
    )

    recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=forma_pagamento.id if forma_pagamento else None,
        valor_recebido=Decimal(str(valor_recebido)),
        data_recebimento=conta.data_recebimento,
        observacoes=historico,
        user_id=current_user.id,
        tenant_id=str(tenant_id),
    )
    db.add(recebimento)
    db.commit()
    db.refresh(conta)

    status_resolvido, status_label = _status_transferencia_parceiro(conta)

    return {
        "sucesso": True,
        "conta_receber_id": conta.id,
        "status": status_resolvido,
        "status_label": status_label,
        "valor_recebido": float(conta.valor_recebido or 0),
        "saldo_aberto": _saldo_conta_receber(conta),
        "data_recebimento": conta.data_recebimento.isoformat() if conta.data_recebimento else None,
        "modo_baixa": modo_baixa,
        "modo_baixa_label": modo_label,
        "forma_pagamento_id": forma_pagamento.id if forma_pagamento else None,
        "forma_pagamento_nome": _texto_limpo(getattr(forma_pagamento, "nome", None)),
        "compensacoes": compensacoes_processadas,
    }


@router.delete("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def excluir_transferencia_parceiro(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Exclui uma transferencia ainda sem baixa, estornando o estoque."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de excluir o lancamento."
            ),
        )

    movimentacoes = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.tenant_id == str(tenant_id),
        EstoqueMovimentacao.referencia_id == conta.id,
        EstoqueMovimentacao.tipo == "saida",
        EstoqueMovimentacao.motivo.in_(
            [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
        ),
    ).order_by(EstoqueMovimentacao.id.asc()).all()

    try:
        estoques_finais: dict[int, float] = {}
        lotes_restaurados = 0

        for movimentacao in movimentacoes:
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(db, movimentacao)
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno por exclusao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[movimentacao.produto_id] = resultado_estorno["estoque_novo"]
            db.delete(movimentacao)

        recebimentos = db.query(Recebimento).filter(
            Recebimento.conta_receber_id == conta.id,
            Recebimento.tenant_id == str(tenant_id),
        ).all()
        for recebimento in recebimentos:
            db.delete(recebimento)

        db.delete(conta)
        db.commit()

        for produto_id, estoque_novo in estoques_finais.items():
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_exclusao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (exclusao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "conta_receber_id": conta_receber_id,
            "documento": conta.documento,
            "lotes_restaurados": lotes_restaurados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao excluir transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel excluir a transferencia para parceiro",
        )


@router.post("/saida-full-nf", status_code=status.HTTP_201_CREATED)
def saida_full_por_nf(
    payload: SaidaFullNFRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Baixa estoque em lote por NF de saida (operacao FULL).

    Regras:
    - Cada item baixa apenas estoque (sem gerar financeiro).
    - Se qualquer item falhar, toda a transacao e cancelada.
    """
    current_user, tenant_id = user_and_tenant

    itens_validos = [item for item in payload.itens if item.quantidade and item.quantidade > 0]
    if not itens_validos:
        raise HTTPException(status_code=400, detail="Informe ao menos um item com quantidade maior que zero")

    processados = []
    observacao_movimentacao = _observacao_full_nf(payload.numero_nf, payload.plataforma, payload.observacao)

    try:
        for item in itens_validos:
            processados.append(
                _processar_item_saida_full_nf(
                    db=db,
                    tenant_id=tenant_id,
                    item=item,
                    numero_nf=payload.numero_nf,
                    observacao_movimentacao=observacao_movimentacao,
                    current_user=current_user,
                )
            )

        db.commit()

        for item in processados:
            try:
                sincronizar_bling_background(item["produto_id"], item["estoque_novo"], "saida_full_nfe")
            except Exception as e_sync:
                logger.warning(f"[BLING-SYNC] Erro ao agendar sync (saida-full-nf): {e_sync}")

        return {
            "success": True,
            "message": "Baixa de estoque por NF concluida",
            "numero_nf": payload.numero_nf,
            "plataforma": payload.plataforma,
            "total_itens": len(processados),
            "itens": processados,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro na baixa FULL por NF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar baixa por NF: {str(e)}")


@router.post("/saida-full-pdf/parse")
async def parse_saida_full_pdf(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai SKU + quantidade de um PDF para preencher a baixa FULL por NF.
    Nao baixa estoque automaticamente; apenas retorna os itens interpretados.
    """
    if pdfplumber is None:
        raise HTTPException(
            status_code=500,
            detail="Leitura de PDF indisponivel no backend (pdfplumber nao instalado)",
        )

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo PDF nao informado")

    nome = file.filename.lower()
    if not nome.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF valido")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo PDF vazio")

    try:
        texto_paginas = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                texto_paginas.append(page.extract_text() or "")

        texto = "\n".join(texto_paginas).strip()
        if not texto:
            raise HTTPException(status_code=400, detail="Nao foi possivel ler texto do PDF")

        itens = _extrair_itens_full_pdf(texto)
        if not itens:
            raise HTTPException(
                status_code=400,
                detail="Nenhum item SKU+quantidade foi identificado no PDF",
            )

        return {
            "success": True,
            "message": "Itens extraidos do PDF com sucesso",
            "total_itens": len(itens),
            "itens": itens,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao interpretar PDF FULL NF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao interpretar PDF: {str(e)}")


@router.post("/saida-full-xml/parse")
async def parse_saida_full_xml(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai numero da NF e itens (SKU + quantidade) de XML da NF-e.
    Nao baixa estoque automaticamente; apenas preenche o formulario.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo XML nao informado")

    nome = file.filename.lower()
    if not nome.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Envie um arquivo XML valido")

    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Arquivo XML vazio")

    try:
        dados = _parse_saida_full_xml(xml_bytes)
        return {
            "success": True,
            "message": "XML lido com sucesso",
            **dados,
        }
    except HTTPException:
        raise
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="XML invalido: erro de estrutura")
    except Exception as e:
        logger.error(f"Erro ao interpretar XML FULL NF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao interpretar XML: {str(e)}")

# ============================================================================
# TRANSFERÊNCIA ENTRE ESTOQUES
# ============================================================================

@router.post("/transferencia", status_code=status.HTTP_201_CREATED)
def transferencia_estoque(
    transf: TransferenciaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Transferência entre estoques
    
    Tipos de estoque:
    - fisico: Estoque físico da loja
    - ecommerce: Estoque online (marketplace)
    - consignado: Produtos em consignação
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"🔄 Transferência - Produto {transf.produto_id}: {transf.estoque_origem} → {transf.estoque_destino}")
    
    if transf.estoque_origem == transf.estoque_destino:
        raise HTTPException(status_code=400, detail="Origem e destino não podem ser iguais")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == transf.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    estoque_anterior = produto.estoque_atual or 0
    
    # Validar estoque origem
    # TODO: Implementar controle de estoques separados por tipo
    # Por enquanto, valida apenas o estoque_atual total
    if estoque_anterior < transf.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente em '{transf.estoque_origem}'"
        )
    
    # Gerar código de transferência
    codigo_transf = f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Movimentação de SAÍDA (origem)
    mov_saida = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='transferencia',
        motivo='transferencia_enviada',
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,  # Não altera total ainda
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(mov_saida)
    
    # Movimentação de ENTRADA (destino)
    mov_entrada = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='transferencia',
        motivo='transferencia_recebida',
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,  # Não altera total
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(mov_entrada)
    
    db.commit()
    
    logger.info(f"✅ Transferência registrada: {codigo_transf}")
    
    return {
        "message": "Transferência registrada com sucesso",
        "codigo": codigo_transf,
        "movimentacoes": [mov_saida.id, mov_entrada.id]
    }

# ============================================================================
# ALERTAS DE ESTOQUE
# ============================================================================

@router.get("/alertas")
def alertas_estoque(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Alertas de estoque
    
    Retorna:
    - Produtos zerados
    - Produtos abaixo do mínimo
    - Lotes vencendo em 30 dias
    - Lotes vencidos
    """
    current_user, tenant_id = user_and_tenant
    logger.info("⚠️ Consultando alertas de estoque")
    
    hoje = datetime.now().date()
    daqui_30_dias = hoje + timedelta(days=30)
    
    # Produtos zerados
    zerados = db.query(Produto).filter(
        or_(
            Produto.estoque_atual == 0,
            Produto.estoque_atual == None
        ),
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).all()
    
    # Produtos abaixo do mínimo
    abaixo_minimo = db.query(Produto).filter(
        Produto.estoque_atual <= Produto.estoque_minimo,
        Produto.estoque_atual > 0,
        Produto.estoque_minimo > 0,
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).all()
    
    # Lotes vencendo
    lotes_vencendo = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade.between(hoje, daqui_30_dias),
        ProdutoLote.quantidade > 0,
        ProdutoLote.status == 'disponivel',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).options(joinedload(ProdutoLote.produto)).all()
    
    # Lotes vencidos
    lotes_vencidos = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade < hoje,
        ProdutoLote.quantidade > 0,
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).options(joinedload(ProdutoLote.produto)).all()
    
    return {
        "zerados": {
            "total": len(zerados),
            "produtos": [{
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "categoria": p.categoria.nome if p.categoria else None
            } for p in zerados[:20]]  # Limitar a 20
        },
        "abaixo_minimo": {
            "total": len(abaixo_minimo),
            "produtos": [{
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "estoque_atual": p.estoque_atual,
                "estoque_minimo": p.estoque_minimo,
                "diferenca": p.estoque_minimo - p.estoque_atual
            } for p in abaixo_minimo[:20]]
        },
        "lotes_vencendo": {
            "total": len(lotes_vencendo),
            "lotes": [{
                "id": l.id,
                "produto_id": l.produto_id,
                "produto_nome": l.produto.nome,
                "numero_lote": l.numero_lote,
                "quantidade": l.quantidade,
                "data_validade": l.data_validade.isoformat(),
                "dias_restantes": (l.data_validade - hoje).days
            } for l in lotes_vencendo[:20]]
        },
        "lotes_vencidos": {
            "total": len(lotes_vencidos),
            "lotes": [{
                "id": l.id,
                "produto_id": l.produto_id,
                "produto_nome": l.produto.nome,
                "numero_lote": l.numero_lote,
                "quantidade": l.quantidade,
                "data_validade": l.data_validade.isoformat(),
                "dias_vencido": (hoje - l.data_validade).days
            } for l in lotes_vencidos[:20]]
        }
    }

# ============================================================================
# EXCLUSÃO E EDIÇÃO DE MOVIMENTAÇÕES
# ============================================================================

@router.delete("/movimentacoes/{movimentacao_id}")
def excluir_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Exclui uma movimentação de estoque e reverte o efeito no produto
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar movimentação
        movimentacao = db.query(EstoqueMovimentacao).filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id
        ).first()
        
        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")
        
        # Buscar produto
        produto = db.query(Produto).filter(Produto.id == movimentacao.produto_id, Produto.tenant_id == tenant_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        logger.info(f"🗑️ Excluindo movimentação {movimentacao_id} - Tipo: {movimentacao.tipo}, Qtd: {movimentacao.quantidade}")
        
        # ========== ESTORNO DE COMPONENTES PARA KIT FÍSICO ==========
        componentes_estornados = []
        if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
            componentes_kit = db.query(ProdutoKitComponente).filter(
                ProdutoKitComponente.kit_id == produto.id
            ).all()
            
            if componentes_kit:
                logger.info(f"📦 KIT FÍSICO detectado - Estornando componentes...")
                
                for comp in componentes_kit:
                    componente_produto = db.query(Produto).filter(Produto.id == comp.produto_componente_id, Produto.tenant_id == tenant_id).first()
                    if componente_produto:
                        quantidade_componente = comp.quantidade * movimentacao.quantidade
                        estoque_ant_comp = componente_produto.estoque_atual
                        
                        # LÓGICA DE ESTORNO:
                        # - Se foi ENTRADA de kit: os componentes foram CONSUMIDOS (-) 
                        #   → Ao excluir, devemos DEVOLVER (+) os componentes
                        # - Se foi SAÍDA de kit com retorno: os componentes foram DEVOLVIDOS (+)
                        #   → Ao excluir, devemos REMOVER (-) os componentes novamente
                        
                        if movimentacao.tipo == 'entrada':
                            # Estornando entrada de kit: devolver componentes consumidos
                            componente_produto.estoque_atual += quantidade_componente
                            logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (+{quantidade_componente}) [devolvido]")
                            componentes_estornados.append({
                                "nome": componente_produto.nome,
                                "quantidade": quantidade_componente,
                                "estoque_anterior": estoque_ant_comp,
                                "estoque_novo": componente_produto.estoque_atual,
                                "acao": "devolvido"
                            })
                        elif movimentacao.tipo == 'saida' and movimentacao.observacao and 'componentes retornados' in movimentacao.observacao.lower():
                            # Estornando saída com retorno: remover componentes que foram devolvidos
                            componente_produto.estoque_atual -= quantidade_componente
                            logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (-{quantidade_componente}) [estornando retorno]")
                            componentes_estornados.append({
                                "nome": componente_produto.nome,
                                "quantidade": quantidade_componente,
                                "estoque_anterior": estoque_ant_comp,
                                "estoque_novo": componente_produto.estoque_atual,
                                "acao": "estornado"
                            })
                
                logger.info(f"✅ KIT FÍSICO: {len(componentes_estornados)} componentes estornados")
        
        # Reverter estoque do kit/produto principal
        estoque_anterior = produto.estoque_atual
        if movimentacao.tipo == 'entrada':
            produto.estoque_atual -= movimentacao.quantidade
            logger.info(f"📉 Estoque {produto.nome}: {estoque_anterior} → {produto.estoque_atual} (-{movimentacao.quantidade})")
        elif movimentacao.tipo == 'saida':
            produto.estoque_atual += movimentacao.quantidade
            logger.info(f"📈 Estoque {produto.nome}: {estoque_anterior} → {produto.estoque_atual} (+{movimentacao.quantidade})")
        
        # Se tinha lote, reverter também
        if movimentacao.lote_id:
            lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
            if lote:
                if movimentacao.tipo == 'entrada':
                    lote.quantidade_disponivel -= movimentacao.quantidade
                    if lote.quantidade_disponivel <= 0:
                        lote.status = 'esgotado'
                elif movimentacao.tipo == 'saida':
                    lote.quantidade_disponivel += movimentacao.quantidade
                    lote.status = 'ativo'
        
        # Excluir movimentação
        db.delete(movimentacao)
        db.commit()
        
        logger.info(f"✅ Movimentação {movimentacao_id} excluída por {current_user.nome}")
        
        # Sincronizar estoque com Bling automaticamente
        try:
            sincronizar_bling_background(produto.id, produto.estoque_atual, "exclusao_movimentacao")
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (exclusao_mov): {e_sync}")
        
        return {
            "message": "Movimentação excluída com sucesso",
            "componentes_estornados": componentes_estornados
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir movimentação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMovimentacaoRequest(BaseModel):
    quantidade: Optional[float] = None
    custo_unitario: Optional[float] = None
    observacao: Optional[str] = None


@router.patch("/movimentacoes/{movimentacao_id}")
def editar_movimentacao(
    movimentacao_id: int,
    dados: UpdateMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Edita uma movimentação existente
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar movimentação
        movimentacao = db.query(EstoqueMovimentacao).filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id
        ).first()
        
        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")
        
        # Buscar produto
        produto = db.query(Produto).filter(Produto.id == movimentacao.produto_id, Produto.tenant_id == tenant_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Se mudou a quantidade, ajustar estoque
        if dados.quantidade is not None and dados.quantidade != movimentacao.quantidade:
            diferenca = dados.quantidade - movimentacao.quantidade
            
            if movimentacao.tipo == 'entrada':
                produto.estoque_atual += diferenca
                if movimentacao.lote_id:
                    lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
                    if lote:
                        lote.quantidade_disponivel += diferenca
            elif movimentacao.tipo == 'saida':
                produto.estoque_atual -= diferenca
                if movimentacao.lote_id:
                    lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
                    if lote:
                        lote.quantidade_disponivel -= diferenca
            
            movimentacao.quantidade = dados.quantidade
            movimentacao.quantidade_nova = produto.estoque_atual
        
        # Atualizar outros campos
        if dados.custo_unitario is not None:
            movimentacao.custo_unitario = dados.custo_unitario
            movimentacao.valor_total = movimentacao.quantidade * dados.custo_unitario
        
        if dados.observacao is not None:
            movimentacao.observacao = dados.observacao
        
        db.commit()
        db.refresh(movimentacao)
        
        logger.info(f"✅ Movimentação {movimentacao_id} editada por {current_user.nome}")
        
        # Sincronizar estoque com Bling se quantidade foi alterada
        if dados.quantidade is not None:
            try:
                sincronizar_bling_background(produto.id, produto.estoque_atual, "edicao_movimentacao")
            except Exception as e_sync:
                logger.warning(f"[BLING-SYNC] Erro ao agendar sync (edicao_mov): {e_sync}")
        
        return {
            "id": movimentacao.id,
            "quantidade": movimentacao.quantidade,
            "custo_unitario": movimentacao.custo_unitario,
            "observacao": movimentacao.observacao,
            "estoque_atual_produto": produto.estoque_atual
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao editar movimentação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RELATÓRIOS
# ============================================================================

@router.get("/relatorio/valorizado")
def relatorio_estoque_valorizado(
    data_referencia: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Relatório de estoque valorizado
    
    Calcula valor total do estoque baseado no preço de custo
    """
    current_user, tenant_id = user_and_tenant
    logger.info("📊 Gerando relatório de estoque valorizado")
    
    # Query base
    query = db.query(
        Produto.id,
        Produto.sku,
        Produto.nome,
        Produto.estoque_atual,
        Produto.preco_custo,
        (Produto.estoque_atual * Produto.preco_custo).label('valor_total')
    ).filter(
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.estoque_atual > 0,
        Produto.tenant_id == tenant_id
    )
    
    # Filtros
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    
    produtos = query.all()
    
    # Calcular totais
    valor_total = sum(p.valor_total for p in produtos if p.valor_total)
    total_itens = sum(p.estoque_atual for p in produtos if p.estoque_atual)
    
    return {
        "resumo": {
            "valor_total": valor_total,
            "total_produtos": len(produtos),
            "total_itens": total_itens,
            "custo_medio_unitario": valor_total / total_itens if total_itens > 0 else 0
        },
        "produtos": [{
            "id": p.id,
            "sku": p.sku,
            "nome": p.nome,
            "quantidade": p.estoque_atual,
            "custo_unitario": p.preco_custo,
            "valor_total": p.valor_total
        } for p in produtos]
    }

@router.get("/movimentacoes/produto/{produto_id}")
def listar_movimentacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as movimentações de um produto específico
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📋 Listando movimentações do produto {produto_id}")
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Buscar movimentações ordenadas por data (mais antigas primeiro para calcular variações)
    movimentacoes = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto_id,
        EstoqueMovimentacao.tenant_id == tenant_id
    ).order_by(EstoqueMovimentacao.created_at).all()

    pedido_integrado_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == 'pedido_integrado' and mov.referencia_id
        }
    )
    pedidos_integrados = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.id.in_(pedido_integrado_ids),
        )
        .all()
        if pedido_integrado_ids
        else []
    )
    pedidos_integrados_por_id = {pedido.id: pedido for pedido in pedidos_integrados}
    
    resultado = []
    custo_anterior_entrada = None
    
    # Dicionário para rastrear consumo acumulado por lote
    consumo_por_lote = {}
    
    for mov in movimentacoes:
        # Buscar informações do lote
        lote_nome = None
        lote_info = None
        
        # Para ENTRADAS: verificar se tem lote_id
        if mov.tipo == 'entrada' and mov.lote_id:
            lote = db.query(ProdutoLote).filter(ProdutoLote.id == mov.lote_id).first()
            if lote:
                lote_nome = lote.nome_lote
                lote_info = {
                    "nome": lote_nome,
                    "total_lote": lote.quantidade_inicial,
                    "tipo": "entrada"
                }
        
        # Para SAÍDAS: verificar lotes_consumidos
        elif mov.tipo == 'saida' and mov.lotes_consumidos:
            try:
                lotes = json.loads(mov.lotes_consumidos)
                if lotes and len(lotes) > 0:
                    # Pegar o primeiro lote consumido
                    primeiro_lote = lotes[0]
                    lote_id = primeiro_lote.get('lote_id')
                    
                    if lote_id:
                        # Rastrear consumo acumulado
                        if lote_id not in consumo_por_lote:
                            consumo_por_lote[lote_id] = 0
                        consumo_por_lote[lote_id] += primeiro_lote.get('quantidade', 0)
                        
                        # Buscar dados do lote
                        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
                        if lote:
                            lote_info = {
                                "nome": lote.nome_lote,
                                "consumido_acumulado": consumo_por_lote[lote_id],
                                "total_lote": lote.quantidade_inicial,
                                "quantidade_movimento": primeiro_lote.get('quantidade', 0),
                                "tipo": "saida"
                            }
            except:
                pass
        
        # Calcular variação de custo para entradas
        variacao_custo = None
        if mov.tipo == 'entrada' and mov.custo_unitario:
            if custo_anterior_entrada and custo_anterior_entrada > 0:
                diferenca_valor = mov.custo_unitario - custo_anterior_entrada
                diferenca_percentual = (diferenca_valor / custo_anterior_entrada) * 100
                
                variacao_custo = {
                    "custo_anterior": custo_anterior_entrada,
                    "custo_atual": mov.custo_unitario,
                    "diferenca_valor": diferenca_valor,
                    "diferenca_percentual": diferenca_percentual,
                    "tipo": "aumento" if diferenca_valor > 0 else "reducao" if diferenca_valor < 0 else "estavel"
                }
            
            # Atualizar custo anterior apenas se for entrada com custo
            custo_anterior_entrada = mov.custo_unitario
        
        # Buscar canal da venda quando for movimentação de venda
        canal_venda = None
        preco_venda_unitario = None
        nf_numero = None
        documento_exibicao = mov.documento
        observacao_exibicao = mov.observacao
        if mov.referencia_tipo == 'venda' and mov.referencia_id:
            venda = db.query(Venda.canal, Venda.total).filter(Venda.id == mov.referencia_id).first()
            if venda:
                canal_venda = venda.canal
                if mov.quantidade and mov.quantidade > 0:
                    preco_venda_unitario = float(venda.total) / float(mov.quantidade) if venda.total else None
        elif mov.referencia_tipo == 'pedido_integrado' and mov.referencia_id:
            pedido_integrado = pedidos_integrados_por_id.get(int(mov.referencia_id))
            if pedido_integrado:
                contexto_venda = _contexto_venda_pedido_integrado(db, pedido_integrado, produto_id)
                canal_venda = contexto_venda.get("canal")
                nf_numero = contexto_venda.get("nf_numero")
                nf_id = contexto_venda.get("nf_id")
                try:
                    from .services.bling_nf_service import movimento_documentado_por_nf
                except Exception:
                    movimento_documentado_por_nf = None

                movimento_usa_nf = bool(
                    movimento_documentado_por_nf
                    and movimento_documentado_por_nf(
                        mov,
                        nf_numero=nf_numero,
                        nf_bling_id=nf_id,
                    )
                )

                if movimento_usa_nf:
                    preco_venda_unitario = contexto_venda.get("preco_venda_unitario")
                    documento_exibicao = nf_numero or mov.documento
                    observacao_exibicao = _observacao_exibicao_movimentacao_bling(
                        canal=canal_venda,
                        nf_numero=nf_numero,
                        observacao_original=mov.observacao,
                    )
                else:
                    nf_numero = None

        resultado.append({
            "id": mov.id,
            "tipo": mov.tipo,
            "status": mov.status,
            "motivo": mov.motivo,
            "quantidade": mov.quantidade,
            "quantidade_anterior": mov.quantidade_anterior,
            "quantidade_nova": mov.quantidade_nova,
            "custo_unitario": mov.custo_unitario,
            "valor_total": mov.valor_total,
            "documento": documento_exibicao,
            "documento_original": mov.documento,
            "referencia_id": mov.referencia_id,
            "referencia_tipo": mov.referencia_tipo,
            "observacao": mov.observacao,
            "observacao_exibicao": observacao_exibicao,
            "lote_id": mov.lote_id,
            "lote_nome": lote_nome,
            "lote_info": lote_info,
            "variacao_custo": variacao_custo,
            "canal": canal_venda,
            "canal_label": _label_canal_movimentacao(canal_venda),
            "nf_numero": nf_numero,
            "preco_venda_unitario": preco_venda_unitario,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
            "user_id": mov.user_id
        })
    
    # Inverter para mostrar mais recentes primeiro
    resultado.reverse()
    
    return resultado


@router.get("/produto/{produto_id}/reservas-ativas")
def listar_reservas_ativas_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    logger.info(f"🔎 Listando reservas ativas do produto {produto_id}")

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    reservas = _detalhar_reservas_ativas_produto(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
    )

    return {
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "total_pedidos": len(reservas),
        "quantidade_reservada": round(
            sum(float(item.get("quantidade_reservada") or 0) for item in reservas),
            4,
        ),
        "pedidos": reservas,
    }

