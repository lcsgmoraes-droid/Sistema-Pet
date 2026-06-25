"""Busca e serializacao de pessoas para o PDV mobile."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .common import _somente_digitos_funcionario_pdv
from .schemas import FuncionarioPdvClienteResponse

router = APIRouter()


def _serialize_funcionario_pdv_cliente(cliente: Cliente) -> dict:
    documento = cliente.cpf or cliente.cnpj
    partes_endereco = [
        getattr(cliente, "endereco", None),
        getattr(cliente, "numero", None),
        getattr(cliente, "bairro", None),
        getattr(cliente, "cidade", None),
        getattr(cliente, "estado", None),
    ]
    endereco = (
        ", ".join(
            str(parte).strip() for parte in partes_endereco if str(parte or "").strip()
        )
        or None
    )
    credito = (
        getattr(cliente, "credito", None)
        or getattr(cliente, "saldo_credito", None)
        or getattr(cliente, "credito_cliente", None)
        or 0
    )
    fidelidade = {
        "pontos": int(
            getattr(cliente, "pontos_fidelidade", None)
            or getattr(cliente, "pontos", None)
            or 0
        ),
        "carimbos": int(
            getattr(cliente, "carimbos_fidelidade", None)
            or getattr(cliente, "carimbos", None)
            or 0
        ),
    }
    return {
        "id": cliente.id,
        "codigo": cliente.codigo,
        "nome": cliente.nome
        or cliente.nome_fantasia
        or cliente.razao_social
        or f"Cliente #{cliente.id}",
        "telefone": cliente.telefone,
        "celular": cliente.celular,
        "documento": documento,
        "tipo_cadastro": cliente.tipo_cadastro,
        "email": cliente.email,
        "endereco": endereco,
        "credito": float(credito or 0),
        "fidelidade": fidelidade,
        "cupons_disponiveis": [],
    }


def _buscar_cliente_pdv_funcionario(
    db: Session, tenant_id: str, cliente_id: Optional[int]
) -> Optional[Cliente]:
    if not cliente_id:
        return None
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_(True),
        )
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada.")
    return cliente


@router.get(
    "/funcionario/pdv/clientes/buscar",
    response_model=list[FuncionarioPdvClienteResponse],
)
def buscar_clientes_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    termo_digits = _somente_digitos_funcionario_pdv(termo)
    cpf_digits = func.regexp_replace(func.coalesce(Cliente.cpf, ""), r"\D", "", "g")
    cnpj_digits = func.regexp_replace(func.coalesce(Cliente.cnpj, ""), r"\D", "", "g")
    telefone_digits = func.regexp_replace(
        func.coalesce(Cliente.telefone, ""), r"\D", "", "g"
    )
    celular_digits = func.regexp_replace(
        func.coalesce(Cliente.celular, ""), r"\D", "", "g"
    )
    filtros = [
        Cliente.codigo.ilike(f"%{termo}%"),
        Cliente.nome.ilike(f"%{termo}%"),
        Cliente.nome_fantasia.ilike(f"%{termo}%"),
        Cliente.razao_social.ilike(f"%{termo}%"),
        Cliente.cpf.ilike(f"%{termo}%"),
        Cliente.cnpj.ilike(f"%{termo}%"),
        Cliente.telefone.ilike(f"%{termo}%"),
        Cliente.celular.ilike(f"%{termo}%"),
    ]
    if termo_digits:
        filtros.extend(
            [
                cpf_digits.ilike(f"%{termo_digits}%"),
                cnpj_digits.ilike(f"%{termo_digits}%"),
                telefone_digits.ilike(f"%{termo_digits}%"),
                celular_digits.ilike(f"%{termo_digits}%"),
            ]
        )

    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_(True),
            or_(*filtros),
        )
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_pdv_cliente(cliente) for cliente in clientes]
