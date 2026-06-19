"""Rotas de fornecedores vinculados a produtos."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.produtos.fornecedores import _garantir_fornecedor_principal_quando_unico
from app.produtos.schemas import (
    FornecedorVinculoCreate,
    FornecedorVinculoResponse,
    FornecedorVinculoUpdate,
)
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto, ProdutoFornecedor

logger = logging.getLogger(__name__)
router = APIRouter()


# ==========================================
# ENDPOINTS - FORNECEDORES
# ==========================================


@router.post("/{produto_id}/fornecedores", response_model=FornecedorVinculoResponse)
def vincular_fornecedor(
    produto_id: int,
    dados: FornecedorVinculoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Vincular fornecedor a um produto

    - Pode ter mÃºltiplos fornecedores por produto
    - Apenas 1 pode ser principal
    - Fornecedor deve ser do tipo 'fornecedor' no cadastro de clientes
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        logger.info(
            f"[FORNECEDOR] Vinculando fornecedor {dados.fornecedor_id} ao produto {produto_id}"
        )

        # Verificar se produto existe e pertence ao usuÃ¡rio
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.tenant_id == tenant_id,
                Produto.situacao.is_(True),
            )
            .first()
        )

        if not produto:
            logger.error(f"[FORNECEDOR] Produto {produto_id} nÃ£o encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
            )

        logger.info(f"[FORNECEDOR] Produto encontrado: {produto.nome}")

        # Verificar se fornecedor existe e pertence ao usuÃ¡rio
        fornecedor = (
            db.query(Cliente)
            .filter(
                Cliente.id == dados.fornecedor_id,
                Cliente.tenant_id == tenant_id,
                Cliente.tipo_cadastro == "fornecedor",
            )
            .first()
        )

        if not fornecedor:
            logger.error(
                f"[FORNECEDOR] Fornecedor {dados.fornecedor_id} nÃ£o encontrado"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nÃ£o encontrado ou nÃ£o Ã© do tipo fornecedor",
            )

        logger.info(f"[FORNECEDOR] Fornecedor encontrado: {fornecedor.nome}")

        # Verificar se jÃ¡ existe vÃ­nculo
        vinculo_existente = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.fornecedor_id == dados.fornecedor_id,
            )
            .first()
        )

        if vinculo_existente:
            logger.error("[FORNECEDOR] VÃ­nculo jÃ¡ existe")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fornecedor jÃ¡ vinculado a este produto",
            )

        vinculos_ativos_existentes = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.ativo.is_(True),
            )
            .count()
        )
        sera_principal = bool(dados.e_principal) or vinculos_ativos_existentes == 0

        # Se for marcar como principal, desmarcar outros
        if sera_principal:
            logger.info("[FORNECEDOR] Desmarcando outros fornecedores principais")
            db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.e_principal.is_(True),
            ).update({"e_principal": False})

            # Atualizar fornecedor_id do produto
            produto.fornecedor_id = dados.fornecedor_id

        # Criar vÃ­nculo
        logger.info("[FORNECEDOR] Criando vÃ­nculo no banco")
        novo_vinculo = ProdutoFornecedor(
            produto_id=produto_id,
            fornecedor_id=dados.fornecedor_id,
            codigo_fornecedor=dados.codigo_fornecedor,
            preco_custo=dados.preco_custo,
            prazo_entrega=dados.prazo_entrega,
            estoque_fornecedor=dados.estoque_fornecedor,
            e_principal=sera_principal,
            tenant_id=tenant_id,
        )

        db.add(novo_vinculo)
        db.flush()
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)
        db.commit()
        db.refresh(novo_vinculo)

        logger.info(f"[FORNECEDOR] VÃ­nculo criado com ID {novo_vinculo.id}")

        # Montar resposta com dados do fornecedor
        response = FornecedorVinculoResponse(
            id=novo_vinculo.id,
            produto_id=novo_vinculo.produto_id,
            fornecedor_id=novo_vinculo.fornecedor_id,
            codigo_fornecedor=novo_vinculo.codigo_fornecedor,
            preco_custo=novo_vinculo.preco_custo,
            prazo_entrega=novo_vinculo.prazo_entrega,
            estoque_fornecedor=novo_vinculo.estoque_fornecedor,
            e_principal=novo_vinculo.e_principal,
            ativo=novo_vinculo.ativo,
            created_at=novo_vinculo.created_at,
            updated_at=novo_vinculo.updated_at,
            fornecedor_nome=fornecedor.nome,
            fornecedor_cpf_cnpj=fornecedor.cnpj
            if fornecedor.tipo_pessoa == "PJ"
            else fornecedor.cpf,
            fornecedor_email=fornecedor.email,
            fornecedor_telefone=fornecedor.telefone or fornecedor.celular,
        )

        logger.info("[FORNECEDOR] âœ… VÃ­nculo completado com sucesso")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORNECEDOR] âŒ ERRO: {str(e)}")
        logger.error(f"[FORNECEDOR] Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao vincular fornecedor: {str(e)}",
        )


@router.get(
    "/{produto_id}/fornecedores", response_model=List[FornecedorVinculoResponse]
)
def listar_fornecedores_produto(
    produto_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Listar todos os fornecedores vinculados a um produto
    Ordenados por: principal DESC, created_at ASC
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
        )

    # Buscar fornecedores
    query = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto_id
    )

    if apenas_ativos:
        query = query.filter(ProdutoFornecedor.ativo.is_(True))

    vinculos = query.order_by(
        ProdutoFornecedor.e_principal.desc(), ProdutoFornecedor.created_at.asc()
    ).all()

    # Montar resposta com dados dos fornecedores
    resultado = []
    for vinculo in vinculos:
        fornecedor = (
            db.query(Cliente).filter(Cliente.id == vinculo.fornecedor_id).first()
        )

        if fornecedor:
            cpf_cnpj = (
                fornecedor.cnpj if fornecedor.tipo_pessoa == "PJ" else fornecedor.cpf
            )
            telefone = fornecedor.telefone or fornecedor.celular
        else:
            cpf_cnpj = None
            telefone = None

        resultado.append(
            FornecedorVinculoResponse(
                id=vinculo.id,
                produto_id=vinculo.produto_id,
                fornecedor_id=vinculo.fornecedor_id,
                codigo_fornecedor=vinculo.codigo_fornecedor,
                preco_custo=vinculo.preco_custo,
                prazo_entrega=vinculo.prazo_entrega,
                estoque_fornecedor=vinculo.estoque_fornecedor,
                e_principal=vinculo.e_principal,
                ativo=vinculo.ativo,
                created_at=vinculo.created_at,
                updated_at=vinculo.updated_at,
                fornecedor_nome=fornecedor.nome if fornecedor else None,
                fornecedor_cpf_cnpj=cpf_cnpj,
                fornecedor_email=fornecedor.email if fornecedor else None,
                fornecedor_telefone=telefone,
            )
        )

    return resultado


@router.put("/fornecedores/{vinculo_id}", response_model=FornecedorVinculoResponse)
def atualizar_vinculo_fornecedor(
    vinculo_id: int,
    dados: FornecedorVinculoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualizar dados do vÃ­nculo fornecedor-produto
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = (
        db.query(ProdutoFornecedor)
        .join(Produto)
        .filter(ProdutoFornecedor.id == vinculo_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="VÃ­nculo nÃ£o encontrado"
        )

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == vinculo.produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    # Se for marcar como principal, desmarcar outros
    if dados.e_principal and not vinculo.e_principal:
        db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == vinculo.produto_id,
            ProdutoFornecedor.tenant_id == tenant_id,
            ProdutoFornecedor.e_principal.is_(True),
        ).update({"e_principal": False})

        if produto:
            produto.fornecedor_id = vinculo.fornecedor_id

    # Atualizar campos
    if dados.codigo_fornecedor is not None:
        vinculo.codigo_fornecedor = dados.codigo_fornecedor
    if dados.preco_custo is not None:
        vinculo.preco_custo = dados.preco_custo
    if dados.prazo_entrega is not None:
        vinculo.prazo_entrega = dados.prazo_entrega
    if dados.estoque_fornecedor is not None:
        vinculo.estoque_fornecedor = dados.estoque_fornecedor
    if dados.e_principal is not None:
        vinculo.e_principal = dados.e_principal
    if dados.ativo is not None:
        vinculo.ativo = dados.ativo

    if produto:
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)

    vinculo.updated_at = datetime.now()

    db.commit()
    db.refresh(vinculo)

    logger.info("Vinculo de fornecedor atualizado")

    # Buscar dados do fornecedor para resposta
    fornecedor = db.query(Cliente).filter(Cliente.id == vinculo.fornecedor_id).first()

    response = FornecedorVinculoResponse(
        id=vinculo.id,
        produto_id=vinculo.produto_id,
        fornecedor_id=vinculo.fornecedor_id,
        codigo_fornecedor=vinculo.codigo_fornecedor,
        preco_custo=vinculo.preco_custo,
        prazo_entrega=vinculo.prazo_entrega,
        estoque_fornecedor=vinculo.estoque_fornecedor,
        e_principal=vinculo.e_principal,
        ativo=vinculo.ativo,
        created_at=vinculo.created_at,
        updated_at=vinculo.updated_at,
        fornecedor_nome=fornecedor.nome if fornecedor else None,
        fornecedor_cpf_cnpj=fornecedor.cnpj
        if (fornecedor and fornecedor.tipo_pessoa == "PJ")
        else (fornecedor.cpf if fornecedor else None),
        fornecedor_email=fornecedor.email if fornecedor else None,
        fornecedor_telefone=(fornecedor.telefone or fornecedor.celular)
        if fornecedor
        else None,
    )

    return response


@router.delete("/fornecedores/{vinculo_id}")
def desvincular_fornecedor(
    vinculo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Desvincular fornecedor de um produto
    Remove o vÃ­nculo do banco de dados
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = (
        db.query(ProdutoFornecedor)
        .join(Produto)
        .filter(ProdutoFornecedor.id == vinculo_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="VÃ­nculo nÃ£o encontrado"
        )

    produto_id = vinculo.produto_id
    era_principal = vinculo.e_principal
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    # Deletar vÃ­nculo
    db.delete(vinculo)

    # Se era principal, tentar promover outro
    if era_principal:
        outro_vinculo = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.id != vinculo_id,
                ProdutoFornecedor.ativo.is_(True),
            )
            .first()
        )

        if outro_vinculo:
            outro_vinculo.e_principal = True
            if produto:
                produto.fornecedor_id = outro_vinculo.fornecedor_id
        else:
            # Nenhum fornecedor restante, remover do produto
            if produto:
                produto.fornecedor_id = None

    if produto:
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)

    db.commit()

    logger.info("Fornecedor desvinculado do produto")

    return {"message": "Fornecedor desvinculado com sucesso"}
