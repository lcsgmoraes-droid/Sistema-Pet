"""Geracao de fotos promocionais preservando o produto real."""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException


UPLOAD_DIR = Path("uploads/ofertas")
ESTILOS = {"profissional", "natural", "fundo_limpo"}
logger = logging.getLogger(__name__)


def segmento_tenant_storage(tenant_id) -> str:
    """Converte o tenant em um nome sem separadores de caminho."""

    normalizado = UUID(str(tenant_id)).hex
    return os.path.basename(normalizado)


def diretorio_storage_tenant(tenant_id, *subdiretorios) -> Path:
    """Monta um destino e garante que ele permanece sob uploads/ofertas."""

    raiz = UPLOAD_DIR.resolve()
    segmentos = [segmento_tenant_storage(tenant_id)]
    for valor in subdiretorios:
        original = str(valor)
        seguro = os.path.basename(original)
        if seguro != original or seguro in {"", ".", ".."}:
            raise ValueError("Segmento de storage invalido.")
        segmentos.append(seguro)
    destino = raiz.joinpath(*segmentos).resolve()
    destino.relative_to(raiz)
    return destino


def resolver_chave_openai_tenant(db, tenant_id) -> str:
    try:
        from app.whatsapp.models import TenantWhatsAppConfig

        config = (
            db.query(TenantWhatsAppConfig)
            .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
            .first()
        )
        if config and config.openai_api_key:
            return config.openai_api_key.strip()
    except Exception:
        pass
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def _prompt(
    produto_nome: str,
    estilo: str,
    orientacao: str,
    prompt_usuario: str | None = None,
) -> str:
    direcao = {
        "natural": "um ambiente natural e acolhedor, coerente com a especie e o uso do produto",
        "fundo_limpo": "um estudio branco premium, com sombra suave e fundo limpo",
        "profissional": "um cenario publicitario premium para pet shop, sofisticado e comercial",
    }[estilo]
    prompt_base = (
        f"Crie uma fotografia publicitaria profissional do produto real '{produto_nome}' usando "
        f"a imagem enviada como referencia principal. Coloque-o em {direcao}. "
        "PRESERVE com alta fidelidade a embalagem, o logotipo, as cores, o formato, o rotulo e "
        "todas as caracteristicas visuais do produto. Nao troque a marca, nao invente uma nova "
        "embalagem e nao adicione preco, desconto, selo, slogan, texto promocional ou letras fora "
        "do que ja existe na embalagem. Deixe espaco visual seguro nas bordas para o sistema "
        f"compor a arte depois. Composicao {orientacao}, iluminacao de estudio, acabamento realista."
    )
    direcao_usuario = " ".join(str(prompt_usuario or "").split()).strip()
    if not direcao_usuario:
        return prompt_base
    return (
        f"{prompt_base} Direcao criativa adicional do usuario: {direcao_usuario}. "
        "A direcao adicional pode mudar o cenario e a composicao, mas nunca pode alterar "
        "a identidade, o rotulo, a marca, as cores ou o formato da embalagem real."
    )


def _codigo_erro_openai(exc: Exception) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        erro = body.get("error") if isinstance(body.get("error"), dict) else body
        return str(erro.get("code") or erro.get("type") or "").strip().lower()
    return str(getattr(exc, "code", "") or "").strip().lower()


def gerar_imagem_profissional(
    *,
    api_key: str,
    tenant_id,
    produto_id: int,
    produto_nome: str,
    file_bytes: bytes,
    content_type: str,
    estilo: str,
    orientacao: str,
    prompt_usuario: str | None = None,
) -> str:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        OpenAI,
        RateLimitError,
    )

    estilo = estilo if estilo in ESTILOS else "profissional"
    orientacao = orientacao if orientacao in {"quadrada", "vertical"} else "quadrada"
    size = "1024x1536" if orientacao == "vertical" else "1024x1024"
    try:
        resposta = OpenAI(api_key=api_key, timeout=120.0).images.edit(
            model="gpt-image-2",
            image=("produto.png", file_bytes, content_type),
            prompt=_prompt(produto_nome, estilo, orientacao, prompt_usuario),
            size=size,
            quality="high",
            output_format="png",
        )
        payload = resposta.data[0].b64_json if resposta.data else None
        if not payload:
            raise HTTPException(status_code=502, detail="A IA nao retornou uma imagem.")
        imagem = base64.b64decode(payload)
    except AuthenticationError as exc:
        logger.warning(
            "OpenAI recusou a credencial do tenant %s: authentication_error", tenant_id
        )
        raise HTTPException(
            status_code=401,
            detail="A chave da OpenAI desta empresa esta invalida. Revise em Configuracoes > Integracoes.",
        ) from exc
    except RateLimitError as exc:
        codigo = _codigo_erro_openai(exc)
        logger.warning(
            "OpenAI limitou o tenant %s: %s", tenant_id, codigo or "rate_limit"
        )
        if codigo in {"insufficient_quota", "billing_hard_limit_reached"}:
            raise HTTPException(
                status_code=429,
                detail="A conta da OpenAI esta sem creditos ou atingiu o limite de gastos.",
            ) from exc
        raise HTTPException(
            status_code=429,
            detail="A IA atingiu o limite temporario. Aguarde um pouco e tente novamente.",
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        logger.warning("Falha de conexao com OpenAI para o tenant %s", tenant_id)
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel falar com a IA agora. Tente novamente em instantes.",
        ) from exc
    except BadRequestError as exc:
        codigo = _codigo_erro_openai(exc)
        logger.warning(
            "OpenAI recusou a imagem do tenant %s: %s",
            tenant_id,
            codigo or "bad_request",
        )
        raise HTTPException(
            status_code=400,
            detail="A IA nao conseguiu processar esta foto. Tente outra imagem JPG, PNG ou WebP.",
        ) from exc
    except APIStatusError as exc:
        codigo = _codigo_erro_openai(exc)
        logger.warning(
            "OpenAI retornou status %s para o tenant %s: %s",
            getattr(exc, "status_code", None),
            tenant_id,
            codigo or "api_status_error",
        )
        if getattr(exc, "status_code", None) == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "O projeto da OpenAI nao tem acesso ao GPT Image. "
                    "Revise a verificacao da organizacao e as permissoes do projeto."
                ),
            ) from exc
        raise HTTPException(
            status_code=502, detail="A IA retornou um erro ao gerar a foto."
        ) from exc

    tenant_segmento = segmento_tenant_storage(tenant_id)
    destino = diretorio_storage_tenant(tenant_id, "ia")
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"produto-{produto_id}-{datetime.utcnow():%Y%m%d}-{uuid4().hex}.png"
    (destino / nome).write_bytes(imagem)
    return f"/uploads/ofertas/{tenant_segmento}/ia/{nome}"
