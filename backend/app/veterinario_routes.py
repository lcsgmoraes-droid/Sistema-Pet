"""
Rotas do módulo veterinário.
Cobre: agendamentos, consultas, vacinas, exames, prescrições,
internações, peso, fotos, catálogos e perfil comportamental.
"""
import hashlib
import json
import re
import secrets
import csv
from datetime import date, datetime, timedelta
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet, Tenant, User
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
    VetPartnerLink,
)

router = APIRouter(prefix="/vet", tags=["Veterinário"])


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_tenant(current: tuple) -> tuple:
    """Extrai user e tenant_id do tuple retornado pelo Depends."""
    user, tenant_id = current
    return user, tenant_id


def _get_partner_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna lista de empresa_tenant_ids onde este vet é parceiro ativo."""
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).all()
    return [link.empresa_tenant_id for link in links]


def _all_accessible_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna tenant_id atual + todos os tenants das empresas parceiras vinculadas."""
    return [str(tenant_id)] + _get_partner_tenant_ids(db, tenant_id)


def _pet_or_404(db: Session, pet_id: int, tenant_id) -> Pet:
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Pet.id == pet_id, Cliente.tenant_id.in_(tenant_ids))
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    return pet


def _consulta_or_404(db: Session, consulta_id: int, tenant_id) -> ConsultaVet:
    c = db.query(ConsultaVet).filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


_BAIA_MOTIVO_RE = re.compile(r"\s*\[BAIA:(?P<baia>[^\]]+)\]\s*$")
_PROC_PREFIX = "[PROC_INT]"


def _pack_motivo_baia(motivo: str, baia: Optional[str]) -> str:
    motivo_limpo = (motivo or "").strip()
    baia_limpa = (baia or "").strip()
    if not baia_limpa:
        return motivo_limpo
    return f"{motivo_limpo} [BAIA:{baia_limpa}]"


def _split_motivo_baia(motivo: Optional[str]) -> tuple[str, Optional[str]]:
    texto = (motivo or "").strip()
    m = _BAIA_MOTIVO_RE.search(texto)
    if not m:
        return texto, None
    baia = (m.group("baia") or "").strip() or None
    motivo_sem_baia = _BAIA_MOTIVO_RE.sub("", texto).strip()
    return motivo_sem_baia, baia


def _normalizar_baia(baia: Optional[str]) -> Optional[str]:
    valor = (baia or "").strip()
    if not valor:
        return None
    return valor.lower()


def _build_procedimento_observacao(payload: dict) -> str:
    return f"{_PROC_PREFIX}{json.dumps(payload, ensure_ascii=False)}"


def _parse_procedimento_observacao(observacoes: Optional[str]) -> Optional[dict]:
    texto = (observacoes or "").strip()
    if not texto.startswith(_PROC_PREFIX):
        return None
    bruto = texto[len(_PROC_PREFIX):]
    if not bruto:
        return None
    try:
        parsed = json.loads(bruto)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _separar_evolucoes_e_procedimentos(registros: list[EvolucaoInternacao]) -> tuple[list[dict], list[dict]]:
    evolucoes_formatadas = []
    procedimentos_formatados = []

    for ev in registros:
        proc_payload = _parse_procedimento_observacao(ev.observacoes)
        if proc_payload:
            procedimentos_formatados.append({
                "id": ev.id,
                "data_hora": ev.data_hora,
                "status": proc_payload.get("status") or "concluido",
                "horario_agendado": proc_payload.get("horario_agendado"),
                "medicamento": proc_payload.get("medicamento"),
                "dose": proc_payload.get("dose"),
                "via": proc_payload.get("via"),
                "executado_por": proc_payload.get("executado_por"),
                "horario_execucao": proc_payload.get("horario_execucao"),
                "observacao_execucao": proc_payload.get("observacao_execucao"),
                "observacoes_agenda": proc_payload.get("observacoes_agenda"),
            })
            continue

        evolucoes_formatadas.append({
            "id": ev.id,
            "data_hora": ev.data_hora,
            "temperatura": ev.temperatura,
            "freq_cardiaca": ev.frequencia_cardiaca,
            "freq_respiratoria": ev.frequencia_respiratoria,
            "nivel_dor": ev.nivel_dor,
            "pressao_sistolica": ev.pressao_sistolica,
            "glicemia": ev.glicemia,
            "peso": ev.peso,
            "observacoes": ev.observacoes,
        })

    return evolucoes_formatadas, procedimentos_formatados


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


# ═══════════════════════════════════════════════════════════════
# VETERINÁRIOS (listagem para seleção em formulários)
# ═══════════════════════════════════════════════════════════════

class VeterinarioSimples(BaseModel):
    id: int
    nome: str
    crmv: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/veterinarios", response_model=List[VeterinarioSimples])
def listar_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista pessoas cadastradas como veterinário neste tenant (para selects nos formulários)."""
    user, tenant_id = _get_tenant(current)
    vets = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "veterinario",
            Cliente.ativo == True,
        )
        .order_by(Cliente.nome)
        .all()
    )
    return [
        {"id": v.id, "nome": v.nome, "crmv": getattr(v, "crmv", None), "email": v.email, "telefone": v.telefone}
        for v in vets
    ]


# ═══════════════════════════════════════════════════════════════
# PETS ACESSÍVEIS (próprio tenant + empresas parceiras)
# ═══════════════════════════════════════════════════════════════

@router.get("/pets")
def listar_pets_vet(
    busca: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista os pets acessíveis ao veterinário:
    - pets do próprio tenant (se tiver cadastros próprios)
    - pets de todas as empresas parceiras ativas vinculadas
    """
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)

    q = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Cliente.tenant_id.in_(tenant_ids), Pet.ativo == True)
    )

    if busca:
        busca_term = f"%{busca}%"
        q = q.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Cliente.nome.ilike(busca_term),
            )
        )

    pets = q.order_by(Pet.nome).limit(limit).all()

    return [
        {
            "id": p.id,
            "codigo": p.codigo,
            "cliente_id": p.cliente_id,
            "nome": p.nome,
            "especie": p.especie,
            "raca": p.raca,
            "sexo": p.sexo,
            "castrado": p.castrado,
            "data_nascimento": p.data_nascimento,
            "peso": p.peso,
            "porte": p.porte,
            "microchip": p.microchip,
            "alergias": p.alergias,
            "doencas_cronicas": p.doencas_cronicas,
            "medicamentos_continuos": p.medicamentos_continuos,
            "historico_clinico": p.historico_clinico,
            "observacoes": p.observacoes,
            "foto_url": p.foto_url,
            "ativo": p.ativo,
            "tenant_id": str(p.tenant_id),
            "cliente_nome": p.cliente.nome if p.cliente else None,
            "cliente_telefone": p.cliente.telefone if p.cliente else None,
            "cliente_celular": p.cliente.celular if p.cliente else None,
        }
        for p in pets
    ]


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

    # Fallback defensivo: alguns fluxos podem chegar sem tenant no contexto.
    if tenant_id is None:
        cliente_ref = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
        if not cliente_ref or not cliente_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Cliente inválido para criação da consulta")
        tenant_id = cliente_ref.tenant_id

    cliente_ok = db.query(Cliente).filter(
        Cliente.id == body.cliente_id,
        Cliente.tenant_id == tenant_id,
    ).first()
    if not cliente_ok:
        raise HTTPException(status_code=404, detail="Tutor não encontrado neste tenant")

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.cliente_id == body.cliente_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado para o tutor informado")

    c = ConsultaVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
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
    c.hash_prontuario = _hash_prontuario_consulta(c)

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


def _hash_prontuario_consulta(c: ConsultaVet) -> str:
    conteudo = f"{c.id}|{c.pet_id}|{c.diagnostico}|{c.conduta}|{c.finalizado_em}"
    return hashlib.sha256(conteudo.encode()).hexdigest()


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

    if tenant_id is None:
        consulta_ref = db.query(ConsultaVet).filter(ConsultaVet.id == body.consulta_id).first()
        if not consulta_ref or not consulta_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Consulta inválida para emissão de prescrição")
        tenant_id = consulta_ref.tenant_id

    consulta_ok = db.query(ConsultaVet).filter(
        ConsultaVet.id == body.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not consulta_ok:
        raise HTTPException(status_code=404, detail="Consulta não encontrada neste tenant")

    # Número sequencial
    total = db.query(func.count(PrescricaoVet.id)).filter(PrescricaoVet.tenant_id == tenant_id).scalar() or 0
    numero = f"REC-{total + 1:05d}"

    p = PrescricaoVet(
        consulta_id=body.consulta_id,
        pet_id=body.pet_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
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
            tenant_id=tenant_id,
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

    # Fallback defensivo: quando o tenant não vem no contexto, usa o tenant do pet informado.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=404, detail="Pet não encontrado")
        tenant_id = pet_ref.tenant_id

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

    # Fallback defensivo: em alguns fluxos o tenant pode vir nulo no contexto.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para registro de vacina")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar vacina")

    v = VacinaRegistro(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
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
    motivo: Optional[str] = None
    motivo_internacao: Optional[str] = None
    box: Optional[str] = None
    baia_numero: Optional[str] = None
    data_entrada: Optional[datetime] = None


class EvolucaoCreate(BaseModel):
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    # Compatibilidade com payload antigo do frontend
    freq_cardiaca: Optional[int] = None
    freq_respiratoria: Optional[int] = None
    nivel_dor: Optional[int] = None
    pressao_sistolica: Optional[int] = None
    glicemia: Optional[float] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None


class ProcedimentoInternacaoCreate(BaseModel):
    horario_agendado: Optional[datetime] = None
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    observacoes_agenda: Optional[str] = None
    executado_por: Optional[str] = None
    horario_execucao: Optional[datetime] = None
    observacao_execucao: Optional[str] = None
    status: Optional[str] = "concluido"


@router.get("/internacoes")
def listar_internacoes(
    status: Optional[str] = "internado",
    pet_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    data_saida_inicio: Optional[date] = Query(None),
    data_saida_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Compatibilidade: telas antigas enviavam "ativa" para status de internação aberta.
    status_map = {
        "ativa": "internado",
    }
    status_normalizado = status_map.get(status, status)

    # Fallback defensivo: em alguns fluxos o tenant pode vir no usuário e não no retorno do Depends.
    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado para listar internações")

    q = db.query(InternacaoVet).filter(InternacaoVet.tenant_id == tenant_id)
    if status_normalizado:
        q = q.filter(InternacaoVet.status == status_normalizado)
    if pet_id:
        q = q.filter(InternacaoVet.pet_id == pet_id)
    if cliente_id:
        q = q.filter(InternacaoVet.pet.has(Pet.cliente_id == cliente_id))
    if data_saida_inicio:
        q = q.filter(func.date(InternacaoVet.data_saida) >= data_saida_inicio)
    if data_saida_fim:
        q = q.filter(func.date(InternacaoVet.data_saida) <= data_saida_fim)

    internacoes = q.order_by(InternacaoVet.data_entrada.desc()).all()
    result = []
    for i in internacoes:
        motivo_limpo, box = _split_motivo_baia(i.motivo)
        tutor = i.pet.cliente if i.pet and i.pet.cliente else None
        result.append({
            "id": i.id,
            "pet_id": i.pet_id,
            "pet_nome": i.pet.nome if i.pet else None,
            "tutor_id": tutor.id if tutor else None,
            "tutor_nome": tutor.nome if tutor else None,
            "motivo": motivo_limpo,
            "box": box,
            "status": i.status,
            "data_entrada": i.data_entrada,
            "data_saida": i.data_saida,
            "observacoes_alta": i.observacoes,
        })
    return result


@router.get("/internacoes/{internacao_id}")
def obter_internacao(
    internacao_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    evolucoes = (
        db.query(EvolucaoInternacao)
        .filter(EvolucaoInternacao.internacao_id == internacao_id)
        .order_by(EvolucaoInternacao.data_hora.desc())
        .all()
    )

    motivo_limpo, box = _split_motivo_baia(i.motivo)

    evolucoes_formatadas, procedimentos_formatados = _separar_evolucoes_e_procedimentos(evolucoes)

    return {
        "id": i.id,
        "pet_id": i.pet_id,
        "pet_nome": i.pet.nome if i.pet else None,
        "tutor_id": i.pet.cliente.id if i.pet and i.pet.cliente else None,
        "tutor_nome": i.pet.cliente.nome if i.pet and i.pet.cliente else None,
        "motivo": motivo_limpo,
        "box": box,
        "status": i.status,
        "data_entrada": i.data_entrada,
        "data_saida": i.data_saida,
        "observacoes_alta": i.observacoes,
        "evolucoes": evolucoes_formatadas,
        "procedimentos": procedimentos_formatados,
    }


@router.get("/pets/{pet_id}/internacoes-historico")
def obter_historico_internacoes_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado")

    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(404, "Pet não encontrado")

    internacoes = (
        db.query(InternacaoVet)
        .filter(InternacaoVet.pet_id == pet_id, InternacaoVet.tenant_id == tenant_id)
        .order_by(InternacaoVet.data_entrada.desc())
        .all()
    )

    historico = []
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        registros = (
            db.query(EvolucaoInternacao)
            .filter(EvolucaoInternacao.internacao_id == internacao.id)
            .order_by(EvolucaoInternacao.data_hora.desc())
            .all()
        )
        evols, procs = _separar_evolucoes_e_procedimentos(registros)

        historico.append({
            "internacao_id": internacao.id,
            "status": internacao.status,
            "motivo": motivo_limpo,
            "box": box,
            "data_entrada": internacao.data_entrada,
            "data_saida": internacao.data_saida,
            "observacoes_alta": internacao.observacoes,
            "evolucoes": evols,
            "procedimentos": procs,
        })

    return {
        "pet_id": pet.id,
        "pet_nome": pet.nome,
        "historico": historico,
    }


@router.post("/internacoes", status_code=201)
def criar_internacao(
    body: InternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    motivo = (body.motivo or body.motivo_internacao or "").strip()
    box = (body.box or body.baia_numero or "").strip()
    box_normalizado = _normalizar_baia(box)
    if not motivo:
        raise HTTPException(status_code=422, detail="Campo 'motivo' é obrigatório")

    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para internação")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    if box_normalizado:
        internacoes_ativas = (
            db.query(InternacaoVet)
            .filter(
                InternacaoVet.tenant_id == tenant_id,
                InternacaoVet.status == "internado",
            )
            .all()
        )
        for internacao_ativa in internacoes_ativas:
            _, box_ocupado = _split_motivo_baia(internacao_ativa.motivo)
            if _normalizar_baia(box_ocupado) == box_normalizado:
                raise HTTPException(
                    status_code=409,
                    detail=f"A baia {box} já está ocupada por outro internado.",
                )

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para internação")

    i = InternacaoVet(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
        motivo=_pack_motivo_baia(motivo, box),
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

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    # Se o tenant veio no contexto, valida acesso. Se não veio, usa o tenant da internação.
    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_evolucao = i.tenant_id or tenant_id
    if tenant_id_evolucao is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar evolução")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar evolução")

    dados = body.model_dump(exclude_unset=True)
    # Compatibilidade de nomes de campos vindos de versões antigas da tela.
    if dados.get("frequencia_cardiaca") is None and body.freq_cardiaca is not None:
        dados["frequencia_cardiaca"] = body.freq_cardiaca
    if dados.get("frequencia_respiratoria") is None and body.freq_respiratoria is not None:
        dados["frequencia_respiratoria"] = body.freq_respiratoria
    dados.pop("freq_cardiaca", None)
    dados.pop("freq_respiratoria", None)

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_evolucao,
        **dados,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/internacoes/{internacao_id}/procedimento", status_code=201)
def registrar_procedimento_internacao(
    internacao_id: int,
    body: ProcedimentoInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_registro = i.tenant_id or tenant_id
    if tenant_id_registro is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar procedimento")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar procedimento")

    status_procedimento = (body.status or "concluido").strip().lower()
    if status_procedimento not in {"agendado", "concluido"}:
        raise HTTPException(status_code=422, detail="Status do procedimento inválido. Use 'agendado' ou 'concluido'.")

    if status_procedimento == "concluido":
        if not (body.executado_por or "").strip():
            raise HTTPException(status_code=422, detail="Campo 'executado_por' é obrigatório para procedimento concluído")
        if not body.horario_execucao:
            raise HTTPException(status_code=422, detail="Campo 'horario_execucao' é obrigatório para procedimento concluído")

    data_referencia = body.horario_agendado or body.horario_execucao or datetime.now()

    payload = {
        "status": status_procedimento,
        "horario_agendado": body.horario_agendado.isoformat() if body.horario_agendado else None,
        "medicamento": body.medicamento,
        "dose": body.dose,
        "via": body.via,
        "observacoes_agenda": body.observacoes_agenda,
        "executado_por": (body.executado_por or "").strip() or None,
        "horario_execucao": body.horario_execucao.isoformat() if body.horario_execucao else None,
        "observacao_execucao": body.observacao_execucao,
    }

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_registro,
        data_hora=data_referencia,
        observacoes=_build_procedimento_observacao(payload),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "data_hora": ev.data_hora,
        "status": status_procedimento,
        **payload,
    }


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
    _, tenant_id = _get_tenant(current)
    hoje = date.today()
    janela_30d = hoje - timedelta(days=30)

    agendamentos_hoje = db.query(func.count(AgendamentoVet.id)).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == hoje,
    ).scalar() or 0

    consultas_hoje = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) == hoje,
    ).scalar() or 0

    em_atendimento = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.status == "em_andamento",
    ).scalar() or 0

    internados = db.query(func.count(InternacaoVet.id)).filter(
        InternacaoVet.tenant_id == tenant_id,
        InternacaoVet.status == "internado",
    ).scalar() or 0

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

    consultas_com_retorno_vencido = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.data_retorno.isnot(None),
        ConsultaVet.data_retorno < hoje,
        ConsultaVet.status == "finalizada",
    ).all()

    retornos_pendentes = 0
    for consulta_base in consultas_com_retorno_vencido:
        existe_retorno = db.query(ConsultaVet.id).filter(
            ConsultaVet.tenant_id == tenant_id,
            ConsultaVet.pet_id == consulta_base.pet_id,
            ConsultaVet.tipo == "retorno",
            ConsultaVet.status != "cancelada",
            func.date(ConsultaVet.created_at) >= consulta_base.data_retorno,
        ).first()
        if not existe_retorno:
            retornos_pendentes += 1

    consultas_30d = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()

    total_30d = len(consultas_30d)
    retornos_30d = sum(1 for c in consultas_30d if (c.tipo or "").strip().lower() == "retorno")
    taxa_retorno_30d = round((retornos_30d / total_30d) * 100, 1) if total_30d else 0.0

    duracoes_min = []
    for consulta in consultas_30d:
        if consulta.inicio_atendimento and consulta.fim_atendimento:
            delta = consulta.fim_atendimento - consulta.inicio_atendimento
            duracoes_min.append(max(delta.total_seconds() / 60.0, 0))

    tempo_medio_atendimento_min = round(sum(duracoes_min) / len(duracoes_min), 1) if duracoes_min else 0.0

    return {
        "consultas_hoje": consultas_hoje,
        "agendamentos_hoje": agendamentos_hoje,
        "em_atendimento": em_atendimento,
        "internados": internados,
        "vacinas_vencendo_30d": vacinas_vencendo_30d,
        "consultas_mes": consultas_mes,
        "retornos_pendentes": retornos_pendentes,
        "total_consultas_30d": total_30d,
        "retornos_30d": retornos_30d,
        "taxa_retorno_30d": taxa_retorno_30d,
        "tempo_medio_atendimento_min": tempo_medio_atendimento_min,
    }


@router.get("/relatorios/clinicos")
def relatorio_clinico_vet(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    data_inicio = date.today() - timedelta(days=dias)

    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    total_consultas = len(consultas)
    consultas_finalizadas = sum(1 for c in consultas if (c.status or "").strip().lower() == "finalizada")

    diagnosticos_count = {}
    for consulta in consultas:
        diagnostico = (consulta.diagnostico or "").strip()
        if not diagnostico:
            continue
        chave = diagnostico.split("\n")[0].split(";")[0].strip()
        if not chave:
            continue
        diagnosticos_count[chave] = diagnosticos_count.get(chave, 0) + 1

    top_diagnosticos = [
        {"nome": nome, "quantidade": qtd}
        for nome, qtd in sorted(diagnosticos_count.items(), key=lambda item: item[1], reverse=True)[:top]
    ]

    top_procedimentos_db = (
        db.query(
            ProcedimentoConsulta.nome.label("nome"),
            func.count(ProcedimentoConsulta.id).label("quantidade"),
        )
        .join(ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id)
        .filter(
            ProcedimentoConsulta.tenant_id == tenant_id,
            func.date(ConsultaVet.created_at) >= data_inicio,
        )
        .group_by(ProcedimentoConsulta.nome)
        .order_by(func.count(ProcedimentoConsulta.id).desc())
        .limit(top)
        .all()
    )

    top_medicamentos_db = (
        db.query(
            ItemPrescricao.nome_medicamento.label("nome"),
            func.count(ItemPrescricao.id).label("quantidade"),
        )
        .join(PrescricaoVet, PrescricaoVet.id == ItemPrescricao.prescricao_id)
        .filter(
            PrescricaoVet.tenant_id == tenant_id,
            func.date(PrescricaoVet.created_at) >= data_inicio,
        )
        .group_by(ItemPrescricao.nome_medicamento)
        .order_by(func.count(ItemPrescricao.id).desc())
        .limit(top)
        .all()
    )

    return {
        "periodo_dias": dias,
        "consultas": {
            "total": total_consultas,
            "finalizadas": consultas_finalizadas,
            "em_andamento": max(total_consultas - consultas_finalizadas, 0),
        },
        "top_diagnosticos": [
            {"nome": item["nome"], "quantidade": int(item["quantidade"])}
            for item in top_diagnosticos
        ],
        "top_procedimentos": [
            {"nome": item.nome, "quantidade": int(item.quantidade)}
            for item in top_procedimentos_db
        ],
        "top_medicamentos": [
            {"nome": item.nome, "quantidade": int(item.quantidade)}
            for item in top_medicamentos_db
        ],
    }


@router.get("/relatorios/clinicos/export.csv")
def exportar_relatorio_clinico_csv(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    dados = relatorio_clinico_vet(dias=dias, top=top, db=db, current=current)
    conteudo = []
    conteudo.append(["Relatório clínico veterinário"])
    conteudo.append(["Período (dias)", str(dados["periodo_dias"])])
    conteudo.append(["Consultas totais", str(dados["consultas"]["total"])])
    conteudo.append(["Consultas finalizadas", str(dados["consultas"]["finalizadas"])])
    conteudo.append(["Consultas em andamento", str(dados["consultas"]["em_andamento"])])
    conteudo.append([])
    conteudo.append(["Top diagnósticos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_diagnosticos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])
    conteudo.append([])
    conteudo.append(["Top procedimentos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_procedimentos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])
    conteudo.append([])
    conteudo.append(["Top medicamentos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_medicamentos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])

    sio = StringIO()
    writer = csv.writer(sio, delimiter=';')
    writer.writerows(conteudo)
    csv_string = "\ufeff" + sio.getvalue()

    return Response(
        content=csv_string,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=relatorio_clinico_vet_{dias}d.csv"},
    )


@router.get("/consultas/{consulta_id}/assinatura")
def validar_assinatura_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if not c.finalizado_em or not c.hash_prontuario:
        return {
            "assinada": False,
            "hash_valido": False,
            "hash_prontuario": c.hash_prontuario,
            "hash_recalculado": None,
            "finalizado_em": c.finalizado_em,
            "motivo": "Consulta ainda não foi finalizada e assinada digitalmente.",
        }

    hash_recalculado = _hash_prontuario_consulta(c)
    return {
        "assinada": True,
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
        "hash_recalculado": hash_recalculado,
        "finalizado_em": c.finalizado_em,
        "motivo": "OK" if hash_recalculado == c.hash_prontuario else "Hash divergente: possível alteração após finalização.",
    }


# ═══════════════════════════════════════════════════════════════
# PARCEIRO VETERINÁRIO (MULTI-TENANT)
# ═══════════════════════════════════════════════════════════════


class PartnerLinkCreate(BaseModel):
    vet_tenant_id: str  # UUID do tenant do veterinário parceiro
    tipo_relacao: str = "parceiro"  # 'parceiro' | 'funcionario'
    comissao_empresa_pct: Optional[float] = None


class PartnerLinkUpdate(BaseModel):
    tipo_relacao: Optional[str] = None
    comissao_empresa_pct: Optional[float] = None
    ativo: Optional[bool] = None


class PartnerLinkResponse(BaseModel):
    id: int
    empresa_tenant_id: str
    vet_tenant_id: str
    tipo_relacao: str
    comissao_empresa_pct: Optional[float]
    ativo: bool
    criado_em: datetime
    # campos extras enriquecidos
    vet_tenant_nome: Optional[str] = None
    empresa_tenant_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/parceiros", response_model=List[PartnerLinkResponse], summary="Lista parcerias do tenant atual")
def listar_parceiros(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Retorna todos os vínculos de parceria em que o tenant atual é a empresa (loja)."""
    user, tenant_id = _get_tenant(current)
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).all()

    result = []
    for link in links:
        vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
        result.append(
            PartnerLinkResponse(
                id=link.id,
                empresa_tenant_id=str(link.empresa_tenant_id),
                vet_tenant_id=str(link.vet_tenant_id),
                tipo_relacao=link.tipo_relacao,
                comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
                ativo=link.ativo,
                criado_em=link.criado_em,
                vet_tenant_nome=vet_tenant.name if vet_tenant else None,
            )
        )
    return result


@router.post("/parceiros", response_model=PartnerLinkResponse, status_code=201, summary="Cria vínculo com veterinário parceiro")
def criar_parceiro(
    payload: PartnerLinkCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Cria um vínculo de parceria entre o tenant atual (loja) e um tenant veterinário."""
    user, tenant_id = _get_tenant(current)

    # Verifica se o tenant de destino existe
    vet_tenant = db.query(Tenant).filter(Tenant.id == payload.vet_tenant_id).first()
    if not vet_tenant:
        raise HTTPException(status_code=404, detail="Tenant do veterinário não encontrado.")

    # Impede vínculo consigo mesmo
    if str(payload.vet_tenant_id) == str(tenant_id):
        raise HTTPException(status_code=400, detail="O tenant parceiro não pode ser o mesmo tenant atual.")

    # Impede duplicata
    existente = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
        VetPartnerLink.vet_tenant_id == payload.vet_tenant_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um vínculo com este veterinário parceiro.")

    link = VetPartnerLink(
        empresa_tenant_id=str(tenant_id),
        vet_tenant_id=payload.vet_tenant_id,
        tipo_relacao=payload.tipo_relacao,
        comissao_empresa_pct=payload.comissao_empresa_pct,
        ativo=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name,
    )


@router.patch("/parceiros/{link_id}", response_model=PartnerLinkResponse, summary="Atualiza vínculo de parceria")
def atualizar_parceiro(
    link_id: int,
    payload: PartnerLinkUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")

    if payload.tipo_relacao is not None:
        link.tipo_relacao = payload.tipo_relacao
    if payload.comissao_empresa_pct is not None:
        link.comissao_empresa_pct = payload.comissao_empresa_pct
    if payload.ativo is not None:
        link.ativo = payload.ativo

    db.commit()
    db.refresh(link)

    vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name if vet_tenant else None,
    )


@router.delete("/parceiros/{link_id}", status_code=204, summary="Remove vínculo de parceria")
def remover_parceiro(
    link_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")
    db.delete(link)
    db.commit()


@router.get("/tenants-veterinarios", summary="Lista tenants com tipo veterinary_clinic")
def listar_tenants_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista tenants que podem ser vinculados como parceiros (veterinary_clinic)."""
    _get_tenant(current)
    tenants = db.query(Tenant).filter(
        Tenant.organization_type == "veterinary_clinic",
        Tenant.status == "active",
    ).all()
    return [{"id": str(t.id), "nome": t.name, "cnpj": t.cnpj} for t in tenants]
