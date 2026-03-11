"""
Routes para gerenciamento de categorias financeiras
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth import get_current_user
from app.models import User
from app.financeiro_models import CategoriaFinanceira
from app.domain.validators.dre_validator import validar_categoria_financeira_dre
from app.utils.logger import logger

router = APIRouter(prefix="/categorias-financeiras", tags=["Categorias Financeiras"])


# ==================== Schemas ====================

class CategoriaFinanceiraCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., pattern="^(receita|despesa)$")
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    descricao: Optional[str] = None
    categoria_pai_id: Optional[int] = None
    ativo: bool = True
    tipo_custo: Optional[str] = None  # 'fixo', 'variavel', 'ambos'


class CategoriaFinanceiraUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, pattern="^(receita|despesa)$")
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    descricao: Optional[str] = None
    categoria_pai_id: Optional[int] = None
    ativo: Optional[bool] = None
    tipo_custo: Optional[str] = None  # 'fixo', 'variavel', 'ambos'


class CategoriaFinanceiraResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    cor: Optional[str] = None
    icone: Optional[str] = None
    descricao: Optional[str] = None
    categoria_pai_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None  # Campo DRE
    tipo_custo: Optional[str] = None  # 'fixo', 'variavel', 'ambos'
    ativo: bool
    
    # Informações adicionais
    nivel: int = 0
    caminho_completo: str = ""
    tem_subcategorias: bool = False
    
    model_config = {"from_attributes": True}


# ==================== Funções Auxiliares ====================

def calcular_nivel_categoria(categoria: CategoriaFinanceira, db: Session) -> int:
    """Calcula o nível hierárquico da categoria"""
    nivel = 0
    pai_id = categoria.categoria_pai_id
    while pai_id:
        nivel += 1
        pai = db.query(CategoriaFinanceira).filter(CategoriaFinanceira.id == pai_id).first()
        if pai:
            pai_id = pai.categoria_pai_id
        else:
            break
    return nivel


def obter_caminho_completo(categoria: CategoriaFinanceira, db: Session) -> str:
    """Retorna o caminho completo da categoria (ex: Despesas > Salários > FGTS)"""
    caminho = [categoria.nome]
    pai_id = categoria.categoria_pai_id
    
    while pai_id:
        pai = db.query(CategoriaFinanceira).filter(CategoriaFinanceira.id == pai_id).first()
        if pai:
            caminho.insert(0, pai.nome)
            pai_id = pai.categoria_pai_id
        else:
            break
    
    return " > ".join(caminho)


def categoria_para_response(categoria: CategoriaFinanceira, db: Session) -> CategoriaFinanceiraResponse:
    """Converte CategoriaFinanceira para Response com informações adicionais"""
    tem_subcategorias = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.categoria_pai_id == categoria.id
    ).count() > 0
    
    return CategoriaFinanceiraResponse(
        id=categoria.id,
        nome=categoria.nome,
        tipo=categoria.tipo,
        cor=categoria.cor,
        icone=categoria.icone,
        descricao=categoria.descricao,
        categoria_pai_id=categoria.categoria_pai_id,
        dre_subcategoria_id=categoria.dre_subcategoria_id,  # Incluir DRE
        tipo_custo=categoria.tipo_custo,
        ativo=categoria.ativo,
        nivel=calcular_nivel_categoria(categoria, db),
        caminho_completo=obter_caminho_completo(categoria, db),
        tem_subcategorias=tem_subcategorias
    )


# ==================== Endpoints ====================

@router.get("", response_model=List[CategoriaFinanceiraResponse])
def listar_categorias(
    tipo: Optional[str] = None,
    apenas_ativas: bool = True,
    apenas_raiz: bool = False,
    categoria_pai_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Lista categorias financeiras com filtros
    - tipo: 'receita' ou 'despesa'
    - apenas_ativas: Filtrar apenas categorias ativas
    - apenas_raiz: Retorna apenas categorias raiz (sem pai)
    - categoria_pai_id: Retorna subcategorias de uma categoria específica
    """
    tenant_id = current_user.tenant_id
    
    logger.info("listar_categorias", "\n🔍 [CATEGORIAS] Listando categorias:")
    logger.info("user_info", f"  👤 User ID: {current_user.id}")
    logger.info("tenant_info", f"  🏢 Tenant ID: {tenant_id}")
    logger.info("filter_tipo", f"  📊 Tipo: {tipo}")
    logger.info("filter_ativas", f"  ✅ Apenas Ativas: {apenas_ativas}")
    logger.info("filter_raiz", f"  🌳 Apenas Raiz: {apenas_raiz}")
    
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.user_id == current_user.id
    )
    
    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)
    
    if apenas_ativas:
        query = query.filter(CategoriaFinanceira.ativo == True)
    
    if apenas_raiz:
        query = query.filter(CategoriaFinanceira.categoria_pai_id == None)
    elif categoria_pai_id is not None:
        query = query.filter(CategoriaFinanceira.categoria_pai_id == categoria_pai_id)
    
    categorias = query.order_by(CategoriaFinanceira.nome).all()
    
    logger.info("total_encontrado", f"  📋 Total encontrado: {len(categorias)}")
    for cat in categorias[:5]:  # Mostra apenas as 5 primeiras
        logger.info("categoria_item", f"    - {cat.nome} ({cat.tipo})")
    if len(categorias) > 5:
        logger.info("categoria_mais", f"    ... e mais {len(categorias) - 5} categorias")
    
    resultado = [categoria_para_response(cat, db) for cat in categorias]
    logger.info("resultado_final", f"  ✅ Retornando {len(resultado)} categorias\n")
    
    return resultado


@router.get("/arvore", response_model=List[CategoriaFinanceiraResponse])
def listar_categorias_arvore(
    tipo: Optional[str] = None,
    apenas_ativas: bool = True,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna todas as categorias hierarquicamente
    """
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.user_id == current_user.id
    )
    
    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)
    
    if apenas_ativas:
        query = query.filter(CategoriaFinanceira.ativo == True)
    
    categorias = query.all()
    
    # Ordenar por nível e nome para exibição hierárquica
    categorias_response = [categoria_para_response(cat, db) for cat in categorias]
    categorias_response.sort(key=lambda x: (x.nivel, x.caminho_completo))
    
    return categorias_response


@router.get("/{categoria_id}", response_model=CategoriaFinanceiraResponse)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retorna uma categoria específica"""
    categoria = db.query(CategoriaFinanceira).filter(
        and_(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.user_id == current_user.id
        )
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    return categoria_para_response(categoria, db)


@router.post("", response_model=CategoriaFinanceiraResponse)
def criar_categoria(
    categoria_data: CategoriaFinanceiraCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cria uma nova categoria financeira"""
    tenant_id = current_user.tenant_id
    
    # Validar categoria pai se fornecida
    if categoria_data.categoria_pai_id:
        pai = db.query(CategoriaFinanceira).filter(
            and_(
                CategoriaFinanceira.id == categoria_data.categoria_pai_id,
                CategoriaFinanceira.user_id == current_user.id
            )
        ).first()
        
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
        
        # Validar que a categoria pai é do mesmo tipo
        if pai.tipo != categoria_data.tipo:
            raise HTTPException(
                status_code=400, 
                detail="Categoria pai deve ser do mesmo tipo (receita/despesa)"
            )
    
    categoria = CategoriaFinanceira(
        **categoria_data.model_dump(),
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    
    db.add(categoria)
    db.flush()  # Flush para gerar o ID antes da validação
    
    # Validar vínculo com DRE
    validar_categoria_financeira_dre(
        db=db,
        categoria_financeira_id=categoria.id,
        dre_subcategoria_id=getattr(categoria_data, 'dre_subcategoria_id', None),
        tenant_id=tenant_id
    )
    
    db.commit()
    db.refresh(categoria)
    
    return categoria_para_response(categoria, db)


@router.put("/{categoria_id}", response_model=CategoriaFinanceiraResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria_data: CategoriaFinanceiraUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Atualiza uma categoria existente"""
    tenant_id = current_user.tenant_id
    
    categoria = db.query(CategoriaFinanceira).filter(
        and_(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.user_id == current_user.id
        )
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Atualizar apenas campos fornecidos
    update_data = categoria_data.model_dump(exclude_unset=True)
    
    # Validar categoria pai se fornecida
    if 'categoria_pai_id' in update_data and update_data['categoria_pai_id']:
        # Não permitir categoria ser pai de si mesma
        if update_data['categoria_pai_id'] == categoria_id:
            raise HTTPException(
                status_code=400, 
                detail="Categoria não pode ser pai de si mesma"
            )
        
        pai = db.query(CategoriaFinanceira).filter(
            and_(
                CategoriaFinanceira.id == update_data['categoria_pai_id'],
                CategoriaFinanceira.user_id == current_user.id
            )
        ).first()
        
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
    
    for key, value in update_data.items():
        setattr(categoria, key, value)
    
    # Propagar tipo_custo 'fixo'/'variavel' para filhos diretos
    if 'tipo_custo' in update_data and update_data['tipo_custo'] in ('fixo', 'variavel'):
        filhos = db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.categoria_pai_id == categoria_id,
            CategoriaFinanceira.user_id == current_user.id
        ).all()
        for filho in filhos:
            filho.tipo_custo = update_data['tipo_custo']
    
    # Validar vínculo com DRE se foi alterado
    if 'dre_subcategoria_id' in update_data:
        validar_categoria_financeira_dre(
            db=db,
            categoria_financeira_id=categoria.id,
            dre_subcategoria_id=update_data.get('dre_subcategoria_id'),
            tenant_id=tenant_id
        )
    
    db.commit()
    db.refresh(categoria)
    
    return categoria_para_response(categoria, db)


@router.delete("/{categoria_id}")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Desativa uma categoria (soft delete)"""
    categoria = db.query(CategoriaFinanceira).filter(
        and_(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.user_id == current_user.id
        )
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Verificar se tem subcategorias ativas
    subcategorias_ativas = db.query(CategoriaFinanceira).filter(
        and_(
            CategoriaFinanceira.categoria_pai_id == categoria_id,
            CategoriaFinanceira.ativo == True
        )
    ).count()
    
    if subcategorias_ativas > 0:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível desativar categoria com subcategorias ativas"
        )
    
    categoria.ativo = False
    db.commit()
    
    return {"message": "Categoria desativada com sucesso"}


@router.get("/{categoria_id}/subcategorias-dre")
def listar_subcategorias_dre_da_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna as subcategorias DRE vinculadas a uma categoria financeira específica
    """
    from app.dre_plano_contas_models import DRESubcategoria
    
    tenant_id = current_user.tenant_id
    
    # Verificar se a categoria existe e pertence ao usuário
    categoria = db.query(CategoriaFinanceira).filter(
        and_(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.user_id == current_user.id
        )
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Se a categoria não tem dre_subcategoria_id, retorna lista vazia
    if not categoria.dre_subcategoria_id:
        return []
    
    # Buscar a subcategoria DRE vinculada
    subcategoria_dre = db.query(DRESubcategoria).filter(
        and_(
            DRESubcategoria.id == categoria.dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id
        )
    ).first()
    
    if not subcategoria_dre:
        return []
    
    # Retornar como lista (pode ser expandido no futuro para múltiplas subcategorias)
    return [subcategoria_dre]
