"""Rotas principais de funcionarios/RH."""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.cargo_models import Cargo
from app.db import get_session
from app.models import Cliente
from app.services.remuneracao_service import calcular_composicao_remuneracao

from .helpers import (
    _aplicar_app_access_profiles,
    _buscar_cargo_funcionario,
    _funcionario_app_access_profiles,
    _funcionario_response_dict,
)
from .schemas import (
    FuncionarioCreate,
    FuncionarioResponse,
    FuncionarioUpdate,
    RemuneracaoResponse,
)

router = APIRouter()


@router.get("", response_model=List[FuncionarioResponse])
async def listar_funcionarios(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    cargo_id: Optional[int] = Query(None, description="Filtrar por cargo"),
    search: Optional[str] = Query(None, description="Buscar por nome, email ou CPF"),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todos os funcionários do tenant.
    """
    _user, tenant_id = current_user_and_tenant

    query = (
        db.query(Cliente)
        .outerjoin(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(Cliente.tenant_id == tenant_id, Cliente.tipo_cadastro == "funcionario")
    )

    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)

    if cargo_id:
        query = query.filter(Cliente.cargo_id == cargo_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Cliente.nome.ilike(search_term))
            | (Cliente.email.ilike(search_term))
            | (Cliente.cpf.ilike(search_term))
        )

    funcionarios = query.order_by(Cliente.nome).all()

    cargo_ids = {func.cargo_id for func in funcionarios if func.cargo_id}
    cargos_por_id = {}
    if cargo_ids:
        cargos = (
            db.query(Cargo)
            .filter(Cargo.tenant_id == tenant_id, Cargo.id.in_(cargo_ids))
            .all()
        )
        cargos_por_id = {cargo.id: cargo for cargo in cargos}

    return [
        FuncionarioResponse(
            **_funcionario_response_dict(
                func,
                cargos_por_id.get(func.cargo_id),
                _funcionario_app_access_profiles(db, tenant_id, func),
            )
        )
        for func in funcionarios
    ]


@router.get("/{funcionario_id}", response_model=FuncionarioResponse)
async def obter_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Obtém detalhes de um funcionário específico.
    """
    _user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
        )
        .first()
    )

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    return FuncionarioResponse(
        **_funcionario_response_dict(
            funcionario,
            cargo,
            _funcionario_app_access_profiles(db, tenant_id, funcionario),
        )
    )


@router.get("/{funcionario_id}/remuneracao", response_model=RemuneracaoResponse)
async def obter_remuneracao_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna a composicao gerencial mensal de remuneracao do funcionario.
    """
    _user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
        )
        .first()
    )

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    if not cargo:
        raise HTTPException(
            status_code=400, detail="Funcionário não possui cargo definido"
        )

    return RemuneracaoResponse(**calcular_composicao_remuneracao(cargo, funcionario))


@router.post("", response_model=FuncionarioResponse, status_code=201)
async def criar_funcionario(
    funcionario_data: FuncionarioCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria um novo funcionário.
    """
    user, tenant_id = current_user_and_tenant

    cargo = (
        db.query(Cargo)
        .filter(Cargo.id == funcionario_data.cargo_id, Cargo.tenant_id == tenant_id)
        .first()
    )
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")

    if funcionario_data.cpf:
        cpf_existente = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cpf == funcionario_data.cpf,
                Cliente.ativo.is_(True),
            )
            .first()
        )
        if cpf_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cadastro ativo com o CPF '{funcionario_data.cpf}'",
            )

    from app.clientes_routes import gerar_codigo_cliente

    codigo = gerar_codigo_cliente(db, "funcionario", "PF", tenant_id)
    funcionario = Cliente(
        tenant_id=tenant_id,
        user_id=user.id,
        codigo=codigo,
        nome=funcionario_data.nome.strip(),
        email=funcionario_data.email,
        telefone=funcionario_data.telefone,
        cpf=funcionario_data.cpf,
        tipo_cadastro="funcionario",
        tipo_pessoa="PF",
        cargo_id=funcionario_data.cargo_id,
        data_fechamento_comissao=funcionario_data.data_fechamento_comissao,
        salario_base_override=funcionario_data.salario_base_override,
        liquido_combinado=funcionario_data.liquido_combinado,
        complemento_modo=funcionario_data.complemento_modo,
        complemento_fixo_valor=funcionario_data.complemento_fixo_valor,
        remuneracao_observacoes=funcionario_data.remuneracao_observacoes.strip()
        if funcionario_data.remuneracao_observacoes
        else None,
        ativo=funcionario_data.ativo,
    )

    db.add(funcionario)
    db.flush()
    _aplicar_app_access_profiles(
        db,
        tenant_id=tenant_id,
        funcionario=funcionario,
        profile_types=funcionario_data.app_access_profiles,
        user_id=user.id,
    )
    db.commit()
    db.refresh(funcionario)

    return FuncionarioResponse(
        **_funcionario_response_dict(
            funcionario,
            cargo,
            _funcionario_app_access_profiles(db, tenant_id, funcionario),
        )
    )


@router.put("/{funcionario_id}", response_model=FuncionarioResponse)
async def atualizar_funcionario(
    funcionario_id: int,
    funcionario_data: FuncionarioUpdate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza um funcionário existente.
    """
    user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    if funcionario_data.cargo_id:
        cargo = (
            db.query(Cargo)
            .filter(Cargo.id == funcionario_data.cargo_id, Cargo.tenant_id == tenant_id)
            .first()
        )
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo não encontrado")

    if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
        cpf_existente = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cpf == funcionario_data.cpf,
                Cliente.id != funcionario_id,
                Cliente.ativo.is_(True),
            )
            .first()
        )
        if cpf_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cadastro ativo com o CPF '{funcionario_data.cpf}'",
            )

    update_data = funcionario_data.model_dump(exclude_unset=True)
    app_access_profiles = update_data.pop("app_access_profiles", None)
    for field, value in update_data.items():
        if field == "nome" and value:
            setattr(funcionario, field, value.strip())
        elif field == "remuneracao_observacoes" and value:
            setattr(funcionario, field, value.strip())
        elif field == "complemento_fixo_valor" and value is None:
            setattr(funcionario, field, Decimal("0.00"))
        else:
            setattr(funcionario, field, value)

    _aplicar_app_access_profiles(
        db,
        tenant_id=tenant_id,
        funcionario=funcionario,
        profile_types=app_access_profiles,
        user_id=user.id,
    )

    db.commit()
    db.refresh(funcionario)

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    return FuncionarioResponse(
        **_funcionario_response_dict(
            funcionario,
            cargo,
            _funcionario_app_access_profiles(db, tenant_id, funcionario),
        )
    )


@router.post("/{funcionario_id}/ativar", response_model=FuncionarioResponse)
async def ativar_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reativa um funcionario inativo.
    """
    _user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    funcionario.ativo = True
    db.commit()
    db.refresh(funcionario)

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    return FuncionarioResponse(
        **_funcionario_response_dict(
            funcionario,
            cargo,
            _funcionario_app_access_profiles(db, tenant_id, funcionario),
        )
    )


@router.delete("/{funcionario_id}")
async def deletar_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Inativa um funcionário (soft delete).
    """
    _user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    funcionario.ativo = False
    db.commit()

    return {"message": f"Funcionário '{funcionario.nome}' inativado com sucesso"}
