"""Rotas para cadastro e acompanhamento do imobilizado."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.imobilizado_schemas import (
    BemImobilizadoCreate,
    BemImobilizadoResponse,
    BemImobilizadoUpdate,
    ListaImobilizadoResponse,
    ResumoImobilizado,
)
from app.financeiro.imobilizado_service import calcular_valores_bem, decimal_moeda
from app.financeiro.models_imobilizado import BemImobilizado
from app.security.permissions_decorator import require_permission


router = APIRouter(prefix="/imobilizado", tags=["Financeiro - Imobilizado"])


def _bem_do_tenant(db: Session, tenant_id, bem_id: int) -> BemImobilizado:
    bem = (
        db.query(BemImobilizado)
        .filter(
            BemImobilizado.id == bem_id,
            BemImobilizado.tenant_id == tenant_id,
        )
        .first()
    )
    if not bem:
        raise HTTPException(status_code=404, detail="Bem nao encontrado.")
    return bem


def _serializar_bem(bem: BemImobilizado) -> BemImobilizadoResponse:
    dados = {coluna.name: getattr(bem, coluna.name) for coluna in bem.__table__.columns}
    dados.update(calcular_valores_bem(bem))
    return BemImobilizadoResponse.model_validate(dados)


@router.get("", response_model=ListaImobilizadoResponse)
@require_permission("relatorios.financeiro")
def listar_imobilizado(
    busca: str | None = None,
    categoria: str | None = None,
    situacao: str | None = Query(None, alias="status"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    query = db.query(BemImobilizado).filter(BemImobilizado.tenant_id == tenant_id)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                BemImobilizado.nome.ilike(termo),
                BemImobilizado.codigo_patrimonial.ilike(termo),
                BemImobilizado.localizacao.ilike(termo),
            )
        )
    if categoria:
        query = query.filter(BemImobilizado.categoria == categoria)
    if situacao == "em_posse":
        query = query.filter(BemImobilizado.status.in_(["ativo", "manutencao"]))
    elif situacao:
        query = query.filter(BemImobilizado.status == situacao)

    bens = query.order_by(BemImobilizado.nome.asc()).all()
    items = [_serializar_bem(bem) for bem in bens]
    resumo = ResumoImobilizado(
        total_registros=len(items),
        total_itens=sum(item.quantidade for item in items),
        valor_aquisicao=sum(
            (item.valor_aquisicao for item in items), Decimal("0")
        ),
        depreciacao_acumulada=sum(
            (item.depreciacao_acumulada for item in items), Decimal("0")
        ),
        valor_contabil=sum((item.valor_contabil for item in items), Decimal("0")),
        valor_mercado_informado=sum(
            (item.valor_mercado or Decimal("0") for item in items), Decimal("0")
        ),
        registros_sem_valor_mercado=sum(
            1 for item in items if item.valor_mercado is None
        ),
    )
    return ListaImobilizadoResponse(items=items, resumo=resumo)


@router.get("/{bem_id}", response_model=BemImobilizadoResponse)
@require_permission("relatorios.financeiro")
def obter_bem(
    bem_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    return _serializar_bem(_bem_do_tenant(db, tenant_id, bem_id))


@router.post("", response_model=BemImobilizadoResponse, status_code=status.HTTP_201_CREATED)
@require_permission("relatorios.financeiro")
def criar_bem(
    payload: BemImobilizadoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    dados = payload.model_dump()
    dados["valor_aquisicao"] = decimal_moeda(dados["valor_aquisicao"])
    dados["valor_residual"] = decimal_moeda(dados["valor_residual"])
    if dados["valor_mercado"] is not None:
        dados["valor_mercado"] = decimal_moeda(dados["valor_mercado"])
    bem = BemImobilizado(tenant_id=tenant_id, **dados)
    db.add(bem)
    db.commit()
    db.refresh(bem)
    return _serializar_bem(bem)


@router.put("/{bem_id}", response_model=BemImobilizadoResponse)
@require_permission("relatorios.financeiro")
def atualizar_bem(
    bem_id: int,
    payload: BemImobilizadoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    bem = _bem_do_tenant(db, tenant_id, bem_id)
    for campo, valor in payload.model_dump().items():
        setattr(bem, campo, valor)
    db.commit()
    db.refresh(bem)
    return _serializar_bem(bem)


@router.delete("/{bem_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("relatorios.financeiro")
def excluir_bem(
    bem_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    bem = _bem_do_tenant(db, tenant_id, bem_id)
    db.delete(bem)
    db.commit()
