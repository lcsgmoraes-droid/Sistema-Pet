"""
Routes para gerenciamento de Funcionários (RH)
Utiliza a tabela 'clientes' com tipo_cadastro='funcionario'
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
from datetime import date

from app.db import get_session
from app.models import Cliente
from app.cargo_models import Cargo
from app.auth.dependencies import get_current_user_and_tenant
from app.services.ferias_service import conceder_ferias
from app.services.decimo_terceiro_service import pagar_decimo_terceiro
from app.services.remuneracao_service import calcular_composicao_remuneracao

router = APIRouter(prefix="/funcionarios", tags=["RH - Funcionários"])


# Schemas
class FuncionarioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    cargo_id: int
    ativo: bool = True
    data_fechamento_comissao: Optional[int] = Field(None, ge=1, le=31, description="Dia do mês para fechamento de comissão (1-31)")
    salario_base_override: Optional[Decimal] = Field(None, ge=0)
    liquido_combinado: Optional[Decimal] = Field(None, ge=0)
    complemento_modo: str = Field(default="automatico", pattern="^(automatico|manual|nenhum)$")
    complemento_fixo_valor: Decimal = Field(default=Decimal("0.00"), ge=0)
    remuneracao_observacoes: Optional[str] = None

    model_config = {"from_attributes": True}


class FuncionarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    cargo_id: Optional[int] = None
    ativo: Optional[bool] = None
    data_fechamento_comissao: Optional[int] = Field(None, ge=1, le=31, description="Dia do mês para fechamento de comissão (1-31)")
    salario_base_override: Optional[Decimal] = Field(None, ge=0)
    liquido_combinado: Optional[Decimal] = Field(None, ge=0)
    complemento_modo: Optional[str] = Field(None, pattern="^(automatico|manual|nenhum)$")
    complemento_fixo_valor: Optional[Decimal] = Field(None, ge=0)
    remuneracao_observacoes: Optional[str] = None

    model_config = {"from_attributes": True}


class CargoSimples(BaseModel):
    id: int
    nome: str
    salario_base: Decimal
    regime_remuneracao: str = "clt"

    model_config = {"from_attributes": True}


class RemuneracaoResponse(BaseModel):
    regime_remuneracao: str
    usa_encargos: bool
    salario_base: Decimal
    inss_funcionario: Decimal
    desconto_transporte: Decimal
    outros_descontos: Decimal
    descontos_funcionario_total: Decimal
    liquido_holerite: Decimal
    liquido_combinado: Decimal
    complemento_modo: str
    complemento_interno: Decimal
    inss_patronal: Decimal
    fgts_empresa: Decimal
    encargos_empresa_total: Decimal
    provisao_ferias: Decimal
    provisao_terco_ferias: Decimal
    provisao_13: Decimal
    provisoes_total: Decimal
    custo_total_empresa: Decimal

    model_config = {"from_attributes": True}


class FuncionarioResponse(BaseModel):
    id: int
    codigo: Optional[str]
    nome: str
    email: Optional[str]
    telefone: Optional[str]
    cpf: Optional[str]
    cargo: Optional[CargoSimples]
    ativo: bool
    data_fechamento_comissao: Optional[int]
    salario_base_override: Optional[Decimal]
    liquido_combinado: Optional[Decimal]
    complemento_modo: str
    complemento_fixo_valor: Decimal
    remuneracao_observacoes: Optional[str]
    remuneracao: Optional[RemuneracaoResponse] = None

    model_config = {"from_attributes": True}


def _cargo_dict(cargo: Optional[Cargo]) -> Optional[dict]:
    if not cargo:
        return None
    return {
        "id": cargo.id,
        "nome": cargo.nome,
        "salario_base": cargo.salario_base,
        "regime_remuneracao": cargo.regime_remuneracao,
    }


def _funcionario_response_dict(funcionario: Cliente, cargo: Optional[Cargo]) -> dict:
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
        "remuneracao": calcular_composicao_remuneracao(cargo, funcionario) if cargo else None,
    }


def _buscar_cargo_funcionario(db: Session, tenant_id, cargo_id: Optional[int]) -> Optional[Cargo]:
    if not cargo_id:
        return None
    return db.query(Cargo).filter(
        Cargo.id == cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()


# Schemas para Eventos RH
class ConcederFeriasRequest(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mês de competência (1-12)")
    ano: int = Field(..., ge=2020, le=2030, description="Ano de competência")
    dias_ferias: int = Field(30, ge=1, le=30, description="Dias de férias (padrão: 30)")
    data_pagamento: Optional[date] = Field(None, description="Data de vencimento da conta a pagar")

    model_config = {"from_attributes": True}


class PagarDecimoTerceiroRequest(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mês de competência (1-12)")
    ano: int = Field(..., ge=2020, le=2030, description="Ano de competência")
    percentual: float = Field(..., ge=0, le=100, description="Percentual do 13º (50 para 1ª parcela, 100 para total)")
    descricao_parcela: Optional[str] = Field(None, description="Descrição da parcela (ex: '1ª Parcela')")
    data_pagamento: Optional[date] = Field(None, description="Data de vencimento da conta a pagar")

    model_config = {"from_attributes": True}


class ProvisoesResponse(BaseModel):
    funcionario_id: int
    funcionario_nome: str
    cargo_nome: str
    salario_base: Decimal
    provisao_ferias: Decimal
    provisao_terco_ferias: Decimal
    provisao_13_salario: Decimal
    total_provisoes: Decimal

    model_config = {"from_attributes": True}


# Endpoints
@router.get("", response_model=List[FuncionarioResponse])
async def listar_funcionarios(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    cargo_id: Optional[int] = Query(None, description="Filtrar por cargo"),
    search: Optional[str] = Query(None, description="Buscar por nome, email ou CPF"),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Lista todos os funcionários do tenant.
    """
    user, tenant_id = current_user_and_tenant

    query = db.query(Cliente).outerjoin(
        Cargo, Cliente.cargo_id == Cargo.id
    ).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    )

    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)

    if cargo_id:
        query = query.filter(Cliente.cargo_id == cargo_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Cliente.nome.ilike(search_term)) |
            (Cliente.email.ilike(search_term)) |
            (Cliente.cpf.ilike(search_term))
        )

    query = query.order_by(Cliente.nome)
    funcionarios = query.all()

    cargo_ids = {func.cargo_id for func in funcionarios if func.cargo_id}
    cargos_por_id = {}
    if cargo_ids:
        cargos = db.query(Cargo).filter(
            Cargo.tenant_id == tenant_id,
            Cargo.id.in_(cargo_ids)
        ).all()
        cargos_por_id = {cargo.id: cargo for cargo in cargos}

    return [
        FuncionarioResponse(**_funcionario_response_dict(func, cargos_por_id.get(func.cargo_id)))
        for func in funcionarios
    ]


@router.get("/{funcionario_id}", response_model=FuncionarioResponse)
async def obter_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Obtém detalhes de um funcionário específico.
    """
    user, tenant_id = current_user_and_tenant

    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    ).first()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    return FuncionarioResponse(**_funcionario_response_dict(funcionario, cargo))


@router.get("/{funcionario_id}/remuneracao", response_model=RemuneracaoResponse)
async def obter_remuneracao_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Retorna a composicao gerencial mensal de remuneracao do funcionario.
    """
    user, tenant_id = current_user_and_tenant

    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    ).first()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    if not cargo:
        raise HTTPException(status_code=400, detail="Funcionário não possui cargo definido")

    return RemuneracaoResponse(**calcular_composicao_remuneracao(cargo, funcionario))


@router.post("", response_model=FuncionarioResponse, status_code=201)
async def criar_funcionario(
    funcionario_data: FuncionarioCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Cria um novo funcionário.
    """
    user, tenant_id = current_user_and_tenant

    # Verificar se cargo existe
    cargo = db.query(Cargo).filter(
        Cargo.id == funcionario_data.cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()

    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")

    # Verificar CPF duplicado (se fornecido)
    if funcionario_data.cpf:
        cpf_existente = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf == funcionario_data.cpf,
            Cliente.ativo == True
        ).first()

        if cpf_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cadastro ativo com o CPF '{funcionario_data.cpf}'"
            )

    # Gerar código de funcionário
    from app.clientes_routes import gerar_codigo_cliente
    codigo = gerar_codigo_cliente(db, "funcionario", "PF", tenant_id)

    # Criar funcionário
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
        remuneracao_observacoes=funcionario_data.remuneracao_observacoes.strip() if funcionario_data.remuneracao_observacoes else None,
        ativo=funcionario_data.ativo
    )

    db.add(funcionario)
    db.commit()
    db.refresh(funcionario)

    return FuncionarioResponse(**_funcionario_response_dict(funcionario, cargo))


@router.put("/{funcionario_id}", response_model=FuncionarioResponse)
async def atualizar_funcionario(
    funcionario_id: int,
    funcionario_data: FuncionarioUpdate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Atualiza um funcionário existente.
    """
    user, tenant_id = current_user_and_tenant

    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    ).first()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    # Verificar cargo se fornecido
    if funcionario_data.cargo_id:
        cargo = db.query(Cargo).filter(
            Cargo.id == funcionario_data.cargo_id,
            Cargo.tenant_id == tenant_id
        ).first()

        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo não encontrado")

    # Verificar CPF duplicado (se alterado)
    if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
        cpf_existente = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf == funcionario_data.cpf,
            Cliente.id != funcionario_id,
            Cliente.ativo == True
        ).first()

        if cpf_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cadastro ativo com o CPF '{funcionario_data.cpf}'"
            )

    # Atualizar campos
    update_data = funcionario_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "nome" and value:
            setattr(funcionario, field, value.strip())
        elif field == "remuneracao_observacoes" and value:
            setattr(funcionario, field, value.strip())
        elif field == "complemento_fixo_valor" and value is None:
            setattr(funcionario, field, Decimal("0.00"))
        else:
            setattr(funcionario, field, value)

    db.commit()
    db.refresh(funcionario)

    cargo = _buscar_cargo_funcionario(db, tenant_id, funcionario.cargo_id)
    return FuncionarioResponse(**_funcionario_response_dict(funcionario, cargo))


@router.delete("/{funcionario_id}")
async def deletar_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Inativa um funcionário (soft delete).
    """
    user, tenant_id = current_user_and_tenant

    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    ).first()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    # Inativar
    funcionario.ativo = False
    db.commit()

    return {"message": f"Funcionário '{funcionario.nome}' inativado com sucesso"}


# ============================================================================
# EVENTOS RH - FÉRIAS E 13º SALÁRIO
# ============================================================================

@router.post("/{funcionario_id}/ferias")
async def api_conceder_ferias(
    funcionario_id: int,
    dados: ConcederFeriasRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Concede férias a um funcionário.

    - Consome provisão acumulada
    - Gera conta a pagar
    - Registra no DRE de competência
    """
    user, tenant_id = current_user_and_tenant

    # Verificar se funcionário existe e está ativo
    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario",
        Cliente.ativo == True
    ).first()

    if not funcionario:
        raise HTTPException(
            status_code=404,
            detail="Funcionário não encontrado ou inativo"
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
            dias_ferias=dados.dias_ferias
        )

        return {
            "success": True,
            "mensagem": f"Férias concedidas com sucesso para {funcionario.nome}",
            "dados": resultado
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{funcionario_id}/decimo-terceiro")
async def api_pagar_decimo_terceiro(
    funcionario_id: int,
    dados: PagarDecimoTerceiroRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Paga 13º salário (parcial ou total).

    - Percentual 50 = 1ª parcela
    - Percentual 100 = pagamento integral
    - Consome provisão acumulada
    - Gera conta a pagar
    """
    user, tenant_id = current_user_and_tenant

    # Verificar se funcionário existe e está ativo
    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario",
        Cliente.ativo == True
    ).first()

    if not funcionario:
        raise HTTPException(
            status_code=404,
            detail="Funcionário não encontrado ou inativo"
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
            descricao_parcela=dados.descricao_parcela
        )

        return {
            "success": True,
            "mensagem": f"13º salário pago com sucesso para {funcionario.nome}",
            "dados": resultado
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{funcionario_id}/provisoes", response_model=ProvisoesResponse)
async def api_obter_provisoes_funcionario(
    funcionario_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Obtém o saldo de provisões de um funcionário.

    Retorna:
    - Provisão de férias
    - Provisão de 1/3 de férias
    - Provisão de 13º salário
    - Total de provisões acumuladas
    """
    user, tenant_id = current_user_and_tenant

    # Buscar funcionário
    funcionario = db.query(Cliente).filter(
        Cliente.id == funcionario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "funcionario"
    ).first()

    if not funcionario:
        raise HTTPException(
            status_code=404,
            detail="Funcionário não encontrado"
        )

    if not funcionario.cargo_id:
        raise HTTPException(
            status_code=400,
            detail="Funcionário não possui cargo definido"
        )

    cargo = db.query(Cargo).filter(
        Cargo.id == funcionario.cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()

    if not cargo:
        raise HTTPException(
            status_code=404,
            detail="Cargo do funcionário não encontrado"
        )

    composicao = calcular_composicao_remuneracao(cargo, funcionario)
    salario = Decimal(str(composicao["salario_base"]))
    usa_encargos = bool(composicao["usa_encargos"])

    # Calcular provisões individuais do funcionário com base no salário e tempo trabalhado.
    # A tabela dre_detalhe_canais não tem funcionario_id (é agregada por período),
    # portanto calculamos diretamente: salário/12 × meses acumulados.

    hoje = date.today()
    data_contratacao = funcionario.created_at.date() if funcionario.created_at else hoje
    delta_dias = (hoje - data_contratacao).days
    meses_totais = int(delta_dias / 30.44)

    # Férias: ciclo aquisitivo de 12 meses (reinicia a cada período completo)
    meses_aquisitivos = meses_totais % 12
    if meses_aquisitivos == 0 and meses_totais >= 12:
        meses_aquisitivos = 12  # Ciclo completo acumulado

    # 13º salário: acumula apenas nos meses do ano corrente
    inicio_periodo_13 = max(data_contratacao, date(hoje.year, 1, 1))
    meses_no_ano = int((hoje - inicio_periodo_13).days / 30.44)

    # Garantir ao menos 1 mês para quem foi contratado há poucos dias
    if delta_dias >= 1 and meses_aquisitivos == 0:
        meses_aquisitivos = 1
    if delta_dias >= 1 and meses_no_ano == 0:
        meses_no_ano = 1

    # Provisão de férias = salário/12 × meses do ciclo aquisitivo
    if usa_encargos and cargo.gera_ferias:
        prov_ferias = (salario / 12 * meses_aquisitivos).quantize(Decimal("0.01"))
        prov_terco = (prov_ferias / 3).quantize(Decimal("0.01"))
    else:
        prov_ferias = Decimal("0.00")
        prov_terco = Decimal("0.00")

    # Provisão de 13º = salário/12 × meses no ano corrente
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
        total_provisoes=total
    )
