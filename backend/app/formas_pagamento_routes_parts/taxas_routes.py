"""Rotas de taxas por forma de pagamento."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.formas_pagamento_models import FormaPagamentoTaxa
from app.security.permissions_decorator import (
    require_any_permission,
    require_permission,
)

from .schemas import FormaPagamentoTaxaCreate, FormaPagamentoTaxaResponse

router = APIRouter()


@router.post("/taxas", response_model=FormaPagamentoTaxaResponse)
@require_permission("configuracoes.editar")
def criar_taxa(
    taxa: FormaPagamentoTaxaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Criar nova taxa para forma de pagamento"""
    current_user, tenant_id = user_and_tenant

    # Verificar se forma de pagamento existe
    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.id == taxa.forma_pagamento_id,
            FormaPagamento.tenant_id == tenant_id,
        )
        .first()
    )
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")

    # Verificar se já existe taxa para esse número de parcelas
    taxa_existente = (
        db.query(FormaPagamentoTaxa)
        .filter(
            FormaPagamentoTaxa.tenant_id == tenant_id,
            FormaPagamentoTaxa.forma_pagamento_id == taxa.forma_pagamento_id,
            FormaPagamentoTaxa.parcelas == taxa.parcelas,
        )
        .first()
    )

    if taxa_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe taxa cadastrada para {taxa.parcelas}x nesta forma de pagamento",
        )

    nova_taxa = FormaPagamentoTaxa(
        tenant_id=tenant_id,
        forma_pagamento_id=taxa.forma_pagamento_id,
        parcelas=taxa.parcelas,
        taxa_percentual=taxa.taxa_percentual,
        descricao=taxa.descricao,
    )

    db.add(nova_taxa)
    db.commit()
    db.refresh(nova_taxa)

    return nova_taxa


@router.get(
    "/taxas/{forma_pagamento_id}", response_model=List[FormaPagamentoTaxaResponse]
)
@require_any_permission(("vendas.criar", "configuracoes.editar"))
def listar_taxas(
    forma_pagamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar todas as taxas de uma forma de pagamento"""
    current_user, tenant_id = user_and_tenant

    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.id == forma_pagamento_id,
            FormaPagamento.tenant_id == tenant_id,
        )
        .first()
    )
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento nao encontrada")

    taxas = (
        db.query(FormaPagamentoTaxa)
        .filter(
            FormaPagamentoTaxa.tenant_id == tenant_id,
            FormaPagamentoTaxa.forma_pagamento_id == forma_pagamento_id,
        )
        .order_by(FormaPagamentoTaxa.parcelas)
        .all()
    )

    return taxas


@router.put("/taxas/{taxa_id}", response_model=FormaPagamentoTaxaResponse)
@require_permission("configuracoes.editar")
def atualizar_taxa(
    taxa_id: int,
    taxa_data: FormaPagamentoTaxaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualizar taxa existente"""
    current_user, tenant_id = user_and_tenant

    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.id == taxa_data.forma_pagamento_id,
            FormaPagamento.tenant_id == tenant_id,
        )
        .first()
    )
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento nao encontrada")

    taxa = (
        db.query(FormaPagamentoTaxa)
        .filter(
            FormaPagamentoTaxa.id == taxa_id,
            FormaPagamentoTaxa.tenant_id == tenant_id,
        )
        .first()
    )
    if not taxa:
        raise HTTPException(status_code=404, detail="Taxa não encontrada")

    taxa.parcelas = taxa_data.parcelas
    taxa.taxa_percentual = taxa_data.taxa_percentual
    taxa.descricao = taxa_data.descricao
    taxa.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(taxa)

    return taxa


@router.delete("/taxas/{taxa_id}")
@require_permission("configuracoes.editar")
def deletar_taxa(
    taxa_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deletar taxa"""
    current_user, tenant_id = user_and_tenant

    taxa = (
        db.query(FormaPagamentoTaxa)
        .filter(
            FormaPagamentoTaxa.id == taxa_id,
            FormaPagamentoTaxa.tenant_id == tenant_id,
        )
        .first()
    )
    if not taxa:
        raise HTTPException(status_code=404, detail="Taxa não encontrada")

    db.delete(taxa)
    db.commit()

    return {"message": "Taxa deletada com sucesso"}
