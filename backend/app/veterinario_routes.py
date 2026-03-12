"""
Rotas do módulo veterinário.
Cobre: agendamentos, consultas, vacinas, exames, prescrições,
internações, peso, fotos, catálogos e perfil comportamental.
"""
import hashlib
import secrets
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet, User
from .veterinario_models import (
    AgendamentoVet,
    CatalogoProcedimento,
    ConsultaVet,
    ExameVet,
    FotoClinica,
    InternacaoVet,
    EvolucaoInternacao,
    ItemPrescricao,
    MedicamentoCatalogo,
    PerfilComportamental,
    PesoRegistro,
    PrescricaoVet,
    ProcedimentoConsulta,
    ProtocoloVacina,
    VacinaRegistro,
)

router = APIRouter(prefix="/vet", tags=["Veterinário"])


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_tenant(current: tuple) -> tuple:
    """Extrai user e tenant_id do tuple retornado pelo Depends."""
    user, tenant_id = current
    return user, tenant_id


def _pet_or_404(db: Session, pet_id: int, tenant_id) -> Pet:
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.user_id == db.query(User.id).filter(User.tenant_id == tenant_id).scalar_subquery()).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    return pet


def _consulta_or_404(db: Session, consulta_id: int, tenant_id) -> ConsultaVet:
    c = db.query(ConsultaVet).filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


# ═══════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════════════════════════

class AgendamentoCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    data_hora: datetime
    duracao_minutos: int = 30
    tipo: str = "consulta"
    motivo: Optional[str] = None
    is_emergencia: bool = False
    sintoma_emergencia: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoUpdate(BaseModel):
    data_hora: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    tipo: Optional[str] = None
    motivo: Optional[str] = None
    status: Optional[str] = None
    veterinario_id: Optional[int] = None
    observacoes: Optional[str] = None
    pretriagem: Optional[dict] = None


class AgendamentoResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    data_hora: datetime
    duracao_minutos: int
    tipo: str
    motivo: Optional[str]
    status: str
    is_emergencia: bool
    consulta_id: Optional[int]
    observacoes: Optional[str]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[str] = None,
    pet_id: Optional[int] = None,
    veterinario_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(AgendamentoVet).filter(AgendamentoVet.tenant_id == tenant_id)

    if data_inicio:
        q = q.filter(func.date(AgendamentoVet.data_hora) >= data_inicio)
    if data_fim:
        q = q.filter(func.date(AgendamentoVet.data_hora) <= data_fim)
    if status:
        q = q.filter(AgendamentoVet.status == status)
    if pet_id:
        q = q.filter(AgendamentoVet.pet_id == pet_id)
    if veterinario_id:
        q = q.filter(AgendamentoVet.veterinario_id == veterinario_id)

    agendamentos = q.order_by(AgendamentoVet.data_hora).all()

    result = []
    for ag in agendamentos:
        d = {
            "id": ag.id,
            "pet_id": ag.pet_id,
            "cliente_id": ag.cliente_id,
            "veterinario_id": ag.veterinario_id,
            "data_hora": ag.data_hora,
            "duracao_minutos": ag.duracao_minutos,
            "tipo": ag.tipo,
            "motivo": ag.motivo,
            "status": ag.status,
            "is_emergencia": ag.is_emergencia,
            "consulta_id": ag.consulta_id,
            "observacoes": ag.observacoes,
            "created_at": ag.created_at,
        }
        if ag.pet:
            d["pet_nome"] = ag.pet.nome
        if ag.cliente:
            d["cliente_nome"] = ag.cliente.nome
        if ag.veterinario:
            d["veterinario_nome"] = ag.veterinario.nome
        result.append(d)
    return result


@router.post("/agendamentos", response_model=AgendamentoResponse, status_code=201)
def criar_agendamento(
    body: AgendamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = AgendamentoVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        tipo=body.tipo,
        motivo=body.motivo,
        is_emergencia=body.is_emergencia,
        sintoma_emergencia=body.sintoma_emergencia,
        observacoes=body.observacoes,
        status="agendado",
    )
    db.add(ag)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.patch("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def atualizar_agendamento(
    agendamento_id: int,
    body: AgendamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ag, field, value)

    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


def _agendamento_to_dict(ag: AgendamentoVet) -> dict:
    return {
        "id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "veterinario_id": ag.veterinario_id,
        "data_hora": ag.data_hora,
        "duracao_minutos": ag.duracao_minutos,
        "tipo": ag.tipo,
        "motivo": ag.motivo,
        "status": ag.status,
        "is_emergencia": ag.is_emergencia,
        "consulta_id": ag.consulta_id,
        "observacoes": ag.observacoes,
        "created_at": ag.created_at,
        "pet_nome": ag.pet.nome if ag.pet else None,
        "cliente_nome": ag.cliente.nome if ag.cliente else None,
        "veterinario_nome": ag.veterinario.nome if ag.veterinario else None,
    }


# ═══════════════════════════════════════════════════════════════
# CONSULTAS
# ═══════════════════════════════════════════════════════════════

class ConsultaCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    tipo: str = "consulta"
    agendamento_id: Optional[int] = None
    queixa_principal: Optional[str] = None


class ConsultaUpdate(BaseModel):
    queixa_principal: Optional[str] = None
    historia_clinica: Optional[str] = None
    peso_consulta: Optional[float] = None
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    tpc: Optional[str] = None
    mucosas: Optional[str] = None
    hidratacao: Optional[str] = None
    nivel_dor: Optional[int] = None
    saturacao_o2: Optional[float] = None
    pressao_sistolica: Optional[int] = None
    pressao_diastolica: Optional[int] = None
    glicemia: Optional[float] = None
    exame_fisico: Optional[str] = None
    hipotese_diagnostica: Optional[str] = None
    diagnostico: Optional[str] = None
    diagnostico_simples: Optional[str] = None
    conduta: Optional[str] = None
    retorno_em_dias: Optional[int] = None
    data_retorno: Optional[date] = None
    asa_score: Optional[int] = None
    asa_justificativa: Optional[str] = None
    observacoes_internas: Optional[str] = None
    observacoes_tutor: Optional[str] = None
    veterinario_id: Optional[int] = None


class ConsultaResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    tipo: str
    status: str
    queixa_principal: Optional[str]
    historia_clinica: Optional[str]
    peso_consulta: Optional[float]
    temperatura: Optional[float]
    frequencia_cardiaca: Optional[int]
    frequencia_respiratoria: Optional[int]
    tpc: Optional[str]
    mucosas: Optional[str]
    hidratacao: Optional[str]
    nivel_dor: Optional[int]
    saturacao_o2: Optional[float]
    pressao_sistolica: Optional[int]
    pressao_diastolica: Optional[int]
    glicemia: Optional[float]
    exame_fisico: Optional[str]
    hipotese_diagnostica: Optional[str]
    diagnostico: Optional[str]
    diagnostico_simples: Optional[str]
    conduta: Optional[str]
    retorno_em_dias: Optional[int]
    data_retorno: Optional[date]
    asa_score: Optional[int]
    asa_justificativa: Optional[str]
    observacoes_internas: Optional[str]
    observacoes_tutor: Optional[str]
    hash_prontuario: Optional[str]
    finalizado_em: Optional[datetime]
    inicio_atendimento: Optional[datetime]
    fim_atendimento: Optional[datetime]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas", response_model=List[ConsultaResponse])
def listar_consultas(
    pet_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(ConsultaVet).filter(ConsultaVet.tenant_id == tenant_id)
    if pet_id:
        q = q.filter(ConsultaVet.pet_id == pet_id)
    if status:
        q = q.filter(ConsultaVet.status == status)
    consultas = q.order_by(ConsultaVet.created_at.desc()).offset(skip).limit(limit).all()
    return [_consulta_to_dict(c) for c in consultas]


@router.post("/consultas", response_model=ConsultaResponse, status_code=201)
def criar_consulta(
    body: ConsultaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = ConsultaVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tipo=body.tipo,
        queixa_principal=body.queixa_principal,
        status="em_andamento",
        inicio_atendimento=datetime.now(),
    )
    db.add(c)
    db.flush()

    # Vincula ao agendamento se informado
    if body.agendamento_id:
        ag = db.query(AgendamentoVet).filter(
            AgendamentoVet.id == body.agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        ).first()
        if ag:
            ag.consulta_id = c.id
            ag.status = "em_atendimento"
            ag.inicio_atendimento = c.inicio_atendimento

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def obter_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)
    return _consulta_to_dict(c)


@router.patch("/consultas/{consulta_id}", response_model=ConsultaResponse)
def atualizar_consulta(
    consulta_id: int,
    body: ConsultaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já finalizada não pode ser editada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)

    # Se registrou peso, cria registro na curva de peso
    if body.peso_consulta and body.peso_consulta > 0:
        peso_reg = PesoRegistro(
            pet_id=c.pet_id,
            consulta_id=c.id,
            user_id=user.id,
            data=date.today(),
            peso_kg=body.peso_consulta,
        )
        db.add(peso_reg)

        # Atualiza peso no cadastro do pet
        pet = db.query(Pet).filter(Pet.id == c.pet_id).first()
        if pet:
            pet.peso = body.peso_consulta

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.post("/consultas/{consulta_id}/finalizar", response_model=ConsultaResponse)
def finalizar_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já está finalizada")

    c.status = "finalizada"
    c.fim_atendimento = datetime.now()
    c.finalizado_em = datetime.now()
    c.finalizado_por_id = user.id

    # Hash do prontuário para imutabilidade
    conteudo = f"{c.id}|{c.pet_id}|{c.diagnostico}|{c.conduta}|{c.finalizado_em}"
    c.hash_prontuario = hashlib.sha256(conteudo.encode()).hexdigest()

    # Finaliza agendamento vinculado
    if c.agendamento:
        c.agendamento.status = "finalizado"
        c.agendamento.fim_atendimento = c.fim_atendimento

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


def _consulta_to_dict(c: ConsultaVet) -> dict:
    return {
        "id": c.id,
        "pet_id": c.pet_id,
        "cliente_id": c.cliente_id,
        "veterinario_id": c.veterinario_id,
        "tipo": c.tipo,
        "status": c.status,
        "queixa_principal": c.queixa_principal,
        "historia_clinica": c.historia_clinica,
        "peso_consulta": c.peso_consulta,
        "temperatura": c.temperatura,
        "frequencia_cardiaca": c.frequencia_cardiaca,
        "frequencia_respiratoria": c.frequencia_respiratoria,
        "tpc": c.tpc,
        "mucosas": c.mucosas,
        "hidratacao": c.hidratacao,
        "nivel_dor": c.nivel_dor,
        "saturacao_o2": c.saturacao_o2,
        "pressao_sistolica": c.pressao_sistolica,
        "pressao_diastolica": c.pressao_diastolica,
        "glicemia": c.glicemia,
        "exame_fisico": c.exame_fisico,
        "hipotese_diagnostica": c.hipotese_diagnostica,
        "diagnostico": c.diagnostico,
        "diagnostico_simples": c.diagnostico_simples,
        "conduta": c.conduta,
        "retorno_em_dias": c.retorno_em_dias,
        "data_retorno": c.data_retorno,
        "asa_score": c.asa_score,
        "asa_justificativa": c.asa_justificativa,
        "observacoes_internas": c.observacoes_internas,
        "observacoes_tutor": c.observacoes_tutor,
        "hash_prontuario": c.hash_prontuario,
        "finalizado_em": c.finalizado_em,
        "inicio_atendimento": c.inicio_atendimento,
        "fim_atendimento": c.fim_atendimento,
        "pet_nome": c.pet.nome if c.pet else None,
        "cliente_nome": c.cliente.nome if c.cliente else None,
        "veterinario_nome": c.veterinario.nome if c.veterinario else None,
        "created_at": c.created_at,
    }


# ═══════════════════════════════════════════════════════════════
# PRESCRIÇÕES
# ═══════════════════════════════════════════════════════════════

class ItemPrescricaoIn(BaseModel):
    nome_medicamento: str
    concentracao: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    quantidade: Optional[str] = None
    posologia: str
    via_administracao: Optional[str] = None
    duracao_dias: Optional[int] = None
    medicamento_catalogo_id: Optional[int] = None


class PrescricaoCreate(BaseModel):
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int] = None
    tipo_receituario: str = "simples"
    observacoes: Optional[str] = None
    itens: List[ItemPrescricaoIn]


class PrescricaoResponse(BaseModel):
    id: int
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int]
    numero: Optional[str]
    data_emissao: date
    tipo_receituario: str
    observacoes: Optional[str]
    hash_receita: Optional[str]
    itens: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/prescricoes", response_model=List[PrescricaoResponse])
def listar_prescricoes(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _consulta_or_404(db, consulta_id, tenant_id)
    prescricoes = db.query(PrescricaoVet).filter(
        PrescricaoVet.consulta_id == consulta_id,
        PrescricaoVet.tenant_id == tenant_id,
    ).all()
    return [_prescricao_to_dict(p) for p in prescricoes]


@router.post("/prescricoes", response_model=PrescricaoResponse, status_code=201)
def criar_prescricao(
    body: PrescricaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Número sequencial
    total = db.query(func.count(PrescricaoVet.id)).filter(PrescricaoVet.tenant_id == tenant_id).scalar() or 0
    numero = f"REC-{total + 1:05d}"

    p = PrescricaoVet(
        consulta_id=body.consulta_id,
        pet_id=body.pet_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        numero=numero,
        data_emissao=date.today(),
        tipo_receituario=body.tipo_receituario,
        observacoes=body.observacoes,
    )
    db.add(p)
    db.flush()

    for it in body.itens:
        item = ItemPrescricao(
            prescricao_id=p.id,
            user_id=user.id,
            nome_medicamento=it.nome_medicamento,
            concentracao=it.concentracao,
            forma_farmaceutica=it.forma_farmaceutica,
            quantidade=it.quantidade,
            posologia=it.posologia,
            via_administracao=it.via_administracao,
            duracao_dias=it.duracao_dias,
            medicamento_catalogo_id=it.medicamento_catalogo_id,
        )
        db.add(item)

    db.flush()

    # Hash da receita
    conteudo = f"{p.id}|{p.pet_id}|{p.data_emissao}|{[it.nome_medicamento for it in body.itens]}"
    p.hash_receita = hashlib.sha256(conteudo.encode()).hexdigest()

    db.commit()
    db.refresh(p)
    return _prescricao_to_dict(p)


def _prescricao_to_dict(p: PrescricaoVet) -> dict:
    return {
        "id": p.id,
        "consulta_id": p.consulta_id,
        "pet_id": p.pet_id,
        "veterinario_id": p.veterinario_id,
        "numero": p.numero,
        "data_emissao": p.data_emissao,
        "tipo_receituario": p.tipo_receituario,
        "observacoes": p.observacoes,
        "hash_receita": p.hash_receita,
        "created_at": p.created_at,
        "itens": [
            {
                "id": it.id,
                "nome_medicamento": it.nome_medicamento,
                "concentracao": it.concentracao,
                "forma_farmaceutica": it.forma_farmaceutica,
                "quantidade": it.quantidade,
                "posologia": it.posologia,
                "via_administracao": it.via_administracao,
                "duracao_dias": it.duracao_dias,
                "medicamento_catalogo_id": it.medicamento_catalogo_id,
            }
            for it in p.itens
        ],
    }


# ═══════════════════════════════════════════════════════════════
# VACINAS
# ═══════════════════════════════════════════════════════════════

class VacinaCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    nome_vacina: str
    fabricante: Optional[str] = None
    lote: Optional[str] = None
    data_aplicacao: date
    data_proxima_dose: Optional[date] = None
    numero_dose: int = 1
    via_administracao: Optional[str] = None
    observacoes: Optional[str] = None


class VacinaResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    nome_vacina: str
    fabricante: Optional[str]
    lote: Optional[str]
    data_aplicacao: date
    data_proxima_dose: Optional[date]
    numero_dose: int
    via_administracao: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/vacinas", response_model=List[VacinaResponse])
def listar_vacinas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    vacinas = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet_id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()
    return vacinas


@router.post("/vacinas", response_model=VacinaResponse, status_code=201)
def registrar_vacina(
    body: VacinaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    v = VacinaRegistro(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        protocolo_id=body.protocolo_id,
        nome_vacina=body.nome_vacina,
        fabricante=body.fabricante,
        lote=body.lote,
        data_aplicacao=body.data_aplicacao,
        data_proxima_dose=body.data_proxima_dose,
        numero_dose=body.numero_dose,
        via_administracao=body.via_administracao,
        observacoes=body.observacoes,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/vacinas/vencendo")
def vacinas_vencendo(
    dias: int = 30,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista vacinas que vencem nos próximos N dias."""
    user, tenant_id = _get_tenant(current)
    from datetime import timedelta
    limite = date.today() + timedelta(days=dias)
    vacinas = (
        db.query(VacinaRegistro)
        .filter(
            VacinaRegistro.tenant_id == tenant_id,
            VacinaRegistro.data_proxima_dose != None,  # noqa
            VacinaRegistro.data_proxima_dose <= limite,
            VacinaRegistro.data_proxima_dose >= date.today(),
        )
        .order_by(VacinaRegistro.data_proxima_dose)
        .all()
    )
    result = []
    for v in vacinas:
        result.append({
            "id": v.id,
            "pet_id": v.pet_id,
            "pet_nome": v.pet.nome if v.pet else None,
            "nome_vacina": v.nome_vacina,
            "data_proxima_dose": v.data_proxima_dose,
            "dias_restantes": (v.data_proxima_dose - date.today()).days,
        })
    return result


# ═══════════════════════════════════════════════════════════════
# EXAMES
# ═══════════════════════════════════════════════════════════════

class ExameCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    tipo: str = "laboratorial"
    nome: str
    data_solicitacao: Optional[date] = None
    laboratorio: Optional[str] = None
    observacoes: Optional[str] = None


class ExameUpdate(BaseModel):
    data_resultado: Optional[date] = None
    status: Optional[str] = None
    resultado_texto: Optional[str] = None
    resultado_json: Optional[dict] = None
    interpretacao: Optional[str] = None
    interpretacao_ia: Optional[str] = None
    arquivo_url: Optional[str] = None
    arquivo_nome: Optional[str] = None
    observacoes: Optional[str] = None


class ExameResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    tipo: str
    nome: str
    data_solicitacao: Optional[date]
    data_resultado: Optional[date]
    status: str
    laboratorio: Optional[str]
    resultado_texto: Optional[str]
    resultado_json: Optional[dict]
    interpretacao: Optional[str]
    interpretacao_ia: Optional[str]
    arquivo_url: Optional[str]
    arquivo_nome: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/exames", response_model=List[ExameResponse])
def listar_exames_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet_id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.data_solicitacao.desc()).all()
    return exames


@router.post("/exames", response_model=ExameResponse, status_code=201)
def criar_exame(
    body: ExameCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    e = ExameVet(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        user_id=user.id,
        tipo=body.tipo,
        nome=body.nome,
        data_solicitacao=body.data_solicitacao or date.today(),
        laboratorio=body.laboratorio,
        observacoes=body.observacoes,
        status="solicitado",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/exames/{exame_id}", response_model=ExameResponse)
def atualizar_exame(
    exame_id: int,
    body: ExameUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    e = db.query(ExameVet).filter(ExameVet.id == exame_id, ExameVet.tenant_id == tenant_id).first()
    if not e:
        raise HTTPException(404, "Exame não encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    if body.data_resultado and e.status == "solicitado":
        e.status = "disponivel"
    db.commit()
    db.refresh(e)
    return e


# ═══════════════════════════════════════════════════════════════
# PESO — curva de peso do pet
# ═══════════════════════════════════════════════════════════════

@router.get("/pets/{pet_id}/peso")
def curva_peso(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    registros = db.query(PesoRegistro).filter(
        PesoRegistro.pet_id == pet_id,
        PesoRegistro.tenant_id == tenant_id,
    ).order_by(PesoRegistro.data).all()
    return [{"data": r.data, "peso_kg": r.peso_kg, "consulta_id": r.consulta_id} for r in registros]


@router.post("/pets/{pet_id}/peso", status_code=201)
def registrar_peso(
    pet_id: int,
    peso_kg: float = Query(..., gt=0),
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    r = PesoRegistro(
        pet_id=pet_id,
        user_id=user.id,
        data=date.today(),
        peso_kg=peso_kg,
        observacoes=observacoes,
    )
    db.add(r)
    # Atualiza peso principal do pet
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    if pet:
        pet.peso = peso_kg
    db.commit()
    return {"ok": True, "peso_kg": peso_kg}


# ═══════════════════════════════════════════════════════════════
# PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class ProcedimentoCreate(BaseModel):
    consulta_id: int
    catalogo_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    valor: Optional[float] = None
    realizado: bool = True
    observacoes: Optional[str] = None


class ProcedimentoResponse(BaseModel):
    id: int
    consulta_id: int
    catalogo_id: Optional[int]
    nome: str
    descricao: Optional[str]
    valor: Optional[float]
    realizado: bool
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/procedimentos", response_model=List[ProcedimentoResponse])
def listar_procedimentos_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).all()


@router.post("/procedimentos", response_model=ProcedimentoResponse, status_code=201)
def adicionar_procedimento(
    body: ProcedimentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProcedimentoConsulta(
        consulta_id=body.consulta_id,
        catalogo_id=body.catalogo_id,
        user_id=user.id,
        nome=body.nome,
        descricao=body.descricao,
        valor=body.valor,
        realizado=body.realizado,
        observacoes=body.observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class CatalogoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: bool = False
    observacoes: Optional[str] = None


@router.get("/catalogo/procedimentos")
def listar_catalogo_procedimentos(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).order_by(CatalogoProcedimento.nome).all()


@router.post("/catalogo/procedimentos", status_code=201)
def criar_catalogo_procedimento(
    body: CatalogoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = CatalogoProcedimento(
        nome=body.nome,
        descricao=body.descricao,
        categoria=body.categoria,
        valor_padrao=body.valor_padrao,
        duracao_minutos=body.duracao_minutos,
        requer_anestesia=body.requer_anestesia,
        observacoes=body.observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE MEDICAMENTOS
# ═══════════════════════════════════════════════════════════════

class MedicamentoCreate(BaseModel):
    nome: str
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: bool = False
    eh_controlado: bool = False
    observacoes: Optional[str] = None


@router.get("/catalogo/medicamentos")
def listar_medicamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(
            or_(
                MedicamentoCatalogo.nome.ilike(termo),
                MedicamentoCatalogo.principio_ativo.ilike(termo),
                MedicamentoCatalogo.nome_comercial.ilike(termo),
            )
        )
    return q.order_by(MedicamentoCatalogo.nome).limit(50).all()


@router.post("/catalogo/medicamentos", status_code=201)
def criar_medicamento(
    body: MedicamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    m = MedicamentoCatalogo(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ═══════════════════════════════════════════════════════════════
# PROTOCOLOS DE VACINAS
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogo/protocolos-vacinas")
def listar_protocolos_vacinas(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).order_by(ProtocoloVacina.nome).all()


@router.post("/catalogo/protocolos-vacinas", status_code=201)
def criar_protocolo_vacina(
    nome: str,
    especie: Optional[str] = None,
    reforco_anual: bool = True,
    numero_doses_serie: int = 1,
    intervalo_doses_dias: Optional[int] = None,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProtocoloVacina(
        nome=nome,
        especie=especie,
        reforco_anual=reforco_anual,
        numero_doses_serie=numero_doses_serie,
        intervalo_doses_dias=intervalo_doses_dias,
        observacoes=observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ═══════════════════════════════════════════════════════════════
# INTERNAÇÃO
# ═══════════════════════════════════════════════════════════════

class InternacaoCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    motivo: str
    data_entrada: Optional[datetime] = None


class EvolucaoCreate(BaseModel):
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    nivel_dor: Optional[int] = None
    pressao_sistolica: Optional[int] = None
    glicemia: Optional[float] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None


@router.get("/internacoes")
def listar_internacoes(
    status: Optional[str] = "internado",
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(InternacaoVet).filter(InternacaoVet.tenant_id == tenant_id)
    if status:
        q = q.filter(InternacaoVet.status == status)
    internacoes = q.order_by(InternacaoVet.data_entrada.desc()).all()
    result = []
    for i in internacoes:
        result.append({
            "id": i.id,
            "pet_id": i.pet_id,
            "pet_nome": i.pet.nome if i.pet else None,
            "motivo": i.motivo,
            "status": i.status,
            "data_entrada": i.data_entrada,
            "data_saida": i.data_saida,
        })
    return result


@router.post("/internacoes", status_code=201)
def criar_internacao(
    body: InternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    i = InternacaoVet(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        motivo=body.motivo,
        data_entrada=body.data_entrada or datetime.now(),
        status="internado",
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return {"id": i.id, "status": i.status, "data_entrada": i.data_entrada}


@router.post("/internacoes/{internacao_id}/evolucao", status_code=201)
def registrar_evolucao(
    internacao_id: int,
    body: EvolucaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    i = db.query(InternacaoVet).filter(
        InternacaoVet.id == internacao_id,
        InternacaoVet.tenant_id == tenant_id,
    ).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user.id,
        **body.model_dump(exclude_unset=False),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.patch("/internacoes/{internacao_id}/alta")
def dar_alta(
    internacao_id: int,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    i = db.query(InternacaoVet).filter(
        InternacaoVet.id == internacao_id,
        InternacaoVet.tenant_id == tenant_id,
    ).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")
    i.status = "alta"
    i.data_saida = datetime.now()
    if observacoes:
        i.observacoes = observacoes
    db.commit()
    return {"ok": True, "status": "alta", "data_saida": i.data_saida}


# ═══════════════════════════════════════════════════════════════
# PERFIL COMPORTAMENTAL
# ═══════════════════════════════════════════════════════════════

class PerfilComportamentalIn(BaseModel):
    temperamento: Optional[str] = None
    reacao_animais: Optional[str] = None
    reacao_pessoas: Optional[str] = None
    medo_secador: Optional[str] = None
    medo_tesoura: Optional[str] = None
    aceita_focinheira: Optional[str] = None
    comportamento_carro: Optional[str] = None
    observacoes: Optional[str] = None


@router.get("/pets/{pet_id}/perfil-comportamental")
def obter_perfil_comportamental(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()
    return perfil or {}


@router.put("/pets/{pet_id}/perfil-comportamental")
def salvar_perfil_comportamental(
    pet_id: int,
    body: PerfilComportamentalIn,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()

    if perfil:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(perfil, field, value)
    else:
        perfil = PerfilComportamental(
            pet_id=pet_id,
            user_id=user.id,
            **body.model_dump(),
        )
        db.add(perfil)

    db.commit()
    db.refresh(perfil)
    return perfil


# ═══════════════════════════════════════════════════════════════
# DASHBOARD VETERINÁRIO
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Resumo do dia para o dashboard veterinário."""
    user, tenant_id = _get_tenant(current)
    hoje = date.today()

    agendamentos_hoje = db.query(func.count(AgendamentoVet.id)).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == hoje,
    ).scalar() or 0

    em_atendimento = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.status == "em_andamento",
    ).scalar() or 0

    internados = db.query(func.count(InternacaoVet.id)).filter(
        InternacaoVet.tenant_id == tenant_id,
        InternacaoVet.status == "internado",
    ).scalar() or 0

    from datetime import timedelta
    vacinas_vencendo_30d = db.query(func.count(VacinaRegistro.id)).filter(
        VacinaRegistro.tenant_id == tenant_id,
        VacinaRegistro.data_proxima_dose != None,  # noqa
        VacinaRegistro.data_proxima_dose >= hoje,
        VacinaRegistro.data_proxima_dose <= hoje + timedelta(days=30),
    ).scalar() or 0

    consultas_mes = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.extract("month", ConsultaVet.created_at) == hoje.month,
        func.extract("year", ConsultaVet.created_at) == hoje.year,
    ).scalar() or 0

    return {
        "agendamentos_hoje": agendamentos_hoje,
        "em_atendimento": em_atendimento,
        "internados": internados,
        "vacinas_vencendo_30d": vacinas_vencendo_30d,
        "consultas_mes": consultas_mes,
    }
