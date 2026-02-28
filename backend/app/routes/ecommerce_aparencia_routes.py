"""
Rotas de Aparência do E-commerce por lojista.
Permite upload de logo e até 3 banners rotativos para a loja virtual.
"""
import logging
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant

router = APIRouter(prefix="/ecommerce-aparencia", tags=["ecommerce-aparencia"])

UPLOAD_DIR = Path("uploads/ecommerce")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # O diretório é criado via volume montado; se já existir, não há problema.
    import logging
    logging.getLogger(__name__).warning(
        "Não foi possível criar %s (PermissionError). "
        "Certifique-se de que o diretório existe no host com chown 1000:1000.",
        UPLOAD_DIR,
    )

ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
MAX_SIZE = 5 * 1024 * 1024  # 5MB

TIPOS_VALIDOS = {"logo", "banner_1", "banner_2", "banner_3"}


# ─── Schemas ───────────────────────────────────────────────────────────────

class AparenciaResponse(BaseModel):
    logo_url: str | None = None
    banner_1_url: str | None = None
    banner_2_url: str | None = None
    banner_3_url: str | None = None


class AparenciaUrlUpdate(BaseModel):
    """Para quem prefere colar uma URL externa em vez de fazer upload."""
    logo_url: str | None = None
    banner_1_url: str | None = None
    banner_2_url: str | None = None
    banner_3_url: str | None = None


class SlugUpdate(BaseModel):
    slug: str | None = None


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
        try:
            old.unlink(missing_ok=True)
        except (PermissionError, OSError):
            # Arquivo com ownership errado (volume mount no Docker/Windows)
            # Tentamos corrigir a permissão e deletar novamente
            try:
                import os as _os
                _os.chmod(old, 0o666)
                old.unlink(missing_ok=True)
            except (PermissionError, OSError):
                pass  # Se ainda falhar, open("wb") vai sobrescrever o conteúdo

    filename = f"{tipo}.{ext}"
    file_path = tenant_dir / filename

    try:
        with file_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except PermissionError:
        raise HTTPException(
            status_code=500,
            detail="Erro de permissão no servidor ao salvar o arquivo. Execute: docker exec -u root petshop-dev-backend chown -R 999:999 /app/uploads"
        )

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


@router.put("/slug")
def atualizar_slug(
    body: SlugUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Atualiza o slug (endereço público) da loja.
    O slug define a URL: mlprohub.com.br/{slug}
    """
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    slug = (body.slug or "").strip().lower()
    if slug:
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            raise HTTPException(
                status_code=400,
                detail="Slug inválido. Use apenas letras minúsculas, números e hífens (ex: minha-loja).",
            )
        if len(slug) < 3:
            raise HTTPException(status_code=400, detail="Slug muito curto. Use pelo menos 3 caracteres.")
        if len(slug) > 80:
            raise HTTPException(status_code=400, detail="Slug muito longo. Máximo 80 caracteres.")
        # Verificar unicidade
        existing = db.query(Tenant).filter(
            Tenant.ecommerce_slug == slug,
            Tenant.id != tenant_id,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Este slug já está em uso. Escolha outro.")
        tenant.ecommerce_slug = slug
    else:
        tenant.ecommerce_slug = None

    db.commit()
    db.refresh(tenant)
    return {"ecommerce_slug": tenant.ecommerce_slug}


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
        try:
            file_path = Path(url_atual.lstrip("/"))
            file_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Não foi possível remover arquivo físico '%s': %s", url_atual, exc)

    try:
        setattr(tenant, campo, None)
        db.commit()
        db.refresh(tenant)
    except Exception as exc:
        db.rollback()
        logger.error("Erro ao remover campo '%s' do tenant %s: %s", campo, tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao remover imagem: {exc}")

    return AparenciaResponse(
        logo_url=tenant.logo_url,
        banner_1_url=tenant.banner_1_url,
        banner_2_url=tenant.banner_2_url,
        banner_3_url=tenant.banner_3_url,
    )
