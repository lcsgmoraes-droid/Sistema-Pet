"""Rotas da avaliacao gerencial do valor da empresa."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.models_contas import ContaPagar
from app.financeiro.models_valor_empresa import ValorEmpresaConfiguracao
from app.financeiro.valor_empresa_schemas import (
    SimulacaoValorEmpresaPayload,
    ValorEmpresaConfiguracaoPayload,
    ValorEmpresaResponse,
)
from app.financeiro.valor_empresa_service import montar_avaliacao
from app.models import Cliente
from app.produtos_models import Produto, ProdutoFornecedor
from app.security.permissions_decorator import require_permission


router = APIRouter(prefix="/valor-empresa", tags=["Financeiro - Valor da Empresa"])


def _obter_configuracao(db: Session, tenant_id):
    return (
        db.query(ValorEmpresaConfiguracao)
        .filter(ValorEmpresaConfiguracao.tenant_id == tenant_id)
        .first()
    )


@router.get("", response_model=ValorEmpresaResponse)
@require_permission("relatorios.financeiro")
async def obter_valor_empresa(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    return await montar_avaliacao(
        db, current_user, tenant_id, _obter_configuracao(db, tenant_id)
    )


@router.put("/configuracao", response_model=ValorEmpresaResponse)
@require_permission("relatorios.financeiro")
async def salvar_configuracao(
    payload: ValorEmpresaConfiguracaoPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    config = _obter_configuracao(db, tenant_id)
    if config is None:
        config = ValorEmpresaConfiguracao(tenant_id=tenant_id)
        db.add(config)
    for campo, valor in payload.model_dump().items():
        setattr(config, campo, valor)
    db.commit()
    db.refresh(config)
    return await montar_avaliacao(db, current_user, tenant_id, config)


@router.post("/simular", response_model=ValorEmpresaResponse)
@require_permission("relatorios.financeiro")
async def simular_valor_empresa(
    payload: SimulacaoValorEmpresaPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    return await montar_avaliacao(
        db,
        current_user,
        tenant_id,
        _obter_configuracao(db, tenant_id),
        payload.faturamento_mensal,
    )


@router.get("/fornecedores")
@require_permission("relatorios.financeiro")
def listar_fornecedores_avaliacao(
    busca: str | None = Query(None, max_length=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    ids_referenciados = {
        item[0]
        for item in db.query(ContaPagar.fornecedor_id)
        .filter(ContaPagar.tenant_id == tenant_id, ContaPagar.fornecedor_id.isnot(None))
        .distinct()
        .all()
    }
    ids_referenciados.update(
        item[0]
        for item in db.query(Produto.fornecedor_id)
        .filter(Produto.tenant_id == tenant_id, Produto.fornecedor_id.isnot(None))
        .distinct()
        .all()
    )
    ids_referenciados.update(
        item[0]
        for item in db.query(ProdutoFornecedor.fornecedor_id)
        .join(Produto, ProdutoFornecedor.produto_id == Produto.id)
        .filter(Produto.tenant_id == tenant_id)
        .distinct()
        .all()
    )
    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        or_(Cliente.tipo_cadastro == "fornecedor", Cliente.id.in_(ids_referenciados)),
    )
    if busca and busca.strip():
        query = query.filter(Cliente.nome.ilike(f"%{busca.strip()}%"))
    return [
        {"id": fornecedor.id, "nome": fornecedor.nome}
        for fornecedor in query.order_by(Cliente.nome.asc()).limit(100).all()
    ]
