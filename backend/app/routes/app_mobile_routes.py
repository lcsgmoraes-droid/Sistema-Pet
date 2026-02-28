"""
Rotas exclusivas do App Mobile (clientes).

Prefixo : /app
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do e-commerce)
"""

import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, Pet, User
from app.produtos_models import Produto
from app.routes.ecommerce_auth import _get_current_ecommerce_user

router = APIRouter(prefix="/app", tags=["App Mobile"])

PET_UPLOAD_DIR = Path("uploads/pets")


# ─────────────────────────────────────────
# Schemas de RESPOSTA (response_model)
# Definem exatamente o que a API devolve ao app.
# Importante: evita vazar campos internos do banco.
# ─────────────────────────────────────────

class PetResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    castrado: bool
    data_nascimento: Optional[str]   # ISO 8601 string
    peso: Optional[float]
    porte: Optional[str]
    cor: Optional[str]
    alergias: Optional[str]
    observacoes: Optional[str]
    foto_url: Optional[str]

    class Config:
        from_attributes = True


class ProdutoBarcodeResponse(BaseModel):
    id: int
    nome: str
    preco: float
    preco_original: float
    foto_url: Optional[str]
    codigo_barras: Optional[str]
    unidade: str
    estoque: float


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _get_cliente_or_404(db: Session, user: User) -> Cliente:
    """Retorna o Cliente ligado a este usuário ecommerce ou lança 404."""
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == str(user.tenant_id),
            Cliente.user_id == user.id,
        )
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cliente não encontrado. Contate a loja.",
        )
    return cliente


def _gerar_codigo_pet(db: Session, user_id: int) -> str:
    """Gera código único para o pet (ex.: PET-3A7F1C2B)."""
    for _ in range(10):
        codigo = f"PET-{secrets.token_hex(4).upper()}"
        if not db.query(Pet).filter(Pet.codigo == codigo).first():
            return codigo
    raise RuntimeError("Não foi possível gerar código único para o pet.")


# ─────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────

class PetCreate(BaseModel):
    nome: str
    especie: str
    raca: Optional[str] = None
    sexo: Optional[str] = None
    castrado: bool = False
    data_nascimento: Optional[datetime] = None
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
    peso: Optional[float] = None
    porte: Optional[str] = None
    cor: Optional[str] = None
    alergias: Optional[str] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class PushTokenPayload(BaseModel):
    token: str
    plataforma: Optional[str] = None  # "android" | "ios"


# ─────────────────────────────────────────
# Serialização
# ─────────────────────────────────────────

def _serialize_pet(pet: Pet) -> dict:
    return {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "castrado": pet.castrado,
        "data_nascimento": pet.data_nascimento.isoformat() if pet.data_nascimento else None,
        "peso": pet.peso,
        "porte": pet.porte,
        "cor": pet.cor,
        "alergias": pet.alergias,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
    }


# ─────────────────────────────────────────
# PETS — CRUD
# ─────────────────────────────────────────

@router.get("/pets", response_model=list[PetResponse])
def listar_pets(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Lista todos os pets do cliente autenticado."""
    cliente = _get_cliente_or_404(db, current_user)
    pets = (
        db.query(Pet)
        .filter(
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
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
    cliente = _get_cliente_or_404(db, current_user)
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
    cliente = _get_cliente_or_404(db, current_user)
    pet = (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
        )
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado.")

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
    cliente = _get_cliente_or_404(db, current_user)
    pet = (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
        )
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado.")

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
    cliente = _get_cliente_or_404(db, current_user)
    pet = (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
        )
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado.")

    # Valida tipo de arquivo
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado. Use JPG, PNG ou WebP.")

    # Salva o arquivo em uploads/pets/{tenant_id}/
    ext = Path(file.filename or "foto.jpg").suffix or ".jpg"
    tenant_dir = PET_UPLOAD_DIR / str(current_user.tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pet-{pet_id}-{uuid.uuid4().hex[:8]}{ext}"
    dest = tenant_dir / filename

    content = await file.read()
    dest.write_bytes(content)

    # Remove foto anterior se era um upload local
    if pet.foto_url and pet.foto_url.startswith("/uploads/pets/"):
        old_path = Path(pet.foto_url.lstrip("/"))
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    pet.foto_url = f"/uploads/pets/{current_user.tenant_id}/{filename}"
    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


# ─────────────────────────────────────────
# PRODUTO POR CÓDIGO DE BARRAS
# ─────────────────────────────────────────

@router.get("/produto-barcode/{barcode}", response_model=ProdutoBarcodeResponse)
def buscar_produto_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Busca produto pelo código de barras (EAN/GTIN).
    Tenta `codigo_barras` e depois `gtin_ean`.
    Retorna apenas produtos ativos do tenant.
    """
    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == str(current_user.tenant_id),
            Produto.situacao == True,
            Produto.codigo_barras == barcode,
        )
        .first()
    )

    if not produto:
        produto = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == str(current_user.tenant_id),
                Produto.situacao == True,
                Produto.gtin_ean == barcode,
            )
            .first()
        )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado para este código de barras.",
        )

    preco = float(produto.preco_venda or 0)
    preco_original = float(produto.preco_promocional or produto.preco_venda or 0) if produto.preco_promocional else preco

    return {
        "id": produto.id,
        "nome": produto.nome,
        "preco": preco,
        "preco_original": preco_original,
        "foto_url": produto.imagem_principal,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "estoque": float(produto.estoque_atual or 0),
    }


# ─────────────────────────────────────────
# PUSH TOKEN
# ─────────────────────────────────────────

@router.post("/push-token")
def registrar_push_token(
    payload: PushTokenPayload,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Salva o token de notificação push (Expo Push Token ou FCM)
    no campo `push_token` do usuário.

    Requer migration para adicionar a coluna `push_token` a `users`.
    Execute: `alembic revision --autogenerate -m "add push_token to users"`
    seguido de `alembic upgrade head` em produção.
    """
    if not hasattr(current_user, "push_token"):
        # Coluna ainda não existe (migration pendente)
        return {"status": "ignored", "motivo": "Migration pendente: coluna push_token não existe."}

    current_user.push_token = payload.token
    db.commit()
    return {"status": "ok"}
