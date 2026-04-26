from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_fotos_storage import (
    remover_arquivos_foto_banho_tosa,
    salvar_foto_banho_tosa_upload,
    thumbnail_url_banho_tosa,
)
from app.banho_tosa_models import BanhoTosaAtendimento, BanhoTosaFoto
from app.banho_tosa_schemas import (
    BanhoTosaFotoCreate,
    BanhoTosaFotoResponse,
    BanhoTosaOcorrenciaCreate,
)
from app.db import get_session
from app.models import Cliente
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/atendimentos/{atendimento_id}/ocorrencias")
def listar_ocorrencias_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    return atendimento.ocorrencias or []


@router.post("/atendimentos/{atendimento_id}/ocorrencias", status_code=201)
def registrar_ocorrencia_atendimento(
    atendimento_id: int,
    body: BanhoTosaOcorrenciaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    atendimento = _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    responsavel = _obter_responsavel(db, tenant_id, body.responsavel_id)
    ocorrencia = {
        "id": str(uuid4()),
        "tipo": body.tipo.strip().lower(),
        "gravidade": body.gravidade.strip().lower(),
        "descricao": body.descricao.strip(),
        "responsavel_id": body.responsavel_id,
        "responsavel_nome": responsavel.nome if responsavel else None,
        "created_by": user.id,
        "created_at": datetime.now().isoformat(),
    }
    atendimento.ocorrencias = [*(atendimento.ocorrencias or []), ocorrencia]
    db.commit()
    return ocorrencia


@router.delete("/atendimentos/{atendimento_id}/ocorrencias/{ocorrencia_id}", status_code=204)
def remover_ocorrencia_atendimento(
    atendimento_id: int,
    ocorrencia_id: str,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    originais = atendimento.ocorrencias or []
    novas = [item for item in originais if item.get("id") != ocorrencia_id]
    if len(novas) == len(originais):
        raise HTTPException(status_code=404, detail="Ocorrencia nao encontrada")
    atendimento.ocorrencias = novas
    db.commit()
    return Response(status_code=204)


@router.get("/atendimentos/{atendimento_id}/fotos", response_model=list[BanhoTosaFotoResponse])
def listar_fotos_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    fotos = db.query(BanhoTosaFoto).filter(
        BanhoTosaFoto.tenant_id == tenant_id,
        BanhoTosaFoto.atendimento_id == atendimento_id,
    ).order_by(BanhoTosaFoto.id.desc()).all()
    return [_serializar_foto(foto) for foto in fotos]


@router.post("/atendimentos/{atendimento_id}/fotos", response_model=BanhoTosaFotoResponse, status_code=201)
def registrar_foto_atendimento(
    atendimento_id: int,
    body: BanhoTosaFotoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    foto = BanhoTosaFoto(
        tenant_id=tenant_id,
        atendimento_id=atendimento_id,
        tipo=body.tipo.strip().lower(),
        url=body.url.strip(),
        descricao=body.descricao,
        created_by=user.id,
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)
    return _serializar_foto(foto)


@router.post("/atendimentos/{atendimento_id}/fotos/upload", response_model=BanhoTosaFotoResponse, status_code=201)
async def upload_foto_atendimento(
    atendimento_id: int,
    tipo: str = Form("entrada"),
    descricao: str | None = Form(None),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    arquivo_salvo = await salvar_foto_banho_tosa_upload(tenant_id, atendimento_id, arquivo, tipo)
    foto = BanhoTosaFoto(
        tenant_id=tenant_id,
        atendimento_id=atendimento_id,
        tipo=tipo.strip().lower(),
        url=arquivo_salvo["url"],
        descricao=descricao,
        created_by=user.id,
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)
    return _serializar_foto(foto)


@router.delete("/atendimentos/{atendimento_id}/fotos/{foto_id}", status_code=204)
def remover_foto_atendimento(
    atendimento_id: int,
    foto_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    foto = db.query(BanhoTosaFoto).filter(
        BanhoTosaFoto.id == foto_id,
        BanhoTosaFoto.tenant_id == tenant_id,
        BanhoTosaFoto.atendimento_id == atendimento_id,
    ).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")
    remover_arquivos_foto_banho_tosa(foto.url)
    db.delete(foto)
    db.commit()
    return Response(status_code=204)


def _serializar_foto(foto: BanhoTosaFoto) -> dict:
    return {
        "id": foto.id,
        "atendimento_id": foto.atendimento_id,
        "tipo": foto.tipo,
        "url": foto.url,
        "thumbnail_url": thumbnail_url_banho_tosa(foto.url),
        "descricao": foto.descricao,
        "created_by": foto.created_by,
    }


def _obter_atendimento_ou_404(db: Session, tenant_id, atendimento_id: int):
    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.id == atendimento_id,
        BanhoTosaAtendimento.tenant_id == tenant_id,
    ).first()
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")
    return atendimento


def _obter_responsavel(db: Session, tenant_id, responsavel_id: int | None):
    if not responsavel_id:
        return None
    responsavel = db.query(Cliente).filter(Cliente.id == responsavel_id, Cliente.tenant_id == tenant_id).first()
    if not responsavel:
        raise HTTPException(status_code=404, detail="Responsavel nao encontrado")
    return responsavel
