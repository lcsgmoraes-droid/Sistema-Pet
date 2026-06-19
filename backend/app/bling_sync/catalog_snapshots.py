"""Snapshots de catalogo e cobertura da sincronizacao Bling."""

from datetime import UTC, datetime
import logging
import threading
import time

from sqlalchemy.orm import Session

from ..bling_integration import BlingAPI
from ..produtos_models import Produto, ProdutoBlingSync
from .product_matching import (
    _acao_faltante_bling,
    _barcode_bling,
    _coerce_float,
    _extrair_codigos_bling_item,
    _extrair_lista_produtos_bling,
    _indexar_produtos_locais_por_codigo,
    _motivo_faltante_bling,
    _origem_match_produto_bling,
    _produto_eh_pai,
    _produto_sincroniza_estoque,
    _sku_bling,
    _tipo_produto_local,
)
from .snapshots import (
    _delete_shared_snapshot,
    _read_shared_snapshot,
    _shared_snapshot_age_seconds,
    _write_shared_snapshot,
)
from .status_queries import _count_sync_problems_abertos

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_cobertura_bling_lock = threading.Lock()
_cobertura_bling_cache: dict[int, dict] = {}

_faltantes_bling_lock = threading.Lock()
_faltantes_bling_cache: dict[int, dict] = {}

_sem_vinculo_match_bling_lock = threading.Lock()
_sem_vinculo_match_bling_cache: dict[int, dict] = {}

_catalogo_bling_lock = threading.Lock()
_catalogo_bling_cache: dict[int, dict] = {}
_CATALOGO_FORCE_REFRESH_REUSE_SECONDS = 15


def _invalidate_bling_snapshots(tenant_id: int) -> None:
    with _cobertura_bling_lock:
        _cobertura_bling_cache.pop(tenant_id, None)
    with _faltantes_bling_lock:
        _faltantes_bling_cache.pop(tenant_id, None)
    with _sem_vinculo_match_bling_lock:
        _sem_vinculo_match_bling_cache.pop(tenant_id, None)

    for snapshot_name in ("cobertura", "faltantes", "sem_vinculo"):
        _delete_shared_snapshot(snapshot_name, tenant_id)


def _remover_ids_do_snapshot_sem_vinculo_cache(
    tenant_id, produto_ids: list[int]
) -> None:
    ids_para_remover = {
        int(produto_id) for produto_id in produto_ids if produto_id is not None
    }
    if not ids_para_remover:
        return

    payload = None

    with _sem_vinculo_match_bling_lock:
        cache_atual = _sem_vinculo_match_bling_cache.get(tenant_id)
        if cache_atual and cache_atual.get("payload"):
            payload = dict(cache_atual.get("payload", {}) or {})

    if payload is None:
        snapshot_compartilhado = _read_shared_snapshot("sem_vinculo", tenant_id)
        if snapshot_compartilhado and snapshot_compartilhado.get("payload"):
            payload = dict(snapshot_compartilhado.get("payload", {}) or {})

    if payload is None:
        return

    itens_atuais = list(payload.get("items", []) or [])
    itens_filtrados = [
        item
        for item in itens_atuais
        if int(item.get("id") or 0) not in ids_para_remover
    ]

    removidos = len(itens_atuais) - len(itens_filtrados)
    if removidos <= 0:
        return

    payload["items"] = itens_filtrados
    payload["total"] = len(itens_filtrados)
    payload["total_sem_vinculo_universo_local"] = max(
        int(payload.get("total_sem_vinculo_universo_local", len(itens_filtrados)))
        - removidos,
        0,
    )
    payload["atualizado_em"] = utc_now()

    with _sem_vinculo_match_bling_lock:
        _sem_vinculo_match_bling_cache[tenant_id] = {
            "ts_monotonic": time.monotonic(),
            "payload": payload,
        }

    _write_shared_snapshot("sem_vinculo", tenant_id, payload)


def _listar_todos_produtos_bling(
    bling: BlingAPI, limite: int = 100, max_paginas: int = 100
) -> tuple[list[dict], bool]:
    itens: list[dict] = []
    completo = True

    for pagina in range(1, max_paginas + 1):
        resultado = None
        ultima_falha = None
        for tentativa in range(3):
            try:
                resultado = bling.listar_produtos(pagina=pagina, limite=limite)
                ultima_falha = None
                break
            except Exception as e:
                ultima_falha = e
                mensagem = str(e)
                if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
                    time.sleep(0.8 + tentativa * 0.7)
                    continue
                raise

        if ultima_falha:
            logger.warning(
                "⚠️ Coleta parcial no Bling (página %s): %s", pagina, ultima_falha
            )
            completo = False
            break

        pagina_itens = _extrair_lista_produtos_bling(resultado)
        if not pagina_itens:
            break

        itens.extend(pagina_itens)
        if len(pagina_itens) < limite:
            break
    else:
        completo = False

    return itens, completo


def _get_catalogo_bling_snapshot(tenant_id: int, force_refresh: bool = False) -> dict:
    agora = time.monotonic()
    cache_compartilhado = _read_shared_snapshot("catalogo", tenant_id)

    with _catalogo_bling_lock:
        cache_atual = _catalogo_bling_cache.get(tenant_id)
        if cache_atual and cache_atual.get("payload"):
            idade = int(max(agora - cache_atual.get("ts_monotonic", 0), 0))
            pode_reusar_no_force_refresh = idade < _CATALOGO_FORCE_REFRESH_REUSE_SECONDS

            if not force_refresh or pode_reusar_no_force_refresh:
                return {
                    **cache_atual.get("payload", {}),
                    "snapshot_disponivel": True,
                    "cache_idade_segundos": idade,
                }

    if cache_compartilhado and cache_compartilhado.get("payload"):
        idade_compartilhada = _shared_snapshot_age_seconds(cache_compartilhado)
        pode_reusar_no_force_refresh = (
            idade_compartilhada < _CATALOGO_FORCE_REFRESH_REUSE_SECONDS
        )

        if not force_refresh or pode_reusar_no_force_refresh:
            payload_compartilhado = dict(cache_compartilhado.get("payload", {}) or {})
            with _catalogo_bling_lock:
                _catalogo_bling_cache[tenant_id] = {
                    "ts_monotonic": time.monotonic(),
                    "payload": payload_compartilhado,
                }
            return {
                **payload_compartilhado,
                "snapshot_disponivel": True,
                "cache_idade_segundos": idade_compartilhada,
            }

    if not force_refresh:
        return {
            "items": [],
            "total": 0,
            "coleta_bling_completa": False,
            "atualizado_em": None,
            "snapshot_disponivel": False,
            "cache_idade_segundos": 0,
            "precisa_atualizar": True,
        }

    try:
        bling = BlingAPI()
        bling_itens, coleta_completa = _listar_todos_produtos_bling(
            bling=bling, limite=100, max_paginas=100
        )
        payload = {
            "items": bling_itens,
            "total": len(bling_itens),
            "coleta_bling_completa": coleta_completa,
            "atualizado_em": utc_now(),
        }
    except Exception as error:
        if cache_compartilhado and cache_compartilhado.get("payload"):
            payload = dict(cache_compartilhado.get("payload", {}) or {})
            payload["coleta_bling_completa"] = False
            payload["cache_utilizado_por_falha"] = True
            payload["erro_coleta_bling"] = str(error)
            return {
                **payload,
                "snapshot_disponivel": True,
                "cache_idade_segundos": _shared_snapshot_age_seconds(
                    cache_compartilhado
                ),
            }
        raise

    with _catalogo_bling_lock:
        _catalogo_bling_cache[tenant_id] = {
            "ts_monotonic": time.monotonic(),
            "payload": payload,
        }
    _write_shared_snapshot("catalogo", tenant_id, payload)

    return {
        **payload,
        "snapshot_disponivel": True,
        "cache_idade_segundos": 0,
    }


def _calcular_resumo_cobertura_bling(
    db: Session,
    tenant_id: int,
    bling_itens: list[dict],
    coleta_completa: bool,
) -> dict:
    produtos_locais = db.query(Produto).filter(Produto.tenant_id == tenant_id).all()

    produtos_por_id = {produto.id: produto for produto in produtos_locais}
    codigos_para_produto = _indexar_produtos_locais_por_codigo(produtos_locais)

    syncs = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != "",
        )
        .all()
    )
    sync_por_produto = {sync.produto_id: sync for sync in syncs}

    total_bling = len(bling_itens)
    ids_syncaveis_com_match: set[int] = set()
    bling_com_match = 0
    bling_match_catalogo_sem_sync = 0
    bling_monitoraveis = 0
    bling_sync_ok = 0

    for item in bling_itens:
        codigos_bling = _extrair_codigos_bling_item(item)
        if not codigos_bling:
            continue

        candidatos: set[int] = set()
        for codigo in codigos_bling:
            candidatos.update(codigos_para_produto.get(codigo, set()))

        if not candidatos:
            continue

        bling_com_match += 1
        candidatos_syncaveis = {
            produto_id
            for produto_id in candidatos
            if _produto_sincroniza_estoque(produtos_por_id.get(produto_id))
        }

        if not candidatos_syncaveis:
            bling_match_catalogo_sem_sync += 1
            continue

        bling_monitoraveis += 1
        ids_syncaveis_com_match.update(candidatos_syncaveis)

        bling_id = str(item.get("id") or "").strip()
        if not bling_id:
            continue

        for produto_id in candidatos_syncaveis:
            sync = sync_por_produto.get(produto_id)
            if not sync:
                continue
            if str(sync.bling_produto_id or "").strip() != bling_id:
                continue
            if not sync.sincronizar:
                continue
            if sync.status != "ativo":
                continue
            bling_sync_ok += 1
            break

    total_local_syncavel = sum(
        1 for produto in produtos_locais if _produto_sincroniza_estoque(produto)
    )
    somente_sistema = max(total_local_syncavel - len(ids_syncaveis_com_match), 0)
    sync_problemas_abertos = _count_sync_problems_abertos(db, tenant_id)

    return {
        "total_bling": total_bling,
        "bling_com_match_no_sistema": bling_com_match,
        "bling_sem_match_no_sistema": max(total_bling - bling_com_match, 0),
        "bling_sync_ok": bling_sync_ok,
        "bling_match_catalogo_sem_sync": bling_match_catalogo_sem_sync,
        "bling_com_problema": max(bling_monitoraveis - bling_sync_ok, 0),
        "sync_problemas_abertos": sync_problemas_abertos,
        "total_sistema": total_local_syncavel,
        "somente_sistema": somente_sistema,
        "coleta_bling_completa": coleta_completa,
        "atualizado_em": utc_now(),
        "snapshot_disponivel": True,
    }


def _get_resumo_cobertura_bling(
    db: Session, tenant_id: int, force_refresh: bool = False
) -> dict:
    agora = time.monotonic()
    cache_atual = None
    cache_compartilhado = _read_shared_snapshot("cobertura", tenant_id)

    with _cobertura_bling_lock:
        cache_atual = _cobertura_bling_cache.get(tenant_id)

    if not force_refresh and cache_atual:
        return {
            **cache_atual.get("payload", {}),
            "cache_idade_segundos": int(
                max(agora - cache_atual.get("ts_monotonic", 0), 0)
            ),
        }

    if not force_refresh and cache_compartilhado and cache_compartilhado.get("payload"):
        idade_compartilhada = _shared_snapshot_age_seconds(cache_compartilhado)
        payload_compartilhado = dict(cache_compartilhado.get("payload", {}) or {})
        with _cobertura_bling_lock:
            _cobertura_bling_cache[tenant_id] = {
                "ts_monotonic": time.monotonic(),
                "payload": payload_compartilhado,
            }
        return {
            **payload_compartilhado,
            "cache_idade_segundos": idade_compartilhada,
        }

    try:
        catalogo = _get_catalogo_bling_snapshot(
            tenant_id=tenant_id, force_refresh=force_refresh
        )
        if not catalogo.get("snapshot_disponivel"):
            return {
                "total_bling": 0,
                "bling_com_match_no_sistema": 0,
                "bling_sem_match_no_sistema": 0,
                "bling_sync_ok": 0,
                "bling_com_problema": 0,
                "sync_problemas_abertos": 0,
                "total_sistema": 0,
                "somente_sistema": 0,
                "coleta_bling_completa": False,
                "atualizado_em": None,
                "snapshot_disponivel": False,
                "cache_idade_segundos": 0,
                "precisa_atualizar": True,
            }
        payload = _calcular_resumo_cobertura_bling(
            db,
            tenant_id,
            bling_itens=list(catalogo.get("items", []) or []),
            coleta_completa=bool(catalogo.get("coleta_bling_completa", True)),
        )
    except Exception as e:
        if cache_atual and cache_atual.get("payload"):
            payload = dict(cache_atual.get("payload", {}))
            payload["coleta_bling_completa"] = False
            payload["cache_utilizado_por_falha"] = True
            payload["erro_coleta_bling"] = str(e)
            payload["atualizado_em"] = payload.get("atualizado_em") or utc_now()
            return payload
        raise

    with _cobertura_bling_lock:
        _cobertura_bling_cache[tenant_id] = {
            "ts_monotonic": agora,
            "payload": payload,
        }
    _write_shared_snapshot("cobertura", tenant_id, payload)

    return payload


def _calcular_snapshot_faltantes_bling(
    db: Session,
    tenant_id: int,
    bling_itens: list[dict],
    coleta_completa: bool,
) -> dict:
    produtos_locais = db.query(Produto).filter(Produto.tenant_id == tenant_id).all()
    codigos_locais = set(_indexar_produtos_locais_por_codigo(produtos_locais).keys())

    faltantes: list[dict] = []
    ids_ja_adicionados: set[str] = set()
    for item in bling_itens:
        codigos_bling = _extrair_codigos_bling_item(item)
        if codigos_bling and codigos_bling.intersection(codigos_locais):
            continue

        bling_id = str(item.get("id") or "").strip()
        if bling_id and bling_id in ids_ja_adicionados:
            continue
        if bling_id:
            ids_ja_adicionados.add(bling_id)

        sku = _sku_bling(item)
        codigo_barras = _barcode_bling(item)
        faltantes.append(
            {
                "id": bling_id,
                "descricao": item.get("nome")
                or item.get("descricao")
                or "Sem descrição",
                "codigo": item.get("codigo") or item.get("sku") or "",
                "sku": sku,
                "codigo_barras": codigo_barras,
                "estoque": _coerce_float(
                    item.get("estoque") or item.get("saldoFisicoTotal") or 0
                ),
                "motivo": _motivo_faltante_bling(item),
                "acao_sugerida": _acao_faltante_bling(item),
                "pronto_para_autocorrecao": bool(sku or codigo_barras),
            }
        )

    return {
        "items": faltantes,
        "total": len(faltantes),
        "total_bling": len(bling_itens),
        "coleta_bling_completa": coleta_completa,
        "atualizado_em": utc_now(),
        "snapshot_disponivel": True,
    }


def _get_snapshot_faltantes_bling(
    db: Session,
    tenant_id: int,
    force_refresh: bool = False,
) -> dict:
    agora = time.monotonic()
    cache_atual = None
    cache_compartilhado = _read_shared_snapshot("faltantes", tenant_id)

    with _faltantes_bling_lock:
        cache_atual = _faltantes_bling_cache.get(tenant_id)

    if not force_refresh and cache_atual:
        return {
            **cache_atual.get("payload", {}),
            "snapshot_disponivel": True,
            "cache_idade_segundos": int(
                max(agora - cache_atual.get("ts_monotonic", 0), 0)
            ),
        }

    if not force_refresh and cache_compartilhado and cache_compartilhado.get("payload"):
        idade_compartilhada = _shared_snapshot_age_seconds(cache_compartilhado)
        payload_compartilhado = dict(cache_compartilhado.get("payload", {}) or {})
        with _faltantes_bling_lock:
            _faltantes_bling_cache[tenant_id] = {
                "ts_monotonic": time.monotonic(),
                "payload": payload_compartilhado,
            }
        return {
            **payload_compartilhado,
            "snapshot_disponivel": True,
            "cache_idade_segundos": idade_compartilhada,
        }

    try:
        catalogo = _get_catalogo_bling_snapshot(
            tenant_id=tenant_id, force_refresh=force_refresh
        )
        if not catalogo.get("snapshot_disponivel"):
            return {
                "items": [],
                "total": 0,
                "total_bling": 0,
                "snapshot_disponivel": False,
                "coleta_bling_completa": False,
                "precisa_atualizar": True,
                "atualizado_em": None,
                "cache_idade_segundos": 0,
            }
        payload = _calcular_snapshot_faltantes_bling(
            db,
            tenant_id,
            bling_itens=list(catalogo.get("items", []) or []),
            coleta_completa=bool(catalogo.get("coleta_bling_completa", True)),
        )
    except Exception as e:
        if cache_atual and cache_atual.get("payload"):
            payload = dict(cache_atual.get("payload", {}))
            payload["snapshot_disponivel"] = True
            payload["coleta_bling_completa"] = False
            payload["cache_utilizado_por_falha"] = True
            payload["erro_coleta_bling"] = str(e)
            return payload
        raise

    with _faltantes_bling_lock:
        _faltantes_bling_cache[tenant_id] = {
            "ts_monotonic": agora,
            "payload": payload,
        }
    _write_shared_snapshot("faltantes", tenant_id, payload)

    return {
        **payload,
        "snapshot_disponivel": True,
        "cache_idade_segundos": 0,
    }


def _calcular_snapshot_sem_vinculo_com_match_bling(
    db: Session,
    tenant_id: int,
    bling_itens: list[dict],
    coleta_completa: bool,
) -> dict:
    subq_vinculados = (
        db.query(ProdutoBlingSync.produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != "",
        )
        .subquery()
    )

    produtos_sem_vinculo = (
        db.query(
            Produto.id,
            Produto.nome,
            Produto.codigo,
            Produto.tipo_produto,
            Produto.estoque_atual,
            Produto.codigo_barras,
            Produto.gtin_ean,
            Produto.gtin_ean_tributario,
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.codigo.isnot(None),
            Produto.codigo != "",
        )
        .filter(Produto.id.notin_(subq_vinculados))
        .all()
    )

    codigos_para_ids = _indexar_produtos_locais_por_codigo(produtos_sem_vinculo)
    produtos_por_id = {produto.id: produto for produto in produtos_sem_vinculo}
    detalhes_match_por_id: dict[int, dict] = {}

    for item in bling_itens:
        codigos_bling = _extrair_codigos_bling_item(item)
        if not codigos_bling:
            continue
        candidatos: set[int] = set()
        for codigo in codigos_bling:
            candidatos.update(codigos_para_ids.get(codigo, set()))

        if not candidatos:
            continue

        for produto_id in candidatos:
            if produto_id in detalhes_match_por_id:
                continue
            produto = produtos_por_id.get(produto_id)
            if not produto:
                continue
            match_origem = _origem_match_produto_bling(produto, item)
            detalhes_match_por_id[produto_id] = {
                "bling_id": str(item.get("id") or "").strip(),
                "bling_nome": item.get("nome")
                or item.get("descricao")
                or "Sem descricao",
                "bling_codigo": item.get("codigo") or item.get("sku") or "",
                "bling_sku": _sku_bling(item),
                "bling_codigo_barras": _barcode_bling(item),
                "match_origem": match_origem,
            }

    itens_match = [
        {
            "id": produto.id,
            "nome": produto.nome,
            "codigo": produto.codigo,
            "tipo_produto": _tipo_produto_local(produto),
            "codigo_barras": produto.codigo_barras,
            "estoque_atual": float(produto.estoque_atual or 0),
            "bling_id": detalhes_match_por_id[produto.id]["bling_id"],
            "bling_nome": detalhes_match_por_id[produto.id]["bling_nome"],
            "bling_codigo": detalhes_match_por_id[produto.id]["bling_codigo"],
            "bling_sku": detalhes_match_por_id[produto.id]["bling_sku"],
            "bling_codigo_barras": detalhes_match_por_id[produto.id][
                "bling_codigo_barras"
            ],
            "match_origem": detalhes_match_por_id[produto.id]["match_origem"],
            "sincroniza_estoque": _produto_sincroniza_estoque(produto),
            "motivo": (
                (
                    "Encontramos esse item no CorePet como produto PAI. O vinculo pode existir para catalogo, "
                    "mas o estoque fica nas variacoes e nao sera sincronizado por esse cadastro."
                )
                if _produto_eh_pai(produto)
                else (
                    "Encontramos esse item no Bling por SKU, mas o vinculo ainda nao foi criado."
                    if detalhes_match_por_id[produto.id]["match_origem"] == "sku"
                    else "Encontramos esse item no Bling pelo codigo de barras, mas o vinculo ainda nao foi criado."
                )
            ),
            "acao_sugerida": "Vincular sem sync de estoque"
            if _produto_eh_pai(produto)
            else "Vincular agora",
        }
        for produto in produtos_sem_vinculo
        if produto.id in detalhes_match_por_id
    ]

    return {
        "items": itens_match,
        "total": len(itens_match),
        "total_sem_vinculo_universo_local": len(produtos_sem_vinculo),
        "total_bling": len(bling_itens),
        "coleta_bling_completa": coleta_completa,
        "atualizado_em": utc_now(),
        "snapshot_disponivel": True,
    }


def _get_snapshot_sem_vinculo_com_match_bling(
    db: Session,
    tenant_id: int,
    force_refresh: bool = False,
) -> dict:
    agora = time.monotonic()
    cache_compartilhado = _read_shared_snapshot("sem_vinculo", tenant_id)

    with _sem_vinculo_match_bling_lock:
        cache_atual = _sem_vinculo_match_bling_cache.get(tenant_id)

    if not force_refresh and cache_atual:
        return {
            **cache_atual.get("payload", {}),
            "cache_idade_segundos": int(
                max(agora - cache_atual.get("ts_monotonic", 0), 0)
            ),
        }

    if not force_refresh and cache_compartilhado and cache_compartilhado.get("payload"):
        idade_compartilhada = _shared_snapshot_age_seconds(cache_compartilhado)
        payload_compartilhado = dict(cache_compartilhado.get("payload", {}) or {})
        with _sem_vinculo_match_bling_lock:
            _sem_vinculo_match_bling_cache[tenant_id] = {
                "ts_monotonic": time.monotonic(),
                "payload": payload_compartilhado,
            }
        return {
            **payload_compartilhado,
            "cache_idade_segundos": idade_compartilhada,
        }

    try:
        catalogo = _get_catalogo_bling_snapshot(
            tenant_id=tenant_id, force_refresh=force_refresh
        )
        if not catalogo.get("snapshot_disponivel"):
            return {
                "items": [],
                "total": 0,
                "total_sem_vinculo_universo_local": 0,
                "total_bling": 0,
                "coleta_bling_completa": False,
                "atualizado_em": None,
                "snapshot_disponivel": False,
                "cache_idade_segundos": 0,
                "precisa_atualizar": True,
            }
        payload = _calcular_snapshot_sem_vinculo_com_match_bling(
            db,
            tenant_id,
            bling_itens=list(catalogo.get("items", []) or []),
            coleta_completa=bool(catalogo.get("coleta_bling_completa", True)),
        )
    except Exception as e:
        if cache_atual and cache_atual.get("payload"):
            payload = dict(cache_atual.get("payload", {}))
            payload["coleta_bling_completa"] = False
            payload["cache_utilizado_por_falha"] = True
            payload["erro_coleta_bling"] = str(e)
            payload["cache_idade_segundos"] = int(
                max(agora - cache_atual.get("ts_monotonic", 0), 0)
            )
            return payload
        raise

    with _sem_vinculo_match_bling_lock:
        _sem_vinculo_match_bling_cache[tenant_id] = {
            "ts_monotonic": agora,
            "payload": payload,
        }
    _write_shared_snapshot("sem_vinculo", tenant_id, payload)

    return {
        **payload,
        "cache_idade_segundos": 0,
    }
