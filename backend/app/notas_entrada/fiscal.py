"""Calculos fiscais e de custo para notas de entrada."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any, Dict
import xml.etree.ElementTree as ET

from app.produtos_models import NotaEntrada


ZERO_DECIMAL = Decimal("0")
UNIT_PRECISION = Decimal("0.0001")
TOTAL_PRECISION = Decimal("0.01")
COST_COMPONENT_KEYS = (
    "valor_frete",
    "valor_seguro",
    "valor_outras_despesas",
    "valor_desconto",
    "valor_icms_st",
    "valor_ipi",
)


def detectar_multiplicador_pack(descricao: str) -> int:
    """
    Detecta padrao de pack no texto, ex:
    - 10X250G
    - 3X2,5KG
    - 6x3
    Retorna multiplicador (>=1).
    """
    if not descricao:
        return 1

    texto = str(descricao).upper()

    padroes = [
        # Ex.: 4x1.8kg | 12*0,5kg | 6x3
        re.compile(
            r"(?<!\d)(\d{1,3})\s*[X\*\u00d7]\s*(\d+(?:[\.,]\d+)?)(?:\s*(KG|G|GR|ML|L|MG|UN|UND|PCT|PC|SACHE|SACHES|SACH\u00ca))?"
        ),
        # Ex.: CX 12 UN | CAIXA C/ 12
        re.compile(r"\b(?:CX|CAIXA)\s*(?:C\/)?\s*(\d{1,3})\s*(?:UN|UND|UNID)?\b"),
        re.compile(r"(?<!\d)(\d{1,3})\s*[X\*\u00d7]\s*(\d{1,3})(?!\d)"),
    ]

    for padrao in padroes:
        match = padrao.search(texto)
        if not match:
            continue

        try:
            multiplicador = int(match.group(1))
        except (TypeError, ValueError):
            continue

        if 1 < multiplicador <= 200:
            return multiplicador

    return 1


def calcular_quantidade_custo_efetivos(
    descricao: str,
    quantidade: float,
    valor_unitario: float,
    valor_total: float,
) -> dict:
    """
    Calcula quantidade efetiva e custo unitario efetivo considerando pack.
    """
    qtd_base = float(quantidade or 0)
    v_unit = float(valor_unitario or 0)
    v_total = float(valor_total or 0)

    multiplicador_pack = detectar_multiplicador_pack(descricao)
    quantidade_efetiva = qtd_base * multiplicador_pack

    if quantidade_efetiva > 0:
        if v_total > 0:
            custo_unitario_efetivo = v_total / quantidade_efetiva
        elif multiplicador_pack > 1 and v_unit > 0:
            custo_unitario_efetivo = v_unit / multiplicador_pack
        else:
            custo_unitario_efetivo = v_unit
    else:
        custo_unitario_efetivo = 0.0

    return {
        "pack_detectado": multiplicador_pack > 1,
        "multiplicador_pack": multiplicador_pack,
        "quantidade_efetiva": quantidade_efetiva,
        "custo_unitario_efetivo": custo_unitario_efetivo,
    }


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return ZERO_DECIMAL
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _round_decimal(value: Decimal, precision: Decimal = TOTAL_PRECISION) -> Decimal:
    return value.quantize(precision, rounding=ROUND_HALF_UP)


def _decimal_to_float(value: Decimal, precision: Decimal = TOTAL_PRECISION) -> float:
    return float(_round_decimal(value, precision))


def extrair_resumo_fiscal_xml(xml_content: str) -> Dict[str, Any]:
    """Extrai valores fiscais e acessorios por item a partir do XML da NF-e."""
    root = ET.fromstring(xml_content)
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    inf_nfe = root.find(".//nfe:infNFe", ns)
    if inf_nfe is None:
        raise ValueError("Tag infNFe nao encontrada no XML")

    total = inf_nfe.find(".//nfe:total/nfe:ICMSTot", ns)
    totais_nota = {
        "valor_produtos": _to_decimal(
            total.findtext("nfe:vProd", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_frete": _to_decimal(
            total.findtext("nfe:vFrete", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_seguro": _to_decimal(
            total.findtext("nfe:vSeg", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_desconto": _to_decimal(
            total.findtext("nfe:vDesc", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_outras_despesas": _to_decimal(
            total.findtext("nfe:vOutro", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_icms": _to_decimal(
            total.findtext("nfe:vICMS", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_icms_st": _to_decimal(
            total.findtext("nfe:vST", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_ipi": _to_decimal(
            total.findtext("nfe:vIPI", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_pis": _to_decimal(
            total.findtext("nfe:vPIS", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_cofins": _to_decimal(
            total.findtext("nfe:vCOFINS", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
        "valor_total": _to_decimal(
            total.findtext("nfe:vNF", default="0", namespaces=ns)
            if total is not None
            else "0"
        ),
    }

    itens = []
    for idx, det in enumerate(inf_nfe.findall(".//nfe:det", ns), start=1):
        prod = det.find("nfe:prod", ns)
        imposto = det.find("nfe:imposto", ns)

        valor_icms = ZERO_DECIMAL
        valor_icms_st = ZERO_DECIMAL
        valor_ipi = ZERO_DECIMAL
        valor_pis = ZERO_DECIMAL
        valor_cofins = ZERO_DECIMAL

        if imposto is not None:
            icms_group = imposto.find("nfe:ICMS", ns)
            if icms_group is not None and list(icms_group):
                icms_node = list(icms_group)[0]
                valor_icms = _to_decimal(
                    icms_node.findtext("nfe:vICMS", default="0", namespaces=ns)
                )
                valor_icms_st = _to_decimal(
                    icms_node.findtext("nfe:vICMSST", default="0", namespaces=ns)
                )
                if valor_icms_st == ZERO_DECIMAL:
                    valor_icms_st = _to_decimal(
                        icms_node.findtext("nfe:vST", default="0", namespaces=ns)
                    )

            ipi_group = imposto.find("nfe:IPI", ns)
            if ipi_group is not None:
                ipi_node = ipi_group.find("nfe:IPITrib", ns) or ipi_group.find(
                    "nfe:IPINT", ns
                )
                if ipi_node is not None:
                    valor_ipi = _to_decimal(
                        ipi_node.findtext("nfe:vIPI", default="0", namespaces=ns)
                    )

            pis_group = imposto.find("nfe:PIS", ns)
            if pis_group is not None and list(pis_group):
                valor_pis = _to_decimal(
                    list(pis_group)[0].findtext("nfe:vPIS", default="0", namespaces=ns)
                )

            cofins_group = imposto.find("nfe:COFINS", ns)
            if cofins_group is not None and list(cofins_group):
                valor_cofins = _to_decimal(
                    list(cofins_group)[0].findtext(
                        "nfe:vCOFINS", default="0", namespaces=ns
                    )
                )

        itens.append(
            {
                "numero_item": int(det.attrib.get("nItem") or idx),
                "valor_produtos": _to_decimal(
                    prod.findtext("nfe:vProd", default="0", namespaces=ns)
                    if prod is not None
                    else "0"
                ),
                "valor_frete": _to_decimal(
                    prod.findtext("nfe:vFrete", default="0", namespaces=ns)
                    if prod is not None
                    else "0"
                ),
                "valor_seguro": _to_decimal(
                    prod.findtext("nfe:vSeg", default="0", namespaces=ns)
                    if prod is not None
                    else "0"
                ),
                "valor_desconto": _to_decimal(
                    prod.findtext("nfe:vDesc", default="0", namespaces=ns)
                    if prod is not None
                    else "0"
                ),
                "valor_outras_despesas": _to_decimal(
                    prod.findtext("nfe:vOutro", default="0", namespaces=ns)
                    if prod is not None
                    else "0"
                ),
                "valor_icms": valor_icms,
                "valor_icms_st": valor_icms_st,
                "valor_ipi": valor_ipi,
                "valor_pis": valor_pis,
                "valor_cofins": valor_cofins,
            }
        )

    return {
        "totais": totais_nota,
        "itens": itens,
    }


def calcular_composicao_custos_nota(nota: NotaEntrada) -> Dict[int, Dict[str, Any]]:
    """Calcula custo de aquisicao por item usando XML da nota e rateio proporcional quando necessario."""
    if not nota.xml_content or not nota.itens:
        return {}

    resumo_fiscal = extrair_resumo_fiscal_xml(nota.xml_content)
    totais_nota = resumo_fiscal["totais"]
    itens_xml = {int(item["numero_item"]): item for item in resumo_fiscal["itens"]}
    total_produtos_nota = sum(_to_decimal(item.valor_total) for item in nota.itens)

    somas_itens = {key: ZERO_DECIMAL for key in COST_COMPONENT_KEYS}
    itens_base = []

    for item in nota.itens:
        xml_item = itens_xml.get(int(item.numero_item), {})
        valor_produtos_total = _to_decimal(item.valor_total)
        quantidade_efetiva = _to_decimal(
            calcular_quantidade_custo_efetivos(
                item.descricao,
                item.quantidade,
                item.valor_unitario,
                item.valor_total,
            )["quantidade_efetiva"]
        )
        proporcao = (
            (valor_produtos_total / total_produtos_nota)
            if total_produtos_nota > 0
            else ZERO_DECIMAL
        )

        diretos = {
            key: _to_decimal(xml_item.get(key, 0)) for key in COST_COMPONENT_KEYS
        }
        for key, value in diretos.items():
            somas_itens[key] += value

        itens_base.append(
            {
                "item": item,
                "valor_produtos_total": valor_produtos_total,
                "quantidade_efetiva": quantidade_efetiva,
                "proporcao": proporcao,
                "diretos": diretos,
                "tributos_info": {
                    "valor_icms": _to_decimal(xml_item.get("valor_icms", 0)),
                    "valor_pis": _to_decimal(xml_item.get("valor_pis", 0)),
                    "valor_cofins": _to_decimal(xml_item.get("valor_cofins", 0)),
                },
            }
        )

    rateios_restantes = {
        key: max(totais_nota.get(key, ZERO_DECIMAL) - somas_itens[key], ZERO_DECIMAL)
        for key in COST_COMPONENT_KEYS
    }

    composicoes: Dict[int, Dict[str, Any]] = {}
    for base in itens_base:
        item = base["item"]
        quantidade_efetiva = base["quantidade_efetiva"]
        valor_produtos_total = base["valor_produtos_total"]

        componentes_total = {}
        componentes_unitario = {}
        for key in COST_COMPONENT_KEYS:
            valor_total = base["diretos"][key] + (
                rateios_restantes[key] * base["proporcao"]
            )
            componentes_total[key] = valor_total
            componentes_unitario[key] = (
                (valor_total / quantidade_efetiva)
                if quantidade_efetiva > 0
                else ZERO_DECIMAL
            )

        custo_bruto_unitario = (
            (valor_produtos_total / quantidade_efetiva)
            if quantidade_efetiva > 0
            else ZERO_DECIMAL
        )
        custo_aquisicao_total = (
            valor_produtos_total
            + componentes_total["valor_frete"]
            + componentes_total["valor_seguro"]
            + componentes_total["valor_outras_despesas"]
            + componentes_total["valor_icms_st"]
            + componentes_total["valor_ipi"]
            - componentes_total["valor_desconto"]
        )
        custo_aquisicao_unitario = (
            (custo_aquisicao_total / quantidade_efetiva)
            if quantidade_efetiva > 0
            else ZERO_DECIMAL
        )

        composicoes[item.id] = {
            "quantidade_efetiva": float(quantidade_efetiva),
            "custo_bruto_unitario": _decimal_to_float(
                custo_bruto_unitario, UNIT_PRECISION
            ),
            "custo_aquisicao_total": _decimal_to_float(
                custo_aquisicao_total, TOTAL_PRECISION
            ),
            "custo_aquisicao_unitario": _decimal_to_float(
                custo_aquisicao_unitario, UNIT_PRECISION
            ),
            "componentes_total": {
                "valor_produtos": _decimal_to_float(
                    valor_produtos_total, TOTAL_PRECISION
                ),
                "valor_frete": _decimal_to_float(
                    componentes_total["valor_frete"], TOTAL_PRECISION
                ),
                "valor_seguro": _decimal_to_float(
                    componentes_total["valor_seguro"], TOTAL_PRECISION
                ),
                "valor_outras_despesas": _decimal_to_float(
                    componentes_total["valor_outras_despesas"], TOTAL_PRECISION
                ),
                "valor_desconto": _decimal_to_float(
                    componentes_total["valor_desconto"], TOTAL_PRECISION
                ),
                "valor_icms_st": _decimal_to_float(
                    componentes_total["valor_icms_st"], TOTAL_PRECISION
                ),
                "valor_ipi": _decimal_to_float(
                    componentes_total["valor_ipi"], TOTAL_PRECISION
                ),
                "valor_icms": _decimal_to_float(
                    base["tributos_info"]["valor_icms"], TOTAL_PRECISION
                ),
                "valor_pis": _decimal_to_float(
                    base["tributos_info"]["valor_pis"], TOTAL_PRECISION
                ),
                "valor_cofins": _decimal_to_float(
                    base["tributos_info"]["valor_cofins"], TOTAL_PRECISION
                ),
            },
            "componentes_unitario": {
                "valor_frete": _decimal_to_float(
                    componentes_unitario["valor_frete"], UNIT_PRECISION
                ),
                "valor_seguro": _decimal_to_float(
                    componentes_unitario["valor_seguro"], UNIT_PRECISION
                ),
                "valor_outras_despesas": _decimal_to_float(
                    componentes_unitario["valor_outras_despesas"], UNIT_PRECISION
                ),
                "valor_desconto": _decimal_to_float(
                    componentes_unitario["valor_desconto"], UNIT_PRECISION
                ),
                "valor_icms_st": _decimal_to_float(
                    componentes_unitario["valor_icms_st"], UNIT_PRECISION
                ),
                "valor_ipi": _decimal_to_float(
                    componentes_unitario["valor_ipi"], UNIT_PRECISION
                ),
                "valor_icms": _decimal_to_float(
                    (base["tributos_info"]["valor_icms"] / quantidade_efetiva)
                    if quantidade_efetiva > 0
                    else ZERO_DECIMAL,
                    UNIT_PRECISION,
                ),
                "valor_pis": _decimal_to_float(
                    (base["tributos_info"]["valor_pis"] / quantidade_efetiva)
                    if quantidade_efetiva > 0
                    else ZERO_DECIMAL,
                    UNIT_PRECISION,
                ),
                "valor_cofins": _decimal_to_float(
                    (base["tributos_info"]["valor_cofins"] / quantidade_efetiva)
                    if quantidade_efetiva > 0
                    else ZERO_DECIMAL,
                    UNIT_PRECISION,
                ),
            },
            "tem_rateio": any(
                rateios_restantes[key] > ZERO_DECIMAL for key in COST_COMPONENT_KEYS
            ),
        }

    return composicoes
