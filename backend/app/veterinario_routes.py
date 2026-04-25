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


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════════════════════════


# Rotas de agenda/base ficam em veterinario_agenda_routes.py.

# ═══════════════════════════════════════════════════════════════
# CONSULTAS
# ═══════════════════════════════════════════════════════════════

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
        inicio_atendimento=_vet_now(),
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
            _sincronizar_marcos_agendamento(ag)

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


@router.get("/consultas/{consulta_id}/timeline")
def obter_timeline_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    eventos: list[dict] = []

    def adicionar_evento(*, kind: str, item_id: int | str, titulo: str, status_item: Optional[str], data_evento: Optional[datetime], descricao: Optional[str] = None, link: Optional[str] = None, meta: Optional[dict] = None):
        if data_evento is None:
            return
        data_evento_ordenacao = _normalizar_datetime_vet(data_evento) or data_evento
        eventos.append({
            "kind": kind,
            "item_id": item_id,
            "titulo": titulo,
            "status": status_item,
            "data_hora": _serializar_datetime_vet(data_evento),
            "descricao": descricao,
            "link": link,
            "meta": meta or {},
            "_ordem": data_evento_ordenacao,
        })

    adicionar_evento(
        kind="consulta",
        item_id=c.id,
        titulo=f"Consulta #{c.id} iniciada",
        status_item=c.status,
        data_evento=c.inicio_atendimento or c.created_at,
        descricao=c.queixa_principal or c.diagnostico or c.conduta,
        link=f"/veterinario/consultas/{c.id}",
    )

    if c.finalizado_em:
        adicionar_evento(
            kind="alta_consulta",
            item_id=f"consulta-finalizada-{c.id}",
            titulo=f"Consulta #{c.id} finalizada",
            status_item="finalizada",
            data_evento=c.finalizado_em,
            descricao=c.diagnostico or c.conduta or "Consulta concluída.",
            link=f"/veterinario/consultas/{c.id}",
        )

    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    for procedimento in procedimentos:
        adicionar_evento(
            kind="procedimento",
            item_id=procedimento.id,
            titulo=procedimento.nome,
            status_item="realizado" if procedimento.realizado else "pendente",
            data_evento=procedimento.created_at,
            descricao=procedimento.observacoes or procedimento.descricao,
            link=f"/veterinario/consultas/{c.id}",
            meta={
                "valor": _round_money(procedimento.valor),
                "insumos": _normalizar_insumos(procedimento.insumos),
                "estoque_baixado": bool(procedimento.estoque_baixado),
            },
        )

    exames = db.query(ExameVet).filter(
        ExameVet.consulta_id == consulta_id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).all()
    for exame in exames:
        adicionar_evento(
            kind="exame",
            item_id=exame.id,
            titulo=exame.nome,
            status_item=exame.status,
            data_evento=_date_para_datetime_vet(exame.data_resultado) or _date_para_datetime_vet(exame.data_solicitacao) or exame.created_at,
            descricao=exame.observacoes or exame.interpretacao_ia_resumo or exame.tipo,
            link=f"/veterinario/exames?consulta_id={c.id}&pet_id={c.pet_id}",
            meta={
                "tipo": exame.tipo,
                "arquivo_nome": exame.arquivo_nome,
                "arquivo_url": exame.arquivo_url,
            },
        )

    vacinas = db.query(VacinaRegistro).filter(
        VacinaRegistro.consulta_id == consulta_id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()
    for vacina in vacinas:
        adicionar_evento(
            kind="vacina",
            item_id=vacina.id,
            titulo=vacina.nome_vacina,
            status_item="aplicada",
            data_evento=_date_para_datetime_vet(vacina.data_aplicacao),
            descricao=vacina.observacoes or vacina.fabricante,
            link=f"/veterinario/vacinas?consulta_id={c.id}&pet_id={c.pet_id}",
            meta={
                "lote": vacina.lote,
                "numero_dose": vacina.numero_dose,
                "proxima_dose": vacina.data_proxima_dose.isoformat() if vacina.data_proxima_dose else None,
            },
        )

    internacoes = db.query(InternacaoVet).filter(
        InternacaoVet.consulta_id == consulta_id,
        InternacaoVet.tenant_id == tenant_id,
    ).order_by(InternacaoVet.data_entrada.desc()).all()
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        adicionar_evento(
            kind="internacao",
            item_id=internacao.id,
            titulo=f"Internação #{internacao.id}",
            status_item=internacao.status,
            data_evento=internacao.data_entrada,
            descricao=motivo_limpo or internacao.observacoes,
            link=f"/veterinario/internacoes?consulta_id={c.id}",
            meta={
                "box": box,
                "data_saida": _serializar_datetime_vet(internacao.data_saida).isoformat() if internacao.data_saida else None,
            },
        )
        if internacao.data_saida:
            adicionar_evento(
                kind="alta_internacao",
                item_id=f"alta-{internacao.id}",
                titulo=f"Alta da internação #{internacao.id}",
                status_item=internacao.status,
                data_evento=internacao.data_saida,
                descricao=internacao.observacoes,
                link=f"/veterinario/internacoes?consulta_id={c.id}",
                meta={"box": box},
            )

    prescricoes = db.query(PrescricaoVet).filter(
        PrescricaoVet.consulta_id == consulta_id,
        PrescricaoVet.tenant_id == tenant_id,
    ).order_by(PrescricaoVet.created_at.desc()).all()
    for prescricao in prescricoes:
        adicionar_evento(
            kind="prescricao",
            item_id=prescricao.id,
            titulo=prescricao.numero or f"Prescrição #{prescricao.id}",
            status_item=prescricao.tipo_receituario,
            data_evento=prescricao.created_at,
            descricao=prescricao.observacoes,
            link=f"/veterinario/consultas/{c.id}",
            meta={
                "itens": len(prescricao.itens or []),
                "hash_receita": prescricao.hash_receita,
            },
        )

    eventos.sort(key=lambda item: item["_ordem"], reverse=True)
    for item in eventos:
        item.pop("_ordem", None)
    return {
        "consulta_id": c.id,
        "pet_id": c.pet_id,
        "pet_nome": c.pet.nome if c.pet else None,
        "eventos": eventos,
    }


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
    c.fim_atendimento = _vet_now()
    c.finalizado_em = _vet_now()
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


# ═══════════════════════════════════════════════════════════════
# PRESCRIÇÕES
# ═══════════════════════════════════════════════════════════════

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
    if consulta_ok.pet_id != body.pet_id:
        raise HTTPException(status_code=422, detail="Pet da prescricao nao confere com o pet da consulta")
    _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "nova prescricao vinculada")
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


# ═══════════════════════════════════════════════════════════════
# EXAMES
# ═══════════════════════════════════════════════════════════════

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


@router.get("/exames", summary="Lista exames com arquivo anexado")
def listar_exames_anexados(
    periodo: str = Query("hoje", description="hoje | semana | periodo"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    tutor: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    periodo = (periodo or "hoje").strip().lower()
    hoje = date.today()

    if periodo == "hoje":
        inicio_ref = hoje
        fim_ref = hoje
    elif periodo == "semana":
        inicio_ref = hoje - timedelta(days=6)
        fim_ref = hoje
    elif periodo == "periodo":
        if not data_inicio or not data_fim:
            raise HTTPException(422, "Informe data_inicio e data_fim para o período personalizado.")
        inicio_ref = data_inicio
        fim_ref = data_fim
    else:
        raise HTTPException(422, "Período inválido. Use: hoje, semana ou periodo.")

    data_ref_expr = func.date(func.coalesce(ExameVet.data_resultado, ExameVet.created_at))

    q = (
        db.query(ExameVet)
        .join(Pet, Pet.id == ExameVet.pet_id)
        .outerjoin(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            ExameVet.tenant_id == tenant_id,
            ExameVet.arquivo_url.isnot(None),
            ExameVet.arquivo_url != "",
            data_ref_expr >= inicio_ref,
            data_ref_expr <= fim_ref,
        )
    )

    if tutor and tutor.strip():
        termo = f"%{tutor.strip()}%"
        q = q.filter(Cliente.nome.ilike(termo))

    exames = q.order_by(data_ref_expr.desc(), ExameVet.id.desc()).all()

    items = []
    for exame in exames:
        data_upload = exame.data_resultado
        if not data_upload and exame.created_at:
            data_upload = exame.created_at.date()

        pet = exame.pet
        tutor_nome = pet.cliente.nome if pet and pet.cliente else None

        items.append({
            "exame_id": exame.id,
            "pet_id": exame.pet_id,
            "consulta_id": exame.consulta_id,
            "pet_nome": pet.nome if pet else None,
            "tutor_nome": tutor_nome,
            "nome_exame": exame.nome,
            "tipo": exame.tipo,
            "status": exame.status,
            "data_upload": data_upload.isoformat() if data_upload else None,
            "arquivo_nome": exame.arquivo_nome,
            "arquivo_url": exame.arquivo_url,
            "tem_interpretacao_ia": bool(exame.interpretacao_ia),
        })

    return {
        "items": items,
        "total": len(items),
        "periodo": periodo,
        "data_inicio": inicio_ref.isoformat(),
        "data_fim": fim_ref.isoformat(),
    }


@router.post("/exames", response_model=ExameResponse, status_code=201)
def criar_exame(
    body: ExameCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")
    if body.consulta_id:
        _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "nova solicitacao de exame vinculada")

    e = ExameVet(
        tenant_id=tenant_id,
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
    _atualizar_status_agendamento(
        db,
        tenant_id=tenant_id,
        agendamento_id=body.agendamento_id,
        status_agendamento="finalizado",
    )
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
    dados_update = body.model_dump(exclude_unset=True)
    audit_old = {
        "status": e.status,
        "data_resultado": e.data_resultado,
        "resultado_texto": e.resultado_texto,
        "resultado_json": e.resultado_json,
        "arquivo_url": e.arquivo_url,
    }
    for field, value in dados_update.items():
        setattr(e, field, value)
    if body.data_resultado and e.status == "solicitado":
        e.status = "disponivel"
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=e,
        action="vet_exame_update_pos_finalizacao",
        details={"campos": sorted(dados_update.keys())},
        old_value=audit_old,
        new_value={
            "status": e.status,
            "data_resultado": e.data_resultado,
            "resultado_texto": e.resultado_texto,
            "resultado_json": e.resultado_json,
            "arquivo_url": e.arquivo_url,
        },
    )
    db.commit()
    db.refresh(e)
    return e


@router.post("/exames/{exame_id}/interpretar-ia", response_model=ExameResponse)
def interpretar_exame_ia(
    exame_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")
    if not exame.resultado_texto and not exame.resultado_json:
        if exame.arquivo_url:
            exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
        else:
            raise HTTPException(400, "O exame ainda não possui resultado para interpretar")

    analise = _gerar_interpretacao_exame(exame)
    exame.interpretacao_ia = analise["conclusao"]
    exame.interpretacao_ia_resumo = analise["resumo"]
    exame.interpretacao_ia_confianca = analise["confianca"]
    exame.interpretacao_ia_alertas = analise["alertas"]
    exame.interpretacao_ia_payload = analise["payload"]
    if exame.status in {"disponivel", "aguardando", "coletado", "solicitado"}:
        exame.status = "interpretado"
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_ia_pos_finalizacao",
        details={"origem": "interpretar_ia"},
        new_value={"status": exame.status, "interpretacao_ia_resumo": exame.interpretacao_ia_resumo},
    )
    db.commit()
    db.refresh(exame)
    return exame


@router.post("/exames/{exame_id}/processar-arquivo-ia", response_model=ExameResponse)
def processar_arquivo_exame_ia(
    exame_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")
    if not exame.arquivo_url:
        raise HTTPException(400, "O exame ainda não possui arquivo anexado.")

    exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_process_file_ia_pos_finalizacao",
        details={"origem": "processar_arquivo_ia"},
        new_value={"status": exame.status, "resultado_texto": exame.resultado_texto},
    )
    db.commit()
    db.refresh(exame)
    return exame


@router.post("/exames/{exame_id}/arquivo", response_model=ExameResponse)
def upload_arquivo_exame(
    exame_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")

    audit_old = {
        "arquivo_url": exame.arquivo_url,
        "arquivo_nome": exame.arquivo_nome,
        "status": exame.status,
        "data_resultado": exame.data_resultado,
    }

    nome_original = salvar_arquivo_exame_upload(exame, tenant_id, arquivo)
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_upload_pos_finalizacao",
        details={"arquivo_nome": nome_original},
        old_value=audit_old,
        new_value={
            "arquivo_url": exame.arquivo_url,
            "arquivo_nome": exame.arquivo_nome,
            "status": exame.status,
            "data_resultado": exame.data_resultado,
        },
    )
    db.commit()
    db.refresh(exame)
    return exame


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

@router.get("/consultas/{consulta_id}/procedimentos", response_model=List[ProcedimentoResponse])
def listar_procedimentos_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    return [_serializar_procedimento(procedimento, db, tenant_id) for procedimento in procedimentos]


@router.post("/procedimentos", response_model=ProcedimentoResponse, status_code=201)
def adicionar_procedimento(
    body: ProcedimentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    consulta = _consulta_or_404(db, body.consulta_id, tenant_id)
    _bloquear_lancamento_em_consulta_finalizada(consulta, "novo procedimento vinculado")

    catalogo = None
    if body.catalogo_id:
        catalogo = db.query(CatalogoProcedimento).filter(
            CatalogoProcedimento.id == body.catalogo_id,
            CatalogoProcedimento.tenant_id == tenant_id,
        ).first()
        if not catalogo:
            raise HTTPException(status_code=404, detail="Procedimento de catálogo não encontrado")

    insumos = _normalizar_insumos(body.insumos or [])
    if not insumos and catalogo and isinstance(catalogo.insumos, list):
        insumos = _normalizar_insumos(catalogo.insumos)
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, insumos)

    p = ProcedimentoConsulta(
        tenant_id=tenant_id,
        consulta_id=body.consulta_id,
        catalogo_id=body.catalogo_id,
        user_id=user.id,
        nome=body.nome or (catalogo.nome if catalogo else "Procedimento"),
        descricao=body.descricao if body.descricao is not None else (catalogo.descricao if catalogo else None),
        valor=body.valor if body.valor is not None else (float(catalogo.valor_padrao) if catalogo and catalogo.valor_padrao is not None else None),
        realizado=body.realizado,
        observacoes=body.observacoes,
        insumos=insumos,
    )
    db.add(p)
    db.flush()
    if body.baixar_estoque:
        _aplicar_baixa_estoque_procedimento(db, p, tenant_id, user.id)
    _sincronizar_financeiro_procedimento(db, p, tenant_id, user.id)
    db.commit()
    db.refresh(p)
    return _serializar_procedimento(p, db, tenant_id)


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogo/procedimentos", response_model=List[CatalogoResponse])
def listar_catalogo_procedimentos(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    catalogos = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).order_by(CatalogoProcedimento.nome).all()
    return [_serializar_catalogo(catalogo, db, tenant_id) for catalogo in catalogos]


@router.post("/catalogo/procedimentos", response_model=CatalogoResponse, status_code=201)
def criar_catalogo_procedimento(
    body: CatalogoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = CatalogoProcedimento(
        tenant_id=tenant_id,
        nome=body.nome,
        descricao=body.descricao,
        categoria=body.categoria,
        valor_padrao=body.valor_padrao,
        duracao_minutos=body.duracao_minutos,
        requer_anestesia=body.requer_anestesia,
        observacoes=body.observacoes,
        insumos=_normalizar_insumos(body.insumos),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar_catalogo(p, db, tenant_id)


@router.patch("/catalogo/procedimentos/{catalogo_id}", response_model=CatalogoResponse)
def atualizar_catalogo_procedimento(
    catalogo_id: int,
    body: CatalogoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "insumos" in payload:
        catalogo.insumos = _normalizar_insumos(payload.pop("insumos"))
    for campo, valor in payload.items():
        setattr(catalogo, campo, valor)

    db.commit()
    db.refresh(catalogo)
    return _serializar_catalogo(catalogo, db, tenant_id)


@router.delete("/catalogo/procedimentos/{catalogo_id}", status_code=204)
def remover_catalogo_procedimento(
    catalogo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    catalogo.ativo = False
    db.commit()
    return Response(status_code=204)


@router.get("/catalogo/produtos-estoque")
def listar_produtos_estoque(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
        Produto.situacao == True,
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(or_(Produto.nome.ilike(termo), Produto.codigo.ilike(termo)))
    produtos = q.order_by(Produto.nome).limit(limit).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "unidade": produto.unidade,
            "estoque_atual": float(produto.estoque_atual or 0),
            "preco_custo": _round_money(produto.preco_custo),
        }
        for produto in produtos
    ]


@router.get("/pets/{pet_id}/alertas")
def listar_alertas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    return {
        "pet_id": pet.id,
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": _status_vacinal_pet(db, pet, tenant_id),
    }


@router.get("/pets/{pet_id}/carteirinha")
def obter_carteirinha_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).limit(10).all()
    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.pet_id == pet.id,
        ConsultaVet.tenant_id == tenant_id,
    ).order_by(ConsultaVet.created_at.desc()).limit(10).all()

    return {
        "pet": {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "peso": float(pet.peso) if pet.peso is not None else None,
            "foto_url": pet.foto_url,
            "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
            "alergias": getattr(pet, "alergias_lista", None) or ([pet.alergias] if pet.alergias else []),
            "restricoes_alimentares": getattr(pet, "restricoes_alimentares_lista", None) or [],
            "medicamentos_continuos": getattr(pet, "medicamentos_continuos_lista", None) or [],
            "condicoes_cronicas": getattr(pet, "condicoes_cronicas_lista", None) or [],
        },
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.date().isoformat() if consulta.created_at else None,
                "tipo": consulta.tipo,
                "status": consulta.status,
                "diagnostico": consulta.diagnostico,
                "observacoes_tutor": consulta.observacoes_tutor,
            }
            for consulta in consultas
        ],
        "exames": [
            {
                "id": exame.id,
                "nome": exame.nome,
                "tipo": exame.tipo,
                "status": exame.status,
                "data_resultado": exame.data_resultado.isoformat() if exame.data_resultado else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE MEDICAMENTOS
# ═══════════════════════════════════════════════════════════════

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
    m = MedicamentoCatalogo(tenant_id=tenant_id, **body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/catalogo/medicamentos/{medicamento_id}")
def atualizar_medicamento(
    medicamento_id: int,
    body: MedicamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(medicamento, campo, valor)

    db.commit()
    db.refresh(medicamento)
    return medicamento


@router.delete("/catalogo/medicamentos/{medicamento_id}", status_code=204)
def remover_medicamento(
    medicamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    medicamento.ativo = False
    db.commit()
    return Response(status_code=204)


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
    dose_inicial_semanas: Optional[int] = None,
    reforco_anual: bool = True,
    numero_doses_serie: int = 1,
    intervalo_doses_dias: Optional[int] = None,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProtocoloVacina(
        tenant_id=tenant_id,
        nome=nome,
        especie=especie,
        dose_inicial_semanas=dose_inicial_semanas,
        reforco_anual=reforco_anual,
        numero_doses_serie=numero_doses_serie,
        intervalo_doses_dias=intervalo_doses_dias,
        observacoes=observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/catalogo/protocolos-vacinas/{protocolo_id}")
def atualizar_protocolo_vacina(
    protocolo_id: int,
    body: ProtocoloVacinaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(protocolo, campo, valor)

    db.commit()
    db.refresh(protocolo)
    return protocolo


@router.delete("/catalogo/protocolos-vacinas/{protocolo_id}", status_code=204)
def remover_protocolo_vacina(
    protocolo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    protocolo.ativo = False
    db.commit()
    return Response(status_code=204)



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
