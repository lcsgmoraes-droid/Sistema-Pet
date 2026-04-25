"""
Rotas do módulo veterinário.
Cobre: agendamentos, consultas, vacinas, exames, prescrições,
internações, peso, fotos, catálogos e perfil comportamental.
"""
import hashlib
import json
import os
import re
import csv
import base64
import mimetypes
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import List, Optional

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, inspect, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .financeiro_models import ContaReceber
from .ia.aba6_models import Conversa, MensagemChat
from .models import AuditLog, Cliente, Pet, Tenant, User
from .pdf_veterinario import gerar_pdf_prontuario, gerar_pdf_receita
from .produtos_models import EstoqueMovimentacao, Produto
from .veterinario_calendar import (
    buscar_agendamentos_para_calendario,
    gerar_calendario_ics,
    gerar_token_calendario_vet,
    montar_payload_calendario_vet,
)
from .veterinario_core import (
    _all_accessible_tenant_ids,
    _date_para_datetime_vet,
    _get_tenant,
    _normalizar_datetime_vet,
    _parse_numeric_text,
    _serializar_datetime_vet,
    _vet_now,
)
from .veterinario_financeiro import (
    _as_float,
    _buscar_produtos_por_ids,
    _enriquecer_insumos_com_custos,
    _normalizar_insumos,
    _obter_regra_financeira_veterinaria,
    _resumo_financeiro_procedimento,
    _round_money,
    _serializar_catalogo,
    _serializar_procedimento,
    _sincronizar_financeiro_procedimento,
)
from .veterinario_ia import _responder_chat_exame
from .veterinario_internacao import (
    _build_payload_procedimento_agenda_internacao,
    _build_procedimento_observacao,
    _normalizar_baia,
    _pack_motivo_baia,
    _resolver_data_entrada_exibicao_internacao,
    _resolver_tenant_id_vet,
    _resolver_user_id_vet,
    _separar_evolucoes_e_procedimentos,
    _serializar_procedimento_agenda_internacao,
    _split_motivo_baia,
)
from .veterinario_preventivo import _CALENDARIO_PADRAO
from .veterinario_models import (
    AgendamentoVet,
    CatalogoProcedimento,
    ConsultaVet,
    ConsultorioVet,
    ExameVet,
    FotoClinica,
    InternacaoConfig,
    InternacaoProcedimentoAgenda,
    InternacaoVet,
    EvolucaoInternacao,
    ItemPrescricao,
    MedicamentoCatalogo,
    PerfilComportamental,
    PesoRegistro,
    PrescricaoVet,
    ProcedimentoConsulta,
    ProtocoloVacina,
    VacinaRegistro,
    VetPartnerLink,
)
from .whatsapp.models import TenantWhatsAppConfig

router = APIRouter(prefix="/vet", tags=["Veterinário"])
# Em produção o backend roda em /app/app/*.py, então `parents[1]` aponta para
# /app, que é onde o volume de uploads está montado. `parents[2]` subiria até /
# e faria o upload tentar gravar em /uploads, gerando erro 500.
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "veterinario" / "exames"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

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


def _resolve_exame_file_path(exame: ExameVet, tenant_id) -> Path:
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
    trechos: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages[:max_pages]:
            texto = (page.extract_text() or "").strip()
            if texto:
                trechos.append(texto)
            if sum(len(parte) for parte in trechos) >= max_chars:
                break
    return "\n\n".join(trechos)[:max_chars].strip()


def _basic_lab_values_from_text(texto: str) -> dict:
    if not texto:
        return {}

    padroes = {
        "hematocrito": [
            r"hemat[oó]crito[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"\bht\b[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "hemacias": [
            r"hem[aá]cias[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"eritr[oó]citos?[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "hemoglobina": [
            r"hemoglobina[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"\bhb\b[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "leucocitos": [
            r"leuc[oó]citos?[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"leu[cç][^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "plaquetas": [
            r"plaquetas?[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "ureia": [
            r"ur[eé]ia[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "creatinina": [
            r"creatinina[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "alt": [
            r"\balt\b[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"alanina aminotransferase[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "ast": [
            r"\bast\b[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
            r"aspartato aminotransferase[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
        "glicose": [
            r"glicose[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)",
        ],
    }

    resultado = {}
    for chave, lista_padroes in padroes.items():
        for padrao in lista_padroes:
            match = re.search(padrao, texto, flags=re.IGNORECASE)
            if not match:
                continue
            numero = _parse_numeric_text(match.group(1))
            if numero is not None:
                resultado[chave] = numero
                break
    return resultado


def _strip_markdown_code_block(content: str) -> str:
    texto = (content or "").strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\s*```$", "", texto)
    return texto.strip()


def _parse_llm_json_payload(content: str) -> dict:
    texto = _strip_markdown_code_block(content)
    if not texto:
        return {}

    try:
        parsed = json.loads(texto)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", texto)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _normalize_ai_alerts(alertas) -> list[dict]:
    normalizados: list[dict] = []
    if not isinstance(alertas, list):
        return normalizados

    for alerta in alertas:
        if isinstance(alerta, str):
            mensagem = alerta.strip()
            if mensagem:
                normalizados.append({"campo": "atencao", "status": "atencao", "mensagem": mensagem})
            continue
        if not isinstance(alerta, dict):
            continue
        mensagem = str(alerta.get("mensagem") or "").strip()
        if not mensagem:
            continue
        normalizados.append({
            "campo": str(alerta.get("campo") or "atencao").strip() or "atencao",
            "status": str(alerta.get("status") or "atencao").strip() or "atencao",
            "mensagem": mensagem,
        })
    return normalizados


def _normalize_ai_result_json(resultado_json) -> dict:
    if not isinstance(resultado_json, dict):
        return {}
    normalizado = {}
    for chave, valor in resultado_json.items():
        if chave is None:
            continue
        chave_limpa = str(chave).strip()
        if not chave_limpa:
            continue
        numero = _parse_numeric_text(valor)
        normalizado[chave_limpa] = numero if numero is not None else valor
    return normalizado


def _merge_exam_result_json(exame: ExameVet, novo_json: dict) -> dict:
    atual = exame.resultado_json if isinstance(exame.resultado_json, dict) else {}
    merged = dict(atual)
    for chave, valor in (novo_json or {}).items():
        if valor in (None, "", []):
            continue
        merged[chave] = valor
    return merged


def _build_local_image_data_url(path_arquivo: Path) -> str:
    mime = mimetypes.guess_type(str(path_arquivo))[0] or "image/png"
    conteudo = path_arquivo.read_bytes()
    encoded = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _call_openai_exam_file_analysis(
    *,
    api_key: str,
    model: str,
    exame: ExameVet,
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
    exame: ExameVet,
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
    exame: ExameVet,
) -> ExameVet:
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


def _meses_desde(data_base: Optional[date], referencia: Optional[date] = None) -> Optional[int]:
    if not data_base:
        return None
    ref = referencia or date.today()
    return max((ref.year - data_base.year) * 12 + (ref.month - data_base.month), 0)


def _avaliar_resultado_item(chave: str, valor) -> Optional[dict]:
    numero = _as_float(valor)
    if numero is None:
        return None

    regras = {
        "hematocrito": (25, 55, "Hematócrito fora da faixa."),
        "hemacias": (5, 10, "Hemácias fora da faixa."),
        "hemoglobina": (8, 18, "Hemoglobina fora da faixa."),
        "leucocitos": (6000, 17000, "Leucócitos fora da faixa."),
        "plaquetas": (180000, 500000, "Plaquetas fora da faixa."),
        "ureia": (10, 60, "Ureia elevada ou reduzida."),
        "creatinina": (0.5, 1.8, "Creatinina fora da faixa."),
        "alt": (10, 120, "ALT fora da faixa."),
        "ast": (10, 80, "AST fora da faixa."),
        "glicose": (70, 140, "Glicose fora da faixa."),
    }

    chave_limpa = (chave or "").strip().lower()
    if chave_limpa not in regras:
        return None

    minimo, maximo, mensagem = regras[chave_limpa]
    if minimo <= numero <= maximo:
        return {
            "campo": chave,
            "valor": numero,
            "status": "normal",
            "mensagem": f"{chave}: dentro da faixa esperada.",
        }

    status = "alto" if numero > maximo else "baixo"
    return {
        "campo": chave,
        "valor": numero,
        "status": status,
        "mensagem": mensagem,
    }


def _gerar_interpretacao_exame(exame: ExameVet) -> dict:
    alertas = []
    dados = exame.resultado_json if isinstance(exame.resultado_json, dict) else {}
    for chave, valor in dados.items():
        avaliacao = _avaliar_resultado_item(chave, valor)
        if avaliacao and avaliacao["status"] != "normal":
            alertas.append(avaliacao)

    texto_livre = (exame.resultado_texto or "").lower()
    termos_criticos = {
        "anemia": "Possível anemia descrita no laudo.",
        "trombocitopenia": "Laudo cita trombocitopenia.",
        "leucocitose": "Laudo cita leucocitose.",
        "insuficiência renal": "Laudo cita insuficiência renal.",
        "insuficiencia renal": "Laudo cita insuficiência renal.",
        "hepatopatia": "Laudo cita alteração hepática.",
        "fratura": "Laudo cita fratura.",
        "massa": "Laudo cita presença de massa.",
    }
    for termo, mensagem in termos_criticos.items():
        if termo in texto_livre:
            alertas.append({"campo": termo, "status": "atencao", "mensagem": mensagem})

    if not alertas:
        resumo = "Nenhum alerta automático relevante foi encontrado. Confirmar com avaliação clínica."
        conclusao = "Triagem automática sem achados críticos aparentes."
        confianca = 0.58
    else:
        resumo = "; ".join(dict.fromkeys(a["mensagem"] for a in alertas))
        conclusao = f"Triagem automática encontrou {len(alertas)} ponto(s) que merecem revisão veterinária."
        confianca = min(0.45 + (len(alertas) * 0.1), 0.89)

    return {
        "resumo": resumo,
        "conclusao": conclusao,
        "confianca": round(confianca, 2),
        "alertas": alertas,
        "payload": {
            "resultado_json": dados,
            "tem_resultado_texto": bool(exame.resultado_texto),
            "analisado_em": datetime.utcnow().isoformat(),
        },
    }


def _aplicar_baixa_estoque_itens(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    itens: Optional[list],
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    documento: str,
    observacao: str,
) -> tuple[list[dict], list[int]]:
    itens = _normalizar_insumos(itens)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in itens])
    movimentacoes_ids = []
    for item in itens:
        if not item["baixar_estoque"]:
            continue

        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} nÃ£o encontrado para o procedimento")
        if not produto.ativo:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} nÃ£o encontrado para o procedimento")

        estoque_atual = float(produto.estoque_atual or 0)
        if estoque_atual < item["quantidade"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {produto.nome}. DisponÃ­vel: {estoque_atual}, necessÃ¡rio: {item['quantidade']}",
            )

        quantidade_anterior = estoque_atual
        quantidade_nova = estoque_atual - item["quantidade"]
        produto.estoque_atual = quantidade_nova
        custo_unitario = _round_money(produto.preco_custo)
        custo_total = _round_money(custo_unitario * item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            tenant_id=str(tenant_id),
            produto_id=produto.id,
            tipo="saida",
            motivo=motivo,
            quantidade=item["quantidade"],
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=quantidade_nova,
            custo_unitario=custo_unitario,
            valor_total=custo_total,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            documento=documento,
            observacao=observacao,
            user_id=user_id,
        )
        db.add(movimentacao)
        db.flush()
        movimentacoes_ids.append(movimentacao.id)
        item["nome"] = item.get("nome") or produto.nome
        item["unidade"] = item.get("unidade") or produto.unidade
        item["custo_unitario"] = custo_unitario
        item["custo_total"] = custo_total

    return itens, movimentacoes_ids


def _aplicar_baixa_estoque_procedimento(db: Session, procedimento: ProcedimentoConsulta, tenant_id, user_id: int) -> None:
    if not procedimento.realizado or procedimento.estoque_baixado:
        return

    itens = _normalizar_insumos(procedimento.insumos)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in itens])
    movimentacoes_ids = []
    for item in itens:
        if not item["baixar_estoque"]:
            continue

        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")
        if not produto.ativo:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")

        estoque_atual = float(produto.estoque_atual or 0)
        if estoque_atual < item["quantidade"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {produto.nome}. Disponível: {estoque_atual}, necessário: {item['quantidade']}",
            )

        quantidade_anterior = estoque_atual
        quantidade_nova = estoque_atual - item["quantidade"]
        produto.estoque_atual = quantidade_nova
        custo_unitario = _round_money(produto.preco_custo)
        custo_total = _round_money(custo_unitario * item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            tenant_id=str(tenant_id),
            produto_id=produto.id,
            tipo="saida",
            motivo="procedimento_veterinario",
            quantidade=item["quantidade"],
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=quantidade_nova,
            custo_unitario=custo_unitario,
            valor_total=custo_total,
            referencia_id=procedimento.id,
            referencia_tipo="procedimento_veterinario",
            documento=str(procedimento.consulta_id),
            observacao=f"Baixa automática do procedimento {procedimento.nome}",
            user_id=user_id,
        )
        db.add(movimentacao)
        db.flush()
        movimentacoes_ids.append(movimentacao.id)
        item["nome"] = item.get("nome") or produto.nome
        item["unidade"] = item.get("unidade") or produto.unidade
        item["custo_unitario"] = custo_unitario
        item["custo_total"] = custo_total

    procedimento.insumos = itens
    procedimento.estoque_baixado = bool(movimentacoes_ids) or procedimento.estoque_baixado
    procedimento.estoque_movimentacao_ids = movimentacoes_ids or procedimento.estoque_movimentacao_ids


def _status_vacinal_pet(db: Session, pet: Pet, tenant_id) -> dict:
    especie = (pet.especie or "").strip().lower()
    protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,
    ).all()
    protocolos_ativos = [
        protocolo for protocolo in protocolos
        if not protocolo.especie or protocolo.especie.strip().lower() in {"", especie, "todos", "all"}
    ]

    registros = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet.id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()

    pendentes = []
    vencidas = []
    carteira = []
    hoje = date.today()
    registros_por_nome = {}
    for registro in registros:
        chave = (registro.nome_vacina or "").strip().lower()
        registros_por_nome.setdefault(chave, []).append(registro)
        status = "em_dia"
        if registro.data_proxima_dose and registro.data_proxima_dose < hoje:
            status = "atrasada"
            vencidas.append({
                "nome": registro.nome_vacina,
                "data_proxima_dose": registro.data_proxima_dose.isoformat(),
                "dias_atraso": (hoje - registro.data_proxima_dose).days,
            })
        elif registro.data_proxima_dose and registro.data_proxima_dose <= hoje + timedelta(days=30):
            status = "vence_breve"
        carteira.append({
            "id": registro.id,
            "nome": registro.nome_vacina,
            "data_aplicacao": registro.data_aplicacao.isoformat(),
            "data_proxima_dose": registro.data_proxima_dose.isoformat() if registro.data_proxima_dose else None,
            "numero_dose": registro.numero_dose,
            "lote": registro.lote,
            "fabricante": registro.fabricante,
            "status": status,
        })

    idade_meses = _meses_desde(pet.data_nascimento)
    for protocolo in protocolos_ativos:
        chave = (protocolo.nome or "").strip().lower()
        registros_vacina = registros_por_nome.get(chave, [])
        if registros_vacina:
            continue
        idade_inicio = protocolo.dose_inicial_semanas * 4 if protocolo.dose_inicial_semanas else None
        if idade_inicio is None or idade_meses is None or idade_meses >= idade_inicio:
            pendentes.append({
                "nome": protocolo.nome,
                "motivo": "Vacina prevista no protocolo sem registro aplicado.",
                "idade_inicio_meses": idade_inicio,
            })

    return {
        "carteira": carteira,
        "pendentes": pendentes,
        "vencidas": vencidas,
        "resumo": {
            "total_aplicadas": len(carteira),
            "total_pendentes": len(pendentes),
            "total_vencidas": len(vencidas),
        },
    }


def _montar_alertas_pet(db: Session, pet: Pet, tenant_id) -> list[dict]:
    alertas = []
    alergias = pet.alergias_lista if isinstance(getattr(pet, "alergias_lista", None), list) else None
    if not alergias and pet.alergias:
        alergias = [pet.alergias]
    for alergia in alergias or []:
        alertas.append({"tipo": "alergia", "nivel": "critico", "mensagem": f"Alergia registrada: {alergia}"})

    restricoes = getattr(pet, "restricoes_alimentares_lista", None) or []
    for restricao in restricoes:
        alertas.append({"tipo": "restricao", "nivel": "aviso", "mensagem": f"Restrição alimentar: {restricao}"})

    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    for vacina in status_vacinal["vencidas"]:
        alertas.append({
            "tipo": "vacina_atrasada",
            "nivel": "aviso",
            "mensagem": f"Vacina {vacina['nome']} atrasada há {vacina['dias_atraso']} dia(s).",
        })
    for pendente in status_vacinal["pendentes"][:3]:
        alertas.append({
            "tipo": "vacina_pendente",
            "nivel": "info",
            "mensagem": f"Protocolo sem registro: {pendente['nome']}.",
        })

    exames_pendentes = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
        ExameVet.status.in_(["solicitado", "aguardando", "disponivel"]),
    ).order_by(ExameVet.created_at.desc()).limit(3).all()
    for exame in exames_pendentes:
        alertas.append({
            "tipo": "exame_pendente",
            "nivel": "info",
            "mensagem": f"Exame {exame.nome} ainda está em {exame.status}.",
        })

    return alertas


def _pet_or_404(db: Session, pet_id: int, tenant_id) -> Pet:
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Pet.id == pet_id, Cliente.tenant_id.in_(tenant_ids))
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    return pet


def _consulta_or_404(db: Session, consulta_id: int, tenant_id) -> ConsultaVet:
    c = db.query(ConsultaVet).filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


def _consulta_esta_finalizada(consulta: Optional[ConsultaVet]) -> bool:
    return (getattr(consulta, "status", None) or "").strip().lower() == "finalizada"


def _bloquear_lancamento_em_consulta_finalizada(consulta: Optional[ConsultaVet], acao: str) -> None:
    if not _consulta_esta_finalizada(consulta):
        return
    raise HTTPException(
        status_code=409,
        detail=(
            f"Consulta finalizada nao permite {acao}. "
            "Registre uma nova consulta/retorno ou reabra o fluxo com auditoria controlada."
        ),
    )


def _auditar_exame_pos_finalizacao(
    db: Session,
    *,
    tenant_id,
    user_id: Optional[int],
    exame: ExameVet,
    action: str,
    details: dict,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> None:
    if not exame.consulta_id:
        return

    consulta = db.query(ConsultaVet).filter(
        ConsultaVet.id == exame.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not _consulta_esta_finalizada(consulta):
        return

    db.add(AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type="vet_exame",
        entity_id=exame.id,
        old_value=json.dumps(old_value, ensure_ascii=True, default=str) if old_value else None,
        new_value=json.dumps(new_value, ensure_ascii=True, default=str) if new_value else None,
        details=json.dumps({
            "consulta_id": exame.consulta_id,
            "consulta_finalizada": True,
            **details,
        }, ensure_ascii=True, default=str),
        timestamp=_vet_now(),
    ))


def _prescricao_or_404(db: Session, prescricao_id: int, tenant_id) -> PrescricaoVet:
    p = (
        db.query(PrescricaoVet)
        .options(joinedload(PrescricaoVet.itens), joinedload(PrescricaoVet.pet), joinedload(PrescricaoVet.consulta))
        .filter(PrescricaoVet.id == prescricao_id, PrescricaoVet.tenant_id == tenant_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prescrição não encontrada")
    return p


def _upsert_lembretes_push_agendamento(db: Session, ag: AgendamentoVet, tenant_id) -> None:
    """Cria/atualiza lembretes push de 24h e 1h para o tutor no app mobile."""
    if not ag.data_hora or not ag.cliente_id:
        return

    if ag.status in {"cancelado", "faltou"}:
        return

    from app.campaigns.models import NotificationChannelEnum, NotificationQueue, NotificationStatusEnum

    cliente = db.query(Cliente).filter(
        Cliente.id == ag.cliente_id,
        Cliente.tenant_id == str(tenant_id),
    ).first()
    if not cliente or not cliente.user_id:
        return

    user_tutor = db.query(User).filter(
        User.id == cliente.user_id,
        User.tenant_id == str(tenant_id),
    ).first()
    if not user_tutor or not getattr(user_tutor, "push_token", None):
        return

    prefixo = f"vet-agendamento:{ag.id}:"

    db.query(NotificationQueue).filter(
        NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        NotificationQueue.status == NotificationStatusEnum.pending,
    ).delete(synchronize_session=False)

    agora = datetime.now(ag.data_hora.tzinfo) if getattr(ag.data_hora, "tzinfo", None) else datetime.now()
    lembretes = [
        (
            24,
            "Lembrete de consulta veterinária",
            f"Olá! A consulta do pet está marcada para amanhã às {ag.data_hora.strftime('%H:%M')}.",
        ),
        (
            1,
            "Lembrete de consulta veterinária",
            f"A consulta do pet começa em 1 hora ({ag.data_hora.strftime('%H:%M')}).",
        ),
    ]

    for horas, assunto, mensagem in lembretes:
        envio_em = ag.data_hora - timedelta(hours=horas)
        if envio_em <= agora:
            continue

        idempotencia = f"{prefixo}{horas}h:{ag.data_hora.isoformat()}"
        existe = db.query(NotificationQueue.id).filter(
            NotificationQueue.idempotency_key == idempotencia
        ).first()
        if existe:
            continue

        db.add(
            NotificationQueue(
                tenant_id=tenant_id,
                idempotency_key=idempotencia,
                customer_id=cliente.id,
                channel=NotificationChannelEnum.push,
                subject=assunto,
                body=mensagem,
                push_token=user_tutor.push_token,
                scheduled_at=envio_em,
            )
        )


# ═══════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════════════════════════

class AgendamentoCreate(BaseModel):
    pet_id: int
    cliente_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    consultorio_id: Optional[int] = None
    data_hora: datetime
    duracao_minutos: int = 30
    tipo: str = "consulta"
    motivo: Optional[str] = None
    is_emergencia: bool = False
    sintoma_emergencia: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoUpdate(BaseModel):
    pet_id: Optional[int] = None
    cliente_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    consultorio_id: Optional[int] = None
    data_hora: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    tipo: Optional[str] = None
    motivo: Optional[str] = None
    status: Optional[str] = None
    is_emergencia: Optional[bool] = None
    observacoes: Optional[str] = None
    pretriagem: Optional[dict] = None


class AgendamentoResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    consultorio_id: Optional[int]
    data_hora: datetime
    duracao_minutos: int
    tipo: str
    motivo: Optional[str]
    status: str
    is_emergencia: bool
    consulta_id: Optional[int]
    observacoes: Optional[str]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    consultorio_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


def _sincronizar_marcos_agendamento(ag: AgendamentoVet) -> None:
    agora = _vet_now()
    if ag.status in {"agendado", "confirmado", "aguardando"}:
        ag.inicio_atendimento = None
        ag.fim_atendimento = None
        return
    if ag.status == "em_atendimento" and not ag.inicio_atendimento:
        ag.inicio_atendimento = agora
    if ag.status == "finalizado":
        if not ag.inicio_atendimento:
            ag.inicio_atendimento = agora
        if not ag.fim_atendimento:
            ag.fim_atendimento = agora


def _atualizar_status_agendamento(
    db: Session,
    *,
    tenant_id,
    agendamento_id: Optional[int],
    status_agendamento: str,
) -> Optional[AgendamentoVet]:
    if not agendamento_id:
        return None

    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        return None

    ag.status = status_agendamento
    _sincronizar_marcos_agendamento(ag)
    return ag


def _validar_veterinario_agendamento(db: Session, tenant_id, veterinario_id: Optional[int]) -> Optional[Cliente]:
    if not veterinario_id:
        return None

    veterinario = db.query(Cliente).filter(
        Cliente.id == veterinario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "veterinario",
        Cliente.ativo == True,
    ).first()
    if not veterinario:
        raise HTTPException(status_code=422, detail="Veterinario selecionado nao foi encontrado ou esta inativo")
    return veterinario


def _validar_consultorio_agendamento(db: Session, tenant_id, consultorio_id: Optional[int]) -> Optional[ConsultorioVet]:
    if not consultorio_id:
        return None

    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
        ConsultorioVet.ativo == True,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=422, detail="Consultorio selecionado nao foi encontrado ou esta inativo")
    return consultorio


def _agendamento_intervalo(data_hora: datetime, duracao_minutos: Optional[int]) -> tuple[datetime, datetime]:
    inicio = data_hora
    fim = data_hora + timedelta(minutes=max(int(duracao_minutos or 30), 1))
    return inicio, fim


def _garantir_sem_conflitos_agendamento(
    db: Session,
    *,
    tenant_id,
    data_hora: datetime,
    duracao_minutos: Optional[int],
    veterinario_id: Optional[int],
    consultorio_id: Optional[int],
    agendamento_id_ignorar: Optional[int] = None,
) -> None:
    if not veterinario_id and not consultorio_id:
        return

    consulta = db.query(AgendamentoVet).options(
        joinedload(AgendamentoVet.veterinario),
        joinedload(AgendamentoVet.consultorio),
    ).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == data_hora.date(),
        AgendamentoVet.status != "cancelado",
    )

    if agendamento_id_ignorar:
        consulta = consulta.filter(AgendamentoVet.id != agendamento_id_ignorar)

    if veterinario_id and consultorio_id:
        consulta = consulta.filter(
            or_(
                AgendamentoVet.veterinario_id == veterinario_id,
                AgendamentoVet.consultorio_id == consultorio_id,
            )
        )
    elif veterinario_id:
        consulta = consulta.filter(AgendamentoVet.veterinario_id == veterinario_id)
    else:
        consulta = consulta.filter(AgendamentoVet.consultorio_id == consultorio_id)

    novo_inicio, novo_fim = _agendamento_intervalo(data_hora, duracao_minutos)
    conflito_veterinario = None
    conflito_consultorio = None

    for existente in consulta.all():
        existente_inicio, existente_fim = _agendamento_intervalo(existente.data_hora, existente.duracao_minutos)
        if novo_inicio >= existente_fim or novo_fim <= existente_inicio:
            continue

        if veterinario_id and existente.veterinario_id == veterinario_id and conflito_veterinario is None:
            conflito_veterinario = existente
        if consultorio_id and existente.consultorio_id == consultorio_id and conflito_consultorio is None:
            conflito_consultorio = existente

    mensagens = []
    if conflito_veterinario:
        nome_vet = conflito_veterinario.veterinario.nome if conflito_veterinario.veterinario else "O veterinario selecionado"
        mensagens.append(
            f"{nome_vet} ja possui outro agendamento em conflito nesse horario"
        )
    if conflito_consultorio:
        nome_consultorio = conflito_consultorio.consultorio.nome if conflito_consultorio.consultorio else "O consultorio selecionado"
        mensagens.append(
            f"{nome_consultorio} ja esta reservado nesse horario"
        )
    if mensagens:
        raise HTTPException(status_code=409, detail=". ".join(mensagens) + ".")


def _consulta_tem_conteudo_clinico(consulta: ConsultaVet) -> bool:
    campos_texto = [
        "historia_clinica",
        "exame_fisico",
        "hipotese_diagnostica",
        "diagnostico",
        "diagnostico_simples",
        "conduta",
        "asa_justificativa",
        "observacoes_internas",
        "observacoes_tutor",
    ]
    for campo in campos_texto:
        valor = getattr(consulta, campo, None)
        if isinstance(valor, str) and valor.strip():
            return True

    campos_numericos = [
        "peso_consulta",
        "temperatura",
        "frequencia_cardiaca",
        "frequencia_respiratoria",
        "nivel_dor",
        "saturacao_o2",
        "pressao_sistolica",
        "pressao_diastolica",
        "glicemia",
        "retorno_em_dias",
        "asa_score",
    ]
    for campo in campos_numericos:
        if getattr(consulta, campo, None) is not None:
            return True

    if getattr(consulta, "data_retorno", None) is not None:
        return True
    if getattr(consulta, "tpc", None):
        return True
    if getattr(consulta, "mucosas", None):
        return True
    if getattr(consulta, "hidratacao", None):
        return True
    return False


def _consulta_tem_dependencias(db: Session, tenant_id, consulta_id: int) -> bool:
    checagens = (
        db.query(PrescricaoVet.id).filter(PrescricaoVet.tenant_id == tenant_id, PrescricaoVet.consulta_id == consulta_id).first(),
        db.query(ExameVet.id).filter(ExameVet.tenant_id == tenant_id, ExameVet.consulta_id == consulta_id).first(),
        db.query(ProcedimentoConsulta.id).filter(ProcedimentoConsulta.tenant_id == tenant_id, ProcedimentoConsulta.consulta_id == consulta_id).first(),
        db.query(FotoClinica.id).filter(FotoClinica.tenant_id == tenant_id, FotoClinica.consulta_id == consulta_id).first(),
        db.query(VacinaRegistro.id).filter(VacinaRegistro.tenant_id == tenant_id, VacinaRegistro.consulta_id == consulta_id).first(),
        db.query(InternacaoVet.id).filter(InternacaoVet.tenant_id == tenant_id, InternacaoVet.consulta_id == consulta_id).first(),
        db.query(PesoRegistro.id).filter(PesoRegistro.tenant_id == tenant_id, PesoRegistro.consulta_id == consulta_id).first(),
    )
    return any(item is not None for item in checagens)


# ═══════════════════════════════════════════════════════════════
# VETERINÁRIOS (listagem para seleção em formulários)
# ═══════════════════════════════════════════════════════════════

class VeterinarioSimples(BaseModel):
    id: int
    nome: str
    crmv: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


class ConsultorioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1, le=999)


class ConsultorioUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1, le=999)
    ativo: Optional[bool] = None


class ConsultorioResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    ordem: int
    ativo: bool

    class Config:
        from_attributes = True


@router.get("/veterinarios", response_model=List[VeterinarioSimples])
def listar_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista pessoas cadastradas como veterinário neste tenant (para selects nos formulários)."""
    user, tenant_id = _get_tenant(current)
    vets = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "veterinario",
            Cliente.ativo == True,
        )
        .order_by(Cliente.nome)
        .all()
    )
    return [
        {"id": v.id, "nome": v.nome, "crmv": getattr(v, "crmv", None), "email": v.email, "telefone": v.telefone}
        for v in vets
    ]


@router.get("/consultorios", response_model=List[ConsultorioResponse])
def listar_consultorios(
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(ConsultorioVet).filter(ConsultorioVet.tenant_id == tenant_id)
    if ativos_only:
        q = q.filter(ConsultorioVet.ativo == True)
    return q.order_by(ConsultorioVet.ordem.asc(), ConsultorioVet.nome.asc()).all()


@router.post("/consultorios", response_model=ConsultorioResponse, status_code=201)
def criar_consultorio(
    body: ConsultorioCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = (body.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=422, detail="Informe o nome do consultorio")

    existente = db.query(ConsultorioVet).filter(
        ConsultorioVet.tenant_id == tenant_id,
        func.lower(ConsultorioVet.nome) == nome.lower(),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ja existe um consultorio com esse nome")

    ultima_ordem = db.query(func.max(ConsultorioVet.ordem)).filter(
        ConsultorioVet.tenant_id == tenant_id
    ).scalar() or 0

    consultorio = ConsultorioVet(
        tenant_id=tenant_id,
        nome=nome,
        descricao=(body.descricao or "").strip() or None,
        ordem=body.ordem or (int(ultima_ordem) + 1),
        ativo=True,
    )
    db.add(consultorio)
    db.commit()
    db.refresh(consultorio)
    return consultorio


@router.patch("/consultorios/{consultorio_id}", response_model=ConsultorioResponse)
def atualizar_consultorio(
    consultorio_id: int,
    body: ConsultorioUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            raise HTTPException(status_code=422, detail="Informe o nome do consultorio")
        duplicado = db.query(ConsultorioVet).filter(
            ConsultorioVet.tenant_id == tenant_id,
            func.lower(ConsultorioVet.nome) == nome.lower(),
            ConsultorioVet.id != consultorio_id,
        ).first()
        if duplicado:
            raise HTTPException(status_code=409, detail="Ja existe um consultorio com esse nome")
        consultorio.nome = nome

    if "descricao" in payload:
        consultorio.descricao = (payload.get("descricao") or "").strip() or None
    if "ordem" in payload and payload.get("ordem") is not None:
        consultorio.ordem = int(payload["ordem"])
    if "ativo" in payload and payload.get("ativo") is not None:
        consultorio.ativo = bool(payload["ativo"])

    db.commit()
    db.refresh(consultorio)
    return consultorio


@router.delete("/consultorios/{consultorio_id}", status_code=204)
def remover_consultorio(
    consultorio_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    agendamento_vinculado = db.query(AgendamentoVet.id).filter(
        AgendamentoVet.tenant_id == tenant_id,
        AgendamentoVet.consultorio_id == consultorio_id,
    ).first()
    if agendamento_vinculado:
        raise HTTPException(
            status_code=409,
            detail="Esse consultorio ja possui agendamentos vinculados. Inative-o em vez de excluir.",
        )

    db.delete(consultorio)
    db.commit()
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════════════
# PETS ACESSÍVEIS (próprio tenant + empresas parceiras)
# ═══════════════════════════════════════════════════════════════

@router.get("/pets")
def listar_pets_vet(
    busca: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista os pets acessíveis ao veterinário:
    - pets do próprio tenant (se tiver cadastros próprios)
    - pets de todas as empresas parceiras ativas vinculadas
    """
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)

    q = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Cliente.tenant_id.in_(tenant_ids), Pet.ativo == True)
    )

    if cliente_id:
        q = q.filter(Pet.cliente_id == cliente_id)

    if busca:
        busca_term = f"%{busca}%"
        q = q.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Cliente.nome.ilike(busca_term),
            )
        )

    pets = q.order_by(Pet.nome).limit(limit).all()

    return [
        {
            "id": p.id,
            "codigo": p.codigo,
            "cliente_id": p.cliente_id,
            "nome": p.nome,
            "especie": p.especie,
            "raca": p.raca,
            "sexo": p.sexo,
            "castrado": p.castrado,
            "data_nascimento": p.data_nascimento,
            "peso": p.peso,
            "porte": p.porte,
            "microchip": p.microchip,
            "alergias": p.alergias,
            "doencas_cronicas": p.doencas_cronicas,
            "medicamentos_continuos": p.medicamentos_continuos,
            "historico_clinico": p.historico_clinico,
            "observacoes": p.observacoes,
            "foto_url": p.foto_url,
            "ativo": p.ativo,
            "tenant_id": str(p.tenant_id),
            "cliente_nome": p.cliente.nome if p.cliente else None,
            "cliente_telefone": p.cliente.telefone if p.cliente else None,
            "cliente_celular": p.cliente.celular if p.cliente else None,
        }
        for p in pets
    ]


@router.get("/agenda/calendario")
def obter_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)


@router.post("/agenda/calendario/token")
def regenerar_token_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    user.vet_calendar_token = gerar_token_calendario_vet(db)
    db.add(user)
    db.commit()
    db.refresh(user)
    return montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)


@router.get("/agenda/calendario.ics")
def baixar_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    payload = montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)
    agendamentos = buscar_agendamentos_para_calendario(
        db,
        tenant_id=tenant_id,
        veterinario_id=payload["veterinario_id"],
    )
    nome_calendario = (
        f"Agenda Vet - {payload['veterinario_nome']}"
        if payload["veterinario_nome"]
        else "Agenda Veterinaria"
    )
    conteudo = gerar_calendario_ics(agendamentos, nome_calendario=nome_calendario)
    headers = {
        "Content-Disposition": 'attachment; filename="agenda-veterinaria.ics"',
        "Cache-Control": "no-store",
    }
    return Response(content=conteudo, media_type="text/calendar; charset=utf-8", headers=headers)


@router.get("/agenda/feed/{token}.ics")
def feed_publico_calendario_agenda_vet(
    token: str,
    request: Request,
    db: Session = Depends(get_session),
):
    user = db.query(User).filter(User.vet_calendar_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Calendario nao encontrado")

    tenant_id = user.tenant_id
    payload = montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)
    agendamentos = buscar_agendamentos_para_calendario(
        db,
        tenant_id=tenant_id,
        veterinario_id=payload["veterinario_id"],
    )
    nome_calendario = (
        f"Agenda Vet - {payload['veterinario_nome']}"
        if payload["veterinario_nome"]
        else "Agenda Veterinaria"
    )
    conteudo = gerar_calendario_ics(agendamentos, nome_calendario=nome_calendario)
    return Response(content=conteudo, media_type="text/calendar; charset=utf-8")


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[str] = None,
    pet_id: Optional[int] = None,
    veterinario_id: Optional[int] = None,
    consultorio_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = (
        db.query(AgendamentoVet)
        .options(
            joinedload(AgendamentoVet.pet),
            joinedload(AgendamentoVet.cliente),
            joinedload(AgendamentoVet.veterinario),
            joinedload(AgendamentoVet.consultorio),
        )
        .filter(AgendamentoVet.tenant_id == tenant_id)
    )

    if data_inicio:
        q = q.filter(func.date(AgendamentoVet.data_hora) >= data_inicio)
    if data_fim:
        q = q.filter(func.date(AgendamentoVet.data_hora) <= data_fim)
    if status:
        q = q.filter(AgendamentoVet.status == status)
    if pet_id:
        q = q.filter(AgendamentoVet.pet_id == pet_id)
    if veterinario_id:
        q = q.filter(AgendamentoVet.veterinario_id == veterinario_id)
    if consultorio_id:
        q = q.filter(AgendamentoVet.consultorio_id == consultorio_id)

    agendamentos = q.order_by(AgendamentoVet.data_hora).all()

    result = []
    for ag in agendamentos:
        d = {
            "id": ag.id,
            "pet_id": ag.pet_id,
            "cliente_id": ag.cliente_id,
            "veterinario_id": ag.veterinario_id,
            "consultorio_id": ag.consultorio_id,
            "data_hora": ag.data_hora,
            "duracao_minutos": ag.duracao_minutos,
            "tipo": ag.tipo,
            "motivo": ag.motivo,
            "status": ag.status,
            "is_emergencia": ag.is_emergencia,
            "consulta_id": ag.consulta_id,
            "observacoes": ag.observacoes,
            "created_at": ag.created_at,
        }
        if ag.pet:
            d["pet_nome"] = ag.pet.nome
        if ag.cliente:
            d["cliente_nome"] = ag.cliente.nome
        if ag.veterinario:
            d["veterinario_nome"] = ag.veterinario.nome
        if ag.consultorio:
            d["consultorio_nome"] = ag.consultorio.nome
        result.append(d)
    return result


@router.get("/agendamentos/{agendamento_id}/push-diagnostico")
def diagnostico_push_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    from app.campaigns.models import NotificationQueue

    cliente = db.query(Cliente).filter(
        Cliente.id == ag.cliente_id,
        Cliente.tenant_id == str(tenant_id),
    ).first()
    user_tutor = None
    if cliente and cliente.user_id:
        user_tutor = db.query(User).filter(
            User.id == cliente.user_id,
            User.tenant_id == str(tenant_id),
        ).first()

    prefixo = f"vet-agendamento:{ag.id}:"
    lembretes = db.query(NotificationQueue).filter(
        NotificationQueue.tenant_id == str(tenant_id),
        NotificationQueue.idempotency_key.like(f"{prefixo}%"),
    ).order_by(NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()).all()

    return {
        "agendamento_id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "data_hora": ag.data_hora.isoformat() if ag.data_hora else None,
        "status": ag.status,
        "tutor_tem_push_token": bool(getattr(user_tutor, "push_token", None)),
        "push_token_preview": f"{user_tutor.push_token[:18]}..." if getattr(user_tutor, "push_token", None) else None,
        "lembretes": [
            {
                "id": lembrete.id,
                "subject": lembrete.subject,
                "status": lembrete.status.value if hasattr(lembrete.status, "value") else str(lembrete.status),
                "scheduled_at": lembrete.scheduled_at.isoformat() if lembrete.scheduled_at else None,
            }
            for lembrete in lembretes
        ],
        "observacao": "Para validar push real no celular, o app precisa estar fora do Expo Go e com token registrado.",
    }


@router.post("/agendamentos", response_model=AgendamentoResponse, status_code=201)
def criar_agendamento(
    body: AgendamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet_ref = (
        db.query(Pet)
        .join(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            Pet.id == body.pet_id,
            Cliente.tenant_id.in_(tenant_ids),
        )
        .first()
    )
    if not pet_ref:
        raise HTTPException(status_code=404, detail="Pet nao encontrado para este agendamento")

    cliente_id = body.cliente_id or pet_ref.cliente_id
    if cliente_id != pet_ref.cliente_id:
        raise HTTPException(status_code=422, detail="Tutor informado nao corresponde ao pet selecionado")

    _validar_veterinario_agendamento(db, tenant_id, body.veterinario_id)
    _validar_consultorio_agendamento(db, tenant_id, body.consultorio_id)
    _garantir_sem_conflitos_agendamento(
        db,
        tenant_id=tenant_id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
    )

    tenant_agendamento = tenant_id or getattr(pet_ref, "tenant_id", None)
    if tenant_agendamento is None:
        raise HTTPException(status_code=400, detail="Nao foi possivel identificar o tenant do agendamento")

    ag = AgendamentoVet(
        tenant_id=tenant_agendamento,
        pet_id=body.pet_id,
        cliente_id=cliente_id,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
        user_id=user.id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        tipo=body.tipo,
        motivo=body.motivo,
        is_emergencia=body.is_emergencia,
        sintoma_emergencia=body.sintoma_emergencia,
        observacoes=body.observacoes,
        status="agendado",
    )
    db.add(ag)
    db.flush()
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.patch("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def atualizar_agendamento(
    agendamento_id: int,
    body: AgendamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    payload = body.model_dump(exclude_unset=True)
    pet_id_novo = payload.pop("pet_id", None)
    cliente_id_novo = payload.pop("cliente_id", None)

    if pet_id_novo is not None:
        tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
        pet_ref = (
            db.query(Pet)
            .join(Cliente, Cliente.id == Pet.cliente_id)
            .filter(
                Pet.id == pet_id_novo,
                Cliente.tenant_id.in_(tenant_ids),
            )
            .first()
        )
        if not pet_ref:
            raise HTTPException(status_code=404, detail="Pet nao encontrado para este agendamento")

        cliente_relacionado = cliente_id_novo or pet_ref.cliente_id
        if cliente_relacionado != pet_ref.cliente_id:
            raise HTTPException(status_code=422, detail="Tutor informado nao corresponde ao pet selecionado")

        ag.pet_id = pet_ref.id
        ag.cliente_id = cliente_relacionado
    elif cliente_id_novo is not None and cliente_id_novo != ag.cliente_id:
        raise HTTPException(status_code=422, detail="Para alterar o tutor, selecione tambem o pet correspondente")

    veterinario_id_novo = payload.get("veterinario_id", ag.veterinario_id)
    consultorio_id_novo = payload.get("consultorio_id", ag.consultorio_id)
    data_hora_nova = payload.get("data_hora", ag.data_hora)
    duracao_nova = payload.get("duracao_minutos", ag.duracao_minutos)

    _validar_veterinario_agendamento(db, tenant_id, veterinario_id_novo)
    _validar_consultorio_agendamento(db, tenant_id, consultorio_id_novo)
    _garantir_sem_conflitos_agendamento(
        db,
        tenant_id=tenant_id,
        data_hora=data_hora_nova,
        duracao_minutos=duracao_nova,
        veterinario_id=veterinario_id_novo,
        consultorio_id=consultorio_id_novo,
        agendamento_id_ignorar=agendamento_id,
    )

    for field, value in payload.items():
        setattr(ag, field, value)

    _sincronizar_marcos_agendamento(ag)
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.delete("/agendamentos/{agendamento_id}", status_code=204)
def remover_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    if ag.consulta_id or ag.status == "finalizado":
        raise HTTPException(
            status_code=409,
            detail="Esse agendamento ja gerou um atendimento. Use 'Desfazer inicio do atendimento' primeiro. Se o atendimento ja tiver dados clinicos, exclua ou cancele o atendimento antes.",
        )

    try:
        from app.campaigns.models import NotificationQueue

        prefixo = f"vet-agendamento:{ag.id}:"
        db.query(NotificationQueue).filter(
            NotificationQueue.tenant_id == str(tenant_id),
            NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        ).delete(synchronize_session=False)
    except Exception:
        pass

    db.delete(ag)
    db.commit()
    return Response(status_code=204)


@router.post("/agendamentos/{agendamento_id}/desfazer-inicio", response_model=AgendamentoResponse)
def desfazer_inicio_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).options(
        joinedload(AgendamentoVet.consulta),
        joinedload(AgendamentoVet.pet),
        joinedload(AgendamentoVet.cliente),
        joinedload(AgendamentoVet.veterinario),
        joinedload(AgendamentoVet.consultorio),
    ).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

    if ag.status == "finalizado":
        raise HTTPException(
            status_code=409,
            detail="Esse agendamento ja foi finalizado e nao pode voltar para agendado.",
        )

    consulta = None
    if ag.consulta_id:
        consulta = db.query(ConsultaVet).filter(
            ConsultaVet.id == ag.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()

    if consulta:
        if consulta.status == "finalizada":
            raise HTTPException(
                status_code=409,
                detail="Esse atendimento ja foi finalizado. Para excluir o agendamento, primeiro cancele ou trate o atendimento vinculado.",
            )
        if _consulta_tem_conteudo_clinico(consulta) or _consulta_tem_dependencias(db, tenant_id, consulta.id):
            raise HTTPException(
                status_code=409,
                detail="Esse atendimento ja tem dados clinicos ou registros vinculados. Exclua/cancele o atendimento antes de voltar o agendamento.",
            )
        ag.consulta_id = None
        db.flush()
        db.delete(consulta)

    ag.status = "agendado"
    _sincronizar_marcos_agendamento(ag)
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


def _agendamento_to_dict(ag: AgendamentoVet) -> dict:
    return {
        "id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "veterinario_id": ag.veterinario_id,
        "consultorio_id": ag.consultorio_id,
        "data_hora": _serializar_datetime_vet(ag.data_hora),
        "duracao_minutos": ag.duracao_minutos,
        "tipo": ag.tipo,
        "motivo": ag.motivo,
        "status": ag.status,
        "is_emergencia": ag.is_emergencia,
        "consulta_id": ag.consulta_id,
        "observacoes": ag.observacoes,
        "created_at": _serializar_datetime_vet(ag.created_at),
        "pet_nome": ag.pet.nome if ag.pet else None,
        "cliente_nome": ag.cliente.nome if ag.cliente else None,
        "veterinario_nome": ag.veterinario.nome if ag.veterinario else None,
        "consultorio_nome": ag.consultorio.nome if ag.consultorio else None,
    }


# ═══════════════════════════════════════════════════════════════
# CONSULTAS
# ═══════════════════════════════════════════════════════════════

class ConsultaCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    tipo: str = "consulta"
    agendamento_id: Optional[int] = None
    queixa_principal: Optional[str] = None


class ConsultaUpdate(BaseModel):
    queixa_principal: Optional[str] = None
    historia_clinica: Optional[str] = None
    peso_consulta: Optional[float] = None
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    tpc: Optional[str] = None
    mucosas: Optional[str] = None
    hidratacao: Optional[str] = None
    nivel_dor: Optional[int] = None
    saturacao_o2: Optional[float] = None
    pressao_sistolica: Optional[int] = None
    pressao_diastolica: Optional[int] = None
    glicemia: Optional[float] = None
    exame_fisico: Optional[str] = None
    hipotese_diagnostica: Optional[str] = None
    diagnostico: Optional[str] = None
    diagnostico_simples: Optional[str] = None
    conduta: Optional[str] = None
    retorno_em_dias: Optional[int] = None
    data_retorno: Optional[date] = None
    asa_score: Optional[int] = None
    asa_justificativa: Optional[str] = None
    observacoes_internas: Optional[str] = None
    observacoes_tutor: Optional[str] = None
    veterinario_id: Optional[int] = None


class ConsultaResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    tipo: str
    status: str
    queixa_principal: Optional[str]
    historia_clinica: Optional[str]
    peso_consulta: Optional[float]
    temperatura: Optional[float]
    frequencia_cardiaca: Optional[int]
    frequencia_respiratoria: Optional[int]
    tpc: Optional[str]
    mucosas: Optional[str]
    hidratacao: Optional[str]
    nivel_dor: Optional[int]
    saturacao_o2: Optional[float]
    pressao_sistolica: Optional[int]
    pressao_diastolica: Optional[int]
    glicemia: Optional[float]
    exame_fisico: Optional[str]
    hipotese_diagnostica: Optional[str]
    diagnostico: Optional[str]
    diagnostico_simples: Optional[str]
    conduta: Optional[str]
    retorno_em_dias: Optional[int]
    data_retorno: Optional[date]
    asa_score: Optional[int]
    asa_justificativa: Optional[str]
    observacoes_internas: Optional[str]
    observacoes_tutor: Optional[str]
    hash_prontuario: Optional[str]
    finalizado_em: Optional[datetime]
    inicio_atendimento: Optional[datetime]
    fim_atendimento: Optional[datetime]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas", response_model=List[ConsultaResponse])
def listar_consultas(
    pet_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(ConsultaVet).filter(ConsultaVet.tenant_id == tenant_id)
    if pet_id:
        q = q.filter(ConsultaVet.pet_id == pet_id)
    if status:
        q = q.filter(ConsultaVet.status == status)
    consultas = q.order_by(ConsultaVet.created_at.desc()).offset(skip).limit(limit).all()
    return [_consulta_to_dict(c) for c in consultas]


@router.post("/consultas", response_model=ConsultaResponse, status_code=201)
def criar_consulta(
    body: ConsultaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: alguns fluxos podem chegar sem tenant no contexto.
    if tenant_id is None:
        cliente_ref = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
        if not cliente_ref or not cliente_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Cliente inválido para criação da consulta")
        tenant_id = cliente_ref.tenant_id

    cliente_ok = db.query(Cliente).filter(
        Cliente.id == body.cliente_id,
        Cliente.tenant_id == tenant_id,
    ).first()
    if not cliente_ok:
        raise HTTPException(status_code=404, detail="Tutor não encontrado neste tenant")

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.cliente_id == body.cliente_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado para o tutor informado")

    c = ConsultaVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
        tipo=body.tipo,
        queixa_principal=body.queixa_principal,
        status="em_andamento",
        inicio_atendimento=_vet_now(),
    )
    db.add(c)
    db.flush()

    # Vincula ao agendamento se informado
    if body.agendamento_id:
        ag = db.query(AgendamentoVet).filter(
            AgendamentoVet.id == body.agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        ).first()
        if ag:
            ag.consulta_id = c.id
            ag.status = "em_atendimento"
            ag.inicio_atendimento = c.inicio_atendimento
            _sincronizar_marcos_agendamento(ag)

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def obter_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)
    return _consulta_to_dict(c)


@router.get("/consultas/{consulta_id}/timeline")
def obter_timeline_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    eventos: list[dict] = []

    def adicionar_evento(*, kind: str, item_id: int | str, titulo: str, status_item: Optional[str], data_evento: Optional[datetime], descricao: Optional[str] = None, link: Optional[str] = None, meta: Optional[dict] = None):
        if data_evento is None:
            return
        data_evento_ordenacao = _normalizar_datetime_vet(data_evento) or data_evento
        eventos.append({
            "kind": kind,
            "item_id": item_id,
            "titulo": titulo,
            "status": status_item,
            "data_hora": _serializar_datetime_vet(data_evento),
            "descricao": descricao,
            "link": link,
            "meta": meta or {},
            "_ordem": data_evento_ordenacao,
        })

    adicionar_evento(
        kind="consulta",
        item_id=c.id,
        titulo=f"Consulta #{c.id} iniciada",
        status_item=c.status,
        data_evento=c.inicio_atendimento or c.created_at,
        descricao=c.queixa_principal or c.diagnostico or c.conduta,
        link=f"/veterinario/consultas/{c.id}",
    )

    if c.finalizado_em:
        adicionar_evento(
            kind="alta_consulta",
            item_id=f"consulta-finalizada-{c.id}",
            titulo=f"Consulta #{c.id} finalizada",
            status_item="finalizada",
            data_evento=c.finalizado_em,
            descricao=c.diagnostico or c.conduta or "Consulta concluída.",
            link=f"/veterinario/consultas/{c.id}",
        )

    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    for procedimento in procedimentos:
        adicionar_evento(
            kind="procedimento",
            item_id=procedimento.id,
            titulo=procedimento.nome,
            status_item="realizado" if procedimento.realizado else "pendente",
            data_evento=procedimento.created_at,
            descricao=procedimento.observacoes or procedimento.descricao,
            link=f"/veterinario/consultas/{c.id}",
            meta={
                "valor": _round_money(procedimento.valor),
                "insumos": _normalizar_insumos(procedimento.insumos),
                "estoque_baixado": bool(procedimento.estoque_baixado),
            },
        )

    exames = db.query(ExameVet).filter(
        ExameVet.consulta_id == consulta_id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).all()
    for exame in exames:
        adicionar_evento(
            kind="exame",
            item_id=exame.id,
            titulo=exame.nome,
            status_item=exame.status,
            data_evento=_date_para_datetime_vet(exame.data_resultado) or _date_para_datetime_vet(exame.data_solicitacao) or exame.created_at,
            descricao=exame.observacoes or exame.interpretacao_ia_resumo or exame.tipo,
            link=f"/veterinario/exames?consulta_id={c.id}&pet_id={c.pet_id}",
            meta={
                "tipo": exame.tipo,
                "arquivo_nome": exame.arquivo_nome,
                "arquivo_url": exame.arquivo_url,
            },
        )

    vacinas = db.query(VacinaRegistro).filter(
        VacinaRegistro.consulta_id == consulta_id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()
    for vacina in vacinas:
        adicionar_evento(
            kind="vacina",
            item_id=vacina.id,
            titulo=vacina.nome_vacina,
            status_item="aplicada",
            data_evento=_date_para_datetime_vet(vacina.data_aplicacao),
            descricao=vacina.observacoes or vacina.fabricante,
            link=f"/veterinario/vacinas?consulta_id={c.id}&pet_id={c.pet_id}",
            meta={
                "lote": vacina.lote,
                "numero_dose": vacina.numero_dose,
                "proxima_dose": vacina.data_proxima_dose.isoformat() if vacina.data_proxima_dose else None,
            },
        )

    internacoes = db.query(InternacaoVet).filter(
        InternacaoVet.consulta_id == consulta_id,
        InternacaoVet.tenant_id == tenant_id,
    ).order_by(InternacaoVet.data_entrada.desc()).all()
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        adicionar_evento(
            kind="internacao",
            item_id=internacao.id,
            titulo=f"Internação #{internacao.id}",
            status_item=internacao.status,
            data_evento=internacao.data_entrada,
            descricao=motivo_limpo or internacao.observacoes,
            link=f"/veterinario/internacoes?consulta_id={c.id}",
            meta={
                "box": box,
                "data_saida": _serializar_datetime_vet(internacao.data_saida).isoformat() if internacao.data_saida else None,
            },
        )
        if internacao.data_saida:
            adicionar_evento(
                kind="alta_internacao",
                item_id=f"alta-{internacao.id}",
                titulo=f"Alta da internação #{internacao.id}",
                status_item=internacao.status,
                data_evento=internacao.data_saida,
                descricao=internacao.observacoes,
                link=f"/veterinario/internacoes?consulta_id={c.id}",
                meta={"box": box},
            )

    prescricoes = db.query(PrescricaoVet).filter(
        PrescricaoVet.consulta_id == consulta_id,
        PrescricaoVet.tenant_id == tenant_id,
    ).order_by(PrescricaoVet.created_at.desc()).all()
    for prescricao in prescricoes:
        adicionar_evento(
            kind="prescricao",
            item_id=prescricao.id,
            titulo=prescricao.numero or f"Prescrição #{prescricao.id}",
            status_item=prescricao.tipo_receituario,
            data_evento=prescricao.created_at,
            descricao=prescricao.observacoes,
            link=f"/veterinario/consultas/{c.id}",
            meta={
                "itens": len(prescricao.itens or []),
                "hash_receita": prescricao.hash_receita,
            },
        )

    eventos.sort(key=lambda item: item["_ordem"], reverse=True)
    for item in eventos:
        item.pop("_ordem", None)
    return {
        "consulta_id": c.id,
        "pet_id": c.pet_id,
        "pet_nome": c.pet.nome if c.pet else None,
        "eventos": eventos,
    }


@router.patch("/consultas/{consulta_id}", response_model=ConsultaResponse)
def atualizar_consulta(
    consulta_id: int,
    body: ConsultaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já finalizada não pode ser editada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)

    # Se registrou peso, cria registro na curva de peso
    if body.peso_consulta and body.peso_consulta > 0:
        peso_reg = PesoRegistro(
            pet_id=c.pet_id,
            consulta_id=c.id,
            user_id=user.id,
            data=date.today(),
            peso_kg=body.peso_consulta,
        )
        db.add(peso_reg)

        # Atualiza peso no cadastro do pet
        pet = db.query(Pet).filter(Pet.id == c.pet_id).first()
        if pet:
            pet.peso = body.peso_consulta

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.post("/consultas/{consulta_id}/finalizar", response_model=ConsultaResponse)
def finalizar_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já está finalizada")

    c.status = "finalizada"
    c.fim_atendimento = _vet_now()
    c.finalizado_em = _vet_now()
    c.finalizado_por_id = user.id

    # Hash do prontuário para imutabilidade
    c.hash_prontuario = _hash_prontuario_consulta(c)

    # Finaliza agendamento vinculado
    if c.agendamento:
        c.agendamento.status = "finalizado"
        c.agendamento.fim_atendimento = c.fim_atendimento

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


def _consulta_to_dict(c: ConsultaVet) -> dict:
    return {
        "id": c.id,
        "pet_id": c.pet_id,
        "cliente_id": c.cliente_id,
        "veterinario_id": c.veterinario_id,
        "tipo": c.tipo,
        "status": c.status,
        "queixa_principal": c.queixa_principal,
        "historia_clinica": c.historia_clinica,
        "peso_consulta": c.peso_consulta,
        "temperatura": c.temperatura,
        "frequencia_cardiaca": c.frequencia_cardiaca,
        "frequencia_respiratoria": c.frequencia_respiratoria,
        "tpc": c.tpc,
        "mucosas": c.mucosas,
        "hidratacao": c.hidratacao,
        "nivel_dor": c.nivel_dor,
        "saturacao_o2": c.saturacao_o2,
        "pressao_sistolica": c.pressao_sistolica,
        "pressao_diastolica": c.pressao_diastolica,
        "glicemia": c.glicemia,
        "exame_fisico": c.exame_fisico,
        "hipotese_diagnostica": c.hipotese_diagnostica,
        "diagnostico": c.diagnostico,
        "diagnostico_simples": c.diagnostico_simples,
        "conduta": c.conduta,
        "retorno_em_dias": c.retorno_em_dias,
        "data_retorno": c.data_retorno,
        "asa_score": c.asa_score,
        "asa_justificativa": c.asa_justificativa,
        "observacoes_internas": c.observacoes_internas,
        "observacoes_tutor": c.observacoes_tutor,
        "hash_prontuario": c.hash_prontuario,
        "finalizado_em": _serializar_datetime_vet(c.finalizado_em),
        "inicio_atendimento": _serializar_datetime_vet(c.inicio_atendimento),
        "fim_atendimento": _serializar_datetime_vet(c.fim_atendimento),
        "pet_nome": c.pet.nome if c.pet else None,
        "cliente_nome": c.cliente.nome if c.cliente else None,
        "veterinario_nome": c.veterinario.nome if c.veterinario else None,
        "created_at": _serializar_datetime_vet(c.created_at),
    }


def _hash_prontuario_consulta(c: ConsultaVet) -> str:
    conteudo = f"{c.id}|{c.pet_id}|{c.diagnostico}|{c.conduta}|{c.finalizado_em}"
    return hashlib.sha256(conteudo.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
# PRESCRIÇÕES
# ═══════════════════════════════════════════════════════════════

class ItemPrescricaoIn(BaseModel):
    nome_medicamento: str
    concentracao: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    quantidade: Optional[str] = None
    posologia: str
    via_administracao: Optional[str] = None
    duracao_dias: Optional[int] = None
    medicamento_catalogo_id: Optional[int] = None


class PrescricaoCreate(BaseModel):
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int] = None
    tipo_receituario: str = "simples"
    observacoes: Optional[str] = None
    itens: List[ItemPrescricaoIn]


class PrescricaoResponse(BaseModel):
    id: int
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int]
    numero: Optional[str]
    data_emissao: date
    tipo_receituario: str
    observacoes: Optional[str]
    hash_receita: Optional[str]
    itens: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/prescricoes", response_model=List[PrescricaoResponse])
def listar_prescricoes(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _consulta_or_404(db, consulta_id, tenant_id)
    prescricoes = db.query(PrescricaoVet).filter(
        PrescricaoVet.consulta_id == consulta_id,
        PrescricaoVet.tenant_id == tenant_id,
    ).all()
    return [_prescricao_to_dict(p) for p in prescricoes]


@router.post("/prescricoes", response_model=PrescricaoResponse, status_code=201)
def criar_prescricao(
    body: PrescricaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        consulta_ref = db.query(ConsultaVet).filter(ConsultaVet.id == body.consulta_id).first()
        if not consulta_ref or not consulta_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Consulta inválida para emissão de prescrição")
        tenant_id = consulta_ref.tenant_id

    consulta_ok = db.query(ConsultaVet).filter(
        ConsultaVet.id == body.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not consulta_ok:
        raise HTTPException(status_code=404, detail="Consulta não encontrada neste tenant")

    # Número sequencial
    if consulta_ok.pet_id != body.pet_id:
        raise HTTPException(status_code=422, detail="Pet da prescricao nao confere com o pet da consulta")
    _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "nova prescricao vinculada")
    total = db.query(func.count(PrescricaoVet.id)).filter(PrescricaoVet.tenant_id == tenant_id).scalar() or 0
    numero = f"REC-{total + 1:05d}"

    p = PrescricaoVet(
        consulta_id=body.consulta_id,
        pet_id=body.pet_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
        numero=numero,
        data_emissao=date.today(),
        tipo_receituario=body.tipo_receituario,
        observacoes=body.observacoes,
    )
    db.add(p)
    db.flush()

    for it in body.itens:
        item = ItemPrescricao(
            prescricao_id=p.id,
            tenant_id=tenant_id,
            nome_medicamento=it.nome_medicamento,
            concentracao=it.concentracao,
            forma_farmaceutica=it.forma_farmaceutica,
            quantidade=it.quantidade,
            posologia=it.posologia,
            via_administracao=it.via_administracao,
            duracao_dias=it.duracao_dias,
            medicamento_catalogo_id=it.medicamento_catalogo_id,
        )
        db.add(item)

    db.flush()

    # Hash da receita
    conteudo = f"{p.id}|{p.pet_id}|{p.data_emissao}|{[it.nome_medicamento for it in body.itens]}"
    p.hash_receita = hashlib.sha256(conteudo.encode()).hexdigest()

    db.commit()
    db.refresh(p)
    return _prescricao_to_dict(p)


def _prescricao_to_dict(p: PrescricaoVet) -> dict:
    return {
        "id": p.id,
        "consulta_id": p.consulta_id,
        "pet_id": p.pet_id,
        "veterinario_id": p.veterinario_id,
        "numero": p.numero,
        "data_emissao": p.data_emissao,
        "tipo_receituario": p.tipo_receituario,
        "observacoes": p.observacoes,
        "hash_receita": p.hash_receita,
        "created_at": p.created_at,
        "itens": [
            {
                "id": it.id,
                "nome_medicamento": it.nome_medicamento,
                "concentracao": it.concentracao,
                "forma_farmaceutica": it.forma_farmaceutica,
                "quantidade": it.quantidade,
                "posologia": it.posologia,
                "via_administracao": it.via_administracao,
                "duracao_dias": it.duracao_dias,
                "medicamento_catalogo_id": it.medicamento_catalogo_id,
            }
            for it in p.itens
        ],
    }


# ═══════════════════════════════════════════════════════════════
# VACINAS
# ═══════════════════════════════════════════════════════════════

class VacinaCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    agendamento_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    nome_vacina: str
    fabricante: Optional[str] = None
    lote: Optional[str] = None
    data_aplicacao: date
    data_proxima_dose: Optional[date] = None
    numero_dose: int = 1
    via_administracao: Optional[str] = None
    observacoes: Optional[str] = None


class VacinaResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    nome_vacina: str
    fabricante: Optional[str]
    lote: Optional[str]
    data_aplicacao: date
    data_proxima_dose: Optional[date]
    numero_dose: int
    via_administracao: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/vacinas", response_model=List[VacinaResponse])
def listar_vacinas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: quando o tenant não vem no contexto, usa o tenant do pet informado.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=404, detail="Pet não encontrado")
        tenant_id = pet_ref.tenant_id

    vacinas = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet_id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()
    return vacinas


@router.post("/vacinas", response_model=VacinaResponse, status_code=201)
def registrar_vacina(
    body: VacinaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: em alguns fluxos o tenant pode vir nulo no contexto.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para registro de vacina")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")

    if body.consulta_id:
        _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "novo registro de vacina vinculado")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar vacina")

    v = VacinaRegistro(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
        protocolo_id=body.protocolo_id,
        nome_vacina=body.nome_vacina,
        fabricante=body.fabricante,
        lote=body.lote,
        data_aplicacao=body.data_aplicacao,
        data_proxima_dose=body.data_proxima_dose,
        numero_dose=body.numero_dose,
        via_administracao=body.via_administracao,
        observacoes=body.observacoes,
    )
    db.add(v)
    _atualizar_status_agendamento(
        db,
        tenant_id=tenant_id,
        agendamento_id=body.agendamento_id,
        status_agendamento="finalizado",
    )
    db.commit()
    db.refresh(v)
    return v


@router.get("/vacinas/vencendo")
def vacinas_vencendo(
    dias: int = 30,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista vacinas que vencem nos próximos N dias."""
    user, tenant_id = _get_tenant(current)
    from datetime import timedelta
    limite = date.today() + timedelta(days=dias)
    vacinas = (
        db.query(VacinaRegistro)
        .filter(
            VacinaRegistro.tenant_id == tenant_id,
            VacinaRegistro.data_proxima_dose != None,  # noqa
            VacinaRegistro.data_proxima_dose <= limite,
            VacinaRegistro.data_proxima_dose >= date.today(),
        )
        .order_by(VacinaRegistro.data_proxima_dose)
        .all()
    )
    result = []
    for v in vacinas:
        result.append({
            "id": v.id,
            "pet_id": v.pet_id,
            "pet_nome": v.pet.nome if v.pet else None,
            "nome_vacina": v.nome_vacina,
            "data_proxima_dose": v.data_proxima_dose,
            "dias_restantes": (v.data_proxima_dose - date.today()).days,
        })
    return result


# ═══════════════════════════════════════════════════════════════
# EXAMES
# ═══════════════════════════════════════════════════════════════

class ExameCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    agendamento_id: Optional[int] = None
    tipo: str = "laboratorial"
    nome: str
    data_solicitacao: Optional[date] = None
    laboratorio: Optional[str] = None
    observacoes: Optional[str] = None


class ExameUpdate(BaseModel):
    data_resultado: Optional[date] = None
    status: Optional[str] = None
    resultado_texto: Optional[str] = None
    resultado_json: Optional[dict] = None
    interpretacao: Optional[str] = None
    interpretacao_ia: Optional[str] = None
    interpretacao_ia_resumo: Optional[str] = None
    interpretacao_ia_confianca: Optional[float] = None
    interpretacao_ia_alertas: Optional[list] = None
    interpretacao_ia_payload: Optional[dict] = None
    arquivo_url: Optional[str] = None
    arquivo_nome: Optional[str] = None
    observacoes: Optional[str] = None


class ExameResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    tipo: str
    nome: str
    data_solicitacao: Optional[date]
    data_resultado: Optional[date]
    status: str
    laboratorio: Optional[str]
    resultado_texto: Optional[str]
    resultado_json: Optional[dict]
    interpretacao: Optional[str]
    interpretacao_ia: Optional[str]
    interpretacao_ia_resumo: Optional[str]
    interpretacao_ia_confianca: Optional[float]
    interpretacao_ia_alertas: Optional[list]
    interpretacao_ia_payload: Optional[dict]
    arquivo_url: Optional[str]
    arquivo_nome: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/exames", response_model=List[ExameResponse])
def listar_exames_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet_id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.data_solicitacao.desc()).all()
    return exames


@router.get("/exames", summary="Lista exames com arquivo anexado")
def listar_exames_anexados(
    periodo: str = Query("hoje", description="hoje | semana | periodo"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    tutor: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    periodo = (periodo or "hoje").strip().lower()
    hoje = date.today()

    if periodo == "hoje":
        inicio_ref = hoje
        fim_ref = hoje
    elif periodo == "semana":
        inicio_ref = hoje - timedelta(days=6)
        fim_ref = hoje
    elif periodo == "periodo":
        if not data_inicio or not data_fim:
            raise HTTPException(422, "Informe data_inicio e data_fim para o período personalizado.")
        inicio_ref = data_inicio
        fim_ref = data_fim
    else:
        raise HTTPException(422, "Período inválido. Use: hoje, semana ou periodo.")

    data_ref_expr = func.date(func.coalesce(ExameVet.data_resultado, ExameVet.created_at))

    q = (
        db.query(ExameVet)
        .join(Pet, Pet.id == ExameVet.pet_id)
        .outerjoin(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            ExameVet.tenant_id == tenant_id,
            ExameVet.arquivo_url.isnot(None),
            ExameVet.arquivo_url != "",
            data_ref_expr >= inicio_ref,
            data_ref_expr <= fim_ref,
        )
    )

    if tutor and tutor.strip():
        termo = f"%{tutor.strip()}%"
        q = q.filter(Cliente.nome.ilike(termo))

    exames = q.order_by(data_ref_expr.desc(), ExameVet.id.desc()).all()

    items = []
    for exame in exames:
        data_upload = exame.data_resultado
        if not data_upload and exame.created_at:
            data_upload = exame.created_at.date()

        pet = exame.pet
        tutor_nome = pet.cliente.nome if pet and pet.cliente else None

        items.append({
            "exame_id": exame.id,
            "pet_id": exame.pet_id,
            "consulta_id": exame.consulta_id,
            "pet_nome": pet.nome if pet else None,
            "tutor_nome": tutor_nome,
            "nome_exame": exame.nome,
            "tipo": exame.tipo,
            "status": exame.status,
            "data_upload": data_upload.isoformat() if data_upload else None,
            "arquivo_nome": exame.arquivo_nome,
            "arquivo_url": exame.arquivo_url,
            "tem_interpretacao_ia": bool(exame.interpretacao_ia),
        })

    return {
        "items": items,
        "total": len(items),
        "periodo": periodo,
        "data_inicio": inicio_ref.isoformat(),
        "data_fim": fim_ref.isoformat(),
    }


@router.post("/exames", response_model=ExameResponse, status_code=201)
def criar_exame(
    body: ExameCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")
    if body.consulta_id:
        _bloquear_lancamento_em_consulta_finalizada(consulta_ok, "nova solicitacao de exame vinculada")

    e = ExameVet(
        tenant_id=tenant_id,
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        user_id=user.id,
        tipo=body.tipo,
        nome=body.nome,
        data_solicitacao=body.data_solicitacao or date.today(),
        laboratorio=body.laboratorio,
        observacoes=body.observacoes,
        status="solicitado",
    )
    db.add(e)
    _atualizar_status_agendamento(
        db,
        tenant_id=tenant_id,
        agendamento_id=body.agendamento_id,
        status_agendamento="finalizado",
    )
    db.commit()
    db.refresh(e)
    return e


@router.patch("/exames/{exame_id}", response_model=ExameResponse)
def atualizar_exame(
    exame_id: int,
    body: ExameUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    e = db.query(ExameVet).filter(ExameVet.id == exame_id, ExameVet.tenant_id == tenant_id).first()
    if not e:
        raise HTTPException(404, "Exame não encontrado")
    dados_update = body.model_dump(exclude_unset=True)
    audit_old = {
        "status": e.status,
        "data_resultado": e.data_resultado,
        "resultado_texto": e.resultado_texto,
        "resultado_json": e.resultado_json,
        "arquivo_url": e.arquivo_url,
    }
    for field, value in dados_update.items():
        setattr(e, field, value)
    if body.data_resultado and e.status == "solicitado":
        e.status = "disponivel"
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=e,
        action="vet_exame_update_pos_finalizacao",
        details={"campos": sorted(dados_update.keys())},
        old_value=audit_old,
        new_value={
            "status": e.status,
            "data_resultado": e.data_resultado,
            "resultado_texto": e.resultado_texto,
            "resultado_json": e.resultado_json,
            "arquivo_url": e.arquivo_url,
        },
    )
    db.commit()
    db.refresh(e)
    return e


@router.post("/exames/{exame_id}/interpretar-ia", response_model=ExameResponse)
def interpretar_exame_ia(
    exame_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")
    if not exame.resultado_texto and not exame.resultado_json:
        if exame.arquivo_url:
            exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
        else:
            raise HTTPException(400, "O exame ainda não possui resultado para interpretar")

    analise = _gerar_interpretacao_exame(exame)
    exame.interpretacao_ia = analise["conclusao"]
    exame.interpretacao_ia_resumo = analise["resumo"]
    exame.interpretacao_ia_confianca = analise["confianca"]
    exame.interpretacao_ia_alertas = analise["alertas"]
    exame.interpretacao_ia_payload = analise["payload"]
    if exame.status in {"disponivel", "aguardando", "coletado", "solicitado"}:
        exame.status = "interpretado"
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_ia_pos_finalizacao",
        details={"origem": "interpretar_ia"},
        new_value={"status": exame.status, "interpretacao_ia_resumo": exame.interpretacao_ia_resumo},
    )
    db.commit()
    db.refresh(exame)
    return exame


@router.post("/exames/{exame_id}/processar-arquivo-ia", response_model=ExameResponse)
def processar_arquivo_exame_ia(
    exame_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")
    if not exame.arquivo_url:
        raise HTTPException(400, "O exame ainda não possui arquivo anexado.")

    exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_process_file_ia_pos_finalizacao",
        details={"origem": "processar_arquivo_ia"},
        new_value={"status": exame.status, "resultado_texto": exame.resultado_texto},
    )
    db.commit()
    db.refresh(exame)
    return exame


@router.post("/exames/{exame_id}/arquivo", response_model=ExameResponse)
def upload_arquivo_exame(
    exame_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")

    audit_old = {
        "arquivo_url": exame.arquivo_url,
        "arquivo_nome": exame.arquivo_nome,
        "status": exame.status,
        "data_resultado": exame.data_resultado,
    }

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

    with open(caminho_arquivo, "wb") as file_handle:
        file_handle.write(conteudo)

    exame.arquivo_nome = nome_original
    exame.arquivo_url = f"/uploads/veterinario/exames/{tenant_id}/{nome_arquivo}"
    if not exame.data_resultado:
        exame.data_resultado = date.today()
    if exame.status == "solicitado":
        exame.status = "disponivel"
    _auditar_exame_pos_finalizacao(
        db,
        tenant_id=tenant_id,
        user_id=_resolver_user_id_vet(user, "Usuario invalido para auditar exame"),
        exame=exame,
        action="vet_exame_upload_pos_finalizacao",
        details={"arquivo_nome": nome_original},
        old_value=audit_old,
        new_value={
            "arquivo_url": exame.arquivo_url,
            "arquivo_nome": exame.arquivo_nome,
            "status": exame.status,
            "data_resultado": exame.data_resultado,
        },
    )
    db.commit()
    db.refresh(exame)
    return exame


# ═══════════════════════════════════════════════════════════════
# PESO — curva de peso do pet
# ═══════════════════════════════════════════════════════════════

@router.get("/pets/{pet_id}/peso")
def curva_peso(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    registros = db.query(PesoRegistro).filter(
        PesoRegistro.pet_id == pet_id,
        PesoRegistro.tenant_id == tenant_id,
    ).order_by(PesoRegistro.data).all()
    return [{"data": r.data, "peso_kg": r.peso_kg, "consulta_id": r.consulta_id} for r in registros]


@router.post("/pets/{pet_id}/peso", status_code=201)
def registrar_peso(
    pet_id: int,
    peso_kg: float = Query(..., gt=0),
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    r = PesoRegistro(
        pet_id=pet_id,
        user_id=user.id,
        data=date.today(),
        peso_kg=peso_kg,
        observacoes=observacoes,
    )
    db.add(r)
    # Atualiza peso principal do pet
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    if pet:
        pet.peso = peso_kg
    db.commit()
    return {"ok": True, "peso_kg": peso_kg}


# ═══════════════════════════════════════════════════════════════
# PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class ProcedimentoCreate(BaseModel):
    consulta_id: int
    catalogo_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    valor: Optional[float] = None
    realizado: bool = True
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)
    baixar_estoque: bool = True


class ProcedimentoResponse(BaseModel):
    id: int
    consulta_id: int
    catalogo_id: Optional[int]
    nome: str
    descricao: Optional[str]
    valor: Optional[float]
    valor_cobrado: float = 0
    realizado: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_total: float = 0
    margem_valor: float = 0
    margem_percentual: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_valor: float = 0
    receita_tenant_valor: float = 0
    entrada_empresa_valor: float = 0
    estoque_baixado: bool = False
    estoque_movimentacao_ids: list[int] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/procedimentos", response_model=List[ProcedimentoResponse])
def listar_procedimentos_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    return [_serializar_procedimento(procedimento, db, tenant_id) for procedimento in procedimentos]


@router.post("/procedimentos", response_model=ProcedimentoResponse, status_code=201)
def adicionar_procedimento(
    body: ProcedimentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    consulta = _consulta_or_404(db, body.consulta_id, tenant_id)
    _bloquear_lancamento_em_consulta_finalizada(consulta, "novo procedimento vinculado")

    catalogo = None
    if body.catalogo_id:
        catalogo = db.query(CatalogoProcedimento).filter(
            CatalogoProcedimento.id == body.catalogo_id,
            CatalogoProcedimento.tenant_id == tenant_id,
        ).first()
        if not catalogo:
            raise HTTPException(status_code=404, detail="Procedimento de catálogo não encontrado")

    insumos = _normalizar_insumos(body.insumos or [])
    if not insumos and catalogo and isinstance(catalogo.insumos, list):
        insumos = _normalizar_insumos(catalogo.insumos)
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, insumos)

    p = ProcedimentoConsulta(
        tenant_id=tenant_id,
        consulta_id=body.consulta_id,
        catalogo_id=body.catalogo_id,
        user_id=user.id,
        nome=body.nome or (catalogo.nome if catalogo else "Procedimento"),
        descricao=body.descricao if body.descricao is not None else (catalogo.descricao if catalogo else None),
        valor=body.valor if body.valor is not None else (float(catalogo.valor_padrao) if catalogo and catalogo.valor_padrao is not None else None),
        realizado=body.realizado,
        observacoes=body.observacoes,
        insumos=insumos,
    )
    db.add(p)
    db.flush()
    if body.baixar_estoque:
        _aplicar_baixa_estoque_procedimento(db, p, tenant_id, user.id)
    _sincronizar_financeiro_procedimento(db, p, tenant_id, user.id)
    db.commit()
    db.refresh(p)
    return _serializar_procedimento(p, db, tenant_id)


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class CatalogoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: bool = False
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)


class CatalogoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: Optional[bool] = None
    observacoes: Optional[str] = None
    insumos: Optional[list[dict]] = None


class CatalogoResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    categoria: Optional[str]
    valor_padrao: Optional[float]
    duracao_minutos: Optional[int]
    requer_anestesia: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_estimado: float = 0
    margem_estimada: float = 0
    margem_percentual_estimada: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_estimado: float = 0
    receita_tenant_estimada: float = 0
    ativo: bool

    class Config:
        from_attributes = True


@router.get("/catalogo/procedimentos", response_model=List[CatalogoResponse])
def listar_catalogo_procedimentos(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    catalogos = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).order_by(CatalogoProcedimento.nome).all()
    return [_serializar_catalogo(catalogo, db, tenant_id) for catalogo in catalogos]


@router.post("/catalogo/procedimentos", response_model=CatalogoResponse, status_code=201)
def criar_catalogo_procedimento(
    body: CatalogoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = CatalogoProcedimento(
        tenant_id=tenant_id,
        nome=body.nome,
        descricao=body.descricao,
        categoria=body.categoria,
        valor_padrao=body.valor_padrao,
        duracao_minutos=body.duracao_minutos,
        requer_anestesia=body.requer_anestesia,
        observacoes=body.observacoes,
        insumos=_normalizar_insumos(body.insumos),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar_catalogo(p, db, tenant_id)


@router.patch("/catalogo/procedimentos/{catalogo_id}", response_model=CatalogoResponse)
def atualizar_catalogo_procedimento(
    catalogo_id: int,
    body: CatalogoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "insumos" in payload:
        catalogo.insumos = _normalizar_insumos(payload.pop("insumos"))
    for campo, valor in payload.items():
        setattr(catalogo, campo, valor)

    db.commit()
    db.refresh(catalogo)
    return _serializar_catalogo(catalogo, db, tenant_id)


@router.delete("/catalogo/procedimentos/{catalogo_id}", status_code=204)
def remover_catalogo_procedimento(
    catalogo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    catalogo.ativo = False
    db.commit()
    return Response(status_code=204)


@router.get("/catalogo/produtos-estoque")
def listar_produtos_estoque(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
        Produto.situacao == True,
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(or_(Produto.nome.ilike(termo), Produto.codigo.ilike(termo)))
    produtos = q.order_by(Produto.nome).limit(limit).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "unidade": produto.unidade,
            "estoque_atual": float(produto.estoque_atual or 0),
            "preco_custo": _round_money(produto.preco_custo),
        }
        for produto in produtos
    ]


@router.get("/pets/{pet_id}/alertas")
def listar_alertas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    return {
        "pet_id": pet.id,
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": _status_vacinal_pet(db, pet, tenant_id),
    }


@router.get("/pets/{pet_id}/carteirinha")
def obter_carteirinha_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).limit(10).all()
    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.pet_id == pet.id,
        ConsultaVet.tenant_id == tenant_id,
    ).order_by(ConsultaVet.created_at.desc()).limit(10).all()

    return {
        "pet": {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "peso": float(pet.peso) if pet.peso is not None else None,
            "foto_url": pet.foto_url,
            "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
            "alergias": getattr(pet, "alergias_lista", None) or ([pet.alergias] if pet.alergias else []),
            "restricoes_alimentares": getattr(pet, "restricoes_alimentares_lista", None) or [],
            "medicamentos_continuos": getattr(pet, "medicamentos_continuos_lista", None) or [],
            "condicoes_cronicas": getattr(pet, "condicoes_cronicas_lista", None) or [],
        },
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.date().isoformat() if consulta.created_at else None,
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
                "data_resultado": exame.data_resultado.isoformat() if exame.data_resultado else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE MEDICAMENTOS
# ═══════════════════════════════════════════════════════════════

class MedicamentoCreate(BaseModel):
    nome: str
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: bool = False
    eh_controlado: bool = False
    observacoes: Optional[str] = None


class MedicamentoUpdate(BaseModel):
    nome: Optional[str] = None
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: Optional[bool] = None
    eh_controlado: Optional[bool] = None
    observacoes: Optional[str] = None


@router.get("/catalogo/medicamentos")
def listar_medicamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(
            or_(
                MedicamentoCatalogo.nome.ilike(termo),
                MedicamentoCatalogo.principio_ativo.ilike(termo),
                MedicamentoCatalogo.nome_comercial.ilike(termo),
            )
        )
    return q.order_by(MedicamentoCatalogo.nome).limit(50).all()


@router.post("/catalogo/medicamentos", status_code=201)
def criar_medicamento(
    body: MedicamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    m = MedicamentoCatalogo(tenant_id=tenant_id, **body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/catalogo/medicamentos/{medicamento_id}")
def atualizar_medicamento(
    medicamento_id: int,
    body: MedicamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(medicamento, campo, valor)

    db.commit()
    db.refresh(medicamento)
    return medicamento


@router.delete("/catalogo/medicamentos/{medicamento_id}", status_code=204)
def remover_medicamento(
    medicamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    medicamento.ativo = False
    db.commit()
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════════════
# PROTOCOLOS DE VACINAS
# ═══════════════════════════════════════════════════════════════

class ProtocoloVacinaUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    dose_inicial_semanas: Optional[int] = None
    reforco_anual: Optional[bool] = None
    numero_doses_serie: Optional[int] = None
    intervalo_doses_dias: Optional[int] = None
    observacoes: Optional[str] = None


@router.get("/catalogo/protocolos-vacinas")
def listar_protocolos_vacinas(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).order_by(ProtocoloVacina.nome).all()


@router.post("/catalogo/protocolos-vacinas", status_code=201)
def criar_protocolo_vacina(
    nome: str,
    especie: Optional[str] = None,
    dose_inicial_semanas: Optional[int] = None,
    reforco_anual: bool = True,
    numero_doses_serie: int = 1,
    intervalo_doses_dias: Optional[int] = None,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProtocoloVacina(
        tenant_id=tenant_id,
        nome=nome,
        especie=especie,
        dose_inicial_semanas=dose_inicial_semanas,
        reforco_anual=reforco_anual,
        numero_doses_serie=numero_doses_serie,
        intervalo_doses_dias=intervalo_doses_dias,
        observacoes=observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/catalogo/protocolos-vacinas/{protocolo_id}")
def atualizar_protocolo_vacina(
    protocolo_id: int,
    body: ProtocoloVacinaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(protocolo, campo, valor)

    db.commit()
    db.refresh(protocolo)
    return protocolo


@router.delete("/catalogo/protocolos-vacinas/{protocolo_id}", status_code=204)
def remover_protocolo_vacina(
    protocolo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    protocolo.ativo = False
    db.commit()
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════════════
# INTERNAÇÃO
# ═══════════════════════════════════════════════════════════════

class InternacaoCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    motivo: Optional[str] = None
    motivo_internacao: Optional[str] = None
    box: Optional[str] = None
    baia_numero: Optional[str] = None
    data_entrada: Optional[datetime] = None


class EvolucaoCreate(BaseModel):
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    # Compatibilidade com payload antigo do frontend
    freq_cardiaca: Optional[int] = None
    freq_respiratoria: Optional[int] = None
    nivel_dor: Optional[int] = None
    pressao_sistolica: Optional[int] = None
    glicemia: Optional[float] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None


class ProcedimentoInternacaoCreate(BaseModel):
    horario_agendado: Optional[datetime] = None
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    quantidade_executada: Optional[float] = None
    quantidade_desperdicio: Optional[float] = None
    unidade_quantidade: Optional[str] = None
    tipo_registro: Optional[str] = "procedimento"
    insumos: list[dict] = Field(default_factory=list)
    observacoes_agenda: Optional[str] = None
    executado_por: Optional[str] = None
    horario_execucao: Optional[datetime] = None
    observacao_execucao: Optional[str] = None
    status: Optional[str] = "concluido"


class InternacaoConfigUpdate(BaseModel):
    total_baias: int = Field(..., ge=1, le=200)


class ProcedimentoAgendaInternacaoCreate(BaseModel):
    horario_agendado: datetime
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    unidade_quantidade: Optional[str] = None
    lembrete_min: Optional[int] = Field(30, ge=0, le=1440)
    observacoes_agenda: Optional[str] = None


class ProcedimentoAgendaInternacaoConcluir(BaseModel):
    executado_por: str
    horario_execucao: datetime
    observacao_execucao: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    quantidade_executada: Optional[float] = None
    quantidade_desperdicio: Optional[float] = None
    unidade_quantidade: Optional[str] = None


@router.get("/internacoes")
def listar_internacoes(
    status: Optional[str] = "internado",
    pet_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    data_saida_inicio: Optional[date] = Query(None),
    data_saida_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Compatibilidade: telas antigas enviavam "ativa" para status de internação aberta.
    status_map = {
        "ativa": "internado",
    }
    status_normalizado = status_map.get(status, status)

    # Fallback defensivo: em alguns fluxos o tenant pode vir no usuário e não no retorno do Depends.
    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado para listar internações")

    q = db.query(InternacaoVet).filter(InternacaoVet.tenant_id == tenant_id)
    if status_normalizado:
        q = q.filter(InternacaoVet.status == status_normalizado)
    if pet_id:
        q = q.filter(InternacaoVet.pet_id == pet_id)
    if cliente_id:
        q = q.filter(InternacaoVet.pet.has(Pet.cliente_id == cliente_id))
    if data_saida_inicio:
        q = q.filter(func.date(InternacaoVet.data_saida) >= data_saida_inicio)
    if data_saida_fim:
        q = q.filter(func.date(InternacaoVet.data_saida) <= data_saida_fim)

    internacoes = q.order_by(InternacaoVet.data_entrada.desc()).all()
    result = []
    for i in internacoes:
        motivo_limpo, box = _split_motivo_baia(i.motivo)
        tutor = i.pet.cliente if i.pet and i.pet.cliente else None
        result.append({
            "id": i.id,
            "pet_id": i.pet_id,
            "consulta_id": i.consulta_id,
            "pet_nome": i.pet.nome if i.pet else None,
            "tutor_id": tutor.id if tutor else None,
            "tutor_nome": tutor.nome if tutor else None,
            "motivo": motivo_limpo,
            "box": box,
            "status": i.status,
            "data_entrada": _serializar_datetime_vet(i.data_entrada),
            "data_saida": _serializar_datetime_vet(i.data_saida),
            "observacoes_alta": i.observacoes,
        })
    return result


@router.get("/internacoes/config")
def obter_config_internacao(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para configuracao de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para configuracao de internacao")

    config = db.query(InternacaoConfig).filter(InternacaoConfig.tenant_id == tenant_id).first()
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=12,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }


@router.put("/internacoes/config")
def atualizar_config_internacao(
    body: InternacaoConfigUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para configuracao de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para configuracao de internacao")

    config = db.query(InternacaoConfig).filter(InternacaoConfig.tenant_id == tenant_id).first()
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=body.total_baias,
        )
        db.add(config)
    else:
        config.user_id = user_id
        config.total_baias = body.total_baias

    db.commit()
    db.refresh(config)
    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }


@router.get("/internacoes/procedimentos-agenda")
def listar_procedimentos_agenda_internacao(
    status: Optional[str] = Query("ativos"),
    internacao_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")

    status_normalizado = (status or "ativos").strip().lower()
    if status_normalizado in {"", "ativos", "ativo"}:
        status_filtro = ["agendado", "concluido"]
    elif status_normalizado in {"pendente", "pendentes", "agendado"}:
        status_filtro = ["agendado"]
    elif status_normalizado in {"feito", "feitos", "concluido", "concluidos"}:
        status_filtro = ["concluido"]
    elif status_normalizado in {"cancelado", "cancelados"}:
        status_filtro = ["cancelado"]
    else:
        raise HTTPException(status_code=422, detail="Status da agenda de internacao invalido")

    query = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
            InternacaoProcedimentoAgenda.status.in_(status_filtro),
        )
    )
    if internacao_id:
        query = query.filter(InternacaoProcedimentoAgenda.internacao_id == internacao_id)

    itens = query.order_by(InternacaoProcedimentoAgenda.horario_agendado.asc()).all()
    return [_serializar_procedimento_agenda_internacao(item) for item in itens]


@router.post("/internacoes/{internacao_id}/procedimentos-agenda", status_code=201)
def criar_procedimento_agenda_internacao(
    internacao_id: int,
    body: ProcedimentoAgendaInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    internacao = (
        db.query(InternacaoVet)
        .options(joinedload(InternacaoVet.pet))
        .filter(
            InternacaoVet.id == internacao_id,
            InternacaoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not internacao:
        raise HTTPException(404, "Internacao nao encontrada")
    if internacao.status != "internado":
        raise HTTPException(status_code=409, detail="Agenda de procedimento so pode ser criada para internacao ativa")

    medicamento = (body.medicamento or "").strip()
    if not medicamento:
        raise HTTPException(status_code=422, detail="Medicamento/procedimento e obrigatorio")

    horario_agendado = _normalizar_datetime_vet(body.horario_agendado)
    if not horario_agendado:
        raise HTTPException(status_code=422, detail="Horario agendado e obrigatorio")

    quantidade_prevista = _as_float(body.quantidade_prevista)
    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nao pode ser negativa")

    item = InternacaoProcedimentoAgenda(
        tenant_id=tenant_id,
        user_id=user_id,
        internacao_id=internacao.id,
        pet_id=internacao.pet_id,
        horario_agendado=horario_agendado,
        medicamento=medicamento,
        dose=(body.dose or "").strip() or None,
        via=(body.via or "").strip() or None,
        quantidade_prevista=quantidade_prevista,
        unidade_quantidade=(body.unidade_quantidade or "").strip() or None,
        lembrete_minutos=body.lembrete_min if body.lembrete_min is not None else 30,
        observacoes_agenda=(body.observacoes_agenda or "").strip() or None,
        status="agendado",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    item.internacao = internacao
    item.pet = internacao.pet
    return _serializar_procedimento_agenda_internacao(item)


@router.patch("/internacoes/procedimentos-agenda/{agenda_id}/concluir")
def concluir_procedimento_agenda_internacao(
    agenda_id: int,
    body: ProcedimentoAgendaInternacaoConcluir,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    item = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.id == agenda_id,
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    if item.status == "cancelado":
        raise HTTPException(status_code=409, detail="Procedimento cancelado nao pode ser concluido")

    executado_por = (body.executado_por or "").strip()
    if not executado_por:
        raise HTTPException(status_code=422, detail="Campo 'executado_por' e obrigatorio")

    horario_execucao = _normalizar_datetime_vet(body.horario_execucao)
    if not horario_execucao:
        raise HTTPException(status_code=422, detail="Campo 'horario_execucao' e obrigatorio")

    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nao pode ser negativa")
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(status_code=422, detail="Quantidade executada nao pode ser negativa")
    if quantidade_desperdicio < 0:
        raise HTTPException(status_code=422, detail="Quantidade de desperdicio nao pode ser negativa")
    if quantidade_executada is None and quantidade_prevista is not None:
        quantidade_executada = quantidade_prevista

    item.status = "concluido"
    item.executado_por = executado_por
    item.horario_execucao = horario_execucao
    item.observacao_execucao = (body.observacao_execucao or "").strip() or None
    item.quantidade_prevista = quantidade_prevista if quantidade_prevista is not None else item.quantidade_prevista
    item.quantidade_executada = quantidade_executada
    item.quantidade_desperdicio = quantidade_desperdicio
    item.unidade_quantidade = (body.unidade_quantidade or "").strip() or item.unidade_quantidade

    payload = _build_payload_procedimento_agenda_internacao(item)
    if item.procedimento_evolucao_id:
        evolucao = db.query(EvolucaoInternacao).filter(
            EvolucaoInternacao.id == item.procedimento_evolucao_id,
            EvolucaoInternacao.tenant_id == tenant_id,
        ).first()
        if evolucao:
            evolucao.user_id = user_id
            evolucao.data_hora = horario_execucao
            evolucao.observacoes = _build_procedimento_observacao(payload)
        else:
            item.procedimento_evolucao_id = None

    if not item.procedimento_evolucao_id:
        evolucao = EvolucaoInternacao(
            internacao_id=item.internacao_id,
            user_id=user_id,
            tenant_id=tenant_id,
            data_hora=horario_execucao,
            observacoes=_build_procedimento_observacao(payload),
        )
        db.add(evolucao)
        db.flush()
        item.procedimento_evolucao_id = evolucao.id

    db.commit()
    db.refresh(item)
    return _serializar_procedimento_agenda_internacao(item)


@router.delete("/internacoes/procedimentos-agenda/{agenda_id}", status_code=204)
def remover_procedimento_agenda_internacao(
    agenda_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(user, tenant_id, "Tenant nao identificado para agenda de internacao")

    item = db.query(InternacaoProcedimentoAgenda).filter(
        InternacaoProcedimentoAgenda.id == agenda_id,
        InternacaoProcedimentoAgenda.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    if item.status == "concluido":
        raise HTTPException(
            status_code=409,
            detail="Procedimento concluido ja compoe o historico clinico e nao pode ser excluido",
        )

    item.status = "cancelado"
    db.commit()
    return Response(status_code=204)


@router.get("/internacoes/{internacao_id}")
def obter_internacao(
    internacao_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    evolucoes = (
        db.query(EvolucaoInternacao)
        .filter(EvolucaoInternacao.internacao_id == internacao_id)
        .order_by(EvolucaoInternacao.data_hora.desc())
        .all()
    )

    motivo_limpo, box = _split_motivo_baia(i.motivo)

    evolucoes_formatadas, procedimentos_formatados = _separar_evolucoes_e_procedimentos(evolucoes)

    data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(i, evolucoes)

    return {
        "id": i.id,
        "pet_id": i.pet_id,
        "consulta_id": i.consulta_id,
        "pet_nome": i.pet.nome if i.pet else None,
        "tutor_id": i.pet.cliente.id if i.pet and i.pet.cliente else None,
        "tutor_nome": i.pet.cliente.nome if i.pet and i.pet.cliente else None,
        "motivo": motivo_limpo,
        "box": box,
        "status": i.status,
        "data_entrada": data_entrada_exibicao,
        "data_saida": _serializar_datetime_vet(i.data_saida),
        "observacoes_alta": i.observacoes,
        "evolucoes": evolucoes_formatadas,
        "procedimentos": procedimentos_formatados,
    }


@router.get("/pets/{pet_id}/internacoes-historico")
def obter_historico_internacoes_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado")

    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(404, "Pet não encontrado")

    internacoes = (
        db.query(InternacaoVet)
        .filter(InternacaoVet.pet_id == pet_id, InternacaoVet.tenant_id == tenant_id)
        .order_by(InternacaoVet.data_entrada.desc())
        .all()
    )

    historico = []
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        registros = (
            db.query(EvolucaoInternacao)
            .filter(EvolucaoInternacao.internacao_id == internacao.id)
            .order_by(EvolucaoInternacao.data_hora.desc())
            .all()
        )
        evols, procs = _separar_evolucoes_e_procedimentos(registros)

        data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(internacao, registros)

        historico.append({
            "internacao_id": internacao.id,
            "status": internacao.status,
            "motivo": motivo_limpo,
            "box": box,
            "data_entrada": data_entrada_exibicao,
            "data_saida": _serializar_datetime_vet(internacao.data_saida),
            "observacoes_alta": internacao.observacoes,
            "evolucoes": evols,
            "procedimentos": procs,
        })

    return {
        "pet_id": pet.id,
        "pet_nome": pet.nome,
        "historico": historico,
    }


@router.post("/internacoes", status_code=201)
def criar_internacao(
    body: InternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    motivo = (body.motivo or body.motivo_internacao or "").strip()
    box = (body.box or body.baia_numero or "").strip()
    box_normalizado = _normalizar_baia(box)
    if not motivo:
        raise HTTPException(status_code=422, detail="Campo 'motivo' é obrigatório")

    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para internação")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    if body.consulta_id:
        consulta_ok = db.query(ConsultaVet).filter(
            ConsultaVet.id == body.consulta_id,
            ConsultaVet.pet_id == body.pet_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if not consulta_ok:
            raise HTTPException(status_code=404, detail="Consulta vinculada nÃ£o encontrada para este pet")

    if box_normalizado:
        internacoes_ativas = (
            db.query(InternacaoVet)
            .filter(
                InternacaoVet.tenant_id == tenant_id,
                InternacaoVet.status == "internado",
            )
            .all()
        )
        for internacao_ativa in internacoes_ativas:
            _, box_ocupado = _split_motivo_baia(internacao_ativa.motivo)
            if _normalizar_baia(box_ocupado) == box_normalizado:
                raise HTTPException(
                    status_code=409,
                    detail=f"A baia {box} já está ocupada por outro internado.",
                )

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para internação")

    i = InternacaoVet(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
        motivo=_pack_motivo_baia(motivo, box),
        data_entrada=_normalizar_datetime_vet(body.data_entrada) or _vet_now(),
        status="internado",
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return {
        "id": i.id,
        "consulta_id": i.consulta_id,
        "status": i.status,
        "data_entrada": _serializar_datetime_vet(i.data_entrada),
    }


@router.post("/internacoes/{internacao_id}/evolucao", status_code=201)
def registrar_evolucao(
    internacao_id: int,
    body: EvolucaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    # Se o tenant veio no contexto, valida acesso. Se não veio, usa o tenant da internação.
    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_evolucao = i.tenant_id or tenant_id
    if tenant_id_evolucao is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar evolução")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar evolução")

    dados = body.model_dump(exclude_unset=True)
    # Compatibilidade de nomes de campos vindos de versões antigas da tela.
    if dados.get("frequencia_cardiaca") is None and body.freq_cardiaca is not None:
        dados["frequencia_cardiaca"] = body.freq_cardiaca
    if dados.get("frequencia_respiratoria") is None and body.freq_respiratoria is not None:
        dados["frequencia_respiratoria"] = body.freq_respiratoria
    dados.pop("freq_cardiaca", None)
    dados.pop("freq_respiratoria", None)

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_evolucao,
        **dados,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/internacoes/{internacao_id}/procedimento", status_code=201)
def registrar_procedimento_internacao(
    internacao_id: int,
    body: ProcedimentoInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_registro = i.tenant_id or tenant_id
    if tenant_id_registro is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar procedimento")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar procedimento")

    status_procedimento = (body.status or "concluido").strip().lower()
    if status_procedimento not in {"agendado", "concluido"}:
        raise HTTPException(status_code=422, detail="Status do procedimento inválido. Use 'agendado' ou 'concluido'.")

    if status_procedimento == "concluido":
        if not (body.executado_por or "").strip():
            raise HTTPException(status_code=422, detail="Campo 'executado_por' é obrigatório para procedimento concluído")
        if not body.horario_execucao:
            raise HTTPException(status_code=422, detail="Campo 'horario_execucao' é obrigatório para procedimento concluído")

    horario_agendado = _normalizar_datetime_vet(body.horario_agendado)
    horario_execucao = _normalizar_datetime_vet(body.horario_execucao)
    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(status_code=422, detail="Quantidade prevista nÃ£o pode ser negativa")
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(status_code=422, detail="Quantidade executada nÃ£o pode ser negativa")
    if quantidade_desperdicio < 0:
        raise HTTPException(status_code=422, detail="Quantidade de desperdÃ­cio nÃ£o pode ser negativa")
    if status_procedimento == "concluido" and quantidade_executada is None and quantidade_prevista is not None:
        quantidade_executada = quantidade_prevista

    data_referencia = horario_agendado or horario_execucao or _vet_now()
    insumos = _enriquecer_insumos_com_custos(db, tenant_id_registro, body.insumos or []) if body.insumos else []

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_registro,
        data_hora=data_referencia,
        observacoes="",
    )
    db.add(ev)
    db.flush()

    estoque_baixado = False
    estoque_movimentacao_ids: list[int] = []
    if status_procedimento == "concluido" and insumos:
        insumos, estoque_movimentacao_ids = _aplicar_baixa_estoque_itens(
            db,
            tenant_id=tenant_id_registro,
            user_id=user_id,
            itens=insumos,
            motivo="procedimento_internacao",
            referencia_id=ev.id,
            referencia_tipo="procedimento_internacao",
            documento=str(internacao_id),
            observacao=f"Baixa automÃ¡tica da internaÃ§Ã£o #{internacao_id} - {body.medicamento}",
        )
        estoque_baixado = bool(estoque_movimentacao_ids)

    payload = {
        "status": status_procedimento,
        "tipo_registro": (body.tipo_registro or "procedimento").strip().lower() or "procedimento",
        "horario_agendado": horario_agendado.isoformat() if horario_agendado else None,
        "medicamento": body.medicamento,
        "dose": body.dose,
        "via": body.via,
        "quantidade_prevista": quantidade_prevista,
        "quantidade_executada": quantidade_executada,
        "quantidade_desperdicio": quantidade_desperdicio,
        "unidade_quantidade": (body.unidade_quantidade or "").strip() or None,
        "insumos": insumos,
        "estoque_baixado": estoque_baixado,
        "estoque_movimentacao_ids": estoque_movimentacao_ids,
        "observacoes_agenda": body.observacoes_agenda,
        "executado_por": (body.executado_por or "").strip() or None,
        "horario_execucao": horario_execucao.isoformat() if horario_execucao else None,
        "observacao_execucao": body.observacao_execucao,
    }

    ev.observacoes = _build_procedimento_observacao(payload)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "data_hora": _serializar_datetime_vet(ev.data_hora),
        "status": status_procedimento,
        **payload,
    }


@router.patch("/internacoes/{internacao_id}/alta")
def dar_alta(
    internacao_id: int,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    i = db.query(InternacaoVet).filter(
        InternacaoVet.id == internacao_id,
        InternacaoVet.tenant_id == tenant_id,
    ).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")
    i.status = "alta"
    i.data_saida = _vet_now()
    if observacoes:
        i.observacoes = observacoes
    db.commit()
    return {"ok": True, "status": "alta", "data_saida": _serializar_datetime_vet(i.data_saida)}


# ═══════════════════════════════════════════════════════════════
# PERFIL COMPORTAMENTAL
# ═══════════════════════════════════════════════════════════════

class PerfilComportamentalIn(BaseModel):
    temperamento: Optional[str] = None
    reacao_animais: Optional[str] = None
    reacao_pessoas: Optional[str] = None
    medo_secador: Optional[str] = None
    medo_tesoura: Optional[str] = None
    aceita_focinheira: Optional[str] = None
    comportamento_carro: Optional[str] = None
    observacoes: Optional[str] = None


@router.get("/pets/{pet_id}/perfil-comportamental")
def obter_perfil_comportamental(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()
    return perfil or {}


@router.put("/pets/{pet_id}/perfil-comportamental")
def salvar_perfil_comportamental(
    pet_id: int,
    body: PerfilComportamentalIn,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()

    if perfil:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(perfil, field, value)
    else:
        perfil = PerfilComportamental(
            pet_id=pet_id,
            user_id=user.id,
            **body.model_dump(),
        )
        db.add(perfil)

    db.commit()
    db.refresh(perfil)
    return perfil


# ═══════════════════════════════════════════════════════════════
# DASHBOARD VETERINÁRIO
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Resumo do dia para o dashboard veterinário."""
    _, tenant_id = _get_tenant(current)
    hoje = date.today()
    janela_30d = hoje - timedelta(days=30)

    agendamentos_hoje = db.query(func.count(AgendamentoVet.id)).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == hoje,
    ).scalar() or 0

    consultas_hoje = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) == hoje,
    ).scalar() or 0

    em_atendimento = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.status == "em_andamento",
    ).scalar() or 0

    internados = db.query(func.count(InternacaoVet.id)).filter(
        InternacaoVet.tenant_id == tenant_id,
        InternacaoVet.status == "internado",
    ).scalar() or 0

    vacinas_vencendo_30d = db.query(func.count(VacinaRegistro.id)).filter(
        VacinaRegistro.tenant_id == tenant_id,
        VacinaRegistro.data_proxima_dose != None,  # noqa
        VacinaRegistro.data_proxima_dose >= hoje,
        VacinaRegistro.data_proxima_dose <= hoje + timedelta(days=30),
    ).scalar() or 0

    consultas_mes = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.extract("month", ConsultaVet.created_at) == hoje.month,
        func.extract("year", ConsultaVet.created_at) == hoje.year,
    ).scalar() or 0

    consultas_com_retorno_vencido = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.data_retorno.isnot(None),
        ConsultaVet.data_retorno < hoje,
        ConsultaVet.status == "finalizada",
    ).all()

    retornos_pendentes = 0
    for consulta_base in consultas_com_retorno_vencido:
        existe_retorno = db.query(ConsultaVet.id).filter(
            ConsultaVet.tenant_id == tenant_id,
            ConsultaVet.pet_id == consulta_base.pet_id,
            ConsultaVet.tipo == "retorno",
            ConsultaVet.status != "cancelada",
            func.date(ConsultaVet.created_at) >= consulta_base.data_retorno,
        ).first()
        if not existe_retorno:
            retornos_pendentes += 1

    consultas_30d = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()

    total_30d = len(consultas_30d)
    retornos_30d = sum(1 for c in consultas_30d if (c.tipo or "").strip().lower() == "retorno")
    taxa_retorno_30d = round((retornos_30d / total_30d) * 100, 1) if total_30d else 0.0

    duracoes_min = []
    for consulta in consultas_30d:
        if consulta.inicio_atendimento and consulta.fim_atendimento:
            delta = consulta.fim_atendimento - consulta.inicio_atendimento
            duracoes_min.append(max(delta.total_seconds() / 60.0, 0))

    tempo_medio_atendimento_min = round(sum(duracoes_min) / len(duracoes_min), 1) if duracoes_min else 0.0
    procedimentos_30d = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    financeiro_30d = [_resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira) for procedimento in procedimentos_30d]
    faturamento_procedimentos_30d = _round_money(sum(item["valor_cobrado"] for item in financeiro_30d))
    custo_procedimentos_30d = _round_money(sum(item["custo_total"] for item in financeiro_30d))
    margem_procedimentos_30d = _round_money(sum(item["margem_valor"] for item in financeiro_30d))
    margem_percentual_procedimentos_30d = round((margem_procedimentos_30d / faturamento_procedimentos_30d) * 100, 2) if faturamento_procedimentos_30d > 0 else 0.0
    repasse_empresa_procedimentos_30d = _round_money(sum(item["repasse_empresa_valor"] for item in financeiro_30d))
    receita_tenant_procedimentos_30d = _round_money(sum(item["receita_tenant_valor"] for item in financeiro_30d))
    entrada_empresa_procedimentos_30d = _round_money(sum(item["entrada_empresa_valor"] for item in financeiro_30d))

    return {
        "consultas_hoje": consultas_hoje,
        "agendamentos_hoje": agendamentos_hoje,
        "em_atendimento": em_atendimento,
        "internados": internados,
        "vacinas_vencendo_30d": vacinas_vencendo_30d,
        "consultas_mes": consultas_mes,
        "retornos_pendentes": retornos_pendentes,
        "total_consultas_30d": total_30d,
        "retornos_30d": retornos_30d,
        "taxa_retorno_30d": taxa_retorno_30d,
        "tempo_medio_atendimento_min": tempo_medio_atendimento_min,
        "modelo_operacional_financeiro": regra_financeira["modo_operacional"],
        "comissao_empresa_pct_padrao": regra_financeira["comissao_empresa_pct"],
        "faturamento_procedimentos_30d": faturamento_procedimentos_30d,
        "custo_procedimentos_30d": custo_procedimentos_30d,
        "margem_procedimentos_30d": margem_procedimentos_30d,
        "margem_percentual_procedimentos_30d": margem_percentual_procedimentos_30d,
        "repasse_empresa_procedimentos_30d": repasse_empresa_procedimentos_30d,
        "receita_tenant_procedimentos_30d": receita_tenant_procedimentos_30d,
        "entrada_empresa_procedimentos_30d": entrada_empresa_procedimentos_30d,
    }


@router.get("/relatorios/clinicos")
def relatorio_clinico_vet(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    data_inicio = date.today() - timedelta(days=dias)

    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    total_consultas = len(consultas)
    consultas_finalizadas = sum(1 for c in consultas if (c.status or "").strip().lower() == "finalizada")

    diagnosticos_count = {}
    for consulta in consultas:
        diagnostico = (consulta.diagnostico or "").strip()
        if not diagnostico:
            continue
        chave = diagnostico.split("\n")[0].split(";")[0].strip()
        if not chave:
            continue
        diagnosticos_count[chave] = diagnosticos_count.get(chave, 0) + 1

    top_diagnosticos = [
        {"nome": nome, "quantidade": qtd}
        for nome, qtd in sorted(diagnosticos_count.items(), key=lambda item: item[1], reverse=True)[:top]
    ]

    procedimentos_periodo = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    procedimentos_resumo = {}
    total_procedimentos_valor = 0.0
    total_procedimentos_custo = 0.0
    total_procedimentos_margem = 0.0
    total_repasse_empresa = 0.0
    total_receita_tenant = 0.0
    total_entrada_empresa = 0.0
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    for procedimento in procedimentos_periodo:
        resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira)
        chave = (procedimento.nome or "Procedimento").strip() or "Procedimento"
        item = procedimentos_resumo.setdefault(chave, {
            "nome": chave,
            "quantidade": 0,
            "valor_total": 0.0,
            "custo_total": 0.0,
            "margem_total": 0.0,
            "repasse_empresa_total": 0.0,
            "receita_tenant_total": 0.0,
            "entrada_empresa_total": 0.0,
        })
        item["quantidade"] += 1
        item["valor_total"] += resumo["valor_cobrado"]
        item["custo_total"] += resumo["custo_total"]
        item["margem_total"] += resumo["margem_valor"]
        item["repasse_empresa_total"] += resumo["repasse_empresa_valor"]
        item["receita_tenant_total"] += resumo["receita_tenant_valor"]
        item["entrada_empresa_total"] += resumo["entrada_empresa_valor"]
        total_procedimentos_valor += resumo["valor_cobrado"]
        total_procedimentos_custo += resumo["custo_total"]
        total_procedimentos_margem += resumo["margem_valor"]
        total_repasse_empresa += resumo["repasse_empresa_valor"]
        total_receita_tenant += resumo["receita_tenant_valor"]
        total_entrada_empresa += resumo["entrada_empresa_valor"]

    top_procedimentos = [
        {
            "nome": item["nome"],
            "quantidade": int(item["quantidade"]),
            "valor_total": _round_money(item["valor_total"]),
            "custo_total": _round_money(item["custo_total"]),
            "margem_total": _round_money(item["margem_total"]),
            "repasse_empresa_total": _round_money(item["repasse_empresa_total"]),
            "receita_tenant_total": _round_money(item["receita_tenant_total"]),
            "entrada_empresa_total": _round_money(item["entrada_empresa_total"]),
            "margem_percentual": round((item["margem_total"] / item["valor_total"]) * 100, 2) if item["valor_total"] > 0 else 0.0,
        }
        for item in sorted(
            procedimentos_resumo.values(),
            key=lambda item: (item["quantidade"], item["valor_total"]),
            reverse=True,
        )[:top]
    ]

    top_medicamentos_db = (
        db.query(
            ItemPrescricao.nome_medicamento.label("nome"),
            func.count(ItemPrescricao.id).label("quantidade"),
        )
        .join(PrescricaoVet, PrescricaoVet.id == ItemPrescricao.prescricao_id)
        .filter(
            PrescricaoVet.tenant_id == tenant_id,
            func.date(PrescricaoVet.created_at) >= data_inicio,
        )
        .group_by(ItemPrescricao.nome_medicamento)
        .order_by(func.count(ItemPrescricao.id).desc())
        .limit(top)
        .all()
    )

    return {
        "periodo_dias": dias,
        "consultas": {
            "total": total_consultas,
            "finalizadas": consultas_finalizadas,
            "em_andamento": max(total_consultas - consultas_finalizadas, 0),
        },
        "financeiro_procedimentos": {
            "modo_operacional": regra_financeira["modo_operacional"],
            "comissao_empresa_pct": regra_financeira["comissao_empresa_pct"],
            "faturamento_total": _round_money(total_procedimentos_valor),
            "custo_total": _round_money(total_procedimentos_custo),
            "margem_total": _round_money(total_procedimentos_margem),
            "repasse_empresa_total": _round_money(total_repasse_empresa),
            "receita_tenant_total": _round_money(total_receita_tenant),
            "entrada_empresa_total": _round_money(total_entrada_empresa),
            "margem_percentual": round((total_procedimentos_margem / total_procedimentos_valor) * 100, 2) if total_procedimentos_valor > 0 else 0.0,
        },
        "top_diagnosticos": [
            {"nome": item["nome"], "quantidade": int(item["quantidade"])}
            for item in top_diagnosticos
        ],
        "top_procedimentos": top_procedimentos,
        "top_medicamentos": [
            {"nome": item.nome, "quantidade": int(item.quantidade)}
            for item in top_medicamentos_db
        ],
    }


@router.get("/relatorios/clinicos/export.csv")
def exportar_relatorio_clinico_csv(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    dados = relatorio_clinico_vet(dias=dias, top=top, db=db, current=current)
    conteudo = []
    conteudo.append(["Relatório clínico veterinário"])
    conteudo.append(["Período (dias)", str(dados["periodo_dias"])])
    conteudo.append(["Consultas totais", str(dados["consultas"]["total"])])
    conteudo.append(["Consultas finalizadas", str(dados["consultas"]["finalizadas"])])
    conteudo.append(["Consultas em andamento", str(dados["consultas"]["em_andamento"])])
    conteudo.append(["Faturamento procedimentos", f"{dados['financeiro_procedimentos']['faturamento_total']:.2f}"])
    conteudo.append(["Custo procedimentos", f"{dados['financeiro_procedimentos']['custo_total']:.2f}"])
    conteudo.append(["Margem procedimentos", f"{dados['financeiro_procedimentos']['margem_total']:.2f}"])
    conteudo.append(["Margem % procedimentos", f"{dados['financeiro_procedimentos']['margem_percentual']:.2f}"])
    conteudo.append(["Modo operacional", dados["financeiro_procedimentos"]["modo_operacional"]])
    conteudo.append(["Comissão empresa %", f"{dados['financeiro_procedimentos']['comissao_empresa_pct']:.2f}"])
    conteudo.append(["Entrada empresa", f"{dados['financeiro_procedimentos']['entrada_empresa_total']:.2f}"])
    conteudo.append(["Repasse empresa", f"{dados['financeiro_procedimentos']['repasse_empresa_total']:.2f}"])
    conteudo.append(["Receita líquida vet", f"{dados['financeiro_procedimentos']['receita_tenant_total']:.2f}"])
    conteudo.append([])
    conteudo.append(["Top diagnósticos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_diagnosticos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])
    conteudo.append([])
    conteudo.append(["Top procedimentos"])
    conteudo.append(["Nome", "Quantidade", "Faturamento", "Custo", "Margem", "Entrada empresa", "Repasse empresa", "Líquido vet", "Margem %"])
    for item in dados["top_procedimentos"]:
        conteudo.append([
            item["nome"],
            str(item["quantidade"]),
            f"{item['valor_total']:.2f}",
            f"{item['custo_total']:.2f}",
            f"{item['margem_total']:.2f}",
            f"{item['entrada_empresa_total']:.2f}",
            f"{item['repasse_empresa_total']:.2f}",
            f"{item['receita_tenant_total']:.2f}",
            f"{item['margem_percentual']:.2f}",
        ])
    conteudo.append([])
    conteudo.append(["Top medicamentos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_medicamentos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])

    sio = StringIO()
    writer = csv.writer(sio, delimiter=';')
    writer.writerows(conteudo)
    csv_string = "\ufeff" + sio.getvalue()

    return Response(
        content=csv_string,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=relatorio_clinico_vet_{dias}d.csv"},
    )


@router.get("/consultas/{consulta_id}/assinatura")
def validar_assinatura_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if not c.finalizado_em or not c.hash_prontuario:
        return {
            "assinada": False,
            "hash_valido": False,
            "hash_prontuario": c.hash_prontuario,
            "hash_recalculado": None,
            "finalizado_em": c.finalizado_em,
            "motivo": "Consulta ainda não foi finalizada e assinada digitalmente.",
        }

    hash_recalculado = _hash_prontuario_consulta(c)
    return {
        "assinada": True,
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
        "hash_recalculado": hash_recalculado,
        "finalizado_em": c.finalizado_em,
        "motivo": "OK" if hash_recalculado == c.hash_prontuario else "Hash divergente: possível alteração após finalização.",
    }


@router.get("/consultas/{consulta_id}/prontuario.pdf")
def baixar_prontuario_pdf(
    consulta_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = (
        db.query(ConsultaVet)
        .options(
            joinedload(ConsultaVet.pet),
            joinedload(ConsultaVet.cliente),
            joinedload(ConsultaVet.veterinario),
            joinedload(ConsultaVet.prescricoes).joinedload(PrescricaoVet.itens),
        )
        .filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    if c.status != "finalizada":
        raise HTTPException(status_code=400, detail="A consulta precisa estar finalizada para gerar o prontuário em PDF")

    hash_recalculado = _hash_prontuario_consulta(c)
    validacao = {
        "assinada": bool(c.finalizado_em and c.hash_prontuario),
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
    }
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_prontuario(c, validacao, c.prescricoes or [], url_validacao)

    filename = f"prontuario_consulta_{consulta_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/prescricoes/{prescricao_id}/pdf")
def baixar_prescricao_pdf(
    prescricao_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    p = _prescricao_or_404(db, prescricao_id, tenant_id)
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{p.consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_receita(p, url_validacao)

    numero = (p.numero or f"prescricao_{p.id}").replace("/", "-")
    filename = f"{numero}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════
# PARCEIRO VETERINÁRIO (MULTI-TENANT)
# ═══════════════════════════════════════════════════════════════


class PartnerLinkCreate(BaseModel):
    vet_tenant_id: str  # UUID do tenant do veterinário parceiro
    tipo_relacao: str = "parceiro"  # 'parceiro' | 'funcionario'
    comissao_empresa_pct: Optional[float] = None


class PartnerLinkUpdate(BaseModel):
    tipo_relacao: Optional[str] = None
    comissao_empresa_pct: Optional[float] = None
    ativo: Optional[bool] = None


class PartnerLinkResponse(BaseModel):
    id: int
    empresa_tenant_id: str
    vet_tenant_id: str
    tipo_relacao: str
    comissao_empresa_pct: Optional[float]
    ativo: bool
    criado_em: datetime
    # campos extras enriquecidos
    vet_tenant_nome: Optional[str] = None
    empresa_tenant_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/parceiros", response_model=List[PartnerLinkResponse], summary="Lista parcerias do tenant atual")
def listar_parceiros(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Retorna todos os vínculos de parceria em que o tenant atual é a empresa (loja)."""
    user, tenant_id = _get_tenant(current)
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).all()

    result = []
    for link in links:
        vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
        result.append(
            PartnerLinkResponse(
                id=link.id,
                empresa_tenant_id=str(link.empresa_tenant_id),
                vet_tenant_id=str(link.vet_tenant_id),
                tipo_relacao=link.tipo_relacao,
                comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
                ativo=link.ativo,
                criado_em=link.criado_em,
                vet_tenant_nome=vet_tenant.name if vet_tenant else None,
            )
        )
    return result


@router.post("/parceiros", response_model=PartnerLinkResponse, status_code=201, summary="Cria vínculo com veterinário parceiro")
def criar_parceiro(
    payload: PartnerLinkCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Cria um vínculo de parceria entre o tenant atual (loja) e um tenant veterinário."""
    user, tenant_id = _get_tenant(current)

    # Verifica se o tenant de destino existe
    vet_tenant = db.query(Tenant).filter(Tenant.id == payload.vet_tenant_id).first()
    if not vet_tenant:
        raise HTTPException(status_code=404, detail="Tenant do veterinário não encontrado.")

    # Impede vínculo consigo mesmo
    if str(payload.vet_tenant_id) == str(tenant_id):
        raise HTTPException(status_code=400, detail="O tenant parceiro não pode ser o mesmo tenant atual.")

    # Impede duplicata
    existente = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
        VetPartnerLink.vet_tenant_id == payload.vet_tenant_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um vínculo com este veterinário parceiro.")

    link = VetPartnerLink(
        empresa_tenant_id=str(tenant_id),
        vet_tenant_id=payload.vet_tenant_id,
        tipo_relacao=payload.tipo_relacao,
        comissao_empresa_pct=payload.comissao_empresa_pct,
        ativo=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name,
    )


@router.patch("/parceiros/{link_id}", response_model=PartnerLinkResponse, summary="Atualiza vínculo de parceria")
def atualizar_parceiro(
    link_id: int,
    payload: PartnerLinkUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")

    if payload.tipo_relacao is not None:
        link.tipo_relacao = payload.tipo_relacao
    if payload.comissao_empresa_pct is not None:
        link.comissao_empresa_pct = payload.comissao_empresa_pct
    if payload.ativo is not None:
        link.ativo = payload.ativo

    db.commit()
    db.refresh(link)

    vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name if vet_tenant else None,
    )


@router.delete("/parceiros/{link_id}", status_code=204, summary="Remove vínculo de parceria")
def remover_parceiro(
    link_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")
    db.delete(link)
    db.commit()


@router.get("/tenants-veterinarios", summary="Lista tenants com tipo veterinary_clinic")
def listar_tenants_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista tenants que podem ser vinculados como parceiros (veterinary_clinic)."""
    _get_tenant(current)
    tenants = db.query(Tenant).filter(
        Tenant.organization_type == "veterinary_clinic",
        Tenant.status == "active",
    ).all()
    return [{"id": str(t.id), "nome": t.name, "cnpj": t.cnpj} for t in tenants]


# ═══════════════════════════════════════════════════════════════
# RELATÓRIO DE REPASSE — fechamento operacional parceiro
# ═══════════════════════════════════════════════════════════════

@router.get("/relatorios/repasse", summary="Relatório de repasse veterinário por período")
def relatorio_repasse(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as contas a receber geradas por procedimentos veterinários
    (documento começando com VET-PROC-), filtrando por período e status.
    Útil para fechar o repasse com o veterinário parceiro.
    """
    user, tenant_id = _get_tenant(current)

    query = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    )

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)
    if status:
        query = query.filter(ContaReceber.status == status)

    contas = query.order_by(ContaReceber.data_emissao.desc()).all()

    items = []
    total_valor = 0.0
    total_recebido = 0.0
    total_pendente = 0.0

    for c in contas:
        tipo = "repasse_empresa" if "-REPASSE-EMPRESA" in (c.documento or "") else "liquido_vet"
        valor = float(c.valor_final or 0)
        recebido = float(c.valor_recebido or 0)
        pendente = valor - recebido if c.status != "recebido" else 0.0

        total_valor += valor
        total_recebido += recebido if c.status == "recebido" else 0.0
        total_pendente += pendente

        items.append({
            "id": c.id,
            "documento": c.documento,
            "descricao": c.descricao,
            "tipo": tipo,
            "valor": valor,
            "valor_recebido": recebido,
            "data_emissao": c.data_emissao.isoformat() if c.data_emissao else None,
            "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
            "data_recebimento": c.data_recebimento.isoformat() if c.data_recebimento else None,
            "status": c.status,
            "observacoes": c.observacoes,
        })

    return {
        "items": items,
        "total_valor": _round_money(total_valor),
        "total_recebido": _round_money(total_recebido),
        "total_pendente": _round_money(total_pendente),
        "quantidade": len(items),
    }


@router.post("/relatorios/repasse/{conta_id}/baixar", summary="Dá baixa (recebimento) em um lançamento de repasse")
def baixar_repasse(
    conta_id: int,
    data_recebimento: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Marca um lançamento de repasse veterinário como recebido.
    Atualiza status='recebido', valor_recebido=valor_final e data_recebimento.
    """
    user, tenant_id = _get_tenant(current)

    conta = db.query(ContaReceber).filter(
        ContaReceber.id == conta_id,
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    ).first()

    if not conta:
        raise HTTPException(404, "Lançamento de repasse não encontrado.")
    if conta.status == "recebido":
        raise HTTPException(400, "Este lançamento já foi baixado.")

    conta.status = "recebido"
    conta.valor_recebido = conta.valor_final
    conta.data_recebimento = data_recebimento or date.today()
    db.commit()

    return {
        "ok": True,
        "id": conta.id,
        "status": conta.status,
        "data_recebimento": conta.data_recebimento.isoformat(),
        "valor_recebido": float(conta.valor_recebido),
    }


# ═══════════════════════════════════════════════════════════════
# CHAT IA — interpretação clínica conversacional de exames
# ═══════════════════════════════════════════════════════════════

class ExameChatPayload(BaseModel):
    pergunta: str


class VetAssistenteIAPayload(BaseModel):
    mensagem: str
    modo: str = "livre"  # livre | atendimento
    conversa_id: Optional[int] = None
    salvar_historico: bool = True
    pet_id: Optional[int] = None
    consulta_id: Optional[int] = None
    exame_id: Optional[int] = None
    medicamento_1: Optional[str] = None
    medicamento_2: Optional[str] = None
    peso_kg: Optional[float] = None
    especie: Optional[str] = None


class VetMensagemFeedbackPayload(BaseModel):
    util: bool
    nota: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = None


def _normalizar_texto(v: Optional[str]) -> str:
    return (v or "").strip().lower()


def _detectar_medicamentos_no_texto(texto: str, meds: list[MedicamentoCatalogo]) -> list[MedicamentoCatalogo]:
    encontrados: list[MedicamentoCatalogo] = []
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (nome and nome in texto) or (nome_comercial and nome_comercial in texto) or (principio and principio in texto):
            encontrados.append(med)
        if len(encontrados) >= 2:
            break
    return encontrados


def _normalizar_modo_ia(modo: Optional[str]) -> str:
    modo_limpo = (modo or "livre").strip().lower()
    return modo_limpo if modo_limpo in ["livre", "atendimento"] else "livre"


def _garantir_tabelas_memoria_ia(db: Session) -> dict:
    """
    Garante que as tabelas de memória usadas pela IA existam.
    Evita falha silenciosa de histórico em ambientes sem migração aplicada.
    """
    bind = db.get_bind()
    insp = inspect(bind)
    criadas = []

    if not insp.has_table("conversas_ia"):
        Conversa.__table__.create(bind=bind, checkfirst=True)
        criadas.append("conversas_ia")

    if not insp.has_table("mensagens_chat"):
        MensagemChat.__table__.create(bind=bind, checkfirst=True)
        criadas.append("mensagens_chat")

    return {"ok": True, "criadas": criadas}


def _carregar_memoria_conversa(db: Session, tenant_id, conversa_id: int, limite: int = 8) -> list[MensagemChat]:
    return db.query(MensagemChat).filter(
        MensagemChat.tenant_id == str(tenant_id),
        MensagemChat.conversa_id == conversa_id,
    ).order_by(MensagemChat.id.desc()).limit(limite).all()[::-1]


def _obter_ou_criar_conversa_vet(
    db: Session,
    tenant_id,
    user_id: int,
    payload: VetAssistenteIAPayload,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Conversa:
    if payload.conversa_id:
        conversa = db.query(Conversa).filter(
            Conversa.id == payload.conversa_id,
            Conversa.tenant_id == str(tenant_id),
            Conversa.usuario_id == user_id,
        ).first()
        if conversa:
            return conversa

    modo = _normalizar_modo_ia(payload.modo)
    if pet:
        titulo = f"Vet {modo} - {pet.nome}"
    elif consulta:
        titulo = f"Vet {modo} - Consulta {consulta.id}"
    elif exame:
        titulo = f"Vet {modo} - Exame {exame.id}"
    else:
        titulo = f"Vet {modo} - {datetime.now().strftime('%d/%m %H:%M')}"

    conversa = Conversa(
        tenant_id=str(tenant_id),
        usuario_id=user_id,
        titulo=titulo,
        finalizada=False,
    )
    db.add(conversa)
    db.flush()
    return conversa


def _resumo_contexto_clinico(
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> str:
    blocos = []
    if pet:
        blocos.append(
            f"Paciente: {pet.nome} | espécie: {pet.especie or 'não informada'} | raça: {pet.raca or 'n/i'}"
        )
    if consulta:
        blocos.append(
            "Consulta atual: "
            f"queixa={consulta.queixa_principal or 'n/i'}; "
            f"história={consulta.historia_clinica or 'n/i'}; "
            f"exame físico={consulta.exame_fisico or 'n/i'}; "
            f"diagnóstico={consulta.diagnostico or consulta.hipotese_diagnostica or 'n/i'}"
        )
    if exame:
        data_ref = exame.data_resultado.isoformat() if exame.data_resultado else "n/i"
        blocos.append(
            "Exame selecionado: "
            f"{exame.nome or exame.tipo} | data={data_ref} | "
            f"resumo ia={exame.interpretacao_ia_resumo or 'n/i'}"
        )
    return "\n".join(blocos).strip()


def _montar_resposta_dose(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    peso_kg: Optional[float],
    especie: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(k in texto for k in ["dose", "dosagem", "mg/kg", "posologia"]):
        return None

    if not peso_kg or peso_kg <= 0:
        return "Para calcular dose com segurança, informe o peso atual do pet em kg."

    if not especie:
        return "Para cálculo de dose com segurança, informe também a espécie do pet (cão, gato, etc.)."

    med_match = None
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (nome and nome in texto) or (nome_comercial and nome_comercial in texto) or (principio and principio in texto):
            med_match = med
            break

    if not med_match:
        return "Não identifiquei o medicamento na pergunta. Informe o nome (ou princípio ativo) para calcular a dose."

    dose_min = med_match.dose_min_mgkg
    dose_max = med_match.dose_max_mgkg
    if dose_min is None and dose_max is None:
        return (
            f"Encontrei {med_match.nome}, mas ele não tem dose mg/kg cadastrada no catálogo. "
            "Verifique a bula/protocolo antes de prescrever."
        )

    dose_ref = dose_min if dose_min is not None else dose_max
    dose_max_ref = dose_max if dose_max is not None else dose_min

    total_min = float(dose_ref) * float(peso_kg)
    total_max = float(dose_max_ref) * float(peso_kg)
    total_media = (total_min + total_max) / 2

    if abs(total_min - total_max) < 1e-9:
        faixa = f"{total_min:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} mg/kg"
    else:
        faixa = f"{total_min:.2f} mg a {total_max:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} a {dose_max_ref:.2f} mg/kg"

    return (
        f"Dose de referência para {med_match.nome} (peso {peso_kg:.2f} kg): {faixa_mgkg}. "
        f"Total estimado: {faixa} (média {total_media:.2f} mg). "
        "Confirme frequência, via e duração conforme bula e condição clínica. "
        "Se houver comorbidade renal/hepática, considere ajuste de dose."
    )


def _montar_resposta_interacao(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    medicamento_1: Optional[str],
    medicamento_2: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(k in texto for k in ["associar", "junto", "intera", "combinar", "pode usar com"]):
        return None

    med_a = None
    med_b = None
    m1 = _normalizar_texto(medicamento_1)
    m2 = _normalizar_texto(medicamento_2)

    if m1 and m2:
        for med in meds:
            nome = _normalizar_texto(med.nome)
            nome_comercial = _normalizar_texto(med.nome_comercial)
            principio = _normalizar_texto(med.principio_ativo)
            if not med_a and (m1 == nome or m1 == nome_comercial or m1 == principio or m1 in nome):
                med_a = med
            if not med_b and (m2 == nome or m2 == nome_comercial or m2 == principio or m2 in nome):
                med_b = med
    else:
        encontrados = _detectar_medicamentos_no_texto(texto, meds)
        if len(encontrados) >= 2:
            med_a, med_b = encontrados[0], encontrados[1]

    if not med_a or not med_b:
        return "Para avaliar associação medicamentosa, informe dois medicamentos (nome ou princípio ativo)."

    principio_a = _normalizar_texto(med_a.principio_ativo)
    principio_b = _normalizar_texto(med_b.principio_ativo)

    if principio_a and principio_b and principio_a == principio_b:
        return (
            f"Atenção: {med_a.nome} e {med_b.nome} parecem ter o mesmo princípio ativo ({med_a.principio_ativo}). "
            "Há risco de duplicidade terapêutica e aumento de efeitos adversos."
        )

    riscos = []
    texto_interacoes = f"{_normalizar_texto(med_a.interacoes)} {_normalizar_texto(med_b.interacoes)}"
    if principio_a and principio_a in texto_interacoes:
        riscos.append(f"{med_b.nome} cita interação relevante com o princípio {med_a.principio_ativo}.")
    if principio_b and principio_b in texto_interacoes:
        riscos.append(f"{med_a.nome} cita interação relevante com o princípio {med_b.principio_ativo}.")

    if riscos:
        return (
            f"Associação {med_a.nome} + {med_b.nome}: encontrada possível interação em catálogo. "
            + " ".join(riscos)
            + " Avalie ajuste de dose, intervalo e monitoramento clínico."
        )

    return (
        f"Não encontrei alerta explícito de interação entre {med_a.nome} e {med_b.nome} no catálogo local. "
        "Mesmo assim, confirme em bula e considere função renal/hepática, idade e comorbidades antes de associar."
    )


def _montar_resposta_sintomas(mensagem: str, especie: Optional[str]) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = ["sintoma", "possibilidade", "diagnóstico", "hipótese", "o que olhar", "investigar"]
    if not any(k in texto for k in gatilhos):
        return None

    mapa = {
        "vomit": ["gastroenterite", "ingestão alimentar inadequada", "pancreatite", "corpo estranho"],
        "diarre": ["parasitoses", "gastroenterite", "disbiose", "doença inflamatória intestinal"],
        "tosse": ["traqueobronquite", "colapso de traqueia", "cardiopatia", "pneumonia"],
        "febre": ["processo infeccioso", "inflamação sistêmica", "doença transmitida por vetor"],
        "apat": ["dor", "infecção", "anemia", "distúrbio metabólico"],
        "prur": ["dermatite alérgica", "ectoparasitas", "infecção cutânea secundária"],
        "poliuria": ["doença renal", "diabetes mellitus", "hiperadrenocorticismo"],
        "convuls": ["epilepsia", "distúrbio metabólico", "intoxicação", "doença intracraniana"],
    }

    hipoteses = []
    for chave, possibilidades in mapa.items():
        if chave in texto:
            hipoteses.extend(possibilidades)

    if not hipoteses:
        hipoteses = [
            "processo infeccioso",
            "dor/condição inflamatória",
            "distúrbio metabólico/endócrino",
            "causa gastrointestinal",
        ]

    especie_txt = (especie or "não informada").strip()
    hipoteses_unicas = []
    for h in hipoteses:
        if h not in hipoteses_unicas:
            hipoteses_unicas.append(h)

    principais = ", ".join(hipoteses_unicas[:5])
    return (
        f"Pelas informações citadas ({especie_txt}), as principais hipóteses iniciais incluem: {principais}. "
        "Para fechar diagnóstico, recomendo revisar sinais vitais completos, dor, hidratação, evolução temporal, "
        "histórico medicamentoso e exames complementares dirigidos (hemograma, bioquímica e imagem conforme achados)."
    )


def _montar_resposta_plano_estruturado(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = ["plano", "conduta", "fechar diagnóstico", "fechar diagnostico", "o que fazer agora"]
    if not any(k in texto for k in gatilhos):
        return None

    contexto = _resumo_contexto_clinico(pet, consulta, exame)
    if not contexto:
        return (
            "Plano sugerido (estrutura mínima):\n"
            "1) Estabilização e dor: confirmar sinais vitais e escala de dor.\n"
            "2) Diagnóstico direcionado: hemograma + bioquímica + exame complementar conforme sistema acometido.\n"
            "3) Terapêutica inicial: suporte e monitorização de resposta em 24-48h.\n"
            "4) Reavaliação: definir critério de melhora/piora e retorno programado."
        )

    return (
        "Plano clínico estruturado com base no contexto atual:\n"
        "1) Hipóteses priorizadas: usar queixa + exame físico + exame complementar para ranquear hipóteses.\n"
        "2) Exames de confirmação: escolher exames com maior impacto para diferenciar as principais hipóteses.\n"
        "3) Conduta imediata: suporte, analgesia e hidratação conforme estado clínico.\n"
        "4) Segurança medicamentosa: revisar dose por espécie/peso e risco de interação.\n"
        "5) Follow-up: registrar sinais de alarme e prazo de reavaliação.\n"
        f"Resumo de contexto utilizado:\n{contexto}"
    )


def _montar_prompt_vet_llm(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
) -> tuple[str, str]:
    especie_txt = (especie or "não informada").strip()
    peso_txt = f"{float(peso_kg):.2f} kg" if peso_kg and peso_kg > 0 else "não informado"

    meds_preview = []
    for med in meds[:20]:
        partes = [med.nome]
        if med.principio_ativo:
            partes.append(f"princípio: {med.principio_ativo}")
        if med.dose_min_mgkg is not None or med.dose_max_mgkg is not None:
            dmin = med.dose_min_mgkg if med.dose_min_mgkg is not None else med.dose_max_mgkg
            dmax = med.dose_max_mgkg if med.dose_max_mgkg is not None else med.dose_min_mgkg
            partes.append(f"dose mg/kg: {dmin} a {dmax}")
        meds_preview.append(" | ".join(partes))

    contexto_clinico = _resumo_contexto_clinico(pet, consulta, exame) or "Sem contexto clínico detalhado."

    prompt_system = (
        "Você é um assistente clínico veterinário para apoio à decisão. "
        "Responda em português do Brasil, direto e claro. "
        "Não invente dados. Não substitua consulta veterinária. "
        "Sempre inclua orientação de segurança quando houver dose, interação medicamentosa ou risco clínico.\n\n"
        "REGRAS:\n"
        "1) Se faltar dado crítico (peso, espécie, medicamento), peça esse dado antes de concluir.\n"
        "2) Em dose, informe faixa e recomende confirmar bula/protocolo.\n"
        "3) Em interação, sinalize incerteza quando não houver dado explícito.\n"
        "4) Evite diagnóstico definitivo; forneça hipóteses e próximos passos.\n"
        "5) Seja objetivo (preferir até 8 linhas, exceto quando pedirem plano detalhado).\n\n"
        f"MODO: {_normalizar_modo_ia(modo)}\n"
        f"ESPÉCIE: {especie_txt}\n"
        f"PESO: {peso_txt}\n"
        f"CONTEXTO CLÍNICO:\n{contexto_clinico}\n\n"
        "CATÁLOGO RESUMIDO DE MEDICAMENTOS (amostra):\n"
        f"{chr(10).join(meds_preview) if meds_preview else 'Sem medicamentos ativos no catálogo.'}"
    )

    prompt_user = f"Pergunta do veterinário: {mensagem}"
    return prompt_system, prompt_user


def _tentar_resposta_llm_veterinaria(
    mensagem: str,
    memoria: list[MensagemChat],
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not (groq_key or openai_key or gemini_key):
        return None, None

    prompt_system, prompt_user = _montar_prompt_vet_llm(
        mensagem=mensagem,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=modo,
    )

    mensagens = [{"role": "system", "content": prompt_system}]
    for m in memoria[-6:]:
        conteudo = (m.conteudo or "").strip()
        if not conteudo:
            continue
        role = "assistant" if m.tipo == "assistente" else "user"
        mensagens.append({"role": role, "content": conteudo[:3000]})
    mensagens.append({"role": "user", "content": prompt_user})

    try:
        if groq_key:
            from groq import Groq

            client_ia = Groq(api_key=groq_key)
            completion = client_ia.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensagens,
                temperature=0.2,
                max_tokens=600,
            )
            resposta = (completion.choices[0].message.content or "").strip()
            return (resposta or None), "groq:llama-3.3-70b-versatile"

        if openai_key:
            from openai import OpenAI

            client_ia = OpenAI(api_key=openai_key, timeout=25.0)
            completion = client_ia.chat.completions.create(
                model="gpt-4o-mini",
                messages=mensagens,
                temperature=0.2,
                max_tokens=600,
            )
            resposta = (completion.choices[0].message.content or "").strip()
            return (resposta or None), "openai:gpt-4o-mini"

        if gemini_key:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model_ia = genai.GenerativeModel("gemini-1.5-flash")
            historico_txt = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in mensagens if msg["role"] != "system"]
            )
            prompt_completo = f"{prompt_system}\n\n{historico_txt}"
            response = model_ia.generate_content(prompt_completo)
            resposta = (getattr(response, "text", "") or "").strip()
            return (resposta or None), "gemini:gemini-1.5-flash"

    except Exception:
        return None, None

    return None, None


@router.post("/ia/assistente", summary="Assistente IA veterinário (livre ou vinculado ao atendimento)")
def assistente_ia_veterinario(
    payload: VetAssistenteIAPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    mensagem = (payload.mensagem or "").strip()
    if not mensagem:
        raise HTTPException(422, "Informe uma mensagem para o assistente.")

    pet = None
    consulta = None
    exame = None

    if payload.pet_id:
        pet = db.query(Pet).filter(Pet.id == payload.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.consulta_id:
        consulta = db.query(ConsultaVet).filter(
            ConsultaVet.id == payload.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if consulta and not pet:
            pet = db.query(Pet).filter(Pet.id == consulta.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.exame_id:
        exame = db.query(ExameVet).filter(
            ExameVet.id == payload.exame_id,
            ExameVet.tenant_id == tenant_id,
        ).first()
        if exame and not pet:
            pet = db.query(Pet).filter(Pet.id == exame.pet_id, Pet.tenant_id == tenant_id).first()

    especie = payload.especie or (pet.especie if pet else None)
    peso_kg = payload.peso_kg
    if (not peso_kg or peso_kg <= 0) and pet and getattr(pet, "peso", None):
        try:
            peso_kg = float(pet.peso)
        except Exception:
            peso_kg = None
    if (not peso_kg or peso_kg <= 0) and consulta and getattr(consulta, "peso_consulta", None):
        try:
            peso_kg = float(consulta.peso_consulta)
        except Exception:
            peso_kg = None

    meds = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).order_by(MedicamentoCatalogo.nome).limit(200).all()

    conversa = None
    memoria = []
    contexto_memoria = ""
    historico_salvo = False
    modelo_usado = "vet-regra"
    if payload.salvar_historico:
        try:
            _garantir_tabelas_memoria_ia(db)
            conversa = _obter_ou_criar_conversa_vet(
                db=db,
                tenant_id=tenant_id,
                user_id=user.id,
                payload=payload,
                pet=pet,
                consulta=consulta,
                exame=exame,
            )
            memoria = _carregar_memoria_conversa(db, tenant_id, conversa.id, limite=8)
            memoria_usuario = [m.conteudo for m in memoria if m.tipo == "usuario"]
            contexto_memoria = " | ".join(memoria_usuario[-2:]).strip()
        except Exception:
            db.rollback()
            conversa = None
            memoria = []
            contexto_memoria = ""

    mensagem_analise = mensagem
    if contexto_memoria:
        mensagem_analise = f"{mensagem} {contexto_memoria}"

    resposta_llm, modelo_llm = _tentar_resposta_llm_veterinaria(
        mensagem=mensagem,
        memoria=memoria,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=payload.modo,
    )

    if resposta_llm:
        resposta_final = resposta_llm
        modelo_usado = modelo_llm or "vet-llm"
    else:
        respostas = []

        if exame:
            respostas.append(
                _responder_chat_exame(
                    pergunta=mensagem_analise.lower(),
                    exame_nome=exame.nome,
                    tipo_exame=exame.tipo,
                    especie=(pet.especie if pet else "não informada"),
                    nome_pet=(pet.nome if pet else "paciente"),
                    alergias=(getattr(pet, "alergias_lista", None) or []),
                    alertas=(exame.interpretacao_ia_alertas or []),
                    resumo_ia=(exame.interpretacao_ia_resumo or ""),
                    conclusao_ia=(exame.interpretacao_ia or ""),
                    dados_json=(exame.resultado_json or {}),
                    texto_resultado=(exame.resultado_texto or ""),
                )
            )

        resp_dose = _montar_resposta_dose(mensagem_analise, meds, peso_kg, especie)
        if resp_dose:
            respostas.append(resp_dose)

        resp_interacao = _montar_resposta_interacao(
            mensagem_analise,
            meds,
            payload.medicamento_1,
            payload.medicamento_2,
        )
        if resp_interacao:
            respostas.append(resp_interacao)

        resp_sintomas = _montar_resposta_sintomas(mensagem_analise, especie)
        if resp_sintomas:
            respostas.append(resp_sintomas)

        resp_plano = _montar_resposta_plano_estruturado(mensagem_analise, pet, consulta, exame)
        if resp_plano:
            respostas.append(resp_plano)

        if not respostas:
            contexto = []
            if pet:
                contexto.append(f"pet: {pet.nome}")
            if especie:
                contexto.append(f"espécie: {especie}")
            if peso_kg:
                contexto.append(f"peso: {peso_kg:.2f} kg")
            contexto_txt = " | ".join(contexto) if contexto else "sem contexto clínico selecionado"

            respostas.append(
                "Posso te ajudar com: cálculo de dose por mg/kg, avaliação de associação medicamentosa, "
                "hipóteses por sintomas e checklist para fechamento diagnóstico. "
                f"Contexto atual: {contexto_txt}."
            )

        resposta_final = "\n\n".join(respostas)

    resposta_final += (
        "\n\nAviso clínico: resposta de apoio à decisão. "
        "Sempre confirmar conduta final com exame físico, histórico completo e protocolos da clínica."
    )

    contexto_msg = {
        "modulo": "vet",
        "modo": _normalizar_modo_ia(payload.modo),
        "pet_id": pet.id if pet else None,
        "consulta_id": consulta.id if consulta else None,
        "exame_id": exame.id if exame else None,
        "peso_kg": peso_kg,
        "especie": especie,
    }

    if payload.salvar_historico and conversa:
        try:
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="usuario",
                conteudo=mensagem,
                modelo_usado=modelo_usado,
                contexto_usado=contexto_msg,
            ))
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="assistente",
                conteudo=resposta_final,
                modelo_usado=modelo_usado,
                contexto_usado={**contexto_msg, "feedback": None},
            ))
            conversa.atualizado_em = datetime.utcnow()
            db.commit()
            historico_salvo = True
        except Exception:
            db.rollback()
            historico_salvo = False

    return {
        "resposta": resposta_final,
        "conversa_id": conversa.id if conversa else payload.conversa_id,
        "historico_salvo": historico_salvo,
        "contexto": {
            "modo": payload.modo,
            "pet_id": pet.id if pet else None,
            "pet_nome": pet.nome if pet else None,
            "consulta_id": consulta.id if consulta else None,
            "exame_id": exame.id if exame else None,
            "peso_kg": peso_kg,
            "especie": especie,
        },
    }


@router.get("/ia/conversas", summary="Lista conversas do assistente IA veterinário")
def listar_conversas_assistente_vet(
    limit: int = Query(20, ge=1, le=100),
    pet_id: Optional[int] = Query(None),
    consulta_id: Optional[int] = Query(None),
    exame_id: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversas = db.query(Conversa).filter(
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).order_by(Conversa.atualizado_em.desc(), Conversa.id.desc()).limit(limit).all()

    itens = []
    for conversa in conversas:
        mensagens = db.query(MensagemChat).filter(
            MensagemChat.tenant_id == str(tenant_id),
            MensagemChat.conversa_id == conversa.id,
        ).order_by(MensagemChat.id.asc()).all()

        if not mensagens:
            continue

        mensagens_vet = [m for m in mensagens if isinstance(m.contexto_usado, dict) and m.contexto_usado.get("modulo") == "vet"]
        if not mensagens_vet:
            continue

        ultima = mensagens[-1]
        contexto_base = next((m.contexto_usado for m in mensagens_vet if isinstance(m.contexto_usado, dict)), {}) or {}

        if pet_id and int(contexto_base.get("pet_id") or 0) != int(pet_id):
            continue
        if consulta_id and int(contexto_base.get("consulta_id") or 0) != int(consulta_id):
            continue
        if exame_id and int(contexto_base.get("exame_id") or 0) != int(exame_id):
            continue

        itens.append({
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
            "ultima_mensagem": (ultima.conteudo or "")[:180],
            "contexto": {
                "modo": contexto_base.get("modo"),
                "pet_id": contexto_base.get("pet_id"),
                "consulta_id": contexto_base.get("consulta_id"),
                "exame_id": contexto_base.get("exame_id"),
            },
        })

    return {"items": itens}


@router.get("/ia/conversas/{conversa_id}/mensagens", summary="Lista mensagens de uma conversa IA veterinária")
def listar_mensagens_conversa_assistente_vet(
    conversa_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada.")

    mensagens = db.query(MensagemChat).filter(
        MensagemChat.tenant_id == str(tenant_id),
        MensagemChat.conversa_id == conversa_id,
    ).order_by(MensagemChat.id.asc()).all()

    itens = []
    for msg in mensagens:
        contexto = msg.contexto_usado if isinstance(msg.contexto_usado, dict) else {}
        if contexto.get("modulo") != "vet":
            continue
        itens.append({
            "id": msg.id,
            "tipo": msg.tipo,
            "conteudo": msg.conteudo,
            "criado_em": msg.criado_em.isoformat() if msg.criado_em else None,
            "feedback": contexto.get("feedback"),
        })

    return {
        "conversa": {
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
        },
        "items": itens,
    }


@router.post("/ia/mensagens/{mensagem_id}/feedback", summary="Registra feedback da resposta da IA veterinária")
def registrar_feedback_mensagem_assistente_vet(
    mensagem_id: int,
    payload: VetMensagemFeedbackPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    mensagem = db.query(MensagemChat).join(
        Conversa, Conversa.id == MensagemChat.conversa_id
    ).filter(
        MensagemChat.id == mensagem_id,
        MensagemChat.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not mensagem:
        raise HTTPException(404, "Mensagem não encontrada.")
    if mensagem.tipo != "assistente":
        raise HTTPException(400, "Feedback só pode ser registrado em respostas da IA.")

    contexto = mensagem.contexto_usado if isinstance(mensagem.contexto_usado, dict) else {}
    if contexto.get("modulo") != "vet":
        raise HTTPException(400, "Mensagem não pertence ao assistente veterinário.")

    contexto["feedback"] = {
        "util": bool(payload.util),
        "nota": payload.nota,
        "comentario": (payload.comentario or "").strip() or None,
        "avaliado_em": datetime.utcnow().isoformat(),
        "avaliado_por": user.id,
    }
    mensagem.contexto_usado = contexto
    db.commit()

    return {"ok": True, "mensagem_id": mensagem.id, "feedback": contexto["feedback"]}


@router.get("/ia/memoria-status", summary="Verifica e prepara tabelas de memória da IA veterinária")
def memoria_status_assistente_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, _tenant_id = _get_tenant(current)
    status_memoria = _garantir_tabelas_memoria_ia(db)
    return status_memoria


@router.post("/exames/{exame_id}/chat", summary="Chat clínico conversacional sobre um exame")
def chat_exame_ia(
    exame_id: int,
    payload: ExameChatPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Responde perguntas clínicas sobre um exame específico, usando o resultado,
    a interpretação existente e o histórico básico do paciente como contexto.
    """
    user, tenant_id = _get_tenant(current)

    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")

    if exame.arquivo_url and not exame.resultado_texto and not exame.resultado_json:
        try:
            exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
            db.commit()
            db.refresh(exame)
        except HTTPException:
            pass

    pet = db.query(Pet).filter(Pet.id == exame.pet_id).first()
    pergunta = (payload.pergunta or "").strip().lower()

    # Monta contexto clínico do paciente
    especie = (pet.especie or "não informada") if pet else "não informada"
    nome_pet = pet.nome if pet else "paciente"
    alergias = []
    if pet:
        al = pet.alergias_lista or pet.alergias
        if isinstance(al, list):
            alergias = al
        elif isinstance(al, str) and al.strip():
            alergias = [al]

    alertas_exame = exame.interpretacao_ia_alertas or []
    resumo_ia = exame.interpretacao_ia_resumo or ""
    conclusao_ia = exame.interpretacao_ia or ""
    dados_json = exame.resultado_json or {}
    texto_resultado = exame.resultado_texto or ""
    payload_ia = exame.interpretacao_ia_payload or {}

    # Base de conhecimento para Q&A clínica
    resposta = _responder_chat_exame(
        pergunta=pergunta,
        exame_nome=exame.nome,
        tipo_exame=exame.tipo,
        especie=especie,
        nome_pet=nome_pet,
        alergias=alergias,
        alertas=alertas_exame,
        resumo_ia=resumo_ia,
        conclusao_ia=conclusao_ia,
        dados_json=dados_json,
        texto_resultado=texto_resultado,
        payload_ia=payload_ia,
        tem_arquivo=bool(exame.arquivo_url),
    )

    return {
        "exame_id": exame_id,
        "pergunta": payload.pergunta,
        "resposta": resposta,
        "contexto": {
            "pet_nome": nome_pet,
            "especie": especie,
            "exame_nome": exame.nome,
            "tem_interpretacao": bool(conclusao_ia),
        },
    }


# ═══════════════════════════════════════════════════════════════
# CALENDÁRIO PREVENTIVO — protocolos por espécie
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogo/calendario-preventivo", summary="Calendário preventivo por espécie")
def calendario_preventivo(
    especie: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Retorna o calendário preventivo padrão por espécie (cão, gato, coelho, todos)
    mesclado com os protocolos de vacina configurados pelo tenant.
    """
    user, tenant_id = _get_tenant(current)

    especie_norm = (especie or "").strip().lower()

    # Monta calendário base
    calendario_base = []
    for esp, protocolos in _CALENDARIO_PADRAO.items():
        if not especie_norm or especie_norm in esp or esp in especie_norm or esp == "todos":
            for p in protocolos:
                calendario_base.append({**p, "especie": esp, "fonte": "padrao"})

    # Adiciona protocolos personalizados do tenant
    query_protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    )
    if especie_norm:
        query_protocolos = query_protocolos.filter(
            (ProtocoloVacina.especie == None) |
            (ProtocoloVacina.especie == "") |
            (ProtocoloVacina.especie.ilike(f"%{especie_norm}%"))
        )

    for p in query_protocolos.all():
        idade_min = p.dose_inicial_semanas

        reforco_dias = p.intervalo_doses_dias or (365 if p.reforco_anual else None)
        calendario_base.append({
            "vacina": p.nome,
            "fase": "filhote" if (idade_min or 0) < 26 else "adulto",
            "idade_semanas_min": idade_min,
            "idade_semanas_max": None,
            "dose": f"{p.numero_doses_serie} dose(s)" if p.numero_doses_serie > 1 else "dose única",
            "reforco_anual": p.reforco_anual,
            "intervalo_doses_dias": p.intervalo_doses_dias,
            "observacoes": p.observacoes or "",
            "especie": p.especie or "todos",
            "fonte": "personalizado",
            "protocolo_id": p.id,
        })

    # Ordena por espécie e idade mínima
    calendario_base.sort(key=lambda x: (x.get("especie", ""), x.get("idade_semanas_min") or 0))

    return {
        "especie_filtro": especie_norm or "todas",
        "total": len(calendario_base),
        "items": calendario_base,
    }
