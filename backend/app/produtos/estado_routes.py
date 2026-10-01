"""Rotas de atualizacao rapida, exclusao e ativacao de produtos."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.core import _aplicar_status_ativo_produto
from app.produtos.listagem import _resolver_promocao_erp_produto
from app.produtos.schemas import ProdutoAtivoUpdate, ProdutoResponse
from app.produtos.validators import (
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Produto, ProdutoHistoricoPreco
from app.security.permissions_decorator import require_permission
from app.services.kit_custo_service import KitCustoService
from app.empresa_grupo_estoque_compartilhado_service import (
    EmpresaGrupoEstoqueCompartilhadoService,
)
from app.tenancy.context import set_current_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


class PrecoEtiquetaBalancaUpdate(BaseModel):
    preco_kg_etiqueta: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    preco_kg_sistema_esperado: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    codigo_etiqueta: str = Field(pattern=r"^2\d{12}$")


@router.patch("/{produto_id}/preco-etiqueta-balanca")
@require_permission("produtos.editar")
def atualizar_preco_etiqueta_balanca(
    produto_id: int,
    payload: PrecoEtiquetaBalancaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Corrige o preco padrao de um granel apos confirmacao no PDV."""
    current_user, tenant_solicitante_id = user_and_tenant
    acesso_catalogo = EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not produto or produto.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    if not produto.ativo or produto.situacao is False:
        raise HTTPException(status_code=409, detail="O produto nao esta mais ativo.")
    if not produto.e_granel or str(produto.unidade or "").upper() != "KG":
        raise HTTPException(
            status_code=409, detail="O produto deixou de ser granel em KG."
        )
    soma_ean = sum(
        int(digito) * (1 if indice % 2 == 0 else 3)
        for indice, digito in enumerate(payload.codigo_etiqueta[:12])
    )
    if (10 - soma_ean % 10) % 10 != int(payload.codigo_etiqueta[12]):
        raise HTTPException(status_code=422, detail="Codigo da etiqueta invalido.")
    codigo_produto = str(produto.codigo or "").lstrip("0") or "0"
    codigo_etiqueta = payload.codigo_etiqueta[1:7].lstrip("0") or "0"
    if codigo_produto != codigo_etiqueta:
        raise HTTPException(
            status_code=409, detail="A etiqueta nao corresponde mais ao produto."
        )

    promocao = _resolver_promocao_erp_produto(produto)
    if promocao["promocao_ativa"]:
        raise HTTPException(
            status_code=409,
            detail="Produto com promocao ativa. Ajuste o preco promocional no cadastro.",
        )
    preco_atual = Decimal(str(promocao["preco_pdv"])).quantize(Decimal("0.01"))
    if preco_atual != payload.preco_kg_sistema_esperado:
        raise HTTPException(
            status_code=409,
            detail="O preco do cadastro mudou desde a leitura. Leia a etiqueta novamente.",
        )

    preco_novo = payload.preco_kg_etiqueta
    if preco_novo != preco_atual:
        custo = float(produto.preco_custo or 0)
        preco_anterior = float(preco_atual)
        preco_novo_float = float(preco_novo)
        produto.preco_venda = preco_novo_float
        produto.updated_at = datetime.utcnow()
        db.add(
            ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=custo,
                preco_custo_novo=custo,
                preco_venda_anterior=preco_anterior,
                preco_venda_novo=preco_novo_float,
                margem_anterior=(preco_anterior - custo) / preco_anterior * 100
                if preco_anterior > 0
                else 0,
                margem_nova=(preco_novo_float - custo) / preco_novo_float * 100,
                variacao_custo_percentual=0,
                variacao_venda_percentual=(preco_novo_float - preco_anterior)
                / preco_anterior
                * 100
                if preco_anterior > 0
                else 0,
                motivo="etiqueta_balanca_pdv",
                referencia=payload.codigo_etiqueta,
                observacoes="Preco por kg corrigido no PDV apos confirmacao do operador.",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        db.commit()
    return {"produto_id": produto.id, "preco_venda": float(preco_novo)}


@router.patch("/{produto_id}")
def atualizar_preco_produto(
    produto_id: int,
    preco_venda: Optional[float] = None,
    preco_custo: Optional[float] = None,
    preco_promocional: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o preço de um produto (edição rápida)"""

    current_user, tenant_solicitante_id = user_and_tenant
    acesso_catalogo = EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    logger.info(f"🏷️ Atualizando preço do produto {produto_id}")

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Atualizar apenas os preços fornecidos
    if preco_venda is not None:
        produto.preco_venda = preco_venda
    if preco_custo is not None:
        produto.preco_custo = preco_custo
        KitCustoService.recalcular_kits_que_usam_produto(db, produto.id)
    if preco_promocional is not None:
        produto.preco_promocional = preco_promocional

    produto.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(produto)

    logger.info(f"✅ Preço atualizado: PV={produto.preco_venda}")

    return {
        "id": produto.id,
        "preco_venda": produto.preco_venda,
        "preco_custo": produto.preco_custo,
        "preco_promocional": produto.preco_promocional,
    }


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um produto"""

    current_user, tenant_solicitante_id = _validar_tenant_e_obter_usuario(
        user_and_tenant
    )
    acesso_catalogo = EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    _validar_pode_inativar_produto(db, produto, tenant_id)

    # Soft delete
    _aplicar_status_ativo_produto(produto, False)

    db.commit()

    return None


@router.patch("/{produto_id}/ativo", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_status_ativo_produto(
    produto_id: int,
    payload: ProdutoAtivoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Ativa ou desativa produto sem removê-lo do sistema."""

    _, tenant_solicitante_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    acesso_catalogo = EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    produto = _obter_produto_ou_404(db, produto_id, tenant_id)

    if payload.ativo == bool(produto.ativo):
        return produto

    if not payload.ativo:
        _validar_pode_inativar_produto(db, produto, tenant_id)

    _aplicar_status_ativo_produto(produto, payload.ativo)

    db.commit()
    db.refresh(produto)

    logger.info(
        "🔁 Produto %s #%s com status alterado para %s",
        produto.nome,
        produto.id,
        "ativo" if payload.ativo else "inativo",
    )

    return produto
