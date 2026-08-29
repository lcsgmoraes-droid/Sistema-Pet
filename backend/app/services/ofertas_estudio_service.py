"""Selecao, sugestoes e validacoes comerciais do Estudio de Ofertas."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.produtos_models import Produto, ProdutoLote
from app.services.validade_campanha_service import (
    construir_oferta_validade,
    obter_campanha_validade_config,
)
from app.vendas_models import Venda, VendaItem


ESTRATEGIAS = {
    "mais_vendidos",
    "melhor_margem",
    "baixo_giro",
    "estoque_alto",
    "validade_proxima",
    "mesclado",
}
STATUS_LOTE_BLOQUEADOS = {"vencido", "bloqueado", "esgotado", "excluido"}


def resumir_navegacao_publicacao(
    tipo_arte: str,
    imagens_urls: Iterable[str] | None,
    produtos_snapshot: Iterable[dict] | None,
) -> dict:
    """Monta o contrato comum usado nas chamadas do app e do e-commerce."""

    total_paginas = len([url for url in (imagens_urls or []) if str(url).strip()])
    total_produtos = len(list(produtos_snapshot or []))
    paginas_individuais = tipo_arte in {"individual", "produto"}

    if total_paginas <= 1:
        cta_label = "Ver oferta"
    elif tipo_arte == "individual":
        quantidade = total_produtos or total_paginas
        cta_label = f"Ver jornal — {quantidade} ofertas"
    elif tipo_arte == "produto":
        quantidade = total_produtos or total_paginas
        cta_label = f"Ver catálogo — {quantidade} produtos"
    else:
        cta_label = f"Ver jornal — {total_paginas} páginas"

    return {
        "total_paginas": total_paginas,
        "total_produtos": total_produtos,
        "modo_paginacao": (
            "produto_por_pagina" if paginas_individuais else "catalogo"
        ),
        "cta_label": cta_label,
    }


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _imagens_produto(produto: Produto) -> list[dict]:
    imagens = sorted(
        produto.imagens or [],
        key=lambda imagem: (
            not bool(imagem.e_principal),
            int(imagem.ordem or 0),
            int(imagem.id or 0),
        ),
    )
    resultado = []
    urls_vistas = set()
    principal = str(produto.imagem_principal or "").strip()
    if principal:
        resultado.append(
            {
                "id": None,
                "url": principal,
                "ordem": 0,
                "e_principal": True,
            }
        )
        urls_vistas.add(principal)
    for imagem in imagens:
        url = str(imagem.url or "").strip()
        if not url or url in urls_vistas:
            continue
        resultado.append(
            {
                "id": int(imagem.id) if imagem.id is not None else None,
                "url": url,
                "ordem": int(imagem.ordem or 0),
                "e_principal": bool(imagem.e_principal),
            }
        )
        urls_vistas.add(url)
    return resultado


def _imagem_produto(produto: Produto) -> str | None:
    imagens = _imagens_produto(produto)
    return imagens[0]["url"] if imagens else None


def _lotes_validos(
    produto: Produto, agora: datetime | None = None
) -> list[ProdutoLote]:
    agora = _naive(agora or datetime.utcnow())
    lotes = []
    for lote in produto.lotes or []:
        validade = _naive(lote.data_validade)
        status = str(lote.status or "ativo").strip().lower()
        if float(lote.quantidade_disponivel or 0) <= 0:
            continue
        if status in STATUS_LOTE_BLOQUEADOS:
            continue
        if validade and validade < agora:
            continue
        lotes.append(lote)
    return sorted(
        lotes,
        key=lambda lote: (
            lote.data_validade is None,
            _naive(lote.data_validade) or datetime.max,
            int(lote.ordem_entrada or 0),
        ),
    )


def produto_publicavel(produto: Produto, agora: datetime | None = None) -> bool:
    agora = _naive(agora or datetime.utcnow())
    if (
        not bool(produto.ativo)
        or produto.situacao is False
        or not bool(produto.is_sellable)
    ):
        return False
    if float(produto.estoque_atual or 0) <= 0:
        return False
    validade_produto = _naive(produto.data_validade)
    if validade_produto and validade_produto < agora:
        return False
    if bool(produto.controle_lote) and not _lotes_validos(produto, agora):
        return False
    return True


def _metricas_vendas(
    db: Session,
    tenant_id,
    *,
    dias: int,
) -> dict[int, dict]:
    data_inicio = datetime.utcnow() - timedelta(days=max(1, min(int(dias), 365)))
    rows = (
        db.query(
            VendaItem.produto_id,
            func.coalesce(func.sum(VendaItem.quantidade), 0).label("quantidade"),
            func.coalesce(func.sum(VendaItem.subtotal), 0).label("receita"),
            func.max(Venda.data_venda).label("ultima_venda"),
        )
        .join(Venda, Venda.id == VendaItem.venda_id)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.tenant_id == tenant_id,
            VendaItem.produto_id.isnot(None),
            Venda.data_venda >= data_inicio,
            Venda.status != "cancelada",
        )
        .group_by(VendaItem.produto_id)
        .all()
    )
    return {
        int(row.produto_id): {
            "quantidade": float(row.quantidade or 0),
            "receita": float(row.receita or 0),
            "ultima_venda": row.ultima_venda,
        }
        for row in rows
        if row.produto_id
    }


def buscar_produtos_publicaveis(
    db: Session,
    tenant_id,
    *,
    busca: str = "",
    limite: int = 80,
) -> list[Produto]:
    query = (
        db.query(Produto)
        .options(selectinload(Produto.imagens), selectinload(Produto.lotes))
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.is_sellable.is_(True),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            func.coalesce(Produto.estoque_atual, 0) > 0,
        )
    )
    termo = str(busca or "").strip()
    if termo:
        like = f"%{termo}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(like),
                Produto.codigo.ilike(like),
                Produto.codigo_barras.ilike(like),
            )
        )
    candidatos = (
        query.order_by(Produto.nome.asc()).limit(max(1, min(limite, 500))).all()
    )
    return [produto for produto in candidatos if produto_publicavel(produto)]


def serializar_produto_oferta(
    produto: Produto,
    *,
    campanha_validade=None,
    metricas: dict | None = None,
    motivo: str | None = None,
) -> dict:
    preco_erp = round(float(produto.preco_venda or 0), 2)
    preco_app = round(
        float(produto.preco_app if produto.preco_app is not None else preco_erp), 2
    )
    preco_ecommerce = round(
        float(
            produto.preco_ecommerce
            if produto.preco_ecommerce is not None
            else preco_erp
        ),
        2,
    )
    lotes = _lotes_validos(produto)
    lote_validade = next((lote for lote in lotes if lote.data_validade), None)
    preco_validade = None
    desconto_validade = None
    if lote_validade and campanha_validade:
        oferta = construir_oferta_validade(
            produto,
            lote_validade,
            "ecommerce",
            config=campanha_validade,
        )
        preco_validade = oferta.promotional_price if oferta.active else None
        desconto_validade = oferta.percentual_desconto if oferta.active else None

    metricas = metricas or {}
    quantidade_vendida = float(metricas.get("quantidade") or 0)
    receita = float(metricas.get("receita") or 0)
    custo_estimado = float(produto.preco_custo or 0) * quantidade_vendida
    margem_realizada = (
        ((receita - custo_estimado) / receita * 100) if receita > 0 else 0
    )
    return {
        "id": int(produto.id),
        "codigo": produto.codigo,
        "nome": produto.nome,
        "imagem_url": _imagem_produto(produto),
        "imagens": _imagens_produto(produto),
        "preco_erp": preco_erp,
        "preco_app": preco_app,
        "preco_ecommerce": preco_ecommerce,
        "preco_custo": round(float(produto.preco_custo or 0), 2),
        "estoque_atual": round(float(produto.estoque_atual or 0), 3),
        "unidade": produto.unidade or "UN",
        "precos_divergentes": len({preco_erp, preco_app, preco_ecommerce}) > 1,
        "preco_sugerido_validade": preco_validade,
        "desconto_sugerido_validade": desconto_validade,
        "lote_validade": (
            {
                "id": int(lote_validade.id),
                "nome": lote_validade.nome_lote,
                "data_validade": lote_validade.data_validade.isoformat(),
                "quantidade_disponivel": float(
                    lote_validade.quantidade_disponivel or 0
                ),
                "dias_para_vencer": lote_validade.dias_para_vencer,
            }
            if lote_validade
            else None
        ),
        "quantidade_vendida_periodo": round(quantidade_vendida, 2),
        "receita_periodo": round(receita, 2),
        "margem_periodo": round(margem_realizada, 2),
        "motivo_sugestao": motivo,
    }


def _ordenar_estrategia(
    produtos: Iterable[Produto],
    metricas: dict[int, dict],
    estrategia: str,
) -> list[Produto]:
    produtos = list(produtos)
    if estrategia == "mais_vendidos":
        return sorted(
            [
                p
                for p in produtos
                if metricas.get(int(p.id), {}).get("quantidade", 0) > 0
            ],
            key=lambda p: metricas[int(p.id)]["quantidade"],
            reverse=True,
        )
    if estrategia == "melhor_margem":
        vendidos = [
            p for p in produtos if metricas.get(int(p.id), {}).get("receita", 0) > 0
        ]
        return sorted(
            vendidos,
            key=lambda p: (
                (
                    metricas[int(p.id)]["receita"]
                    - float(p.preco_custo or 0) * metricas[int(p.id)]["quantidade"]
                )
                / metricas[int(p.id)]["receita"]
            ),
            reverse=True,
        )
    if estrategia == "baixo_giro":
        return sorted(
            produtos,
            key=lambda p: (
                metricas.get(int(p.id), {}).get("quantidade", 0),
                -float(p.estoque_atual or 0),
            ),
        )
    if estrategia == "estoque_alto":
        return sorted(
            produtos,
            key=lambda p: (
                float(p.estoque_atual or 0) / max(float(p.estoque_maximo or 0), 1),
                float(p.estoque_atual or 0),
            ),
            reverse=True,
        )
    if estrategia == "validade_proxima":
        return sorted(
            [
                produto
                for produto in produtos
                if any(lote.data_validade for lote in _lotes_validos(produto))
            ],
            key=lambda produto: _naive(
                next(
                    lote.data_validade
                    for lote in _lotes_validos(produto)
                    if lote.data_validade
                )
            ),
        )
    return produtos


def _motivo(estrategia: str, produto: Produto, metricas: dict[int, dict]) -> str:
    dados = metricas.get(int(produto.id), {})
    if estrategia == "mais_vendidos":
        return f"Mais vendido · {float(dados.get('quantidade') or 0):g} un."
    if estrategia == "melhor_margem":
        receita = float(dados.get("receita") or 0)
        qtd = float(dados.get("quantidade") or 0)
        margem = (
            ((receita - float(produto.preco_custo or 0) * qtd) / receita * 100)
            if receita
            else 0
        )
        return f"Alta margem · {margem:.0f}%"
    if estrategia == "baixo_giro":
        return f"Baixo giro · {float(dados.get('quantidade') or 0):g} un. no periodo"
    if estrategia == "estoque_alto":
        return f"Estoque alto · {float(produto.estoque_atual or 0):g} un."
    if estrategia == "validade_proxima":
        lote = next(
            (lote for lote in _lotes_validos(produto) if lote.data_validade),
            None,
        )
        return (
            f"Validade proxima · {lote.dias_para_vencer} dias"
            if lote
            else "Validade proxima"
        )
    return "Selecao inteligente"


def montar_sugestao(
    db: Session,
    tenant_id,
    *,
    estrategia: str,
    dias: int = 7,
    limite: int = 8,
) -> list[dict]:
    estrategia = str(estrategia or "mesclado").strip().lower()
    if estrategia not in ESTRATEGIAS:
        raise HTTPException(status_code=400, detail="Estrategia de sugestao invalida.")
    limite = max(1, min(int(limite), 24))
    metricas = _metricas_vendas(db, tenant_id, dias=dias)
    produtos = buscar_produtos_publicaveis(db, tenant_id, limite=500)
    campanha = obter_campanha_validade_config(db, tenant_id)

    if estrategia != "mesclado":
        escolhidos = _ordenar_estrategia(produtos, metricas, estrategia)[:limite]
        return [
            serializar_produto_oferta(
                produto,
                campanha_validade=campanha,
                metricas=metricas.get(int(produto.id)),
                motivo=_motivo(estrategia, produto, metricas),
            )
            for produto in escolhidos
        ]

    quantidade_por_grupo = max(1, ceil(limite / 4))
    escolhidos: list[tuple[Produto, str]] = []
    vistos: set[int] = set()
    for grupo in ("mais_vendidos", "melhor_margem", "baixo_giro", "validade_proxima"):
        adicionados = 0
        for produto in _ordenar_estrategia(produtos, metricas, grupo):
            if int(produto.id) in vistos:
                continue
            escolhidos.append((produto, grupo))
            vistos.add(int(produto.id))
            adicionados += 1
            if adicionados >= quantidade_por_grupo or len(escolhidos) >= limite:
                break
        if len(escolhidos) >= limite:
            break
    if len(escolhidos) < limite:
        for produto in _ordenar_estrategia(produtos, metricas, "estoque_alto"):
            if int(produto.id) in vistos:
                continue
            escolhidos.append((produto, "estoque_alto"))
            vistos.add(int(produto.id))
            if len(escolhidos) >= limite:
                break
    return [
        serializar_produto_oferta(
            produto,
            campanha_validade=campanha,
            metricas=metricas.get(int(produto.id)),
            motivo=_motivo(grupo, produto, metricas),
        )
        for produto, grupo in escolhidos
    ]


def validar_snapshot_publicacao(
    db: Session,
    tenant_id,
    itens,
    *,
    fim_em: datetime,
) -> list[dict]:
    produto_ids = list(dict.fromkeys(int(item.produto_id) for item in itens))
    if len(produto_ids) != len(itens):
        raise HTTPException(
            status_code=400, detail="Nao repita o mesmo produto na publicacao."
        )
    produtos = (
        db.query(Produto)
        .options(selectinload(Produto.imagens), selectinload(Produto.lotes))
        .filter(Produto.tenant_id == tenant_id, Produto.id.in_(produto_ids))
        .all()
    )
    por_id = {int(produto.id): produto for produto in produtos}
    if len(por_id) != len(produto_ids):
        raise HTTPException(
            status_code=404, detail="Um ou mais produtos nao foram encontrados."
        )

    snapshots = []
    for item in itens:
        produto = por_id[int(item.produto_id)]
        if not produto_publicavel(produto):
            raise HTTPException(
                status_code=400,
                detail=f"{produto.nome} esta sem estoque valido ou esta vencido.",
            )
        lote_snapshot = None
        if item.mostrar_validade:
            lote = next(
                (
                    lote
                    for lote in _lotes_validos(produto)
                    if int(lote.id) == int(item.lote_id or 0)
                ),
                None,
            )
            if lote is None or lote.data_validade is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selecione um lote valido para {produto.nome}.",
                )
            if _naive(fim_em).date() > _naive(lote.data_validade).date():
                raise HTTPException(
                    status_code=400,
                    detail=f"A promocao de {produto.nome} nao pode terminar depois da validade do lote.",
                )
            lote_snapshot = {
                "id": int(lote.id),
                "nome": lote.nome_lote,
                "data_validade": lote.data_validade.isoformat(),
                "quantidade_disponivel": float(lote.quantidade_disponivel or 0),
                "aviso": "Quantidade limitada ao lote",
            }
        preco = round(float(item.preco_arte), 2)
        custo = round(float(produto.preco_custo or 0), 2)
        snapshots.append(
            {
                "produto_id": int(produto.id),
                "codigo": produto.codigo,
                "nome": produto.nome,
                "preco_arte": preco,
                "preco_erp": round(float(produto.preco_venda or 0), 2),
                "preco_custo": custo,
                "margem_percentual": round(
                    ((preco - custo) / preco * 100) if preco else 0, 2
                ),
                "imagem_url": item.imagem_url or _imagem_produto(produto),
                "mostrar_validade": bool(item.mostrar_validade),
                "lote": lote_snapshot,
            }
        )
    return snapshots
