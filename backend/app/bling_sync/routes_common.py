"""Helpers compartilhados das rotas de sincronizacao Bling."""

from __future__ import annotations

from datetime import UTC, datetime
import time
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.produtos_models import Produto, ProdutoBlingSync
from app.bling_sync.product_matching import (
    _escolher_item_melhor_match,
    _escolher_item_sku_estrito,
    _extrair_lista_produtos_bling,
    _limpar_texto_busca,
    _montar_codigos_busca,
    _montar_codigos_busca_estrita,
    _produto_sincroniza_estoque,
)

PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _buscar_item_bling_para_vinculo(
    bling: BlingAPI,
    codigo_busca: str,
    nome_busca: str,
    codigos_extras: Optional[list[str]] = None,
) -> Optional[dict]:
    codigos_busca = _montar_codigos_busca_estrita(codigo_busca, codigos_extras)

    for codigo in codigos_busca:
        resultado = bling.listar_produtos(codigo=codigo, limite=50)
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            item = _escolher_item_sku_estrito(itens, codigos_busca)
            if item:
                return item

        resultado = bling.listar_produtos(sku=codigo, limite=50)
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            item = _escolher_item_sku_estrito(itens, codigos_busca)
            if item:
                return item

    return None


def _buscar_item_bling_por_codigos(
    bling: BlingAPI,
    codigo_busca: str,
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

    return None


def _buscar_produtos_bling_por_termo(
    bling: BlingAPI, termo: str, pagina: int, limite: int
) -> list[dict]:
    termo_limpo = _limpar_texto_busca(termo)
    if not termo_limpo:
        return _extrair_lista_produtos_bling(
            bling.listar_produtos(pagina=pagina, limite=limite)
        )

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
            return _buscar_item_bling_para_vinculo(
                bling, codigo_busca, nome_busca, codigos_extras=codigos_extras
            )
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


def _buscar_item_bling_por_codigos_com_retry(
    bling: BlingAPI,
    codigo_busca: str,
    codigos_extras: Optional[list[str]] = None,
) -> Optional[dict]:
    ultima_falha = None
    for tentativa in range(3):
        try:
            return _buscar_item_bling_por_codigos(
                bling, codigo_busca, codigos_extras=codigos_extras
            )
        except Exception as e:
            ultima_falha = e
            mensagem = str(e)
            if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
                time.sleep(0.8 + tentativa * 0.6)
                continue
            raise

    if ultima_falha:
        raise ultima_falha
    return None


def _consultar_produto_bling_com_retry(
    bling: BlingAPI, produto_id: str
) -> Optional[dict]:
    ultima_falha = None
    for tentativa in range(3):
        try:
            return bling.consultar_produto(produto_id)
        except Exception as e:
            ultima_falha = e
            mensagem = str(e)
            if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
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
    bling_produto_id = str(bling_produto_id or "").strip()
    if bling_produto_id:
        conflito = (
            db.query(ProdutoBlingSync)
            .filter(
                ProdutoBlingSync.tenant_id == tenant_id,
                ProdutoBlingSync.bling_produto_id == bling_produto_id,
                ProdutoBlingSync.produto_id != produto.id,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Esse item do Bling ja esta vinculado ao produto local "
                    f"{conflito.produto_id}."
                ),
            )

    sync = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.produto_id == produto.id,
            ProdutoBlingSync.tenant_id == tenant_id,
        )
        .first()
    )

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
