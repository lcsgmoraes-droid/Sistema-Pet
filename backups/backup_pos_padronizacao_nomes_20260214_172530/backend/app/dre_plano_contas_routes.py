"""
Rotas para gerenciamento de Plano de Contas DRE.
CRUD de Categorias e Subcategorias DRE (estrutural apenas).
NÃO cria períodos ou lançamentos DRE.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE, TipoCusto, BaseRateio, EscopoRateio
from pydantic import BaseModel, Field, validator
from datetime import datetime

router = APIRouter(prefix="/dre", tags=["DRE - Plano de Contas"])

# ============================================================
# SCHEMAS
# ============================================================

class DRECategoriaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    ordem: int = Field(default=0, ge=0)
    natureza: NaturezaDRE
    
    class Config:
        use_enum_values = True

class DRECategoriaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    ordem: int | None = Field(None, ge=0)
    ativo: bool | None = None

class DRECategoriaResponse(BaseModel):
    id: int
    tenant_id: str
    nome: str
    ordem: int
    natureza: str
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DRESubcategoriaCreate(BaseModel):
    categoria_id: int
    nome: str = Field(..., min_length=1, max_length=150)
    tipo_custo: TipoCusto
    base_rateio: BaseRateio | None = None
    escopo_rateio: EscopoRateio
    
    @validator('base_rateio', always=True)
    def validar_base_rateio(cls, v, values):
        tipo_custo = values.get('tipo_custo')
        if tipo_custo == TipoCusto.INDIRETO_RATEAVEL and v is None:
            raise ValueError('base_rateio é obrigatório quando tipo_custo = INDIRETO_RATEAVEL')
        return v
    
    class Config:
        use_enum_values = True

class DRESubcategoriaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=150)
    tipo_custo: TipoCusto | None = None
    base_rateio: BaseRateio | None = None
    escopo_rateio: EscopoRateio | None = None
    ativo: bool | None = None
    
    class Config:
        use_enum_values = True

class DRESubcategoriaResponse(BaseModel):
    id: int
    tenant_id: UUID | str  # Aceita UUID ou string
    categoria_id: int
    nome: str
    tipo_custo: str
    base_rateio: str | None
    escopo_rateio: str
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        use_enum_values = True
        # Permite conversão automática de UUID para string no JSON
        json_encoders = {
            UUID: lambda v: str(v)
        }

# ============================================================
# ROTAS - DRE CATEGORIAS
# ============================================================

@router.get("/categorias", response_model=List[DRECategoriaResponse])
def listar_categorias(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as categorias DRE do tenant ordenadas"""
    current_user, tenant_id = user_and_tenant
    
    categorias = db.query(DRECategoria).filter(
        DRECategoria.tenant_id == tenant_id
    ).order_by(DRECategoria.ordem, DRECategoria.nome).all()
    
    return categorias

@router.post("/categorias", response_model=DRECategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria: DRECategoriaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova categoria DRE (apenas estrutural, NÃO cria DRE)"""
    current_user, tenant_id = user_and_tenant
    
    nova_categoria = DRECategoria(
        tenant_id=tenant_id,
        nome=categoria.nome,
        ordem=categoria.ordem,
        natureza=categoria.natureza,
        ativo=True
    )
    
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)
    
    return nova_categoria

@router.put("/categorias/{categoria_id}", response_model=DRECategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria: DRECategoriaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma categoria DRE"""
    current_user, tenant_id = user_and_tenant
    
    db_categoria = db.query(DRECategoria).filter(
        DRECategoria.id == categoria_id,
        DRECategoria.tenant_id == tenant_id
    ).first()
    
    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    if categoria.nome is not None:
        db_categoria.nome = categoria.nome
    if categoria.ordem is not None:
        db_categoria.ordem = categoria.ordem
    if categoria.ativo is not None:
        db_categoria.ativo = categoria.ativo
    
    db.commit()
    db.refresh(db_categoria)
    
    return db_categoria

@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta uma categoria DRE (se não houver subcategorias ativas)"""
    current_user, tenant_id = user_and_tenant
    
    db_categoria = db.query(DRECategoria).filter(
        DRECategoria.id == categoria_id,
        DRECategoria.tenant_id == tenant_id
    ).first()
    
    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Verificar se há subcategorias ativas
    subcategorias_ativas = db.query(DRESubcategoria).filter(
        DRESubcategoria.categoria_id == categoria_id,
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.ativo.is_(True)
    ).count()
    
    if subcategorias_ativas > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir: existem {subcategorias_ativas} subcategorias ativas vinculadas"
        )
    
    db.delete(db_categoria)
    db.commit()
    
    return None

# ============================================================
# ROTAS - DRE SUBCATEGORIAS
# ============================================================

@router.get("/subcategorias", response_model=List[DRESubcategoriaResponse])
def listar_subcategorias(
    categoria_id: int | None = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as subcategorias DRE do tenant (ou filtra por categoria)"""
    current_user, tenant_id = user_and_tenant
    
    query = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id
    )
    
    if categoria_id:
        query = query.filter(DRESubcategoria.categoria_id == categoria_id)
    
    subcategorias = query.order_by(DRESubcategoria.nome).all()
    
    return subcategorias

@router.post("/subcategorias", response_model=DRESubcategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_subcategoria(
    subcategoria: DRESubcategoriaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova subcategoria DRE (apenas estrutural, NÃO cria DRE)"""
    current_user, tenant_id = user_and_tenant
    
    # Validar se categoria existe e pertence ao tenant
    categoria = db.query(DRECategoria).filter(
        DRECategoria.id == subcategoria.categoria_id,
        DRECategoria.tenant_id == tenant_id
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=400, detail="Categoria inválida ou não pertence a este tenant")
    
    nova_subcategoria = DRESubcategoria(
        tenant_id=tenant_id,
        categoria_id=subcategoria.categoria_id,
        nome=subcategoria.nome,
        tipo_custo=subcategoria.tipo_custo,
        base_rateio=subcategoria.base_rateio,
        escopo_rateio=subcategoria.escopo_rateio,
        ativo=True
    )
    
    db.add(nova_subcategoria)
    db.commit()
    db.refresh(nova_subcategoria)
    
    return nova_subcategoria

@router.put("/subcategorias/{subcategoria_id}", response_model=DRESubcategoriaResponse)
def atualizar_subcategoria(
    subcategoria_id: int,
    subcategoria: DRESubcategoriaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma subcategoria DRE"""
    current_user, tenant_id = user_and_tenant
    
    db_subcategoria = db.query(DRESubcategoria).filter(
        DRESubcategoria.id == subcategoria_id,
        DRESubcategoria.tenant_id == tenant_id
    ).first()
    
    if not db_subcategoria:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
    
    if subcategoria.nome is not None:
        db_subcategoria.nome = subcategoria.nome
    if subcategoria.tipo_custo is not None:
        db_subcategoria.tipo_custo = subcategoria.tipo_custo
    if subcategoria.base_rateio is not None:
        db_subcategoria.base_rateio = subcategoria.base_rateio
    if subcategoria.escopo_rateio is not None:
        db_subcategoria.escopo_rateio = subcategoria.escopo_rateio
    if subcategoria.ativo is not None:
        db_subcategoria.ativo = subcategoria.ativo
    
    # Validar regra: INDIRETO_RATEAVEL precisa de base_rateio
    if db_subcategoria.tipo_custo == TipoCusto.INDIRETO_RATEAVEL and db_subcategoria.base_rateio is None:
        raise HTTPException(
            status_code=400,
            detail="base_rateio é obrigatório quando tipo_custo = INDIRETO_RATEAVEL"
        )
    
    db.commit()
    db.refresh(db_subcategoria)
    
    return db_subcategoria

@router.delete("/subcategorias/{subcategoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_subcategoria(
    subcategoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Inativa uma subcategoria DRE (soft delete).
    NÃO deleta fisicamente se houver lançamentos.
    """
    current_user, tenant_id = user_and_tenant
    
    db_subcategoria = db.query(DRESubcategoria).filter(
        DRESubcategoria.id == subcategoria_id,
        DRESubcategoria.tenant_id == tenant_id
    ).first()
    
    if not db_subcategoria:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
    
    # Verificar se há lançamentos (contas_pagar ou contas_receber)
    from app.financeiro_models import ContaPagar, ContaReceber
    
    lancamentos_pagar = db.query(ContaPagar).filter(
        ContaPagar.dre_subcategoria_id == subcategoria_id,
        ContaPagar.tenant_id == tenant_id
    ).count()
    
    lancamentos_receber = db.query(ContaReceber).filter(
        ContaReceber.dre_subcategoria_id == subcategoria_id,
        ContaReceber.tenant_id == tenant_id
    ).count()
    
    total_lancamentos = lancamentos_pagar + lancamentos_receber
    
    if total_lancamentos > 0:
        # Apenas inativa (soft delete)
        db_subcategoria.ativo = False
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Subcategoria possui {total_lancamentos} lançamentos. Foi inativada (ativo=False)."
        )
    
    # Sem lançamentos: pode deletar fisicamente
    db.delete(db_subcategoria)
    db.commit()
    
    return None
