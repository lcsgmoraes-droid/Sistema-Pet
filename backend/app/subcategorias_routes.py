"""
LEGADO - NAO USAR

Rotas antigas de subcategorias. O fluxo oficial multi-tenant esta em
`/dre/subcategorias`; estes endpoints retornam HTTP 410 para forcar migracao.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .auth.dependencies import get_current_user_and_tenant


router = APIRouter(prefix="/subcategorias", tags=["subcategorias (LEGADO)"])


class SubcategoriaCreate(BaseModel):
    categoria_id: int
    nome: str
    descricao: Optional[str] = None
    ativo: bool = True


class SubcategoriaUpdate(BaseModel):
    categoria_id: Optional[int] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None


def _legacy_response(replacement: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias",
            "deprecated": True,
            "replacement": replacement,
            "reason": "Migracao para DRESubcategorias multi-tenant (PostgreSQL)",
        },
    )


@router.get("")
async def listar_subcategorias(user_and_tenant=Depends(get_current_user_and_tenant)):
    return _legacy_response("/dre/subcategorias")


@router.get("/categoria/{categoria_id}")
async def listar_por_categoria(
    categoria_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return _legacy_response(f"/dre/subcategorias?categoria_id={categoria_id}")


@router.get("/{subcategoria_id}")
async def buscar_subcategoria(
    subcategoria_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return _legacy_response(f"/dre/subcategorias/{subcategoria_id}")


@router.post("")
async def criar_subcategoria(
    data: SubcategoriaCreate,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return _legacy_response("/dre/subcategorias")


@router.put("/{subcategoria_id}")
@router.patch("/{subcategoria_id}")
async def atualizar_subcategoria(
    subcategoria_id: int,
    data: SubcategoriaUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return _legacy_response(f"/dre/subcategorias/{subcategoria_id}")


@router.delete("/{subcategoria_id}")
async def deletar_subcategoria(
    subcategoria_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return _legacy_response(f"/dre/subcategorias/{subcategoria_id}")
