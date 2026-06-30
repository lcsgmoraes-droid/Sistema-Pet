"""Helpers compartilhados pelas rotas de funcionarios/RH."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.cargo_models import Cargo
from app.models import Cliente
from app.services.app_access_profile_service import (
    build_available_profiles_for_clientes,
    list_explicit_app_access_profiles,
    sync_cliente_app_access_profiles,
)
from app.services.remuneracao_service import calcular_composicao_remuneracao


def _cargo_dict(cargo: Optional[Cargo]) -> Optional[dict]:
    if not cargo:
        return None
    return {
        "id": cargo.id,
        "nome": cargo.nome,
        "salario_base": cargo.salario_base,
        "regime_remuneracao": cargo.regime_remuneracao,
    }


def _funcionario_response_dict(
    funcionario: Cliente,
    cargo: Optional[Cargo],
    app_access_profiles: Optional[List[str]] = None,
) -> dict:
    return {
        "id": funcionario.id,
        "codigo": funcionario.codigo,
        "nome": funcionario.nome,
        "email": funcionario.email,
        "telefone": funcionario.telefone,
        "cpf": funcionario.cpf,
        "cargo": _cargo_dict(cargo),
        "ativo": funcionario.ativo,
        "data_fechamento_comissao": funcionario.data_fechamento_comissao,
        "salario_base_override": funcionario.salario_base_override,
        "liquido_combinado": funcionario.liquido_combinado,
        "complemento_modo": funcionario.complemento_modo or "automatico",
        "complemento_fixo_valor": funcionario.complemento_fixo_valor or Decimal("0.00"),
        "remuneracao_observacoes": funcionario.remuneracao_observacoes,
        "app_access_profiles": app_access_profiles or [],
        "remuneracao": calcular_composicao_remuneracao(cargo, funcionario)
        if cargo
        else None,
    }


def _funcionario_app_access_profiles(
    db: Session, tenant_id, funcionario: Cliente
) -> List[str]:
    grants = list_explicit_app_access_profiles(
        db,
        tenant_id=tenant_id,
        user_id=funcionario.user_id,
        cliente_ids=[funcionario.id],
    )
    profiles = build_available_profiles_for_clientes(
        None, [funcionario], explicit_grants=grants
    )
    return [profile["type"] for profile in profiles]


def _aplicar_app_access_profiles(
    db: Session,
    *,
    tenant_id,
    funcionario: Cliente,
    profile_types: Optional[List[str]],
    user_id: int,
) -> None:
    if profile_types is None:
        return

    profiles = sync_cliente_app_access_profiles(
        db,
        tenant_id=tenant_id,
        cliente=funcionario,
        profile_types=profile_types,
        granted_by_user_id=user_id,
    )
    if "entregador" in profiles:
        funcionario.is_entregador = True
        funcionario.entregador_ativo = True
        funcionario.tipo_vinculo_entrega = "funcionario"
        funcionario.is_terceirizado = False
    else:
        funcionario.is_entregador = False


def _buscar_cargo_funcionario(
    db: Session, tenant_id, cargo_id: Optional[int]
) -> Optional[Cargo]:
    if not cargo_id:
        return None
    return (
        db.query(Cargo)
        .filter(Cargo.id == cargo_id, Cargo.tenant_id == tenant_id)
        .first()
    )
