# -*- coding: utf-8 -*-
"""Varredura/reconciliacao de ProdutoIdentidade pra produtos ja cadastrados
antes da identidade compartilhada existir (fase D, Checkpoint 7 de
Documentacao/Dominio/Plano-Camada-Geral.md).

Mesma regra de correspondencia do fluxo ao vivo (codigo de barras ou, na
falta dele, GTIN, exato) — ver app/services/produto_identidade_service.py.
Nunca apaga/funde Produto; so cria ProdutoIdentidade novas e preenche o FK
nullable produtos.produto_identidade_id. Idempotente: rodar de novo sem dado
novo nao duplica nem diverge.

Uso:
    python -m scripts.backfill_produto_identidades --dry-run
    python -m scripts.backfill_produto_identidades --grupo-id 3
    python -m scripts.backfill_produto_identidades --grupo-id 3 --dry-run

--dry-run e o padrao OBRIGATORIO da primeira execucao em qualquer ambiente —
so roda escrita real com --dry-run explicitamente omitido, depois de revisar
o relatorio de cobertura de um --dry-run anterior.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import text

import app.db.base  # noqa: F401 -- registra todos os models
from app.db import SessionLocal
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.grupo_comercial_contexto import listar_empresas_do_grupo
from app.produto_identidade_models import (
    ProdutoIdentidade,
    ProdutoIdentidadeBackfillRun,
    ProdutoIdentidadeConflito,
)
from app.produtos_catalogo_models import Produto, ProdutoHistoricoAlteracao
from app.services.produto_identidade_service import (
    INHERENT_FIELDS,
    normalizar_chave_matching,
)
from app.tenancy.context import tenant_context, set_current_tenant

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("backfill_produto_identidades")


def _grupos_ativos_com_2_mais_membros(db) -> list[int]:
    membros_por_grupo: dict[int, int] = defaultdict(int)
    for grupo_id, in db.query(GrupoComercialMembro.grupo_id).join(
        GrupoComercial, GrupoComercial.id == GrupoComercialMembro.grupo_id
    ).filter(
        GrupoComercialMembro.status == "ativo",
        GrupoComercial.status == "ativo",
    ):
        membros_por_grupo[grupo_id] += 1
    return sorted(gid for gid, qtd in membros_por_grupo.items() if qtd >= 2)


def _candidatos_por_chave(db, tenant_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Scan leve (so id/tenant_id/produto_identidade_id), so produto ativo e
    nao deletado, com chave de correspondencia nao vazia."""
    linhas = db.execute(
        text(
            """
            SELECT id, tenant_id::text AS tenant_id, produto_identidade_id,
                   COALESCE(NULLIF(trim(codigo_barras), ''), NULLIF(trim(gtin_ean), '')) AS chave
            FROM produtos
            WHERE tenant_id::text = ANY(:ids)
              AND ativo IS TRUE
              AND deleted_at IS NULL
              AND tipo <> 'servico'
              AND COALESCE(NULLIF(trim(codigo_barras), ''), NULLIF(trim(gtin_ean), '')) IS NOT NULL
            """
        ),
        {"ids": tenant_ids},
    ).mappings().all()

    por_chave: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for linha in linhas:
        por_chave[linha["chave"]].append(dict(linha))
    # Só nos interessa quem aparece em 2+ lojas DISTINTAS — dentro da mesma
    # loja é problema do fusão-de-duplicados local, fora de escopo aqui.
    return {
        chave: registros
        for chave, registros in por_chave.items()
        if len({r["tenant_id"] for r in registros}) > 1
    }


def _carregar_produto(db, tenant_id: str, produto_id: int) -> Produto | None:
    with tenant_context(tenant_id):
        set_current_tenant(tenant_id)
        return db.query(Produto).filter(Produto.id == produto_id).first()


def _reconciliar_campos(produtos: list[Produto]) -> dict[str, Any]:
    """Campo a campo, mais recente-atualizado primeiro, só usa valor
    preenchido — nunca deixa um produto mais recente mas incompleto apagar um
    campo que outro produto do grupo já tinha preenchido."""
    ordenados = sorted(produtos, key=lambda p: p.updated_at or p.created_at, reverse=True)
    valores: dict[str, Any] = {}
    for campo in INHERENT_FIELDS:
        for produto in ordenados:
            valor = getattr(produto, campo)
            if valor is not None and valor != "":
                valores[campo] = valor
                break
    return valores


def _processar_chave(
    db,
    grupo_id: int,
    chave: str,
    registros: list[dict[str, Any]],
    dry_run: bool,
    contadores: dict[str, int],
) -> None:
    produtos = [
        p
        for p in (
            _carregar_produto(db, r["tenant_id"], r["id"]) for r in registros
        )
        if p is not None
    ]
    if len(produtos) < 2:
        return

    identidades_existentes = {
        p.produto_identidade_id for p in produtos if p.produto_identidade_id is not None
    }

    if len(identidades_existentes) > 1:
        contadores["conflitos"] += 1
        if not dry_run:
            db.add(
                ProdutoIdentidadeConflito(
                    grupo_id=grupo_id,
                    chave_matching=chave,
                    produto_ids=[
                        {"tenant_id": str(p.tenant_id), "produto_id": p.id}
                        for p in produtos
                    ],
                )
            )
        logger.info(
            "  CONFLITO chave=%s: %d identidades diferentes ja vinculadas (%s) -- revisao manual",
            chave,
            len(identidades_existentes),
            sorted(str(i) for i in identidades_existentes),
        )
        return

    nao_vinculados = [p for p in produtos if p.produto_identidade_id is None]
    if not nao_vinculados:
        return  # já todos vinculados à mesma identidade, nada a fazer (idempotência)

    origem = min(produtos, key=lambda p: p.created_at or p.updated_at)
    # Resolucao da identidade (leitura da existente, ou criacao da nova)
    # precisa de um tenant_id ativo no contexto -- o guard de ORM
    # (app/database/orm_guards.py) exige isso pra qualquer insert em tabela
    # multi-tenant, e o filtro de leitura (app/tenancy/filters.py) tambem.
    # Qualquer loja do grupo serve pra LER produto_identidades (RLS aberta),
    # mas um INSERT novo precisa bater exatamente com a loja de origem.
    with tenant_context(origem.tenant_id):
        set_current_tenant(origem.tenant_id)
        if identidades_existentes:
            identidade_id = next(iter(identidades_existentes))
            identidade = db.query(ProdutoIdentidade).filter_by(id=identidade_id).first()
            contadores["vinculados"] += len(nao_vinculados)
            logger.info(
                "  chave=%s: ligando %d produto(s) a identidade existente id=%s",
                chave,
                len(nao_vinculados),
                identidade_id,
            )
        else:
            valores = _reconciliar_campos(produtos)
            identidade = ProdutoIdentidade(
                tenant_id=origem.tenant_id,
                origem_tenant_id=origem.tenant_id,
                chave_matching=chave,
            )
            for campo, valor in valores.items():
                setattr(identidade, campo, valor)
            if not dry_run:
                db.add(identidade)
                db.flush()
            contadores["identidades_criadas"] += 1
            contadores["vinculados"] += len(nao_vinculados)
            logger.info(
                "  chave=%s: identidade nova criada a partir de %d produto(s), ligando todos",
                chave,
                len(produtos),
            )

    if dry_run:
        return

    for produto in nao_vinculados:
        with tenant_context(produto.tenant_id):
            set_current_tenant(produto.tenant_id)
            for campo in INHERENT_FIELDS:
                valor_novo = getattr(identidade, campo)
                valor_atual = getattr(produto, campo)
                if valor_atual == valor_novo:
                    continue
                db.add(
                    ProdutoHistoricoAlteracao(
                        tenant_id=produto.tenant_id,
                        produto_id=produto.id,
                        user_id=None,
                        campo=campo,
                        valor_anterior=str(valor_atual) if valor_atual is not None else None,
                        valor_novo=str(valor_novo) if valor_novo is not None else None,
                    )
                )
                setattr(produto, campo, valor_novo)
            produto.produto_identidade_id = identidade.id
            db.flush()


def processar_grupo(db, grupo_id: int, dry_run: bool) -> dict[str, int]:
    tenant_ids = listar_empresas_do_grupo(db, _primeiro_tenant_do_grupo(db, grupo_id))
    logger.info(
        "Grupo %s: %d loja(s) ativa(s) -- %s",
        grupo_id,
        len(tenant_ids),
        ", ".join(tenant_ids),
    )

    candidatos = _candidatos_por_chave(db, tenant_ids)
    total_produtos_ativos = db.execute(
        text(
            "SELECT count(*) FROM produtos WHERE tenant_id::text = ANY(:ids) "
            "AND ativo IS TRUE AND deleted_at IS NULL"
        ),
        {"ids": tenant_ids},
    ).scalar()
    total_com_gtin = db.execute(
        text(
            "SELECT count(*) FROM produtos WHERE tenant_id::text = ANY(:ids) "
            "AND ativo IS TRUE AND deleted_at IS NULL "
            "AND COALESCE(NULLIF(trim(codigo_barras), ''), NULLIF(trim(gtin_ean), '')) IS NOT NULL"
        ),
        {"ids": tenant_ids},
    ).scalar()

    contadores = {
        "identidades_criadas": 0,
        "vinculados": 0,
        "conflitos": 0,
    }
    for chave, registros in sorted(candidatos.items()):
        _processar_chave(db, grupo_id, chave, registros, dry_run, contadores)

    if dry_run:
        db.rollback()
    else:
        db.add(
            ProdutoIdentidadeBackfillRun(
                grupo_id=grupo_id,
                dry_run=False,
                total_produtos_ativos=total_produtos_ativos or 0,
                total_com_gtin=total_com_gtin or 0,
                total_identidades_criadas=contadores["identidades_criadas"],
                total_vinculados=contadores["vinculados"],
                total_sem_gtin=(total_produtos_ativos or 0) - (total_com_gtin or 0),
                total_conflitos=contadores["conflitos"],
            )
        )
        db.commit()

    logger.info(
        "Grupo %s -- produtos ativos: %d | com codigo/GTIN: %d | sem GTIN: %d | "
        "identidades criadas: %d | produtos vinculados: %d | conflitos: %d%s",
        grupo_id,
        total_produtos_ativos or 0,
        total_com_gtin or 0,
        (total_produtos_ativos or 0) - (total_com_gtin or 0),
        contadores["identidades_criadas"],
        contadores["vinculados"],
        contadores["conflitos"],
        "  [DRY RUN -- nada foi escrito]" if dry_run else "",
    )
    return contadores


def _primeiro_tenant_do_grupo(db, grupo_id: int) -> str:
    membro = (
        db.query(GrupoComercialMembro.empresa_id)
        .filter(
            GrupoComercialMembro.grupo_id == grupo_id,
            GrupoComercialMembro.status == "ativo",
        )
        .order_by(GrupoComercialMembro.id)
        .first()
    )
    if membro is None:
        raise ValueError(f"Grupo {grupo_id} nao tem nenhum membro ativo")
    return str(membro[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grupo-id", type=int, default=None, help="Processa só este grupo")
    parser.add_argument(
        "--dry-run", action="store_true", help="Calcula e mostra o plano, nao escreve nada"
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        grupo_ids = (
            [args.grupo_id] if args.grupo_id else _grupos_ativos_com_2_mais_membros(db)
        )
        if not grupo_ids:
            logger.info("Nenhum grupo comercial ativo com 2+ lojas encontrado.")
            return

        logger.info(
            "%d grupo(s) a processar: %s%s",
            len(grupo_ids),
            grupo_ids,
            "  [DRY RUN]" if args.dry_run else "",
        )
        for grupo_id in grupo_ids:
            processar_grupo(db, grupo_id, args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
