"""Grupos reutilizáveis e provisão das comissões dos produtos selecionados."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_grupos_models import ComissaoGrupoProdutos
from app.comissoes_models import ComissaoItem
from app.comissoes_provisao import provisionar_comissoes_venda
from app.db import get_session
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission_dependency

router = APIRouter()


class GrupoProdutosPayload(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    produto_ids: list[int] = Field(min_length=1, max_length=2000)

    @field_validator("nome")
    @classmethod
    def normalizar_nome(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe o nome do grupo")
        return value

    @field_validator("produto_ids")
    @classmethod
    def normalizar_produtos(cls, value):
        if any(item <= 0 for item in value):
            raise ValueError("Produto inválido")
        return sorted(set(value))


class ProvisionarGrupoPayload(BaseModel):
    data_inicio: date
    data_fim: date
    funcionario_id: Optional[int] = Field(default=None, gt=0)


def _grupo(db, tenant_id, grupo_id):
    grupo = (
        db.query(ComissaoGrupoProdutos)
        .filter(
            ComissaoGrupoProdutos.id == grupo_id,
            ComissaoGrupoProdutos.tenant_id == tenant_id,
            ComissaoGrupoProdutos.ativo.is_(True),
        )
        .first()
    )
    if grupo is None:
        raise HTTPException(404, "Grupo de produtos não encontrado")
    return grupo


def _serializar(grupo, produtos=()):
    return {
        "id": grupo.id,
        "nome": grupo.nome,
        "produto_ids": grupo.produto_ids,
        "produtos": [
            {"id": produto.id, "nome": produto.nome, "codigo": produto.codigo}
            for produto in produtos
            if produto.id in grupo.produto_ids
        ],
    }


def _validar_produtos(db, tenant_id, produto_ids):
    encontrados = {
        row[0]
        for row in db.query(Produto.id)
        .filter(Produto.tenant_id == tenant_id, Produto.id.in_(produto_ids))
        .all()
    }
    if encontrados != set(produto_ids):
        raise HTTPException(
            400, "O grupo contém produtos não disponíveis nesta empresa"
        )


@router.get(
    "/grupos-produtos",
    dependencies=[Depends(require_permission_dependency("comissoes.demonstrativo"))],
)
def listar_grupos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    grupos = (
        db.query(ComissaoGrupoProdutos)
        .filter(
            ComissaoGrupoProdutos.tenant_id == tenant_id,
            ComissaoGrupoProdutos.ativo.is_(True),
        )
        .order_by(ComissaoGrupoProdutos.nome)
        .all()
    )
    ids = {produto_id for grupo in grupos for produto_id in grupo.produto_ids}
    produtos = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.id.in_(ids))
        .all()
        if ids
        else []
    )
    return {"success": True, "data": [_serializar(grupo, produtos) for grupo in grupos]}


@router.post(
    "/grupos-produtos",
    dependencies=[Depends(require_permission_dependency("comissoes.configurar"))],
)
def salvar_grupo(
    payload: GrupoProdutosPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    _validar_produtos(db, tenant_id, payload.produto_ids)
    grupo = ComissaoGrupoProdutos(
        tenant_id=tenant_id, nome=payload.nome, produto_ids=payload.produto_ids
    )
    db.add(grupo)
    try:
        db.commit()
        db.refresh(grupo)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um grupo com esse nome")
    produtos = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.id.in_(grupo.produto_ids))
        .all()
    )
    return {"success": True, "data": _serializar(grupo, produtos)}


@router.put(
    "/grupos-produtos/{grupo_id}",
    dependencies=[Depends(require_permission_dependency("comissoes.configurar"))],
)
def atualizar_grupo(
    grupo_id: int,
    payload: GrupoProdutosPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    grupo = _grupo(db, tenant_id, grupo_id)
    _validar_produtos(db, tenant_id, payload.produto_ids)
    grupo.nome = payload.nome
    grupo.produto_ids = payload.produto_ids
    try:
        db.commit()
        db.refresh(grupo)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um grupo com esse nome")
    produtos = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.id.in_(grupo.produto_ids))
        .all()
    )
    return {"success": True, "data": _serializar(grupo, produtos)}


@router.post(
    "/grupos-produtos/{grupo_id}/provisionar",
    dependencies=[Depends(require_permission_dependency("comissoes.fechamentos"))],
)
def provisionar_grupo(
    grupo_id: int,
    payload: ProvisionarGrupoPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, tenant_id = user_and_tenant
    grupo = _grupo(db, tenant_id, grupo_id)
    if payload.data_inicio > payload.data_fim:
        raise HTTPException(400, "O início do período deve ser anterior ao fim")
    # Os valores vêm dos itens de comissão já calculados. Nunca se inventa uma
    # comissão a partir do faturamento, nem se gera outra conta para o mesmo item.
    query = db.query(ComissaoItem).filter(
        ComissaoItem.tenant_id == tenant_id,
        ComissaoItem.produto_id.in_(grupo.produto_ids),
        ComissaoItem.data_venda.between(payload.data_inicio, payload.data_fim),
        ComissaoItem.status == "pendente",
        ComissaoItem.valor_comissao_gerada > 0,
        or_(
            ComissaoItem.comissao_provisionada.is_(False),
            ComissaoItem.comissao_provisionada.is_(None),
        ),
        ComissaoItem.conta_pagar_id.is_(None),
    )
    if payload.funcionario_id is not None:
        query = query.filter(ComissaoItem.funcionario_id == payload.funcionario_id)
    itens = (
        query.order_by(ComissaoItem.venda_id, ComissaoItem.id).with_for_update().all()
    )
    por_venda = {}
    for item in itens:
        por_venda.setdefault(item.venda_id, []).append(item.id)
    resultado = {
        "success": True,
        "comissoes_provisionadas": 0,
        "valor_total": 0,
        "contas_criadas": [],
    }
    try:
        for venda_id, item_ids in por_venda.items():
            parcial = provisionar_comissoes_venda(
                venda_id=venda_id,
                tenant_id=tenant_id,
                db=db,
                user_id=usuario.id,
                comissao_ids=item_ids,
                commit=False,
            )
            if not parcial["success"]:
                raise HTTPException(409, parcial["message"])
            resultado["comissoes_provisionadas"] += parcial["comissoes_provisionadas"]
            resultado["valor_total"] += parcial["valor_total"]
            resultado["contas_criadas"].extend(parcial["contas_criadas"])
        db.commit()
    except Exception:
        db.rollback()
        raise
    resultado["valor_total"] = round(resultado["valor_total"], 2)
    resultado["message"] = (
        f"{len(resultado['contas_criadas'])} conta(s) a pagar criada(s)"
        if itens
        else "Nenhuma comissão calculada pendente de provisão neste grupo e período"
    )
    return resultado
