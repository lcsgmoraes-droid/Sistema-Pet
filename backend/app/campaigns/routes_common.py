"""Helpers compartilhados pelas rotas de campanhas."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Cliente


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _current_user_id(user) -> int | None:
    if user is None:
        return None
    if isinstance(user, int):
        return user
    return getattr(user, "id", None)


def _resolver_customer_id_campanhas(db: Session, *, tenant_id, customer_ref) -> int:
    ref_text = str(customer_ref or "").strip()
    if not ref_text:
        raise HTTPException(status_code=400, detail="Cliente nao informado")

    if ref_text.isdigit():
        cliente_por_id = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.id == int(ref_text),
                Cliente.ativo.is_(True),
            )
            .first()
        )
        if cliente_por_id:
            return cliente_por_id.id

    cliente_por_codigo = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.codigo == ref_text,
            Cliente.ativo.is_(True),
        )
        .first()
    )
    if cliente_por_codigo:
        return cliente_por_codigo.id

    raise HTTPException(
        status_code=404,
        detail=f"Cliente nao encontrado para o codigo/ID {ref_text}",
    )
