"""Lojas do grupo comercial e trava para codigos unicos no grupo."""

from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.grupo_comercial_models import GrupoComercialMembro


def tenants_do_grupo(db: Session, tenant_id) -> set[str]:
    """Id da propria loja mais as lojas ativas dos grupos comerciais em que ela esta."""
    tid = str(tenant_id)
    grupos = {
        grupo_id
        for (grupo_id,) in db.query(GrupoComercialMembro.grupo_id).filter(
            GrupoComercialMembro.empresa_id == tid,
            GrupoComercialMembro.status == "ativo",
        )
    }
    ids = {tid}
    if grupos:
        ids |= {
            str(empresa_id)
            for (empresa_id,) in db.query(GrupoComercialMembro.empresa_id).filter(
                GrupoComercialMembro.grupo_id.in_(grupos),
                GrupoComercialMembro.status == "ativo",
            )
        }
    return ids


def ids_uuid_do_grupo(db: Session, tenant_id) -> list[UUID]:
    return [UUID(t) for t in tenants_do_grupo(db, tenant_id)]


def trava_codigos_do_grupo(db: Session, tenant_id, recurso: str) -> None:
    """Serializa a criacao de codigos do grupo ate o fim da transacao."""
    chave = f"{recurso}:{min(tenants_do_grupo(db, tenant_id))}"
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:chave))"), {"chave": chave})


def codigo_em_uso_no_grupo(db: Session, *, tenant_id, coluna, valor: str, excluir_id=None, modelo=None) -> bool:
    ids = ids_uuid_do_grupo(db, tenant_id)
    consulta = db.query(modelo).filter(
        modelo.tenant_id.in_(ids),
        func.lower(func.trim(coluna)) == valor.strip().lower(),
    )
    if excluir_id is not None:
        consulta = consulta.filter(modelo.id != excluir_id)
    return db.query(consulta.exists()).scalar()
