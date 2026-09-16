"""Consulta local da tabela NCM vigente publicada pela Receita Federal.

A fonte oficial disponibiliza um JSON publico e sem captcha. O download fica em
cache no processo para que a tela fiscal nao dependa de uma chamada externa a
cada pesquisa. A correspondencia textual sugere candidatos; ela nao determina
sozinha a classificacao fiscal da mercadoria.
"""

from __future__ import annotations

import logging
import json
import os
import re
import threading
import time
import unicodedata
from collections.abc import Iterable
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

NCM_OFICIAL_JSON_URL = (
    "https://portalunico.siscomex.gov.br/"
    "classif/api/publico/nomenclatura/download/json"
)
NCM_CACHE_TTL_SECONDS = 24 * 60 * 60
NCM_RETRY_SECONDS = 15 * 60
NCM_CACHE_PATH = Path(
    os.getenv("NCM_OFICIAL_CACHE_PATH")
    or Path(__file__).resolve().parents[2] / "data" / "fiscal" / "ncm_oficial.json"
)

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {
    "carregado_em": 0.0,
    "atualizado_em": None,
    "ato": None,
    "itens": [],
    "baixado_em_epoch": 0.0,
    "ultima_tentativa_em": 0.0,
}

_STOPWORDS = {
    "a",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "o",
    "os",
    "para",
    "por",
    "um",
    "uma",
}


def _normalizar_texto(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


def _digitos(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _tokens(value: Any) -> list[str]:
    return [
        token
        for token in _normalizar_texto(value).split()
        if token not in _STOPWORDS and len(token) >= 3
    ]


def _montar_itens(nomenclaturas: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    contexto: dict[int, str] = {}
    itens: list[dict[str, str]] = []
    for row in nomenclaturas:
        codigo_original = str(row.get("Codigo") or "").strip()
        codigo = _digitos(codigo_original)
        descricao = re.sub(r"^[-\s]+", "", str(row.get("Descricao") or "")).strip()
        if not codigo or not descricao:
            continue

        nivel = len(codigo)
        contexto[nivel] = descricao
        for deeper in [key for key in contexto if key > nivel]:
            contexto.pop(deeper, None)

        if nivel != 8:
            continue

        descricao_hierarquica = " > ".join(
            contexto[key] for key in sorted(contexto) if contexto[key]
        )
        itens.append(
            {
                "ncm": codigo,
                "descricao": descricao,
                "descricao_hierarquica": descricao_hierarquica,
                "texto_busca": _normalizar_texto(descricao_hierarquica),
            }
        )
    return itens


def _baixar_tabela() -> dict[str, Any]:
    response = requests.get(NCM_OFICIAL_JSON_URL, timeout=(3.05, 20))
    response.raise_for_status()
    # O endpoint entrega JSON UTF-8, mas atualmente nao declara o charset no
    # Content-Type. Sem esta definicao o requests pode interpretar acentos como
    # ISO-8859-1 em algumas maquinas.
    response.encoding = "utf-8"
    payload = response.json()
    return {
        "carregado_em": time.monotonic(),
        "baixado_em_epoch": time.time(),
        "atualizado_em": payload.get("Data_Ultima_Atualizacao_NCM"),
        "ato": payload.get("Ato"),
        "itens": _montar_itens(payload.get("Nomenclaturas") or []),
    }


def _carregar_cache_disco() -> dict[str, Any] | None:
    try:
        payload = json.loads(NCM_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload.get("itens"), list) or not payload["itens"]:
        return None
    payload["carregado_em"] = time.monotonic()
    payload["ultima_tentativa_em"] = 0.0
    return payload


def _salvar_cache_disco(payload: dict[str, Any]) -> None:
    try:
        NCM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporario = NCM_CACHE_PATH.with_name(
            f"{NCM_CACHE_PATH.name}.{os.getpid()}.tmp"
        )
        persistido = {
            chave: payload.get(chave)
            for chave in ("baixado_em_epoch", "atualizado_em", "ato", "itens")
        }
        temporario.write_text(
            json.dumps(persistido, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporario.replace(NCM_CACHE_PATH)
    except OSError as exc:
        logger.warning("Falha ao persistir cache da NCM oficial: %s", exc)


def _adquirir_lock_disco() -> Path | None:
    lock_path = NCM_CACHE_PATH.with_suffix(".lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "w", encoding="utf-8") as arquivo:
            arquivo.write(str(os.getpid()))
        return lock_path
    except FileExistsError:
        try:
            if time.time() - lock_path.stat().st_mtime > 60:
                lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    except OSError as exc:
        logger.warning("Falha ao criar lock do cache da NCM: %s", exc)
        return None


def _cache_vigente(agora_epoch: float) -> bool:
    baixado_em = float(_CACHE.get("baixado_em_epoch") or 0)
    return bool(_CACHE["itens"] and agora_epoch - baixado_em < NCM_CACHE_TTL_SECONDS)


def obter_tabela_ncm_oficial() -> dict[str, Any]:
    agora_epoch = time.time()
    if _cache_vigente(agora_epoch):
        return _CACHE

    with _CACHE_LOCK:
        agora_epoch = time.time()
        if not _CACHE["itens"]:
            cache_disco = _carregar_cache_disco()
            if cache_disco:
                _CACHE.update(cache_disco)
        if _cache_vigente(agora_epoch):
            return _CACHE
        ultima_tentativa = float(_CACHE.get("ultima_tentativa_em") or 0)
        if agora_epoch - ultima_tentativa < NCM_RETRY_SECONDS:
            return _CACHE
        _CACHE["ultima_tentativa_em"] = agora_epoch
        lock_path = _adquirir_lock_disco()
        if lock_path is None:
            # Outro worker esta atualizando a mesma copia persistente. Se ja ha
            # dados, sirva a versao anterior; caso contrario, espere brevemente.
            for _ in range(20 if not _CACHE["itens"] else 0):
                time.sleep(0.1)
                cache_disco = _carregar_cache_disco()
                if cache_disco:
                    _CACHE.update(cache_disco)
                    break
            return _CACHE
        try:
            atualizado = _baixar_tabela()
            _CACHE.update(atualizado)
            _salvar_cache_disco(atualizado)
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("Falha ao atualizar tabela NCM oficial: %s", exc)
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
        return _CACHE


def _score_item(consulta: str, item: dict[str, str]) -> int:
    consulta_digitos = _digitos(consulta)
    if len(consulta_digitos) == 8 and consulta_digitos == item["ncm"]:
        return 100

    consulta_tokens = _tokens(consulta)
    if not consulta_tokens:
        return 0
    texto = item["texto_busca"]
    encontrados = sum(1 for token in consulta_tokens if token in texto)
    if not encontrados:
        return 0

    cobertura = encontrados / len(consulta_tokens)
    similaridade = SequenceMatcher(None, _normalizar_texto(consulta), texto).ratio()
    score = 25 + int(cobertura * 55) + int(similaridade * 15)
    if encontrados == len(consulta_tokens):
        score += 5
    return min(92, score)


def pesquisar_ncm_oficial(consulta: str, limite: int = 8) -> dict[str, Any]:
    tabela = obter_tabela_ncm_oficial()
    encontrados: list[dict[str, Any]] = []
    for item in tabela["itens"]:
        score = _score_item(consulta, item)
        if score < 35:
            continue
        encontrados.append({**item, "score": score})

    encontrados.sort(key=lambda item: (item["score"], item["ncm"]), reverse=True)
    return {
        "resultados": encontrados[: max(1, limite)],
        "atualizado_em": tabela.get("atualizado_em"),
        "ato": tabela.get("ato"),
        "disponivel": bool(tabela["itens"]),
    }


def limpar_cache_ncm_oficial() -> None:
    """Disponivel para testes e para uma futura rotina administrativa de refresh."""

    with _CACHE_LOCK:
        _CACHE.update(
            {
                "carregado_em": 0.0,
                "atualizado_em": None,
                "ato": None,
                "itens": [],
                "baixado_em_epoch": 0.0,
                "ultima_tentativa_em": 0.0,
            }
        )
