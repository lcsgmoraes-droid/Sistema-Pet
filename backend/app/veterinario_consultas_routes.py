"""Rotas de consultas, prontuario e prescricoes veterinarias."""
import hashlib
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet
from .veterinario_agendamentos import _sincronizar_marcos_agendamento
from .veterinario_clinico import _bloquear_lancamento_em_consulta_finalizada, _consulta_or_404
from .veterinario_core import (
    _date_para_datetime_vet,
    _get_tenant,
    _normalizar_datetime_vet,
    _serializar_datetime_vet,
    _vet_now,
)
from .veterinario_financeiro import _normalizar_insumos, _round_money
from .veterinario_internacao import _split_motivo_baia
from .veterinario_models import (
    AgendamentoVet,
    ConsultaVet,
    ExameVet,
    InternacaoVet,
    ItemPrescricao,
    PesoRegistro,
    PrescricaoVet,
    ProcedimentoConsulta,
    VacinaRegistro,
)
from .veterinario_schemas import ConsultaCreate, ConsultaResponse, ConsultaUpdate, PrescricaoCreate, PrescricaoResponse
from .veterinario_serializers import _consulta_to_dict, _hash_prontuario_consulta, _prescricao_to_dict

router = APIRouter()


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
