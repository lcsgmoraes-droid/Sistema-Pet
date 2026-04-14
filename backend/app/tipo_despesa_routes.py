"""
Rotas para Tipos de Despesa
Define se cada tipo é FIXO ou VARIÁVEL — base para cálculo do Ponto de Equilíbrio.

Exemplos pré-cadastrados:
  Aluguel           → Fixo
  Salários          → Fixo
  Impostos / DAS    → Fixo
  Energia Elétrica  → Fixo
  Internet / Telefone → Fixo
  Fornecedor de Produto para Revenda → Variável
  Frete de Compra   → Variável
  Comissões         → Variável
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .financeiro_models import TipoDespesa
from .dre_plano_contas_models import DRESubcategoria

router = APIRouter(prefix="/cadastros/tipo-despesa", tags=["Cadastros - Tipo de Despesa"])

# ===================== SCHEMAS =====================

class TipoDespesaCreate(BaseModel):
    nome: str
    e_custo_fixo: bool  # True = Fixo, False = Variável
    dre_subcategoria_id: int

class TipoDespesaUpdate(BaseModel):
    nome: Optional[str] = None
    e_custo_fixo: Optional[bool] = None
    dre_subcategoria_id: Optional[int] = None
    ativo: Optional[bool] = None

class TipoDespesaResponse(BaseModel):
    id: int
    nome: str
    e_custo_fixo: bool
    dre_subcategoria_id: int
    ativo: bool
    model_config = {"from_attributes": True}

# ===================== TIPOS PADRÃO A CRIAR NO PRIMEIRO ACESSO =====================

TIPOS_PADRAO = [
    # Fixos
    {"nome": "Aluguel",                           "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Salários e Encargos",               "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Impostos / DAS Simples Nacional",   "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Energia Elétrica",                  "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Internet / Telefone",               "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Água",                              "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Contador / Assessoria Contábil",    "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Sistema / Software",                "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Seguro",                            "e_custo_fixo": True, "dre_subcategoria_id": 2},
    {"nome": "Marketing / Publicidade Fixo",      "e_custo_fixo": True, "dre_subcategoria_id": 2},
    # Variáveis
    {"nome": "Fornecedor de Produto para Revenda","e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Frete de Compra",                   "e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Comissões de Vendas",               "e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Embalagens",                        "e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Marketing / Anúncios por Resultado","e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Outros Custos Variáveis",           "e_custo_fixo": False, "dre_subcategoria_id": 2},
    {"nome": "Outros Custos Fixos",               "e_custo_fixo": True, "dre_subcategoria_id": 2},
]

# ===================== ENDPOINTS =====================

@router.get("/", response_model=List[TipoDespesaResponse])
def listar_tipos_despesa(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Lista todos os tipos de despesa do tenant.
    Na primeira chamada, cria automaticamente os tipos padrão se não existir nenhum.
    """
    _, tenant_id = user_and_tenant

    tipos = db.query(TipoDespesa).filter(
        TipoDespesa.tenant_id == tenant_id
    ).order_by(TipoDespesa.e_custo_fixo.desc(), TipoDespesa.nome).all()

    # Seed automático na primeira vez
    if not tipos:
        for t in TIPOS_PADRAO:
            novo = TipoDespesa(tenant_id=tenant_id, **t)
            db.add(novo)
        db.commit()
        tipos = db.query(TipoDespesa).filter(
            TipoDespesa.tenant_id == tenant_id
        ).order_by(TipoDespesa.e_custo_fixo.desc(), TipoDespesa.nome).all()

    return tipos


@router.post("/", response_model=TipoDespesaResponse, status_code=201)
def criar_tipo_despesa(
    data: TipoDespesaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    subcategoria = db.query(DRESubcategoria).filter(
        DRESubcategoria.id == data.dre_subcategoria_id,
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.ativo.is_(True),
    ).first()
    if not subcategoria:
        raise HTTPException(status_code=400, detail="Subcategoria DRE inválida")

    novo = TipoDespesa(
        tenant_id=tenant_id,
        nome=data.nome,
        e_custo_fixo=data.e_custo_fixo,
        dre_subcategoria_id=data.dre_subcategoria_id,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.put("/{tipo_id}", response_model=TipoDespesaResponse)
def atualizar_tipo_despesa(
    tipo_id: int,
    data: TipoDespesaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tipo = db.query(TipoDespesa).filter(
        TipoDespesa.id == tipo_id,
        TipoDespesa.tenant_id == tenant_id,
    ).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de despesa não encontrado")
    if data.nome is not None:
        tipo.nome = data.nome
    if data.e_custo_fixo is not None:
        tipo.e_custo_fixo = data.e_custo_fixo
    if data.dre_subcategoria_id is not None:
        subcategoria = db.query(DRESubcategoria).filter(
            DRESubcategoria.id == data.dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        ).first()
        if not subcategoria:
            raise HTTPException(status_code=400, detail="Subcategoria DRE inválida")
        tipo.dre_subcategoria_id = data.dre_subcategoria_id
    if data.ativo is not None:
        tipo.ativo = data.ativo
    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/{tipo_id}", status_code=204)
def excluir_tipo_despesa(
    tipo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tipo = db.query(TipoDespesa).filter(
        TipoDespesa.id == tipo_id,
        TipoDespesa.tenant_id == tenant_id,
    ).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de despesa não encontrado")
    # Desativa ao invés de deletar para não quebrar histórico
    tipo.ativo = False
    db.commit()
