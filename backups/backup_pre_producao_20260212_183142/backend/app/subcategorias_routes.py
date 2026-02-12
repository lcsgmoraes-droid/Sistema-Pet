"""
⚠️ LEGADO — NÃO USAR ⚠️

Este arquivo contém rotas antigas de subcategorias que usam SQLite
e NÃO são multi-tenant. 

❌ DEPRECATED: Não deve ser usado em novas implementações
✅ USAR: /dre/subcategorias (em dre_plano_contas_routes.py)

As rotas aqui retornam HTTP 410 (Gone) para forçar migração.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User

logger = logging.getLogger(__name__)
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


@router.get("")
async def listar_subcategorias(user_and_tenant = Depends(get_current_user_and_tenant)):
    """
    ⚠️ ENDPOINT LEGADO - HTTP 410 GONE
    
    Esta rota foi descontinuada. Use o endpoint oficial:
    GET /dre/subcategorias
    """
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias",
            "deprecated": True,
            "replacement": "/dre/subcategorias",
            "reason": "Migração para DRESubcategorias multi-tenant (PostgreSQL)"
        }
    )


@router.get("/{subcategoria_id}")
async def buscar_subcategoria(
    subcategoria_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """⚠️ ENDPOINT LEGADO - HTTP 410 GONE"""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias/{id}",
            "deprecated": True,
            "replacement": f"/dre/subcategorias/{subcategoria_id}",
            "reason": "Migração para DRESubcategorias multi-tenant (PostgreSQL)"
        }
    )


@router.post("")
async def criar_subcategoria(
    data: SubcategoriaCreate,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """⚠️ ENDPOINT LEGADO - HTTP 410 GONE"""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias",
            "deprecated": True,
            "replacement": "/dre/subcategorias",
            "reason": "Migração para DRESubcategorias multi-tenant (PostgreSQL)"
        }
    )


@router.put("/{subcategoria_id}")
@router.patch("/{subcategoria_id}")
async def atualizar_subcategoria(
    subcategoria_id: int,
    data: SubcategoriaUpdate,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """⚠️ ENDPOINT LEGADO - HTTP 410 GONE"""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias/{id}",
            "deprecated": True,
            "replacement": f"/dre/subcategorias/{subcategoria_id}",
            "reason": "Migração para DRESubcategorias multi-tenant (PostgreSQL)"
        }
    )


@router.delete("/{subcategoria_id}")
async def deletar_subcategoria(
    subcategoria_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """⚠️ ENDPOINT LEGADO - HTTP 410 GONE"""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": "Endpoint legado descontinuado. Use /dre/subcategorias/{id}",
            "deprecated": True,
            "replacement": f"/dre/subcategorias/{subcategoria_id}",
            "reason": "Migração para DRESubcategorias multi-tenant (PostgreSQL)"
        }
    )
        
        # Inserir
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO subcategorias 
            (categoria_id, nome, descricao, ativo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.categoria_id,
            data.nome,
            data.descricao,
            data.ativo,
            now,
            now
        ))
        
        conn.commit()
        subcategoria_id = cursor.lastrowid
        
        return {
            "success": True,
            "message": "Subcategoria criada com sucesso",
            "id": subcategoria_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar subcategoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar subcategoria: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


@router.put("/{subcategoria_id}")
async def atualizar_subcategoria(
    subcategoria_id: int,
    data: SubcategoriaUpdate,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma subcategoria"""
    db = None
    try:
        from sqlalchemy import text
        from .db import SessionLocal
        
        db = SessionLocal()
        
        # Verificar se existe
        result = db.execute(text("SELECT id FROM subcategorias WHERE id = :id"), {"id": subcategoria_id})
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subcategoria não encontrada"
            )
        
        # Montar UPDATE dinâmico
        updates = []
        params = {}
        
        if data.categoria_id is not None:
            # Verificar se nova categoria existe
            result_cat = db.execute(text("SELECT id FROM categorias WHERE id = :id"), {"id": data.categoria_id})
            if not result_cat.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoria não encontrada"
                )
            updates.append("categoria_id = :categoria_id")
            params['categoria_id'] = data.categoria_id
        
        if data.nome is not None:
            updates.append("nome = :nome")
            params['nome'] = data.nome
        
        if data.descricao is not None:
            updates.append("descricao = :descricao")
            params['descricao'] = data.descricao
        
        if data.ativo is not None:
            updates.append("ativo = :ativo")
            params['ativo'] = data.ativo
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar"
            )
        
        updates.append("updated_at = :updated_at")
        params['updated_at'] = datetime.now().isoformat()
        params['id'] = subcategoria_id
        
        sql = f"UPDATE subcategorias SET {', '.join(updates)} WHERE id = :id"
        db.execute(text(sql), params)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Subcategoria atualizada com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar subcategoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar subcategoria: {str(e)}"
        )
    finally:
        if db:
            db.close()


@router.delete("/{subcategoria_id}")
async def excluir_subcategoria(
    subcategoria_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exclui uma subcategoria (soft delete)"""
    db = None
    try:
        from sqlalchemy import text
        from .db import SessionLocal
        
        db = SessionLocal()
        
        # Verificar se existe
        result = db.execute(text("SELECT id FROM subcategorias WHERE id = :id"), {"id": subcategoria_id})
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subcategoria não encontrada"
            )
        
        # Verificar se há produtos usando esta subcategoria
        result_count = db.execute(
            text("""
                SELECT COUNT(*) as total 
                FROM produtos 
                WHERE subcategoria_id = :id
            """),
            {"id": subcategoria_id}
        )
        
        count = result_count.fetchone()[0]
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível excluir. Existem {count} produto(s) usando esta subcategoria"
            )
        
        # Soft delete
        db.execute(
            text("""
                UPDATE subcategorias 
                SET ativo = 0, updated_at = :updated_at
                WHERE id = :id
            """),
            {"updated_at": datetime.now().isoformat(), "id": subcategoria_id}
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": "Subcategoria excluída com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir subcategoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir subcategoria: {str(e)}"
        )
    finally:
        if db:
            db.close()


@router.get("/categoria/{categoria_id}")
async def listar_por_categoria(
    categoria_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista subcategorias de uma categoria específica"""
    try:
        from sqlalchemy import text
        from .db import SessionLocal
        
        db = SessionLocal()
        
        result = db.execute(
            text("""
                SELECT 
                    id,
                    categoria_id,
                    nome,
                    descricao,
                    ativo,
                    created_at,
                    updated_at
                FROM subcategorias
                WHERE categoria_id = :categoria_id
                ORDER BY nome
            """),
            {"categoria_id": categoria_id}
        )
        
        subcategorias = [dict(row) for row in result.fetchall()]
        db.close()
        
        return subcategorias
        
    except Exception as e:
        logger.error(f"Erro ao listar subcategorias por categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar subcategorias: {str(e)}"
        )
