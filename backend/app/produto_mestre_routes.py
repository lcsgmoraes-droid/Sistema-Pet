"""Rotas de produto-mestre (+ categoria/marca/departamento mestre) — camada
geral do grupo comercial, Checkpoint 2. Aditivo: não altera nenhuma rota
existente de cadastro de produto.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.grupo_comercial_contexto import obter_grupo_id_ativo
from app.produto_mestre_service import (
    desvincular_produto_mestre,
    sugerir_categoria_mestre,
    sugerir_departamento_mestre,
    sugerir_marca_mestre,
    sugerir_produto_mestre,
    vincular_categoria_mestre,
    vincular_departamento_mestre,
    vincular_marca_mestre,
    vincular_produto_mestre,
)
from app.produtos_catalogo_models import Categoria, Departamento, Marca, Produto

router = APIRouter(prefix="/produto-mestre", tags=["Produto mestre"])


class MestreSugestaoResponse(BaseModel):
    id: int
    nome: str


class VincularMestreRequest(BaseModel):
    mestre_id: Optional[int] = None
    """Vincula a este mestre existente do grupo; se omitido, promove o
    próprio registro local a um mestre novo."""


def _grupo_id_ou_erro(db: Session, tenant_id) -> int:
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta loja não tem grupo comercial ativo.",
        )
    return grupo_id


@router.get("/produtos/sugestao", response_model=Optional[MestreSugestaoResponse])
def sugerir_mestre_produto(
    nome: Optional[str] = None,
    gtin: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_produto_mestre(db, grupo_id, nome=nome, gtin=gtin)


@router.post("/produtos/{produto_id}/vincular", response_model=MestreSugestaoResponse)
def vincular_mestre_produto(
    produto_id: int,
    payload: VincularMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado"
        )
    grupo_id = _grupo_id_ou_erro(db, tenant_id)
    mestre = vincular_produto_mestre(
        db,
        produto=produto,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        produto_mestre_id=payload.mestre_id,
    )
    return mestre


@router.delete("/produtos/{produto_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def remover_vinculo_mestre_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado"
        )
    desvincular_produto_mestre(db, produto=produto)
    return None


@router.get("/categorias/sugestao", response_model=Optional[MestreSugestaoResponse])
def sugerir_mestre_categoria(
    nome: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_categoria_mestre(db, grupo_id, nome)


@router.post("/categorias/{categoria_id}/vincular", response_model=MestreSugestaoResponse)
def vincular_mestre_categoria(
    categoria_id: int,
    payload: VincularMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    categoria = (
        db.query(Categoria)
        .filter(Categoria.id == categoria_id, Categoria.tenant_id == tenant_id)
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )
    grupo_id = _grupo_id_ou_erro(db, tenant_id)
    return vincular_categoria_mestre(
        db,
        categoria=categoria,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        mestre_id=payload.mestre_id,
    )


@router.get("/marcas/sugestao", response_model=Optional[MestreSugestaoResponse])
def sugerir_mestre_marca(
    nome: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_marca_mestre(db, grupo_id, nome)


@router.post("/marcas/{marca_id}/vincular", response_model=MestreSugestaoResponse)
def vincular_mestre_marca(
    marca_id: int,
    payload: VincularMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    marca = (
        db.query(Marca)
        .filter(Marca.id == marca_id, Marca.tenant_id == tenant_id)
        .first()
    )
    if not marca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Marca não encontrada"
        )
    grupo_id = _grupo_id_ou_erro(db, tenant_id)
    return vincular_marca_mestre(
        db,
        marca=marca,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        mestre_id=payload.mestre_id,
    )


@router.get("/departamentos/sugestao", response_model=Optional[MestreSugestaoResponse])
def sugerir_mestre_departamento(
    nome: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_departamento_mestre(db, grupo_id, nome)


@router.post(
    "/departamentos/{departamento_id}/vincular", response_model=MestreSugestaoResponse
)
def vincular_mestre_departamento(
    departamento_id: int,
    payload: VincularMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    departamento = (
        db.query(Departamento)
        .filter(Departamento.id == departamento_id, Departamento.tenant_id == tenant_id)
        .first()
    )
    if not departamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Departamento não encontrado"
        )
    grupo_id = _grupo_id_ou_erro(db, tenant_id)
    return vincular_departamento_mestre(
        db,
        departamento=departamento,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        mestre_id=payload.mestre_id,
    )
