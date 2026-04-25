"""Processamento de arquivos e IA para exames veterinarios."""

import base64
import mimetypes
import os
import re
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ModuleNotFoundError:  # pragma: no cover - dependencia existe no container de producao.
    pdfplumber = None

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from .veterinario_exames_ia import (
    _basic_lab_values_from_text,
    _gerar_interpretacao_exame,
    _merge_exam_result_json,
    _normalize_ai_alerts,
    _normalize_ai_result_json,
    _parse_llm_json_payload,
)
from .veterinario_financeiro import _as_float
from .whatsapp.models import TenantWhatsAppConfig


# Em producao o backend roda em /app/app/*.py, entao `parents[1]` aponta para
# /app, que e onde o volume de uploads esta montado. `parents[2]` subiria ate /
# e faria o upload tentar gravar em /uploads, gerando erro 500.
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "veterinario" / "exames"


def _resolve_vet_openai_config(db: Session, tenant_id) -> tuple[str, str]:
    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == str(tenant_id))
        .first()
    )
    api_key = ""
    model = "gpt-4o-mini"
    if config and config.openai_api_key:
        api_key = config.openai_api_key.strip()
        model = (config.model_preference or model).strip() or model
    else:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        model = (os.getenv("OPENAI_MODEL") or model).strip() or model
    return api_key, model


def _resolve_exame_file_path(exame, tenant_id) -> Path:
    if not exame.arquivo_url:
        raise HTTPException(400, "O exame ainda não possui arquivo anexado.")

    nome_arquivo = Path(exame.arquivo_url).name
    caminho = UPLOADS_DIR / str(tenant_id) / nome_arquivo
    if caminho.exists():
        return caminho

    partes = Path(str(exame.arquivo_url).lstrip("/")).parts
    uploads_idx = None
    for idx, parte in enumerate(partes):
        if parte == "uploads":
            uploads_idx = idx
            break
    if uploads_idx is not None:
        caminho_alternativo = Path(__file__).resolve().parents[1].joinpath(*partes[uploads_idx:])
        if caminho_alternativo.exists():
            return caminho_alternativo

    raise HTTPException(404, "Arquivo do exame não foi encontrado no servidor.")


def _extract_text_from_pdf(pdf_path: Path, max_pages: int = 8, max_chars: int = 18000) -> str:
    if pdfplumber is None:
        raise HTTPException(500, "Leitor de PDF indisponível no backend.")

    trechos: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages[:max_pages]:
            texto = (page.extract_text() or "").strip()
            if texto:
                trechos.append(texto)
            if sum(len(parte) for parte in trechos) >= max_chars:
                break
    return "\n\n".join(trechos)[:max_chars].strip()


def _build_local_image_data_url(path_arquivo: Path) -> str:
    mime = mimetypes.guess_type(str(path_arquivo))[0] or "image/png"
    conteudo = path_arquivo.read_bytes()
    encoded = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _call_openai_exam_file_analysis(
    *,
    api_key: str,
    model: str,
    exame,
    texto_extraido: str,
    imagem_data_url: Optional[str] = None,
) -> dict:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        OpenAI,
        RateLimitError,
    )

    client = OpenAI(api_key=api_key, timeout=45.0)
    system_prompt = (
        "Você é um assistente veterinário de apoio à triagem de exames.\n"
        "Sua tarefa é ler o conteúdo do exame e responder SOMENTE em JSON válido.\n"
        "Nunca invente valores. Se não conseguir ler algo, assuma incerteza e registre em limitacoes.\n"
        "Para exames de imagem, descreva achados prováveis, mas deixe claro que não substitui laudo do especialista.\n"
        "Formato JSON obrigatório:\n"
        "{\n"
        '  "resultado_texto": "texto resumido e fiel ao exame",\n'
        '  "resultado_json": {"campo": valor},\n'
        '  "resumo": "resumo curto da triagem",\n'
        '  "conclusao": "conclusão curta",\n'
        '  "alertas": [{"campo":"...","status":"alto|baixo|atencao","mensagem":"..."}],\n'
        '  "confianca": 0.0,\n'
        '  "achados_imagem": ["..."],\n'
        '  "conduta_sugerida": ["..."],\n'
        '  "limitacoes": ["..."]\n'
        "}"
    )

    prompt_texto = (
        f"Tipo do exame: {exame.tipo}\n"
        f"Nome do exame: {exame.nome}\n"
        f"Laboratório: {exame.laboratorio or 'não informado'}\n"
        f"Status atual: {exame.status}\n"
    )
    if texto_extraido:
        prompt_texto += f"\nTexto já extraído do arquivo:\n{texto_extraido[:16000]}"
    else:
        prompt_texto += "\nNão há texto previamente extraído. Analise a imagem anexada."

    try:
        if imagem_data_url:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_texto},
                            {"type": "image_url", "image_url": {"url": imagem_data_url}},
                        ],
                    },
                ],
                temperature=0.1,
                max_tokens=1400,
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_texto},
                ],
                temperature=0.1,
                max_tokens=1400,
            )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="A chave da OpenAI configurada para exames veterinarios esta invalida. Revise a chave em Configuracoes > Integracoes.",
        ) from exc
    except RateLimitError as exc:
        mensagem = str(exc).lower()
        if "insufficient_quota" in mensagem or "quota" in mensagem or "billing" in mensagem:
            raise HTTPException(
                status_code=429,
                detail="A IA veterinaria da OpenAI esta sem creditos ou sem faturamento ativo. Adicione creditos em platform.openai.com/account/billing e tente novamente.",
            ) from exc
        raise HTTPException(
            status_code=429,
            detail="A OpenAI atingiu o limite temporario de uso para este exame. Aguarde um pouco e tente novamente.",
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel falar com a OpenAI agora. Verifique a conexao e tente novamente em instantes.",
        ) from exc
    except BadRequestError as exc:
        raise HTTPException(
            status_code=400,
            detail="A OpenAI recusou este processamento do exame. Verifique o arquivo anexado e tente novamente.",
        ) from exc
    except APIStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="A OpenAI retornou um erro ao processar este exame. Tente novamente em instantes.",
        ) from exc

    content = response.choices[0].message.content or ""
    return _parse_llm_json_payload(content)


def _persist_exam_file_ai_analysis(
    exame,
    *,
    texto_extraido: str,
    resultado_json: dict,
    resumo: Optional[str],
    conclusao: Optional[str],
    alertas: list[dict],
    confianca: Optional[float],
    payload_extra: Optional[dict] = None,
) -> None:
    if texto_extraido and not (exame.resultado_texto or "").strip():
        exame.resultado_texto = texto_extraido
    elif texto_extraido and (exame.resultado_texto or "").strip() and texto_extraido not in (exame.resultado_texto or ""):
        exame.resultado_texto = f"{(exame.resultado_texto or '').strip()}\n\n--- Texto extraído do arquivo ---\n{texto_extraido}".strip()

    exame.resultado_json = _merge_exam_result_json(exame, resultado_json)

    analise_fallback = _gerar_interpretacao_exame(exame)
    exame.interpretacao_ia = (conclusao or "").strip() or analise_fallback["conclusao"]
    exame.interpretacao_ia_resumo = (resumo or "").strip() or analise_fallback["resumo"]
    exame.interpretacao_ia_confianca = round(float(confianca), 2) if confianca is not None else analise_fallback["confianca"]
    exame.interpretacao_ia_alertas = alertas or analise_fallback["alertas"]

    payload_base = {
        "resultado_json": exame.resultado_json if isinstance(exame.resultado_json, dict) else {},
        "tem_resultado_texto": bool(exame.resultado_texto),
        "analisado_em": datetime.utcnow().isoformat(),
        "fonte_arquivo": True,
    }
    if isinstance(payload_extra, dict):
        payload_base.update(payload_extra)
    exame.interpretacao_ia_payload = payload_base
    if not exame.data_resultado:
        exame.data_resultado = date.today()
    if exame.status in {"solicitado", "coletado", "aguardando", "disponivel"}:
        exame.status = "interpretado"


def _process_exam_file_with_ai(
    db: Session,
    *,
    tenant_id,
    exame,
) -> object:
    caminho_arquivo = _resolve_exame_file_path(exame, tenant_id)
    extensao = caminho_arquivo.suffix.lower()
    texto_extraido = ""
    imagem_data_url = None
    payload_extra = {
        "arquivo_nome": exame.arquivo_nome,
        "arquivo_url": exame.arquivo_url,
        "tipo_arquivo": extensao,
    }
    falha_ia_detail = ""

    if extensao == ".pdf":
        texto_extraido = _extract_text_from_pdf(caminho_arquivo)
        payload_extra["fonte_extracao"] = "pdf_texto"
    elif extensao in {".png", ".jpg", ".jpeg", ".webp"}:
        imagem_data_url = _build_local_image_data_url(caminho_arquivo)
        payload_extra["fonte_extracao"] = "imagem"
    else:
        raise HTTPException(400, "Formato inválido para análise. Envie PDF ou imagem.")

    api_key, model = _resolve_vet_openai_config(db, tenant_id)
    resposta_ai = {}
    if api_key and (imagem_data_url or texto_extraido):
        try:
            resposta_ai = _call_openai_exam_file_analysis(
                api_key=api_key,
                model=model,
                exame=exame,
                texto_extraido=texto_extraido,
                imagem_data_url=imagem_data_url,
            )
            payload_extra["modelo_ia"] = model
        except HTTPException as exc:
            if not texto_extraido:
                raise
            falha_ia_detail = str(exc.detail or "").strip()
            payload_extra["modelo_ia"] = model
            payload_extra["ia_status_code"] = exc.status_code
            payload_extra["ia_indisponivel"] = True
            payload_extra["ia_erro"] = falha_ia_detail

    if not texto_extraido:
        texto_extraido = str(resposta_ai.get("resultado_texto") or "").strip()

    resultado_json = _normalize_ai_result_json(resposta_ai.get("resultado_json"))
    if not resultado_json and texto_extraido:
        resultado_json = _basic_lab_values_from_text(texto_extraido)

    alertas = _normalize_ai_alerts(resposta_ai.get("alertas"))
    resumo = str(resposta_ai.get("resumo") or "").strip()
    conclusao = str(resposta_ai.get("conclusao") or "").strip()
    confianca = _as_float(resposta_ai.get("confianca"))
    achados_imagem = resposta_ai.get("achados_imagem") if isinstance(resposta_ai.get("achados_imagem"), list) else []
    conduta_sugerida = resposta_ai.get("conduta_sugerida") if isinstance(resposta_ai.get("conduta_sugerida"), list) else []
    limitacoes = resposta_ai.get("limitacoes") if isinstance(resposta_ai.get("limitacoes"), list) else []
    if falha_ia_detail:
        limitacoes = [*limitacoes, falha_ia_detail]

    if not texto_extraido and not resultado_json and not resposta_ai:
        raise HTTPException(
            400,
            "Não foi possível extrair conteúdo útil do arquivo. Em PDFs escaneados, tente anexar como imagem ou informe o laudo em texto.",
        )

    payload_extra.update({
        "achados_imagem": achados_imagem,
        "conduta_sugerida": conduta_sugerida,
        "limitacoes": limitacoes,
    })

    _persist_exam_file_ai_analysis(
        exame,
        texto_extraido=texto_extraido,
        resultado_json=resultado_json,
        resumo=resumo,
        conclusao=conclusao,
        alertas=alertas,
        confianca=confianca,
        payload_extra=payload_extra,
    )
    return exame


def salvar_arquivo_exame_upload(exame, tenant_id, arquivo: UploadFile) -> str:
    nome_original = (arquivo.filename or "resultado").strip()
    extensao = Path(nome_original).suffix.lower()
    extensoes_permitidas = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    if extensao not in extensoes_permitidas:
        raise HTTPException(400, "Formato inválido. Envie PDF ou imagem.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")

    pasta_tenant = UPLOADS_DIR / str(tenant_id)
    pasta_tenant.mkdir(parents=True, exist_ok=True)

    nome_seguro = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(nome_original).stem).strip("_") or "resultado"
    nome_arquivo = f"exame_{exame.id}_{secrets.token_hex(4)}_{nome_seguro}{extensao}"
    caminho_arquivo = pasta_tenant / nome_arquivo
    caminho_arquivo.write_bytes(conteudo)

    exame.arquivo_nome = nome_original
    exame.arquivo_url = f"/uploads/veterinario/exames/{tenant_id}/{nome_arquivo}"
    if not exame.data_resultado:
        exame.data_resultado = date.today()
    if exame.status == "solicitado":
        exame.status = "disponivel"
    return nome_original
