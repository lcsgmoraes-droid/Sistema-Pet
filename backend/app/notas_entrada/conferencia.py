"""Helpers de conferencia e lotes de notas de entrada."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from fastapi import HTTPException

from app.produtos_models import NotaEntrada, NotaEntradaItem


logger = logging.getLogger(__name__)

CONFERENCIA_STATUS_NAO_INICIADA = "nao_iniciada"
CONFERENCIA_STATUS_SEM_DIVERGENCIA = "sem_divergencia"
CONFERENCIA_STATUS_COM_DIVERGENCIA = "com_divergencia"
ACOES_CONFERENCIA_VALIDAS = {
    "sem_acao",
    "contatar_fornecedor",
    "reposicao_fornecedor",
    "nf_devolucao",
    "ajuste_interno",
}


def _parse_data_validade_texto(valor: str):
    valor_normalizado = (valor or "").strip()
    if not valor_normalizado:
        return None

    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(valor_normalizado, formato).date()
        except ValueError:
            continue

    return None


def _extrair_lote_validade_info_adicional(texto: str) -> tuple[str, Any]:
    texto_normalizado = (texto or "").strip().upper()
    if not texto_normalizado:
        return "", None

    lote = ""
    data_validade = None

    lote_match = re.search(
        r"\b(?:LOTE|LOT)\s*[:\-]?\s*([A-Z0-9][A-Z0-9._/\-]*)",
        texto_normalizado,
    )
    if lote_match:
        lote = lote_match.group(1).strip(".,;")

    validade_match = re.search(
        r"\b(?:VALIDADE|VALID|VAL\.?|VENCIMENTO|VENC|VECTO|VCTO|VENCTO)\s*[:\-]?\s*"
        r"(\d{4}-\d{2}-\d{2}|\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})",
        texto_normalizado,
    )
    if validade_match:
        data_validade = _parse_data_validade_texto(validade_match.group(1))

    return lote, data_validade


def _round_quantity(value: Any) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def _normalizar_texto_curto(value: Optional[str]) -> Optional[str]:
    texto = (value or "").strip()
    return texto or None


def _data_para_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def _mapear_lotes_rastro_xml(
    xml_content: Optional[str],
) -> Dict[int, List[Dict[str, Any]]]:
    if not xml_content:
        return {}

    try:
        root = ET.fromstring(xml_content)
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        inf_nfe = root.find(".//nfe:infNFe", ns)
        if inf_nfe is None:
            return {}

        lotes_por_item: Dict[int, List[Dict[str, Any]]] = {}
        for idx, det in enumerate(inf_nfe.findall(".//nfe:det", ns), start=1):
            try:
                numero_item = int(det.attrib.get("nItem") or idx)
            except (TypeError, ValueError):
                numero_item = idx

            prod = det.find("nfe:prod", ns)
            if prod is None:
                continue

            rastros = []
            for rastro in prod.findall("nfe:rastro", ns):
                nome_lote = _normalizar_texto_curto(
                    rastro.findtext("nfe:nLote", default="", namespaces=ns)
                )
                quantidade_nf = _round_quantity(
                    rastro.findtext("nfe:qLote", default="0", namespaces=ns)
                )
                data_fabricacao = _parse_data_validade_texto(
                    rastro.findtext("nfe:dFab", default="", namespaces=ns)
                )
                data_validade = _parse_data_validade_texto(
                    rastro.findtext("nfe:dVal", default="", namespaces=ns)
                )

                if not any([nome_lote, quantidade_nf > 0, data_validade]):
                    continue

                rastros.append(
                    {
                        "nome_lote": nome_lote,
                        "quantidade_nf": quantidade_nf,
                        "data_fabricacao": data_fabricacao,
                        "data_validade": data_validade,
                    }
                )

            if rastros:
                lotes_por_item[numero_item] = rastros

        return lotes_por_item
    except Exception as exc:
        logger.warning(f"Nao foi possivel mapear lotes rastro do XML: {exc}")
        return {}


def _montar_lotes_entrada_item(
    item: NotaEntradaItem,
    nota: NotaEntrada,
    quantidade_entrada: float,
    lotes_rastro_por_item: Dict[int, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    quantidade_entrada = _round_quantity(quantidade_entrada)
    if quantidade_entrada <= 0:
        return []

    try:
        numero_item = int(item.numero_item)
    except (TypeError, ValueError):
        numero_item = 0

    rastros = lotes_rastro_por_item.get(numero_item) or []
    if rastros:
        soma_quantidade_nf = _round_quantity(
            sum(lote.get("quantidade_nf", 0) for lote in rastros)
        )

        if soma_quantidade_nf > 0:
            lotes = []
            restante = quantidade_entrada
            for index, lote_xml in enumerate(rastros):
                if index == len(rastros) - 1:
                    quantidade_lote = restante
                else:
                    proporcao = (
                        lote_xml.get("quantidade_nf", 0) or 0
                    ) / soma_quantidade_nf
                    quantidade_lote = _round_quantity(quantidade_entrada * proporcao)
                    restante = _round_quantity(restante - quantidade_lote)

                if quantidade_lote <= 0:
                    continue

                lotes.append(
                    {
                        "nome_lote": lote_xml.get("nome_lote")
                        or f"NF{nota.numero_nota}-{item.numero_item}-{index + 1}",
                        "quantidade": quantidade_lote,
                        "data_fabricacao": _data_para_datetime(
                            lote_xml.get("data_fabricacao")
                        ),
                        "data_validade": _data_para_datetime(
                            lote_xml.get("data_validade") or item.data_validade
                        ),
                    }
                )

            if lotes:
                return lotes

        if len(rastros) == 1:
            lote_xml = rastros[0]
            return [
                {
                    "nome_lote": lote_xml.get("nome_lote")
                    or f"NF{nota.numero_nota}-{item.numero_item}",
                    "quantidade": quantidade_entrada,
                    "data_fabricacao": _data_para_datetime(
                        lote_xml.get("data_fabricacao")
                    ),
                    "data_validade": _data_para_datetime(
                        lote_xml.get("data_validade") or item.data_validade
                    ),
                }
            ]

    return [
        {
            "nome_lote": item.lote
            if item.lote
            else f"NF{nota.numero_nota}-{item.numero_item}",
            "quantidade": quantidade_entrada,
            "data_fabricacao": None,
            "data_validade": _data_para_datetime(item.data_validade),
        }
    ]


def _obter_override_mapa(mapa: Dict[Any, Any], chave: Any) -> Any:
    if not isinstance(mapa, dict):
        return None
    if chave in mapa:
        return mapa[chave]
    chave_str = str(chave)
    if chave_str in mapa:
        return mapa[chave_str]
    return None


def _normalizar_custo_unitario_override(valor: Any, item_id: int) -> Optional[float]:
    if valor is None or str(valor).strip() == "":
        return None

    try:
        custo = float(valor)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"Custo manual invalido para o item {item_id}.",
        )

    custo = round(custo, 4)
    if custo <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"O custo manual do item {item_id} deve ser maior que zero.",
        )
    return custo


def _obter_acao_conferencia(acao: Optional[str], tem_divergencia: bool) -> str:
    acao_normalizada = (acao or "").strip() or (
        "contatar_fornecedor" if tem_divergencia else "sem_acao"
    )
    if acao_normalizada not in ACOES_CONFERENCIA_VALIDAS:
        return "contatar_fornecedor" if tem_divergencia else "sem_acao"
    if not tem_divergencia:
        return "sem_acao"
    return acao_normalizada


def _quantidades_conferencia_item(item: NotaEntradaItem) -> Dict[str, float]:
    quantidade_nf = _round_quantity(item.quantidade)
    quantidade_conferida = item.quantidade_conferida
    if quantidade_conferida is None:
        quantidade_conferida = quantidade_nf
    quantidade_conferida = max(
        0.0, min(_round_quantity(quantidade_conferida), quantidade_nf)
    )

    quantidade_avariada = max(0.0, _round_quantity(item.quantidade_avariada))
    max_avariada = max(quantidade_nf - quantidade_conferida, 0.0)
    quantidade_avariada = min(quantidade_avariada, max_avariada)
    quantidade_faltante = max(
        quantidade_nf - quantidade_conferida - quantidade_avariada, 0.0
    )

    return {
        "quantidade_nf": quantidade_nf,
        "quantidade_conferida": quantidade_conferida,
        "quantidade_avariada": quantidade_avariada,
        "quantidade_faltante": _round_quantity(quantidade_faltante),
    }


def _status_conferencia_item(item: NotaEntradaItem) -> str:
    quantidades = _quantidades_conferencia_item(item)
    tem_avaria = quantidades["quantidade_avariada"] > 0
    tem_falta = quantidades["quantidade_faltante"] > 0

    if tem_avaria and tem_falta:
        return "falta_avaria"
    if tem_avaria:
        return "avaria"
    if tem_falta:
        return "falta"
    return "ok"


def _serializar_conferencia_item(item: NotaEntradaItem) -> Dict[str, Any]:
    quantidades = _quantidades_conferencia_item(item)
    status_conferencia = _status_conferencia_item(item)
    tem_divergencia = status_conferencia != "ok"
    acao_sugerida = _obter_acao_conferencia(item.acao_sugerida, tem_divergencia)

    return {
        **quantidades,
        "status_conferencia": status_conferencia,
        "tem_divergencia": tem_divergencia,
        "observacao_conferencia": _normalizar_texto_curto(item.observacao_conferencia),
        "acao_sugerida": acao_sugerida,
        "pode_gerar_nf_devolucao": quantidades["quantidade_avariada"] > 0,
        "quantidade_para_devolucao": quantidades["quantidade_avariada"],
    }


def _resumir_conferencia_nota(nota: NotaEntrada) -> Dict[str, Any]:
    itens = list(getattr(nota, "itens", []) or [])
    itens_serializados = [_serializar_conferencia_item(item) for item in itens]
    itens_divergencia = [item for item in itens_serializados if item["tem_divergencia"]]
    itens_com_avaria = [
        item for item in itens_serializados if item["quantidade_avariada"] > 0
    ]

    if nota.conferencia_realizada_em:
        status_conferencia = nota.conferencia_status or (
            CONFERENCIA_STATUS_COM_DIVERGENCIA
            if itens_divergencia
            else CONFERENCIA_STATUS_SEM_DIVERGENCIA
        )
    else:
        status_conferencia = CONFERENCIA_STATUS_NAO_INICIADA

    return {
        "status": status_conferencia,
        "observacao_geral": _normalizar_texto_curto(nota.conferencia_observacoes),
        "conferida_em": nota.conferencia_realizada_em.isoformat()
        if nota.conferencia_realizada_em
        else None,
        "itens_total": len(itens),
        "itens_ok": len(itens_serializados) - len(itens_divergencia),
        "itens_com_divergencia": len(itens_divergencia),
        "itens_com_avaria": len(itens_com_avaria),
        "quantidade_total_nf": _round_quantity(
            sum(item["quantidade_nf"] for item in itens_serializados)
        ),
        "quantidade_total_conferida": _round_quantity(
            sum(item["quantidade_conferida"] for item in itens_serializados)
        ),
        "quantidade_total_avariada": _round_quantity(
            sum(item["quantidade_avariada"] for item in itens_serializados)
        ),
        "quantidade_total_faltante": _round_quantity(
            sum(item["quantidade_faltante"] for item in itens_serializados)
        ),
        "tem_nf_devolucao_sugerida": len(itens_com_avaria) > 0,
    }


def _montar_payload_nota(
    nota: NotaEntrada,
    itens_formatados: List[Dict[str, Any]],
    fornecedor_criado_automaticamente: bool = False,
) -> Dict[str, Any]:
    conferencia = _resumir_conferencia_nota(nota)
    return {
        "id": nota.id,
        "numero_nota": nota.numero_nota,
        "serie": nota.serie,
        "chave_acesso": nota.chave_acesso,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "fornecedor_id": nota.fornecedor_id,
        "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
        "data_emissao": nota.data_emissao,
        "valor_total": nota.valor_total,
        "status": nota.status,
        "produtos_vinculados": nota.produtos_vinculados,
        "produtos_nao_vinculados": nota.produtos_nao_vinculados,
        "entrada_estoque_realizada": nota.entrada_estoque_realizada,
        "tipo_rateio": nota.tipo_rateio,
        "percentual_online": nota.percentual_online,
        "percentual_loja": nota.percentual_loja,
        "valor_online": nota.valor_online,
        "valor_loja": nota.valor_loja,
        "conferencia": conferencia,
        "conferencia_status": conferencia["status"],
        "divergencias_count": conferencia["itens_com_divergencia"],
        "itens": itens_formatados,
    }
