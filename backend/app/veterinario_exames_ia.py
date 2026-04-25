"""Helpers de IA e triagem automatica para exames veterinarios."""

import json
import re
from datetime import date, datetime
from typing import Optional

from .veterinario_core import _parse_numeric_text


def _as_float_exame(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _merge_exam_result_json(exame, novo_json: dict) -> dict:
    atual = exame.resultado_json if isinstance(exame.resultado_json, dict) else {}
    merged = dict(atual)
    for chave, valor in (novo_json or {}).items():
        if valor in (None, "", []):
            continue
        merged[chave] = valor
    return merged


def _meses_desde(data_base: Optional[date], referencia: Optional[date] = None) -> Optional[int]:
    if not data_base:
        return None
    ref = referencia or date.today()
    return max((ref.year - data_base.year) * 12 + (ref.month - data_base.month), 0)


def _avaliar_resultado_item(chave: str, valor) -> Optional[dict]:
    numero = _as_float_exame(valor)
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


def _gerar_interpretacao_exame(exame) -> dict:
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
