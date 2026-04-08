"""
SINCRONIZAÇÃO BLING - Sistema Pet Shop Pro
Sincronização bidirecional de estoque entre sistema e Bling

Fluxo:
1. Venda Loja Física (PDV) → Atualiza Sistema → Envia para Bling
2. Venda Online (Bling) → Webhook → Atualiza Sistema
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import and_, or_, func, desc
from typing import Any, List, Optional
from datetime import UTC, datetime, timedelta
from pydantic import BaseModel, Field
from pathlib import Path
import json
import asyncio
import threading
import re
import time
import os

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue, EstoqueMovimentacao
from .bling_integration import BlingAPI
from .services.bling_nf_service import (
    buscar_produto_do_item,
    criar_produto_automatico_do_bling_por_item,
)
from .services.bling_sync_service import BlingSyncService, DIVERGENCIA_MINIMA

import logging
logger = logging.getLogger(__name__)


PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalizar_codigo_match(valor: Optional[str]) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", (valor or "").strip()).lower()


def _texto_limpo(valor: Optional[str]) -> str:
    return str(valor or "").strip()


def _coerce_float(valor, default: float = 0.0) -> float:
    if valor is None:
        return float(default)

    if isinstance(valor, dict):
        for chave in ("saldoFisicoTotal", "saldoVirtualTotal", "quantidade", "valor"):
            if chave in valor:
                return _coerce_float(valor.get(chave), default=default)
        return float(default)

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    if not texto:
        return float(default)

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except (TypeError, ValueError):
        return float(default)


def _latest_queue_ids_subquery_route(db: Session, tenant_id) -> Any:
    referencia_recente = func.coalesce(
        ProdutoBlingSyncQueue.proxima_tentativa_em,
        ProdutoBlingSyncQueue.processado_em,
        ProdutoBlingSyncQueue.ultima_tentativa_em,
        ProdutoBlingSyncQueue.updated_at,
        ProdutoBlingSyncQueue.created_at,
    )
    ranked = (
        db.query(
            ProdutoBlingSyncQueue.produto_id.label("produto_id"),
            ProdutoBlingSyncQueue.id.label("queue_id"),
            func.row_number().over(
                partition_by=ProdutoBlingSyncQueue.produto_id,
                order_by=(
                    desc(referencia_recente),
                    desc(ProdutoBlingSyncQueue.updated_at),
                    desc(ProdutoBlingSyncQueue.id),
                ),
            ).label("rn"),
        )
        .filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
        .subquery()
    )
    return (
        db.query(
            ranked.c.produto_id.label("produto_id"),
            ranked.c.queue_id.label("queue_id"),
        )
        .filter(ranked.c.rn == 1)
        .subquery()
    )


def _sku_bling(item: dict) -> str:
    return _texto_limpo(item.get("sku") or item.get("codigo"))


def _barcode_bling(item: dict) -> str:
    return _texto_limpo(item.get("codigoBarras") or item.get("gtin"))


def _motivo_faltante_bling(item: dict) -> str:
    sku = _sku_bling(item)
    barcode = _barcode_bling(item)

    if sku and barcode:
        return "Nao existe produto local com esse SKU nem com esse codigo de barras."
    if sku:
        return "O SKU do Bling ainda nao existe no Sistema Pet."
    if barcode:
        return "O codigo de barras do Bling ainda nao existe no Sistema Pet."
    return "O cadastro do Bling esta sem SKU e sem codigo de barras para autocorrecao."


def _acao_faltante_bling(item: dict) -> str:
    return "Criar e vincular" if (_sku_bling(item) or _barcode_bling(item)) else "Revisar cadastro no Bling"


def _montar_codigos_busca(codigo_principal: str, codigos_extras: Optional[list[str]] = None) -> list[str]:
    codigos: list[str] = []
    vistos: set[str] = set()

    for bruto in [codigo_principal, *(codigos_extras or [])]:
        codigo = (bruto or "").strip()
        if not codigo:
            continue

        candidatos = [codigo]
        codigo_normalizado = _normalizar_codigo_match(codigo)
        if codigo_normalizado and codigo_normalizado != codigo:
            candidatos.append(codigo_normalizado)

        for candidato in candidatos:
            chave = candidato.lower()
            if chave in vistos:
                continue
            vistos.add(chave)
            codigos.append(candidato)

    return codigos


def _escolher_item_melhor_match(itens: list[dict], codigos_busca: list[str]) -> dict:
    if not itens:
        return {}

    codigos_normalizados = {
        _normalizar_codigo_match(codigo)
        for codigo in codigos_busca
        if _normalizar_codigo_match(codigo)
    }

    if not codigos_normalizados:
        return itens[0]

    for item in itens:
        campos_codigo = [
            item.get("codigo"),
            item.get("sku"),
            item.get("codigoBarras"),
            item.get("gtin"),
        ]
        for campo in campos_codigo:
            codigo_item = _normalizar_codigo_match(str(campo or ""))
            if codigo_item and codigo_item in codigos_normalizados:
                return item

    return itens[0]


def _buscar_item_bling_para_vinculo(
    bling: BlingAPI,
    codigo_busca: str,
    nome_busca: str,
    codigos_extras: Optional[list[str]] = None,
) -> Optional[dict]:
    codigos_busca = _montar_codigos_busca(codigo_busca, codigos_extras)

    for codigo in codigos_busca:
        resultado = bling.listar_produtos(codigo=codigo, limite=50)
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            return _escolher_item_melhor_match(itens, codigos_busca)

        resultado = bling.listar_produtos(sku=codigo, limite=50)
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            return _escolher_item_melhor_match(itens, codigos_busca)

    if nome_busca:
        resultado = bling.listar_produtos(nome=nome_busca, limite=50)
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            return _escolher_item_melhor_match(itens, codigos_busca)

    return None


def _normalizar_termo_busca(valor: Optional[str]) -> str:
    return (valor or "").strip()


def _limpar_texto_busca(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip()


def _extrair_lista_produtos_bling(resultado: Optional[dict]) -> list[dict]:
    itens = (resultado or {}).get("data", [])
    produtos: list[dict] = []
    for item in itens:
        if isinstance(item, dict) and isinstance(item.get("produto"), dict):
            produtos.append(item.get("produto") or {})
        elif isinstance(item, dict):
            produtos.append(item)
    return produtos


def _buscar_produtos_bling_por_termo(bling: BlingAPI, termo: str, pagina: int, limite: int) -> list[dict]:
    termo_limpo = _limpar_texto_busca(termo)
    if not termo_limpo:
        return _extrair_lista_produtos_bling(bling.listar_produtos(pagina=pagina, limite=limite))

    resultados: list[dict] = []
    vistos: set[str] = set()

    consultas = [
        {"codigo": termo_limpo, "pagina": pagina, "limite": limite},
        {"sku": termo_limpo, "pagina": pagina, "limite": limite},
        {"nome": termo_limpo, "pagina": pagina, "limite": limite},
    ]

    for params in consultas:
        try:
            itens = _extrair_lista_produtos_bling(bling.listar_produtos(**params))
        except Exception:
            # Tenta as outras estratégias de busca para reduzir falhas por filtro específico.
            continue

        for item in itens:
            item_id = str(item.get("id") or "").strip()
            if not item_id or item_id in vistos:
                continue
            vistos.add(item_id)
            resultados.append(item)

    return resultados


def _buscar_item_bling_com_retry(
    bling: BlingAPI,
    codigo_busca: str,
    nome_busca: str,
    codigos_extras: Optional[list[str]] = None,
) -> Optional[dict]:
    ultima_falha = None
    for tentativa in range(3):
        try:
            return _buscar_item_bling_para_vinculo(bling, codigo_busca, nome_busca, codigos_extras=codigos_extras)
        except Exception as e:
            ultima_falha = e
            msg = str(e)
            if "429" in msg or "TOO_MANY_REQUESTS" in msg:
                time.sleep(0.8 + tentativa * 0.6)
                continue
            raise

    if ultima_falha:
        raise ultima_falha
    return None


def _upsert_sync_vinculo(
    db: Session,
    tenant_id,
    produto: Produto,
    bling_produto_id: str,
) -> None:
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto.id,
        ProdutoBlingSync.tenant_id == tenant_id
    ).first()

    if not sync:
        sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=produto.id)
        db.add(sync)

    sincronizar_estoque = _produto_sincroniza_estoque(produto)

    sync.bling_produto_id = bling_produto_id
    sync.sincronizar = sincronizar_estoque
    sync.estoque_compartilhado = sincronizar_estoque
    sync.status = "ativo" if sincronizar_estoque else "pausado"
    sync.erro_mensagem = None
    sync.updated_at = utc_now()


router = APIRouter(prefix="/estoque/sync", tags=["Sincronização Bling"])

_reconciliacao_geral_lock = threading.Lock()
_reconciliacao_geral_estado = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "result": None,
}

_cobertura_bling_lock = threading.Lock()
_cobertura_bling_cache: dict[int, dict] = {}
_COBERTURA_BLG_CACHE_SECONDS = 180

_faltantes_bling_lock = threading.Lock()
_faltantes_bling_cache: dict[int, dict] = {}
_FALTANTES_BLG_CACHE_SECONDS = 300

_sem_vinculo_match_bling_lock = threading.Lock()
_sem_vinculo_match_bling_cache: dict[int, dict] = {}
_SEM_VINCULO_MATCH_BLG_CACHE_SECONDS = 300

_catalogo_bling_lock = threading.Lock()
_catalogo_bling_cache: dict[int, dict] = {}
_CATALOGO_BLG_CACHE_SECONDS = 300
_CATALOGO_FORCE_REFRESH_REUSE_SECONDS = 15

_SNAPSHOT_STORAGE_ENV = "BLING_SNAPSHOT_DIR"
_SNAPSHOT_STORAGE_FALLBACK = Path("/tmp/petshop/bling_snapshots")
_SYNC_PROBLEMS_FRESHNESS_HOURS = 24


def _resolver_snapshot_storage_base() -> Path:
    candidatos: list[Path] = []

    env_path = os.getenv(_SNAPSHOT_STORAGE_ENV)
    if env_path:
        candidatos.append(Path(env_path))

    candidatos.extend([
        Path("/app/data/bling_snapshots"),
        Path("/app/uploads/bling_snapshots"),
        Path(__file__).resolve().parents[1] / "data" / "bling_snapshots",
        _SNAPSHOT_STORAGE_FALLBACK,
    ])

    vistos: set[str] = set()
    for candidato in candidatos:
        chave = str(candidato.resolve(strict=False))
        if chave in vistos:
            continue
        vistos.add(chave)

        try:
            candidato.mkdir(parents=True, exist_ok=True)
            teste = candidato / ".write_test"
            teste.write_text("ok", encoding="utf-8")
            teste.unlink(missing_ok=True)
            logger.info("Snapshots compartilhados do Bling em %s", candidato)
            return candidato
        except Exception as error:
            logger.warning("Snapshot compartilhado indisponivel em %s: %s", candidato, error)

    logger.warning("Nenhum diretorio de snapshot compartilhado ficou gravavel. Usando fallback %s", _SNAPSHOT_STORAGE_FALLBACK)
    return _SNAPSHOT_STORAGE_FALLBACK


_SNAPSHOT_STORAGE_BASE = _resolver_snapshot_storage_base()


def _snapshot_file_path(snapshot_name: str, tenant_id: int) -> Path:
    return _SNAPSHOT_STORAGE_BASE / str(tenant_id) / f"{snapshot_name}.json"


def _read_shared_snapshot(snapshot_name: str, tenant_id: int) -> Optional[dict]:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        logger.warning("Falha ao ler snapshot compartilhado %s do tenant %s: %s", snapshot_name, tenant_id, error)
        return None

    if not isinstance(data, dict) or not isinstance(data.get("payload"), dict):
        return None
    return data


def _write_shared_snapshot(snapshot_name: str, tenant_id: int, payload: dict) -> None:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "ts_epoch": time.time(),
            "payload": payload,
        }
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, default=str, ensure_ascii=False), encoding="utf-8")
        os.replace(temp_path, path)
    except Exception as error:
        logger.warning("Falha ao gravar snapshot compartilhado %s do tenant %s: %s", snapshot_name, tenant_id, error)


def _delete_shared_snapshot(snapshot_name: str, tenant_id: int) -> None:
    path = _snapshot_file_path(snapshot_name, tenant_id)
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except Exception as error:
        logger.warning("Falha ao remover snapshot compartilhado %s do tenant %s: %s", snapshot_name, tenant_id, error)


def _shared_snapshot_age_seconds(snapshot_record: Optional[dict]) -> int:
    if not snapshot_record:
        return 0

    try:
        ts_epoch = float(snapshot_record.get("ts_epoch") or 0)
    except Exception:
        ts_epoch = 0

    if ts_epoch <= 0:
        return 0
    return int(max(time.time() - ts_epoch, 0))


def _sync_problem_freshness_cutoff() -> datetime:
    return utc_now() - timedelta(hours=_SYNC_PROBLEMS_FRESHNESS_HOURS)


def _build_sync_problem_query(
    db: Session,
    tenant_id: int,
    busca: Optional[str] = None,
):
    fila_atual_ids = _latest_queue_ids_subquery_route(db, tenant_id)
    fila_atual = aliased(ProdutoBlingSyncQueue)
    cutoff = _sync_problem_freshness_cutoff()

    erro_sync_aberto = and_(
        ProdutoBlingSync.status == "erro",
        ProdutoBlingSync.erro_mensagem.isnot(None),
        ProdutoBlingSync.erro_mensagem != "",
        or_(
            fila_atual.id.is_(None),
            fila_atual.status.in_(["erro", "falha_final", "pendente", "processando"]),
        ),
    )
    fila_falhou = fila_atual.status.in_(["erro", "falha_final"])
    pendencia_sem_fila = and_(
        ProdutoBlingSync.status == "pendente",
        fila_atual.id.is_(None),
    )
    divergencia_atual = and_(
        ProdutoBlingSync.ultima_divergencia.isnot(None),
        func.abs(ProdutoBlingSync.ultima_divergencia) >= DIVERGENCIA_MINIMA,
        ProdutoBlingSync.ultima_conferencia_bling.isnot(None),
        ProdutoBlingSync.ultima_conferencia_bling >= cutoff,
        or_(
            ProdutoBlingSync.ultima_sincronizacao_sucesso.is_(None),
            ProdutoBlingSync.ultima_conferencia_bling >= ProdutoBlingSync.ultima_sincronizacao_sucesso,
        ),
    )

    query = (
        db.query(Produto, ProdutoBlingSync, fila_atual)
        .join(
            ProdutoBlingSync,
            Produto.id == ProdutoBlingSync.produto_id,
        )
        .outerjoin(
            fila_atual_ids,
            fila_atual_ids.c.produto_id == Produto.id,
        )
        .outerjoin(
            fila_atual,
            fila_atual.id == fila_atual_ids.c.queue_id,
        )
        .filter(
            Produto.tenant_id == tenant_id,
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.sincronizar == True,
        )
        .filter(
            or_(
                erro_sync_aberto,
                fila_falhou,
                pendencia_sem_fila,
                divergencia_atual,
            )
        )
    )

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                ProdutoBlingSync.bling_produto_id.ilike(termo),
                ProdutoBlingSync.erro_mensagem.ilike(termo),
                fila_atual.ultimo_erro.ilike(termo),
            )
        )

    return query, fila_atual


def _count_sync_problems_abertos(db: Session, tenant_id: int) -> int:
    query, _fila_atual = _build_sync_problem_query(db, tenant_id=tenant_id, busca=None)
    return int(query.order_by(None).count())


def _invalidate_bling_snapshots(tenant_id: int) -> None:
    with _cobertura_bling_lock:
        _cobertura_bling_cache.pop(tenant_id, None)
    with _faltantes_bling_lock:
        _faltantes_bling_cache.pop(tenant_id, None)
    with _sem_vinculo_match_bling_lock:
        _sem_vinculo_match_bling_cache.pop(tenant_id, None)

    for snapshot_name in ("cobertura", "faltantes", "sem_vinculo"):
        _delete_shared_snapshot(snapshot_name, tenant_id)


def _remover_ids_do_snapshot_sem_vinculo_cache(tenant_id, produto_ids: list[int]) -> None:
    ids_para_remover = {
        int(produto_id)
        for produto_id in produto_ids
        if produto_id is not None
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
        int(payload.get("total_sem_vinculo_universo_local", len(itens_filtrados))) - removidos,
        0,
    )
    payload["atualizado_em"] = utc_now()

    with _sem_vinculo_match_bling_lock:
        _sem_vinculo_match_bling_cache[tenant_id] = {
            "ts_monotonic": time.monotonic(),
            "payload": payload,
        }

    _write_shared_snapshot("sem_vinculo", tenant_id, payload)


def _executar_reconciliacao_geral_em_background(limit: Optional[int]) -> None:
    try:
        resultado = BlingSyncService.reconcile_all_products(limit=limit)
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": True,
                **resultado,
            }
    except Exception as error:
        logger.exception("❌ Erro na reconciliação geral em background")
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": False,
                "erro": str(error),
            }
    finally:
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["running"] = False
            _reconciliacao_geral_estado["finished_at"] = utc_now()


def _chave_codigo_produto(valor: Optional[str]) -> str:
    return _normalizar_codigo_match(valor)


def _tipo_produto_local(produto) -> str:
    return _texto_limpo(getattr(produto, "tipo_produto", None)).upper() or "SIMPLES"


def _produto_eh_pai(produto) -> bool:
    return _tipo_produto_local(produto) == "PAI"


def _produto_sincroniza_estoque(produto) -> bool:
    return not _produto_eh_pai(produto)


def _chaves_match_produto_local(produto) -> set[str]:
    return {
        chave
        for chave in [
            _chave_codigo_produto(getattr(produto, "codigo", None)),
            _chave_codigo_produto(getattr(produto, "codigo_barras", None)),
            _chave_codigo_produto(getattr(produto, "gtin_ean", None)),
            _chave_codigo_produto(getattr(produto, "gtin_ean_tributario", None)),
        ]
        if chave
    }


def _indexar_produtos_locais_por_codigo(produtos: list) -> dict[str, set[int]]:
    codigos_para_produto: dict[str, set[int]] = {}
    for produto in produtos:
        for chave in _chaves_match_produto_local(produto):
            codigos_para_produto.setdefault(chave, set()).add(produto.id)
    return codigos_para_produto


def _extrair_codigos_bling_item(item: dict) -> set[str]:
    return {
        chave
        for chave in [
            _chave_codigo_produto(item.get("codigo")),
            _chave_codigo_produto(item.get("sku")),
            _chave_codigo_produto(item.get("codigoBarras")),
            _chave_codigo_produto(item.get("gtin")),
        ]
        if chave
    }


def _listar_todos_produtos_bling(bling: BlingAPI, limite: int = 100, max_paginas: int = 100) -> tuple[list[dict], bool]:
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
            # Falha após retries: retorna parcial para não derrubar a tela.
            logger.warning("⚠️ Coleta parcial no Bling (página %s): %s", pagina, ultima_falha)
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
        pode_reusar_no_force_refresh = idade_compartilhada < _CATALOGO_FORCE_REFRESH_REUSE_SECONDS

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
        bling_itens, coleta_completa = _listar_todos_produtos_bling(bling=bling, limite=100, max_paginas=100)
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
                "cache_idade_segundos": _shared_snapshot_age_seconds(cache_compartilhado),
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
    produtos_locais = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
    ).all()

    produtos_por_id = {produto.id: produto for produto in produtos_locais}
    codigos_para_produto = _indexar_produtos_locais_por_codigo(produtos_locais)

    syncs = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.tenant_id == tenant_id,
        ProdutoBlingSync.bling_produto_id.isnot(None),
        ProdutoBlingSync.bling_produto_id != "",
    ).all()
    sync_por_produto = {sync.produto_id: sync for sync in syncs}

    total_bling = len(bling_itens)
    ids_locais_com_match: set[int] = set()
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
        ids_locais_com_match.update(candidatos)

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


def _get_resumo_cobertura_bling(db: Session, tenant_id: int, force_refresh: bool = False) -> dict:
    agora = time.monotonic()
    cache_atual = None
    cache_compartilhado = _read_shared_snapshot("cobertura", tenant_id)

    with _cobertura_bling_lock:
        cache_atual = _cobertura_bling_cache.get(tenant_id)

    if not force_refresh and cache_atual:
        return {
            **cache_atual.get("payload", {}),
            "cache_idade_segundos": int(max(agora - cache_atual.get("ts_monotonic", 0), 0)),
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
        catalogo = _get_catalogo_bling_snapshot(tenant_id=tenant_id, force_refresh=force_refresh)
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
    produtos_locais = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
    ).all()

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
        faltantes.append({
            "id": bling_id,
            "descricao": item.get("nome") or item.get("descricao") or "Sem descrição",
            "codigo": item.get("codigo") or item.get("sku") or "",
            "sku": sku,
            "codigo_barras": codigo_barras,
            "estoque": _coerce_float(item.get("estoque") or item.get("saldoFisicoTotal") or 0),
            "motivo": _motivo_faltante_bling(item),
            "acao_sugerida": _acao_faltante_bling(item),
            "pronto_para_autocorrecao": bool(sku or codigo_barras),
        })

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
            "cache_idade_segundos": int(max(agora - cache_atual.get("ts_monotonic", 0), 0)),
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
        catalogo = _get_catalogo_bling_snapshot(tenant_id=tenant_id, force_refresh=force_refresh)
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


def _origem_match_produto_bling(produto, item: dict) -> str:
    codigo_local = _chave_codigo_produto(getattr(produto, "codigo", None))
    barcode_local = (
        _chave_codigo_produto(getattr(produto, "codigo_barras", None))
        or _chave_codigo_produto(getattr(produto, "gtin_ean", None))
        or _chave_codigo_produto(getattr(produto, "gtin_ean_tributario", None))
    )
    chaves_sku_bling = {
        chave
        for chave in [
            _chave_codigo_produto(item.get("sku")),
            _chave_codigo_produto(item.get("codigo")),
        ]
        if chave
    }
    chaves_barcode_bling = {
        chave
        for chave in [
            _chave_codigo_produto(item.get("codigoBarras")),
            _chave_codigo_produto(item.get("gtin")),
        ]
        if chave
    }

    if codigo_local and codigo_local in chaves_sku_bling:
        return "sku"
    if barcode_local and (barcode_local in chaves_barcode_bling or barcode_local in chaves_sku_bling):
        return "codigo_barras"
    return "codigo"


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
                "bling_nome": item.get("nome") or item.get("descricao") or "Sem descricao",
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
            "bling_codigo_barras": detalhes_match_por_id[produto.id]["bling_codigo_barras"],
            "match_origem": detalhes_match_por_id[produto.id]["match_origem"],
            "sincroniza_estoque": _produto_sincroniza_estoque(produto),
            "motivo": (
                (
                    "Encontramos esse item no Sistema Pet como produto PAI. O vinculo pode existir para catalogo, "
                    "mas o estoque fica nas variacoes e nao sera sincronizado por esse cadastro."
                )
                if _produto_eh_pai(produto)
                else (
                    "Encontramos esse item no Bling por SKU, mas o vinculo ainda nao foi criado."
                    if detalhes_match_por_id[produto.id]["match_origem"] == "sku"
                    else "Encontramos esse item no Bling pelo codigo de barras, mas o vinculo ainda nao foi criado."
                )
            ),
            "acao_sugerida": "Vincular sem sync de estoque" if _produto_eh_pai(produto) else "Vincular agora",
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
            "cache_idade_segundos": int(max(agora - cache_atual.get("ts_monotonic", 0), 0)),
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
        catalogo = _get_catalogo_bling_snapshot(tenant_id=tenant_id, force_refresh=force_refresh)
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
            payload["cache_idade_segundos"] = int(max(agora - cache_atual.get("ts_monotonic", 0), 0))
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

# ============================================================================
# SCHEMAS
# ============================================================================

class ConfigSyncRequest(BaseModel):
    """Configurar sincronização de um produto"""
    produto_id: int
    bling_produto_id: Optional[str] = None
    sincronizar: bool = True
    estoque_compartilhado: bool = True

class SyncStatusResponse(BaseModel):
    produto_id: int
    produto_nome: str
    sku: str
    estoque_sistema: float
    estoque_bling: Optional[float]
    divergencia: Optional[float]
    sincronizado: bool
    bling_produto_id: Optional[str]
    ultima_sincronizacao: Optional[datetime]
    status: str
    ultima_tentativa_sync: Optional[datetime] = None
    proxima_tentativa_sync: Optional[datetime] = None
    ultima_conferencia_bling: Optional[datetime] = None
    ultima_sincronizacao_sucesso: Optional[datetime] = None
    ultimo_estoque_bling: Optional[float] = None
    tentativas_sync: int = 0
    ultimo_erro: Optional[str] = None
    queue_id: Optional[int] = None
    queue_status: Optional[str] = None


class VincularProdutoRequest(BaseModel):
    produto_id: int
    bling_id: str


class CriarProdutoBlingFaltanteRequest(BaseModel):
    bling_id: str


class ReconciliarBatchRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    minutes: int = Field(default=30, ge=5, le=1440)

# ============================================================================
# CONFIGURAÇÃO DE SINCRONIZAÇÃO
# ============================================================================

@router.post("/config")
def configurar_sincronizacao(
    config: ConfigSyncRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configurar sincronização de produto com Bling
    
    - bling_produto_id: ID do produto no Bling (ou None para buscar automaticamente)
    - sincronizar: Se TRUE, sincroniza estoque automaticamente
    - estoque_compartilhado: Se TRUE, estoque é único (loja + online)
    """
    logger.info(f"⚙️ Configurando sync - Produto {config.produto_id}")
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == config.produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)
    
    # Buscar ou criar configuração
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == config.produto_id,
        ProdutoBlingSync.tenant_id == tenant_id,
    ).first()
    
    if not sync:
        sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=config.produto_id)
        db.add(sync)
    
    # Atualizar configuração
    sync.bling_produto_id = config.bling_produto_id
    sync.sincronizar = config.sincronizar
    sync.estoque_compartilhado = config.estoque_compartilhado
    sync.status = 'ativo' if config.sincronizar else 'pausado'
    sync.updated_at = utc_now()
    
    # Se não tem bling_produto_id, tentar buscar automaticamente
    if not sync.bling_produto_id and config.sincronizar:
        try:
            # Buscar no Bling por SKU ou código de barras
            bling = BlingAPI()
            resultado = bling.listar_produtos(
                codigo=produto.codigo_barras,
                sku=produto.codigo
            )
            
            produtos_bling = resultado.get('data', [])
            if produtos_bling and len(produtos_bling) > 0:
                sync.bling_produto_id = str(produtos_bling[0].get('id'))
                logger.info(f"✅ Produto vinculado automaticamente: Bling ID {sync.bling_produto_id}")
            else:
                sync.status = 'erro'
                sync.erro_mensagem = "Produto não encontrado no Bling"
                logger.warning("⚠️ Produto não encontrado no Bling")
        except Exception as e:
            logger.error(f"❌ Erro ao buscar produto no Bling: {e}")
            sync.status = 'erro'
            sync.erro_mensagem = str(e)
    
    db.commit()
    _invalidate_bling_snapshots(tenant_id)
    db.refresh(sync)
    
    return {
        "message": "Sincronização configurada com sucesso",
        "produto_id": sync.produto_id,
        "bling_produto_id": sync.bling_produto_id,
        "sincronizar": sync.sincronizar,
        "status": sync.status
    }


@router.post("/vincular")
def vincular_produto_bling(
    body: VincularProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Vincula manualmente um produto local a um produto do Bling."""
    _current_user, tenant_id = user_and_tenant

    produto = db.query(Produto).filter(
        Produto.id == body.produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == body.produto_id,
        ProdutoBlingSync.tenant_id == tenant_id,
    ).first()

    if not sync:
        sync = ProdutoBlingSync(
            tenant_id=produto.tenant_id,
            produto_id=produto.id,
        )
        db.add(sync)

    _upsert_sync_vinculo(db, tenant_id, produto, str(body.bling_id))

    db.commit()
    _invalidate_bling_snapshots(tenant_id)
    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto vinculado com sucesso"
        ),
        "produto_id": produto.id,
        "bling_produto_id": str(body.bling_id),
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }


@router.post("/vincular-automatico/{produto_id}")
def vincular_produto_bling_automatico(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Tenta vincular automaticamente um produto local ao Bling pelo código/SKU."""
    _current_user, tenant_id = user_and_tenant

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    bling = BlingAPI()

    codigo_busca = (produto.codigo or "").strip()
    nome_busca = (produto.nome or "").strip()
    codigos_extras = [
        (produto.codigo_barras or "").strip(),
        (produto.gtin_ean or "").strip(),
        (produto.gtin_ean_tributario or "").strip(),
    ]

    item_escolhido = _buscar_item_bling_para_vinculo(
        bling,
        codigo_busca,
        nome_busca,
        codigos_extras=codigos_extras,
    )

    if not item_escolhido:
        raise HTTPException(status_code=404, detail="Produto não encontrado no Bling para vínculo automático")

    bling_id = str(item_escolhido.get("id") or "").strip()
    if not bling_id:
        raise HTTPException(status_code=400, detail="Resposta do Bling sem ID de produto")

    _upsert_sync_vinculo(db, tenant_id, produto, bling_id)

    db.commit()
    _invalidate_bling_snapshots(tenant_id)

    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto vinculado automaticamente com sucesso"
        ),
        "produto_id": produto.id,
        "bling_produto_id": bling_id,
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }


@router.get("/produtos-bling")
def listar_produtos_bling(
    busca: Optional[str] = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca produtos diretamente no Bling para facilitar vínculo manual."""
    try:
        termo = _normalizar_termo_busca(busca)
        bling = BlingAPI()
        itens = _buscar_produtos_bling_por_termo(bling, termo, pagina, limite)

        # Fallback final: para termo vazio ou quando filtros específicos retornam vazio,
        # faz uma listagem padrão da página para não bloquear a tela.
        if not itens and not termo:
            itens = _extrair_lista_produtos_bling(bling.listar_produtos(pagina=pagina, limite=limite))

        produtos_bling = []
        for item in itens:
            produtos_bling.append({
                "id": str(item.get("id")),
                "descricao": item.get("nome") or item.get("descricao") or "Sem descrição",
                "codigo": item.get("codigo") or item.get("sku"),
                "estoque": _coerce_float(item.get("estoque") or item.get("saldoFisicoTotal") or 0),
            })
        return produtos_bling
    except Exception as e:
        mensagem = str(e)
        if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
            raise HTTPException(
                status_code=429,
                detail="Bling com limite temporário de consultas. Aguarde alguns segundos e tente novamente.",
            )
        raise HTTPException(status_code=500, detail=f"Erro ao consultar produtos no Bling: {mensagem}")


@router.get("/health")
def health_sincronizacao(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Resumo operacional da integração com o Bling."""
    _current_user, tenant_id = user_and_tenant
    return BlingSyncService.get_health_snapshot(db, tenant_id=tenant_id)


@router.get("/produtos-sem-vinculo")
def listar_produtos_sem_vinculo(
    busca: Optional[str] = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    force_refresh: bool = Query(default=False),
    apenas_com_match_bling: bool = Query(default=True),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Lista rápida de produtos sem vínculo, priorizando base Bling (com match no Bling)."""
    _current_user, tenant_id = user_and_tenant
    erro_coleta_bling = None
    fallback_local = False

    subq_vinculados = (
        db.query(ProdutoBlingSync.produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != "",
        )
        .subquery()
    )

    query = (
        db.query(
            Produto.id,
            Produto.nome,
            Produto.codigo,
            Produto.estoque_atual,
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto != "PAI",
            Produto.codigo.isnot(None),
            Produto.codigo != "",
        )
        .filter(Produto.id.notin_(subq_vinculados))
    )

    termo = (busca or "").strip().lower()

    if apenas_com_match_bling:
        try:
            snapshot = _get_snapshot_sem_vinculo_com_match_bling(
                db,
                tenant_id=tenant_id,
                force_refresh=force_refresh,
            )
            itens_base = snapshot.get("items", [])

            if termo:
                itens_base = [
                    item
                    for item in itens_base
                    if termo in (item.get("nome") or "").lower() or termo in (item.get("codigo") or "").lower()
                ]

            paginados = itens_base[offset: offset + limit]

            return {
                "items": paginados,
                "total": len(itens_base),
                "limit": limit,
                "offset": offset,
                "apenas_com_match_bling": True,
                "snapshot_disponivel": snapshot.get("snapshot_disponivel", True),
                "precisa_atualizar": snapshot.get("precisa_atualizar", False),
                "total_sem_vinculo_universo_local": snapshot.get("total_sem_vinculo_universo_local", 0),
                "total_bling": snapshot.get("total_bling", 0),
                "coleta_bling_completa": snapshot.get("coleta_bling_completa", True),
                "cache_utilizado_por_falha": snapshot.get("cache_utilizado_por_falha", False),
                "cache_idade_segundos": snapshot.get("cache_idade_segundos", 0),
                "atualizado_em": snapshot.get("atualizado_em"),
            }
        except Exception as e:
            fallback_local = True
            erro_coleta_bling = str(e)
            logger.warning(f"⚠️ Falha ao montar snapshot de produtos sem vínculo no Bling: {e}. Aplicando fallback local.")

    if termo:
        like = f"%{termo}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(like),
                Produto.codigo.ilike(like),
            )
        )

    total = query.count()
    itens = query.order_by(Produto.id.asc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": item.id,
                "nome": item.nome,
                "codigo": item.codigo,
                "estoque_atual": float(item.estoque_atual or 0),
            }
            for item in itens
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "apenas_com_match_bling": False,
        "fallback_local_por_erro_bling": fallback_local,
        "erro_coleta_bling": erro_coleta_bling,
        "snapshot_disponivel": False,
        "precisa_atualizar": True,
    }


@router.get("/resumo-cobertura")
def resumo_cobertura_bling(
    force_refresh: bool = Query(default=False),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Resumo de cobertura Bling -> Sistema Pet.

    Regra de negócio: o universo principal é o Bling (online/marketplace).
    """
    _current_user, tenant_id = user_and_tenant
    try:
        normalizados = BlingSyncService.normalize_sync_states_from_latest_queue(db, tenant_id=tenant_id)
        if (normalizados.get("repaired_active") or 0) > 0 or (normalizados.get("repaired_error") or 0) > 0:
            db.commit()
        return _get_resumo_cobertura_bling(db, tenant_id=tenant_id, force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo de cobertura Bling: {e}")
        # Não quebrar a tela: retorna payload seguro quando falhar sem cache.
        return {
            "total_bling": 0,
            "bling_com_match_no_sistema": 0,
            "bling_sem_match_no_sistema": 0,
            "bling_sync_ok": 0,
            "bling_com_problema": 0,
            "sync_problemas_abertos": 0,
            "total_sistema": db.query(Produto).filter(Produto.tenant_id == tenant_id, Produto.tipo_produto != "PAI").count(),
            "somente_sistema": db.query(Produto).filter(Produto.tenant_id == tenant_id, Produto.tipo_produto != "PAI").count(),
            "coleta_bling_completa": False,
            "erro_coleta_bling": "Falha temporaria ao consultar Bling",
            "atualizado_em": utc_now(),
            "snapshot_disponivel": False,
            "precisa_atualizar": True,
        }


@router.get("/faltantes-bling")
def listar_faltantes_bling(
    force_refresh: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Retorna snapshot dos produtos existentes no Bling que não possuem match no Sistema Pet.

    - Sem force_refresh: usa cache para responder rápido.
    - Com force_refresh: recalcula snapshot sob demanda.
    """
    _current_user, tenant_id = user_and_tenant

    try:
        snapshot = _get_snapshot_faltantes_bling(db, tenant_id=tenant_id, force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"❌ Erro ao gerar snapshot de faltantes Bling: {e}")
        return {
            "items": [],
            "total": 0,
            "total_bling": 0,
            "snapshot_disponivel": False,
            "coleta_bling_completa": False,
            "precisa_atualizar": True,
            "erro_coleta_bling": "Falha temporária ao consultar o Bling",
            "atualizado_em": None,
            "limit": limit,
            "offset": offset,
        }

    itens = snapshot.get("items", [])
    paginados = itens[offset: offset + limit]

    return {
        "items": paginados,
        "total": snapshot.get("total", len(itens)),
        "total_bling": snapshot.get("total_bling", 0),
        "snapshot_disponivel": snapshot.get("snapshot_disponivel", True),
        "coleta_bling_completa": snapshot.get("coleta_bling_completa", True),
        "cache_utilizado_por_falha": snapshot.get("cache_utilizado_por_falha", False),
        "cache_idade_segundos": snapshot.get("cache_idade_segundos", 0),
        "atualizado_em": snapshot.get("atualizado_em"),
        "limit": limit,
        "offset": offset,
    }


@router.get("/dashboard")
def dashboard_pendencias_bling(
    force_refresh: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Retorna os blocos principais da central do Bling em uma única resposta.

    Objetivo: evitar múltiplas requisições pesadas concorrendo entre si
    quando a tela abre ou quando o usuário pede atualização completa.
    """
    return {
        "resumo": resumo_cobertura_bling(
            force_refresh=force_refresh,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
        "faltantes": listar_faltantes_bling(
            force_refresh=force_refresh,
            limit=limit,
            offset=offset,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
        "vinculos": listar_produtos_sem_vinculo(
            busca=None,
            limit=limit,
            offset=offset,
            force_refresh=force_refresh,
            apenas_com_match_bling=True,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
    }


@router.post("/faltantes-bling/criar")
def criar_produto_local_para_faltante_bling(
    body: CriarProdutoBlingFaltanteRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant

    bling_id = _texto_limpo(body.bling_id)
    if not bling_id:
        raise HTTPException(status_code=400, detail="bling_id e obrigatorio")

    try:
        item_bling = BlingAPI().consultar_produto(bling_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao consultar produto no Bling: {e}") from e

    if isinstance(item_bling, dict) and isinstance(item_bling.get("produto"), dict):
        item_bling = item_bling.get("produto") or {}

    if not isinstance(item_bling, dict) or not item_bling:
        raise HTTPException(status_code=404, detail="Produto do Bling nao encontrado")

    sku = _sku_bling(item_bling)
    codigo_barras = _barcode_bling(item_bling)

    produto = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku) if sku else None
    correspondencia_usada = "sku" if produto else None

    if not produto and codigo_barras:
        produto = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=codigo_barras)
        correspondencia_usada = "codigo_barras" if produto else None

    if not produto:
        produto = criar_produto_automatico_do_bling_por_item(
            db=db,
            tenant_id=tenant_id,
            item_bling=item_bling,
            sku_preferencial=sku or codigo_barras or bling_id,
        )
        correspondencia_usada = "autocadastro"

    if not produto:
        raise HTTPException(status_code=400, detail="Nao foi possivel criar o produto local a partir do Bling")

    conflito_bling = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id == bling_id,
            ProdutoBlingSync.produto_id != produto.id,
        )
        .first()
    )
    if conflito_bling:
        raise HTTPException(
            status_code=409,
            detail=f"Esse item do Bling ja esta vinculado ao produto local {conflito_bling.produto_id}.",
        )

    sync_existente = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.produto_id == produto.id,
        )
        .first()
    )
    if sync_existente and _texto_limpo(sync_existente.bling_produto_id) not in {"", bling_id}:
        raise HTTPException(
            status_code=409,
            detail=(
                f"O produto local {produto.codigo} ja esta vinculado a outro item do Bling "
                f"({sync_existente.bling_produto_id})."
            ),
        )

    _upsert_sync_vinculo(db, tenant_id, produto, bling_id)
    db.commit()
    _invalidate_bling_snapshots(tenant_id)

    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto preparado para sincronizacao com sucesso"
        ),
        "produto_id": produto.id,
        "produto_codigo": produto.codigo,
        "produto_nome": produto.nome,
        "bling_produto_id": bling_id,
        "acao": "vinculado_existente" if correspondencia_usada in {"sku", "codigo_barras"} else "criado_e_vinculado",
        "correspondencia_usada": correspondencia_usada,
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }

# ============================================================================
# ENVIAR ESTOQUE PARA BLING
# ============================================================================

@router.post("/enviar/{produto_id}")
def enviar_estoque_para_bling(
    produto_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Envia estoque atual do produto para o Bling
    Usado após vendas na loja física
    """
    logger.info(f"📤 Enviando estoque para Bling - Produto {produto_id} (force={force})")

    resultado = BlingSyncService.force_sync_now(
        produto_id=produto_id,
        motivo="forcar_manual" if force else "envio_manual",
    )
    if not resultado.get("ok"):
        if resultado.get("auth_invalid"):
            raise HTTPException(
                status_code=409,
                detail=resultado.get("detail") or "Reconecte o Bling antes de tentar novo envio.",
            )
        if resultado.get("rate_limited"):
            return {
                "message": "Bling limitou as requisicoes agora. O item foi reagendado automaticamente.",
                **resultado,
            }
        raise HTTPException(status_code=400, detail=resultado.get("detail") or resultado.get("erro") or "Falha ao sincronizar")

    return {
        "message": "Estoque enviado para Bling com sucesso",
        "produto_id": produto_id,
        "bling_produto_id": resultado.get("bling_produto_id"),
        "estoque_enviado": resultado.get("estoque_enviado"),
        "queue_id": resultado.get("queue_id"),
    }


@router.post("/forcar/{produto_id}")
def forcar_sincronizacao_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Força o envio imediato do estoque de um único produto."""
    resultado = BlingSyncService.force_sync_now(produto_id=produto_id, motivo="botao_forcar_sync")
    if not resultado.get("ok"):
        if resultado.get("auth_invalid"):
            raise HTTPException(
                status_code=409,
                detail=resultado.get("detail") or "Reconecte o Bling antes de tentar novo envio.",
            )
        if resultado.get("rate_limited"):
            return {
                "message": "Bling limitou as requisicoes agora. O item foi reagendado automaticamente.",
                **resultado,
            }
        raise HTTPException(status_code=400, detail=resultado.get("detail") or resultado.get("erro") or "Falha ao forçar sincronização")
    return {
        "message": "Sincronização forçada concluída",
        **resultado,
    }

# ============================================================================
# STATUS DE SINCRONIZAÇÃO
# ============================================================================

@router.get("/status", response_model=List[SyncStatusResponse])
def status_sincronizacao(
    apenas_divergencias: bool = False,
    busca: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista status de sincronização de todos os produtos
    
    - apenas_divergencias: Se TRUE, mostra apenas produtos com divergência de estoque
    """
    logger.info("📊 Consultando status de sincronização")
    _current_user, tenant_id = user_and_tenant
    
    # Buscar produtos com sincronização configurada
    query = db.query(Produto, ProdutoBlingSync).join(
        ProdutoBlingSync,
        Produto.id == ProdutoBlingSync.produto_id
    ).filter(
        Produto.tenant_id == tenant_id,
        ProdutoBlingSync.tenant_id == tenant_id,
        ProdutoBlingSync.sincronizar == True
    )

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                ProdutoBlingSync.bling_produto_id.ilike(termo),
            )
        )
    
    resultados = []
    
    for produto, sync in query.all():
        fila = db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.produto_id == produto.id,
            ProdutoBlingSyncQueue.tenant_id == tenant_id,
        ).order_by(ProdutoBlingSyncQueue.updated_at.desc()).first()

        # Usar dados cacheados para manter endpoint rápido e evitar rate-limit/timeout.
        estoque_bling = sync.ultimo_estoque_bling
        divergencia = sync.ultima_divergencia
        
        # Filtrar divergências se solicitado
        if apenas_divergencias and divergencia is not None and abs(divergencia) < 0.01:
            continue
        
        resultados.append(SyncStatusResponse(
            produto_id=produto.id,
            produto_nome=produto.nome,
            sku=produto.codigo,
            estoque_sistema=produto.estoque_atual or 0,
            estoque_bling=estoque_bling,
            divergencia=divergencia,
            sincronizado=sync.sincronizar,
            bling_produto_id=sync.bling_produto_id,
            ultima_sincronizacao=sync.ultima_sincronizacao,
            status=sync.status,
            ultima_tentativa_sync=sync.ultima_tentativa_sync,
            proxima_tentativa_sync=sync.proxima_tentativa_sync,
            ultima_conferencia_bling=sync.ultima_conferencia_bling,
            ultima_sincronizacao_sucesso=sync.ultima_sincronizacao_sucesso,
            ultimo_estoque_bling=sync.ultimo_estoque_bling,
            tentativas_sync=sync.tentativas_sync or 0,
            ultimo_erro=sync.erro_mensagem or (fila.ultimo_erro if fila else None),
            queue_id=fila.id if fila else None,
            queue_status=fila.status if fila else None,
        ))
    
    logger.info(f"✅ {len(resultados)} produtos em sincronização")
    return resultados


@router.get("/status-problemas", response_model=List[SyncStatusResponse])
def status_sincronizacao_problemas(
    busca: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna apenas itens com pendencias de sincronizacao, sem N+1 de fila."""
    logger.info("Consultando status de sincronizacao com filtro de problemas")
    _current_user, tenant_id = user_and_tenant

    normalizados = BlingSyncService.normalize_sync_states_from_latest_queue(db, tenant_id=tenant_id)
    if (normalizados.get("repaired_active") or 0) > 0 or (normalizados.get("repaired_error") or 0) > 0:
        db.commit()

    query, fila_atual = _build_sync_problem_query(
        db,
        tenant_id=tenant_id,
        busca=busca,
    )

    resultados = []
    for produto, sync, fila in query.order_by(ProdutoBlingSync.updated_at.desc(), Produto.id.asc()).offset(offset).limit(limit).all():
        resultados.append(SyncStatusResponse(
            produto_id=produto.id,
            produto_nome=produto.nome,
            sku=produto.codigo,
            estoque_sistema=produto.estoque_atual or 0,
            estoque_bling=sync.ultimo_estoque_bling,
            divergencia=sync.ultima_divergencia,
            sincronizado=sync.sincronizar,
            bling_produto_id=sync.bling_produto_id,
            ultima_sincronizacao=sync.ultima_sincronizacao,
            status=sync.status,
            ultima_tentativa_sync=sync.ultima_tentativa_sync,
            proxima_tentativa_sync=sync.proxima_tentativa_sync,
            ultima_conferencia_bling=sync.ultima_conferencia_bling,
            ultima_sincronizacao_sucesso=sync.ultima_sincronizacao_sucesso,
            ultimo_estoque_bling=sync.ultimo_estoque_bling,
            tentativas_sync=sync.tentativas_sync or 0,
            ultimo_erro=sync.erro_mensagem or (fila.ultimo_erro if fila else None),
            queue_id=fila.id if fila else None,
            queue_status=fila.status if fila else None,
        ))

    logger.info("Status de problemas retornado com %s item(ns)", len(resultados))
    return resultados


@router.post("/reprocessar-falhas")
def reprocessar_falhas(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Reagenda imediatamente os itens com erro para nova tentativa."""
    limite = body.limit if body else 100
    _current_user, tenant_id = user_and_tenant
    resultado = BlingSyncService.reprocess_failed_syncs(limit=limite, tenant_id=tenant_id)
    if resultado.get("auth_invalid"):
        raise HTTPException(
            status_code=409,
            detail=resultado.get("detail") or "Reconecte o Bling antes de reprocessar as falhas.",
        )
    return resultado


@router.post("/reconciliar-recentes")
def reconciliar_recentes(
    body: ReconciliarBatchRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Confere novamente produtos alterados recentemente ou com erro."""
    return BlingSyncService.reconcile_recent_products(minutes=body.minutes, limit=body.limit)


@router.post("/reconciliar-geral")
def reconciliar_geral(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Inicia auditoria ampla em segundo plano para evitar travamento por timeout."""
    limite = body.limit if body else None

    with _reconciliacao_geral_lock:
        if _reconciliacao_geral_estado["running"]:
            return {
                "status": "running",
                "message": "Auditoria geral já está em execução",
                "started_at": _reconciliacao_geral_estado["started_at"],
            }

        _reconciliacao_geral_estado["running"] = True
        _reconciliacao_geral_estado["started_at"] = utc_now()
        _reconciliacao_geral_estado["finished_at"] = None
        _reconciliacao_geral_estado["result"] = None

    worker = threading.Thread(
        target=_executar_reconciliacao_geral_em_background,
        args=(limite,),
        daemon=True,
    )
    worker.start()

    return {
        "status": "started",
        "message": "Auditoria geral iniciada em segundo plano",
        "limit": limite,
        "started_at": _reconciliacao_geral_estado["started_at"],
    }


@router.get("/reconciliar-geral/status")
def status_reconciliar_geral(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna status da auditoria geral em background."""
    with _reconciliacao_geral_lock:
        return {
            "running": _reconciliacao_geral_estado["running"],
            "started_at": _reconciliacao_geral_estado["started_at"],
            "finished_at": _reconciliacao_geral_estado["finished_at"],
            "result": _reconciliacao_geral_estado["result"],
        }

# ============================================================================
# RECONCILIAR DIVERGÊNCIAS
# ============================================================================

@router.post("/reconciliar/{produto_id}")
def reconciliar_estoque(
    produto_id: int,
    origem: str = Query(default="sistema", description="Origem: sistema, bling ou manual"),
    valor_manual: Optional[float] = Query(default=None, description="Valor manual para ajuste"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Reconciliar divergência de estoque
    
    Opções:
    - origem=sistema: Usa valor do sistema → envia para Bling
    - origem=bling: Busca valor do Bling → atualiza sistema
    - origem=manual: Usa valor_manual → atualiza ambos
    """
    logger.info(f"🔄 Reconciliando estoque - Produto {produto_id}, Origem: {origem}")

    current_user, _tenant = user_and_tenant

    if origem == "sistema":
        resultado = BlingSyncService.reconcile_product(produto_id=produto_id, force_sync=True)
        if not resultado.get("ok"):
            raise HTTPException(status_code=400, detail=resultado.get("detail") or "Erro ao reconciliar")
        return {
            "message": "Reconciliação executada com sucesso",
            **resultado,
        }
    
    # Buscar produto e sync
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)
    
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto_id
    ).first()
    
    if not sync or not sync.bling_produto_id:
        raise HTTPException(status_code=400, detail="Produto não configurado para sincronização")
    
    try:
        bling = BlingAPI()
        estoque_anterior = produto.estoque_atual or 0
        estoque_novo = None
        
        if origem == "sistema":
            # Usa valor do sistema
            estoque_novo = estoque_anterior
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Sistema → Bling: {estoque_novo}")
            
        elif origem == "bling":
            # Busca valor do Bling (saldo físico real)
            saldo = bling.consultar_saldo_estoque(sync.bling_produto_id)
            estoque_novo = _coerce_float(saldo.get('saldoFisicoTotal', 0))
            produto.estoque_atual = estoque_novo
            logger.info(f"✅ Bling → Sistema: {estoque_novo}")
            
        elif origem == "manual":
            if valor_manual is None:
                raise HTTPException(status_code=400, detail="valor_manual é obrigatório para origem=manual")
            estoque_novo = valor_manual
            produto.estoque_atual = estoque_novo
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Manual → Ambos: {estoque_novo}")
            
        else:
            raise HTTPException(status_code=400, detail="origem deve ser: sistema, bling ou manual")
        
        # Registrar movimentação de ajuste
        if origem in ["bling", "manual"] and estoque_novo != estoque_anterior:
            diferenca = estoque_novo - estoque_anterior
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                tipo='entrada' if diferenca > 0 else 'saida',
                motivo='ajuste_reconciliacao',
                quantidade=abs(diferenca),
                quantidade_anterior=estoque_anterior,
                quantidade_nova=estoque_novo,
                observacao=f"Reconciliação Bling - Origem: {origem}",
                user_id=current_user.id
            )
            db.add(movimentacao)
        
        # Atualizar sync
        sync.ultima_sincronizacao = utc_now()
        sync.status = 'ativo'
        sync.erro_mensagem = None
        
        db.commit()
        
        return {
            "message": "Estoque reconciliado com sucesso",
            "produto_id": produto_id,
            "estoque_anterior": estoque_anterior,
            "estoque_novo": estoque_novo,
            "diferenca": estoque_novo - estoque_anterior,
            "origem": origem
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao reconciliar: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar: {str(e)}")

# ============================================================================
# WEBHOOK BLING
# ============================================================================

@router.post("/webhook/bling")
async def webhook_bling(
    request: Request,
    db: Session = Depends(get_session)
):
    """
    Webhook para receber notificações do Bling
    
    Eventos suportados:
    - Venda criada: Baixa estoque no sistema
    - Venda cancelada: Retorna estoque ao sistema
    """
    try:
        body = await request.json()
        logger.info(f"📥 Webhook Bling recebido: {body}")
        
        evento = body.get('topic')
        dados = body.get('data', {})
        
        if evento == 'vendas.created':
            # Venda online criada - baixar estoque
            venda_id = dados.get('id')
            itens = dados.get('itens', [])
            
            for item in itens:
                produto_bling_id = str(item.get('produtoId'))
                quantidade = float(item.get('quantidade', 0))
                
                # Buscar produto no sistema
                sync = db.query(ProdutoBlingSync).filter(
                    ProdutoBlingSync.bling_produto_id == produto_bling_id
                ).first()
                
                if sync and sync.sincronizar:
                    produto = db.query(Produto).filter(
                        Produto.id == sync.produto_id
                    ).first()
                    
                    if produto:
                        estoque_anterior = produto.estoque_atual or 0
                        produto.estoque_atual = max(0, estoque_anterior - quantidade)
                        
                        # Registrar movimentação com status 'reservado' (pendente de NF confirmada)
                        movimentacao = EstoqueMovimentacao(
                            produto_id=produto.id,
                            tipo='saida',
                            motivo='venda_online',
                            quantidade=quantidade,
                            quantidade_anterior=estoque_anterior,
                            quantidade_nova=produto.estoque_atual,
                            documento=f"BLING-{venda_id}",
                            referencia_id=venda_id,
                            referencia_tipo='venda_bling',
                            status='reservado',  # ← NOVO: Estoque reservado até NF ser autorizada
                            observacao="Venda online via Bling - Pendente de NF autorizada",
                            user_id=1  # Sistema
                        )
                        db.add(movimentacao)
                        
                        # Atualizar sync
                        sync.ultima_sincronizacao = utc_now()
                        
                        logger.info(f"✅ Estoque baixado - Produto {produto.id}: {estoque_anterior} → {produto.estoque_atual}")
            
            db.commit()
            return {"status": "success", "message": "Estoque atualizado"}
            
        elif evento == 'vendas.deleted':
            # Venda cancelada - retornar estoque
            # Implementar lógica similar...
            pass
        
        return {"status": "ignored", "message": f"Evento {evento} não processado"}
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}

logger.info("✅ Módulo de sincronização Bling carregado")


# ============================================================================
# VINCULAR TODOS POR SKU
# ============================================================================

@router.post("/vincular-todos")
def vincular_todos_por_sku(
    limite: int = Query(default=20, ge=1, le=200),
    timeout_seconds: int = Query(default=15, ge=5, le=55),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Vincula automaticamente produtos do sistema com o Bling pelo código (SKU).

    Para cada produto faltante no recorte Bling-centric (existe no Bling e ainda sem vínculo local):
    - Busca no Bling pelo campo `codigo`
    - Se encontrar, cria ou atualiza ProdutoBlingSync com o ID do Bling
    - Produtos do tipo PAI são ignorados

    Retorna resumo com vinculados, não encontrados e erros.
    """
    logger.info("🔗 Iniciando vinculação em massa por SKU")
    _current_user, tenant_id = user_and_tenant

    snapshot = _get_snapshot_sem_vinculo_com_match_bling(
        db,
        tenant_id=tenant_id,
        force_refresh=False,
    )

    itens_match = list(snapshot.get("items", []) or [])
    total_sem_vinculo = len(itens_match)
    total_universo_sem_vinculo = int(snapshot.get("total_sem_vinculo_universo_local", total_sem_vinculo) or 0)
    coleta_bling_completa = bool(snapshot.get("coleta_bling_completa", True))
    total_bling = int(snapshot.get("total_bling", 0) or 0)

    itens_lote = itens_match[:limite]
    ids_lote = [
        int(item.get("id"))
        for item in itens_lote
        if item.get("id") is not None
    ]
    produtos_lote = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_(ids_lote),
        )
        .all()
        if ids_lote
        else []
    )
    produtos_por_id = {produto.id: produto for produto in produtos_lote}

    vinculados = []
    nao_encontrados = []
    erros = []
    sincronizados_sucesso = 0
    sincronizados_erro = 0
    interrompido_por_tempo = False
    total_processados = 0
    inicio_execucao = time.monotonic()

    logger.info(
        "Processando lote por snapshot: %s de %s pendencias com match (universo local sem vinculo: %s)",
        len(itens_lote),
        total_sem_vinculo,
        total_universo_sem_vinculo,
    )

    for item in itens_lote:
        if (time.monotonic() - inicio_execucao) >= timeout_seconds:
            interrompido_por_tempo = True
            logger.warning("Vinculo em massa interrompido por limite de tempo (%ss)", timeout_seconds)
            break

        total_processados += 1
        produto_id = int(item.get("id") or 0)
        produto = produtos_por_id.get(produto_id)

        if not produto:
            erros.append({
                "produto_id": produto_id or None,
                "codigo": item.get("codigo"),
                "erro": "Produto local nao encontrado para o item do snapshot.",
            })
            continue

        bling_produto_id = str(item.get("bling_id") or "").strip()
        if not bling_produto_id:
            nao_encontrados.append({
                "produto_id": produto.id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "motivo": "Snapshot sem bling_id para esse item.",
            })
            continue

        try:
            _upsert_sync_vinculo(db, tenant_id, produto, bling_produto_id)
            db.flush()

            if _produto_sincroniza_estoque(produto):
                resultado_sync = BlingSyncService.queue_product_sync(
                    db,
                    produto_id=produto.id,
                    estoque_novo=float(produto.estoque_atual or 0),
                    motivo="vinculo_massa_forcar_sync",
                    origem="manual",
                    force=True,
                )

                sync_ok = bool(resultado_sync.get("ok"))
                if sync_ok:
                    sincronizados_sucesso += 1
                else:
                    sincronizados_erro += 1
            else:
                sync_ok = None
                resultado_sync = {
                    "detail": "Produto PAI vinculado so para catalogo. O estoque segue nas variacoes.",
                }

            vinculados.append({
                "produto_id": produto.id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "bling_produto_id": bling_produto_id,
                "bling_nome": item.get("bling_nome"),
                "match_origem": item.get("match_origem"),
                "tipo_produto": _tipo_produto_local(produto),
                "sync_ok": sync_ok,
                "sync_detail": resultado_sync.get("detail") or resultado_sync.get("erro"),
            })

            logger.info("Vinculado via snapshot: %s -> Bling ID %s", produto.codigo, bling_produto_id)

        except Exception as e:
            logger.error("Erro ao vincular produto %s: %s", produto.codigo, e)
            erros.append({"produto_id": produto.id, "codigo": produto.codigo, "erro": str(e)})

    db.commit()
    _remover_ids_do_snapshot_sem_vinculo_cache(
        tenant_id,
        [item.get("produto_id") for item in vinculados],
    )

    logger.info(
        "Vinculacao concluida: %s vinculados, %s nao encontrados, %s erros",
        len(vinculados),
        len(nao_encontrados),
        len(erros),
    )

    return {
        "limite_lote": limite,
        "timeout_seconds": timeout_seconds,
        "interrompido_por_tempo": interrompido_por_tempo,
        "total_universo_local_sem_vinculo": total_universo_sem_vinculo,
        "total_bling_analisado": total_bling,
        "coleta_bling_completa": coleta_bling_completa,
        "total_sem_vinculo": total_sem_vinculo,
        "total_planejado_no_lote": len(itens_lote),
        "total_processados": total_processados,
        "restantes_para_proximo_lote": max(total_sem_vinculo - len(vinculados), 0),
        "vinculados": len(vinculados),
        "sincronizados_com_sucesso": sincronizados_sucesso,
        "sincronizados_com_erro": sincronizados_erro,
        "nao_encontrados_no_bling": len(nao_encontrados),
        "erros": len(erros),
        "tempo_execucao_ms": int((time.monotonic() - inicio_execucao) * 1000),
        "detalhes_vinculados": vinculados,
        "detalhes_nao_encontrados": nao_encontrados,
        "detalhes_erros": erros,
    }

    # Produtos sem vínculo ou com bling_produto_id vazio
    subq_vinculados = (
        db.query(ProdutoBlingSync.produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != ""
        )
        .subquery()
    )

    consulta_sem_vinculo = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.codigo.isnot(None),
            Produto.codigo != "",
            Produto.tipo_produto != "PAI"
        )
        .filter(Produto.id.notin_(subq_vinculados))
    )

    # Universo local ainda sem vínculo (antes do recorte Bling-centric)
    total_universo_sem_vinculo = consulta_sem_vinculo.count()
    produtos_sem_vinculo_info = consulta_sem_vinculo.with_entities(
        Produto.id,
        Produto.codigo,
        Produto.codigo_barras,
        Produto.gtin_ean,
        Produto.gtin_ean_tributario,
    ).all()

    codigos_para_produto_sem_vinculo: dict[str, set[int]] = {}
    for produto_info in produtos_sem_vinculo_info:
        for chave in [
            _chave_codigo_produto(produto_info.codigo),
            _chave_codigo_produto(produto_info.codigo_barras),
            _chave_codigo_produto(produto_info.gtin_ean),
            _chave_codigo_produto(produto_info.gtin_ean_tributario),
        ]:
            if not chave:
                continue
            codigos_para_produto_sem_vinculo.setdefault(chave, set()).add(produto_info.id)

    bling = BlingAPI()
    bling_itens, coleta_bling_completa = _listar_todos_produtos_bling(bling=bling, limite=100, max_paginas=100)

    ids_sem_vinculo_com_match_bling: set[int] = set()
    for item in bling_itens:
        codigos_bling = _extrair_codigos_bling_item(item)
        if not codigos_bling:
            continue
        for codigo in codigos_bling:
            ids_sem_vinculo_com_match_bling.update(codigos_para_produto_sem_vinculo.get(codigo, set()))

    total_sem_vinculo = len(ids_sem_vinculo_com_match_bling)
    if total_sem_vinculo > 0:
        produtos_sem_vinculo = (
            consulta_sem_vinculo
            .filter(Produto.id.in_(ids_sem_vinculo_com_match_bling))
            .order_by(Produto.id.asc())
            .limit(limite)
            .all()
        )
    else:
        produtos_sem_vinculo = []

    total = len(produtos_sem_vinculo)
    vinculados = []
    nao_encontrados = []
    erros = []
    sincronizados_sucesso = 0
    sincronizados_erro = 0
    interrompido_por_tempo = False
    inicio_execucao = time.monotonic()

    logger.info(
        "📦 Processando lote Bling-centric: %s de %s faltantes (universo local sem vínculo: %s)",
        total,
        total_sem_vinculo,
        total_universo_sem_vinculo,
    )

    for produto in produtos_sem_vinculo:
        if (time.monotonic() - inicio_execucao) >= timeout_seconds:
            interrompido_por_tempo = True
            logger.warning("⏱️ Vínculo em massa interrompido por limite de tempo (%ss)", timeout_seconds)
            break

        try:
            codigo_busca = (produto.codigo or "").strip()
            nome_busca = (produto.nome or "").strip()
            codigos_extras = [
                (produto.codigo_barras or "").strip(),
                (produto.gtin_ean or "").strip(),
                (produto.gtin_ean_tributario or "").strip(),
            ]
            item_escolhido = _buscar_item_bling_com_retry(
                bling,
                codigo_busca,
                nome_busca,
                codigos_extras=codigos_extras,
            )

            if not item_escolhido:
                nao_encontrados.append({"produto_id": produto.id, "codigo": produto.codigo, "nome": produto.nome})
                continue

            bling_produto_id = str(item_escolhido.get("id") or "").strip()
            if not bling_produto_id:
                nao_encontrados.append({"produto_id": produto.id, "codigo": produto.codigo, "nome": produto.nome})
                continue

            _upsert_sync_vinculo(db, tenant_id, produto, bling_produto_id)

            resultado_sync = BlingSyncService.queue_product_sync(
                db,
                produto_id=produto.id,
                estoque_novo=float(produto.estoque_atual or 0),
                motivo="vinculo_massa_forcar_sync",
                origem="manual",
                force=True,
            )

            sync_ok = bool(resultado_sync.get("ok"))
            if sync_ok:
                sincronizados_sucesso += 1
            else:
                sincronizados_erro += 1

            vinculados.append({
                "produto_id": produto.id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "bling_produto_id": bling_produto_id,
                "sync_ok": sync_ok,
                "sync_detail": resultado_sync.get("detail") or resultado_sync.get("erro"),
            })

            logger.info(f"✅ Vinculado: {produto.codigo} → Bling ID {bling_produto_id}")
            time.sleep(0.35)

        except Exception as e:
            logger.error(f"❌ Erro ao vincular produto {produto.codigo}: {e}")
            erros.append({"produto_id": produto.id, "codigo": produto.codigo, "erro": str(e)})

    db.commit()

    logger.info(f"🔗 Vinculação concluída: {len(vinculados)} vinculados, {len(nao_encontrados)} não encontrados, {len(erros)} erros")

    restantes = max(total_sem_vinculo - total, 0)

    return {
        "limite_lote": limite,
        "timeout_seconds": timeout_seconds,
        "interrompido_por_tempo": interrompido_por_tempo,
        "total_universo_local_sem_vinculo": total_universo_sem_vinculo,
        "total_bling_analisado": len(bling_itens),
        "coleta_bling_completa": coleta_bling_completa,
        "total_sem_vinculo": total_sem_vinculo,
        "total_processados": total,
        "restantes_para_proximo_lote": restantes,
        "vinculados": len(vinculados),
        "sincronizados_com_sucesso": sincronizados_sucesso,
        "sincronizados_com_erro": sincronizados_erro,
        "nao_encontrados_no_bling": len(nao_encontrados),
        "erros": len(erros),
        "detalhes_vinculados": vinculados,
        "detalhes_nao_encontrados": nao_encontrados,
        "detalhes_erros": erros
    }
