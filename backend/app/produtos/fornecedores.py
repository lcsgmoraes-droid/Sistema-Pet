from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Cliente
from app.produtos_models import Produto, ProdutoFornecedor


OPERACOES_FORNECEDOR_LOTE = {"adicionar", "definir_principal", "remover"}


def _validar_fornecedor_produto_lote(
    db: Session,
    fornecedor_id: Optional[int],
    tenant_id,
) -> Optional[Cliente]:
    if fornecedor_id is None:
        return None

    fornecedor = db.query(Cliente).filter(
        Cliente.id == fornecedor_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "fornecedor",
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor nao encontrado ou nao e do tipo fornecedor",
        )

    return fornecedor


def _obter_vinculo_fornecedor_lote(
    db: Session,
    produto_id: int,
    fornecedor_id: int,
    tenant_id,
) -> Optional[ProdutoFornecedor]:
    return db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto_id,
        ProdutoFornecedor.fornecedor_id == fornecedor_id,
        ProdutoFornecedor.tenant_id == tenant_id,
    ).first()


def _promover_fornecedor_principal_lote(
    db: Session,
    produto: Produto,
    tenant_id,
    fornecedor_id_ignorado: Optional[int] = None,
) -> bool:
    query = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto.id,
        ProdutoFornecedor.tenant_id == tenant_id,
        ProdutoFornecedor.ativo.is_(True),
    )

    if fornecedor_id_ignorado is not None:
        query = query.filter(ProdutoFornecedor.fornecedor_id != fornecedor_id_ignorado)

    proximo_vinculo = query.order_by(
        ProdutoFornecedor.e_principal.desc(),
        ProdutoFornecedor.created_at.asc(),
    ).first()

    if proximo_vinculo:
        proximo_vinculo.e_principal = True
        produto.fornecedor_id = proximo_vinculo.fornecedor_id
        return True

    produto.fornecedor_id = None
    return True


def _remover_fornecedores_produto_lote(
    db: Session,
    produto: Produto,
    tenant_id,
    fornecedor_id: Optional[int] = None,
) -> bool:
    query = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto.id,
        ProdutoFornecedor.tenant_id == tenant_id,
    )

    if fornecedor_id is not None:
        query = query.filter(ProdutoFornecedor.fornecedor_id == fornecedor_id)

    vinculos = query.all()
    alterado = bool(vinculos)

    if fornecedor_id is None:
        if produto.fornecedor_id is not None:
            alterado = True
        for vinculo in vinculos:
            db.delete(vinculo)
        produto.fornecedor_id = None
        return alterado

    era_principal = any(bool(vinculo.e_principal) for vinculo in vinculos) or produto.fornecedor_id == fornecedor_id

    for vinculo in vinculos:
        db.delete(vinculo)

    if not alterado and not era_principal:
        return False

    if era_principal:
        _promover_fornecedor_principal_lote(
            db,
            produto,
            tenant_id,
            fornecedor_id_ignorado=fornecedor_id,
        )

    return True


def _aplicar_fornecedor_produto_lote(
    db: Session,
    produto: Produto,
    fornecedor_id: Optional[int],
    operacao: str,
    tenant_id,
    remover_outros: bool = False,
) -> bool:
    vinculo = (
        _obter_vinculo_fornecedor_lote(db, produto.id, fornecedor_id, tenant_id)
        if fornecedor_id is not None
        else None
    )

    if operacao == "adicionar":
        if fornecedor_id is None:
            return False
        if vinculo:
            alterado = not bool(vinculo.ativo)
            if vinculo.e_principal and produto.fornecedor_id != fornecedor_id:
                vinculo.e_principal = False
                alterado = True
            vinculo.ativo = True
            vinculo.updated_at = datetime.utcnow()
            return alterado

        db.add(ProdutoFornecedor(
            produto_id=produto.id,
            fornecedor_id=fornecedor_id,
            e_principal=False,
            ativo=True,
            tenant_id=tenant_id,
        ))
        return True

    if operacao == "definir_principal":
        if fornecedor_id is None:
            return False

        if remover_outros:
            outros_vinculos = db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto.id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.fornecedor_id != fornecedor_id,
            ).all()
            for outro_vinculo in outros_vinculos:
                db.delete(outro_vinculo)
        else:
            db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto.id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.e_principal.is_(True),
            ).update({"e_principal": False})

        if vinculo:
            vinculo.ativo = True
            vinculo.e_principal = True
            vinculo.updated_at = datetime.utcnow()
        else:
            db.add(ProdutoFornecedor(
                produto_id=produto.id,
                fornecedor_id=fornecedor_id,
                e_principal=True,
                ativo=True,
                tenant_id=tenant_id,
            ))

        produto.fornecedor_id = fornecedor_id
        return True

    if operacao == "remover":
        return _remover_fornecedores_produto_lote(
            db,
            produto,
            tenant_id,
            fornecedor_id=fornecedor_id,
        )

    return False


def _garantir_fornecedor_principal_quando_unico(db: Session, produto: Produto, tenant_id) -> None:
    """Marca automaticamente como principal quando ha um unico fornecedor ativo."""
    vinculos_ativos = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto.id,
        ProdutoFornecedor.tenant_id == tenant_id,
        ProdutoFornecedor.ativo.is_(True),
    ).order_by(ProdutoFornecedor.id.asc()).all()

    if not vinculos_ativos:
        produto.fornecedor_id = None
        return

    if len(vinculos_ativos) != 1:
        return

    vinculo_unico = vinculos_ativos[0]
    vinculo_unico.e_principal = True
    produto.fornecedor_id = vinculo_unico.fornecedor_id
