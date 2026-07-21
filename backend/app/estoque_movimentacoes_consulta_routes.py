"""
Rotas de consulta de movimentacoes de estoque.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque_movimentacoes_context import (
    _contexto_venda_pedido_integrado,
    _detalhar_reservas_ativas_produto,
    _label_canal_movimentacao,
    _observacao_exibicao_movimentacao_bling,
)
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.vendas_models import Venda


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


_CANAIS_DESTAQUE = ("loja_fisica", "mercado_livre", "shopee", "amazon")


def _filtro_antes_movimentacao(movimentacao):
    if not movimentacao or movimentacao.created_at is None:
        return EstoqueMovimentacao.id < int(getattr(movimentacao, "id", 0) or 0)
    return or_(
        EstoqueMovimentacao.created_at < movimentacao.created_at,
        and_(
            EstoqueMovimentacao.created_at == movimentacao.created_at,
            EstoqueMovimentacao.id < movimentacao.id,
        ),
    )


def _filtro_depois_movimentacao(movimentacao):
    if not movimentacao or movimentacao.created_at is None:
        return EstoqueMovimentacao.id > int(getattr(movimentacao, "id", 0) or 0)
    return or_(
        EstoqueMovimentacao.created_at > movimentacao.created_at,
        and_(
            EstoqueMovimentacao.created_at == movimentacao.created_at,
            EstoqueMovimentacao.id > movimentacao.id,
        ),
    )


def _saldo_antes_da_pagina(
    db: Session,
    *,
    tenant_id,
    produto_id: int,
    primeira_movimentacao,
) -> float:
    if not primeira_movimentacao:
        return 0.0

    filtro_antes = _filtro_antes_movimentacao(primeira_movimentacao)
    ultimo_balanco = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.quantidade_nova.isnot(None),
            filtro_antes,
        )
        .order_by(
            EstoqueMovimentacao.created_at.desc(),
            EstoqueMovimentacao.id.desc(),
        )
        .first()
    )

    saldo = float(ultimo_balanco.quantidade_nova or 0) if ultimo_balanco else 0.0
    query = db.query(
        EstoqueMovimentacao.tipo,
        EstoqueMovimentacao.status,
        EstoqueMovimentacao.quantidade,
        EstoqueMovimentacao.quantidade_nova,
    ).filter(
        EstoqueMovimentacao.tenant_id == tenant_id,
        EstoqueMovimentacao.produto_id == produto_id,
        filtro_antes,
    )
    if ultimo_balanco:
        query = query.filter(_filtro_depois_movimentacao(ultimo_balanco))

    for tipo, status, quantidade, quantidade_nova in query.order_by(
        EstoqueMovimentacao.created_at,
        EstoqueMovimentacao.id,
    ):
        if quantidade_nova is not None:
            saldo = float(quantidade_nova)
            continue
        if status == "cancelado":
            continue
        quantidade_numero = float(quantidade or 0)
        if tipo == "entrada":
            saldo += quantidade_numero
        elif tipo == "saida":
            saldo -= quantidade_numero
    return saldo


def _custo_entrada_antes_da_pagina(
    db: Session,
    *,
    tenant_id,
    produto_id: int,
    primeira_movimentacao,
):
    if not primeira_movimentacao:
        return None
    linha = (
        db.query(EstoqueMovimentacao.custo_unitario)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.tipo == "entrada",
            EstoqueMovimentacao.custo_unitario.isnot(None),
            EstoqueMovimentacao.custo_unitario > 0,
            _filtro_antes_movimentacao(primeira_movimentacao),
        )
        .order_by(
            EstoqueMovimentacao.created_at.desc(),
            EstoqueMovimentacao.id.desc(),
        )
        .first()
    )
    return linha[0] if linha else None


def _primeiro_lote_consumido(movimentacao):
    if not movimentacao or not movimentacao.lotes_consumidos:
        return None
    try:
        lotes = json.loads(movimentacao.lotes_consumidos)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return lotes[0] if isinstance(lotes, list) and lotes else None


def _consumo_lotes_antes_da_pagina(
    db: Session,
    *,
    tenant_id,
    produto_id: int,
    primeira_movimentacao,
    lote_ids: set[int],
) -> dict[int, float]:
    consumo = {lote_id: 0.0 for lote_id in lote_ids}
    if not primeira_movimentacao or not lote_ids:
        return consumo

    linhas = (
        db.query(EstoqueMovimentacao.lotes_consumidos)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.lotes_consumidos.isnot(None),
            _filtro_antes_movimentacao(primeira_movimentacao),
        )
        .order_by(EstoqueMovimentacao.created_at, EstoqueMovimentacao.id)
        .all()
    )
    for (lotes_consumidos,) in linhas:
        try:
            lotes = json.loads(lotes_consumidos)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(lotes, list) or not lotes:
            continue
        primeiro_lote = lotes[0]
        try:
            lote_id = int(primeiro_lote.get("lote_id") or 0)
        except (TypeError, ValueError):
            continue
        if lote_id in consumo:
            consumo[lote_id] += float(primeiro_lote.get("quantidade") or 0)
    return consumo


def _agrupar_vendas_por_canal(registros: list[dict]) -> list[dict]:
    grupos: dict[str, dict] = {}
    for registro in registros:
        canal = registro.get("canal")
        if not canal:
            continue
        grupo = grupos.setdefault(canal, {"qtd": 0.0, "valor": 0.0, "count": 0})
        quantidade = float(registro.get("quantidade") or 0)
        preco = float(registro.get("preco_venda_unitario") or 0)
        grupo["qtd"] += quantidade
        grupo["valor"] += quantidade * preco
        grupo["count"] += 1

    if not grupos:
        return []
    for canal in _CANAIS_DESTAQUE:
        grupos.setdefault(canal, {"qtd": 0.0, "valor": 0.0, "count": 0})

    total_quantidade = sum(grupo["qtd"] for grupo in grupos.values())
    resultado = [
        {
            "canal": canal,
            **grupo,
            "pct": (grupo["qtd"] / total_quantidade) * 100
            if total_quantidade > 0
            else 0,
        }
        for canal, grupo in grupos.items()
        if grupo["count"] > 0 or canal in _CANAIS_DESTAQUE
    ]

    def _chave(item):
        destaque = (
            _CANAIS_DESTAQUE.index(item["canal"])
            if item["canal"] in _CANAIS_DESTAQUE
            else 999
        )
        return (-item["qtd"], destaque, item["canal"])

    return sorted(resultado, key=_chave)


@router.get("/movimentacoes/produto/{produto_id}")
def listar_movimentacoes_produto(
    produto_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista as movimentacoes de um produto em paginas leves.
    """
    _current_user, tenant_id = user_and_tenant
    logger.info("Listando movimentacoes do produto %s", produto_id)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    query_base = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto_id,
        EstoqueMovimentacao.tenant_id == tenant_id,
    )
    total_registros = query_base.count()
    pages = (total_registros + page_size - 1) // page_size if total_registros else 0
    page = min(page, max(pages, 1))

    totais_row = query_base.with_entities(
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            EstoqueMovimentacao.tipo == "entrada",
                            or_(
                                EstoqueMovimentacao.status.is_(None),
                                EstoqueMovimentacao.status != "cancelado",
                            ),
                        ),
                        EstoqueMovimentacao.quantidade,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            EstoqueMovimentacao.tipo == "saida",
                            or_(
                                EstoqueMovimentacao.status.is_(None),
                                EstoqueMovimentacao.status != "cancelado",
                            ),
                        ),
                        EstoqueMovimentacao.quantidade,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
    ).first()

    movimentacoes_desc = (
        query_base.order_by(
            EstoqueMovimentacao.created_at.desc(),
            EstoqueMovimentacao.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    movimentacoes = list(reversed(movimentacoes_desc))

    pedido_integrado_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == "pedido_integrado" and mov.referencia_id
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

    venda_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == "venda" and mov.referencia_id
        }
    )
    vendas = (
        db.query(Venda.id, Venda.canal, Venda.total)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
        .all()
        if venda_ids
        else []
    )
    vendas_por_id = {
        int(venda_id): {"canal": canal, "total": total}
        for venda_id, canal, total in vendas
    }

    lotes_consumidos_pagina = {
        mov.id: _primeiro_lote_consumido(mov) for mov in movimentacoes
    }
    lote_ids = {int(mov.lote_id) for mov in movimentacoes if mov.lote_id}
    for primeiro_lote in lotes_consumidos_pagina.values():
        if not primeiro_lote:
            continue
        try:
            lote_id = int(primeiro_lote.get("lote_id") or 0)
        except (TypeError, ValueError):
            continue
        if lote_id:
            lote_ids.add(lote_id)

    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.tenant_id == tenant_id,
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.id.in_(lote_ids),
        )
        .all()
        if lote_ids
        else []
    )
    lotes_por_id = {int(lote.id): lote for lote in lotes}

    resultado = []
    primeira_movimentacao = movimentacoes[0] if movimentacoes else None
    custo_anterior_entrada = _custo_entrada_antes_da_pagina(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        primeira_movimentacao=primeira_movimentacao,
    )
    consumo_por_lote = _consumo_lotes_antes_da_pagina(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        primeira_movimentacao=primeira_movimentacao,
        lote_ids=lote_ids,
    )
    saldo_estimado = _saldo_antes_da_pagina(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        primeira_movimentacao=primeira_movimentacao,
    )

    try:
        from app.services.bling_nf_service import movimento_documentado_por_nf
    except Exception:
        movimento_documentado_por_nf = None

    for mov in movimentacoes:
        if mov.quantidade_nova is not None:
            saldo_apos_lancamento = float(mov.quantidade_nova)
            saldo_estimado = saldo_apos_lancamento
        else:
            quantidade_movimento = float(mov.quantidade or 0)
            if mov.status != "cancelado":
                if mov.tipo == "entrada":
                    saldo_estimado += quantidade_movimento
                elif mov.tipo == "saida":
                    saldo_estimado -= quantidade_movimento
            saldo_apos_lancamento = saldo_estimado

        lote_nome = None
        lote_info = None

        if mov.tipo == "entrada" and mov.lote_id:
            lote = lotes_por_id.get(int(mov.lote_id))
            if lote:
                lote_nome = lote.nome_lote
                lote_info = {
                    "nome": lote_nome,
                    "total_lote": lote.quantidade_inicial,
                    "tipo": "entrada",
                }

        elif mov.tipo == "saida":
            primeiro_lote = lotes_consumidos_pagina.get(mov.id)
            if primeiro_lote:
                try:
                    lote_id = int(primeiro_lote.get("lote_id") or 0)
                except (TypeError, ValueError):
                    lote_id = 0
                if lote_id:
                    consumo_por_lote.setdefault(lote_id, 0.0)
                    consumo_por_lote[lote_id] += float(
                        primeiro_lote.get("quantidade") or 0
                    )
                    lote = lotes_por_id.get(lote_id)
                    if lote:
                        lote_info = {
                            "nome": lote.nome_lote,
                            "consumido_acumulado": consumo_por_lote[lote_id],
                            "total_lote": lote.quantidade_inicial,
                            "quantidade_movimento": primeiro_lote.get("quantidade", 0),
                            "tipo": "saida",
                        }

        variacao_custo = None
        if mov.tipo == "entrada" and mov.custo_unitario:
            if custo_anterior_entrada and custo_anterior_entrada > 0:
                diferenca_valor = mov.custo_unitario - custo_anterior_entrada
                diferenca_percentual = (diferenca_valor / custo_anterior_entrada) * 100

                variacao_custo = {
                    "custo_anterior": custo_anterior_entrada,
                    "custo_atual": mov.custo_unitario,
                    "diferenca_valor": diferenca_valor,
                    "diferenca_percentual": diferenca_percentual,
                    "tipo": "aumento"
                    if diferenca_valor > 0
                    else "reducao"
                    if diferenca_valor < 0
                    else "estavel",
                }

            custo_anterior_entrada = mov.custo_unitario

        canal_venda = None
        preco_venda_unitario = None
        nf_numero = None
        documento_exibicao = mov.documento
        observacao_exibicao = mov.observacao
        if mov.referencia_tipo == "venda" and mov.referencia_id:
            venda = vendas_por_id.get(int(mov.referencia_id))
            if venda:
                canal_venda = venda["canal"]
                if mov.quantidade and mov.quantidade > 0:
                    preco_venda_unitario = (
                        float(venda["total"]) / float(mov.quantidade)
                        if venda["total"]
                        else None
                    )
        elif mov.referencia_tipo == "pedido_integrado" and mov.referencia_id:
            pedido_integrado = pedidos_integrados_por_id.get(int(mov.referencia_id))
            if pedido_integrado:
                contexto_venda = _contexto_venda_pedido_integrado(
                    db, pedido_integrado, produto_id
                )
                canal_venda = contexto_venda.get("canal")
                nf_numero = contexto_venda.get("nf_numero")
                nf_id = contexto_venda.get("nf_id")
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

        resultado.append(
            {
                "id": mov.id,
                "tipo": mov.tipo,
                "status": mov.status,
                "motivo": mov.motivo,
                "quantidade": mov.quantidade,
                "quantidade_anterior": mov.quantidade_anterior,
                "quantidade_nova": mov.quantidade_nova,
                "saldo_apos_lancamento": saldo_apos_lancamento,
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
                "user_id": mov.user_id,
            }
        )

    resultado.reverse()

    return {
        "movimentacoes": resultado,
        "total_registros": total_registros,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "totais": {
            "total_entradas": float(totais_row[0] or 0),
            "total_saidas": float(totais_row[1] or 0),
        },
    }


@router.get("/movimentacoes/produto/{produto_id}/vendas-por-canal")
def listar_vendas_por_canal_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Resume o historico de vendas por canal sem enviar todas as linhas."""
    _current_user, tenant_id = user_and_tenant
    produto_existe = (
        db.query(Produto.id)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto_existe:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.tipo == "saida",
            or_(
                EstoqueMovimentacao.status.is_(None),
                EstoqueMovimentacao.status != "cancelado",
            ),
            EstoqueMovimentacao.referencia_tipo.in_(("venda", "pedido_integrado")),
        )
        .order_by(EstoqueMovimentacao.created_at, EstoqueMovimentacao.id)
        .all()
    )
    venda_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == "venda" and mov.referencia_id
        }
    )
    pedido_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == "pedido_integrado" and mov.referencia_id
        }
    )
    vendas = (
        db.query(Venda.id, Venda.canal, Venda.total)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
        .all()
        if venda_ids
        else []
    )
    pedidos = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.id.in_(pedido_ids),
        )
        .all()
        if pedido_ids
        else []
    )
    vendas_por_id = {
        int(venda_id): {"canal": canal, "total": total}
        for venda_id, canal, total in vendas
    }
    pedidos_por_id = {int(pedido.id): pedido for pedido in pedidos}
    contextos_pedido: dict[int, dict] = {}

    try:
        from app.services.bling_nf_service import movimento_documentado_por_nf
    except Exception:
        movimento_documentado_por_nf = None

    registros = []
    for mov in movimentacoes:
        canal = None
        preco_venda_unitario = None
        if mov.referencia_tipo == "venda" and mov.referencia_id:
            venda = vendas_por_id.get(int(mov.referencia_id))
            if venda:
                canal = venda["canal"]
                if mov.quantidade and venda["total"]:
                    preco_venda_unitario = float(venda["total"]) / float(mov.quantidade)
        elif mov.referencia_tipo == "pedido_integrado" and mov.referencia_id:
            pedido_id = int(mov.referencia_id)
            pedido = pedidos_por_id.get(pedido_id)
            if pedido:
                contexto = contextos_pedido.get(pedido_id)
                if contexto is None:
                    contexto = _contexto_venda_pedido_integrado(db, pedido, produto_id)
                    contextos_pedido[pedido_id] = contexto
                movimento_usa_nf = bool(
                    movimento_documentado_por_nf
                    and movimento_documentado_por_nf(
                        mov,
                        nf_numero=contexto.get("nf_numero"),
                        nf_bling_id=contexto.get("nf_id"),
                    )
                )
                if movimento_usa_nf:
                    canal = contexto.get("canal")
                    preco_venda_unitario = contexto.get("preco_venda_unitario")

        if canal:
            registros.append(
                {
                    "canal": canal,
                    "quantidade": mov.quantidade,
                    "preco_venda_unitario": preco_venda_unitario,
                }
            )

    return {"vendas_por_canal": _agrupar_vendas_por_canal(registros)}


@router.get("/produto/{produto_id}/reservas-ativas")
def listar_reservas_ativas_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    logger.info("Listando reservas ativas do produto %s", produto_id)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
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
