"""Consulta leve para o relatorio personalizado de pessoas."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import _validar_tenant_e_obter_usuario
from app.clientes.crud_routes import _aplicar_filtro_ativo, _aplicar_filtro_busca
from app.db import get_session
from app.models import Cliente
from app.partner_utils import get_all_accessible_tenant_ids
from app.security.permissions_decorator import require_permission

router = APIRouter()

TIPOS_CADASTRO_RELATORIO = {
    "cliente",
    "fornecedor",
    "veterinario",
    "funcionario",
}

COLUNAS_RELATORIO_PESSOAS = (
    Cliente.id,
    Cliente.codigo,
    Cliente.tipo_cadastro,
    Cliente.tipo_pessoa,
    Cliente.nome,
    Cliente.cpf,
    Cliente.cnpj,
    Cliente.telefone,
    Cliente.celular,
    Cliente.email,
    Cliente.data_nascimento,
    Cliente.razao_social,
    Cliente.nome_fantasia,
    Cliente.responsavel,
    Cliente.inscricao_estadual,
    Cliente.crmv,
    Cliente.cep,
    Cliente.endereco,
    Cliente.numero,
    Cliente.complemento,
    Cliente.bairro,
    Cliente.cidade,
    Cliente.estado,
    Cliente.origem_cliente,
    Cliente.observacoes,
    Cliente.ativo,
    Cliente.created_at,
)


def _validar_tipos_relatorio(tipos: Optional[List[str]]) -> list[str]:
    tipos_normalizados = list(
        dict.fromkeys(tipo.strip().lower() for tipo in tipos or [])
    )
    invalidos = [
        tipo for tipo in tipos_normalizados if tipo not in TIPOS_CADASTRO_RELATORIO
    ]
    if invalidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de cadastro invalido: {', '.join(invalidos)}",
        )
    return tipos_normalizados


@router.get("/relatorio/pessoas")
@require_permission("clientes.visualizar")
def listar_pessoas_para_relatorio(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    search: Optional[str] = None,
    tipo_cadastro: Optional[List[str]] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista somente os campos necessarios para montar relatorios de pessoas."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    tipos = _validar_tipos_relatorio(tipo_cadastro)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)

    query = db.query(Cliente).filter(Cliente.tenant_id.in_(access_ids))
    if tipos:
        query = query.filter(Cliente.tipo_cadastro.in_(tipos))
    query = _aplicar_filtro_busca(query, search)
    query = _aplicar_filtro_ativo(query, ativo=None)

    total = query.count()
    linhas = (
        query.with_entities(*COLUNAS_RELATORIO_PESSOAS)
        .order_by(func.lower(Cliente.nome), Cliente.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "items": [dict(linha._mapping) for linha in linhas],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
