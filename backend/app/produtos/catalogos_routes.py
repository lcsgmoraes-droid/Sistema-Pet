"""Rotas dos catalogos auxiliares de produtos."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.categorias import (
    _calcular_niveis_categorias,
    _construir_arvore_categorias,
)
from app.produtos.schemas import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaUpdate,
    DepartamentoCreate,
    DepartamentoResponse,
    DepartamentoUpdate,
    MarcaCreate,
    MarcaResponse,
    MarcaUpdate,
)
from app.produtos.validators import (
    _obter_marca_ou_404,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Categoria, Departamento, Marca, Produto
from app.security.permissions_decorator import require_permission

router = APIRouter()

# ==========================================
# ENDPOINTS - CATEGORIAS
# ==========================================


@router.post(
    "/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED
)
@require_permission("produtos.criar")
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se categoria pai existe (se fornecida)
    if categoria.categoria_pai_id:
        pai = (
            db.query(Categoria)
            .filter(
                Categoria.id == categoria.categoria_pai_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai nÃ£o encontrada")

        # Verificar nÃ­vel mÃ¡ximo (4 nÃ­veis)
        nivel_pai = calcular_nivel(db, categoria.categoria_pai_id)
        if nivel_pai >= 4:
            raise HTTPException(
                status_code=400, detail="Limite de 4 nÃ­veis de categorias atingido"
            )

    # Criar categoria
    nova_categoria = Categoria(
        **categoria.model_dump(), tenant_id=tenant_id, user_id=current_user.id
    )

    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return nova_categoria


@router.get("/categorias", response_model=List[CategoriaResponse])
@require_permission("produtos.visualizar")
def listar_categorias(
    categoria_pai_id: Optional[int] = None,
    incluir_subcategorias: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as categorias (o frontend constrÃ³i a hierarquia)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Retornar TODAS as categorias ativas do usuÃ¡rio
    # O frontend vai construir a Ã¡rvore hierÃ¡rquica
    query = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id, Categoria.ativo.is_(True)
    )

    categorias = (
        query.options(joinedload(Categoria.departamento))
        .order_by(Categoria.ordem, Categoria.nome)
        .all()
    )

    categoria_por_id = {cat.id: cat for cat in categorias}
    categoria_ids = list(categoria_por_id.keys())

    total_filhos_por_categoria = {
        categoria_pai_id: total_filhos
        for categoria_pai_id, total_filhos in (
            db.query(Categoria.categoria_pai_id, func.count(Categoria.id))
            .filter(
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
                Categoria.categoria_pai_id.isnot(None),
            )
            .group_by(Categoria.categoria_pai_id)
            .all()
        )
    }

    total_produtos_por_categoria = {}
    if categoria_ids:
        total_produtos_por_categoria = {
            categoria_id: total_produtos
            for categoria_id, total_produtos in (
                db.query(Produto.categoria_id, func.count(Produto.id))
                .filter(
                    Produto.tenant_id == tenant_id,
                    Produto.categoria_id.in_(categoria_ids),
                )
                .group_by(Produto.categoria_id)
                .all()
            )
        }

    niveis_por_categoria = _calcular_niveis_categorias(categoria_por_id)

    # Calcular nÃ­vel e contadores para cada categoria sem N+1
    resultado = []
    for cat in categorias:
        cat_dict = {
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "categoria_pai_id": cat.categoria_pai_id,
            "departamento_id": cat.departamento_id,
            "departamento_nome": cat.departamento.nome if cat.departamento else None,
            "icone": cat.icone,
            "cor": cat.cor,
            "ordem": cat.ordem,
            "ativo": cat.ativo,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "nivel": niveis_por_categoria.get(cat.id, 1),
            "total_filhos": int(total_filhos_por_categoria.get(cat.id, 0) or 0),
            "total_produtos": int(total_produtos_por_categoria.get(cat.id, 0) or 0),
        }
        resultado.append(CategoriaResponse(**cat_dict))

    return resultado


def calcular_nivel(db: Session, categoria_id: int, nivel: int = 1) -> int:
    """Calcula o nÃ­vel de uma categoria na hierarquia"""
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria or not categoria.categoria_pai_id:
        return nivel
    return calcular_nivel(db, categoria.categoria_pai_id, nivel + 1)


@router.get("/categorias/hierarquia", response_model=List[dict])
@require_permission("produtos.visualizar")
def listar_categorias_hierarquia(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as categorias em formato de Ã¡rvore hierÃ¡rquica"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar todas as categorias ativas
    categorias = (
        db.query(Categoria)
        .filter(Categoria.tenant_id == tenant_id, Categoria.ativo.is_(True))
        .order_by(Categoria.ordem, Categoria.nome)
        .all()
    )

    return _construir_arvore_categorias(categorias)


@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
@require_permission("produtos.visualizar")
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m detalhes de uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    return categoria


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
@require_permission("produtos.editar")
def atualizar_categoria(
    categoria_id: int,
    categoria_update: CategoriaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se categoria pai existe (se fornecida e diferente)
    if (
        categoria_update.categoria_pai_id
        and categoria_update.categoria_pai_id != categoria.categoria_pai_id
    ):
        # NÃ£o permitir que categoria seja filha de si mesma
        if categoria_update.categoria_pai_id == categoria_id:
            raise HTTPException(
                status_code=400, detail="Categoria nÃ£o pode ser pai de si mesma"
            )

        pai = (
            db.query(Categoria)
            .filter(
                Categoria.id == categoria_update.categoria_pai_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai nÃ£o encontrada")

    # Atualizar campos
    for key, value in categoria_update.model_dump(exclude_unset=True).items():
        setattr(categoria, key, value)

    categoria.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(categoria)

    return categoria


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("produtos.editar")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se categoria tem subcategorias
    subcategorias = (
        db.query(Categoria)
        .filter(
            Categoria.categoria_pai_id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .count()
    )

    if subcategorias > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {subcategorias} subcategorias. Remova-as primeiro.",
        )

    # Verificar se categoria tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.categoria_id == categoria_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {produtos_count} produtos. Remova-os ou mova para outra categoria primeiro.",
        )

    # Soft delete
    categoria.ativo = False
    categoria.updated_at = datetime.utcnow()

    db.commit()

    return None


# ==========================================
# ENDPOINTS - MARCAS
# ==========================================


@router.post(
    "/marcas", response_model=MarcaResponse, status_code=status.HTTP_201_CREATED
)
@require_permission("produtos.criar")
def criar_marca(
    marca: MarcaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova marca"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    nova_marca = Marca(
        **marca.model_dump(),
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    db.add(nova_marca)
    db.commit()
    db.refresh(nova_marca)

    return nova_marca


@router.get("/marcas", response_model=List[MarcaResponse])
@require_permission("produtos.visualizar")
def listar_marcas(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista marcas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Marca).filter(Marca.tenant_id == tenant_id, Marca.ativo.is_(True))

    if busca:
        query = query.filter(Marca.nome.ilike(f"%{busca}%"))

    marcas = query.order_by(Marca.nome).all()

    return marcas


@router.get("/marcas/{marca_id}", response_model=MarcaResponse)
@require_permission("produtos.visualizar")
def obter_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m detalhes de uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    marca = _obter_marca_ou_404(db, marca_id, tenant_id)
    return marca


@router.put("/marcas/{marca_id}", response_model=MarcaResponse)
@require_permission("produtos.editar")
def atualizar_marca(
    marca_id: int,
    marca_update: MarcaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    marca = _obter_marca_ou_404(db, marca_id, tenant_id)

    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")

    for key, value in marca_update.model_dump(exclude_unset=True).items():
        setattr(marca, key, value)

    marca.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(marca)

    return marca


@router.delete("/marcas/{marca_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("produtos.editar")
def deletar_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    marca = (
        db.query(Marca)
        .filter(
            Marca.id == marca_id, Marca.tenant_id == tenant_id, Marca.ativo.is_(True)
        )
        .first()
    )

    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")

    # Verificar se marca tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.marca_id == marca_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Marca possui {produtos_count} produtos. Remova-os ou mova para outra marca primeiro.",
        )

    # Soft delete
    marca.ativo = False
    marca.updated_at = datetime.utcnow()

    db.commit()

    return None


# ==========================================
# ENDPOINTS - DEPARTAMENTOS
# ==========================================


@router.post(
    "/departamentos",
    response_model=DepartamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("produtos.criar")
def criar_departamento(
    departamento: DepartamentoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo departamento"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    novo_departamento = Departamento(
        **departamento.model_dump(),
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    db.add(novo_departamento)
    db.commit()
    db.refresh(novo_departamento)

    return novo_departamento


@router.get("/departamentos", response_model=List[DepartamentoResponse])
@require_permission("produtos.visualizar")
def listar_departamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista departamentos do tenant atual"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Departamento).filter(
        Departamento.tenant_id == tenant_id, Departamento.ativo.is_(True)
    )

    if busca:
        query = query.filter(Departamento.nome.ilike(f"%{busca}%"))

    departamentos = query.order_by(Departamento.nome).all()

    return departamentos


@router.get("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
@require_permission("produtos.visualizar")
def obter_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m um departamento por ID"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    return departamento


@router.put("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
@require_permission("produtos.editar")
def atualizar_departamento(
    departamento_id: int,
    departamento_update: DepartamentoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza um departamento"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    for key, value in departamento_update.model_dump(exclude_unset=True).items():
        setattr(departamento, key, value)

    departamento.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(departamento)

    return departamento


@router.delete(
    "/departamentos/{departamento_id}", status_code=status.HTTP_204_NO_CONTENT
)
@require_permission("produtos.editar")
def deletar_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um departamento"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    # Verificar se departamento tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.departamento_id == departamento_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Departamento possui {produtos_count} produtos. Remova-os ou mova para outro departamento primeiro.",
        )

    # Soft delete
    departamento.ativo = False
    departamento.updated_at = datetime.utcnow()

    db.commit()

    return None
