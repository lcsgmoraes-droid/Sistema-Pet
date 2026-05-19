"""Rotas de extrato realizado para atendimentos veterinarios."""

from __future__ import annotations

from io import BytesIO
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .produtos_models import Produto
from .veterinario_core import _get_tenant
from .veterinario_extratos import (
    coletar_produto_ids_extrato,
    gerar_excel_extrato_bytes,
    gerar_pdf_extrato_bytes,
    montar_extrato_atendimento,
    normalizar_colunas_extrato,
)
from .veterinario_internacao import _separar_evolucoes_e_procedimentos
from .veterinario_models import ConsultaVet, EvolucaoInternacao, InternacaoVet, ProcedimentoConsulta


router = APIRouter(tags=["Veterinario - Extratos"])


def _content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'


def _consulta_or_none(db: Session, tenant_id, consulta_id: Optional[int]) -> Optional[ConsultaVet]:
    if not consulta_id:
        return None
    return (
        db.query(ConsultaVet)
        .options(
            joinedload(ConsultaVet.pet),
            joinedload(ConsultaVet.cliente),
            joinedload(ConsultaVet.veterinario),
        )
        .filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id)
        .first()
    )


def _internacoes_atendimento(
    db: Session,
    tenant_id,
    *,
    consulta_id: Optional[int],
    internacao_id: Optional[int],
) -> list[InternacaoVet]:
    query = (
        db.query(InternacaoVet)
        .options(joinedload(InternacaoVet.pet), joinedload(InternacaoVet.veterinario))
        .filter(InternacaoVet.tenant_id == tenant_id)
    )
    if internacao_id:
        query = query.filter(InternacaoVet.id == internacao_id)
    elif consulta_id:
        query = query.filter(InternacaoVet.consulta_id == consulta_id)
    else:
        return []
    return query.order_by(InternacaoVet.data_entrada.asc(), InternacaoVet.id.asc()).all()


def _procedimentos_consulta(db: Session, tenant_id, consulta_id: Optional[int]) -> list[ProcedimentoConsulta]:
    if not consulta_id:
        return []
    return (
        db.query(ProcedimentoConsulta)
        .filter(
            ProcedimentoConsulta.consulta_id == consulta_id,
            ProcedimentoConsulta.tenant_id == tenant_id,
        )
        .order_by(ProcedimentoConsulta.created_at.asc(), ProcedimentoConsulta.id.asc())
        .all()
    )


def _procedimentos_internacao(db: Session, tenant_id, internacoes: list[InternacaoVet]) -> list[dict]:
    if not internacoes:
        return []
    internacao_ids = [item.id for item in internacoes]
    registros = (
        db.query(EvolucaoInternacao)
        .filter(
            EvolucaoInternacao.tenant_id == tenant_id,
            EvolucaoInternacao.internacao_id.in_(internacao_ids),
        )
        .order_by(EvolucaoInternacao.data_hora.asc(), EvolucaoInternacao.id.asc())
        .all()
    )
    _, procedimentos = _separar_evolucoes_e_procedimentos(registros)
    por_id = {item.id: item for item in internacoes}
    for procedimento in procedimentos:
        internacao = por_id.get(procedimento.get("internacao_id"))
        if internacao:
            procedimento["pet_id"] = internacao.pet_id
            procedimento["consulta_id"] = internacao.consulta_id
        elif procedimento.get("internacao_id") is None:
            evolucao_id = procedimento.get("id")
            registro = next((ev for ev in registros if ev.id == evolucao_id), None)
            if registro:
                procedimento["internacao_id"] = registro.internacao_id
                internacao = por_id.get(registro.internacao_id)
                if internacao:
                    procedimento["pet_id"] = internacao.pet_id
                    procedimento["consulta_id"] = internacao.consulta_id
    return procedimentos


def _produtos_por_id(db: Session, tenant_id, produto_ids: list[int]) -> dict[int, Produto]:
    if not produto_ids:
        return {}
    produtos = (
        db.query(Produto)
        .filter(Produto.tenant_id == str(tenant_id), Produto.id.in_(produto_ids))
        .all()
    )
    return {produto.id: produto for produto in produtos}


def _montar_extrato_route(
    *,
    consulta_id: Optional[int],
    internacao_id: Optional[int],
    colunas: Optional[object],
    db: Session,
    tenant_id,
) -> dict:
    if not consulta_id and not internacao_id:
        raise HTTPException(status_code=422, detail="Informe consulta_id ou internacao_id para gerar o extrato")

    consulta = _consulta_or_none(db, tenant_id, consulta_id)
    if consulta_id and not consulta:
        raise HTTPException(status_code=404, detail="Consulta nao encontrada")

    internacoes = _internacoes_atendimento(
        db,
        tenant_id,
        consulta_id=consulta_id,
        internacao_id=internacao_id,
    )
    if internacao_id and not internacoes:
        raise HTTPException(status_code=404, detail="Internacao nao encontrada")

    procedimentos_consulta = _procedimentos_consulta(db, tenant_id, consulta_id)
    procedimentos_internacao = _procedimentos_internacao(db, tenant_id, internacoes)
    produto_ids = coletar_produto_ids_extrato(
        procedimentos_consulta=procedimentos_consulta,
        procedimentos_internacao=procedimentos_internacao,
    )
    produtos = _produtos_por_id(db, tenant_id, produto_ids)

    return montar_extrato_atendimento(
        consulta=consulta,
        internacoes=internacoes,
        procedimentos_consulta=procedimentos_consulta,
        procedimentos_internacao=procedimentos_internacao,
        produtos_por_id=produtos,
        colunas=colunas,
    )


@router.get("/extratos/atendimento")
def obter_extrato_atendimento(
    consulta_id: Optional[int] = Query(default=None),
    internacao_id: Optional[int] = Query(default=None),
    colunas: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return _montar_extrato_route(
        consulta_id=consulta_id,
        internacao_id=internacao_id,
        colunas=colunas,
        db=db,
        tenant_id=tenant_id,
    )


@router.get("/extratos/atendimento/export.xlsx")
def exportar_extrato_atendimento_excel(
    consulta_id: Optional[int] = Query(default=None),
    internacao_id: Optional[int] = Query(default=None),
    colunas: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    colunas_exportacao = normalizar_colunas_extrato(colunas)
    extrato = _montar_extrato_route(
        consulta_id=consulta_id,
        internacao_id=internacao_id,
        colunas=colunas_exportacao,
        db=db,
        tenant_id=tenant_id,
    )
    content = gerar_excel_extrato_bytes(extrato, colunas_exportacao)
    referencia = consulta_id or internacao_id or "atendimento"
    filename = f"extrato_veterinario_{referencia}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/extratos/atendimento/export.pdf")
def exportar_extrato_atendimento_pdf(
    consulta_id: Optional[int] = Query(default=None),
    internacao_id: Optional[int] = Query(default=None),
    colunas: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    colunas_exportacao = normalizar_colunas_extrato(colunas)
    extrato = _montar_extrato_route(
        consulta_id=consulta_id,
        internacao_id=internacao_id,
        colunas=colunas_exportacao,
        db=db,
        tenant_id=tenant_id,
    )
    content = gerar_pdf_extrato_bytes(extrato, colunas_exportacao)
    referencia = consulta_id or internacao_id or "atendimento"
    filename = f"extrato_veterinario_{referencia}.pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(filename)},
    )
