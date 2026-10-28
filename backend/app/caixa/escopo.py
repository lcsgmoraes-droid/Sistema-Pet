"""Resolve o escopo individual ou compartilhado do caixa da empresa."""

from sqlalchemy import case
from sqlalchemy.orm import Query, Session
from fastapi import HTTPException

from app.caixa_models import Caixa
from app.empresa_config_geral_models import EmpresaConfigGeral


def caixa_compartilhado_habilitado(
    db: Session, tenant_id, *, bloquear_config: bool = False
) -> bool:
    """Retorna o modo da empresa, preservando o caixa individual como padrao."""
    query = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    )
    if bloquear_config:
        query = query.with_for_update()
    config = query.first()
    return bool(config and getattr(config, "caixa_compartilhado", False))


def aplicar_escopo_caixa(
    query: Query, *, tenant_id, usuario_id: int, compartilhado: bool
) -> Query:
    """Limita caixas ao tenant e, no modo individual, ao usuario atual."""
    query = query.filter(Caixa.tenant_id == tenant_id)
    if not compartilhado:
        query = query.filter(Caixa.usuario_id == usuario_id)
    return query


def buscar_caixa_aberto(
    db: Session,
    *,
    tenant_id,
    usuario_id: int,
    bloquear_config: bool = False,
    bloquear_caixa: bool = False,
) -> tuple[Caixa | None, bool]:
    """Busca o caixa aberto acessivel e informa se o modo e compartilhado."""
    compartilhado = caixa_compartilhado_habilitado(
        db, tenant_id, bloquear_config=bloquear_config
    )
    query = aplicar_escopo_caixa(
        db.query(Caixa).filter(Caixa.status == "aberto"),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        compartilhado=compartilhado,
    )
    prioridade_usuario_atual = case((Caixa.usuario_id == usuario_id, 0), else_=1)
    query = query.order_by(prioridade_usuario_atual.asc(), Caixa.id.desc())
    if bloquear_caixa:
        query = query.populate_existing().with_for_update()
    caixa = query.first()
    return caixa, compartilhado


def buscar_caixa_acessivel(
    db: Session,
    *,
    caixa_id: int,
    tenant_id,
    usuario_id: int,
    bloquear_caixa: bool = False,
) -> tuple[Caixa | None, bool]:
    """Busca um caixa por id respeitando o modo definido pela empresa."""
    compartilhado = caixa_compartilhado_habilitado(db, tenant_id)
    query = aplicar_escopo_caixa(
        db.query(Caixa).filter(Caixa.id == caixa_id),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        compartilhado=compartilhado,
    )
    if bloquear_caixa:
        query = query.populate_existing().with_for_update()
    return query.first(), compartilhado


def buscar_caixa_para_recebimento(
    db: Session,
    *,
    tenant_id,
    usuario_id: int,
    caixa_id: int | None = None,
    bloquear_caixa: bool = False,
) -> tuple[Caixa | None, bool]:
    """Seleciona um caixa acessível; exige escolha quando houver mais de um."""
    if caixa_id is not None:
        caixa, compartilhado = buscar_caixa_acessivel(
            db,
            caixa_id=caixa_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            bloquear_caixa=bloquear_caixa,
        )
        if caixa is None:
            raise HTTPException(
                404, "Caixa não encontrado ou não disponível para seu usuário."
            )
        if caixa.status != "aberto":
            raise HTTPException(
                409, "O caixa selecionado está fechado. Escolha um caixa aberto."
            )
        return caixa, compartilhado

    compartilhado = caixa_compartilhado_habilitado(db, tenant_id)
    query = aplicar_escopo_caixa(
        db.query(Caixa).filter(Caixa.status == "aberto"),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        compartilhado=compartilhado,
    ).order_by(Caixa.id)
    if bloquear_caixa:
        query = query.populate_existing().with_for_update()
    caixas = query.limit(2).all()
    if len(caixas) > 1:
        raise HTTPException(
            400, "Há mais de um caixa aberto. Selecione o caixa deste recebimento."
        )
    return (caixas[0] if caixas else None), compartilhado
