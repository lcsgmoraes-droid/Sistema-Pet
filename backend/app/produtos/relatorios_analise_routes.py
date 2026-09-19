"""Analise comercial consolidada de produtos."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos.relatorios import _parse_relatorio_datetime
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Categoria, Departamento, Marca, Produto
from app.security.permissions_decorator import require_permission
from app.vendas_models import Venda, VendaItem

router = APIRouter()


def _variacao_percentual(atual: float, anterior: float) -> Optional[float]:
    """Calcula a variacao; ``None`` indica ausencia de base comparavel."""

    if anterior == 0:
        return 0.0 if atual == 0 else None
    return round(((atual - anterior) / abs(anterior)) * 100, 2)


def _aplicar_curva_abc(
    produtos: list[dict[str, Any]], campo: str, prefixo: str
) -> None:
    """Classifica produtos em A (80%), B (15%) e C (5%) in-place.

    O item que cruza um limite permanece na classe iniciada antes dele. Isso
    evita uma curva sem classe A quando um unico produto representa mais de
    80% do resultado.
    """

    ordenados = sorted(
        produtos, key=lambda item: max(float(item.get(campo) or 0), 0), reverse=True
    )
    total = sum(max(float(item.get(campo) or 0), 0) for item in ordenados)
    acumulado = 0.0

    for item in ordenados:
        participacao_anterior = (acumulado / total * 100) if total else 0.0
        if total == 0:
            classe = "C"
        elif participacao_anterior < 80:
            classe = "A"
        elif participacao_anterior < 95:
            classe = "B"
        else:
            classe = "C"

        acumulado += max(float(item.get(campo) or 0), 0)
        item[f"abc_{prefixo}"] = classe
        item[f"acumulado_{prefixo}_pct"] = round(
            (acumulado / total * 100) if total else 0, 2
        )


def _preencher_evolucao(
    inicio: datetime, fim: datetime, linhas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Completa os dias sem venda para manter a serie temporal continua."""

    por_data = {str(item["data"]): item for item in linhas}
    resultado = []
    cursor = inicio.date()
    while cursor <= fim.date():
        chave = cursor.isoformat()
        item = por_data.get(chave, {})
        resultado.append(
            {
                "data": chave,
                "faturamento": round(float(item.get("faturamento") or 0), 2),
                "quantidade": round(float(item.get("quantidade") or 0), 3),
                "lucro_estimado": round(float(item.get("lucro_estimado") or 0), 2),
            }
        )
        cursor += timedelta(days=1)
    return resultado


def _normalizar_periodo(
    data_inicio: Optional[str], data_fim: Optional[str]
) -> tuple[datetime, datetime]:
    fim = _parse_relatorio_datetime(
        data_fim, end_of_day=True
    ) or datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    inicio = _parse_relatorio_datetime(data_inicio) or (
        fim - timedelta(days=29)
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    if data_inicio and _parse_relatorio_datetime(data_inicio) is None:
        raise HTTPException(status_code=400, detail="Data inicial invalida.")
    if data_fim and _parse_relatorio_datetime(data_fim, end_of_day=True) is None:
        raise HTTPException(status_code=400, detail="Data final invalida.")
    if inicio > fim:
        raise HTTPException(
            status_code=400, detail="A data inicial deve ser anterior a data final."
        )
    if (fim.date() - inicio.date()).days > 730:
        raise HTTPException(
            status_code=400, detail="O periodo maximo para analise e de 731 dias."
        )
    return inicio, fim


def _filtros_base(
    query,
    *,
    tenant_id,
    access_ids,
    inicio: datetime,
    fim: datetime,
    categoria_id: Optional[int],
    marca_id: Optional[int],
    departamento_id: Optional[int],
    fornecedor_id: Optional[int],
    canal: Optional[str],
    busca: Optional[str],
):
    query = query.filter(
        Venda.tenant_id == tenant_id,
        VendaItem.tenant_id == tenant_id,
        Produto.tenant_id.in_(access_ids),
        VendaItem.tipo == "produto",
        VendaItem.produto_id.isnot(None),
        ~func.lower(Venda.status).in_(
            ["cancelada", "cancelado", "devolvida", "devolvido"]
        ),
        Venda.data_venda >= inicio,
        Venda.data_venda <= fim,
    )
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    if departamento_id:
        query = query.filter(Produto.departamento_id == departamento_id)
    if fornecedor_id:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if canal:
        query = query.filter(Venda.canal == canal)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                Produto.codigo_barras.ilike(termo),
            )
        )
    return query


def _consultar_produtos(
    db: Session,
    *,
    tenant_id,
    access_ids,
    inicio: datetime,
    fim: datetime,
    filtros: dict[str, Any],
) -> list[dict[str, Any]]:
    quantidade = func.coalesce(func.sum(VendaItem.quantidade), 0)
    faturamento = func.coalesce(func.sum(VendaItem.subtotal), 0)
    custo = func.coalesce(
        func.sum(VendaItem.quantidade * func.coalesce(Produto.preco_custo, 0)), 0
    )

    query = (
        db.query(
            Produto.id.label("produto_id"),
            Produto.nome.label("produto_nome"),
            Produto.codigo.label("codigo"),
            Produto.codigo_barras.label("codigo_barras"),
            Categoria.id.label("categoria_id"),
            Categoria.nome.label("categoria_nome"),
            Marca.id.label("marca_id"),
            Marca.nome.label("marca_nome"),
            Departamento.id.label("departamento_id"),
            Departamento.nome.label("departamento_nome"),
            Cliente.id.label("fornecedor_id"),
            Cliente.nome.label("fornecedor_nome"),
            Produto.estoque_atual.label("estoque_atual"),
            Produto.estoque_minimo.label("estoque_minimo"),
            Produto.preco_custo.label("preco_custo"),
            Produto.preco_venda.label("preco_venda"),
            quantidade.label("quantidade"),
            faturamento.label("faturamento"),
            custo.label("custo_estimado"),
            func.count(func.distinct(Venda.id)).label("vendas"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(Produto, Produto.id == VendaItem.produto_id)
        .outerjoin(Categoria, Categoria.id == Produto.categoria_id)
        .outerjoin(Marca, Marca.id == Produto.marca_id)
        .outerjoin(Departamento, Departamento.id == Produto.departamento_id)
        .outerjoin(Cliente, Cliente.id == Produto.fornecedor_id)
    )
    query = _filtros_base(
        query,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=inicio,
        fim=fim,
        **filtros,
    )
    rows = query.group_by(
        Produto.id,
        Categoria.id,
        Categoria.nome,
        Marca.id,
        Marca.nome,
        Departamento.id,
        Departamento.nome,
        Cliente.id,
        Cliente.nome,
    ).all()

    dias = max((fim.date() - inicio.date()).days + 1, 1)
    resultado = []
    for row in rows:
        item = dict(row._mapping)
        qtd = float(item["quantidade"] or 0)
        receita = float(item["faturamento"] or 0)
        custo_estimado = float(item["custo_estimado"] or 0)
        lucro = receita - custo_estimado
        media_diaria = qtd / dias
        estoque = float(item["estoque_atual"] or 0)
        item.update(
            quantidade=round(qtd, 3),
            faturamento=round(receita, 2),
            custo_estimado=round(custo_estimado, 2),
            lucro_estimado=round(lucro, 2),
            margem_estimada_pct=round((lucro / receita * 100) if receita else 0, 2),
            ticket_unitario=round((receita / qtd) if qtd else 0, 2),
            media_diaria=round(media_diaria, 3),
            cobertura_estoque_dias=(
                round(max(estoque, 0) / media_diaria, 1) if media_diaria > 0 else None
            ),
            estoque_atual=round(estoque, 3),
            estoque_minimo=round(float(item["estoque_minimo"] or 0), 3),
            preco_custo=round(float(item["preco_custo"] or 0), 2),
            preco_venda=round(float(item["preco_venda"] or 0), 2),
            vendas=int(item["vendas"] or 0),
        )
        resultado.append(item)
    return resultado


def _resumir(produtos: list[dict[str, Any]]) -> dict[str, Any]:
    faturamento = sum(float(item["faturamento"]) for item in produtos)
    quantidade = sum(float(item["quantidade"]) for item in produtos)
    custo = sum(float(item["custo_estimado"]) for item in produtos)
    lucro = faturamento - custo
    return {
        "faturamento": round(faturamento, 2),
        "quantidade": round(quantidade, 3),
        "produtos_vendidos": len(produtos),
        "vendas": 0,
        "custo_estimado": round(custo, 2),
        "lucro_estimado": round(lucro, 2),
        "margem_estimada_pct": round(
            (lucro / faturamento * 100) if faturamento else 0, 2
        ),
    }


def _contar_vendas(
    db: Session,
    *,
    tenant_id,
    access_ids,
    inicio: datetime,
    fim: datetime,
    filtros: dict[str, Any],
) -> int:
    query = (
        db.query(func.count(func.distinct(Venda.id)))
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(Produto, Produto.id == VendaItem.produto_id)
    )
    query = _filtros_base(
        query,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=inicio,
        fim=fim,
        **filtros,
    )
    return int(query.scalar() or 0)


@router.get("/relatorio/analise-vendas")
@require_permission("produtos.visualizar")
def relatorio_analise_vendas(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    canal: Optional[str] = None,
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Entrega uma fonte unica para visao geral, ABC e agrupamentos."""

    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    inicio, fim = _normalizar_periodo(data_inicio, data_fim)
    dias = (fim.date() - inicio.date()).days + 1
    comparacao_fim = inicio - timedelta(microseconds=1)
    comparacao_inicio = comparacao_fim.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=dias - 1)
    filtros = {
        "categoria_id": categoria_id,
        "marca_id": marca_id,
        "departamento_id": departamento_id,
        "fornecedor_id": fornecedor_id,
        "canal": canal,
        "busca": busca,
    }

    produtos = _consultar_produtos(
        db,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=inicio,
        fim=fim,
        filtros=filtros,
    )
    anteriores = _consultar_produtos(
        db,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=comparacao_inicio,
        fim=comparacao_fim,
        filtros=filtros,
    )
    anteriores_por_id = {item["produto_id"]: item for item in anteriores}

    _aplicar_curva_abc(produtos, "faturamento", "faturamento")
    _aplicar_curva_abc(produtos, "quantidade", "quantidade")
    for item in produtos:
        anterior = anteriores_por_id.get(item["produto_id"], {})
        item["comparacao"] = {
            "faturamento": float(anterior.get("faturamento") or 0),
            "quantidade": float(anterior.get("quantidade") or 0),
        }
        item["variacao_faturamento_pct"] = _variacao_percentual(
            item["faturamento"], item["comparacao"]["faturamento"]
        )
        item["variacao_quantidade_pct"] = _variacao_percentual(
            item["quantidade"], item["comparacao"]["quantidade"]
        )

    quantidade = func.coalesce(func.sum(VendaItem.quantidade), 0)
    faturamento = func.coalesce(func.sum(VendaItem.subtotal), 0)
    custo = func.coalesce(
        func.sum(VendaItem.quantidade * func.coalesce(Produto.preco_custo, 0)), 0
    )
    diaria = (
        db.query(
            func.date(Venda.data_venda).label("data"),
            quantidade.label("quantidade"),
            faturamento.label("faturamento"),
            (faturamento - custo).label("lucro_estimado"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(Produto, Produto.id == VendaItem.produto_id)
    )
    diaria = _filtros_base(
        diaria,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=inicio,
        fim=fim,
        **filtros,
    )
    linhas_diarias = [
        {
            "data": row.data.isoformat(),
            "quantidade": float(row.quantidade or 0),
            "faturamento": float(row.faturamento or 0),
            "lucro_estimado": float(row.lucro_estimado or 0),
        }
        for row in diaria.group_by(func.date(Venda.data_venda))
        .order_by(func.date(Venda.data_venda))
        .all()
    ]

    resumo = _resumir(produtos)
    comparacao = _resumir(anteriores)
    resumo["vendas"] = _contar_vendas(
        db,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=inicio,
        fim=fim,
        filtros=filtros,
    )
    comparacao["vendas"] = _contar_vendas(
        db,
        tenant_id=tenant_id,
        access_ids=access_ids,
        inicio=comparacao_inicio,
        fim=comparacao_fim,
        filtros=filtros,
    )
    resumo["comparacao"] = comparacao
    resumo["variacoes"] = {
        chave: _variacao_percentual(float(resumo[chave]), float(comparacao[chave]))
        for chave in (
            "faturamento",
            "quantidade",
            "produtos_vendidos",
            "lucro_estimado",
        )
    }

    return {
        "periodo": {
            "inicio": inicio.date().isoformat(),
            "fim": fim.date().isoformat(),
            "dias": dias,
            "comparacao_inicio": comparacao_inicio.date().isoformat(),
            "comparacao_fim": comparacao_fim.date().isoformat(),
        },
        "resumo": resumo,
        "evolucao": _preencher_evolucao(inicio, fim, linhas_diarias),
        "produtos": sorted(
            produtos, key=lambda item: item["faturamento"], reverse=True
        ),
        "metadados": {
            "lucro_estimado": "Receita dos itens menos o custo atual cadastrado do produto.",
            "curva_abc": "Ate 80% acumulado: A; de 80% a 95%: B; restante: C.",
        },
    }
