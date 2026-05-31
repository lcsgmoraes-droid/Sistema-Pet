from fastapi import APIRouter, HTTPException, Response, status

from app.services.product_image_storage import read_public_s3_product_image


router = APIRouter(prefix="/public/product-images", tags=["product-images-public"])


@router.get("/{storage_key:path}")
def serve_public_product_image(storage_key: str):
    try:
        image = read_public_s3_product_image(storage_key)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem nao encontrada.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Imagem temporariamente indisponivel.",
        ) from exc

    headers = {}
    if image.cache_control:
        headers["Cache-Control"] = image.cache_control
    if image.etag:
        headers["ETag"] = image.etag
    if image.last_modified:
        headers["Last-Modified"] = image.last_modified

    return Response(
        content=image.content,
        media_type=image.content_type,
        headers=headers,
    )
