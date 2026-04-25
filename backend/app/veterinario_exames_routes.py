"""Rotas de exames veterinarios, arquivos e interpretacao IA."""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet
from .veterinario_agendamentos import _atualizar_status_agendamento
from .veterinario_clinico import _auditar_exame_pos_finalizacao, _bloquear_lancamento_em_consulta_finalizada
from .veterinario_core import _get_tenant
from .veterinario_exames_arquivos import _process_exam_file_with_ai, salvar_arquivo_exame_upload
from .veterinario_exames_ia import _gerar_interpretacao_exame
from .veterinario_internacao import _resolver_user_id_vet
from .veterinario_models import ConsultaVet, ExameVet
from .veterinario_schemas import ExameCreate, ExameResponse, ExameUpdate

router = APIRouter()


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
