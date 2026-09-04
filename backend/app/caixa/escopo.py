"""Resolve o escopo individual ou compartilhado do caixa da empresa."""

from sqlalchemy import case
from sqlalchemy.orm import Query, Session

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
    caixa = query.order_by(prioridade_usuario_atual.asc(), Caixa.id.desc()).first()
    return caixa, compartilhado


def buscar_caixa_acessivel(
    db: Session, *, caixa_id: int, tenant_id, usuario_id: int
) -> tuple[Caixa | None, bool]:
    """Busca um caixa por id respeitando o modo definido pela empresa."""
    compartilhado = caixa_compartilhado_habilitado(db, tenant_id)
    query = aplicar_escopo_caixa(
        db.query(Caixa).filter(Caixa.id == caixa_id),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        compartilhado=compartilhado,
    )
    return query.first(), compartilhado
