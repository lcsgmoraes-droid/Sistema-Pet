"""Criacao, evolucao, procedimentos e alta de internacoes veterinarias."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Pet
from ..veterinario_core import (
    _get_tenant,
    _normalizar_datetime_local_brasilia,
    _serializar_datetime_vet,
    _vet_now,
)
from ..veterinario_financeiro import (
    _aplicar_baixa_estoque_itens,
    _as_float,
    _enriquecer_insumos_com_custos,
)
from ..veterinario_internacao import (
    _build_procedimento_observacao,
    _garantir_internacao_ativa,
    _normalizar_baia,
    _pack_motivo_baia,
    _split_motivo_baia,
)
from ..veterinario_models import ConsultaVet, EvolucaoInternacao, InternacaoVet
from ..veterinario_schemas import (
    EvolucaoCreate,
    InternacaoCreate,
    ProcedimentoInternacaoCreate,
)

router = APIRouter()


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

    pet_ok = (
        db.query(Pet)
        .filter(
            Pet.id == body.pet_id,
            Pet.tenant_id == tenant_id,
        )
        .first()
    )
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    if body.consulta_id:
        consulta_ok = (
            db.query(ConsultaVet)
            .filter(
                ConsultaVet.id == body.consulta_id,
                ConsultaVet.pet_id == body.pet_id,
                ConsultaVet.tenant_id == tenant_id,
            )
            .first()
        )
        if not consulta_ok:
            raise HTTPException(
                status_code=404,
                detail="Consulta vinculada nÃ£o encontrada para este pet",
            )

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
        data_entrada=_normalizar_datetime_local_brasilia(body.data_entrada)
        if body.data_entrada
        else _vet_now(),
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
    _garantir_internacao_ativa(i, "registrar evolução")

    tenant_id_evolucao = i.tenant_id or tenant_id
    if tenant_id_evolucao is None:
        raise HTTPException(
            status_code=422, detail="Tenant não identificado para registrar evolução"
        )

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(
            status_code=401, detail="Usuário inválido para registrar evolução"
        )

    dados = body.model_dump(exclude_unset=True)
    # Compatibilidade de nomes de campos vindos de versões antigas da tela.
    if dados.get("frequencia_cardiaca") is None and body.freq_cardiaca is not None:
        dados["frequencia_cardiaca"] = body.freq_cardiaca
    if (
        dados.get("frequencia_respiratoria") is None
        and body.freq_respiratoria is not None
    ):
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
    _garantir_internacao_ativa(i, "registrar procedimento")

    tenant_id_registro = i.tenant_id or tenant_id
    if tenant_id_registro is None:
        raise HTTPException(
            status_code=422,
            detail="Tenant não identificado para registrar procedimento",
        )

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(
            status_code=401, detail="Usuário inválido para registrar procedimento"
        )

    status_procedimento = (body.status or "concluido").strip().lower()
    if status_procedimento not in {"agendado", "concluido"}:
        raise HTTPException(
            status_code=422,
            detail="Status do procedimento inválido. Use 'agendado' ou 'concluido'.",
        )

    if status_procedimento == "concluido":
        if not (body.executado_por or "").strip():
            raise HTTPException(
                status_code=422,
                detail="Campo 'executado_por' é obrigatório para procedimento concluído",
            )
        if not body.horario_execucao:
            raise HTTPException(
                status_code=422,
                detail="Campo 'horario_execucao' é obrigatório para procedimento concluído",
            )

    horario_agendado = _normalizar_datetime_local_brasilia(body.horario_agendado)
    horario_execucao = _normalizar_datetime_local_brasilia(body.horario_execucao)
    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade prevista nÃ£o pode ser negativa"
        )
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade executada nÃ£o pode ser negativa"
        )
    if quantidade_desperdicio < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade de desperdÃ­cio nÃ£o pode ser negativa"
        )
    if (
        status_procedimento == "concluido"
        and quantidade_executada is None
        and quantidade_prevista is not None
    ):
        quantidade_executada = quantidade_prevista

    data_referencia = horario_agendado or horario_execucao or _vet_now()
    insumos = (
        _enriquecer_insumos_com_custos(db, tenant_id_registro, body.insumos or [])
        if body.insumos
        else []
    )

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
        "tipo_registro": (body.tipo_registro or "procedimento").strip().lower()
        or "procedimento",
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
    i = (
        db.query(InternacaoVet)
        .filter(
            InternacaoVet.id == internacao_id,
            InternacaoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not i:
        raise HTTPException(404, "Internação não encontrada")
    i.status = "alta"
    i.data_saida = _vet_now()
    if observacoes:
        i.observacoes = observacoes
    db.commit()
    return {
        "ok": True,
        "status": "alta",
        "data_saida": _serializar_datetime_vet(i.data_saida),
    }
