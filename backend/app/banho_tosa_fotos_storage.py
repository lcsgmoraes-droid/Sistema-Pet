from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


UPLOAD_BASE_DIR = Path("uploads") / "banho_tosa"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1600
THUMBNAIL_SIZE = 420


async def salvar_foto_banho_tosa_upload(
    tenant_id,
    atendimento_id: int,
    arquivo: UploadFile,
    tipo: str,
) -> dict:
    if arquivo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Formato nao aceito. Use JPG, PNG ou WebP.")

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Maximo: 8 MB.")

    original_bytes, thumb_bytes = _preparar_variantes(conteudo)
    token = uuid4().hex
    base = UPLOAD_BASE_DIR / str(tenant_id) / str(atendimento_id)
    original_path = base / "originais" / f"{_slug_tipo(tipo)}-{token}.webp"
    thumb_path = base / "thumbs" / f"{_slug_tipo(tipo)}-{token}.webp"

    _gravar_bytes(original_path, original_bytes)
    _gravar_bytes(thumb_path, thumb_bytes)
    return {
        "url": _public_url(original_path),
        "thumbnail_url": _public_url(thumb_path),
    }


def thumbnail_url_banho_tosa(url: str | None) -> str | None:
    if not url:
        return None
    normalizada = str(url).strip()
    if "/originais/" in normalizada:
        return normalizada.replace("/originais/", "/thumbs/")
    return normalizada


def remover_arquivos_foto_banho_tosa(url: str | None) -> None:
    urls = [url, thumbnail_url_banho_tosa(url)]
    for item in {valor for valor in urls if valor}:
        caminho = _local_path_from_public_url(item)
        if not caminho:
            continue
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass


def _preparar_variantes(conteudo: bytes) -> tuple[bytes, bytes]:
    try:
        with Image.open(BytesIO(conteudo)) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

            original = image.copy()
            original.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            thumb = image.copy()
            thumb.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
            return _to_webp(original, quality=82), _to_webp(thumb, quality=72)
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Arquivo enviado nao e uma imagem valida.") from exc


def _to_webp(image: Image.Image, quality: int) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=6)
    return buffer.getvalue()


def _gravar_bytes(path: Path, conteudo: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(conteudo)


def _public_url(path: Path) -> str:
    return f"/{path.as_posix().lstrip('/')}"


def _local_path_from_public_url(url: str) -> Path | None:
    normalized = str(url).strip()
    if not normalized.startswith("/uploads/banho_tosa/"):
        return None
    caminho = Path(normalized.lstrip("/"))
    try:
        caminho_resolvido = caminho.resolve()
        base_resolvida = UPLOAD_BASE_DIR.resolve()
        if base_resolvida not in caminho_resolvido.parents:
            return None
    except OSError:
        return None
    return caminho


def _slug_tipo(tipo: str) -> str:
    valor = "".join(char if char.isalnum() else "-" for char in str(tipo or "foto").lower())
    return valor.strip("-") or "foto"
