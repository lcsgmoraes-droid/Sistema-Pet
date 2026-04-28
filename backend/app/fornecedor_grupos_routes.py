"""Rotas para grupos comerciais de fornecedores.

Mantem cada fornecedor/CNPJ separado no cadastro, mas permite consolidar
operacoes de compra por um grupo comercial.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente, FornecedorGrupo


router = APIRouter(prefix="/fornecedor-grupos", tags=["Grupos de Fornecedores"])


class FornecedorGrupoBase(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=255)
    descricao: Optional[str] = None
    fornecedor_principal_id: Optional[int] = None
    fornecedor_ids: Optional[List[int]] = None
    ativo: Optional[bool] = None


class FornecedorGrupoCreate(FornecedorGrupoBase):
    nome: str = Field(min_length=2, max_length=255)
    fornecedor_ids: List[int] = Field(default_factory=list)


class FornecedorGrupoUpdate(FornecedorGrupoBase):
    pass


def _normalizar_nome(nome: str) -> str:
    return " ".join(str(nome or "").strip().split())


def _payload_fornecedor(fornecedor: Cliente) -> dict:
    return {
        "id": fornecedor.id,
        "nome": fornecedor.nome,
        "cnpj": fornecedor.cnpj,
        "cpf": fornecedor.cpf,
        "cpf_cnpj": fornecedor.cnpj or fornecedor.cpf,
        "razao_social": fornecedor.razao_social,
        "nome_fantasia": fornecedor.nome_fantasia,
        "ativo": bool(fornecedor.ativo),
        "fornecedor_grupo_id": fornecedor.fornecedor_grupo_id,
    }


def _payload_grupo(db: Session, grupo: FornecedorGrupo, tenant_id) -> dict:
    fornecedores = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.fornecedor_grupo_id == grupo.id,
        )
        .order_by(Cliente.nome)
        .all()
    )

    principal = None
    if grupo.fornecedor_principal_id:
        principal = next(
            (fornecedor for fornecedor in fornecedores if fornecedor.id == grupo.fornecedor_principal_id),
            None,
        )

    return {
        "id": grupo.id,
        "nome": grupo.nome,
        "descricao": grupo.descricao,
        "fornecedor_principal_id": grupo.fornecedor_principal_id,
        "fornecedor_principal_nome": principal.nome if principal else None,
        "ativo": bool(grupo.ativo),
        "created_at": grupo.created_at,
        "updated_at": grupo.updated_at,
        "fornecedores": [_payload_fornecedor(fornecedor) for fornecedor in fornecedores],
        "fornecedor_ids": [fornecedor.id for fornecedor in fornecedores],
    }


def _buscar_grupo_ou_404(db: Session, grupo_id: int, tenant_id) -> FornecedorGrupo:
    grupo = (
        db.query(FornecedorGrupo)
        .filter(
            FornecedorGrupo.id == grupo_id,
            FornecedorGrupo.tenant_id == tenant_id,
        )
        .first()
    )
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de fornecedor nao encontrado")
    return grupo


def _buscar_fornecedores_validos(db: Session, fornecedor_ids: List[int], tenant_id) -> List[Cliente]:
    ids_unicos = sorted({int(fornecedor_id) for fornecedor_id in fornecedor_ids if fornecedor_id})
    if not ids_unicos:
        return []

    fornecedores = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.id.in_(ids_unicos),
        )
        .all()
    )
    encontrados = {fornecedor.id for fornecedor in fornecedores}
    faltantes = [fornecedor_id for fornecedor_id in ids_unicos if fornecedor_id not in encontrados]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Fornecedor(es) invalido(s) para este tenant: {', '.join(map(str, faltantes))}",
        )
    return fornecedores


def _aplicar_fornecedores_no_grupo(
    db: Session,
    grupo: FornecedorGrupo,
    fornecedores: List[Cliente],
    tenant_id,
) -> None:
    ids_novos = {fornecedor.id for fornecedor in fornecedores}
    fornecedores_atuais = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.fornecedor_grupo_id == grupo.id,
        )
        .all()
    )

    for fornecedor in fornecedores_atuais:
        if fornecedor.id not in ids_novos:
            fornecedor.fornecedor_grupo_id = None

    for fornecedor in fornecedores:
        fornecedor.fornecedor_grupo_id = grupo.id

    if fornecedores and grupo.fornecedor_principal_id not in ids_novos:
        grupo.fornecedor_principal_id = fornecedores[0].id

    if not fornecedores:
        grupo.fornecedor_principal_id = None


@router.get("/")
def listar_grupos_fornecedores(
    incluir_inativos: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    query = (
        db.query(FornecedorGrupo)
        .filter(FornecedorGrupo.tenant_id == tenant_id)
        .order_by(FornecedorGrupo.nome)
    )
    if not incluir_inativos:
        query = query.filter(FornecedorGrupo.ativo.is_(True))

    grupos = query.all()
    return {
        "items": [_payload_grupo(db, grupo, tenant_id) for grupo in grupos],
        "total": len(grupos),
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def criar_grupo_fornecedor(
    payload: FornecedorGrupoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    fornecedores = _buscar_fornecedores_validos(db, payload.fornecedor_ids or [], tenant_id)
    fornecedor_ids = {fornecedor.id for fornecedor in fornecedores}

    if payload.fornecedor_principal_id and payload.fornecedor_principal_id not in fornecedor_ids:
        raise HTTPException(
            status_code=400,
            detail="Fornecedor principal precisa estar na lista de fornecedores do grupo",
        )

    grupo = FornecedorGrupo(
        tenant_id=tenant_id,
        nome=_normalizar_nome(payload.nome),
        descricao=payload.descricao,
        fornecedor_principal_id=payload.fornecedor_principal_id or (fornecedores[0].id if fornecedores else None),
        ativo=True if payload.ativo is None else payload.ativo,
    )

    try:
        db.add(grupo)
        db.flush()
        _aplicar_fornecedores_no_grupo(db, grupo, fornecedores, tenant_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe um grupo com este nome")

    db.refresh(grupo)
    return _payload_grupo(db, grupo, tenant_id)


@router.patch("/{grupo_id}")
def atualizar_grupo_fornecedor(
    grupo_id: int,
    payload: FornecedorGrupoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    grupo = _buscar_grupo_ou_404(db, grupo_id, tenant_id)
    dados = payload.model_dump(exclude_unset=True)

    fornecedores = None
    if "fornecedor_ids" in dados:
        fornecedores = _buscar_fornecedores_validos(db, dados.get("fornecedor_ids") or [], tenant_id)
        fornecedor_ids = {fornecedor.id for fornecedor in fornecedores}
        principal_id = dados.get("fornecedor_principal_id", grupo.fornecedor_principal_id)
        if principal_id and principal_id not in fornecedor_ids:
            raise HTTPException(
                status_code=400,
                detail="Fornecedor principal precisa estar na lista de fornecedores do grupo",
            )

    if "nome" in dados and dados["nome"] is not None:
        grupo.nome = _normalizar_nome(dados["nome"])
    if "descricao" in dados:
        grupo.descricao = dados["descricao"]
    if "fornecedor_principal_id" in dados:
        grupo.fornecedor_principal_id = dados["fornecedor_principal_id"]
    if "ativo" in dados and dados["ativo"] is not None:
        grupo.ativo = bool(dados["ativo"])
    if fornecedores is not None:
        _aplicar_fornecedores_no_grupo(db, grupo, fornecedores, tenant_id)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe um grupo com este nome")

    db.refresh(grupo)
    return _payload_grupo(db, grupo, tenant_id)


@router.delete("/{grupo_id}")
def excluir_grupo_fornecedor(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    grupo = _buscar_grupo_ou_404(db, grupo_id, tenant_id)

    (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.fornecedor_grupo_id == grupo.id,
        )
        .update({Cliente.fornecedor_grupo_id: None}, synchronize_session=False)
    )
    db.delete(grupo)
    db.commit()

    return {"ok": True, "message": "Grupo de fornecedor excluido"}
