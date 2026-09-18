"""Ranking operacional de clientes baseado nas vendas de um periodo."""

from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import _validar_tenant_e_obter_usuario
from app.db import get_session
from app.models import Cliente
from app.security.permissions_decorator import require_permission
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda, VendaItem

router = APIRouter()


def _periodo_padrao() -> tuple[date, date]:
    hoje = now_brasilia().date()
    return hoje.replace(day=1), hoje


def _validar_periodo(data_inicio: date, data_fim: date) -> None:
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=422,
            detail="A data inicial nao pode ser posterior a data final.",
        )
    if (data_fim - data_inicio).days > 3660:
        raise HTTPException(
            status_code=422,
            detail="Selecione um periodo de no maximo 10 anos.",
        )


def _posicoes_por_metrica(clientes: list[dict], metrica: str) -> dict[int, int]:
    ordenados = sorted(
        clientes,
        key=lambda item: (
            item[metrica] or 0,
            item["total_gasto"],
            -item["cliente_id"],
        ),
        reverse=True,
    )
    return {
        cliente["cliente_id"]: indice + 1 for indice, cliente in enumerate(ordenados)
    }


def _montar_resultado_ranking(
    linhas_vendas,
    itens_por_cliente: dict[int, float],
    *,
    ordenar_por: str,
    busca: Optional[str],
    pagina: int,
    por_pagina: int,
) -> dict:
    clientes = []
    for linha in linhas_vendas:
        total_gasto = float(linha.total_gasto or 0)
        total_compras = int(linha.total_compras or 0)
        total_itens = float(itens_por_cliente.get(linha.cliente_id, 0) or 0)
        clientes.append(
            {
                "cliente_id": linha.cliente_id,
                "codigo": linha.codigo,
                "nome": linha.nome,
                "telefone": linha.telefone or linha.celular,
                "total_gasto": round(total_gasto, 2),
                "total_compras": total_compras,
                "total_itens": round(total_itens, 3),
                "ticket_medio": round(
                    total_gasto / total_compras if total_compras else 0,
                    2,
                ),
                "ultima_compra": (
                    linha.ultima_compra.isoformat() if linha.ultima_compra else None
                ),
            }
        )

    posicoes = {
        metrica: _posicoes_por_metrica(clientes, metrica)
        for metrica in ("total_gasto", "total_compras", "total_itens", "ticket_medio")
    }
    for cliente in clientes:
        cliente["posicoes"] = {
            metrica: mapa[cliente["cliente_id"]] for metrica, mapa in posicoes.items()
        }

    lideres = {
        metrica: min(
            clientes,
            key=lambda item: item["posicoes"][metrica],
            default=None,
        )
        for metrica in ("total_gasto", "total_compras", "total_itens")
    }
    resumo = {
        "clientes_com_compra": len(clientes),
        "faturamento_clientes": round(
            sum(cliente["total_gasto"] for cliente in clientes), 2
        ),
        "total_compras": sum(cliente["total_compras"] for cliente in clientes),
        "total_itens": round(sum(cliente["total_itens"] for cliente in clientes), 3),
    }

    termo = (busca or "").strip().casefold()
    if termo:
        clientes = [
            cliente
            for cliente in clientes
            if termo
            in " ".join(
                str(valor or "")
                for valor in (
                    cliente["nome"],
                    cliente["codigo"],
                    cliente["telefone"],
                )
            ).casefold()
        ]

    if ordenar_por == "ultima_compra":
        clientes.sort(
            key=lambda item: (
                item["ultima_compra"] or "",
                item["total_gasto"],
                -item["cliente_id"],
            ),
            reverse=True,
        )
    else:
        clientes.sort(
            key=lambda item: (
                item[ordenar_por] or 0,
                item["total_gasto"],
                -item["cliente_id"],
            ),
            reverse=True,
        )
    total_filtrado = len(clientes)
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina

    return {
        "resumo": resumo,
        "lideres": lideres,
        "clientes": clientes[inicio:fim],
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_filtrado,
            "total_paginas": max(1, ceil(total_filtrado / por_pagina)),
        },
    }


@router.get("/ranking-vendas")
@require_permission("clientes.visualizar")
def listar_ranking_clientes(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    ordenar_por: Literal[
        "total_gasto",
        "total_compras",
        "total_itens",
        "ticket_medio",
        "ultima_compra",
    ] = "total_gasto",
    busca: Optional[str] = Query(None, max_length=120),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o ranking de clientes calculado diretamente sobre vendas finalizadas."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    inicio_padrao, fim_padrao = _periodo_padrao()
    data_inicio = data_inicio or inicio_padrao
    data_fim = data_fim or fim_padrao
    _validar_periodo(data_inicio, data_fim)

    inicio_dt = datetime.combine(data_inicio, time.min)
    fim_exclusivo = datetime.combine(data_fim + timedelta(days=1), time.min)
    filtros_venda = (
        Venda.tenant_id == tenant_id,
        Venda.status == "finalizada",
        Venda.cliente_id.isnot(None),
        Venda.data_venda >= inicio_dt,
        Venda.data_venda < fim_exclusivo,
    )

    linhas_vendas = (
        db.query(
            Venda.cliente_id.label("cliente_id"),
            Cliente.codigo.label("codigo"),
            Cliente.nome.label("nome"),
            Cliente.telefone.label("telefone"),
            Cliente.celular.label("celular"),
            func.sum(Venda.total).label("total_gasto"),
            func.count(Venda.id).label("total_compras"),
            func.max(Venda.data_venda).label("ultima_compra"),
        )
        .join(
            Cliente,
            (Cliente.id == Venda.cliente_id) & (Cliente.tenant_id == tenant_id),
        )
        .filter(*filtros_venda)
        .group_by(
            Venda.cliente_id,
            Cliente.codigo,
            Cliente.nome,
            Cliente.telefone,
            Cliente.celular,
        )
        .all()
    )

    linhas_itens = (
        db.query(
            Venda.cliente_id.label("cliente_id"),
            func.sum(VendaItem.quantidade).label("total_itens"),
        )
        .join(VendaItem, VendaItem.venda_id == Venda.id)
        .filter(*filtros_venda, VendaItem.tenant_id == tenant_id)
        .group_by(Venda.cliente_id)
        .all()
    )
    itens_por_cliente = {
        linha.cliente_id: float(linha.total_itens or 0) for linha in linhas_itens
    }

    resultado = _montar_resultado_ranking(
        linhas_vendas,
        itens_por_cliente,
        ordenar_por=ordenar_por,
        busca=busca,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    resultado["periodo"] = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }
    resultado["ordenar_por"] = ordenar_por
    return resultado
