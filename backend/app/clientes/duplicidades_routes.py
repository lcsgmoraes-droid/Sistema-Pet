"""Rotas de duplicidade e fusao de pessoas."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
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
            Cliente.tenant_id == tenant_id, Cliente.cpf == cpf, Cliente.ativo
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
            Cliente.tenant_id == tenant_id, Cliente.cnpj == cnpj, Cliente.ativo
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
            Cliente.tenant_id == tenant_id, Cliente.celular == celular, Cliente.ativo
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
            Cliente.tenant_id == tenant_id, Cliente.telefone == telefone, Cliente.ativo
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
            Cliente.tenant_id == tenant_id, Cliente.crmv == crmv, Cliente.ativo
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
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista possiveis duplicidades de pessoas que exigem revisao manual."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    return listar_sugestoes_duplicidade_pessoas(
        db,
        tenant_id=tenant_id,
        limit=limit,
    )


@router.post("/duplicidades/fundir-automaticas")
@require_permission("clientes.editar")
def executar_fusoes_automaticas_pessoas_route(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Funde automaticamente duplicidades seguras por nome 100% igual."""
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
