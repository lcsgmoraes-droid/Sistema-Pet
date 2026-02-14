# -*- coding: utf-8 -*-
"""
Rotas de Integração PDV com Sistema de Rações
Alertas inteligentes, sugestões e cross-sell

Versão: 1.0.0 (2026-02-14)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .produtos_models import Produto, Marca, Categoria
from .vendas_models import VendaItem, Venda

router = APIRouter(prefix="/pdv/racoes", tags=["PDV - Rações Inteligentes"])


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


# ============================================================================
# FUNÇÕES AUXILIARES DE ANÁLISE
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


# ============================================================================
# SCHEMAS
# ============================================================================

class AlertaAlergiaResponse(BaseModel):
    """Resposta de alerta de alergia"""
    tem_alerta: bool
    mensagem: Optional[str] = None
    produto_id: int
    produto_nome: str
    alergenos: List[str] = []
    pets_afetados: List[Dict[str, Any]] = []


class ProdutoSimilar(BaseModel):
    """Produto similar sugerido"""
    produto_id: int
    nome: str
    marca: str
    preco_venda: float
    preco_kg: Optional[float] = None
    similaridade_score: float
    disponivel_estoque: bool
    estoque_quantidade: Optional[float] = None


class SugestaoResponse(BaseModel):
    """Resposta de sugestões de produtos"""
    produto_base_id: int
    produto_base_nome: str
    sugestoes_similares: List[ProdutoSimilar]
    sugestoes_complementares: List[ProdutoSimilar]


class CrossSellResponse(BaseModel):
    """Resposta de cross-sell"""
    item_carrinho_id: int
    produto_id: int
    produto_nome: str
    sugestoes: List[Dict[str, Any]]


# ============================================================================
# ENDPOINTS - ALERTAS DE ALERGIA
# ============================================================================

@router.post("/verificar-alergia/{produto_id}", response_model=AlertaAlergiaResponse)
async def verificar_alergia_produto(
    produto_id: int,
    cliente_id: int = Query(..., description="ID do cliente para verificar pets"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Verifica se produto contém alergenos para pets do cliente
    
    Retorna alertas se:
    - Produto tem sabor/proteína que algum pet é alérgico
    - Produto tem ingrediente específico listado nas alergias do pet
    
    Uso no PDV: Chamar ao escanear produto no carrinho
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produto
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(404, "Produto não encontrado")
    
    # Buscar pets do cliente
    from .models import Cliente, Pet
    
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    
    pets = db.query(Pet).filter(
        Pet.cliente_id == cliente_id,
        Pet.ativo == True
    ).all()
    
    # Verificar alergias
    alergenos_produto = []
    pets_afetados = []
    
    # Adicionar sabor como alergeno se houver
    if produto.sabor_proteina:
        alergenos_produto.append(produto.sabor_proteina.lower())
    
    # Verificar cada pet
    for pet in pets:
        if not pet.alergias:
            continue
        
        # Normalizar alergias do pet (podem estar em texto livre)
        alergias_pet = []
        if isinstance(pet.alergias, str):
            alergias_pet = [a.strip().lower() for a in pet.alergias.split(',')]
        elif isinstance(pet.alergias, list):
            alergias_pet = [str(a).lower() for a in pet.alergias]
        
        # Verificar se algum alergeno do produto está nas alergias do pet
        alergias_detectadas = []
        for alergeno in alergenos_produto:
            for alergia_pet in alergias_pet:
                if alergeno in alergia_pet or alergia_pet in alergeno:
                    alergias_detectadas.append(alergeno)
        
        if alergias_detectadas:
            pets_afetados.append({
                "pet_id": pet.id,
                "pet_nome": pet.nome,
                "pet_especie": pet.especie,
                "alergias": list(set(alergias_detectadas))
            })
    
    # Montar resposta
    tem_alerta = len(pets_afetados) > 0
    mensagem = None
    
    if tem_alerta:
        if len(pets_afetados) == 1:
            pet = pets_afetados[0]
            alergias_str = ", ".join(pet["alergias"])
            mensagem = f"⚠️ ATENÇÃO: {pet['pet_nome']} tem alergia a {alergias_str}"
        else:
            mensagem = f"⚠️ ATENÇÃO: {len(pets_afetados)} pets têm alergias a ingredientes deste produto"
    
    return AlertaAlergiaResponse(
        tem_alerta=tem_alerta,
        mensagem=mensagem,
        produto_id=produto.id,
        produto_nome=produto.nome,
        alergenos=alergenos_produto,
        pets_afetados=pets_afetados
    )


# ============================================================================
# ENDPOINTS - PRODUTOS SIMILARES
# ============================================================================

@router.get("/produtos-similares/{produto_id}", response_model=SugestaoResponse)
async def obter_produtos_similares(
    produto_id: int,
    limite: int = Query(5, ge=1, le=20, description="Limite de sugestões"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Retorna produtos similares ao produto base
    
    Similaridade baseada em:
    - Mesma espécie
    - Mesmo porte
    - Mesma fase
    - Mesmo sabor (opcional)
    - Peso similar
    
    Útil para:
    - Oferecer alternativas quando produto está em falta
    - Sugerir upgrade/downgrade de linha
    - Comparar preços
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produto base
    produto_base = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto_base:
        raise HTTPException(404, "Produto não encontrado")
    
    # Query para produtos similares
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.id != produto_id,
        Produto.tipo == 'ração'
    )
    
    # Filtrar por características similares
    similares = []
    produtos_candidatos = query.all()
    
    for produto in produtos_candidatos:
        score = 0
        
        # Mesma espécie (+40 pontos)
        if produto.especie_animal and produto_base.especie_animal:
            if any(e in produto_base.especie_animal for e in produto.especie_animal):
                score += 40
        
        # Mesmo porte (+30 pontos)
        if produto.porte_animal and produto_base.porte_animal:
            if any(p in produto_base.porte_animal for p in produto.porte_animal):
                score += 30
        
        # Mesma fase (+20 pontos)
        if produto.fase_publico and produto_base.fase_publico:
            if any(f in produto_base.fase_publico for f in produto.fase_publico):
                score += 20
        
        # Mesmo sabor (+10 pontos)
        if produto.sabor_proteina and produto_base.sabor_proteina:
            if produto.sabor_proteina.lower() == produto_base.sabor_proteina.lower():
                score += 10
        
        # Peso similar (+10 pontos se dentro de 20% de diferença)
        if produto.peso_embalagem and produto_base.peso_embalagem:
            diff_peso = abs(produto.peso_embalagem - produto_base.peso_embalagem) / produto_base.peso_embalagem
            if diff_peso <= 0.2:
                score += 10
        
        # Apenas adicionar se tiver score mínimo de 40% (40 pontos)
        if score >= 40:
            preco_kg = None
            if produto.peso_embalagem and produto.peso_embalagem > 0:
                preco_kg = float(produto.preco_venda / produto.peso_embalagem)
            
            marca = db.query(Marca).filter(Marca.id == produto.marca_id).first()
            
            similares.append({
                "produto": produto,
                "marca_nome": marca.nome if marca else "Sem Marca",
                "score": score,
                "preco_kg": preco_kg
            })
    
    # Ordenar por score decrescente
    similares.sort(key=lambda x: x["score"], reverse=True)
    
    # Limitar resultados
    similares = similares[:limite]
    
    # Montar resposta
    sugestoes_lista = []
    for item in similares:
        prod = item["produto"]
        sugestoes_lista.append(ProdutoSimilar(
            produto_id=prod.id,
            nome=prod.nome,
            marca=item["marca_nome"],
            preco_venda=float(prod.preco_venda),
            preco_kg=item["preco_kg"],
            similaridade_score=item["score"],
            disponivel_estoque=prod.estoque_atual > 0,
            estoque_quantidade=float(prod.estoque_atual) if prod.estoque_atual else 0
        ))
    
    return SugestaoResponse(
        produto_base_id=produto_base.id,
        produto_base_nome=produto_base.nome,
        sugestoes_similares=sugestoes_lista,
        sugestoes_complementares=[]  # Implementar em próxima fase
    )


# ============================================================================
# ENDPOINTS - CROSS-SELL INTELIGENTE
# ============================================================================

@router.post("/cross-sell", response_model=List[CrossSellResponse])
async def obter_cross_sell(
    produtos_carrinho: List[int] = Query(..., description="IDs dos produtos no carrinho"),
    limite_por_produto: int = Query(3, ge=1, le=10),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Sugestões de cross-sell baseadas em produtos do carrinho
    
    Lógica:
    - "Clientes que compraram X também compraram Y"
    - Baseado em histórico de vendas (último ano)
    - Filtra produtos já no carrinho
    - Ordena por frequência de co-ocorrência
    
    Uso no PDV: Mostrar sugestões ao adicionar item no carrinho
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    from datetime import datetime, timedelta
    data_limite = datetime.now() - timedelta(days=365)  # Último ano
    
    sugestoes_por_produto = []
    
    for produto_id in produtos_carrinho:
        # Buscar produto
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        
        if not produto:
            continue
        
        # Buscar vendas que incluem este produto
        vendas_com_produto = db.query(Venda.id).join(
            VendaItem, VendaItem.venda_id == Venda.id
        ).filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id == produto_id,
            Venda.data_venda >= data_limite,
            Venda.status != 'cancelada'
        ).distinct().subquery()
        
        # Buscar outros produtos comprados nas mesmas vendas
        produtos_relacionados = db.query(
            VendaItem.produto_id,
            Produto.nome,
            func.count(VendaItem.id).label('frequencia')
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).join(
            Produto, VendaItem.produto_id == Produto.id
        ).filter(
            Venda.id.in_(vendas_com_produto),
            VendaItem.produto_id != produto_id,  # Excluir o produto atual
            VendaItem.produto_id.notin_(produtos_carrinho),  # Excluir produtos já no carrinho
            Produto.ativo == True,
            Produto.tipo == 'ração'
        ).group_by(
            VendaItem.produto_id,
            Produto.nome
        ).order_by(
            func.count(VendaItem.id).desc()
        ).limit(limite_por_produto).all()
        
        # Montar sugestões
        sugestoes = []
        for rel in produtos_relacionados:
            prod_relacionado = db.query(Produto).filter(Produto.id == rel.produto_id).first()
            if not prod_relacionado:
                continue
            
            marca = db.query(Marca).filter(Marca.id == prod_relacionado.marca_id).first()
            
            sugestoes.append({
                "produto_id": prod_relacionado.id,
                "nome": prod_relacionado.nome,
                "marca": marca.nome if marca else "Sem Marca",
                "preco_venda": float(prod_relacionado.preco_venda),
                "frequencia_compra_conjunta": int(rel.frequencia),
                "disponivel_estoque": prod_relacionado.estoque_atual > 0,
                "estoque_quantidade": float(prod_relacionado.estoque_atual) if prod_relacionado.estoque_atual else 0
            })
        
        if sugestoes:
            sugestoes_por_produto.append(CrossSellResponse(
                item_carrinho_id=produto.id,
                produto_id=produto.id,
                produto_nome=produto.nome,
                sugestoes=sugestoes
            ))
    
    return sugestoes_por_produto


# ============================================================================
# ENDPOINTS - PRODUTOS COMPLEMENTARES
# ============================================================================

@router.get("/produtos-complementares/{produto_id}")
async def obter_produtos_complementares(
    produto_id: int,
    limite: int = Query(5, ge=1, le=10),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Retorna produtos complementares à ração (não baseado em vendas)
    
    Sugestões fixas por categoria:
    - Ração → Potes, comedouros, bebedouros, snacks
    - Considera espécie do animal
    
    Futuro: Personalizar com preferências do cliente
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produto base
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(404, "Produto não encontrado")
    
    # Buscar categorias complementares (simplificado)
    categorias_complementares = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id,
        or_(
            Categoria.nome.ilike('%pote%'),
            Categoria.nome.ilike('%comedouro%'),
            Categoria.nome.ilike('%bebedouro%'),
            Categoria.nome.ilike('%snack%'),
            Categoria.nome.ilike('%petisco%')
        )
    ).all()
    
    categoria_ids = [c.id for c in categorias_complementares]
    
    # Buscar produtos complementares
    complementares = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.categoria_id.in_(categoria_ids)
    ).limit(limite).all()
    
    # Montar resposta
    resultado = []
    for prod in complementares:
        marca = db.query(Marca).filter(Marca.id == prod.marca_id).first()
        
        resultado.append({
            "produto_id": prod.id,
            "nome": prod.nome,
            "marca": marca.nome if marca else "Sem Marca",
            "categoria": next((c.nome for c in categorias_complementares if c.id == prod.categoria_id), "Outros"),
            "preco_venda": float(prod.preco_venda),
            "disponivel_estoque": prod.estoque_atual > 0
        })
    
    return {
        "produto_base_id": produto.id,
        "produto_base_nome": produto.nome,
        "complementares": resultado
    }
