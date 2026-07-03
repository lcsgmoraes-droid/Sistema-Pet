"""Dependencias de banco do enriquecimento Bling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal as SessionLocal  # noqa: E402
from app.models import Cliente, User  # noqa: E402
from app.produtos_models import Categoria, Departamento, Marca, Produto  # noqa: E402
from enriquecer_produtos_bling_utils import normalize_text  # noqa: E402


def detect_single_tenant_id(db) -> UUID:
    tenant_ids = [row[0] for row in db.query(User.tenant_id).distinct().all() if row[0]]
    if len(tenant_ids) != 1:
        raise RuntimeError("Ambiente com mais de um tenant. Informe --tenant-id.")
    return tenant_ids[0]


def find_user_id(db, tenant_id: UUID) -> int:
    user = (
        db.query(User)
        .filter(User.tenant_id == tenant_id)
        .order_by(User.id.asc())
        .first()
    )
    if user:
        return user.id

    produto_user = (
        db.query(Produto.user_id)
        .filter(Produto.tenant_id == tenant_id, Produto.user_id.isnot(None))
        .order_by(Produto.user_id.asc())
        .first()
    )
    if produto_user and produto_user[0]:
        return int(produto_user[0])

    raise RuntimeError(f"Nenhum usuario encontrado para tenant {tenant_id}")


def get_or_create_marca(
    db,
    tenant_id: UUID,
    user_id: int,
    cache: Dict[str, Marca],
    nome: str,
    apply_mode: bool,
) -> Optional[Marca]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    marca = (
        db.query(Marca)
        .filter(Marca.tenant_id == tenant_id, Marca.nome.ilike(nome))
        .first()
    )
    if not marca and apply_mode:
        marca = Marca(nome=nome, tenant_id=tenant_id, user_id=user_id, ativo=True)
        db.add(marca)
        db.flush()
    if marca:
        cache[key] = marca
    return marca


def get_or_create_departamento(
    db,
    tenant_id: UUID,
    user_id: int,
    cache: Dict[str, Departamento],
    nome: str,
    apply_mode: bool,
) -> Optional[Departamento]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    dep = (
        db.query(Departamento)
        .filter(Departamento.tenant_id == tenant_id, Departamento.nome.ilike(nome))
        .first()
    )
    if not dep and apply_mode:
        dep = Departamento(nome=nome, tenant_id=tenant_id, user_id=user_id, ativo=True)
        db.add(dep)
        db.flush()
    if dep:
        cache[key] = dep
    return dep


def get_or_create_categoria(
    db,
    tenant_id: UUID,
    user_id: int,
    cache: Dict[str, Categoria],
    nome: str,
    departamento_id: Optional[int],
    apply_mode: bool,
) -> Optional[Categoria]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = f"{nome.upper()}|{departamento_id or 0}"
    if key in cache:
        return cache[key]

    query = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id, Categoria.nome.ilike(nome)
    )
    if departamento_id:
        query = query.filter(
            (Categoria.departamento_id == departamento_id)
            | (Categoria.departamento_id.is_(None))
        )
    cat = query.order_by(Categoria.id.asc()).first()

    if not cat and apply_mode:
        cat = Categoria(
            nome=nome,
            tenant_id=tenant_id,
            user_id=user_id,
            ativo=True,
            departamento_id=departamento_id,
        )
        db.add(cat)
        db.flush()

    if cat:
        if apply_mode and departamento_id and cat.departamento_id is None:
            cat.departamento_id = departamento_id
        cache[key] = cat
    return cat


def get_or_create_fornecedor(
    db,
    tenant_id: UUID,
    user_id: int,
    cache: Dict[str, Cliente],
    nome: str,
    apply_mode: bool,
) -> Optional[Cliente]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    forn = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.nome.ilike(nome),
        )
        .first()
    )

    if not forn and apply_mode:
        forn = Cliente(
            tenant_id=tenant_id,
            user_id=user_id,
            tipo_cadastro="fornecedor",
            tipo_pessoa="PJ",
            nome=nome,
            ativo=True,
        )
        db.add(forn)
        db.flush()

    if forn:
        cache[key] = forn
    return forn
