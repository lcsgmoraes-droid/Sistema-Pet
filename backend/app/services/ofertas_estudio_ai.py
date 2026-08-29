"""Geracao de fotos promocionais preservando o produto real."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


UPLOAD_DIR = Path("uploads/ofertas")
ESTILOS = {"profissional", "natural", "fundo_limpo"}


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
        return ""
    return ""


def _prompt(produto_nome: str, estilo: str, orientacao: str) -> str:
    direcao = {
        "natural": "um ambiente natural e acolhedor, coerente com a especie e o uso do produto",
        "fundo_limpo": "um estudio branco premium, com sombra suave e fundo limpo",
        "profissional": "um cenario publicitario premium para pet shop, sofisticado e comercial",
    }[estilo]
    return (
        f"Crie uma fotografia publicitaria profissional do produto real '{produto_nome}' usando "
        f"a imagem enviada como referencia principal. Coloque-o em {direcao}. "
        "PRESERVE com alta fidelidade a embalagem, o logotipo, as cores, o formato, o rotulo e "
        "todas as caracteristicas visuais do produto. Nao troque a marca, nao invente uma nova "
        "embalagem e nao adicione preco, desconto, selo, slogan, texto promocional ou letras fora "
        "do que ja existe na embalagem. Deixe espaco visual seguro nas bordas para o sistema "
        f"compor a arte depois. Composicao {orientacao}, iluminacao de estudio, acabamento realista."
    )


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
            prompt=_prompt(produto_nome, estilo, orientacao),
            size=size,
            quality="high",
            input_fidelity="high",
            output_format="png",
            response_format="b64_json",
        )
        payload = resposta.data[0].b64_json if resposta.data else None
        if not payload:
            raise HTTPException(status_code=502, detail="A IA nao retornou uma imagem.")
        imagem = base64.b64decode(payload)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="A chave da OpenAI desta empresa esta invalida. Revise em Configuracoes > Integracoes.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="A IA atingiu o limite temporario ou esta sem creditos. Tente novamente depois.",
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel falar com a IA agora. Tente novamente em instantes.",
        ) from exc
    except BadRequestError as exc:
        raise HTTPException(
            status_code=400, detail="A IA nao conseguiu processar esta foto."
        ) from exc
    except APIStatusError as exc:
        raise HTTPException(
            status_code=502, detail="A IA retornou um erro ao gerar a foto."
        ) from exc

    destino = UPLOAD_DIR / str(tenant_id) / "ia"
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"produto-{produto_id}-{datetime.utcnow():%Y%m%d}-{uuid4().hex}.png"
    (destino / nome).write_bytes(imagem)
    return f"/uploads/ofertas/{tenant_id}/ia/{nome}"
