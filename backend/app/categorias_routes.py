"""
Routes para gerenciamento de categorias financeiras
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.categorias_integridade import normalizar_nome_categoria
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
    dre_subcategoria_id: Optional[int] = None  # Vínculo com subcategoria DRE


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
    pode_editar: bool = False

    model_config = {"from_attributes": True}


# ==================== Funções Auxiliares ====================


def calcular_nivel_categoria(categoria: CategoriaFinanceira, db: Session) -> int:
    """Calcula o nível hierárquico da categoria"""
    nivel = 0
    pai_id = categoria.categoria_pai_id
    visitados = {categoria.id}
    while pai_id and pai_id not in visitados:
        visitados.add(pai_id)
        nivel += 1
        pai = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == pai_id,
                CategoriaFinanceira.tenant_id == categoria.tenant_id,
            )
            .first()
        )
        if pai:
            pai_id = pai.categoria_pai_id
        else:
            break
    return nivel


def obter_caminho_completo(categoria: CategoriaFinanceira, db: Session) -> str:
    """Retorna o caminho completo da categoria (ex: Despesas > Salários > FGTS)"""
    caminho = [categoria.nome]
    pai_id = categoria.categoria_pai_id
    visitados = {categoria.id}

    while pai_id and pai_id not in visitados:
        visitados.add(pai_id)
        pai = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == pai_id,
                CategoriaFinanceira.tenant_id == categoria.tenant_id,
            )
            .first()
        )
        if pai:
            caminho.insert(0, pai.nome)
            pai_id = pai.categoria_pai_id
        else:
            break

    return " > ".join(caminho)


def categoria_para_response(
    categoria: CategoriaFinanceira, db: Session, usuario_id: int
) -> CategoriaFinanceiraResponse:
    """Converte CategoriaFinanceira para Response com informações adicionais"""
    tem_subcategorias = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.categoria_pai_id == categoria.id,
            CategoriaFinanceira.tenant_id == categoria.tenant_id,
        )
        .count()
        > 0
    )

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
        tem_subcategorias=tem_subcategorias,
        pode_editar=categoria.user_id == usuario_id,
    )


def _nome_financeiro_duplicado(
    db: Session,
    *,
    tenant_id,
    tipo: str,
    categoria_pai_id: int | None,
    nome: str,
    ignorar_id: int | None = None,
) -> bool:
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == tenant_id,
        CategoriaFinanceira.tipo == tipo,
        CategoriaFinanceira.ativo.is_(True),
    )
    if categoria_pai_id is None:
        query = query.filter(CategoriaFinanceira.categoria_pai_id.is_(None))
    else:
        query = query.filter(CategoriaFinanceira.categoria_pai_id == categoria_pai_id)
    nome_normalizado = normalizar_nome_categoria(nome)
    return any(
        categoria.id != ignorar_id
        and normalizar_nome_categoria(categoria.nome) == nome_normalizado
        for categoria in query.all()
    )


# ==================== Endpoints ====================


@router.get("", response_model=List[CategoriaFinanceiraResponse])
def listar_categorias(
    tipo: Optional[str] = None,
    apenas_ativas: bool = True,
    apenas_raiz: bool = False,
    categoria_pai_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista categorias financeiras com filtros
    - tipo: 'receita' ou 'despesa'
    - apenas_ativas: Filtrar apenas categorias ativas
    - apenas_raiz: Retorna apenas categorias raiz (sem pai)
    - categoria_pai_id: Retorna subcategorias de uma categoria específica
    """
    current_user, tenant_id = user_and_tenant

    logger.info("listar_categorias", "\n🔍 [CATEGORIAS] Listando categorias:")
    logger.info("user_info", f"  👤 User ID: {current_user.id}")
    logger.info("tenant_info", f"  🏢 Tenant ID: {tenant_id}")
    logger.info("filter_tipo", f"  📊 Tipo: {tipo}")
    logger.info("filter_ativas", f"  ✅ Apenas Ativas: {apenas_ativas}")
    logger.info("filter_raiz", f"  🌳 Apenas Raiz: {apenas_raiz}")
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == tenant_id
    )

    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)

    if apenas_ativas:
        query = query.filter(CategoriaFinanceira.ativo.is_(True))

    if apenas_raiz:
        query = query.filter(CategoriaFinanceira.categoria_pai_id.is_(None))
    elif categoria_pai_id is not None:
        query = query.filter(CategoriaFinanceira.categoria_pai_id == categoria_pai_id)

    categorias = query.order_by(CategoriaFinanceira.nome).all()

    logger.info("total_encontrado", f"  📋 Total encontrado: {len(categorias)}")
    for cat in categorias[:5]:  # Mostra apenas as 5 primeiras
        logger.info("categoria_item", f"    - {cat.nome} ({cat.tipo})")
    if len(categorias) > 5:
        logger.info(
            "categoria_mais", f"    ... e mais {len(categorias) - 5} categorias"
        )

    resultado = [
        categoria_para_response(cat, db, current_user.id) for cat in categorias
    ]
    logger.info("resultado_final", f"  ✅ Retornando {len(resultado)} categorias\n")

    return resultado


@router.get("/arvore", response_model=List[CategoriaFinanceiraResponse])
def listar_categorias_arvore(
    tipo: Optional[str] = None,
    apenas_ativas: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna todas as categorias hierarquicamente
    """
    current_user, tenant_id = user_and_tenant

    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == tenant_id
    )

    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)

    if apenas_ativas:
        query = query.filter(CategoriaFinanceira.ativo.is_(True))

    categorias = query.all()

    # Ordenar por nível e nome para exibição hierárquica
    categorias_response = [
        categoria_para_response(cat, db, current_user.id) for cat in categorias
    ]
    categorias_response.sort(key=lambda x: (x.nivel, x.caminho_completo))

    return categorias_response


@router.get("/{categoria_id}", response_model=CategoriaFinanceiraResponse)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna uma categoria específica"""
    current_user, tenant_id = user_and_tenant

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            and_(
                CategoriaFinanceira.id == categoria_id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    return categoria_para_response(categoria, db, current_user.id)


@router.post("", response_model=CategoriaFinanceiraResponse)
def criar_categoria(
    categoria_data: CategoriaFinanceiraCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova categoria financeira"""
    current_user, tenant_id = user_and_tenant
    nome = categoria_data.nome.strip()
    if not normalizar_nome_categoria(nome):
        raise HTTPException(status_code=400, detail="Informe o nome da categoria")

    # Validar categoria pai se fornecida
    if categoria_data.categoria_pai_id:
        pai = (
            db.query(CategoriaFinanceira)
            .filter(
                and_(
                    CategoriaFinanceira.id == categoria_data.categoria_pai_id,
                    CategoriaFinanceira.user_id == current_user.id,
                    CategoriaFinanceira.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai não encontrada")

        # Validar que a categoria pai é do mesmo tipo
        if pai.tipo != categoria_data.tipo:
            raise HTTPException(
                status_code=400,
                detail="Categoria pai deve ser do mesmo tipo (receita/despesa)",
            )

    if categoria_data.ativo and _nome_financeiro_duplicado(
        db,
        tenant_id=tenant_id,
        tipo=categoria_data.tipo,
        categoria_pai_id=categoria_data.categoria_pai_id,
        nome=nome,
    ):
        raise HTTPException(status_code=409, detail="Categoria financeira já existe")

    categoria = CategoriaFinanceira(
        **{**categoria_data.model_dump(), "nome": nome},
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(categoria)
    db.flush()  # Flush para gerar o ID antes da validação

    # Validar vínculo com DRE
    validar_categoria_financeira_dre(
        db=db,
        categoria_financeira_id=categoria.id,
        dre_subcategoria_id=getattr(categoria_data, "dre_subcategoria_id", None),
        tenant_id=tenant_id,
    )

    db.commit()
    db.refresh(categoria)

    return categoria_para_response(categoria, db, current_user.id)


@router.put("/{categoria_id}", response_model=CategoriaFinanceiraResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria_data: CategoriaFinanceiraUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza uma categoria existente"""
    current_user, tenant_id = user_and_tenant

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            and_(
                CategoriaFinanceira.id == categoria_id,
                CategoriaFinanceira.user_id == current_user.id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    # Validar a árvore e o nome antes de aplicar qualquer alteração.
    update_data = categoria_data.model_dump(exclude_unset=True)
    if "nome" in update_data:
        if not update_data["nome"] or not normalizar_nome_categoria(
            update_data["nome"]
        ):
            raise HTTPException(status_code=400, detail="Informe o nome da categoria")
        update_data["nome"] = update_data["nome"].strip()
    if "tipo" in update_data and update_data["tipo"] != categoria.tipo:
        raise HTTPException(
            status_code=400,
            detail="O tipo da categoria não pode ser alterado após a criação",
        )

    tipo_novo = update_data.get("tipo", categoria.tipo)
    pai_id_novo = update_data.get("categoria_pai_id", categoria.categoria_pai_id)
    nome_novo = update_data.get("nome", categoria.nome)
    ativo_novo = update_data.get("ativo", categoria.ativo)

    if "categoria_pai_id" in update_data or "tipo" in update_data:
        if pai_id_novo:
            pai = (
                db.query(CategoriaFinanceira)
                .filter(
                    CategoriaFinanceira.id == pai_id_novo,
                    CategoriaFinanceira.user_id == current_user.id,
                    CategoriaFinanceira.tenant_id == tenant_id,
                )
                .first()
            )
            if not pai:
                raise HTTPException(
                    status_code=404, detail="Categoria pai não encontrada"
                )
            if pai.tipo != tipo_novo:
                raise HTTPException(
                    status_code=400,
                    detail="Categoria pai deve ser do mesmo tipo (receita/despesa)",
                )

            visitados = set()
            ancestral_id = pai_id_novo
            while ancestral_id:
                if ancestral_id == categoria_id or ancestral_id in visitados:
                    raise HTTPException(
                        status_code=400,
                        detail="Categoria não pode criar ciclo na árvore",
                    )
                visitados.add(ancestral_id)
                ancestral = (
                    db.query(CategoriaFinanceira)
                    .filter(
                        CategoriaFinanceira.id == ancestral_id,
                        CategoriaFinanceira.tenant_id == tenant_id,
                    )
                    .first()
                )
                if not ancestral:
                    raise HTTPException(
                        status_code=400, detail="Árvore de categorias inválida"
                    )
                ancestral_id = ancestral.categoria_pai_id

    chave_alterada = (
        normalizar_nome_categoria(nome_novo)
        != normalizar_nome_categoria(categoria.nome)
        or tipo_novo != categoria.tipo
        or pai_id_novo != categoria.categoria_pai_id
        or (ativo_novo and not categoria.ativo)
    )
    if (
        ativo_novo
        and chave_alterada
        and _nome_financeiro_duplicado(
            db,
            tenant_id=tenant_id,
            tipo=tipo_novo,
            categoria_pai_id=pai_id_novo,
            nome=nome_novo,
            ignorar_id=categoria_id,
        )
    ):
        raise HTTPException(status_code=409, detail="Categoria financeira já existe")

    for key, value in update_data.items():
        setattr(categoria, key, value)

    # Propagar tipo_custo 'fixo'/'variavel' para filhos diretos
    if "tipo_custo" in update_data and update_data["tipo_custo"] in (
        "fixo",
        "variavel",
    ):
        filhos = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.categoria_pai_id == categoria_id,
                CategoriaFinanceira.user_id == current_user.id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
            .all()
        )
        for filho in filhos:
            filho.tipo_custo = update_data["tipo_custo"]

    # Validar vínculo com DRE se foi alterado
    if "dre_subcategoria_id" in update_data:
        validar_categoria_financeira_dre(
            db=db,
            categoria_financeira_id=categoria.id,
            dre_subcategoria_id=update_data.get("dre_subcategoria_id"),
            tenant_id=tenant_id,
        )

    db.commit()
    db.refresh(categoria)

    return categoria_para_response(categoria, db, current_user.id)


@router.delete("/{categoria_id}")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativa uma categoria (soft delete)"""
    current_user, tenant_id = user_and_tenant

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            and_(
                CategoriaFinanceira.id == categoria_id,
                CategoriaFinanceira.user_id == current_user.id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    # Verificar se tem subcategorias ativas
    subcategorias_ativas = (
        db.query(CategoriaFinanceira)
        .filter(
            and_(
                CategoriaFinanceira.categoria_pai_id == categoria_id,
                CategoriaFinanceira.tenant_id == tenant_id,
                CategoriaFinanceira.ativo.is_(True),
            )
        )
        .count()
    )

    if subcategorias_ativas > 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível desativar categoria com subcategorias ativas",
        )

    categoria.ativo = False
    db.commit()

    return {"message": "Categoria desativada com sucesso"}


@router.get("/{categoria_id}/subcategorias-dre")
def listar_subcategorias_dre_da_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna as subcategorias DRE vinculadas a uma categoria financeira específica
    """
    from app.dre_plano_contas_models import DRESubcategoria

    _current_user, tenant_id = user_and_tenant

    # Consultas de categorias financeiras são compartilhadas dentro do tenant.
    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            and_(
                CategoriaFinanceira.id == categoria_id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    # Se a categoria não tem dre_subcategoria_id, retorna lista vazia
    if not categoria.dre_subcategoria_id:
        return []

    # Buscar a subcategoria DRE vinculada
    subcategoria_dre = (
        db.query(DRESubcategoria)
        .filter(
            and_(
                DRESubcategoria.id == categoria.dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not subcategoria_dre:
        return []

    # Retornar como lista (pode ser expandido no futuro para múltiplas subcategorias)
    return [subcategoria_dre]
