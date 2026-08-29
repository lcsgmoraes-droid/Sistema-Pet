"""API do Estudio de Ofertas e dos links publicos."""

from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant
from app.ofertas_estudio_models import OfertaPublicacao, OfertaPublicacaoToken
from app.ofertas_estudio_schemas import OfertaPublicacaoCreate
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission
from app.services.ofertas_estudio_ai import (
    ESTILOS,
    diretorio_storage_tenant,
    gerar_imagem_profissional,
    resolver_chave_openai_tenant,
    segmento_tenant_storage,
)
from app.services.ofertas_estudio_service import (
    buscar_produtos_publicaveis,
    montar_sugestao,
    serializar_produto_oferta,
    validar_snapshot_publicacao,
)
from app.services.validade_campanha_service import obter_campanha_validade_config
from app.tenancy.context import tenant_context


router = APIRouter(prefix="/ofertas", tags=["Estudio de Ofertas"])
public_router = APIRouter(prefix="/ofertas", tags=["Ofertas Publicas"])
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_PUBLICATION_BYTES = 60 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utc_aware(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def _status_publicacao(publicacao: OfertaPublicacao) -> str:
    agora = _agora_utc()
    if publicacao.desativada_em:
        return "desativada"
    if (
        _utc_aware(publicacao.expira_em) <= agora
        or _utc_aware(publicacao.fim_em) <= agora
    ):
        return "expirada"
    if _utc_aware(publicacao.inicio_em) > agora:
        return "agendada"
    return "ativa"


def _serializar_publicacao(
    publicacao: OfertaPublicacao, *, incluir_snapshot: bool = True
) -> dict:
    token = publicacao.indice_publico.token if publicacao.indice_publico else None
    payload = {
        "id": int(publicacao.id),
        "titulo": publicacao.titulo,
        "periodicidade": publicacao.periodicidade,
        "tipo_arte": publicacao.tipo_arte,
        "formato": publicacao.formato,
        "inicio_em": publicacao.inicio_em.isoformat(),
        "fim_em": publicacao.fim_em.isoformat(),
        "expira_em": publicacao.expira_em.isoformat(),
        "desativada_em": publicacao.desativada_em.isoformat()
        if publicacao.desativada_em
        else None,
        "status": _status_publicacao(publicacao),
        "token": token,
        "link_path": f"/oferta/{token}" if token else None,
        "imagens_urls": list(publicacao.imagens_urls or []),
        "created_at": publicacao.created_at.isoformat()
        if publicacao.created_at
        else None,
    }
    if incluir_snapshot:
        payload["produtos"] = list(publicacao.produtos_snapshot or [])
        payload["configuracao"] = dict(publicacao.configuracao or {})
    return payload


async def _ler_imagem(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Use imagens JPG, PNG ou WebP.")
    content = await file.read()
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=400, detail="A imagem deve ter no maximo 15 MB."
        )
    try:
        with Image.open(BytesIO(content)) as imagem:
            if imagem.width * imagem.height > MAX_IMAGE_PIXELS:
                raise ValueError("dimensoes excessivas")
            imagem.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(
            status_code=400, detail="O arquivo enviado nao e uma imagem valida."
        ) from exc
    return content


@router.get("/contexto")
@require_permission("vendas.criar")
def obter_contexto(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    return {
        "nome": tenant.name,
        "logo_url": tenant.logo_url,
        "cor_primaria": tenant.ecommerce_cor_primaria or "#0f766e",
        "cor_secundaria": tenant.ecommerce_cor_secundaria or "#0f172a",
    }


@router.get("/produtos")
@require_permission("vendas.criar")
def listar_produtos_oferta(
    busca: str = "",
    limite: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    campanha = obter_campanha_validade_config(db, tenant_id)
    produtos = buscar_produtos_publicaveis(db, tenant_id, busca=busca, limite=limite)
    return {
        "items": [
            serializar_produto_oferta(produto, campanha_validade=campanha)
            for produto in produtos
        ],
        "total": len(produtos),
    }


@router.get("/sugestoes")
@require_permission("vendas.criar")
def sugerir_produtos(
    estrategia: str = "mesclado",
    dias: int = Query(default=7, ge=1, le=365),
    limite: int = Query(default=8, ge=1, le=24),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return {
        "items": montar_sugestao(
            db,
            tenant_id,
            estrategia=estrategia,
            dias=dias,
            limite=limite,
        ),
        "estrategia": estrategia,
        "dias": dias,
    }


@router.post("/imagens/gerar")
@require_permission("vendas.criar")
async def gerar_imagem(
    produto_id: int = Form(...),
    estilo: str = Form(default="profissional"),
    orientacao: str = Form(default="quadrada"),
    prompt_usuario: str = Form(default="", max_length=800),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    produto = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.id == produto_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")
    if estilo not in ESTILOS:
        raise HTTPException(status_code=400, detail="Estilo de imagem invalido.")
    api_key = resolver_chave_openai_tenant(db, tenant_id)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "A conexao com a OpenAI ainda nao esta configurada. "
                "Configure a integracao da empresa ou a chave do servidor."
            ),
        )
    content = await _ler_imagem(file)
    url = await run_in_threadpool(
        gerar_imagem_profissional,
        api_key=api_key,
        tenant_id=tenant_id,
        produto_id=produto.id,
        produto_nome=produto.nome,
        file_bytes=content,
        content_type=file.content_type or "image/png",
        estilo=estilo,
        orientacao=orientacao,
        prompt_usuario=prompt_usuario,
    )
    return {"url": url, "estilo": estilo, "modelo": "gpt-image-2"}


@router.post("/publicacoes")
@require_permission("vendas.criar")
async def publicar_oferta(
    payload: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, tenant_id = user_and_tenant
    try:
        dados = OfertaPublicacaoCreate.model_validate_json(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc
    agora = _agora_utc()
    if dados.fim_em <= dados.inicio_em:
        raise HTTPException(
            status_code=400, detail="A data final deve ser posterior ao inicio."
        )
    if dados.fim_em <= agora:
        raise HTTPException(
            status_code=400, detail="A promocao deve terminar em uma data futura."
        )
    if dados.expira_em <= agora or dados.expira_em <= dados.inicio_em:
        raise HTTPException(
            status_code=400,
            detail="A validade do link deve ser posterior ao inicio da promocao.",
        )
    if not files or len(files) > 30:
        raise HTTPException(
            status_code=400, detail="Envie entre 1 e 30 paginas de arte."
        )

    snapshots = validar_snapshot_publicacao(
        db,
        tenant_id,
        dados.produtos,
        fim_em=dados.fim_em,
    )
    if dados.tipo_arte in {"individual", "produto"} and any(
        not str(item.get("imagem_url") or "").strip() for item in snapshots
    ):
        raise HTTPException(
            status_code=400,
            detail="Toda pagina individual precisa ter uma foto do produto.",
        )
    paginas = []
    total_bytes = 0
    for file in files:
        content = await _ler_imagem(file)
        total_bytes += len(content)
        if total_bytes > MAX_PUBLICATION_BYTES:
            raise HTTPException(
                status_code=400,
                detail="O conjunto de paginas deve ter no maximo 60 MB.",
            )
        paginas.append((file.content_type or "image/png", content))

    publicacao = OfertaPublicacao(
        tenant_id=tenant_id,
        titulo=dados.titulo,
        periodicidade=dados.periodicidade,
        tipo_arte=dados.tipo_arte,
        formato=dados.formato,
        inicio_em=dados.inicio_em,
        fim_em=dados.fim_em,
        expira_em=dados.expira_em,
        produtos_snapshot=snapshots,
        configuracao=dados.configuracao,
        imagens_urls=[],
        criado_por_id=usuario.id,
    )
    db.add(publicacao)
    db.flush()

    tenant_segmento = segmento_tenant_storage(tenant_id)
    destino = diretorio_storage_tenant(tenant_id, int(publicacao.id))
    try:
        destino.mkdir(parents=True, exist_ok=True)
        urls = []
        for indice, (content_type, content) in enumerate(paginas, start=1):
            extensao = {"image/jpeg": "jpg", "image/webp": "webp"}.get(
                content_type, "png"
            )
            nome = f"pagina-{indice:02d}-{uuid4().hex}.{extensao}"
            (destino / nome).write_bytes(content)
            urls.append(f"/uploads/ofertas/{tenant_segmento}/{publicacao.id}/{nome}")
        publicacao.imagens_urls = urls
        token = secrets.token_urlsafe(32)
        publicacao.indice_publico = OfertaPublicacaoToken(
            token=token,
            tenant_id=tenant_id,
            publicacao_id=publicacao.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        shutil.rmtree(destino, ignore_errors=True)
        raise
    db.refresh(publicacao)
    return _serializar_publicacao(publicacao)


@router.get("/publicacoes")
@require_permission("vendas.criar")
def listar_publicacoes(
    limite: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    rows = (
        db.query(OfertaPublicacao)
        .filter(OfertaPublicacao.tenant_id == tenant_id)
        .order_by(OfertaPublicacao.created_at.desc())
        .limit(limite)
        .all()
    )
    return {
        "items": [_serializar_publicacao(row, incluir_snapshot=False) for row in rows]
    }


@router.post("/publicacoes/{publicacao_id}/desativar")
@require_permission("vendas.criar")
def desativar_publicacao(
    publicacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    publicacao = (
        db.query(OfertaPublicacao)
        .filter(
            OfertaPublicacao.tenant_id == tenant_id,
            OfertaPublicacao.id == publicacao_id,
        )
        .first()
    )
    if not publicacao:
        raise HTTPException(status_code=404, detail="Publicacao nao encontrada.")
    publicacao.desativada_em = _agora_utc()
    db.commit()
    return _serializar_publicacao(publicacao, incluir_snapshot=False)


@public_router.get("/publicas/{token}")
def obter_publicacao_publica(token: str, db: Session = Depends(get_session)):
    token = str(token or "").strip()
    if len(token) < 24 or len(token) > 64:
        raise HTTPException(status_code=404, detail="Oferta nao encontrada.")
    indice = (
        db.query(OfertaPublicacaoToken)
        .filter(OfertaPublicacaoToken.token == token)
        .first()
    )
    if not indice:
        raise HTTPException(status_code=404, detail="Oferta nao encontrada.")
    with tenant_context(indice.tenant_id):
        publicacao = (
            db.query(OfertaPublicacao)
            .filter(
                OfertaPublicacao.tenant_id == indice.tenant_id,
                OfertaPublicacao.id == indice.publicacao_id,
            )
            .first()
        )
        tenant = db.query(Tenant).filter(Tenant.id == indice.tenant_id).first()
        if not publicacao or not tenant:
            raise HTTPException(status_code=404, detail="Oferta nao encontrada.")
        status = _status_publicacao(publicacao)
        ativa = status == "ativa"
        return {
            "titulo": publicacao.titulo,
            "empresa": tenant.name,
            "logo_url": tenant.logo_url,
            "cor_primaria": tenant.ecommerce_cor_primaria or "#0f766e",
            "status": status,
            "ativa": ativa,
            "motivo_encerramento": (
                "Esta promocao foi desativada pela loja."
                if status == "desativada"
                else "Esta promocao ja terminou."
                if status == "expirada"
                else "Esta promocao ainda nao comecou."
                if status == "agendada"
                else None
            ),
            "inicio_em": publicacao.inicio_em.isoformat(),
            "fim_em": publicacao.fim_em.isoformat(),
            "imagens_urls": list(publicacao.imagens_urls or []) if ativa else [],
            "produtos": list(publicacao.produtos_snapshot or []) if ativa else [],
        }
