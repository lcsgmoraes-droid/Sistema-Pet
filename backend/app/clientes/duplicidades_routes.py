"""Rotas de duplicidade e fusao de pessoas."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente, PessoaMergeLog
from app.clientes.common import _somente_digitos_coluna
from app.security.permissions_decorator import require_permission
from app.services.pessoa_duplicate_service import (
    executar_fusoes_automaticas_pessoas_duplicadas,
    listar_sugestoes_duplicidade_pessoas,
)
from app.services.pessoa_merge_service import (
    executar_fusao_pessoas,
    montar_preview_fusao_pessoas,
)
from app.clientes.schemas import (
    PessoaFusaoExecutarRequest,
    PessoaFusaoPreviewRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _igual_normalizado(campo, valor: str):
    campo_nome = getattr(campo, "key", "")
    if campo_nome in {"cpf", "cnpj", "telefone", "celular"}:
        digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())
        return _somente_digitos_coluna(campo) == digitos
    if campo_nome == "crmv":
        normalizado = "".join(ch for ch in str(valor or "").casefold() if ch.isalnum())
        return (
            func.lower(
                func.replace(
                    func.replace(
                        func.replace(func.replace(campo, "-", ""), "/", ""),
                        ".",
                        "",
                    ),
                    " ",
                    "",
                )
            )
            == normalizado
        )
    return campo == valor


@router.get("/verificar-duplicata/campo", response_model=dict)
def verificar_duplicata(
    cpf: Optional[str] = None,
    cnpj: Optional[str] = None,
    telefone: Optional[str] = None,
    celular: Optional[str] = None,
    crmv: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Verificar se existe cliente com CPF, CNPJ, telefone, celular ou CRMV duplicado"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    resultado = {"duplicado": False, "cliente": None, "campo": None}

    # Verificar CPF
    if cpf:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            _igual_normalizado(Cliente.cpf, cpf),
            Cliente.ativo.is_not(False),
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)

        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "cpf"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "tipo_pessoa": cliente.tipo_pessoa,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email,
            }
            return resultado

    # Verificar CNPJ
    if cnpj:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            _igual_normalizado(Cliente.cnpj, cnpj),
            Cliente.ativo.is_not(False),
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)

        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "cnpj"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "tipo_pessoa": cliente.tipo_pessoa,
                "cnpj": cliente.cnpj,
                "razao_social": cliente.razao_social,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email,
            }
            return resultado

    # Verificar celular
    if celular:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            _igual_normalizado(Cliente.celular, celular),
            Cliente.ativo.is_not(False),
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)

        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "celular"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email,
            }
            return resultado

    # Verificar telefone
    if telefone:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            _igual_normalizado(Cliente.telefone, telefone),
            Cliente.ativo.is_not(False),
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)

        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "telefone"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email,
            }
            return resultado

    # Verificar CRMV
    if crmv:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            _igual_normalizado(Cliente.crmv, crmv),
            Cliente.ativo.is_not(False),
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)

        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "crmv"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "crmv": cliente.crmv,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email,
            }
            return resultado

    return resultado


@router.post("/fusao/preview")
@require_permission("clientes.editar")
def preview_fusao_pessoas(
    payload: PessoaFusaoPreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Prepara a fusao de duas pessoas sem alterar dados."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return montar_preview_fusao_pessoas(
            db,
            tenant_id=tenant_id,
            principal_id=payload.pessoa_principal_id,
            duplicado_id=payload.pessoa_duplicada_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/fusao/executar")
@require_permission("clientes.editar")
def executar_fusao_pessoas_route(
    payload: PessoaFusaoExecutarRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Funde duas pessoas, mantendo o principal e transferindo historico/vinculos."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return executar_fusao_pessoas(
            db,
            tenant_id=tenant_id,
            principal_id=payload.pessoa_principal_id,
            duplicado_id=payload.pessoa_duplicada_id,
            decisoes_campos=payload.decisoes_campos,
            user_id=current_user.id,
            observacao=payload.observacao,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao fundir pessoas")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fundir pessoas: {str(exc)}",
        )


@router.get("/duplicidades/sugestoes")
@require_permission("clientes.visualizar")
def listar_sugestoes_duplicidade_pessoas_route(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista possiveis duplicidades de pessoas que exigem revisao manual."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    return listar_sugestoes_duplicidade_pessoas(
        db,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )


@router.get("/duplicidades/historico")
@require_permission("clientes.visualizar")
def listar_historico_fusoes_pessoas_route(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista a trilha auditavel das fusoes realizadas no tenant."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    logs = (
        db.query(PessoaMergeLog)
        .filter(PessoaMergeLog.tenant_id == tenant_id)
        .order_by(PessoaMergeLog.created_at.desc(), PessoaMergeLog.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "principal_id": item.principal_id,
                "duplicado_id": item.duplicado_id,
                "actor_user_id": item.actor_user_id,
                "modo": item.modo,
                "motivo": item.motivo,
                "status": item.status,
                "resumo_transferencias": item.resumo_transferencias,
                "observacao": item.observacao,
                "created_at": item.created_at,
            }
            for item in logs
        ]
    }


@router.post("/duplicidades/fundir-automaticas")
@require_permission("clientes.editar")
def executar_fusoes_automaticas_pessoas_route(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Funde em lote apenas duplicidades com identidade forte valida em comum."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return executar_fusoes_automaticas_pessoas_duplicadas(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Erro na varredura de duplicidade de pessoas")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar duplicidades: {str(exc)}",
        )
