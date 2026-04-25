"""Rotas de internacao veterinaria."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Pet
from .veterinario_core import _get_tenant, _normalizar_datetime_vet, _serializar_datetime_vet, _vet_now
from .veterinario_financeiro import _aplicar_baixa_estoque_itens, _as_float, _enriquecer_insumos_com_custos
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
from .veterinario_models import (
    ConsultaVet,
    EvolucaoInternacao,
    InternacaoConfig,
    InternacaoProcedimentoAgenda,
    InternacaoVet,
)
from .veterinario_schemas import (
    EvolucaoCreate,
    InternacaoConfigUpdate,
    InternacaoCreate,
    ProcedimentoAgendaInternacaoConcluir,
    ProcedimentoAgendaInternacaoCreate,
    ProcedimentoInternacaoCreate,
)

router = APIRouter()

# ═══════════════════════════════════════════════════════════════
# INTERNAÇÃO
# ═══════════════════════════════════════════════════════════════

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
            "consulta_id": i.consulta_id,
            "pet_nome": i.pet.nome if i.pet else None,
            "tutor_id": tutor.id if tutor else None,
            "tutor_nome": tutor.nome if tutor else None,
            "motivo": motivo_limpo,
            "box": box,
            "status": i.status,
            "data_entrada": _serializar_datetime_vet(i.data_entrada),
            "data_saida": _serializar_datetime_vet(i.data_saida),
            "observacoes_alta": i.observacoes,
        })
    return result


@router.get("/internacoes/config")
def obter_config_internacao(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para configuracao de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para configuracao de internacao")

    config = db.query(InternacaoConfig).filter(InternacaoConfig.tenant_id == tenant_id).first()
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=12,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }


@router.put("/internacoes/config")
def atualizar_config_internacao(
    body: InternacaoConfigUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para configuracao de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para configuracao de internacao")

    config = db.query(InternacaoConfig).filter(InternacaoConfig.tenant_id == tenant_id).first()
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=body.total_baias,
        )
        db.add(config)
    else:
        config.user_id = user_id
        config.total_baias = body.total_baias

    db.commit()
    db.refresh(config)
    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }


@router.get("/internacoes/procedimentos-agenda")
def listar_procedimentos_agenda_internacao(
    status: Optional[str] = Query("ativos"),
    internacao_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")

    status_normalizado = (status or "ativos").strip().lower()
    if status_normalizado in {"", "ativos", "ativo"}:
        status_filtro = ["agendado", "concluido"]
    elif status_normalizado in {"pendente", "pendentes", "agendado"}:
        status_filtro = ["agendado"]
    elif status_normalizado in {"feito", "feitos", "concluido", "concluidos"}:
        status_filtro = ["concluido"]
    elif status_normalizado in {"cancelado", "cancelados"}:
        status_filtro = ["cancelado"]
    else:
        raise HTTPException(status_code=422, detail="Status da agenda de internacao invalido")

    query = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
            InternacaoProcedimentoAgenda.status.in_(status_filtro),
        )
    )
    if internacao_id:
        query = query.filter(InternacaoProcedimentoAgenda.internacao_id == internacao_id)

    itens = query.order_by(InternacaoProcedimentoAgenda.horario_agendado.asc()).all()
    return [_serializar_procedimento_agenda_internacao(item) for item in itens]


@router.post("/internacoes/{internacao_id}/procedimentos-agenda", status_code=201)
def criar_procedimento_agenda_internacao(
    internacao_id: int,
    body: ProcedimentoAgendaInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    internacao = (
        db.query(InternacaoVet)
        .options(joinedload(InternacaoVet.pet))
        .filter(
            InternacaoVet.id == internacao_id,
            InternacaoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not internacao:
        raise HTTPException(404, "Internacao nao encontrada")
    if internacao.status != "internado":
        raise HTTPException(status_code=409, detail="Agenda de procedimento so pode ser criada para internacao ativa")

    medicamento = (body.medicamento or "").strip()
    if not medicamento:
        raise HTTPException(status_code=422, detail="Medicamento/procedimento e obrigatorio")

    horario_agendado = _normalizar_datetime_vet(body.horario_agendado)
    if not horario_agendado:
        raise HTTPException(status_code=422, detail="Horario agendado e obrigatorio")

    quantidade_prevista = _as_float(body.quantidade_prevista)
    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nao pode ser negativa")

    item = InternacaoProcedimentoAgenda(
        tenant_id=tenant_id,
        user_id=user_id,
        internacao_id=internacao.id,
        pet_id=internacao.pet_id,
        horario_agendado=horario_agendado,
        medicamento=medicamento,
        dose=(body.dose or "").strip() or None,
        via=(body.via or "").strip() or None,
        quantidade_prevista=quantidade_prevista,
        unidade_quantidade=(body.unidade_quantidade or "").strip() or None,
        lembrete_minutos=body.lembrete_min if body.lembrete_min is not None else 30,
        observacoes_agenda=(body.observacoes_agenda or "").strip() or None,
        status="agendado",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    item.internacao = internacao
    item.pet = internacao.pet
    return _serializar_procedimento_agenda_internacao(item)


@router.patch("/internacoes/procedimentos-agenda/{agenda_id}/concluir")
def concluir_procedimento_agenda_internacao(
    agenda_id: int,
    body: ProcedimentoAgendaInternacaoConcluir,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    item = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.id == agenda_id,
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    if item.status == "cancelado":
        raise HTTPException(status_code=409, detail="Procedimento cancelado nao pode ser concluido")

    executado_por = (body.executado_por or "").strip()
    if not executado_por:
        raise HTTPException(status_code=422, detail="Campo 'executado_por' e obrigatorio")

    horario_execucao = _normalizar_datetime_vet(body.horario_execucao)
    if not horario_execucao:
        raise HTTPException(status_code=422, detail="Campo 'horario_execucao' e obrigatorio")

    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nao pode ser negativa")
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(status_code=422, detail="Quantidade executada nao pode ser negativa")
    if quantidade_desperdicio < 0:
        raise HTTPException(status_code=422, detail="Quantidade de desperdicio nao pode ser negativa")
    if quantidade_executada is None and quantidade_prevista is not None:
        quantidade_executada = quantidade_prevista

    item.status = "concluido"
    item.executado_por = executado_por
    item.horario_execucao = horario_execucao
    item.observacao_execucao = (body.observacao_execucao or "").strip() or None
    item.quantidade_prevista = quantidade_prevista if quantidade_prevista is not None else item.quantidade_prevista
    item.quantidade_executada = quantidade_executada
    item.quantidade_desperdicio = quantidade_desperdicio
    item.unidade_quantidade = (body.unidade_quantidade or "").strip() or item.unidade_quantidade

    payload = _build_payload_procedimento_agenda_internacao(item)
    if item.procedimento_evolucao_id:
        evolucao = db.query(EvolucaoInternacao).filter(
            EvolucaoInternacao.id == item.procedimento_evolucao_id,
            EvolucaoInternacao.tenant_id == tenant_id,
        ).first()
        if evolucao:
            evolucao.user_id = user_id
            evolucao.data_hora = horario_execucao
            evolucao.observacoes = _build_procedimento_observacao(payload)
        else:
            item.procedimento_evolucao_id = None

    if not item.procedimento_evolucao_id:
        evolucao = EvolucaoInternacao(
            internacao_id=item.internacao_id,
            user_id=user_id,
            tenant_id=tenant_id,
            data_hora=horario_execucao,
            observacoes=_build_procedimento_observacao(payload),
        )
        db.add(evolucao)
        db.flush()
        item.procedimento_evolucao_id = evolucao.id

    db.commit()
    db.refresh(item)
    return _serializar_procedimento_agenda_internacao(item)


@router.delete("/internacoes/procedimentos-agenda/{agenda_id}", status_code=204)
def remover_procedimento_agenda_internacao(
    agenda_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")

    item = db.query(InternacaoProcedimentoAgenda).filter(
        InternacaoProcedimentoAgenda.id == agenda_id,
        InternacaoProcedimentoAgenda.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    if item.status == "concluido":
        raise HTTPException(
            status_code=409,
            detail="Procedimento concluido ja compoe o historico clinico e nao pode ser excluido",
        )

    item.status = "cancelado"
    db.commit()
    return Response(status_code=204)


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

    data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(i, evolucoes)

    return {
        "id": i.id,
        "pet_id": i.pet_id,
        "consulta_id": i.consulta_id,
        "pet_nome": i.pet.nome if i.pet else None,
        "tutor_id": i.pet.cliente.id if i.pet and i.pet.cliente else None,
        "tutor_nome": i.pet.cliente.nome if i.pet and i.pet.cliente else None,
        "motivo": motivo_limpo,
        "box": box,
        "status": i.status,
        "data_entrada": data_entrada_exibicao,
        "data_saida": _serializar_datetime_vet(i.data_saida),
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

        data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(internacao, registros)

        historico.append({
            "internacao_id": internacao.id,
            "status": internacao.status,
            "motivo": motivo_limpo,
            "box": box,
            "data_entrada": data_entrada_exibicao,
            "data_saida": _serializar_datetime_vet(internacao.data_saida),
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

    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")

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
        data_entrada=_normalizar_datetime_vet(body.data_entrada) or _vet_now(),
        status="internado",
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return {
        "id": i.id,
        "consulta_id": i.consulta_id,
        "status": i.status,
        "data_entrada": _serializar_datetime_vet(i.data_entrada),
    }


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

    horario_agendado = _normalizar_datetime_vet(body.horario_agendado)
    horario_execucao = _normalizar_datetime_vet(body.horario_execucao)
    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nÃ£o pode ser negativa")
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(status_code=422, detail="Quantidade executada nÃ£o pode ser negativa")
    if quantidade_desperdicio < 0:
        raise HTTPException(status_code=422, detail="Quantidade de desperdÃ­cio nÃ£o pode ser negativa")
    if status_procedimento == "concluido" and quantidade_executada is None and quantidade_prevista is not None:
        quantidade_executada = quantidade_prevista

    data_referencia = horario_agendado or horario_execucao or _vet_now()
    insumos = _enriquecer_insumos_com_custos(db, tenant_id_registro, body.insumos or []) if body.insumos else []

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_registro,
        data_hora=data_referencia,
        observacoes="",
    )
    db.add(ev)
    db.flush()

    estoque_baixado = False
    estoque_movimentacao_ids: list[int] = []
    if status_procedimento == "concluido" and insumos:
        insumos, estoque_movimentacao_ids = _aplicar_baixa_estoque_itens(
            db,
            tenant_id=tenant_id_registro,
            user_id=user_id,
            itens=insumos,
            motivo="procedimento_internacao",
            referencia_id=ev.id,
            referencia_tipo="procedimento_internacao",
            documento=str(internacao_id),
            observacao=f"Baixa automÃ¡tica da internaÃ§Ã£o #{internacao_id} - {body.medicamento}",
        )
        estoque_baixado = bool(estoque_movimentacao_ids)

    payload = {
        "status": status_procedimento,
        "tipo_registro": (body.tipo_registro or "procedimento").strip().lower() or "procedimento",
        "horario_agendado": horario_agendado.isoformat() if horario_agendado else None,
        "medicamento": body.medicamento,
        "dose": body.dose,
        "via": body.via,
        "quantidade_prevista": quantidade_prevista,
        "quantidade_executada": quantidade_executada,
        "quantidade_desperdicio": quantidade_desperdicio,
        "unidade_quantidade": (body.unidade_quantidade or "").strip() or None,
        "insumos": insumos,
        "estoque_baixado": estoque_baixado,
        "estoque_movimentacao_ids": estoque_movimentacao_ids,
        "observacoes_agenda": body.observacoes_agenda,
        "executado_por": (body.executado_por or "").strip() or None,
        "horario_execucao": horario_execucao.isoformat() if horario_execucao else None,
        "observacao_execucao": body.observacao_execucao,
    }

    ev.observacoes = _build_procedimento_observacao(payload)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "data_hora": _serializar_datetime_vet(ev.data_hora),
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
    i.data_saida = _vet_now()
    if observacoes:
        i.observacoes = observacoes
    db.commit()
    return {"ok": True, "status": "alta", "data_saida": _serializar_datetime_vet(i.data_saida)}
