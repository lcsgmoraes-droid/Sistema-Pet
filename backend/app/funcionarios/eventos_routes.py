"""Rotas de eventos de RH dos funcionarios."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.cargo_models import Cargo
from app.db import get_session
from app.models import Cliente
from app.services.decimo_terceiro_service import pagar_decimo_terceiro
from app.services.ferias_service import conceder_ferias
from app.services.remuneracao_service import calcular_composicao_remuneracao

from .schemas import (
    ConcederFeriasRequest,
    PagarDecimoTerceiroRequest,
    ProvisoesResponse,
)

router = APIRouter()


@router.post("/{funcionario_id}/ferias")
async def api_conceder_ferias(
    funcionario_id: int,
    dados: ConcederFeriasRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Concede férias a um funcionário.

    - Consome provisão acumulada
    - Gera conta a pagar
    - Registra no DRE de competência
    """
    user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo.is_(True),
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(
            status_code=404, detail="Funcionário não encontrado ou inativo"
        )

    try:
        resultado = conceder_ferias(
            db=db,
            tenant_id=tenant_id,
            funcionario_id=funcionario_id,
            mes=dados.mes,
            ano=dados.ano,
            usuario_id=user.id,
            data_pagamento=dados.data_pagamento,
            dias_ferias=dados.dias_ferias,
        )

        return {
            "success": True,
            "mensagem": f"Férias concedidas com sucesso para {funcionario.nome}",
            "dados": resultado,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{funcionario_id}/decimo-terceiro")
async def api_pagar_decimo_terceiro(
    funcionario_id: int,
    dados: PagarDecimoTerceiroRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Paga 13º salário parcial ou total.

    - Percentual 50 = 1ª parcela
    - Percentual 100 = pagamento integral
    - Consome provisão acumulada
    - Gera conta a pagar
    """
    user, tenant_id = current_user_and_tenant

    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo.is_(True),
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(
            status_code=404, detail="Funcionário não encontrado ou inativo"
        )

    try:
        resultado = pagar_decimo_terceiro(
            db=db,
            tenant_id=tenant_id,
            funcionario_id=funcionario_id,
            percentual=dados.percentual,
            mes=dados.mes,
            ano=dados.ano,
            usuario_id=user.id,
            data_pagamento=dados.data_pagamento,
            descricao_parcela=dados.descricao_parcela,
        )

        return {
            "success": True,
            "mensagem": f"13º salário pago com sucesso para {funcionario.nome}",
            "dados": resultado,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{funcionario_id}/provisoes", response_model=ProvisoesResponse)
async def api_obter_provisoes_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Obtém o saldo de provisões de um funcionário.
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

    if not funcionario.cargo_id:
        raise HTTPException(
            status_code=400, detail="Funcionário não possui cargo definido"
        )

    cargo = (
        db.query(Cargo)
        .filter(Cargo.id == funcionario.cargo_id, Cargo.tenant_id == tenant_id)
        .first()
    )
    if not cargo:
        raise HTTPException(
            status_code=404, detail="Cargo do funcionário não encontrado"
        )

    composicao = calcular_composicao_remuneracao(cargo, funcionario)
    salario = Decimal(str(composicao["salario_base"]))
    usa_encargos = bool(composicao["usa_encargos"])

    hoje = date.today()
    data_contratacao = funcionario.created_at.date() if funcionario.created_at else hoje
    delta_dias = (hoje - data_contratacao).days
    meses_totais = int(delta_dias / 30.44)

    meses_aquisitivos = meses_totais % 12
    if meses_aquisitivos == 0 and meses_totais >= 12:
        meses_aquisitivos = 12

    inicio_periodo_13 = max(data_contratacao, date(hoje.year, 1, 1))
    meses_no_ano = int((hoje - inicio_periodo_13).days / 30.44)

    if delta_dias >= 1 and meses_aquisitivos == 0:
        meses_aquisitivos = 1
    if delta_dias >= 1 and meses_no_ano == 0:
        meses_no_ano = 1

    if usa_encargos and cargo.gera_ferias:
        prov_ferias = (salario / 12 * meses_aquisitivos).quantize(Decimal("0.01"))
        prov_terco = (prov_ferias / 3).quantize(Decimal("0.01"))
    else:
        prov_ferias = Decimal("0.00")
        prov_terco = Decimal("0.00")

    if usa_encargos and cargo.gera_decimo_terceiro:
        prov_13 = (salario / 12 * meses_no_ano).quantize(Decimal("0.01"))
    else:
        prov_13 = Decimal("0.00")

    total = prov_ferias + prov_terco + prov_13

    return ProvisoesResponse(
        funcionario_id=funcionario.id,
        funcionario_nome=funcionario.nome,
        cargo_nome=cargo.nome,
        salario_base=salario,
        provisao_ferias=prov_ferias,
        provisao_terco_ferias=prov_terco,
        provisao_13_salario=prov_13,
        total_provisoes=total,
    )
