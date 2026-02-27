"""
Rotas de Aparência do E-commerce por lojista.
Permite upload de logo e até 3 banners rotativos para a loja virtual.
"""
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant

router = APIRouter(prefix="/ecommerce-aparencia", tags=["ecommerce-aparencia"])

UPLOAD_DIR = Path("uploads/ecommerce")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
MAX_SIZE = 5 * 1024 * 1024  # 5MB

TIPOS_VALIDOS = {"logo", "banner_1", "banner_2", "banner_3"}


# ─── Schemas ───────────────────────────────────────────────────────────────

class AparenciaResponse(BaseModel):
    logo_url: str | None
    banner_1_url: str | None
    banner_2_url: str | None
    banner_3_url: str | None


class AparenciaUrlUpdate(BaseModel):
    """Para quem prefere colar uma URL externa em vez de fazer upload."""
    logo_url: str | None = None
    banner_1_url: str | None = None
    banner_2_url: str | None = None
    banner_3_url: str | None = None


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/tenant-context")
def tenant_context_logado(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Retorna o tenant-context completo do usuário logado.
    Usado pela Prévia da Loja quando acessada pelo painel (sem slug na URL).
    """
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    storefront_ref = tenant.ecommerce_slug or tenant.id
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "ecommerce_slug": tenant.ecommerce_slug,
        "storefront_path": f"/{storefront_ref}",
        "status": tenant.status,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
        "logo_url": tenant.logo_url,
        "banner_1_url": tenant.banner_1_url,
        "banner_2_url": tenant.banner_2_url,
        "banner_3_url": tenant.banner_3_url,
    }


@router.get("", response_model=AparenciaResponse)
def buscar_aparencia(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Retorna as configurações visuais atuais da loja."""
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return AparenciaResponse(
        logo_url=tenant.logo_url,
        banner_1_url=tenant.banner_1_url,
        banner_2_url=tenant.banner_2_url,
        banner_3_url=tenant.banner_3_url,
    )


@router.post("/upload/{tipo}", response_model=AparenciaResponse)
async def upload_imagem_aparencia(
    tipo: str,
    file: UploadFile = File(...),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Faz upload de logo ou banner para a loja.

    **tipo** deve ser: `logo`, `banner_1`, `banner_2` ou `banner_3`

    - Aceita JPG, PNG, WebP, GIF
    - Tamanho máximo: 5 MB
    - Salva em /uploads/ecommerce/{tenant_id}/{tipo}.ext
    """
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Use: {', '.join(sorted(TIPOS_VALIDOS))}",
        )

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Formato não aceito. Use JPG, PNG, WebP ou GIF.",
        )

    # Verificar tamanho
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo: 5 MB.")

    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Salvar arquivo — um arquivo por tipo (sobrescreve o anterior)
    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    tenant_dir = UPLOAD_DIR / str(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Remove imagem antiga do mesmo tipo se existir
    for old in tenant_dir.glob(f"{tipo}.*"):
        old.unlink(missing_ok=True)

    filename = f"{tipo}.{ext}"
    file_path = tenant_dir / filename

    with file_path.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    url = f"/uploads/ecommerce/{tenant_id}/{filename}"

    # Campo a atualizar no tenant
    campo = f"{tipo}_url"
    setattr(tenant, campo, url)
    db.commit()
    db.refresh(tenant)

    return AparenciaResponse(
        logo_url=tenant.logo_url,
        banner_1_url=tenant.banner_1_url,
        banner_2_url=tenant.banner_2_url,
        banner_3_url=tenant.banner_3_url,
    )


@router.put("", response_model=AparenciaResponse)
def atualizar_aparencia_por_url(
    dados: AparenciaUrlUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Atualiza logo e/ou banners usando URLs externas (sem upload de arquivo).
    Passe `null` para remover uma imagem.
    """
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(tenant, campo, valor)

    db.commit()
    db.refresh(tenant)

    return AparenciaResponse(
        logo_url=tenant.logo_url,
        banner_1_url=tenant.banner_1_url,
        banner_2_url=tenant.banner_2_url,
        banner_3_url=tenant.banner_3_url,
    )


@router.delete("/{tipo}", response_model=AparenciaResponse)
def remover_imagem_aparencia(
    tipo: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Remove logo ou banner específico."""
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Use: {', '.join(sorted(TIPOS_VALIDOS))}",
        )

    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Remove arquivo físico se for upload local
    campo = f"{tipo}_url"
    url_atual = getattr(tenant, campo, None)
    if url_atual and url_atual.startswith("/uploads/"):
        file_path = Path(url_atual.lstrip("/"))
        file_path.unlink(missing_ok=True)

    setattr(tenant, campo, None)
    db.commit()
    db.refresh(tenant)

    return AparenciaResponse(
        logo_url=tenant.logo_url,
        banner_1_url=tenant.banner_1_url,
        banner_2_url=tenant.banner_2_url,
        banner_3_url=tenant.banner_3_url,
    )
