"""
🎯 SPRINT 2: ENDPOINTS DE PRODUTOS COM VARIAÇÃO
Gerenciamento completo de variações de produtos
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.produtos_models import Produto
from app.utils.product_variation import build_variation_signature, validate_variation_attributes

router = APIRouter(prefix="/produtos", tags=["Produtos - Variações"])


# ========== SCHEMAS ==========

class VariationAttributesSchema(BaseModel):
    """Atributos de variação (Ex: cor, tamanho, voltagem)"""
    attributes: Dict[str, str] = Field(..., description="Dicionário de atributos: {'cor': 'azul', 'tamanho': 'G'}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "attributes": {
                    "cor": "Azul",
                    "tamanho": "G"
                }
            }
        }


class VariationCreateSchema(BaseModel):
    """Schema para criar variação"""
    codigo: str = Field(..., description="SKU da variação")
    nome_complemento: Optional[str] = Field(None, description="Complemento do nome (ex: '- Azul G')")
    variation_attributes: Dict[str, str] = Field(..., description="Atributos da variação")
    preco_venda: float = Field(..., description="Preço de venda da variação")
    preco_custo: Optional[float] = Field(None, description="Preço de custo")
    estoque_atual: Optional[float] = Field(0, description="Estoque inicial")
    codigo_barras: Optional[str] = Field(None, description="Código de barras")
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo": "CAM001-AZ-G",
                "nome_complemento": "- Azul G",
                "variation_attributes": {
                    "cor": "Azul",
                    "tamanho": "G"
                },
                "preco_venda": 89.90,
                "preco_custo": 45.00,
                "estoque_atual": 10,
                "codigo_barras": "7891234567890"
            }
        }


class VariationUpdateSchema(BaseModel):
    """Schema para atualizar variação"""
    nome_complemento: Optional[str] = None
    preco_venda: Optional[float] = None
    preco_custo: Optional[float] = None
    estoque_atual: Optional[float] = None
    codigo_barras: Optional[str] = None
    situacao: Optional[bool] = None


class VariationResponseSchema(BaseModel):
    """Schema de resposta da variação"""
    id: int
    codigo: str
    nome: str
    variation_attributes: Dict[str, str]
    variation_signature: str
    preco_venda: float
    preco_custo: Optional[float]
    estoque_atual: float
    codigo_barras: Optional[str]
    situacao: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== HELPER FUNCTIONS ==========

def validate_parent_product(produto_id: int, tenant_id: str, db: Session) -> Produto:
    """Valida se o produto pai existe e pode ter variações"""
    produto_pai = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto pai não encontrado")
    
    if not produto_pai.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Este produto não está configurado como produto pai (is_parent=True)"
        )
    
    return produto_pai


def validate_variation_uniqueness(
    parent_id: int,
    tenant_id: str,
    signature: str,
    db: Session,
    exclude_id: Optional[int] = None
):
    """Valida se já existe variação com a mesma assinatura"""
    query = db.query(Produto).filter(
        Produto.produto_pai_id == parent_id,
        Produto.tenant_id == tenant_id,
        Produto.variation_signature == signature
    )
    
    if exclude_id:
        query = query.filter(Produto.id != exclude_id)
    
    existing = query.first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma variação com estes atributos: {signature}"
        )


# ========== ENDPOINTS ==========

@router.post("/{parent_id}/variacoes", response_model=VariationResponseSchema, status_code=201)
def criar_variacao(
    parent_id: int,
    dados: VariationCreateSchema,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    ✨ Criar nova variação de produto
    
    **Regras:**
    - Produto pai deve ter is_parent=True
    - Assinatura da variação deve ser única no contexto do pai
    - Variação herda categoria, marca e fornecedor do pai
    """
    current_user, tenant_id = user_and_tenant
    
    # Validar produto pai
    produto_pai = validate_parent_product(parent_id, tenant_id, db)
    
    # Validar atributos
    validate_variation_attributes(dados.variation_attributes)
    
    # Gerar assinatura
    signature = build_variation_signature(dados.variation_attributes)
    
    # Validar unicidade
    validate_variation_uniqueness(parent_id, tenant_id, signature, db)
    
    # Montar nome completo
    nome_variacao = produto_pai.nome
    if dados.nome_complemento:
        nome_variacao += f" {dados.nome_complemento}"
    
    # Criar variação
    variacao = Produto(
        tenant_id=tenant_id,
        codigo=dados.codigo,
        nome=nome_variacao,
        tipo_produto='VARIACAO',
        is_parent=False,
        is_sellable=True,
        produto_pai_id=parent_id,
        variation_attributes=dados.variation_attributes,
        variation_signature=signature,
        preco_venda=dados.preco_venda,
        preco_custo=dados.preco_custo,
        estoque_atual=dados.estoque_atual or 0,
        codigo_barras=dados.codigo_barras,
        # Herdar do pai
        categoria_id=produto_pai.categoria_id,
        marca_id=produto_pai.marca_id,
        fornecedor_id=produto_pai.fornecedor_id,
        departamento_id=produto_pai.departamento_id,
        user_id=current_user.id,
        situacao=True,
        ativo=True
    )
    
    db.add(variacao)
    db.commit()
    db.refresh(variacao)
    
    return variacao


@router.get("/{parent_id}/variacoes", response_model=List[VariationResponseSchema])
def listar_variacoes(
    parent_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    📋 Listar todas as variações de um produto pai
    """
    current_user, tenant_id = user_and_tenant
    
    # Validar produto pai
    validate_parent_product(parent_id, tenant_id, db)
    
    # Buscar variações
    variacoes = db.query(Produto).filter(
        Produto.produto_pai_id == parent_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).order_by(Produto.variation_signature).all()
    
    return variacoes


@router.get("/variacoes/{variacao_id}", response_model=VariationResponseSchema)
def buscar_variacao(
    variacao_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    🔍 Buscar variação por ID
    """
    current_user, tenant_id = user_and_tenant
    
    variacao = db.query(Produto).filter(
        Produto.id == variacao_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).first()
    
    if not variacao:
        raise HTTPException(status_code=404, detail="Variação não encontrada")
    
    return variacao


@router.put("/variacoes/{variacao_id}", response_model=VariationResponseSchema)
def atualizar_variacao(
    variacao_id: int,
    dados: VariationUpdateSchema,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    ✏️ Atualizar variação existente
    
    **Nota:** Não permite alterar variation_attributes (assinatura é imutável)
    """
    current_user, tenant_id = user_and_tenant
    
    variacao = db.query(Produto).filter(
        Produto.id == variacao_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).first()
    
    if not variacao:
        raise HTTPException(status_code=404, detail="Variação não encontrada")
    
    # Atualizar campos permitidos
    if dados.nome_complemento is not None:
        produto_pai = db.query(Produto).filter(Produto.id == variacao.produto_pai_id).first()
        variacao.nome = produto_pai.nome + f" {dados.nome_complemento}"
    
    if dados.preco_venda is not None:
        variacao.preco_venda = dados.preco_venda
    
    if dados.preco_custo is not None:
        variacao.preco_custo = dados.preco_custo
    
    if dados.estoque_atual is not None:
        variacao.estoque_atual = dados.estoque_atual
    
    if dados.codigo_barras is not None:
        variacao.codigo_barras = dados.codigo_barras
    
    if dados.situacao is not None:
        variacao.situacao = dados.situacao
    
    variacao.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(variacao)
    
    return variacao


@router.delete("/variacoes/{variacao_id}", status_code=204)
def deletar_variacao(
    variacao_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    🗑️ Deletar variação
    
    **Soft delete:** Apenas desativa a variação
    """
    current_user, tenant_id = user_and_tenant
    
    variacao = db.query(Produto).filter(
        Produto.id == variacao_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).first()
    
    if not variacao:
        raise HTTPException(status_code=404, detail="Variação não encontrada")
    
    # Soft delete
    variacao.ativo = False
    variacao.deleted_at = datetime.utcnow()
    
    db.commit()
    
    return None


@router.post("/{parent_id}/converter-produto-pai", status_code=200)
def converter_produto_em_pai(
    parent_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    🔄 Converter produto simples em produto pai
    
    **Ações:**
    - Define is_parent = True
    - Define is_sellable = False
    - Limpa estoque e preço (não vendável)
    """
    current_user, tenant_id = user_and_tenant
    
    produto = db.query(Produto).filter(
        Produto.id == parent_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    if produto.is_parent:
        raise HTTPException(status_code=400, detail="Produto já é pai")
    
    if produto.produto_pai_id:
        raise HTTPException(status_code=400, detail="Este produto é uma variação, não pode ser pai")
    
    # Converter
    produto.is_parent = True
    produto.is_sellable = False
    produto.tipo_produto = 'PAI'
    produto.preco_venda = None
    produto.estoque_atual = 0
    produto.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(produto)
    
    return {
        "message": "Produto convertido para pai com sucesso",
        "produto_id": produto.id,
        "nome": produto.nome,
        "is_parent": produto.is_parent,
        "is_sellable": produto.is_sellable
    }
