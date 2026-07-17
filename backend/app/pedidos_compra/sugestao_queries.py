from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import Cliente, FornecedorGrupo
from ..produtos_models import EstoqueMovimentacao, GranelConversao, Produto
from ..vendas_models import Venda, VendaItem
from .sugestao import (
    JANELAS_GIRO_SUGESTAO,
    _datetime_naive_utc_sugestao,
    _float_seguro_sugestao,
    _montar_resultado_vendas_sugestao,
    _nova_stats_venda_sugestao,
    _somar_conversoes_granel_rows_sugestao,
    _somar_movimentacoes_complementares_sugestao,
    _somar_vendas_rows_sugestao,
)


logger = logging.getLogger(__name__)


def _filtro_ativo_ou_legado_sugestao(coluna_ativo):
    """Inclui registros ativos e cadastros legados sem flag de atividade."""
    return or_(coluna_ativo.is_(True), coluna_ativo.is_(None))


def _resolver_fornecedores_compra(
    db: Session,
    tenant_id,
    fornecedor: Cliente,
    incluir_grupo_fornecedor: bool = False,
    fornecedor_grupo_id: Optional[int] = None,
) -> tuple[List[int], Optional[FornecedorGrupo]]:
    """Resolve quais CNPJs devem entrar na operacao de compra."""
    grupo = None

    if fornecedor_grupo_id:
        grupo = (
            db.query(FornecedorGrupo)
            .filter(
                FornecedorGrupo.id == fornecedor_grupo_id,
                FornecedorGrupo.tenant_id == tenant_id,
                FornecedorGrupo.ativo.is_(True),
            )
            .first()
        )
        if not grupo:
            raise HTTPException(
                status_code=404, detail="Grupo de fornecedor nao encontrado"
            )
    elif incluir_grupo_fornecedor and fornecedor.fornecedor_grupo_id:
        grupo = (
            db.query(FornecedorGrupo)
            .filter(
                FornecedorGrupo.id == fornecedor.fornecedor_grupo_id,
                FornecedorGrupo.tenant_id == tenant_id,
                FornecedorGrupo.ativo.is_(True),
            )
            .first()
        )

    if not grupo:
        return [fornecedor.id], None

    fornecedores_grupo = (
        db.query(Cliente.id)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
            Cliente.fornecedor_grupo_id == grupo.id,
        )
        .all()
    )
    fornecedor_ids = sorted(
        {linha[0] for linha in fornecedores_grupo} | {fornecedor.id}
    )

    return fornecedor_ids, grupo


def _carregar_vendas_sugestao(
    db: Session,
    tenant_id,
    produto_ids: List[int],
    periodo_dias: int,
    data_fim: datetime,
) -> dict:
    """Carrega giro por produto usando vendas como fonte principal e estoque como complemento."""
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    if not produto_ids:
        return {}

    data_fim = _datetime_naive_utc_sugestao(data_fim) or datetime.utcnow()
    ids_busca = sorted(set(produto_ids))

    dias_busca = max(periodo_dias, max(JANELAS_GIRO_SUGESTAO))
    data_inicio_busca = data_fim - timedelta(days=dias_busca)
    data_inicio_periodo = data_fim - timedelta(days=periodo_dias)
    venda_data = func.coalesce(
        Venda.data_finalizacao, Venda.data_venda, Venda.created_at
    )

    vendas_rows = (
        db.query(
            VendaItem.produto_id,
            Venda.id.label("venda_id"),
            Venda.canal,
            venda_data.label("data_ref"),
            VendaItem.quantidade,
        )
        .join(Venda, VendaItem.venda_id == Venda.id)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id.in_(ids_busca),
            VendaItem.tipo == "produto",
            Venda.status.notin_(["cancelada", "devolvida"]),
            venda_data >= data_inicio_busca,
            venda_data <= data_fim,
        )
        .all()
    )

    pares_venda_produto = _somar_vendas_rows_sugestao(
        stats_por_produto,
        produto_ids,
        vendas_rows,
        data_inicio_periodo,
        data_fim,
    )

    conversoes_rows = (
        db.query(GranelConversao, Produto)
        .join(Produto, GranelConversao.produto_granel_id == Produto.id)
        .filter(
            GranelConversao.tenant_id == tenant_id,
            GranelConversao.produto_origem_id.in_(produto_ids),
            GranelConversao.status == "confirmado",
            GranelConversao.created_at >= data_inicio_busca,
            GranelConversao.created_at <= data_fim,
        )
        .all()
    )

    _somar_conversoes_granel_rows_sugestao(
        stats_por_produto,
        conversoes_rows,
        data_inicio_periodo,
        data_fim,
    )

    filtro_movimentacao_venda = or_(
        EstoqueMovimentacao.referencia_tipo.in_(["venda", "venda_bling"]),
        EstoqueMovimentacao.motivo.ilike("venda%"),
    )
    movimentos_rows = (
        db.query(
            EstoqueMovimentacao.produto_id,
            EstoqueMovimentacao.referencia_id,
            EstoqueMovimentacao.referencia_tipo,
            EstoqueMovimentacao.motivo,
            EstoqueMovimentacao.created_at,
            EstoqueMovimentacao.quantidade,
        )
        .filter(
            EstoqueMovimentacao.produto_id.in_(ids_busca),
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
            EstoqueMovimentacao.created_at >= data_inicio_busca,
            EstoqueMovimentacao.created_at <= data_fim,
            filtro_movimentacao_venda,
        )
        .all()
    )

    referencias_venda = {
        int(row.referencia_id)
        for row in movimentos_rows
        if row.referencia_id
        and str(row.referencia_tipo or "").strip().lower() == "venda"
    }
    vendas_referenciadas_validas = set()
    if referencias_venda:
        vendas_referenciadas_validas = {
            int(venda_id)
            for (venda_id,) in (
                db.query(Venda.id)
                .filter(
                    Venda.tenant_id == tenant_id,
                    Venda.id.in_(referencias_venda),
                    Venda.status.notin_(["cancelada", "devolvida"]),
                )
                .all()
            )
        }

    _somar_movimentacoes_complementares_sugestao(
        stats_por_produto,
        movimentos_rows,
        pares_venda_produto,
        vendas_referenciadas_validas,
        data_inicio_periodo,
        data_fim,
    )

    return _montar_resultado_vendas_sugestao(stats_por_produto)


def _agrupar_movimentacoes_estoque_periodo(
    db: Session,
    tenant_id,
    produto_ids: List[int],
    data_inicio: datetime,
    data_fim: datetime,
) -> dict:
    if not produto_ids:
        return {}

    rows = (
        db.query(
            EstoqueMovimentacao.produto_id,
            EstoqueMovimentacao.created_at,
            EstoqueMovimentacao.tipo,
            EstoqueMovimentacao.quantidade,
            EstoqueMovimentacao.quantidade_anterior,
            EstoqueMovimentacao.quantidade_nova,
        )
        .filter(
            EstoqueMovimentacao.produto_id.in_(produto_ids),
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.status != "cancelado",
            EstoqueMovimentacao.created_at >= data_inicio,
            EstoqueMovimentacao.created_at <= data_fim,
        )
        .order_by(EstoqueMovimentacao.produto_id, EstoqueMovimentacao.created_at)
        .all()
    )

    agrupado = defaultdict(list)
    for row in rows:
        agrupado[int(row.produto_id)].append(row)
    return agrupado


def _obter_estoque_atual_sugestao(
    db: Session, produto: Produto, tenant_id
) -> tuple[float, dict]:
    estoque_atual = _float_seguro_sugestao(produto.estoque_atual)
    info = {
        "estoque_derivado": False,
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
    }

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        try:
            from ..services.kit_estoque_service import KitEstoqueService

            estoque_atual = _float_seguro_sugestao(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=tenant_id,
                )
            )
            info["estoque_derivado"] = True
        except Exception as exc:
            logger.warning(
                "Nao foi possivel calcular estoque virtual do produto %s: %s",
                produto.id,
                exc,
            )

    return estoque_atual, info
