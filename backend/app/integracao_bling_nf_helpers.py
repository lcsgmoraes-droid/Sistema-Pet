"""Helpers do webhook de notas fiscais do Bling."""

from datetime import datetime, timezone

from sqlalchemy import exists, not_, or_
from sqlalchemy.orm import Session

from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.services.bling_nf_service import (
    criar_produto_automatico_do_bling,
)
from app.services.nfe_cache_service import upsert_nota_cache
from app.utils.logger import logger


_NF_SITUACAO_AUTORIZADA = {2, 5, 9}
_NF_SITUACAO_CANCELADA = {4}


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _texto(value) -> str | None:
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _primeiro_preenchido(*valores):
    for valor in valores:
        if valor is None:
            continue
        if isinstance(valor, str) and not valor.strip():
            continue
        return valor
    return None


def _nf_id_valido(value) -> str | None:
    texto = _texto(value)
    if not texto or texto in {"0", "-1"}:
        return None
    return texto


def _normalizar_resumo_nf(resumo_nf: dict | None) -> dict | None:
    resumo_nf = dict(_dict(resumo_nf))
    if not resumo_nf:
        return None

    nf_id = _nf_id_valido(
        _primeiro_preenchido(resumo_nf.get("id"), resumo_nf.get("nfe_id"))
    )
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
        or _texto(
            _primeiro_preenchido(resumo_nf.get("chaveAcesso"), resumo_nf.get("chave"))
        )
        or _texto(
            _primeiro_preenchido(resumo_nf.get("situacao"), resumo_nf.get("status"))
        )
        or _texto(
            _primeiro_preenchido(
                resumo_nf.get("data_emissao"), resumo_nf.get("dataEmissao")
            )
        )
        or resumo_nf.get("valor_total") not in (None, "")
    )

    return resumo_nf if possui_referencia_util else None


def _mesclar_ultima_nf(atual: dict | None, nova: dict | None) -> dict:
    atual = _normalizar_resumo_nf(atual) or {}
    nova = _normalizar_resumo_nf(nova) or {}
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
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
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

    if (atual_id and nova_id and atual_id == nova_id) or (
        atual_numero and nova_numero and atual_numero == nova_numero
    ):
        return True

    atual_data = _coerce_data_nf(
        _primeiro_preenchido(atual.get("data_emissao"), atual.get("dataEmissao"))
    )
    nova_data = _coerce_data_nf(
        _primeiro_preenchido(nova.get("data_emissao"), nova.get("dataEmissao"))
    )
    if atual_data and nova_data and atual_data != nova_data:
        return nova_data > atual_data
    if nova_data and not atual_data:
        return True
    if atual_data and not nova_data:
        return False

    atual_numero_int = _numero_nf_int(atual)
    nova_numero_int = _numero_nf_int(nova)
    if (
        atual_numero_int is not None
        and nova_numero_int is not None
        and atual_numero_int != nova_numero_int
    ):
        return nova_numero_int > atual_numero_int

    return False


def _consolidar_ultima_nf(atual: dict | None, nova: dict | None) -> dict:
    atual = _normalizar_resumo_nf(atual)
    nova = _normalizar_resumo_nf(nova)
    if not atual and not nova:
        return {}
    if _nova_nf_deve_substituir(atual, nova):
        return _mesclar_ultima_nf(atual, nova)
    return _mesclar_ultima_nf(nova, atual)


def _modelo_nota_bling(nf_data: dict | None) -> int:
    nf_data = _dict(nf_data)
    for candidato in (
        nf_data.get("modelo"),
        nf_data.get("modeloDocumento"),
        nf_data.get("modelo_nf"),
    ):
        texto = _texto(candidato)
        if texto in {"55", "65"}:
            return int(texto)

    tipo = (_texto(nf_data.get("tipo")) or "").lower()
    if "nfce" in tipo:
        return 65
    return 55


def _status_nota_webhook(
    nf_data: dict | None, situacao_num: int | None = None
) -> str | None:
    nf_data = _dict(nf_data)
    try:
        from app.nfe_routes import _status_nota_bling

        if nf_data:
            return _status_nota_bling(nf_data)
        if situacao_num is not None:
            return _status_nota_bling({"situacao": situacao_num})
    except Exception:
        pass

    if situacao_num in _NF_SITUACAO_CANCELADA:
        return "Cancelada"
    if situacao_num in _NF_SITUACAO_AUTORIZADA:
        return "Autorizada"
    if situacao_num == 1:
        return "Pendente"
    return (
        _texto(_dict(nf_data.get("situacao")).get("descricao"))
        or _texto(nf_data.get("status"))
        or "Pendente"
    )


def _nf_webhook_autorizada(
    nf_data: dict | None, situacao_num: int | None = None
) -> bool:
    return (
        _status_nota_webhook(nf_data, situacao_num) or ""
    ).strip().lower() == "autorizada"


def _nf_webhook_cancelada(
    nf_data: dict | None, situacao_num: int | None = None
) -> bool:
    return (
        _status_nota_webhook(nf_data, situacao_num) or ""
    ).strip().lower() == "cancelada"


def _atualizar_cache_nota_webhook(
    *,
    db: Session,
    tenant_id,
    nf_data: dict | None,
    source: str,
) -> None:
    nf_data = _dict(nf_data)
    nf_id = _texto(nf_data.get("id"))
    if not tenant_id or not nf_id:
        return

    try:
        from app.nfe_routes import _normalizar_nota_bling

        modelo = _modelo_nota_bling(nf_data)
        nota = _normalizar_nota_bling({**nf_data, "id": nf_id}, modelo=modelo)
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source=source,
            resumo_payload=nf_data,
            detalhe_payload=nf_data,
        )
    except Exception as exc:
        logger.warning(
            f"[BLING NF] Falha ao atualizar cache local da NF {nf_id}: {exc}"
        )


def _query_itens_sem_produto(db: Session, tenant_id):
    from app.produtos_models import Produto

    produto_existe = exists().where(
        Produto.tenant_id == tenant_id,
        or_(
            Produto.codigo == PedidoIntegradoItem.sku,
            Produto.codigo_barras == PedidoIntegradoItem.sku,
        ),
    )

    return (
        db.query(PedidoIntegradoItem, PedidoIntegrado)
        .join(
            PedidoIntegrado,
            PedidoIntegrado.id == PedidoIntegradoItem.pedido_integrado_id,
        )
        .filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            not_(produto_existe),
        )
        .order_by(PedidoIntegradoItem.reservado_em.desc())
    )


def _executar_autocadastro_skus(
    db: Session, tenant_id, rows, max_skus_autocadastro: int
):
    skus = []
    vistos = set()

    for item, _pedido in rows:
        sku = (item.sku or "").strip()
        if not sku or sku in vistos:
            continue
        vistos.add(sku)
        skus.append(sku)
        if len(skus) >= max_skus_autocadastro:
            break

    auto_cadastros_executados = 0
    auto_cadastros_falhas = 0

    for sku in skus:
        try:
            produto = criar_produto_automatico_do_bling(
                db=db,
                tenant_id=tenant_id,
                sku=sku,
            )
            if produto:
                auto_cadastros_executados += 1
        except Exception as e:
            auto_cadastros_falhas += 1
            logger.warning(f"[AUTO-BLING-NF] Falha no autocadastro de SKU {sku}: {e}")

    if auto_cadastros_executados > 0:
        db.commit()

    return auto_cadastros_executados, auto_cadastros_falhas


def _serializar_itens_sem_produto(rows):
    def _fmt(dt):
        if not dt:
            return None
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    return [
        {
            "item_id": item.id,
            "sku": item.sku,
            "descricao": item.descricao,
            "quantidade": item.quantidade,
            "reservado_em": _fmt(item.reservado_em),
            "vendido_em": _fmt(item.vendido_em),
            "liberado_em": _fmt(item.liberado_em),
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "pedido_bling_id": pedido.pedido_bling_id,
            "pedido_status": pedido.status,
            "pedido_confirmado_em": _fmt(pedido.confirmado_em),
        }
        for item, pedido in rows
    ]
