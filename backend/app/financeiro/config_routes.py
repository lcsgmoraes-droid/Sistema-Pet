"""Rotas de categorias financeiras e formas de pagamento."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.common import financeiro_erp_required
from app.financeiro_models import CategoriaFinanceira, FormaPagamento
from app.security.permissions_decorator import (
    require_any_permission,
    require_permission,
)

router = APIRouter()


class CategoriaCreate(BaseModel):
    nome: str
    tipo: str  # receita ou despesa
    cor: Optional[str] = None
    categoria_pai_id: Optional[int] = None


class FormaPagamentoCreate(BaseModel):
    nome: str
    tipo: str  # dinheiro, cartao_credito, cartao_debito, pix, boleto, transferencia

    # Taxas e prazos
    taxa_percentual: float = 0
    taxa_fixa: float = 0
    prazo_dias: int = 0

    # Configurações
    operadora: Optional[str] = (
        None  # Stone, Cielo, Rede, etc (LEGACY - usar operadora_id)
    )
    operadora_id: Optional[int] = None  # FK para operadoras_cartao
    gera_contas_receber: bool = False
    split_parcelas: bool = False
    conta_bancaria_destino_id: Optional[int] = None
    requer_nsu: bool = False
    tipo_cartao: Optional[str] = None  # debito, credito, voucher
    bandeira: Optional[str] = None  # visa, master, elo, amex

    # Parcelamento
    ativo: bool = True
    permite_parcelamento: bool = False
    parcelas_maximas: int = 1
    taxas_por_parcela: Optional[str] = None  # JSON string com taxas por parcela

    # Antecipação
    permite_antecipacao: bool = False
    dias_recebimento_antecipado: Optional[int] = None
    taxa_antecipacao_percentual: Optional[float] = None  # Taxa adicional de antecipação

    # UI
    icone: Optional[str] = None
    cor: Optional[str] = None


class FormaPagamentoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    taxa_percentual: float
    taxa_fixa: float
    prazo_dias: int
    operadora: Optional[str]
    operadora_id: Optional[int]
    gera_contas_receber: Optional[bool] = False
    split_parcelas: Optional[bool] = False
    conta_bancaria_destino_id: Optional[int]
    requer_nsu: Optional[bool] = False
    tipo_cartao: Optional[str]
    bandeira: Optional[str]
    ativo: Optional[bool] = True
    permite_parcelamento: Optional[bool] = False
    parcelas_maximas: Optional[int] = 1
    taxas_por_parcela: Optional[str]
    permite_antecipacao: Optional[bool] = False
    dias_recebimento_antecipado: Optional[int] = None
    taxa_antecipacao_percentual: Optional[float] = None
    icone: Optional[str]
    cor: Optional[str]

    model_config = {"from_attributes": True}


# ============================================================================
# CATEGORIAS FINANCEIRAS
# ============================================================================


@router.get("/categorias")
def listar_categorias(
    tipo: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
    _module_access: None = financeiro_erp_required,
):
    """
    Lista todas as categorias financeiras
    """
    current_user, tenant_id = current_user_and_tenant
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == tenant_id
    )

    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)

    categorias = query.order_by(CategoriaFinanceira.nome).all()

    return [
        {
            "id": c.id,
            "nome": c.nome,
            "tipo": c.tipo,
            "cor": c.cor,
            "categoria_pai_id": c.categoria_pai_id,
            "ativo": c.ativo,
        }
        for c in categorias
    ]


@router.post("/categorias", status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
    _module_access: None = financeiro_erp_required,
):
    """
    Cria nova categoria financeira
    """
    current_user, tenant_id = current_user_and_tenant
    nova_categoria = CategoriaFinanceira(
        nome=categoria.nome,
        tipo=categoria.tipo,
        cor=categoria.cor,
        categoria_pai_id=categoria.categoria_pai_id,
        tenant_id=tenant_id,
    )
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return {
        "id": nova_categoria.id,
        "nome": nova_categoria.nome,
        "tipo": nova_categoria.tipo,
    }


@router.put("/categorias/{categoria_id}")
def atualizar_categoria(
    categoria_id: int,
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
    _module_access: None = financeiro_erp_required,
):
    """
    Atualiza categoria financeira
    """
    current_user, tenant_id = current_user_and_tenant
    cat = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.tenant_id == tenant_id,
        )
        .first()
    )

    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    cat.nome = categoria.nome
    cat.tipo = categoria.tipo
    if categoria.cor:
        cat.cor = categoria.cor
    cat.categoria_pai_id = categoria.categoria_pai_id

    db.commit()

    return {"message": "Categoria atualizada"}


@router.delete("/categorias/{categoria_id}")
def desativar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
    _module_access: None = financeiro_erp_required,
):
    """
    Desativa uma categoria (não exclui, apenas marca como inativa)
    """
    current_user, tenant_id = current_user_and_tenant
    cat = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.tenant_id == tenant_id,
        )
        .first()
    )

    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    cat.ativo = False
    db.commit()

    return {"message": "Categoria desativada"}


# ============================================================================
# FORMAS DE PAGAMENTO
# ============================================================================


@router.get("/formas-pagamento", response_model=List[FormaPagamentoResponse])
@require_any_permission(("vendas.criar", "configuracoes.editar"))
def listar_formas_pagamento(
    apenas_ativas: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as formas de pagamento com todos os campos
    """
    current_user, tenant_id = user_and_tenant
    query = db.query(FormaPagamento).filter(FormaPagamento.tenant_id == tenant_id)

    if apenas_ativas:
        query = query.filter(FormaPagamento.ativo.is_(True))

    formas = query.order_by(FormaPagamento.nome).all()

    # Converter valores de centavos para reais
    for f in formas:
        if f.taxa_fixa:
            f.taxa_fixa = f.taxa_fixa / 100
        if f.taxa_percentual:
            f.taxa_percentual = float(f.taxa_percentual)

    return formas


@router.post(
    "/formas-pagamento",
    response_model=FormaPagamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("configuracoes.editar")
def criar_forma_pagamento(
    forma: FormaPagamentoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria nova forma de pagamento com todos os campos
    """
    current_user, tenant_id = user_and_tenant
    nova_forma = FormaPagamento(
        nome=forma.nome,
        tipo=forma.tipo,
        taxa_percentual=forma.taxa_percentual,
        taxa_fixa=forma.taxa_fixa,
        prazo_dias=forma.prazo_dias,
        prazo_recebimento=forma.prazo_dias,  # Compatibilidade
        operadora=forma.operadora,
        operadora_id=forma.operadora_id,
        gera_contas_receber=forma.gera_contas_receber,
        split_parcelas=forma.split_parcelas,
        conta_bancaria_destino_id=forma.conta_bancaria_destino_id,
        requer_nsu=forma.requer_nsu,
        tipo_cartao=forma.tipo_cartao,
        bandeira=forma.bandeira,
        ativo=forma.ativo,
        permite_parcelamento=forma.permite_parcelamento,
        max_parcelas=forma.parcelas_maximas,
        parcelas_maximas=forma.parcelas_maximas,  # Compatibilidade
        taxas_por_parcela=forma.taxas_por_parcela,  # JSON string
        permite_antecipacao=forma.permite_antecipacao,
        dias_recebimento_antecipado=forma.dias_recebimento_antecipado,
        taxa_antecipacao_percentual=forma.taxa_antecipacao_percentual,
        icone=forma.icone,
        cor=forma.cor,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(nova_forma)
    db.commit()
    db.refresh(nova_forma)

    return nova_forma


@router.put("/formas-pagamento/{forma_id}", response_model=FormaPagamentoResponse)
@require_permission("configuracoes.editar")
def atualizar_forma_pagamento(
    forma_id: int,
    forma: FormaPagamentoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza forma de pagamento com todos os campos
    """
    current_user, tenant_id = user_and_tenant
    f = (
        db.query(FormaPagamento)
        .filter(FormaPagamento.id == forma_id, FormaPagamento.tenant_id == tenant_id)
        .first()
    )

    if not f:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")

    # Atualizar todos os campos
    f.nome = forma.nome
    f.tipo = forma.tipo
    f.taxa_percentual = forma.taxa_percentual
    f.taxa_fixa = forma.taxa_fixa
    f.prazo_dias = forma.prazo_dias
    f.prazo_recebimento = forma.prazo_dias
    f.operadora = forma.operadora
    f.operadora_id = forma.operadora_id
    f.gera_contas_receber = forma.gera_contas_receber
    f.split_parcelas = forma.split_parcelas
    f.conta_bancaria_destino_id = forma.conta_bancaria_destino_id
    f.requer_nsu = forma.requer_nsu
    f.tipo_cartao = forma.tipo_cartao
    f.bandeira = forma.bandeira
    f.ativo = forma.ativo
    f.permite_parcelamento = forma.permite_parcelamento
    f.max_parcelas = forma.parcelas_maximas
    f.parcelas_maximas = forma.parcelas_maximas
    f.taxas_por_parcela = forma.taxas_por_parcela  # JSON string
    f.permite_antecipacao = forma.permite_antecipacao
    f.dias_recebimento_antecipado = forma.dias_recebimento_antecipado
    f.taxa_antecipacao_percentual = forma.taxa_antecipacao_percentual
    f.icone = forma.icone
    f.cor = forma.cor

    db.commit()
    db.refresh(f)

    # Converter de volta para resposta
    f.taxa_fixa = f.taxa_fixa / 100

    return f


@router.delete("/formas-pagamento/{forma_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("configuracoes.editar")
def excluir_forma_pagamento(
    forma_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui permanentemente uma forma de pagamento
    """
    current_user, tenant_id = user_and_tenant

    forma = (
        db.query(FormaPagamento)
        .filter(FormaPagamento.id == forma_id, FormaPagamento.tenant_id == tenant_id)
        .first()
    )

    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")

    # Hard delete - remove permanentemente do banco
    db.delete(forma)
    db.commit()

    return None
