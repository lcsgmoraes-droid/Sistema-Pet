from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_schemas import BanhoTosaPessoaApoioResponse, BanhoTosaProdutoEstoqueResponse
from app.db import get_session
from app.models import Cliente
from app.produtos_models import Produto
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/apoios/funcionarios", response_model=List[BanhoTosaPessoaApoioResponse])
def listar_funcionarios_apoio(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.ativo == True,
        Cliente.tipo_cadastro.in_(["funcionario", "veterinario", "outro"]),
    )

    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(or_(Cliente.nome.ilike(termo), Cliente.codigo.ilike(termo)))

    pessoas = query.order_by(Cliente.nome.asc()).limit(limit).all()
    return [
        {
            "id": pessoa.id,
            "nome": pessoa.nome,
            "tipo_cadastro": pessoa.tipo_cadastro,
        }
        for pessoa in pessoas
    ]


@router.get("/apoios/produtos-estoque", response_model=List[BanhoTosaProdutoEstoqueResponse])
def listar_produtos_estoque_apoio(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
        Produto.situacao == True,
    )

    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(or_(Produto.nome.ilike(termo), Produto.codigo.ilike(termo)))

    produtos = query.order_by(Produto.nome.asc()).limit(limit).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "unidade": produto.unidade,
            "estoque_atual": produto.estoque_atual or 0,
            "preco_custo": produto.preco_custo or 0,
        }
        for produto in produtos
    ]
