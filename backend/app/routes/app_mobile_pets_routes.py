import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Pet, User
from app.routes.ecommerce_auth import _get_current_ecommerce_user
from app.veterinario_models import ConsultaVet, ExameVet

router = APIRouter()

PET_UPLOAD_DIR = Path("uploads/pets")
PET_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
PET_SAFE_PATH_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


class PetResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    castrado: bool
    data_nascimento: Optional[str]  # ISO 8601 string
    idade_aproximada: Optional[int] = None
    peso: Optional[float]
    porte: Optional[str]
    cor: Optional[str]
    alergias: Optional[str]
    alergias_lista: list[str] = []
    observacoes: Optional[str]
    restricoes_alimentares_lista: list[str] = []
    condicoes_cronicas_lista: list[str] = []
    medicamentos_continuos_lista: list[str] = []
    tipo_sanguineo: Optional[str] = None
    foto_url: Optional[str]

    class Config:
        from_attributes = True


class PetCreate(BaseModel):
    nome: str
    especie: str
    raca: Optional[str] = None
    sexo: Optional[str] = None
    castrado: bool = False
    data_nascimento: Optional[datetime] = None
    idade_aproximada: Optional[int] = None
    peso: Optional[float] = None
    porte: Optional[str] = None
    cor: Optional[str] = None
    alergias: Optional[str] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class PetUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    raca: Optional[str] = None
    sexo: Optional[str] = None
    castrado: Optional[bool] = None
    data_nascimento: Optional[datetime] = None
    idade_aproximada: Optional[int] = None
    peso: Optional[float] = None
    porte: Optional[str] = None
    cor: Optional[str] = None
    alergias: Optional[str] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class PetCarteirinhaResponse(BaseModel):
    pet: dict
    alertas: list[dict]
    status_vacinal: dict
    consultas: list[dict]
    exames: list[dict]


def _mobile_routes():
    from app.routes import app_mobile_routes

    return app_mobile_routes


def _gerar_codigo_pet(db: Session, user_id: int) -> str:
    """Gera código único para o pet (ex.: PET-3A7F1C2B)."""
    for _ in range(10):
        codigo = f"PET-{secrets.token_hex(4).upper()}"
        if not db.query(Pet).filter(Pet.codigo == codigo).first():
            return codigo
    raise RuntimeError("Não foi possível gerar código único para o pet.")


def _serialize_pet(pet: Pet) -> dict:
    return {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "castrado": pet.castrado,
        "data_nascimento": pet.data_nascimento.isoformat()
        if pet.data_nascimento
        else None,
        "idade_aproximada": pet.idade_aproximada,
        "peso": pet.peso,
        "porte": pet.porte,
        "cor": pet.cor,
        "alergias": pet.alergias,
        "alergias_lista": getattr(pet, "alergias_lista", None) or [],
        "observacoes": pet.observacoes,
        "restricoes_alimentares_lista": getattr(
            pet, "restricoes_alimentares_lista", None
        )
        or [],
        "condicoes_cronicas_lista": getattr(pet, "condicoes_cronicas_lista", None)
        or [],
        "medicamentos_continuos_lista": getattr(
            pet, "medicamentos_continuos_lista", None
        )
        or [],
        "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
        "foto_url": pet.foto_url,
    }


def _get_pet_owned_or_404(db: Session, pet_id: int, current_user: User) -> Pet:
    cliente = _mobile_routes()._get_cliente_or_404(db, current_user)
    pet = (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo.is_(True),
        )
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado.")
    return pet


def _pet_upload_destination(tenant_id, content_type: str | None) -> tuple[Path, str]:
    ext = PET_IMAGE_EXTENSIONS.get(str(content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo nao suportado. Use JPG, PNG ou WebP.",
        )

    tenant_segment = str(tenant_id)
    if not tenant_segment or any(
        char not in PET_SAFE_PATH_CHARS for char in tenant_segment
    ):
        raise HTTPException(status_code=400, detail="Tenant de upload invalido.")

    tenant_dir = PET_UPLOAD_DIR / tenant_segment
    filename = f"pet-{uuid.uuid4().hex}{ext}"
    dest = tenant_dir / filename
    try:
        resolved_base = PET_UPLOAD_DIR.resolve()
        resolved_dir = tenant_dir.resolve()
        if resolved_base not in resolved_dir.parents:
            raise HTTPException(status_code=400, detail="Caminho de upload invalido.")

        tenant_dir.mkdir(parents=True, exist_ok=True)
        resolved_dest = dest.resolve()
        if resolved_dest.parent != resolved_dir:
            raise HTTPException(status_code=400, detail="Caminho de upload invalido.")
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail="Falha ao preparar upload."
        ) from exc
    return dest, filename


def _local_pet_upload_path_from_public_url(url: str | None) -> Path | None:
    normalized = str(url or "").strip()
    if not normalized.startswith("/uploads/pets/"):
        return None
    path = Path(normalized.lstrip("/"))
    try:
        resolved_path = path.resolve()
        resolved_base = PET_UPLOAD_DIR.resolve()
        if resolved_base not in resolved_path.parents:
            return None
    except OSError:
        return None
    return path


@router.get("/pets", response_model=list[PetResponse])
def listar_pets(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Lista todos os pets do cliente autenticado."""
    cliente = _mobile_routes()._get_cliente_or_404(db, current_user)
    pets = (
        db.query(Pet)
        .filter(
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo.is_(True),
        )
        .order_by(Pet.nome)
        .all()
    )
    return [_serialize_pet(p) for p in pets]


@router.post("/pets", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def criar_pet(
    payload: PetCreate,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Cadastra um novo pet para o cliente autenticado."""
    cliente = _mobile_routes()._get_cliente_or_404(db, current_user)
    codigo = _gerar_codigo_pet(db, current_user.id)

    pet = Pet(
        tenant_id=str(current_user.tenant_id),
        user_id=current_user.id,
        cliente_id=cliente.id,
        codigo=codigo,
        nome=payload.nome,
        especie=payload.especie,
        raca=payload.raca,
        sexo=payload.sexo,
        castrado=payload.castrado,
        data_nascimento=payload.data_nascimento,
        idade_aproximada=payload.idade_aproximada,
        peso=payload.peso,
        porte=payload.porte,
        cor=payload.cor,
        alergias=payload.alergias,
        observacoes=payload.observacoes,
        foto_url=payload.foto_url,
        ativo=True,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.put("/pets/{pet_id}", response_model=PetResponse)
def atualizar_pet(
    pet_id: int,
    payload: PetUpdate,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Atualiza dados de um pet do cliente autenticado."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pet, field, value)

    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_pet(
    pet_id: int,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Remove (soft-delete) um pet do cliente autenticado."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    pet.ativo = False
    db.commit()


@router.post("/pets/{pet_id}/foto", response_model=PetResponse)
async def upload_foto_pet(
    pet_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Faz upload da foto do pet e salva em /uploads/pets/{tenant_id}/."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    dest, filename = _pet_upload_destination(current_user.tenant_id, file.content_type)

    content = await file.read()
    dest.write_bytes(content)

    # Remove foto anterior se era um upload local
    old_path = _local_pet_upload_path_from_public_url(pet.foto_url)
    if old_path and old_path.exists():
        old_path.unlink(missing_ok=True)

    pet.foto_url = f"/uploads/pets/{current_user.tenant_id}/{filename}"
    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.get("/pets/{pet_id}/carteirinha", response_model=PetCarteirinhaResponse)
def obter_carteirinha_pet_app(
    pet_id: int,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    pet = _get_pet_owned_or_404(db, pet_id, current_user)
    from app.veterinario_clinico import _montar_alertas_pet, _status_vacinal_pet

    tenant_id = str(current_user.tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    consultas = (
        db.query(ConsultaVet)
        .filter(
            ConsultaVet.pet_id == pet.id,
            ConsultaVet.tenant_id == tenant_id,
        )
        .order_by(ConsultaVet.created_at.desc())
        .limit(10)
        .all()
    )
    exames = (
        db.query(ExameVet)
        .filter(
            ExameVet.pet_id == pet.id,
            ExameVet.tenant_id == tenant_id,
        )
        .order_by(ExameVet.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "pet": _serialize_pet(pet),
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.isoformat()
                if consulta.created_at
                else None,
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
                "data_resultado": exame.data_resultado.isoformat()
                if exame.data_resultado
                else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }
