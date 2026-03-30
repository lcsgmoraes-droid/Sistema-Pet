from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache


def _texto(value) -> str | None:
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_dict(value) -> dict | None:
    return value if isinstance(value, dict) and value else None


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    texto = _texto(value)
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

    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto[:19], formato)
        except ValueError:
            continue
    return None


def serializar_nota_cache(registro: BlingNotaFiscalCache) -> dict:
    valor = registro.valor
    if isinstance(valor, Decimal):
        valor = float(valor)
    elif valor is not None:
        valor = float(valor)

    return {
        "id": registro.bling_id or "",
        "venda_id": None,
        "numero": registro.numero,
        "serie": registro.serie,
        "tipo": registro.tipo or ("nfce" if registro.modelo == 65 else "nfe"),
        "tipo_codigo": 1 if registro.modelo == 65 else 0,
        "modelo": registro.modelo,
        "chave": registro.chave or "",
        "status": registro.status or "Pendente",
        "data_emissao": registro.data_emissao.isoformat() if registro.data_emissao else None,
        "valor": valor or 0.0,
        "cliente": registro.cliente or {"id": None, "nome": None, "cpf_cnpj": None},
        "canal": registro.canal,
        "canal_label": registro.canal_label,
        "loja": registro.loja or {"id": None, "nome": None},
        "unidade_negocio": registro.unidade_negocio or {"id": None, "nome": None},
        "numero_loja_virtual": registro.numero_loja_virtual,
        "origem_loja_virtual": registro.origem_loja_virtual,
        "origem_canal_venda": registro.origem_canal_venda,
        "numero_pedido_loja": registro.numero_pedido_loja,
        "pedido_bling_id_ref": registro.pedido_bling_id_ref,
        "origem": registro.source or "cache_local",
    }


def listar_notas_cache(
    db: Session,
    tenant_id,
    *,
    data_inicial: str | None = None,
    data_final: str | None = None,
    situacao: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    query = db.query(BlingNotaFiscalCache).filter(BlingNotaFiscalCache.tenant_id == tenant_id)

    if situacao:
        query = query.filter(func.lower(BlingNotaFiscalCache.status) == situacao.strip().lower())

    data_inicial_dt = _parse_datetime(data_inicial)
    if data_inicial_dt:
        query = query.filter(func.date(BlingNotaFiscalCache.data_emissao) >= data_inicial_dt.date())

    data_final_dt = _parse_datetime(data_final)
    if data_final_dt:
        query = query.filter(func.date(BlingNotaFiscalCache.data_emissao) <= data_final_dt.date())

    query = query.order_by(
        BlingNotaFiscalCache.data_emissao.desc().nullslast(),
        BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
        BlingNotaFiscalCache.id.desc(),
    )

    if limit:
        query = query.limit(limit)

    return [serializar_nota_cache(registro) for registro in query.all()]


def existe_nota_cache_no_intervalo(
    db: Session,
    tenant_id,
    *,
    data_inicial: str | None = None,
    data_final: str | None = None,
    situacao: str | None = None,
) -> bool:
    return bool(
        listar_notas_cache(
            db,
            tenant_id,
            data_inicial=data_inicial,
            data_final=data_final,
            situacao=situacao,
            limit=1,
        )
    )


def obter_estado_cache_notas(db: Session, tenant_id) -> dict:
    total, ultima_data_emissao, ultimo_sync = (
        db.query(
            func.count(BlingNotaFiscalCache.id),
            func.max(BlingNotaFiscalCache.data_emissao),
            func.max(BlingNotaFiscalCache.last_synced_at),
        )
        .filter(BlingNotaFiscalCache.tenant_id == tenant_id)
        .one()
    )
    return {
        "total": int(total or 0),
        "ultima_data_emissao": ultima_data_emissao,
        "ultimo_sync": ultimo_sync,
    }


def obter_detalhe_nota_cache(
    db: Session,
    tenant_id,
    *,
    nfe_id: int | str,
    modelo: int | None = None,
) -> dict | None:
    query = db.query(BlingNotaFiscalCache).filter(
        BlingNotaFiscalCache.tenant_id == tenant_id,
        BlingNotaFiscalCache.bling_id == str(nfe_id),
    )
    if modelo in {55, 65}:
        query = query.filter(BlingNotaFiscalCache.modelo == modelo)

    registro = (
        query.order_by(BlingNotaFiscalCache.detalhada_em.desc().nullslast(), BlingNotaFiscalCache.id.desc())
        .first()
    )
    if not registro or not isinstance(registro.detalhe_payload, dict):
        return None
    return registro.detalhe_payload


def upsert_nota_cache(
    db: Session,
    tenant_id,
    nota: dict,
    *,
    source: str | None = None,
    resumo_payload: dict | None = None,
    detalhe_payload: dict | None = None,
) -> BlingNotaFiscalCache | None:
    bling_id = _texto(nota.get("id"))
    if not bling_id or bling_id in {"0", "-1"}:
        return None

    modelo = _coerce_int(nota.get("modelo"), 55)
    if modelo not in {55, 65}:
        modelo = 55

    registro = None
    for pendente in getattr(db, "new", ()):
        if not isinstance(pendente, BlingNotaFiscalCache):
            continue
        if (
            getattr(pendente, "tenant_id", None) == tenant_id
            and getattr(pendente, "bling_id", None) == bling_id
            and getattr(pendente, "modelo", None) == modelo
        ):
            registro = pendente
            break

    if not registro:
        registro = (
            db.query(BlingNotaFiscalCache)
            .filter(
                BlingNotaFiscalCache.tenant_id == tenant_id,
                BlingNotaFiscalCache.bling_id == bling_id,
                BlingNotaFiscalCache.modelo == modelo,
            )
            .first()
        )

    if not registro:
        registro = BlingNotaFiscalCache(
            tenant_id=tenant_id,
            bling_id=bling_id,
            modelo=modelo,
            tipo=_texto(nota.get("tipo")) or ("nfce" if modelo == 65 else "nfe"),
        )

    registro.tipo = _texto(nota.get("tipo")) or registro.tipo or ("nfce" if modelo == 65 else "nfe")
    registro.numero = _texto(nota.get("numero")) or registro.numero
    registro.serie = _texto(nota.get("serie")) or registro.serie
    registro.status = _texto(nota.get("status")) or registro.status
    registro.chave = _texto(nota.get("chave")) or registro.chave
    registro.data_emissao = _parse_datetime(nota.get("data_emissao")) or registro.data_emissao

    valor = _coerce_float(nota.get("valor"))
    if valor is not None:
        registro.valor = valor

    registro.cliente = _json_dict(nota.get("cliente")) or registro.cliente
    registro.loja = _json_dict(nota.get("loja")) or registro.loja
    registro.unidade_negocio = _json_dict(nota.get("unidade_negocio")) or registro.unidade_negocio

    registro.canal = _texto(nota.get("canal")) or registro.canal
    registro.canal_label = _texto(nota.get("canal_label")) or registro.canal_label
    registro.numero_loja_virtual = _texto(nota.get("numero_loja_virtual")) or registro.numero_loja_virtual
    registro.origem_loja_virtual = _texto(nota.get("origem_loja_virtual")) or registro.origem_loja_virtual
    registro.origem_canal_venda = _texto(nota.get("origem_canal_venda")) or registro.origem_canal_venda
    registro.numero_pedido_loja = _texto(nota.get("numero_pedido_loja")) or registro.numero_pedido_loja
    registro.pedido_bling_id_ref = _texto(nota.get("pedido_bling_id_ref")) or registro.pedido_bling_id_ref
    registro.source = _texto(source) or registro.source or _texto(nota.get("origem")) or "cache_local"

    if isinstance(resumo_payload, dict) and resumo_payload:
        registro.resumo_payload = resumo_payload
    elif not registro.resumo_payload:
        registro.resumo_payload = nota

    if isinstance(detalhe_payload, dict) and detalhe_payload:
        registro.detalhe_payload = detalhe_payload
        registro.detalhada_em = datetime.utcnow()

    registro.last_synced_at = datetime.utcnow()
    db.add(registro)
    return registro
