"""
Rotas do módulo veterinário.
Cobre: agendamentos, consultas, vacinas, exames, prescrições,
internações, peso, fotos, catálogos e perfil comportamental.
"""
import hashlib
import csv
from datetime import date, datetime, timedelta
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .financeiro_models import ContaReceber
from .ia.aba6_models import Conversa, MensagemChat
from .models import Cliente, Pet, Tenant, User
from .pdf_veterinario import gerar_pdf_prontuario, gerar_pdf_receita
from .produtos_models import Produto
from .veterinario_agendamentos import (
    _agendamento_to_dict,
    _atualizar_status_agendamento,
    _consulta_tem_conteudo_clinico,
    _consulta_tem_dependencias,
    _garantir_sem_conflitos_agendamento,
    _sincronizar_marcos_agendamento,
    _validar_consultorio_agendamento,
    _validar_veterinario_agendamento,
)
from .veterinario_agenda_routes import router as agenda_router
from .veterinario_calendar import (
    buscar_agendamentos_para_calendario,
    gerar_calendario_ics,
    gerar_token_calendario_vet,
    montar_payload_calendario_vet,
)
from .veterinario_clinico import (
    _auditar_exame_pos_finalizacao,
    _bloquear_lancamento_em_consulta_finalizada,
    _consulta_or_404,
    _montar_alertas_pet,
    _pet_or_404,
    _prescricao_or_404,
    _status_vacinal_pet,
    _upsert_lembretes_push_agendamento,
)
from .veterinario_catalogo_routes import router as catalogo_router
from .veterinario_consultas_routes import router as consultas_router
from .veterinario_core import (
    _all_accessible_tenant_ids,
    _date_para_datetime_vet,
    _get_tenant,
    _normalizar_datetime_vet,
    _serializar_datetime_vet,
    _vet_now,
)
from .veterinario_exames_ia import (
    _gerar_interpretacao_exame,
)
from .veterinario_exames_arquivos import (
    _process_exam_file_with_ai,
    salvar_arquivo_exame_upload,
)
from .veterinario_exames_routes import router as exames_router
from .veterinario_financeiro import (
    _aplicar_baixa_estoque_itens,
    _aplicar_baixa_estoque_procedimento,
    _as_float,
    _enriquecer_insumos_com_custos,
    _normalizar_insumos,
    _obter_regra_financeira_veterinaria,
    _resumo_financeiro_procedimento,
    _round_money,
    _serializar_catalogo,
    _serializar_procedimento,
    _sincronizar_financeiro_procedimento,
)
from .veterinario_ia import (
    _carregar_memoria_conversa,
    _garantir_tabelas_memoria_ia,
    _montar_resposta_dose,
    _montar_resposta_interacao,
    _montar_resposta_plano_estruturado,
    _montar_resposta_sintomas,
    _normalizar_modo_ia,
    _obter_ou_criar_conversa_vet,
    _responder_chat_exame,
    _tentar_resposta_llm_veterinaria,
)
from .veterinario_ia_routes import router as ia_router
from .veterinario_internacao import (
    _build_payload_procedimento_agenda_internacao,
    _build_procedimento_observacao,
    _normalizar_baia,
    _pack_motivo_baia,
    _resolver_data_entrada_exibicao_internacao,
    _resolver_tenant_id_vet,
    _resolver_user_id_vet,
    _separar_evolucoes_e_procedimentos,
    _serializar_procedimento_agenda_internacao,
    _split_motivo_baia,
)
from .veterinario_internacao_routes import router as internacao_router
from .veterinario_preventivo import montar_calendario_preventivo
from .veterinario_schemas import (
    AgendamentoCreate,
    AgendamentoResponse,
    AgendamentoUpdate,
    CatalogoCreate,
    CatalogoResponse,
    CatalogoUpdate,
    ConsultaCreate,
    ConsultaResponse,
    ConsultaUpdate,
    ConsultorioCreate,
    ConsultorioResponse,
    ConsultorioUpdate,
    EvolucaoCreate,
    ExameChatPayload,
    ExameCreate,
    ExameResponse,
    ExameUpdate,
    InternacaoConfigUpdate,
    InternacaoCreate,
    ItemPrescricaoIn,
    MedicamentoCreate,
    MedicamentoUpdate,
    PartnerLinkCreate,
    PartnerLinkResponse,
    PartnerLinkUpdate,
    PerfilComportamentalIn,
    PrescricaoCreate,
    PrescricaoResponse,
    ProcedimentoAgendaInternacaoConcluir,
    ProcedimentoAgendaInternacaoCreate,
    ProcedimentoCreate,
    ProcedimentoInternacaoCreate,
    ProcedimentoResponse,
    ProtocoloVacinaUpdate,
    VacinaCreate,
    VacinaResponse,
    VeterinarioSimples,
    VetAssistenteIAPayload,
    VetMensagemFeedbackPayload,
)
from .veterinario_serializers import (
    _consulta_to_dict,
    _hash_prontuario_consulta,
    _prescricao_to_dict,
)
from .veterinario_models import (
    AgendamentoVet,
    CatalogoProcedimento,
    ConsultaVet,
    ConsultorioVet,
    ExameVet,
    FotoClinica,
    InternacaoConfig,
    InternacaoProcedimentoAgenda,
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
router.include_router(agenda_router)
router.include_router(internacao_router)
router.include_router(ia_router)
router.include_router(consultas_router)
router.include_router(exames_router)
router.include_router(catalogo_router)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════════════════════════


# Rotas de agenda/base ficam em veterinario_agenda_routes.py.

# Rotas de consultas e prescricoes ficam em veterinario_consultas_routes.py.


# ═══════════════════════════════════════════════════════════════
# VACINAS
# ═══════════════════════════════════════════════════════════════

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

    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")

    if body.consulta_id:
        _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "novo registro de vacina vinculado")

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
    _atualizar_status_agendamento(
        db,
        tenant_id=tenant_id,
        agendamento_id=body.agendamento_id,
        status_agendamento="finalizado",
    )
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


# Rotas de exames ficam em veterinario_exames_routes.py.


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


# Rotas de procedimentos/catalogos ficam em veterinario_catalogo_routes.py.



# Rotas de internacao ficam em veterinario_internacao_routes.py.



# ═══════════════════════════════════════════════════════════════
# PERFIL COMPORTAMENTAL
# ═══════════════════════════════════════════════════════════════

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
    procedimentos_30d = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    financeiro_30d = [_resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira) for procedimento in procedimentos_30d]
    faturamento_procedimentos_30d = _round_money(sum(item["valor_cobrado"] for item in financeiro_30d))
    custo_procedimentos_30d = _round_money(sum(item["custo_total"] for item in financeiro_30d))
    margem_procedimentos_30d = _round_money(sum(item["margem_valor"] for item in financeiro_30d))
    margem_percentual_procedimentos_30d = round((margem_procedimentos_30d / faturamento_procedimentos_30d) * 100, 2) if faturamento_procedimentos_30d > 0 else 0.0
    repasse_empresa_procedimentos_30d = _round_money(sum(item["repasse_empresa_valor"] for item in financeiro_30d))
    receita_tenant_procedimentos_30d = _round_money(sum(item["receita_tenant_valor"] for item in financeiro_30d))
    entrada_empresa_procedimentos_30d = _round_money(sum(item["entrada_empresa_valor"] for item in financeiro_30d))

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
        "modelo_operacional_financeiro": regra_financeira["modo_operacional"],
        "comissao_empresa_pct_padrao": regra_financeira["comissao_empresa_pct"],
        "faturamento_procedimentos_30d": faturamento_procedimentos_30d,
        "custo_procedimentos_30d": custo_procedimentos_30d,
        "margem_procedimentos_30d": margem_procedimentos_30d,
        "margem_percentual_procedimentos_30d": margem_percentual_procedimentos_30d,
        "repasse_empresa_procedimentos_30d": repasse_empresa_procedimentos_30d,
        "receita_tenant_procedimentos_30d": receita_tenant_procedimentos_30d,
        "entrada_empresa_procedimentos_30d": entrada_empresa_procedimentos_30d,
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

    procedimentos_periodo = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    procedimentos_resumo = {}
    total_procedimentos_valor = 0.0
    total_procedimentos_custo = 0.0
    total_procedimentos_margem = 0.0
    total_repasse_empresa = 0.0
    total_receita_tenant = 0.0
    total_entrada_empresa = 0.0
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    for procedimento in procedimentos_periodo:
        resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira)
        chave = (procedimento.nome or "Procedimento").strip() or "Procedimento"
        item = procedimentos_resumo.setdefault(chave, {
            "nome": chave,
            "quantidade": 0,
            "valor_total": 0.0,
            "custo_total": 0.0,
            "margem_total": 0.0,
            "repasse_empresa_total": 0.0,
            "receita_tenant_total": 0.0,
            "entrada_empresa_total": 0.0,
        })
        item["quantidade"] += 1
        item["valor_total"] += resumo["valor_cobrado"]
        item["custo_total"] += resumo["custo_total"]
        item["margem_total"] += resumo["margem_valor"]
        item["repasse_empresa_total"] += resumo["repasse_empresa_valor"]
        item["receita_tenant_total"] += resumo["receita_tenant_valor"]
        item["entrada_empresa_total"] += resumo["entrada_empresa_valor"]
        total_procedimentos_valor += resumo["valor_cobrado"]
        total_procedimentos_custo += resumo["custo_total"]
        total_procedimentos_margem += resumo["margem_valor"]
        total_repasse_empresa += resumo["repasse_empresa_valor"]
        total_receita_tenant += resumo["receita_tenant_valor"]
        total_entrada_empresa += resumo["entrada_empresa_valor"]

    top_procedimentos = [
        {
            "nome": item["nome"],
            "quantidade": int(item["quantidade"]),
            "valor_total": _round_money(item["valor_total"]),
            "custo_total": _round_money(item["custo_total"]),
            "margem_total": _round_money(item["margem_total"]),
            "repasse_empresa_total": _round_money(item["repasse_empresa_total"]),
            "receita_tenant_total": _round_money(item["receita_tenant_total"]),
            "entrada_empresa_total": _round_money(item["entrada_empresa_total"]),
            "margem_percentual": round((item["margem_total"] / item["valor_total"]) * 100, 2) if item["valor_total"] > 0 else 0.0,
        }
        for item in sorted(
            procedimentos_resumo.values(),
            key=lambda item: (item["quantidade"], item["valor_total"]),
            reverse=True,
        )[:top]
    ]

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
        "financeiro_procedimentos": {
            "modo_operacional": regra_financeira["modo_operacional"],
            "comissao_empresa_pct": regra_financeira["comissao_empresa_pct"],
            "faturamento_total": _round_money(total_procedimentos_valor),
            "custo_total": _round_money(total_procedimentos_custo),
            "margem_total": _round_money(total_procedimentos_margem),
            "repasse_empresa_total": _round_money(total_repasse_empresa),
            "receita_tenant_total": _round_money(total_receita_tenant),
            "entrada_empresa_total": _round_money(total_entrada_empresa),
            "margem_percentual": round((total_procedimentos_margem / total_procedimentos_valor) * 100, 2) if total_procedimentos_valor > 0 else 0.0,
        },
        "top_diagnosticos": [
            {"nome": item["nome"], "quantidade": int(item["quantidade"])}
            for item in top_diagnosticos
        ],
        "top_procedimentos": top_procedimentos,
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
    conteudo.append(["Faturamento procedimentos", f"{dados['financeiro_procedimentos']['faturamento_total']:.2f}"])
    conteudo.append(["Custo procedimentos", f"{dados['financeiro_procedimentos']['custo_total']:.2f}"])
    conteudo.append(["Margem procedimentos", f"{dados['financeiro_procedimentos']['margem_total']:.2f}"])
    conteudo.append(["Margem % procedimentos", f"{dados['financeiro_procedimentos']['margem_percentual']:.2f}"])
    conteudo.append(["Modo operacional", dados["financeiro_procedimentos"]["modo_operacional"]])
    conteudo.append(["Comissão empresa %", f"{dados['financeiro_procedimentos']['comissao_empresa_pct']:.2f}"])
    conteudo.append(["Entrada empresa", f"{dados['financeiro_procedimentos']['entrada_empresa_total']:.2f}"])
    conteudo.append(["Repasse empresa", f"{dados['financeiro_procedimentos']['repasse_empresa_total']:.2f}"])
    conteudo.append(["Receita líquida vet", f"{dados['financeiro_procedimentos']['receita_tenant_total']:.2f}"])
    conteudo.append([])
    conteudo.append(["Top diagnósticos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_diagnosticos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])
    conteudo.append([])
    conteudo.append(["Top procedimentos"])
    conteudo.append(["Nome", "Quantidade", "Faturamento", "Custo", "Margem", "Entrada empresa", "Repasse empresa", "Líquido vet", "Margem %"])
    for item in dados["top_procedimentos"]:
        conteudo.append([
            item["nome"],
            str(item["quantidade"]),
            f"{item['valor_total']:.2f}",
            f"{item['custo_total']:.2f}",
            f"{item['margem_total']:.2f}",
            f"{item['entrada_empresa_total']:.2f}",
            f"{item['repasse_empresa_total']:.2f}",
            f"{item['receita_tenant_total']:.2f}",
            f"{item['margem_percentual']:.2f}",
        ])
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


@router.get("/consultas/{consulta_id}/prontuario.pdf")
def baixar_prontuario_pdf(
    consulta_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = (
        db.query(ConsultaVet)
        .options(
            joinedload(ConsultaVet.pet),
            joinedload(ConsultaVet.cliente),
            joinedload(ConsultaVet.veterinario),
            joinedload(ConsultaVet.prescricoes).joinedload(PrescricaoVet.itens),
        )
        .filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    if c.status != "finalizada":
        raise HTTPException(status_code=400, detail="A consulta precisa estar finalizada para gerar o prontuário em PDF")

    hash_recalculado = _hash_prontuario_consulta(c)
    validacao = {
        "assinada": bool(c.finalizado_em and c.hash_prontuario),
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
    }
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_prontuario(c, validacao, c.prescricoes or [], url_validacao)

    filename = f"prontuario_consulta_{consulta_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/prescricoes/{prescricao_id}/pdf")
def baixar_prescricao_pdf(
    prescricao_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    p = _prescricao_or_404(db, prescricao_id, tenant_id)
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{p.consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_receita(p, url_validacao)

    numero = (p.numero or f"prescricao_{p.id}").replace("/", "-")
    filename = f"{numero}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════
# PARCEIRO VETERINÁRIO (MULTI-TENANT)
# ═══════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════
# RELATÓRIO DE REPASSE — fechamento operacional parceiro
# ═══════════════════════════════════════════════════════════════

@router.get("/relatorios/repasse", summary="Relatório de repasse veterinário por período")
def relatorio_repasse(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as contas a receber geradas por procedimentos veterinários
    (documento começando com VET-PROC-), filtrando por período e status.
    Útil para fechar o repasse com o veterinário parceiro.
    """
    user, tenant_id = _get_tenant(current)

    query = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    )

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)
    if status:
        query = query.filter(ContaReceber.status == status)

    contas = query.order_by(ContaReceber.data_emissao.desc()).all()

    items = []
    total_valor = 0.0
    total_recebido = 0.0
    total_pendente = 0.0

    for c in contas:
        tipo = "repasse_empresa" if "-REPASSE-EMPRESA" in (c.documento or "") else "liquido_vet"
        valor = float(c.valor_final or 0)
        recebido = float(c.valor_recebido or 0)
        pendente = valor - recebido if c.status != "recebido" else 0.0

        total_valor += valor
        total_recebido += recebido if c.status == "recebido" else 0.0
        total_pendente += pendente

        items.append({
            "id": c.id,
            "documento": c.documento,
            "descricao": c.descricao,
            "tipo": tipo,
            "valor": valor,
            "valor_recebido": recebido,
            "data_emissao": c.data_emissao.isoformat() if c.data_emissao else None,
            "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
            "data_recebimento": c.data_recebimento.isoformat() if c.data_recebimento else None,
            "status": c.status,
            "observacoes": c.observacoes,
        })

    return {
        "items": items,
        "total_valor": _round_money(total_valor),
        "total_recebido": _round_money(total_recebido),
        "total_pendente": _round_money(total_pendente),
        "quantidade": len(items),
    }


@router.post("/relatorios/repasse/{conta_id}/baixar", summary="Dá baixa (recebimento) em um lançamento de repasse")
def baixar_repasse(
    conta_id: int,
    data_recebimento: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Marca um lançamento de repasse veterinário como recebido.
    Atualiza status='recebido', valor_recebido=valor_final e data_recebimento.
    """
    user, tenant_id = _get_tenant(current)

    conta = db.query(ContaReceber).filter(
        ContaReceber.id == conta_id,
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    ).first()

    if not conta:
        raise HTTPException(404, "Lançamento de repasse não encontrado.")
    if conta.status == "recebido":
        raise HTTPException(400, "Este lançamento já foi baixado.")

    conta.status = "recebido"
    conta.valor_recebido = conta.valor_final
    conta.data_recebimento = data_recebimento or date.today()
    db.commit()

    return {
        "ok": True,
        "id": conta.id,
        "status": conta.status,
        "data_recebimento": conta.data_recebimento.isoformat(),
        "valor_recebido": float(conta.valor_recebido),
    }



# Rotas de IA veterinaria ficam em veterinario_ia_routes.py.

# ═══════════════════════════════════════════════════════════════
# CALENDÁRIO PREVENTIVO — protocolos por espécie
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogo/calendario-preventivo", summary="Calendário preventivo por espécie")
def calendario_preventivo(
    especie: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Retorna o calendário preventivo padrão por espécie (cão, gato, coelho, todos)
    mesclado com os protocolos de vacina configurados pelo tenant.
    """
    user, tenant_id = _get_tenant(current)
    return montar_calendario_preventivo(db, tenant_id, especie)
