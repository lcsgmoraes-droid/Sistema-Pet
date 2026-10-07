"""Registros clinicos do pet (historico e peso), por loja.

Leitura: qualquer loja que enxerga o pet (propria ou do mesmo grupo).
Escrita: so a loja que registrou pode alterar ou apagar o proprio registro.
"""

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models_cadastros import Cliente, Pet, PetRegistroClinico
from app.tenancy.filters import pessoa_visivel_no_grupo

TIPOS_REGISTRO = ("historico", "peso")


def pet_visivel(db: Session, pet_id: int, tenant_id) -> Pet | None:
    return (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            or_(Pet.tenant_id == tenant_id, pessoa_visivel_no_grupo(Pet, tenant_id)),
        )
        .first()
    )


def cliente_visivel(db: Session, cliente_id: int, tenant_id) -> Cliente | None:
    return (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            or_(Cliente.tenant_id == tenant_id, pessoa_visivel_no_grupo(Cliente, tenant_id)),
        )
        .first()
    )


def ultimo_registro(db: Session, pet_id: int, tipo: str, tenant_id=None) -> PetRegistroClinico | None:
    consulta = db.query(PetRegistroClinico).filter(
        PetRegistroClinico.pet_id == pet_id,
        PetRegistroClinico.tipo == tipo,
    )
    if tenant_id is not None:
        consulta = consulta.filter(PetRegistroClinico.tenant_id == tenant_id)
    return consulta.order_by(
        PetRegistroClinico.registrado_em.desc(), PetRegistroClinico.id.desc()
    ).first()


def listar_registros(db: Session, pet_id: int, tipo: str | None = None) -> list[PetRegistroClinico]:
    consulta = db.query(PetRegistroClinico).filter(PetRegistroClinico.pet_id == pet_id)
    if tipo:
        consulta = consulta.filter(PetRegistroClinico.tipo == tipo)
    return consulta.order_by(
        PetRegistroClinico.registrado_em.desc(), PetRegistroClinico.id.desc()
    ).all()


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_REGISTRO:
        raise HTTPException(status_code=400, detail="Tipo de registro invalido.")


def criar_registro(
    db: Session,
    *,
    pet_id: int,
    tenant_id,
    user_id: int | None,
    tipo: str,
    texto: str | None = None,
    valor: float | None = None,
    registrado_em: datetime | None = None,
) -> PetRegistroClinico:
    _validar_tipo(tipo)
    registro = PetRegistroClinico(
        tenant_id=tenant_id,
        pet_id=pet_id,
        tipo=tipo,
        texto=texto,
        valor=valor,
        registrado_em=registrado_em or datetime.utcnow(),
        user_id=user_id,
    )
    db.add(registro)
    db.flush()
    return registro


def registrar_se_mudou(
    db: Session,
    *,
    pet_id: int,
    tenant_id,
    user_id: int | None,
    tipo: str,
    novo: Any,
) -> PetRegistroClinico | None:
    """Cria um registro da loja so se o valor for diferente do ultimo dela."""
    if novo is None or (isinstance(novo, str) and not novo.strip()):
        return None
    anterior = ultimo_registro(db, pet_id, tipo, tenant_id=tenant_id)
    if tipo == "peso":
        if anterior is not None and anterior.valor == float(novo):
            return None
        return criar_registro(db, pet_id=pet_id, tenant_id=tenant_id, user_id=user_id, tipo=tipo, valor=float(novo))
    texto = str(novo).strip()
    if anterior is not None and (anterior.texto or "").strip() == texto:
        return None
    return criar_registro(db, pet_id=pet_id, tenant_id=tenant_id, user_id=user_id, tipo=tipo, texto=texto)


def _obter_registro_da_loja(db: Session, registro_id: int, pet_id: int, tenant_id) -> PetRegistroClinico:
    registro = (
        db.query(PetRegistroClinico)
        .filter(PetRegistroClinico.id == registro_id, PetRegistroClinico.pet_id == pet_id)
        .first()
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro nao encontrado.")
    if str(registro.tenant_id) != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente a loja que registrou pode alterar este registro.",
        )
    return registro


def atualizar_registro(
    db: Session,
    *,
    registro_id: int,
    pet_id: int,
    tenant_id,
    texto: str | None = None,
    valor: float | None = None,
    registrado_em: datetime | None = None,
) -> PetRegistroClinico:
    registro = _obter_registro_da_loja(db, registro_id, pet_id, tenant_id)
    if texto is not None:
        registro.texto = texto
    if valor is not None:
        registro.valor = valor
    if registrado_em is not None:
        registro.registrado_em = registrado_em
    db.flush()
    return registro


def excluir_registro(db: Session, *, registro_id: int, pet_id: int, tenant_id) -> None:
    registro = _obter_registro_da_loja(db, registro_id, pet_id, tenant_id)
    db.delete(registro)
    db.flush()
