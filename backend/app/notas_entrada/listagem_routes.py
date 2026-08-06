"""Listagem paginada e resumida das notas fiscais de entrada."""

import math
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.schemas import (
    NotaEntradaListagemResponse,
    NotaEntradaResponse,
)
from app.produtos_models import NotaEntrada, NotaEntradaItem

router = APIRouter()


def _serializar_nota_listagem(
    nota: NotaEntrada, divergencias_count: int = 0
) -> NotaEntradaResponse:
    return NotaEntradaResponse.model_validate(
        {
            "id": nota.id,
            "numero_nota": nota.numero_nota,
            "serie": nota.serie,
            "chave_acesso": nota.chave_acesso,
            "fornecedor_nome": nota.fornecedor_nome,
            "fornecedor_cnpj": nota.fornecedor_cnpj,
            "fornecedor_id": nota.fornecedor_id,
            "data_emissao": nota.data_emissao,
            "valor_total": nota.valor_total,
            "status": nota.status,
            "produtos_vinculados": nota.produtos_vinculados,
            "produtos_nao_vinculados": nota.produtos_nao_vinculados,
            "entrada_estoque_realizada": nota.entrada_estoque_realizada,
            "conferencia_status": nota.conferencia_status or "nao_iniciada",
            "divergencias_count": divergencias_count,
        }
    )


def _aplicar_filtros_listagem(
    query,
    *,
    status: Optional[str],
    fornecedor: Optional[str],
    nf: Optional[str],
    data_inicio: Optional[date],
    data_fim: Optional[date],
    conferencia: Optional[str],
):
    if status:
        query = query.filter(NotaEntrada.status == status)

    fornecedor_busca = (fornecedor or "").strip()
    if fornecedor_busca:
        padrao_fornecedor = f"%{fornecedor_busca}%"
        query = query.filter(
            or_(
                NotaEntrada.fornecedor_nome.ilike(padrao_fornecedor),
                NotaEntrada.fornecedor_cnpj.ilike(padrao_fornecedor),
            )
        )

    nf_busca = (nf or "").strip()
    if nf_busca:
        padrao_nf = f"%{nf_busca}%"
        query = query.filter(
            or_(
                NotaEntrada.numero_nota.ilike(padrao_nf),
                NotaEntrada.chave_acesso.ilike(padrao_nf),
            )
        )

    if data_inicio:
        query = query.filter(
            NotaEntrada.data_emissao >= datetime.combine(data_inicio, time.min)
        )
    if data_fim:
        query = query.filter(
            NotaEntrada.data_emissao
            < datetime.combine(data_fim + timedelta(days=1), time.min)
        )

    if conferencia:
        query = query.filter(
            func.coalesce(NotaEntrada.conferencia_status, "nao_iniciada") == conferencia
        )

    return query


def _carregar_metricas_listagem(db: Session, tenant_id) -> dict:
    total, pendentes, conciliadas, com_erro, valor_conciliado = (
        db.query(
            func.count(NotaEntrada.id),
            func.coalesce(
                func.sum(case((NotaEntrada.status == "pendente", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((NotaEntrada.status == "processada", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((NotaEntrada.status == "erro", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (NotaEntrada.status == "processada", NotaEntrada.valor_total),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .filter(NotaEntrada.tenant_id == tenant_id)
        .one()
    )

    return {
        "total_notas": int(total or 0),
        "pendentes": int(pendentes or 0),
        "conciliadas": int(conciliadas or 0),
        "com_erro": int(com_erro or 0),
        "valor_conciliado": float(valor_conciliado or 0),
    }


@router.get("/listagem", response_model=NotaEntradaListagemResponse)
def listar_notas_paginadas(
    status: Optional[str] = Query(
        None, pattern="^(pendente|processada|erro|cancelada)$"
    ),
    fornecedor: Optional[str] = Query(None, max_length=255),
    nf: Optional[str] = Query(None, max_length=100),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    conferencia: Optional[str] = Query(
        None, pattern="^(nao_iniciada|sem_divergencia|com_divergencia)$"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista notas com filtros no banco, métricas globais e paginação."""
    _user, tenant_id = user_and_tenant

    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=422,
            detail="A data inicial não pode ser posterior à data final.",
        )

    query = db.query(NotaEntrada).filter(NotaEntrada.tenant_id == tenant_id)
    query = _aplicar_filtros_listagem(
        query,
        status=status,
        fornecedor=fornecedor,
        nf=nf,
        data_inicio=data_inicio,
        data_fim=data_fim,
        conferencia=conferencia,
    )

    total = query.count()
    pages = max(math.ceil(total / page_size), 1)
    pagina_efetiva = min(page, pages)

    notas = (
        query.order_by(desc(NotaEntrada.data_entrada), desc(NotaEntrada.id))
        .offset((pagina_efetiva - 1) * page_size)
        .limit(page_size)
        .all()
    )

    divergencias_por_nota = {}
    nota_ids = [nota.id for nota in notas]
    if nota_ids:
        divergencias_por_nota = dict(
            db.query(
                NotaEntradaItem.nota_entrada_id,
                func.count(NotaEntradaItem.id),
            )
            .filter(
                NotaEntradaItem.tenant_id == tenant_id,
                NotaEntradaItem.nota_entrada_id.in_(nota_ids),
                NotaEntradaItem.quantidade_conferida.isnot(None),
                NotaEntradaItem.quantidade_conferida < NotaEntradaItem.quantidade,
            )
            .group_by(NotaEntradaItem.nota_entrada_id)
            .all()
        )

    return NotaEntradaListagemResponse(
        items=[
            _serializar_nota_listagem(nota, int(divergencias_por_nota.get(nota.id, 0)))
            for nota in notas
        ],
        total=total,
        page=pagina_efetiva,
        page_size=page_size,
        pages=pages,
        metricas=_carregar_metricas_listagem(db, tenant_id),
    )
