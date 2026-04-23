"""
ROTAS DE ENTRADA POR XML - Sistema Pet Shop Pro
Upload e processamento de NF-e de fornecedores

Funcionalidades:
- Upload de XML de NF-e
- Parser automÃ¡tico de XML
- Matching automÃ¡tico de produtos
- Entrada automÃ¡tica no estoque
- GestÃ£o de produtos nÃ£o vinculados
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import xml.etree.ElementTree as ET
import re
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP

from app.clientes_routes import gerar_codigo_cliente

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from .produtos_models import (
    Produto, ProdutoLote, EstoqueMovimentacao,
    NotaEntrada, NotaEntradaItem, ProdutoHistoricoPreco,
    ProdutoFornecedor
)
from .financeiro_models import ContaPagar
from .fiscal_patterns import aplicar_inteligencia_fiscal, identificar_padrao_fiscal

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-entrada", tags=["Notas de Entrada (XML)"])

# ============================================================================
# SCHEMAS
# ============================================================================

class NotaEntradaResponse(BaseModel):
    id: int
    numero_nota: str
    serie: str
    chave_acesso: str
    fornecedor_nome: str
    fornecedor_cnpj: str
    fornecedor_id: Optional[int] = None
    data_emissao: datetime
    valor_total: float
    status: str
    produtos_vinculados: Optional[int] = 0
    produtos_nao_vinculados: Optional[int] = 0
    entrada_estoque_realizada: Optional[bool] = False
    conferencia_status: Optional[str] = "nao_iniciada"
    divergencias_count: Optional[int] = 0
    
    model_config = {"from_attributes": True}


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


class ConferenciaItemPayload(BaseModel):
    item_id: int
    quantidade_conferida: float
    quantidade_avariada: float = 0
    observacao_conferencia: Optional[str] = None
    acao_sugerida: Optional[str] = "sem_acao"


class ConferenciaNotaPayload(BaseModel):
    itens: List[ConferenciaItemPayload]
    observacao_geral: Optional[str] = None


# ============================================================================
# PARSER DE XML NF-e
# ============================================================================

def detectar_multiplicador_pack(descricao: str) -> int:
    """
    Detecta padrão de pack no texto, ex:
    - 10X250G
    - 3X2,5KG
    - 6x3
    Retorna multiplicador (>=1).
    """
    if not descricao:
        return 1

    texto = str(descricao).upper()

    padroes = [
        # Ex.: 4x1.8kg | 12*0,5kg | 6×3
        re.compile(r'(?<!\d)(\d{1,3})\s*[X\*×]\s*(\d+(?:[\.,]\d+)?)(?:\s*(KG|G|GR|ML|L|MG|UN|UND|PCT|PC|SACHE|SACHES|SACHÊ))?'),
        # Ex.: CX 12 UN | CAIXA C/ 12
        re.compile(r'\b(?:CX|CAIXA)\s*(?:C\/)?\s*(\d{1,3})\s*(?:UN|UND|UNID)?\b'),
        re.compile(r'(?<!\d)(\d{1,3})\s*[X\*×]\s*(\d{1,3})(?!\d)')
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


def calcular_quantidade_custo_efetivos(descricao: str, quantidade: float, valor_unitario: float, valor_total: float) -> dict:
    """
    Calcula quantidade efetiva e custo unitário efetivo considerando pack.
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
        "custo_unitario_efetivo": custo_unitario_efetivo
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
    """Extrai valores fiscais e acessórios por item a partir do XML da NF-e."""
    root = ET.fromstring(xml_content)
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

    inf_nfe = root.find('.//nfe:infNFe', ns)
    if inf_nfe is None:
        raise ValueError("Tag infNFe não encontrada no XML")

    total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', ns)
    totais_nota = {
        "valor_produtos": _to_decimal(total.findtext('nfe:vProd', default='0', namespaces=ns) if total is not None else '0'),
        "valor_frete": _to_decimal(total.findtext('nfe:vFrete', default='0', namespaces=ns) if total is not None else '0'),
        "valor_seguro": _to_decimal(total.findtext('nfe:vSeg', default='0', namespaces=ns) if total is not None else '0'),
        "valor_desconto": _to_decimal(total.findtext('nfe:vDesc', default='0', namespaces=ns) if total is not None else '0'),
        "valor_outras_despesas": _to_decimal(total.findtext('nfe:vOutro', default='0', namespaces=ns) if total is not None else '0'),
        "valor_icms": _to_decimal(total.findtext('nfe:vICMS', default='0', namespaces=ns) if total is not None else '0'),
        "valor_icms_st": _to_decimal(total.findtext('nfe:vST', default='0', namespaces=ns) if total is not None else '0'),
        "valor_ipi": _to_decimal(total.findtext('nfe:vIPI', default='0', namespaces=ns) if total is not None else '0'),
        "valor_pis": _to_decimal(total.findtext('nfe:vPIS', default='0', namespaces=ns) if total is not None else '0'),
        "valor_cofins": _to_decimal(total.findtext('nfe:vCOFINS', default='0', namespaces=ns) if total is not None else '0'),
        "valor_total": _to_decimal(total.findtext('nfe:vNF', default='0', namespaces=ns) if total is not None else '0'),
    }

    itens = []
    for idx, det in enumerate(inf_nfe.findall('.//nfe:det', ns), start=1):
        prod = det.find('nfe:prod', ns)
        imposto = det.find('nfe:imposto', ns)

        valor_icms = ZERO_DECIMAL
        valor_icms_st = ZERO_DECIMAL
        valor_ipi = ZERO_DECIMAL
        valor_pis = ZERO_DECIMAL
        valor_cofins = ZERO_DECIMAL

        if imposto is not None:
            icms_group = imposto.find('nfe:ICMS', ns)
            if icms_group is not None and list(icms_group):
                icms_node = list(icms_group)[0]
                valor_icms = _to_decimal(icms_node.findtext('nfe:vICMS', default='0', namespaces=ns))
                valor_icms_st = _to_decimal(icms_node.findtext('nfe:vICMSST', default='0', namespaces=ns))
                if valor_icms_st == ZERO_DECIMAL:
                    valor_icms_st = _to_decimal(icms_node.findtext('nfe:vST', default='0', namespaces=ns))

            ipi_group = imposto.find('nfe:IPI', ns)
            if ipi_group is not None:
                ipi_node = ipi_group.find('nfe:IPITrib', ns) or ipi_group.find('nfe:IPINT', ns)
                if ipi_node is not None:
                    valor_ipi = _to_decimal(ipi_node.findtext('nfe:vIPI', default='0', namespaces=ns))

            pis_group = imposto.find('nfe:PIS', ns)
            if pis_group is not None and list(pis_group):
                valor_pis = _to_decimal(list(pis_group)[0].findtext('nfe:vPIS', default='0', namespaces=ns))

            cofins_group = imposto.find('nfe:COFINS', ns)
            if cofins_group is not None and list(cofins_group):
                valor_cofins = _to_decimal(list(cofins_group)[0].findtext('nfe:vCOFINS', default='0', namespaces=ns))

        itens.append({
            "numero_item": int(det.attrib.get('nItem') or idx),
            "valor_produtos": _to_decimal(prod.findtext('nfe:vProd', default='0', namespaces=ns) if prod is not None else '0'),
            "valor_frete": _to_decimal(prod.findtext('nfe:vFrete', default='0', namespaces=ns) if prod is not None else '0'),
            "valor_seguro": _to_decimal(prod.findtext('nfe:vSeg', default='0', namespaces=ns) if prod is not None else '0'),
            "valor_desconto": _to_decimal(prod.findtext('nfe:vDesc', default='0', namespaces=ns) if prod is not None else '0'),
            "valor_outras_despesas": _to_decimal(prod.findtext('nfe:vOutro', default='0', namespaces=ns) if prod is not None else '0'),
            "valor_icms": valor_icms,
            "valor_icms_st": valor_icms_st,
            "valor_ipi": valor_ipi,
            "valor_pis": valor_pis,
            "valor_cofins": valor_cofins,
        })

    return {
        "totais": totais_nota,
        "itens": itens,
    }


def calcular_composicao_custos_nota(nota: NotaEntrada) -> Dict[int, Dict[str, Any]]:
    """Calcula custo de aquisição por item usando XML da nota e rateio proporcional quando necessário."""
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
        proporcao = (valor_produtos_total / total_produtos_nota) if total_produtos_nota > 0 else ZERO_DECIMAL

        diretos = {
            key: _to_decimal(xml_item.get(key, 0)) for key in COST_COMPONENT_KEYS
        }
        for key, value in diretos.items():
            somas_itens[key] += value

        itens_base.append({
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
        })

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
            valor_total = base["diretos"][key] + (rateios_restantes[key] * base["proporcao"])
            componentes_total[key] = valor_total
            componentes_unitario[key] = (valor_total / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL

        custo_bruto_unitario = (valor_produtos_total / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL
        custo_aquisicao_total = (
            valor_produtos_total
            + componentes_total["valor_frete"]
            + componentes_total["valor_seguro"]
            + componentes_total["valor_outras_despesas"]
            + componentes_total["valor_icms_st"]
            + componentes_total["valor_ipi"]
            - componentes_total["valor_desconto"]
        )
        custo_aquisicao_unitario = (custo_aquisicao_total / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL

        composicoes[item.id] = {
            "quantidade_efetiva": float(quantidade_efetiva),
            "custo_bruto_unitario": _decimal_to_float(custo_bruto_unitario, UNIT_PRECISION),
            "custo_aquisicao_total": _decimal_to_float(custo_aquisicao_total, TOTAL_PRECISION),
            "custo_aquisicao_unitario": _decimal_to_float(custo_aquisicao_unitario, UNIT_PRECISION),
            "componentes_total": {
                "valor_produtos": _decimal_to_float(valor_produtos_total, TOTAL_PRECISION),
                "valor_frete": _decimal_to_float(componentes_total["valor_frete"], TOTAL_PRECISION),
                "valor_seguro": _decimal_to_float(componentes_total["valor_seguro"], TOTAL_PRECISION),
                "valor_outras_despesas": _decimal_to_float(componentes_total["valor_outras_despesas"], TOTAL_PRECISION),
                "valor_desconto": _decimal_to_float(componentes_total["valor_desconto"], TOTAL_PRECISION),
                "valor_icms_st": _decimal_to_float(componentes_total["valor_icms_st"], TOTAL_PRECISION),
                "valor_ipi": _decimal_to_float(componentes_total["valor_ipi"], TOTAL_PRECISION),
                "valor_icms": _decimal_to_float(base["tributos_info"]["valor_icms"], TOTAL_PRECISION),
                "valor_pis": _decimal_to_float(base["tributos_info"]["valor_pis"], TOTAL_PRECISION),
                "valor_cofins": _decimal_to_float(base["tributos_info"]["valor_cofins"], TOTAL_PRECISION),
            },
            "componentes_unitario": {
                "valor_frete": _decimal_to_float(componentes_unitario["valor_frete"], UNIT_PRECISION),
                "valor_seguro": _decimal_to_float(componentes_unitario["valor_seguro"], UNIT_PRECISION),
                "valor_outras_despesas": _decimal_to_float(componentes_unitario["valor_outras_despesas"], UNIT_PRECISION),
                "valor_desconto": _decimal_to_float(componentes_unitario["valor_desconto"], UNIT_PRECISION),
                "valor_icms_st": _decimal_to_float(componentes_unitario["valor_icms_st"], UNIT_PRECISION),
                "valor_ipi": _decimal_to_float(componentes_unitario["valor_ipi"], UNIT_PRECISION),
                "valor_icms": _decimal_to_float((base["tributos_info"]["valor_icms"] / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL, UNIT_PRECISION),
                "valor_pis": _decimal_to_float((base["tributos_info"]["valor_pis"] / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL, UNIT_PRECISION),
                "valor_cofins": _decimal_to_float((base["tributos_info"]["valor_cofins"] / quantidade_efetiva) if quantidade_efetiva > 0 else ZERO_DECIMAL, UNIT_PRECISION),
            },
            "tem_rateio": any(rateios_restantes[key] > ZERO_DECIMAL for key in COST_COMPONENT_KEYS),
        }

    return composicoes


def _round_quantity(value: Any) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def _normalizar_texto_curto(value: Optional[str]) -> Optional[str]:
    texto = (value or "").strip()
    return texto or None


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
            detail=f"Custo manual inválido para o item {item_id}.",
        )

    custo = round(custo, 4)
    if custo <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"O custo manual do item {item_id} deve ser maior que zero.",
        )
    return custo


def _obter_acao_conferencia(acao: Optional[str], tem_divergencia: bool) -> str:
    acao_normalizada = (acao or "").strip() or ("contatar_fornecedor" if tem_divergencia else "sem_acao")
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
    quantidade_conferida = max(0.0, min(_round_quantity(quantidade_conferida), quantidade_nf))

    quantidade_avariada = max(0.0, _round_quantity(item.quantidade_avariada))
    max_avariada = max(quantidade_nf - quantidade_conferida, 0.0)
    quantidade_avariada = min(quantidade_avariada, max_avariada)
    quantidade_faltante = max(quantidade_nf - quantidade_conferida - quantidade_avariada, 0.0)

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
    itens_com_avaria = [item for item in itens_serializados if item["quantidade_avariada"] > 0]

    if nota.conferencia_realizada_em:
        status_conferencia = nota.conferencia_status or (
            CONFERENCIA_STATUS_COM_DIVERGENCIA if itens_divergencia else CONFERENCIA_STATUS_SEM_DIVERGENCIA
        )
    else:
        status_conferencia = CONFERENCIA_STATUS_NAO_INICIADA

    return {
        "status": status_conferencia,
        "observacao_geral": _normalizar_texto_curto(nota.conferencia_observacoes),
        "conferida_em": nota.conferencia_realizada_em.isoformat() if nota.conferencia_realizada_em else None,
        "itens_total": len(itens),
        "itens_ok": len(itens_serializados) - len(itens_divergencia),
        "itens_com_divergencia": len(itens_divergencia),
        "itens_com_avaria": len(itens_com_avaria),
        "quantidade_total_nf": _round_quantity(sum(item["quantidade_nf"] for item in itens_serializados)),
        "quantidade_total_conferida": _round_quantity(sum(item["quantidade_conferida"] for item in itens_serializados)),
        "quantidade_total_avariada": _round_quantity(sum(item["quantidade_avariada"] for item in itens_serializados)),
        "quantidade_total_faltante": _round_quantity(sum(item["quantidade_faltante"] for item in itens_serializados)),
        "tem_nf_devolucao_sugerida": len(itens_com_avaria) > 0,
    }


def _montar_payload_nota(nota: NotaEntrada, itens_formatados: List[Dict[str, Any]], fornecedor_criado_automaticamente: bool = False) -> Dict[str, Any]:
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

def parse_nfe_xml(xml_content: str) -> dict:
    """
    Parse de XML de NF-e (padrÃ£o SEFAZ)
    Retorna dados estruturados da nota
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Namespace do XML da NF-e
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Buscar informaÃ§Ãµes principais
        inf_nfe = root.find('.//nfe:infNFe', ns)
        if not inf_nfe:
            raise ValueError("Tag infNFe nÃ£o encontrada no XML")
        
        # Chave de acesso
        chave_acesso = inf_nfe.get('Id', '').replace('NFe', '')
        
        # IdentificaÃ§Ã£o da nota
        ide = inf_nfe.find('.//nfe:ide', ns)
        numero_nota = ide.find('nfe:nNF', ns).text if ide.find('nfe:nNF', ns) is not None else ''
        serie = ide.find('nfe:serie', ns).text if ide.find('nfe:serie', ns) is not None else '1'
        data_emissao_str = ide.find('nfe:dhEmi', ns).text if ide.find('nfe:dhEmi', ns) is not None else ide.find('nfe:dEmi', ns).text
        # Usar date.fromisoformat para evitar problema de timezone (perda de 1 dia)
        from datetime import date
        data_emissao = date.fromisoformat(data_emissao_str.replace('Z', '+00:00').split('T')[0])
        
        # Emitente (fornecedor) - Dados completos
        emit = inf_nfe.find('.//nfe:emit', ns)
        fornecedor_cnpj = emit.find('nfe:CNPJ', ns).text if emit.find('nfe:CNPJ', ns) is not None else ''
        fornecedor_nome = emit.find('nfe:xNome', ns).text if emit.find('nfe:xNome', ns) is not None else ''
        fornecedor_fantasia = emit.find('nfe:xFant', ns).text if emit.find('nfe:xFant', ns) is not None else ''
        fornecedor_ie = emit.find('nfe:IE', ns).text if emit.find('nfe:IE', ns) is not None else ''
        
        # EndereÃ§o do fornecedor
        ender_emit = emit.find('nfe:enderEmit', ns)
        fornecedor_endereco = ''
        fornecedor_numero = ''
        fornecedor_bairro = ''
        fornecedor_cidade = ''
        fornecedor_uf = ''
        fornecedor_cep = ''
        fornecedor_telefone = ''
        
        if ender_emit is not None:
            fornecedor_endereco = ender_emit.find('nfe:xLgr', ns).text if ender_emit.find('nfe:xLgr', ns) is not None else ''
            fornecedor_numero = ender_emit.find('nfe:nro', ns).text if ender_emit.find('nfe:nro', ns) is not None else ''
            fornecedor_bairro = ender_emit.find('nfe:xBairro', ns).text if ender_emit.find('nfe:xBairro', ns) is not None else ''
            fornecedor_cidade = ender_emit.find('nfe:xMun', ns).text if ender_emit.find('nfe:xMun', ns) is not None else ''
            fornecedor_uf = ender_emit.find('nfe:UF', ns).text if ender_emit.find('nfe:UF', ns) is not None else ''
            fornecedor_cep = ender_emit.find('nfe:CEP', ns).text if ender_emit.find('nfe:CEP', ns) is not None else ''
            fornecedor_telefone = ender_emit.find('nfe:fone', ns).text if ender_emit.find('nfe:fone', ns) is not None else ''
        
        # Totais
        total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', ns)
        valor_produtos = float(total.find('nfe:vProd', ns).text) if total.find('nfe:vProd', ns) is not None else 0
        valor_frete = float(total.find('nfe:vFrete', ns).text) if total.find('nfe:vFrete', ns) is not None else 0
        valor_desconto = float(total.find('nfe:vDesc', ns).text) if total.find('nfe:vDesc', ns) is not None else 0
        valor_total = float(total.find('nfe:vNF', ns).text) if total.find('nfe:vNF', ns) is not None else 0
        
        # Itens
        itens = []
        det_list = inf_nfe.findall('.//nfe:det', ns)
        
        for idx, det in enumerate(det_list, start=1):
            prod = det.find('nfe:prod', ns)
            
            codigo_produto = prod.find('nfe:cProd', ns).text if prod.find('nfe:cProd', ns) is not None else ''
            descricao = prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else ''
            ncm = prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else ''
            cest = prod.find('nfe:CEST', ns).text if prod.find('nfe:CEST', ns) is not None else ''
            cfop = prod.find('nfe:CFOP', ns).text if prod.find('nfe:CFOP', ns) is not None else ''
            origem = prod.find('nfe:orig', ns).text if prod.find('nfe:orig', ns) is not None else '0'
            unidade = prod.find('nfe:uCom', ns).text if prod.find('nfe:uCom', ns) is not None else 'UN'
            quantidade = float(prod.find('nfe:qCom', ns).text) if prod.find('nfe:qCom', ns) is not None else 0
            valor_unitario = float(prod.find('nfe:vUnCom', ns).text) if prod.find('nfe:vUnCom', ns) is not None else 0
            valor_total_item = float(prod.find('nfe:vProd', ns).text) if prod.find('nfe:vProd', ns) is not None else 0
            ean = prod.find('nfe:cEAN', ns).text if prod.find('nfe:cEAN', ns) is not None else ''
            
            # Extrair lote e validade da tag <rastro> (rastreabilidade)
            lote = ''
            data_validade = None
            
            # Buscar tag de rastreabilidade
            rastro = prod.find('nfe:rastro', ns)
            if rastro is not None:
                # NÃºmero do lote
                lote_elem = rastro.find('nfe:nLote', ns)
                if lote_elem is not None:
                    lote = lote_elem.text
                
                # Data de validade
                validade_elem = rastro.find('nfe:dVal', ns)
                if validade_elem is not None:
                    try:
                        data_validade = datetime.strptime(validade_elem.text, '%Y-%m-%d').date()
                    except:
                        pass
            
            # Extrair alÃ­quotas de impostos
            aliquota_icms = 0.0
            aliquota_pis = 0.0
            aliquota_cofins = 0.0
            
            # Buscar impostos do item
            imposto = det.find('nfe:imposto', ns)
            if imposto is not None:
                # ICMS - pode estar em vÃ¡rias tags (ICMS00, ICMS10, ICMS20, etc)
                icms_group = imposto.find('nfe:ICMS', ns)
                if icms_group is not None:
                    # Tentar vÃ¡rias possibilidades de tag ICMS
                    for icms_tag in ['ICMS00', 'ICMS10', 'ICMS20', 'ICMS30', 'ICMS40', 'ICMS51', 'ICMS60', 'ICMS70', 'ICMS90', 'ICMSSN101', 'ICMSSN102', 'ICMSSN201', 'ICMSSN202', 'ICMSSN500', 'ICMSSN900']:
                        icms_elem = icms_group.find(f'nfe:{icms_tag}', ns)
                        if icms_elem is not None:
                            picms = icms_elem.find('nfe:pICMS', ns)
                            if picms is not None:
                                try:
                                    aliquota_icms = float(picms.text)
                                    break
                                except:
                                    pass
                
                # PIS
                pis_group = imposto.find('nfe:PIS', ns)
                if pis_group is not None:
                    # PISAliq ou PISOutr
                    for pis_tag in ['PISAliq', 'PISOutr', 'PISNT']:
                        pis_elem = pis_group.find(f'nfe:{pis_tag}', ns)
                        if pis_elem is not None:
                            ppis = pis_elem.find('nfe:pPIS', ns)
                            if ppis is not None:
                                try:
                                    aliquota_pis = float(ppis.text)
                                    break
                                except:
                                    pass
                
                # COFINS
                cofins_group = imposto.find('nfe:COFINS', ns)
                if cofins_group is not None:
                    # COFINSAliq ou COFINSOutr
                    for cofins_tag in ['COFINSAliq', 'COFINSOutr', 'COFINSNT']:
                        cofins_elem = cofins_group.find(f'nfe:{cofins_tag}', ns)
                        if cofins_elem is not None:
                            pcofins = cofins_elem.find('nfe:pCOFINS', ns)
                            if pcofins is not None:
                                try:
                                    aliquota_cofins = float(pcofins.text)
                                    break
                                except:
                                    pass
            
            # Se nÃ£o encontrar em rastro, tentar em informaÃ§Ãµes adicionais do produto
            if not lote:
                inf_ad_prod = prod.find('nfe:infAdProd', ns)
                if inf_ad_prod is not None and inf_ad_prod.text:
                    texto_info = inf_ad_prod.text.upper()
                    # Tentar encontrar LOTE: XXXX
                    if 'LOTE' in texto_info or 'LOTE:' in texto_info:
                        import re
                        match = re.search(r'LOTE[:\s]+([A-Z0-9]+)', texto_info)
                        if match:
                            lote = match.group(1)
            
            itens.append({
                'numero_item': idx,
                'codigo_produto': codigo_produto,
                'descricao': descricao,
                'ncm': ncm,
                'cest': cest,
                'cfop': cfop,
                'origem': origem,
                'aliquota_icms': aliquota_icms,
                'aliquota_pis': aliquota_pis,
                'aliquota_cofins': aliquota_cofins,
                'unidade': unidade,
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'valor_total': valor_total_item,
                'ean': ean,
                'lote': lote,
                'data_validade': data_validade
            })
        
        # Duplicatas (CobranÃ§as) - FASE 4: Para gerar contas a pagar
        duplicatas = []
        cobr = inf_nfe.find('.//nfe:cobr', ns)
        if cobr is not None:
            dup_list = cobr.findall('.//nfe:dup', ns)
            for dup in dup_list:
                numero_dup = dup.find('nfe:nDup', ns).text if dup.find('nfe:nDup', ns) is not None else ''
                vencimento_str = dup.find('nfe:dVenc', ns).text if dup.find('nfe:dVenc', ns) is not None else ''
                valor_dup = float(dup.find('nfe:vDup', ns).text) if dup.find('nfe:vDup', ns) is not None else 0
                
                # Parse data de vencimento (formato YYYY-MM-DD) - usar date para evitar problema de timezone
                from datetime import date
                vencimento = date.fromisoformat(vencimento_str) if vencimento_str else (datetime.now() + timedelta(days=30)).date()
                
                duplicatas.append({
                    'numero': numero_dup,
                    'vencimento': vencimento,
                    'valor': valor_dup
                })
        
        return {
            'chave_acesso': chave_acesso,
            'numero_nota': numero_nota,
            'serie': serie,
            'data_emissao': data_emissao,
            'fornecedor_cnpj': fornecedor_cnpj,
            'fornecedor_nome': fornecedor_nome,
            'fornecedor_fantasia': fornecedor_fantasia,
            'fornecedor_ie': fornecedor_ie,
            'fornecedor_endereco': fornecedor_endereco,
            'fornecedor_numero': fornecedor_numero,
            'fornecedor_bairro': fornecedor_bairro,
            'fornecedor_cidade': fornecedor_cidade,
            'fornecedor_uf': fornecedor_uf,
            'fornecedor_cep': fornecedor_cep,
            'fornecedor_telefone': fornecedor_telefone,
            'valor_produtos': valor_produtos,
            'valor_frete': valor_frete,
            'valor_desconto': valor_desconto,
            'valor_total': valor_total,
            'itens': itens,
            'duplicatas': duplicatas
        }
        
    except ET.ParseError as e:
        raise ValueError(f"Erro ao fazer parse do XML: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erro ao processar XML: {str(e)}")


def gerar_prefixo_fornecedor(nome: str) -> str:
    """
    Gera um prefixo baseado no nome do fornecedor
    Ex: Megazoo -> MGZ, Reino das Aves -> RA
    """
    # Remover palavras comuns
    palavras_ignorar = {'ltda', 'sa', 'me', 'epp', 'eireli', 'comercio', 'industria', 'distribuidora', 'de', 'da', 'do', 'das', 'dos', 'e'}
    palavras = [p for p in nome.lower().split() if p not in palavras_ignorar]
    
    if not palavras:
        return nome[:3].upper()
    
    # Se tiver uma palavra, pega as 3 primeiras letras
    if len(palavras) == 1:
        return palavras[0][:3].upper()
    
    # Se tiver 2-3 palavras, pega a primeira letra de cada
    if len(palavras) <= 3:
        return ''.join([p[0] for p in palavras]).upper()
    
    # Se tiver mais de 3, pega as mais significativas (maiores)
    palavras_ordenadas = sorted(palavras, key=len, reverse=True)[:3]
    return ''.join([p[0] for p in palavras_ordenadas]).upper()


def criar_fornecedor_automatico(dados_xml: dict, db: Session, current_user, tenant_id: int) -> tuple:
    """
    Cria um fornecedor automaticamente a partir dos dados do XML
    Se jÃ¡ existir um fornecedor inativo com o mesmo CNPJ, reativa ele
    Retorna (fornecedor, foi_criado_agora)
    """
    cnpj = dados_xml['fornecedor_cnpj']
    
    # Verificar se jÃ¡ existe (ativo ou inativo)
    fornecedor = db.query(Cliente).filter(Cliente.cnpj == cnpj).first()
    
    if fornecedor:
        # Se estiver inativo, reativar e atualizar dados
        if not fornecedor.ativo:
            logger.info(f"ðŸ”„ Reativando fornecedor inativo: {fornecedor.nome}")
            fornecedor.ativo = True
            fornecedor.nome = dados_xml['fornecedor_nome']
            fornecedor.razao_social = dados_xml['fornecedor_nome']
            fornecedor.nome_fantasia = dados_xml.get('fornecedor_fantasia', '')
            fornecedor.inscricao_estadual = dados_xml.get('fornecedor_ie', '')
            fornecedor.endereco = dados_xml.get('fornecedor_endereco', '')
            fornecedor.numero = dados_xml.get('fornecedor_numero', '')
            fornecedor.bairro = dados_xml.get('fornecedor_bairro', '')
            fornecedor.cidade = dados_xml.get('fornecedor_cidade', '')
            fornecedor.estado = dados_xml.get('fornecedor_uf', '')
            fornecedor.cep = dados_xml.get('fornecedor_cep', '')
            fornecedor.telefone = dados_xml.get('fornecedor_telefone', '')
            
            # Se nÃ£o tem cÃ³digo, gerar agora
            if not fornecedor.codigo:
                fornecedor.codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
            
            db.commit()
            db.refresh(fornecedor)
            logger.info(f"âœ… Fornecedor reativado: {fornecedor.nome} (CÃ³digo: {fornecedor.codigo})")
            return (fornecedor, True)
        
        # Se jÃ¡ estÃ¡ ativo, verificar se tem cÃ³digo
        if not fornecedor.codigo:
            fornecedor.codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
            db.commit()
            db.refresh(fornecedor)
            logger.info(f"âœ… CÃ³digo gerado para fornecedor existente: {fornecedor.nome} (CÃ³digo: {fornecedor.codigo})")
        
        return (fornecedor, False)
    
    # Gerar cÃ³digo para novo fornecedor
    codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
    
    # Criar novo fornecedor
    fornecedor = Cliente(
        tipo_cadastro='fornecedor',
        tipo_pessoa='PJ',
        nome=dados_xml['fornecedor_nome'],
        razao_social=dados_xml['fornecedor_nome'],
        nome_fantasia=dados_xml.get('fornecedor_fantasia', ''),
        cnpj=cnpj,
        inscricao_estadual=dados_xml.get('fornecedor_ie', ''),
        endereco=dados_xml.get('fornecedor_endereco', ''),
        numero=dados_xml.get('fornecedor_numero', ''),
        bairro=dados_xml.get('fornecedor_bairro', ''),
        cidade=dados_xml.get('fornecedor_cidade', ''),
        estado=dados_xml.get('fornecedor_uf', ''),
        cep=dados_xml.get('fornecedor_cep', ''),
        telefone=dados_xml.get('fornecedor_telefone', ''),
        codigo=codigo,
        ativo=True,
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    
    logger.info(f"âœ… Fornecedor criado automaticamente: {fornecedor.nome}")
    
    return (fornecedor, True)


def gerar_sku_automatico(prefixo: str, db: Session, user_id: int) -> str:
    """
    Gera um SKU Ãºnico automaticamente para produtos sem cÃ³digo
    Formato: {PREFIXO}-{NÃšMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    # Buscar Ãºltimo SKU com o mesmo prefixo
    ultimo_produto = db.query(Produto).filter(
        Produto.user_id == user_id,
        Produto.codigo.like(f"{prefixo}-%")
    ).order_by(Produto.id.desc()).first()
    
    if ultimo_produto:
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            proximo_numero = 1
    else:
        proximo_numero = 1
    
    # Gerar novo SKU
    novo_sku = f"{prefixo}-{proximo_numero:05d}"
    
    # Verificar se jÃ¡ existe
    existe = db.query(Produto).filter(
        Produto.codigo == novo_sku,
        Produto.user_id == user_id
    ).first()
    
    if existe:
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"
    
    return novo_sku


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """Calcula similaridade entre dois textos (0-1)"""
    if not texto1 or not texto2:
        return 0.0
    return SequenceMatcher(None, texto1.lower(), texto2.lower()).ratio()


def normalizar_codigo_barras(valor: Optional[str]) -> str:
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor))


def obter_detalhe_vinculo_item(item: NotaEntradaItem) -> Dict[str, Optional[str]]:
    """Identifica por qual referencia o item da NF-e coincide com o produto vinculado."""
    if not item or not item.produto_id or not item.produto:
        return {"origem": None, "referencia": None}

    referencia_nf_codigo = (item.codigo_produto or "").strip()
    referencia_nf_ean = normalizar_codigo_barras(item.ean)
    produto_codigo = (item.produto.codigo or "").strip()

    produto_codigos_barras = {
        normalizar_codigo_barras(item.produto.codigo_barras),
        normalizar_codigo_barras(getattr(item.produto, "gtin_ean", None)),
        normalizar_codigo_barras(getattr(item.produto, "gtin_ean_tributario", None)),
    }
    produto_codigos_barras.discard("")

    if referencia_nf_ean and referencia_nf_ean in produto_codigos_barras:
        return {"origem": "codigo_barras", "referencia": referencia_nf_ean}

    if referencia_nf_codigo and referencia_nf_codigo == produto_codigo:
        return {"origem": "sku", "referencia": referencia_nf_codigo}

    codigo_nf_normalizado = normalizar_codigo_barras(referencia_nf_codigo)
    if codigo_nf_normalizado and codigo_nf_normalizado in produto_codigos_barras:
        return {"origem": "codigo_barras", "referencia": codigo_nf_normalizado}

    return {"origem": None, "referencia": None}


def encontrar_produto_similar(
    descricao: str,
    codigo: str,
    db: Session,
    tenant_id = None,
    fornecedor_id: int = None,
    ean: Optional[str] = None,
) -> tuple:
    """
    Encontra produto similar no banco (ativo OU inativo)
    Retorna (produto, confianca, foi_encontrado_inativo, origem_match, referencia_match)
    
    REGRAS DE MATCHING (RIGOROSAS):
    1. SKU exato (codigo) + fornecedor igual = match automático
    2. EAN exato (codigo_barras) = match automático
    3. Caso contrário = NÃO vincula (usuário decide manualmente)
    
    Matching por similaridade de nome foi REMOVIDO para evitar vínculos errados
    """
    # 1. Tentar por SKU exato (código do produto)
    if codigo:
        # Buscar por SKU exato
        query = db.query(Produto).filter(Produto.codigo == codigo)
        if tenant_id is not None:
            query = query.filter(Produto.tenant_id == tenant_id)
        
        # Se tem fornecedor, verificar se produto pertence a ele
        if fornecedor_id:
            # Buscar produto que pertence ao fornecedor
            query_fornecedor = query.join(
                ProdutoFornecedor,
                ProdutoFornecedor.produto_id == Produto.id
            ).filter(
                ProdutoFornecedor.fornecedor_id == fornecedor_id,
                ProdutoFornecedor.ativo == True,
            )
            if tenant_id is not None:
                query_fornecedor = query.join(
                    ProdutoFornecedor,
                    ProdutoFornecedor.produto_id == Produto.id
                ).filter(
                    ProdutoFornecedor.fornecedor_id == fornecedor_id,
                    ProdutoFornecedor.ativo == True,
                    ProdutoFornecedor.tenant_id == tenant_id,
                )

            produto_com_fornecedor = query_fornecedor.first()
            
            if produto_com_fornecedor:
                foi_inativo = not produto_com_fornecedor.ativo
                logger.info(f"✅ Match por SKU + Fornecedor: {produto_com_fornecedor.nome}")
                return (produto_com_fornecedor, 1.0, foi_inativo, "sku", codigo)
        
        # Se não encontrou com fornecedor, buscar só por SKU
        produto = query.first()
        if produto:
            foi_inativo = not produto.ativo
            logger.info(f"✅ Match por SKU: {produto.nome}")
            return (produto, 1.0, foi_inativo, "sku", codigo)
    
    # 2. Tentar por EAN/Código de Barras exato
    referencias_codigo_barras = []
    ean_normalizado = normalizar_codigo_barras(ean)
    codigo_normalizado = normalizar_codigo_barras(codigo)

    if ean_normalizado:
        referencias_codigo_barras.append(ean_normalizado)
    if codigo_normalizado and codigo_normalizado not in referencias_codigo_barras:
        referencias_codigo_barras.append(codigo_normalizado)

    for referencia in referencias_codigo_barras:
        query = db.query(Produto).filter(
            or_(
                Produto.codigo_barras == referencia,
                Produto.gtin_ean == referencia,
                Produto.gtin_ean_tributario == referencia,
            )
        )
        if tenant_id is not None:
            query = query.filter(Produto.tenant_id == tenant_id)

        produto = query.first()
        
        if produto:
            foi_inativo = not produto.ativo
            logger.info(f"✅ Match por EAN: {produto.nome}")
            return (produto, 1.0, foi_inativo, "codigo_barras", referencia)
    
    # 3. NÃO fazer matching automático por nome/similaridade
    # Usuário deve vincular manualmente para evitar erros
    logger.info(f"⚠️ Nenhum match encontrado para: {descricao[:50]} (SKU: {codigo})")
    return (None, 0, False, None, None)


def criar_contas_pagar_da_nota(nota: NotaEntrada, dados_xml: dict, db: Session, user_id: int, tenant_id: str) -> List[int]:
    """
    Cria contas a pagar automaticamente com base nas duplicatas do XML
    FASE 4: IntegraÃ§Ã£o NF-e â†’ Financeiro
    Retorna lista de IDs das contas criadas
    """
    logger.info(f"ðŸ’° Gerando contas a pagar para nota {nota.numero_nota}...")
    
    contas_criadas = []
    
    # Buscar duplicatas no XML (tag <dup>)
    duplicatas = dados_xml.get('duplicatas', [])
    
    if not duplicatas:
        # Se nÃ£o tem duplicatas, criar uma Ãºnica conta com vencimento em 30 dias
        logger.info("   âš ï¸ Sem duplicatas no XML, criando conta Ãºnica com vencimento +30 dias")
        duplicatas = [{
            'numero': f"{nota.numero_nota}-1",
            'vencimento': datetime.now() + timedelta(days=30),
            'valor': nota.valor_total
        }]
    
    total_duplicatas = len(duplicatas)
    eh_parcelado = total_duplicatas > 1
    
    for idx, dup in enumerate(duplicatas, 1):
        try:
            # Valor vem em reais do XML, usar Decimal para precisÃ£o
            from decimal import Decimal
            valor_reais = Decimal(str(dup['valor']))
            
            # Criar conta a pagar
            conta = ContaPagar(
                fornecedor_id=nota.fornecedor_id,
                descricao=f"NF-e {nota.numero_nota} - Parcela {dup['numero']}",
                valor_original=valor_reais,
                valor_final=valor_reais,
                valor_pago=Decimal('0'),
                data_emissao=nota.data_emissao,
                data_vencimento=dup['vencimento'],
                status='pendente',
                eh_parcelado=eh_parcelado,
                numero_parcela=idx if eh_parcelado else None,
                total_parcelas=total_duplicatas if eh_parcelado else None,
                nota_entrada_id=nota.id,
                nfe_numero=str(nota.numero_nota),
                documento=dup.get('numero', ''),  # NÃºmero da duplicata do XML (n1, n2, etc)
                percentual_online=nota.percentual_online or 0,  # Herdar rateio da nota
                percentual_loja=nota.percentual_loja or 100,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            db.add(conta)
            db.flush()
            
            contas_criadas.append(conta.id)
            
            logger.info(f"   âœ… Conta criada: {dup['numero']} - R$ {dup['valor']:.2f} - Venc: {dup['vencimento'].strftime('%d/%m/%Y')}")
            
        except Exception as e:
            logger.error(f"   âŒ Erro ao criar conta da duplicata {dup.get('numero')}: {str(e)}")
            raise
    
    logger.info(f"âœ… Total de contas criadas: {len(contas_criadas)}")
    return contas_criadas


# ============================================================================
# UPLOAD DE XML
# ============================================================================

@router.post("/upload")
async def upload_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Upload de XML de NF-e e parse automÃ¡tico"""
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ“„ Upload de XML - Arquivo: {file.filename}")
    logger.info(f"   - Content-type: {file.content_type}")
    logger.info(f"   - UsuÃ¡rio: {current_user.email} (ID: {current_user.id})")
    
    try:
        # Validar extensÃ£o
        if not file.filename.endswith('.xml'):
            logger.error(f"âŒ Arquivo invÃ¡lido: {file.filename} (nÃ£o Ã© .xml)")
            raise HTTPException(status_code=400, detail="Arquivo deve ser .xml")
        
        # Ler conteÃºdo
        logger.info("ðŸ“– Lendo conteÃºdo do arquivo...")
        xml_content = await file.read()
        logger.info(f"   - Tamanho: {len(xml_content)} bytes")
        
        xml_str = xml_content.decode('utf-8')
        logger.info("âœ… Arquivo decodificado com sucesso")
        
        # Parse do XML
        logger.info("ðŸ” Fazendo parse do XML...")
        try:
            dados_nfe = parse_nfe_xml(xml_str)
            logger.info("âœ… Parse concluÃ­do:")
            logger.info(f"   - Chave: {dados_nfe.get('chave_acesso', 'N/A')}")
            logger.info(f"   - NÃºmero: {dados_nfe.get('numero_nota', 'N/A')}")
            logger.info(f"   - Fornecedor: {dados_nfe.get('fornecedor_nome', 'N/A')}")
            logger.info(f"   - Valor total: R$ {dados_nfe.get('valor_total', 0):.2f}")
            logger.info(f"   - Itens: {len(dados_nfe.get('itens', []))}")
        except ValueError as e:
            logger.error(f"âŒ Erro no parse do XML: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(status_code=400, detail=f"Erro ao processar XML: {str(e)}")
        except Exception as e:
            logger.error(f"âŒ Erro inesperado no parse: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(status_code=500, detail=f"Erro interno ao processar XML: {str(e)}")
        
        # Verificar se nota jÃ¡ existe
        logger.info(f"ðŸ”Ž Verificando se nota jÃ¡ existe (chave: {dados_nfe['chave_acesso']})...")
        nota_existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == dados_nfe['chave_acesso']
        ).first()
        
        if nota_existente:
            logger.warning(f"âš ï¸ Nota jÃ¡ cadastrada! ID: {nota_existente.id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Nota fiscal jÃ¡ cadastrada (ID: {nota_existente.id})"
            )
        
        logger.info("âœ… Nota nÃ£o existe, prosseguindo...")
        
        # Buscar ou criar fornecedor automaticamente
        logger.info(f"ðŸ”Ž Buscando fornecedor por CNPJ: {dados_nfe['fornecedor_cnpj']}...")
        fornecedor = db.query(Cliente).filter(
            Cliente.cnpj == dados_nfe['fornecedor_cnpj'],
            Cliente.ativo == True
        ).first()
        
        fornecedor_criado_automaticamente = False
        
        if fornecedor:
            logger.info(f"âœ… Fornecedor encontrado: {fornecedor.nome} (ID: {fornecedor.id})")
        else:
            logger.warning(f"âš ï¸ Fornecedor nÃ£o cadastrado, criando automaticamente...")
            try:
                fornecedor, fornecedor_criado_automaticamente = criar_fornecedor_automatico(dados_nfe, db, current_user, tenant_id)
                logger.info(f"âœ… Fornecedor criado: {fornecedor.nome} (ID: {fornecedor.id})")
            except Exception as e:
                logger.error(f"âŒ Erro ao criar fornecedor: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Erro ao criar fornecedor: {str(e)}")
        
        # Criar nota
        logger.info("ðŸ’¾ Criando registro da nota no banco...")
        nota = NotaEntrada(
            numero_nota=dados_nfe['numero_nota'],
            serie=dados_nfe['serie'],
            chave_acesso=dados_nfe['chave_acesso'],
            fornecedor_cnpj=dados_nfe['fornecedor_cnpj'],
            fornecedor_nome=dados_nfe['fornecedor_nome'],
            fornecedor_id=fornecedor.id if fornecedor else None,
            data_emissao=dados_nfe['data_emissao'],
            data_entrada=datetime.utcnow(),
            valor_produtos=dados_nfe['valor_produtos'],
            valor_frete=dados_nfe['valor_frete'],
            valor_desconto=dados_nfe['valor_desconto'],
            valor_total=dados_nfe['valor_total'],
            xml_content=xml_str,
            status='pendente',
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        
        db.add(nota)
        db.flush()
        logger.info(f"âœ… Nota criada com ID: {nota.id}")
        
        # Processar itens e fazer matching automÃ¡tico
        logger.info(f"ðŸ”„ Processando {len(dados_nfe['itens'])} itens...")
        vinculados = 0
        nao_vinculados = 0
        produtos_reativados = 0
        
        for item_data in dados_nfe['itens']:
            # Tentar encontrar produto similar (com fornecedor para matching mais preciso)
            produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = encontrar_produto_similar(
                item_data['descricao'],
                item_data['codigo_produto'],
                db,
                tenant_id=tenant_id,
                fornecedor_id=fornecedor.id if fornecedor else None,
                ean=item_data.get('ean')
            )
            
            if produto:
                vinculados += 1
                if foi_inativo:
                    produtos_reativados += 1
                produto_id = produto.id
                vinculado = True
                item_status = 'vinculado'
                
                # âœ… Apenas gerar SKU se necessÃ¡rio (nÃ£o atualizar outros dados no upload)
                if not produto.codigo or produto.codigo.strip() == '':
                    novo_sku = gerar_sku_automatico('PROD', db, current_user.id)
                    produto.codigo = novo_sku
                    logger.info(f"  ðŸ”– SKU gerado automaticamente: {novo_sku}")
                
                # Log de status do produto
                status_msg = " (INATIVO - serÃ¡ reativado no processamento)" if foi_inativo else ""
                detalhe_match = ""
                if origem_vinculo and referencia_vinculo:
                    detalhe_match = f" [match por {origem_vinculo}: {referencia_vinculo}]"
                logger.info(
                    f"  âœ… {item_data['descricao'][:50]} â†’ "
                    f"{produto.nome} (confianÃ§a: {confianca:.0%}){detalhe_match}{status_msg}"
                )
            else:
                nao_vinculados += 1
                produto_id = None
                vinculado = False
                item_status = 'nao_vinculado'
                confianca = 0
                logger.warning(f"  âš ï¸  {item_data['descricao'][:50]} â†’ NÃ£o vinculado")
            
            # Criar item
            item = NotaEntradaItem(
                nota_entrada_id=nota.id,
                numero_item=item_data['numero_item'],
                codigo_produto=item_data['codigo_produto'],
                descricao=item_data['descricao'],
                ncm=item_data['ncm'],
                cest=item_data.get('cest'),
                cfop=item_data['cfop'],
                origem=item_data.get('origem', '0'),
                aliquota_icms=item_data.get('aliquota_icms', 0),
                aliquota_pis=item_data.get('aliquota_pis', 0),
                aliquota_cofins=item_data.get('aliquota_cofins', 0),
                unidade=item_data['unidade'],
                quantidade=item_data['quantidade'],
                valor_unitario=item_data['valor_unitario'],
                valor_total=item_data['valor_total'],
                ean=item_data.get('ean'),
                lote=item_data.get('lote'),
                data_validade=item_data.get('data_validade'),
                produto_id=produto_id,
                vinculado=vinculado,
                confianca_vinculo=confianca,
                status=item_status,
                tenant_id=tenant_id
            )
            db.add(item)
        
        # Atualizar contadores
        nota.produtos_vinculados = vinculados
        nota.produtos_nao_vinculados = nao_vinculados
        
        db.commit()
        db.refresh(nota)
        
        # Log de resumo com informaÃ§Ã£o de reativaÃ§Ãµes
        if produtos_reativados > 0:
            logger.info(f"â™»ï¸  {produtos_reativados} produto(s) inativo(s) foram reativados automaticamente")
        
        logger.info(
            f"âœ… Nota {nota.numero_nota} processada: "
            f"{vinculados} vinculados, {nao_vinculados} nÃ£o vinculados"
        )
        
        return {
            "message": "XML processado com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe['itens']),
            "produtos_vinculados": vinculados,
            "produtos_nao_vinculados": nao_vinculados,
            "produtos_reativados": produtos_reativados
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (jÃ¡ tratadas)
        raise
    except Exception as e:
        logger.error(f"âŒ Erro inesperado no upload: {str(e)}")
        logger.error(f"   - Tipo: {type(e).__name__}")
        logger.error(f"   - Stack: {e.__traceback__}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {str(e)}")


# ============================================================================
# UPLOAD EM LOTE DE MÃšLTIPLOS XMLs
# ============================================================================

@router.post("/upload-lote")
async def upload_lote_xml(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Upload de mÃºltiplos XMLs de NF-e e processamento em lote
    Retorna resumo de sucessos e erros
    """
    logger.info(f"ðŸ“¦ Upload em lote - {len(files)} arquivos")
    logger.info(f"   - UsuÃ¡rio: {current_user.email}")
    
    resultados = []
    sucessos = 0
    erros = 0
    
    for i, file in enumerate(files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"ðŸ“„ Processando arquivo {i}/{len(files)}: {file.filename}")
        logger.info(f"{'='*60}")
        
        resultado = {
            "arquivo": file.filename,
            "ordem": i,
            "sucesso": False,
            "mensagem": "",
            "nota_id": None,
            "numero_nota": None,
            "fornecedor": None,
            "valor_total": None,
            "produtos_vinculados": None,
            "produtos_nao_vinculados": None
        }
        
        try:
            # Validar extensÃ£o
            if not file.filename.endswith('.xml'):
                raise ValueError("Arquivo deve ser .xml")
            
            # Ler e decodificar
            xml_content = await file.read()
            xml_str = xml_content.decode('utf-8')
            
            # Parse do XML
            dados_nfe = parse_nfe_xml(xml_str)
            
            # Verificar se nota jÃ¡ existe
            nota_existente = db.query(NotaEntrada).filter(
                NotaEntrada.chave_acesso == dados_nfe['chave_acesso']
            ).first()
            
            if nota_existente:
                raise ValueError(f"Nota jÃ¡ cadastrada (ID: {nota_existente.id})")
            
            # Buscar ou criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados_nfe['fornecedor_cnpj']
            ).first()
            
            fornecedor_criado = False
            if not fornecedor:
                fornecedor, fornecedor_criado = criar_fornecedor_automatico(dados_nfe, db)
            
            # Criar nota
            nota = NotaEntrada(
                numero_nota=dados_nfe['numero_nota'],
                serie=dados_nfe['serie'],
                chave_acesso=dados_nfe['chave_acesso'],
                fornecedor_cnpj=dados_nfe['fornecedor_cnpj'],
                fornecedor_nome=dados_nfe['fornecedor_nome'],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe['data_emissao'],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe['valor_produtos'],
                valor_frete=dados_nfe['valor_frete'],
                valor_desconto=dados_nfe['valor_desconto'],
                valor_total=dados_nfe['valor_total'],
                xml_content=xml_str,
                status='pendente',
                user_id=current_user.id
            )
            
            db.add(nota)
            db.flush()
            
            # Processar itens com matching
            vinculados = 0
            nao_vinculados = 0
            produtos_reativados = 0
            
            for item_data in dados_nfe['itens']:
                produto, confianca, foi_reativado, _, _ = encontrar_produto_similar(
                    item_data['descricao'],
                    item_data['codigo_produto'],
                    db,
                    tenant_id=tenant_id,
                    fornecedor_id=None,
                    ean=item_data.get('ean')
                )
                
                if produto:
                    vinculados += 1
                    if foi_reativado:
                        produtos_reativados += 1
                    produto_id = produto.id
                    vinculado = True
                    item_status = 'vinculado'
                else:
                    nao_vinculados += 1
                    produto_id = None
                    vinculado = False
                    item_status = 'nao_vinculado'
                    confianca = 0
                
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data['numero_item'],
                    codigo_produto=item_data['codigo_produto'],
                    descricao=item_data['descricao'],
                    ncm=item_data['ncm'],
                    cfop=item_data['cfop'],
                    unidade=item_data['unidade'],
                    quantidade=item_data['quantidade'],
                    valor_unitario=item_data['valor_unitario'],
                    valor_total=item_data['valor_total'],
                    ean=item_data.get('ean'),
                    lote=item_data.get('lote'),
                    data_validade=item_data.get('data_validade'),
                    produto_id=produto_id,
                    vinculado=vinculado,
                    confianca_vinculo=confianca,
                    status=item_status
                )
                db.add(item)
            
            # Atualizar contadores
            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            
            db.commit()
            db.refresh(nota)
            
            # Log de reativaÃ§Ãµes
            if produtos_reativados > 0:
                logger.info(f"â™»ï¸  {produtos_reativados} produto(s) inativo(s) reativado(s) - Nota {nota.numero_nota}")
            
            # Sucesso!
            resultado["sucesso"] = True
            resultado["mensagem"] = "Processado com sucesso"
            resultado["nota_id"] = nota.id
            resultado["numero_nota"] = nota.numero_nota
            resultado["fornecedor"] = nota.fornecedor_nome
            resultado["valor_total"] = nota.valor_total
            resultado["produtos_vinculados"] = vinculados
            resultado["produtos_nao_vinculados"] = nao_vinculados
            
            sucessos += 1
            logger.info(f"âœ… {file.filename} processado com sucesso (Nota {nota.numero_nota})")
            
        except ValueError as e:
            resultado["mensagem"] = f"Erro de validaÃ§Ã£o: {str(e)}"
            erros += 1
            logger.error(f"âŒ {file.filename}: {str(e)}")
            db.rollback()
            
        except Exception as e:
            resultado["mensagem"] = f"Erro ao processar: {str(e)}"
            erros += 1
            logger.error(f"âŒ {file.filename}: Erro inesperado - {str(e)}")
            db.rollback()
        
        resultados.append(resultado)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"ðŸ“Š RESUMO DO LOTE:")
    logger.info(f"   - Total de arquivos: {len(files)}")
    logger.info(f"   - âœ… Sucessos: {sucessos}")
    logger.info(f"   - âŒ Erros: {erros}")
    logger.info(f"{'='*60}\n")
    
    return {
        "message": f"Processamento em lote concluÃ­do: {sucessos} sucessos, {erros} erros",
        "total_arquivos": len(files),
        "sucessos": sucessos,
        "erros": erros,
        "resultados": resultados
    }


# ============================================================================
# LISTAR NOTAS
# ============================================================================

@router.get("/", response_model=List[NotaEntradaResponse])
def listar_notas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    fornecedor_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista notas de entrada"""
    user, tenant_id = user_and_tenant
    
    query = db.query(NotaEntrada).options(joinedload(NotaEntrada.itens)).filter(NotaEntrada.tenant_id == tenant_id)
    
    if status:
        query = query.filter(NotaEntrada.status == status)
    if fornecedor_id:
        query = query.filter(NotaEntrada.fornecedor_id == fornecedor_id)
    
    query = query.order_by(desc(NotaEntrada.data_entrada))
    
    total = query.count()
    notas = query.offset(offset).limit(limit).all()
    
    logger.info(f"ðŸ“‹ {len(notas)} notas encontradas (total: {total})")
    
    respostas = []
    for nota in notas:
        conferencia = _resumir_conferencia_nota(nota)
        respostas.append(
            NotaEntradaResponse.model_validate(
                {
                    "id": nota.id,
                    "numero_nota": nota.numero_nota,
                    "serie": nota.serie,
                    "chave_acesso": nota.chave_acesso,
                    "fornecedor_nome": nota.fornecedor_nome,
                    "fornecedor_cnpj": nota.fornecedor_cnpj,
                    "fornecedor_id": nota.fornecedor_id,
                    "data_emissao": nota.data_emissao,
                    "valor_total": nota.valor_total,
                    "status": nota.status,
                    "produtos_vinculados": nota.produtos_vinculados,
                    "produtos_nao_vinculados": nota.produtos_nao_vinculados,
                    "entrada_estoque_realizada": nota.entrada_estoque_realizada,
                    "conferencia_status": conferencia["status"],
                    "divergencias_count": conferencia["itens_com_divergencia"],
                }
            )
        )

    return respostas


# ============================================================================
# BUSCAR NOTA POR ID
# ============================================================================

@router.get("/{nota_id}")
def buscar_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca nota completa com itens"""
    user, tenant_id = user_and_tenant
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    # Verificar se fornecedor foi criado recentemente (Ãºltimas 24h)
    fornecedor_criado_automaticamente = False
    if nota.fornecedor_id:
        fornecedor = db.query(Cliente).filter(Cliente.id == nota.fornecedor_id).first()
        if fornecedor and fornecedor.created_at:
            # Se o fornecedor foi criado menos de 24h antes da nota
            # Garantir compatibilidade de timezone
            data_entrada = nota.data_entrada.replace(tzinfo=None) if nota.data_entrada.tzinfo else nota.data_entrada
            created_at = fornecedor.created_at.replace(tzinfo=None) if fornecedor.created_at.tzinfo else fornecedor.created_at
            diferenca = data_entrada - created_at
            if diferenca < timedelta(hours=24):
                fornecedor_criado_automaticamente = True
    
    composicoes_custo = calcular_composicao_custos_nota(nota)
    itens_formatados = []
    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao,
            item.quantidade,
            item.valor_unitario,
            item.valor_total
        )
        conferencia_item = _serializar_conferencia_item(item)
        itens_formatados.append({
            "id": item.id,
            "numero_item": item.numero_item,
            "codigo_produto": item.codigo_produto,
            "descricao": item.descricao,
            "ncm": item.ncm,
            "cfop": item.cfop,
            "unidade": item.unidade,
            "quantidade": item.quantidade,
            "valor_unitario": item.valor_unitario,
            "valor_total": item.valor_total,
            "ean": item.ean,
            "lote": item.lote,
            "data_validade": item.data_validade.isoformat() if item.data_validade else None,
            "produto_id": item.produto_id,
            "produto_nome": item.produto.nome if item.produto else None,
            "produto_codigo": item.produto.codigo if item.produto else None,
            "produto_ean": (
                item.produto.codigo_barras
                or item.produto.gtin_ean
                or item.produto.gtin_ean_tributario
            ) if item.produto else None,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            "origem_vinculo_automatico": detalhe_vinculo["origem"],
            "referencia_vinculo": detalhe_vinculo["referencia"],
            "status": item.status,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "quantidade_efetiva": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario": composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]),
            "custo_aquisicao_total": composicao_custo.get("custo_aquisicao_total", item.valor_total),
            "composicao_custo": composicao_custo,
            **conferencia_item,
        })

    return _montar_payload_nota(
        nota,
        itens_formatados,
        fornecedor_criado_automaticamente=fornecedor_criado_automaticamente,
    )


@router.post("/{nota_id}/conferencia")
def salvar_conferencia_nota(
    nota_id: int,
    payload: ConferenciaNotaPayload,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Salva a conferência física da NF, assumindo tudo OK por padrão e ajustando apenas exceções."""
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_por_id = {item.id: item for item in nota.itens}
    payload_por_id = {item.item_id: item for item in payload.itens}

    itens_invalidos = [item_id for item_id in payload_por_id if item_id not in itens_por_id]
    if itens_invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Itens de conferência inválidos: {', '.join(str(item_id) for item_id in itens_invalidos)}",
        )

    for item in nota.itens:
        quantidade_nf = _round_quantity(item.quantidade)
        payload_item = payload_por_id.get(item.id)

        quantidade_conferida = item.quantidade_conferida if item.quantidade_conferida is not None else quantidade_nf
        quantidade_avariada = item.quantidade_avariada or 0
        observacao_conferencia = item.observacao_conferencia
        acao_sugerida = item.acao_sugerida

        if payload_item:
            quantidade_conferida = _round_quantity(payload_item.quantidade_conferida)
            quantidade_avariada = _round_quantity(payload_item.quantidade_avariada)
            observacao_conferencia = payload_item.observacao_conferencia
            acao_sugerida = payload_item.acao_sugerida

        if quantidade_conferida < 0 or quantidade_avariada < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidades inválidas para o item {item.numero_item}.",
            )

        if quantidade_conferida > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A quantidade conferida do item {item.numero_item} não pode ser maior que a quantidade da NF.",
            )

        if quantidade_conferida + quantidade_avariada > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A soma de conferida + avariada do item {item.numero_item} não pode ultrapassar a quantidade da NF.",
            )

        tem_divergencia = (quantidade_conferida + quantidade_avariada) < quantidade_nf or quantidade_avariada > 0

        item.quantidade_conferida = quantidade_conferida
        item.quantidade_avariada = quantidade_avariada
        item.observacao_conferencia = _normalizar_texto_curto(observacao_conferencia)
        item.acao_sugerida = _obter_acao_conferencia(acao_sugerida, tem_divergencia)

    nota.conferencia_observacoes = _normalizar_texto_curto(payload.observacao_geral)
    nota.conferencia_realizada_em = datetime.utcnow()

    resumo = _resumir_conferencia_nota(nota)
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    nota.conferencia_user_id = current_user.id

    db.commit()

    return {
        "message": "Conferência salva com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.post("/{nota_id}/conferencia/desfazer")
def desfazer_conferencia_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Limpa a conferencia registrada da NF antes do processamento do estoque."""
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel desfazer a conferencia apos processar a entrada no estoque.",
        )

    for item in nota.itens:
        item.quantidade_conferida = None
        item.quantidade_avariada = 0
        item.observacao_conferencia = None
        item.acao_sugerida = "sem_acao"

    nota.conferencia_observacoes = None
    nota.conferencia_realizada_em = None
    nota.conferencia_status = CONFERENCIA_STATUS_NAO_INICIADA
    nota.conferencia_user_id = None

    db.commit()

    return {
        "message": "Conferencia desfeita com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.get("/{nota_id}/devolucao-draft")
def gerar_rascunho_nf_devolucao(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Gera um rascunho de NF de devolução com base nos itens avariados da conferência."""
    _, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_devolucao = []
    valor_total_estimado = 0.0

    for item in nota.itens:
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_devolucao = conferencia_item["quantidade_para_devolucao"]
        if quantidade_devolucao <= 0:
            continue

        valor_total_item = round(quantidade_devolucao * float(item.valor_unitario or 0), 2)
        valor_total_estimado += valor_total_item
        itens_devolucao.append(
            {
                "item_id": item.id,
                "numero_item_nf": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "unidade": item.unidade,
                "quantidade_devolucao": quantidade_devolucao,
                "valor_unitario": float(item.valor_unitario or 0),
                "valor_total": valor_total_item,
                "observacao_conferencia": conferencia_item["observacao_conferencia"],
            }
        )

    observacao_padrao = (
        f"Rascunho de NF de devolução referente à NF de entrada {nota.numero_nota}. "
        "Gerado a partir das divergências por avaria registradas na conferência física."
    )

    return {
        "disponivel": len(itens_devolucao) > 0,
        "nota_entrada_id": nota.id,
        "numero_nota_origem": nota.numero_nota,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "data_emissao_origem": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "itens": itens_devolucao,
        "quantidade_itens": len(itens_devolucao),
        "valor_total_estimado": round(valor_total_estimado, 2),
        "observacao_sugerida": observacao_padrao,
        "message": (
            "Rascunho gerado com sucesso"
            if itens_devolucao
            else "Nenhuma divergência com avaria foi encontrada para gerar NF de devolução"
        ),
    }


def _buscar_nota_item_por_tenant(
    nota_id: int,
    item_id: int,
    tenant_id,
    db: Session,
) -> tuple[NotaEntrada, NotaEntradaItem]:
    nota = db.query(NotaEntrada).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id,
    ).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id,
        NotaEntradaItem.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")

    return nota, item


def _buscar_produto_por_codigo_global(
    db: Session,
    codigo: Optional[str],
):
    codigo_limpo = (codigo or "").strip()
    if not codigo_limpo:
        return None

    return db.query(Produto).filter(
        Produto.codigo == codigo_limpo,
    ).first()


def _produto_pertence_ao_tenant(produto: Optional[Produto], tenant_id) -> bool:
    if not produto:
        return False
    return getattr(produto, "tenant_id", None) == tenant_id


def _gerar_candidatos_sku_disponiveis(
    sku_base: str,
    prefixo: str,
    db: Session,
    tenant_id,
    user_id: int,
) -> List[Dict[str, Any]]:
    sugestoes: List[Dict[str, Any]] = []
    vistos = set()

    def adicionar_candidato(sku: Optional[str], descricao: str) -> None:
        sku_limpo = (sku or "").strip()
        if not sku_limpo or sku_limpo in vistos:
            return
        vistos.add(sku_limpo)

        existe = _buscar_produto_por_codigo_global(db, sku_limpo)
        if existe:
            return

        sugestoes.append({
            "sku": sku_limpo,
            "descricao": descricao,
            "disponivel": True,
            "padrao": False,
        })

    sku_base_limpo = (sku_base or "").strip()
    prefixo_limpo = (prefixo or "PROD").strip() or "PROD"

    if sku_base_limpo:
        adicionar_candidato(
            f"{prefixo_limpo}-{sku_base_limpo}",
            f"Prefixo {prefixo_limpo} + cÃ³digo do fornecedor",
        )
        adicionar_candidato(
            f"{sku_base_limpo}-{prefixo_limpo}",
            f"CÃ³digo do fornecedor + sufixo {prefixo_limpo}",
        )
        for indice in range(1, 6):
            adicionar_candidato(
                f"{prefixo_limpo}-{sku_base_limpo}-V{indice}",
                f"VariaÃ§Ã£o {indice} com prefixo {prefixo_limpo}",
            )

    adicionar_candidato(
        gerar_sku_automatico(prefixo_limpo, db, user_id),
        f"Sequencial automÃ¡tico com prefixo {prefixo_limpo}",
    )
    for indice in range(1, 6):
        adicionar_candidato(
            f"{prefixo_limpo}-{indice:05d}",
            f"Sequencial manual {indice} com prefixo {prefixo_limpo}",
        )

    if sugestoes:
        sugestoes[0]["padrao"] = True

    return sugestoes


def _montar_sugestao_sku_produto(
    nota: NotaEntrada,
    item: NotaEntradaItem,
    db: Session,
    tenant_id,
    user_id: int,
    sku_base_customizado: Optional[str] = None,
) -> Dict[str, Any]:
    fornecedor_nome = (nota.fornecedor_nome or "").strip()
    prefixo = gerar_prefixo_fornecedor(fornecedor_nome) if fornecedor_nome else "PROD"

    sku_base = (sku_base_customizado or item.codigo_produto or "").strip()
    if not sku_base:
        descricao_base = re.sub(r"[^A-Z0-9]", "", (item.descricao or "").upper())
        sku_base = (descricao_base[:10] or gerar_sku_automatico(prefixo, db, user_id)).strip()

    produto_existente = _buscar_produto_por_codigo_global(db, sku_base)
    composicoes_custo = calcular_composicao_custos_nota(nota)
    composicao_item = composicoes_custo.get(item.id, {})

    if produto_existente:
        sugestoes = _gerar_candidatos_sku_disponiveis(
            sku_base=sku_base,
            prefixo=prefixo,
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    else:
        sugestoes = [{
            "sku": sku_base,
            "descricao": "CÃ³digo original do fornecedor",
            "disponivel": True,
            "padrao": True,
        }]

    payload: Dict[str, Any] = {
        "item_id": item.id,
        "descricao_item": item.descricao,
        "codigo_fornecedor": item.codigo_produto,
        "fornecedor": nota.fornecedor_nome,
        "prefixo_sugerido": prefixo,
        "sku_proposto": sku_base,
        "ja_existe": produto_existente is not None,
        "sugestoes": sugestoes,
        "dados_produto": {
            "nome": item.descricao,
            "unidade": item.unidade,
            "preco_custo": composicao_item.get("custo_aquisicao_unitario", item.valor_unitario),
            "ncm": item.ncm if hasattr(item, "ncm") else None,
            "ean": item.ean if hasattr(item, "ean") else None,
        },
    }

    if produto_existente:
        nome_produto_existente = (
            produto_existente.nome
            if _produto_pertence_ao_tenant(produto_existente, tenant_id)
            else "SKU já utilizado em outro cadastro"
        )
        payload["produto_existente"] = {
            "id": produto_existente.id if _produto_pertence_ao_tenant(produto_existente, tenant_id) else None,
            "codigo": produto_existente.codigo,
            "nome": nome_produto_existente,
        }

    return payload


# ============================================================================
# VINCULAR PRODUTO MANUALMENTE
# ============================================================================

@router.post("/{nota_id}/itens/{item_id}/vincular")
def vincular_produto(
    nota_id: int,
    item_id: int,
    produto_id: int = Query(..., description="ID do produto a vincular"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Vincula item a um produto manualmente"""
    current_user, tenant_id = user_and_tenant
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Atualizar vinculaÃ§Ã£o
    foi_nao_vinculado = not item.vinculado
    
    item.produto_id = produto_id
    item.vinculado = True
    item.confianca_vinculo = 1.0  # Manual = 100%
    item.status = 'vinculado'
    
    # Atualizar dados fiscais do produto com informações do XML (se disponíveis e produto não tiver)
    atualizar_fiscal = False
    if not produto.ncm and item.ncm:
        produto.ncm = item.ncm
        atualizar_fiscal = True
    if not produto.cfop and item.cfop:
        produto.cfop = item.cfop
        atualizar_fiscal = True
    if not produto.cest and hasattr(item, 'cest') and item.cest:
        produto.cest = item.cest
        atualizar_fiscal = True
    if not produto.origem and hasattr(item, 'origem') and item.origem:
        produto.origem = item.origem
        atualizar_fiscal = True
    if produto.aliquota_icms is None and hasattr(item, 'aliquota_icms') and item.aliquota_icms is not None:
        produto.aliquota_icms = item.aliquota_icms
        atualizar_fiscal = True
    if produto.aliquota_pis is None and hasattr(item, 'aliquota_pis') and item.aliquota_pis is not None:
        produto.aliquota_pis = item.aliquota_pis
        atualizar_fiscal = True
    if produto.aliquota_cofins is None and hasattr(item, 'aliquota_cofins') and item.aliquota_cofins is not None:
        produto.aliquota_cofins = item.aliquota_cofins
        atualizar_fiscal = True
    
    if atualizar_fiscal:
        logger.info(f"📋 Dados fiscais do produto {produto.id} atualizados com informações da NF")
    
    # Vincular produto ao fornecedor da nota automaticamente
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    custo_item_vinculo = item.valor_unitario
    if nota:
        composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
        custo_item_vinculo = composicao_custo.get("custo_aquisicao_unitario", item.valor_unitario)

    if nota and nota.fornecedor_id:
        # Busca o fornecedor PRINCIPAL atual do produto
        vinculo_principal = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == produto_id,
            ProdutoFornecedor.e_principal == True
        ).first()

        if not vinculo_principal:
            # Produto sem fornecedor -> registra o fornecedor da NF como principal
            novo_vinculo = ProdutoFornecedor(
                produto_id=produto_id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=custo_item_vinculo,
                e_principal=True,
                ativo=True,
                tenant_id=tenant_id
            )
            db.add(novo_vinculo)
            logger.info(f"✅ Produto {produto_id} vinculado ao fornecedor {nota.fornecedor_id} como principal")
        elif vinculo_principal.fornecedor_id == nota.fornecedor_id:
            # Mesmo fornecedor -> só atualiza o preço
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(f"🔄 Preço do fornecedor principal do produto {produto_id} atualizado")
        else:
            # Fornecedor diferente -> troca o fornecedor principal + atualiza preço
            vinculo_principal.fornecedor_id = nota.fornecedor_id
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(f"🔄 Fornecedor principal do produto {produto_id} alterado para {nota.fornecedor_id}")
    # Atualizar contadores da nota
    if foi_nao_vinculado:
        nota.produtos_vinculados += 1
        nota.produtos_nao_vinculados -= 1
    
    db.commit()
    
    logger.info(f"âœ… Item {item_id} vinculado manualmente ao produto {produto.nome}")
    
    return {
        "message": "Produto vinculado com sucesso",
        "item_id": item.id,
        "produto_id": produto.id,
        "produto_nome": produto.nome
    }


# ============================================================================
# DESVINCULAR PRODUTO
# ============================================================================

@router.post("/{nota_id}/itens/{item_id}/desvincular")
def desvincular_produto(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Remove vinculaÃ§Ã£o de um item com produto"""
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    if not item.produto_id:
        raise HTTPException(status_code=400, detail="Item nÃ£o estÃ¡ vinculado a nenhum produto")
    
    # Remover vinculaÃ§Ã£o
    item.produto_id = None
    item.vinculado = False
    item.confianca_vinculo = None
    item.status = 'pendente'
    
    # Atualizar contadores da nota
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    nota.produtos_vinculados -= 1
    nota.produtos_nao_vinculados += 1
    
    db.commit()
    
    logger.info(f"âŒ Item {item_id} desvinculado")
    
    return {
        "message": "Produto desvinculado com sucesso",
        "item_id": item.id
    }


# ============================================================================
# CONFIGURAR RATEIO DA NOTA (100% ONLINE, 100% LOJA, OU PARCIAL)
# ============================================================================

class RateioNotaRequest(BaseModel):
    tipo_rateio: str  # 'online', 'loja', 'parcial'


@router.post("/{nota_id}/rateio")
def configurar_rateio_nota(
    nota_id: int,
    rateio: RateioNotaRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configura tipo de rateio da nota inteira:
    - 'online': 100% online
    - 'loja': 100% loja fÃ­sica  
    - 'parcial': configurar por produto
    """
    current_user, tenant_id = user_and_tenant
    
    if rateio.tipo_rateio not in ['online', 'loja', 'parcial']:
        raise HTTPException(status_code=400, detail="Tipo de rateio invÃ¡lido. Use: online, loja ou parcial")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    nota.tipo_rateio = rateio.tipo_rateio
    
    if rateio.tipo_rateio == 'online':
        nota.percentual_online = 100
        nota.percentual_loja = 0
        nota.valor_online = nota.valor_total
        nota.valor_loja = 0
        
        # Zerar rateio dos itens (nÃ£o Ã© parcial)
        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0
            
    elif rateio.tipo_rateio == 'loja':
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total
        
        # Zerar rateio dos itens
        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0
            
    else:  # parcial
        # SerÃ¡ calculado quando configurar os itens
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total
    
    db.commit()
    db.refresh(nota)
    
    logger.info(f"ðŸ“Š Rateio da nota configurado: {rateio.tipo_rateio}")
    
    return {
        "message": "Tipo de rateio configurado com sucesso",
        "nota_id": nota.id,
        "tipo_rateio": nota.tipo_rateio,
        "percentual_online": nota.percentual_online,
        "percentual_loja": nota.percentual_loja,
        "valor_online": nota.valor_online,
        "valor_loja": nota.valor_loja
    }


# ============================================================================
# CONFIGURAR QUANTIDADE ONLINE DE UM ITEM (PARA RATEIO PARCIAL)
# ============================================================================

class RateioItemRequest(BaseModel):
    quantidade_online: float  # Quantidade que Ã© do online


@router.post("/{nota_id}/itens/{item_id}/rateio")
def configurar_rateio_item(
    nota_id: int,
    item_id: int,
    rateio: RateioItemRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configura quantidade do item que Ã© online (para rateio parcial)
    Sistema calcula automaticamente os % da nota
    """
    current_user, tenant_id = user_and_tenant
    
    # Buscar nota
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.tipo_rateio != 'parcial':
        raise HTTPException(
            status_code=400, 
            detail="Nota nÃ£o estÃ¡ configurada como rateio parcial. Configure primeiro o tipo de rateio."
        )
    
    # Buscar item
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id,
        NotaEntradaItem.tenant_id == tenant_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    dados_pack = calcular_quantidade_custo_efetivos(
        item.descricao,
        item.quantidade,
        item.valor_unitario,
        item.valor_total
    )
    quantidade_total_disponivel = dados_pack["quantidade_efetiva"]
    composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
    custo_unitario_efetivo = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])

    # Validar quantidade
    if rateio.quantidade_online < 0:
        raise HTTPException(status_code=400, detail="Quantidade online nÃ£o pode ser negativa")
    
    if rateio.quantidade_online > quantidade_total_disponivel:
        raise HTTPException(
            status_code=400, 
            detail=f"Quantidade online ({rateio.quantidade_online}) nÃ£o pode ser maior que a quantidade total ({quantidade_total_disponivel})"
        )
    
    # Atualizar item
    item.quantidade_online = rateio.quantidade_online
    item.valor_online = rateio.quantidade_online * custo_unitario_efetivo
    
    # Recalcular totais da nota
    valor_online_total = 0
    for it in nota.itens:
        if it.id == item_id:
            valor_online_total += item.valor_online
        else:
            valor_online_total += (it.valor_online or 0)
    
    nota.valor_online = valor_online_total
    nota.valor_loja = nota.valor_total - valor_online_total
    nota.percentual_online = (valor_online_total / nota.valor_total * 100) if nota.valor_total > 0 else 0
    nota.percentual_loja = 100 - nota.percentual_online
    
    db.commit()
    db.refresh(item)
    db.refresh(nota)
    
    logger.info(
        f"ðŸ“Š Rateio item configurado - {item.descricao}: "
        f"{item.quantidade_online}/{item.quantidade} online = R$ {item.valor_online:.2f}"
    )
    logger.info(
        f"ðŸ“Š Nota {nota.numero_nota}: {nota.percentual_online:.1f}% online (R$ {nota.valor_online:.2f}) | "
        f"{nota.percentual_loja:.1f}% loja (R$ {nota.valor_loja:.2f})"
    )
    
    return {
        "message": "Rateio do item configurado com sucesso",
        "item": {
            "id": item.id,
            "quantidade_total": quantidade_total_disponivel,
            "quantidade_online": item.quantidade_online,
            "valor_online": item.valor_online,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"]
        },
        "nota_totais": {
            "valor_total": nota.valor_total,
            "valor_online": nota.valor_online,
            "valor_loja": nota.valor_loja,
            "percentual_online": round(nota.percentual_online, 2),
            "percentual_loja": round(nota.percentual_loja, 2)
        }
    }


# ============================================================================
# PREVIEW DE ENTRADA NO ESTOQUE - REVISÃƒO DE PREÃ‡OS
# ============================================================================

@router.get("/{nota_id}/preview-processamento")
def preview_processamento(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna preview da entrada com comparaÃ§Ã£o de custos e preÃ§os atuais
    """
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(NotaEntrada.id == nota_id).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados"
        )
    
    composicoes_custo = calcular_composicao_custos_nota(nota)
    preview_itens = []
    
    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        # Dados do item da NF (sempre presente)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao,
            item.quantidade,
            item.valor_unitario,
            item.valor_total
        )

        item_nf = {
            "item_id": item.id,
            "codigo_produto_nf": item.codigo_produto,
            "descricao_nf": item.descricao,
            "quantidade_nf": item.quantidade,
            "valor_unitario_nf": item.valor_unitario,
            "quantidade_efetiva_nf": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo_nf": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario_nf": composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]),
            "custo_aquisicao_total_nf": composicao_custo.get("custo_aquisicao_total", item.valor_total),
            "composicao_custo": composicao_custo,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "ean_nf": item.ean,
            "ncm_nf": item.ncm,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            **conferencia_item,
        }

        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        item_nf["origem_vinculo_automatico"] = detalhe_vinculo["origem"]
        item_nf["referencia_vinculo"] = detalhe_vinculo["referencia"]
        
        # Dados do produto vinculado (se houver)
        produto_vinculado = None
        if item.produto_id:
            produto = item.produto
            custo_atual = produto.preco_custo or 0
            custo_novo = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])
            variacao_custo = ((custo_novo - custo_atual) / custo_atual * 100) if custo_atual > 0 else 0
            
            # Calcular margem de referencia (com custo atual do cadastro)
            preco_venda_atual = produto.preco_venda or 0
            if preco_venda_atual > 0 and custo_atual > 0:
                margem_atual = ((preco_venda_atual - custo_atual) / preco_venda_atual) * 100
            else:
                margem_atual = 0

            # Calcular margem projetada mantendo o preço de venda atual e aplicando o novo custo
            if preco_venda_atual > 0 and custo_novo > 0:
                margem_projetada = ((preco_venda_atual - custo_novo) / preco_venda_atual) * 100
            else:
                margem_projetada = 0
            
            produto_vinculado = {
                "produto_id": produto.id,
                "produto_codigo": produto.codigo,
                "produto_nome": produto.nome,
                "produto_ean": produto.codigo_barras,
                "custo_anterior": custo_atual,
                "custo_novo": custo_novo,
                "variacao_custo_percentual": round(variacao_custo, 2),
                "preco_venda_atual": preco_venda_atual,
                "margem_atual": round(margem_atual, 2),
                "margem_projetada_custo_novo": round(margem_projetada, 2),
                "estoque_atual": produto.estoque_atual or 0
            }
        
        preview_itens.append({
            **item_nf,
            "produto_vinculado": produto_vinculado
        })
    
    return {
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "valor_total": nota.valor_total,
        "conferencia": _resumir_conferencia_nota(nota),
        "itens": preview_itens
    }


# ============================================================================
# ATUALIZAR PREÃ‡OS DOS PRODUTOS
# ============================================================================

class AtualizarPrecoRequest(BaseModel):
    produto_id: int
    preco_venda: float

@router.post("/{nota_id}/atualizar-precos")
def atualizar_precos_produtos(
    nota_id: int,
    precos: List[AtualizarPrecoRequest],
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza preÃ§os de venda dos produtos antes de processar a nota
    Registra histÃ³rico de alteraÃ§Ãµes
    """
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    for preco_data in precos:
        produto = db.query(Produto).filter(
            Produto.id == preco_data.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        if produto:
            # Capturar valores anteriores
            preco_venda_anterior = produto.preco_venda
            preco_custo_anterior = produto.preco_custo
            margem_anterior = ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
            
            # Atualizar preÃ§o
            produto.preco_venda = preco_data.preco_venda
            
            # Calcular nova margem
            margem_nova = ((produto.preco_venda - produto.preco_custo) / produto.preco_venda * 100) if produto.preco_venda > 0 else 0
            
            # Registrar histÃ³rico se houve alteraÃ§Ã£o
            if preco_venda_anterior != produto.preco_venda:
                variacao_venda = ((produto.preco_venda - preco_venda_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
                
                historico = ProdutoHistoricoPreco(
                    produto_id=produto.id,
                    preco_custo_anterior=preco_custo_anterior,
                    preco_custo_novo=produto.preco_custo,
                    preco_venda_anterior=preco_venda_anterior,
                    preco_venda_novo=produto.preco_venda,
                    margem_anterior=margem_anterior,
                    margem_nova=margem_nova,
                    variacao_custo_percentual=0,  # Custo nÃ£o mudou neste caso
                    variacao_venda_percentual=variacao_venda,
                    motivo="nfe_revisao_precos",
                    nota_entrada_id=nota.id,
                    referencia=f"NF-e {nota.numero_nota} - RevisÃ£o de PreÃ§os",
                    observacoes=f"PreÃ§o ajustado de R$ {preco_venda_anterior:.2f} para R$ {produto.preco_venda:.2f} (margem: {margem_anterior:.1f}% â†’ {margem_nova:.1f}%)",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(historico)
                
                logger.info(
                    f"ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                    f"PreÃ§o R$ {preco_venda_anterior:.2f} â†’ R$ {produto.preco_venda:.2f} "
                    f"({variacao_venda:+.2f}%)"
                )
    
    db.commit()
    
    return {"message": "PreÃ§os atualizados com sucesso"}


# ============================================================================
# DAR ENTRADA NO ESTOQUE
# ============================================================================

class ProcessarConfig(BaseModel):
    # chave = str(item_id), valor = multiplicador (ex: {"42": 10})
    multiplicadores_override: dict = Field(default_factory=dict)
    # chave = str(item_id), valor = custo unitário manual a aplicar no sistema
    custos_override: dict = Field(default_factory=dict)


@router.post("/{nota_id}/processar")
def processar_entrada_estoque(
    nota_id: int,
    config: ProcessarConfig = ProcessarConfig(),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Processa entrada no estoque de todos os itens vinculados.
    Aceita:
    - multiplicadores_override: {"item_id": multiplicador} para packs manuais
    - custos_override: {"item_id": custo_unitario} para custo manual de sistema
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ“¦ Processando entrada no estoque - Nota {nota_id}")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Entrada no estoque jÃ¡ foi realizada"
        )
    
    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados. "
                   "Vincule todos os produtos antes de processar."
        )
    
    itens_processados = []
    composicoes_custo = calcular_composicao_custos_nota(nota)
    
    # Processar cada item
    for item in nota.itens:
        if not item.produto_id:
            continue

        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_base_conferida = conferencia_item["quantidade_conferida"]

        # Verificar override manual antes de usar auto-deteccao
        override_raw = _obter_override_mapa(config.multiplicadores_override, item.id)
        try:
            override_mult = int(override_raw) if override_raw is not None else None
        except (ValueError, TypeError):
            override_mult = None
        custo_unitario_manual = _normalizar_custo_unitario_override(
            _obter_override_mapa(config.custos_override, item.id),
            item.id,
        )

        if override_mult is not None and 1 <= override_mult <= 200:
            multiplicador_pack = override_mult
            quantidade_total_efetiva_nf = (item.quantidade or 0) * override_mult
            quantidade_entrada = quantidade_base_conferida * override_mult
            custo_total_aquisicao = composicao_custo.get("custo_aquisicao_total", item.valor_total)
            custo_unitario_entrada = (
                (custo_total_aquisicao / quantidade_total_efetiva_nf)
                if quantidade_total_efetiva_nf > 0 else item.valor_unitario
            )
            logger.info(f"📦 Pack MANUAL no item {item.id}: x{override_mult} (qtd NF {item.quantidade} → qtd entrada {quantidade_entrada})")
        else:
            dados_pack = calcular_quantidade_custo_efetivos(
                item.descricao,
                item.quantidade,
                item.valor_unitario,
                item.valor_total
            )
            quantidade_entrada = quantidade_base_conferida * dados_pack["multiplicador_pack"]
            custo_unitario_entrada = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])
            multiplicador_pack = dados_pack["multiplicador_pack"]

        if custo_unitario_manual is not None:
            custo_unitario_entrada = custo_unitario_manual
            logger.info(
                f"💰 Custo manual aplicado no item {item.id}: "
                f"R$ {custo_unitario_entrada:.4f} por unidade"
            )

        if quantidade_entrada <= 0:
            item.status = 'processado'
            itens_processados.append({
                "produto_id": item.produto.id,
                "produto_nome": item.produto.nome,
                "quantidade": 0,
                "lote": None,
                "estoque_atual": item.produto.estoque_atual or 0,
                "pack_multiplicador": multiplicador_pack,
                "status_conferencia": conferencia_item["status_conferencia"],
            })
            logger.info(
                f"  ⚠️ {item.produto.nome}: sem entrada em estoque "
                f"(conferida: {quantidade_base_conferida}, avariada: {conferencia_item['quantidade_avariada']}, "
                f"faltante: {conferencia_item['quantidade_faltante']})"
            )
            continue
        
        produto = item.produto
        
        # âœ… REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(f"  â™»ï¸  Produto reativado: {produto.codigo} - {produto.nome}")
        
        # âœ… ATUALIZAR dados fiscais do produto com informaÃ§Ãµes do XML
        produto.ncm = item.ncm
        produto.cfop = item.cfop
        produto.cest = item.cest if hasattr(item, 'cest') else None
        produto.origem = item.origem if hasattr(item, 'origem') else '0'
        produto.aliquota_icms = item.aliquota_icms if hasattr(item, 'aliquota_icms') else 0
        produto.aliquota_pis = item.aliquota_pis if hasattr(item, 'aliquota_pis') else 0
        produto.aliquota_cofins = item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else 0
        
        # âœ… ATUALIZAR EAN se fornecido e vÃ¡lido
        if item.ean and item.ean != 'SEM GTIN' and item.ean.strip():
            produto.codigo_barras = item.ean
            logger.info(f"  ðŸ”– EAN atualizado: {produto.codigo} â†’ {item.ean}")
        
        # âœ… VINCULAR ao fornecedor da nota
        if nota.fornecedor_id:
            vinculo_existente = db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto.id,
                ProdutoFornecedor.fornecedor_id == nota.fornecedor_id
            ).first()
            
            if not vinculo_existente:
                novo_vinculo = ProdutoFornecedor(
                    produto_id=produto.id,
                    fornecedor_id=nota.fornecedor_id,
                    preco_custo=custo_unitario_entrada,
                    e_principal=True,
                    ativo=True,
                    tenant_id=tenant_id
                )
                db.add(novo_vinculo)
                logger.info(f"  ðŸ”— Produto {produto.codigo} vinculado ao fornecedor {nota.fornecedor_id}")
            else:
                # Reativar vÃ­nculo se estiver inativo
                if not vinculo_existente.ativo:
                    vinculo_existente.ativo = True
                    logger.info(f"  â™»ï¸  VÃ­nculo de fornecedor reativado: {produto.codigo}")
                # Atualizar preÃ§o de custo no vÃ­nculo
                vinculo_existente.preco_custo = custo_unitario_entrada
        
        # Criar lote
        nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
        
        # Preparar data de validade (converter de date para datetime se necessÃ¡rio)
        data_validade = None
        if item.data_validade:
            from datetime import datetime as dt
            if isinstance(item.data_validade, dt):
                data_validade = item.data_validade
            else:
                # Ã‰ um objeto date, converter para datetime
                data_validade = dt.combine(item.data_validade, dt.min.time())
        
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=quantidade_entrada,
            quantidade_disponivel=quantidade_entrada,
            custo_unitario=float(custo_unitario_entrada),
            data_fabricacao=None,
            data_validade=data_validade,
            ordem_entrada=int(datetime.utcnow().timestamp()),
            tenant_id=tenant_id
        )
        db.add(lote)
        db.flush()
        
        # Atualizar estoque
        estoque_anterior = produto.estoque_atual or 0
        produto.estoque_atual = estoque_anterior + quantidade_entrada
        
        # Atualizar preÃ§o de custo e registrar histÃ³rico
        preco_custo_anterior = produto.preco_custo
        preco_venda_anterior = produto.preco_venda
        margem_anterior = ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
        
        alterou_custo = False
        if custo_unitario_entrada != preco_custo_anterior:
            produto.preco_custo = custo_unitario_entrada
            alterou_custo = True
        
        # Calcular margem nova
        margem_nova = ((produto.preco_venda - produto.preco_custo) / produto.preco_venda * 100) if produto.preco_venda > 0 else 0
        
        # Registrar histÃ³rico de preÃ§o se houve alteraÃ§Ã£o
        if alterou_custo:
            variacao_custo = ((produto.preco_custo - preco_custo_anterior) / preco_custo_anterior * 100) if preco_custo_anterior > 0 else 0
            
            historico = ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=produto.preco_venda,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=variacao_custo,
                variacao_venda_percentual=0,  # PreÃ§o de venda nÃ£o mudou
                motivo="nfe_entrada",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota}",
                observacoes=(
                    f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} "
                    f"para R$ {produto.preco_custo:.2f}"
                    f"{' (ajuste manual aplicado no processamento)' if custo_unitario_manual is not None else ''}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(historico)
            
            logger.info(
                f"  ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} â†’ R$ {produto.preco_custo:.2f} "
                f"({variacao_custo:+.2f}%)"
            )
        
        # Registrar movimentaÃ§Ã£o
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            lote_id=lote.id,
            tipo="entrada",
            motivo="compra",
            quantidade=quantidade_entrada,
            quantidade_anterior=estoque_anterior,
            quantidade_nova=produto.estoque_atual,
            custo_unitario=float(custo_unitario_entrada),
            valor_total=float(quantidade_entrada * custo_unitario_entrada),
            documento=nota.chave_acesso,
            referencia_tipo="nota_entrada",
            referencia_id=nota.id,
            observacao=(
                f"Entrada NF-e {nota.numero_nota} - {item.descricao}"
                if conferencia_item["status_conferencia"] == "ok"
                else (
                    f"Entrada NF-e {nota.numero_nota} - {item.descricao} | "
                    f"Conferida: {conferencia_item['quantidade_conferida']} | "
                    f"Avariada: {conferencia_item['quantidade_avariada']} | "
                    f"Faltante: {conferencia_item['quantidade_faltante']}"
                )
            ) + (
                f" | Custo sistema manual: R$ {custo_unitario_entrada:.4f}"
                if custo_unitario_manual is not None else ""
            ),
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        
        # Atualizar status do item
        item.status = 'processado'
        
        itens_processados.append({
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "quantidade": quantidade_entrada,
            "lote": nome_lote,
            "estoque_atual": produto.estoque_atual,
            "pack_multiplicador": multiplicador_pack,
            "status_conferencia": conferencia_item["status_conferencia"],
            "custo_unitario_aplicado": float(custo_unitario_entrada),
            "custo_manual_aplicado": custo_unitario_manual is not None,
        })
        
        logger.info(
            f"  âœ… {produto.nome}: +{quantidade_entrada} unidades "
            f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
        )

        if multiplicador_pack > 1:
            logger.info(
                f"  ðŸ“¦ Pack detectado automaticamente no item {item.numero_item}: "
                f"x{multiplicador_pack} (qtd NF {item.quantidade} â†’ qtd entrada {quantidade_entrada})"
            )
    
    resumo_conferencia = _resumir_conferencia_nota(nota)
    if not nota.conferencia_realizada_em:
        nota.conferencia_realizada_em = datetime.utcnow()
        nota.conferencia_user_id = current_user.id
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo_conferencia["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    resumo_conferencia = _resumir_conferencia_nota(nota)

    # Atualizar nota
    nota.status = 'processada'
    nota.entrada_estoque_realizada = True
    nota.processada_em = datetime.utcnow()
    
    # CRIAR CONTAS A PAGAR apÃ³s processar estoque
    contas_ids = []
    try:
        # Buscar dados do XML salvos na nota para pegar duplicatas
        import xml.etree.ElementTree as ET
        dados_xml = parse_nfe_xml(nota.xml_content)
        
        contas_ids = criar_contas_pagar_da_nota(nota, dados_xml, db, current_user.id, tenant_id)
        logger.info(f"ðŸ’° {len(contas_ids)} contas a pagar criadas")
    except Exception as e:
        logger.error(f"âš ï¸ Erro ao criar contas a pagar: {str(e)}")
        # NÃ£o abortar o processo, apenas avisar
    
    db.commit()
    
    # SINCRONIZAR ESTOQUE COM BLING para todos os itens processados
    try:
        from app.bling_estoque_sync import sincronizar_bling_background
        for item_proc in itens_processados:
            sincronizar_bling_background(item_proc['produto_id'], item_proc['estoque_atual'], "entrada_nfe")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada_nfe): {e_sync}")
    
    # VERIFICAR E NOTIFICAR PENDÊNCIAS DE ESTOQUE
    from app.services.pendencia_estoque_service import verificar_e_notificar_pendencias
    try:
        for item_proc in itens_processados:
            produto_id = item_proc['produto_id']
            quantidade = item_proc['quantidade']
            notificacoes = verificar_e_notificar_pendencias(
                db=db,
                tenant_id=tenant_id,
                produto_id=produto_id,
                quantidade_entrada=quantidade
            )
            if notificacoes > 0:
                logger.info(f"WhatsApp: {notificacoes} clientes notificados sobre {item_proc['produto']}")
    except Exception as e:
        logger.error(f"Erro ao notificar pendencias: {str(e)}")
        # Não abortar, apenas logar o erro
    
    logger.info(f"âœ… Entrada processada: {len(itens_processados)} produtos")
    
    return {
        "message": "Entrada no estoque realizada com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "conferencia": resumo_conferencia,
        "detalhes": itens_processados
    }


# ============================================================================
# REVERTER/ESTORNAR ENTRADA NO ESTOQUE
# ============================================================================

@router.post("/{nota_id}/reverter")
def reverter_entrada_estoque(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Reverte a entrada no estoque de uma nota jÃ¡ processada
    Remove estoque, exclui lotes, movimentaÃ§Ãµes e contas a pagar
    Reverte preÃ§os de custo dos produtos
    """
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ”„ Revertendo entrada no estoque - Nota {nota_id}")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if not nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Esta nota ainda nÃ£o foi processada"
        )
    
    # REVERTER CONTAS A PAGAR vinculadas a esta nota
    logger.info("ðŸ’° Excluindo contas a pagar vinculadas...")
    contas_pagar = db.query(ContaPagar).filter(
        ContaPagar.nota_entrada_id == nota.id,
        ContaPagar.tenant_id == tenant_id
    ).all()
    
    contas_excluidas = 0
    for conta in contas_pagar:
        if conta.status != 'pago':
            db.delete(conta)
            contas_excluidas += 1
            logger.info(f"   âœ… Conta excluÃ­da: {conta.descricao} - R$ {float(conta.valor_final):.2f}")
        else:
            logger.warning(f"   âš ï¸ Conta JÃ PAGA nÃ£o pode ser excluÃ­da: {conta.descricao}")
    
    if contas_excluidas > 0:
        logger.info(f"âœ… Total de contas excluÃ­das: {contas_excluidas}")
    
    itens_revertidos = []
    
    try:
        # Reverter cada item
        for item in nota.itens:
            if not item.produto_id:
                continue
            
            try:
                produto = item.produto
                
                # Buscar lote criado para esta entrada
                nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
                lote = db.query(ProdutoLote).filter(
                    ProdutoLote.produto_id == produto.id,
                    ProdutoLote.nome_lote == nome_lote,
                    ProdutoLote.tenant_id == tenant_id
                ).first()
                
                if lote:
                    quantidade_lancada = float(lote.quantidade_inicial or 0)

                    # REVERTER PREÇO DE CUSTO se foi alterado
                    try:
                        historico_preco = db.query(ProdutoHistoricoPreco).filter(
                            ProdutoHistoricoPreco.produto_id == produto.id,
                            ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                            ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                            ProdutoHistoricoPreco.tenant_id == tenant_id
                        ).first()
                        
                        if historico_preco:
                            # Reverter preços anteriores (com fallback para 0 se None)
                            preco_custo_revertido = float(historico_preco.preco_custo_anterior or 0)
                            preco_venda_revertido = float(historico_preco.preco_venda_anterior or 0)
                            
                            try:
                                logger.info(f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo or 0):.2f} → R$ {preco_custo_revertido:.2f}")
                            except:
                                logger.info(f"  💰 Revertendo preços do produto {produto.id}")
                            
                            produto.preco_custo = preco_custo_revertido
                            produto.preco_venda = preco_venda_revertido
                            
                            # Excluir histórico
                            db.delete(historico_preco)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao reverter preços: {str(e)}")
                    
                    # Remover quantidade do estoque
                    estoque_anterior = produto.estoque_atual or 0
                    produto.estoque_atual = max(0, estoque_anterior - quantidade_lancada)
                    
                    # Registrar movimentação de estorno (sem referência ao lote que será deletado)
                    try:
                        movimentacao_estorno = EstoqueMovimentacao(
                            produto_id=produto.id,
                            lote_id=None,  # Não referenciar o lote que será deletado
                            tipo="saida",
                            motivo="ajuste",
                            quantidade=quantidade_lancada,
                            quantidade_anterior=float(estoque_anterior),
                            quantidade_nova=float(produto.estoque_atual or 0),
                            custo_unitario=float(lote.custo_unitario or item.valor_unitario or 0),
                            valor_total=float(quantidade_lancada * float(lote.custo_unitario or item.valor_unitario or 0)),
                            documento=nota.chave_acesso or "",
                            referencia_tipo="estorno_nota_entrada",
                            referencia_id=nota.id,
                            observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao or ''}",
                            user_id=current_user.id,
                            tenant_id=tenant_id
                        )
                        db.add(movimentacao_estorno)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao criar movimentação: {str(e)}")
                    
                    # Excluir movimentações de estoque vinculadas ao lote (antes de deletar o lote)
                    movimentacoes_lote = db.query(EstoqueMovimentacao).filter(
                        EstoqueMovimentacao.lote_id == lote.id,
                        EstoqueMovimentacao.tenant_id == tenant_id
                    ).all()
                    
                    for mov in movimentacoes_lote:
                        db.delete(mov)
                    
                    if movimentacoes_lote:
                        logger.info(f"  🗑️  {len(movimentacoes_lote)} movimentações do lote excluídas")
                    
                    # Excluir lote
                    db.delete(lote)
                    
                    # Adicionar à lista de revertidos
                    itens_revertidos.append({
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "quantidade_removida": quantidade_lancada,
                        "estoque_atual": float(produto.estoque_atual or 0)
                    })
                    
                    logger.info(
                        f"  ↩️  {produto.nome}: -{quantidade_lancada} unidades "
                        f"(estoque: {estoque_anterior} → {produto.estoque_atual})"
                    )
                
                # Restaurar status do item
                item.status = 'vinculado'
            
            except Exception as e:
                logger.error(f"  ❌ Erro ao reverter item {item.id}: {str(e)}")
                # Continuar com próximo item ao invés de parar tudo
        
        # Atualizar status da nota
        nota.status = 'pendente'
        nota.entrada_estoque_realizada = False
        nota.processada_em = None
        
        db.commit()
        
        # SINCRONIZAR ESTOQUE COM BLING para todos os itens revertidos
        try:
            from app.bling_estoque_sync import sincronizar_bling_background
            for item_rev in itens_revertidos:
                sincronizar_bling_background(item_rev['produto_id'], item_rev['estoque_atual'], "estorno_nfe")
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (estorno_nfe): {e_sync}")
        
        logger.info(f"âœ… Entrada revertida: {len(itens_revertidos)} produtos")
        
        return {
            "message": "Entrada no estoque revertida com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "itens_revertidos": len(itens_revertidos),
            "detalhes": itens_revertidos
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao reverter entrada: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao reverter entrada: {str(e)}")


# ============================================================================
# SUGERIR SKU PARA PRODUTO NOVO
# ============================================================================

@router.get("/{nota_id}/itens/{item_id}/sugerir-sku")
def sugerir_sku(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Sugere SKU para produto novo usando o SKU do fornecedor como primeira opÃ§Ã£o.
    """
    current_user, tenant_id = user_and_tenant
    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)
    return _montar_sugestao_sku_produto(
        nota=nota,
        item=item,
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )


# ============================================================================
# CRIAR PRODUTO A PARTIR DO ITEM DA NOTA
# ============================================================================

class CriarProdutoRequest(BaseModel):
    sku: str
    nome: str
    descricao: Optional[str] = None
    preco_custo: float
    preco_venda: float
    margem_lucro: Optional[float] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    estoque_minimo: Optional[int] = 10
    estoque_maximo: Optional[int] = 100


@router.post("/{nota_id}/itens/{item_id}/criar-produto")
def criar_produto_from_item(
    nota_id: int,
    item_id: int,
    dados: CriarProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria um novo produto a partir do item da nota
    ATUALIZADO: Corrigido para usar descricao_curta e descricao_completa
    """
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ”¨ Criando produto: {dados.sku} - {dados.nome}")
    
    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)

    sku_solicitado = (dados.sku or "").strip()
    sku_final = sku_solicitado
    sku_ajustado_automaticamente = False

    if not sku_final:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(status_code=409, detail="NÃ£o foi possÃ­vel gerar um SKU para o novo produto")
        sku_final = sugestao_recomendada["sku"]
        sku_ajustado_automaticamente = True

    produto_existente = _buscar_produto_por_codigo_global(db, sku_final)
    if produto_existente:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            sku_base_customizado=sku_final,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(status_code=409, detail="O SKU informado jÃ¡ existe e nÃ£o foi possÃ­vel gerar alternativa")
        sku_final = sugestao_recomendada["sku"]
        sku_ajustado_automaticamente = True
        logger.info(
            f"ðŸ”„ SKU ajustado automaticamente para criar novo produto: "
            f"{sku_solicitado or '<vazio>'} -> {sku_final}"
        )
    
    # Criar produto novo e vincular
    try:
        # Preparar descriÃ§Ãµes
        descricao_texto = dados.descricao or item.descricao or ''
        descricao_curta = descricao_texto[:100] if descricao_texto else ''
        descricao_completa = descricao_texto
        
        # Aplicar inteligência fiscal
        dados_produto = {
            "nome": dados.nome,
            "descricao": descricao_texto,
            "ncm": item.ncm if hasattr(item, 'ncm') else None,
            "cfop": item.cfop if hasattr(item, 'cfop') else None,
            "cest": item.cest if hasattr(item, 'cest') else None,
            "origem": item.origem if hasattr(item, 'origem') else None,
            "aliquota_icms": item.aliquota_icms if hasattr(item, 'aliquota_icms') else None,
            "aliquota_pis": item.aliquota_pis if hasattr(item, 'aliquota_pis') else None,
            "aliquota_cofins": item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else None
        }
        
        # Aplicar padrões fiscais inteligentes
        dados_fiscais = aplicar_inteligencia_fiscal(dados_produto, {
            "ncm": item.ncm if hasattr(item, 'ncm') else None,
            "cfop": item.cfop if hasattr(item, 'cfop') else None,
            "cest": item.cest if hasattr(item, 'cest') else None,
            "origem": item.origem if hasattr(item, 'origem') else None,
            "aliquota_icms": item.aliquota_icms if hasattr(item, 'aliquota_icms') else None,
            "aliquota_pis": item.aliquota_pis if hasattr(item, 'aliquota_pis') else None,
            "aliquota_cofins": item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else None
        })
        
        if dados_fiscais.get("padrao_fiscal_motivo"):
            logger.info(f"🎯 {dados_fiscais['padrao_fiscal_motivo']} (confiança: {dados_fiscais.get('padrao_fiscal_confianca', 0):.0%})")
        
        novo_produto = Produto(
            codigo=sku_final,
            nome=dados.nome,
            descricao_curta=descricao_curta,
            descricao_completa=descricao_completa,
            preco_custo=dados.preco_custo,
            preco_venda=dados.preco_venda,
            categoria_id=dados.categoria_id,
            marca_id=dados.marca_id,
            
            # DADOS FISCAIS - Usar dados_fiscais com inteligência aplicada
            ncm=dados_fiscais.get("ncm"),
            cfop=dados_fiscais.get("cfop"),
            cest=dados_fiscais.get("cest"),
            origem=dados_fiscais.get("origem", "0"),
            aliquota_icms=dados_fiscais.get("aliquota_icms", 0),
            aliquota_pis=dados_fiscais.get("aliquota_pis", 0),
            aliquota_cofins=dados_fiscais.get("aliquota_cofins", 0),
            codigo_barras=item.ean if item.ean and item.ean != 'SEM GTIN' else None,
            
            # ESTOQUE
            estoque_minimo=dados.estoque_minimo,
            estoque_maximo=dados.estoque_maximo,
            estoque_atual=0,
            unidade=item.unidade,
            controle_lote=True,  # Sempre ativar controle de lote para produtos do XML
            ativo=True,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        
        db.add(novo_produto)
        db.flush()
        
        # Vincular automaticamente ao item da nota
        item.produto_id = novo_produto.id
        item.vinculado = True
        item.confianca_vinculo = 1.0
        item.status = 'vinculado'
        
        # Vincular produto ao fornecedor da nota automaticamente
        if nota.fornecedor_id:
            novo_vinculo = ProdutoFornecedor(
                produto_id=novo_produto.id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=dados.preco_custo,
                e_principal=True,  # Primeiro fornecedor Ã© principal
                ativo=True,
                tenant_id=tenant_id
            )
            db.add(novo_vinculo)
            logger.info(f"âœ… Novo produto {novo_produto.id} vinculado ao fornecedor {nota.fornecedor_id}")
        
        # IMPORTANTE: Flush antes de contar para garantir que o produto_id esteja no banco
        db.flush()
        
        # Atualizar contadores da nota
        nota.produtos_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.isnot(None)
        ).count()
        
        nota.produtos_nao_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.is_(None)
        ).count()
        
        db.commit()
        db.refresh(novo_produto)
        db.refresh(item)
        db.refresh(nota)
        
    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao criar produto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")
    
    logger.info(f"âœ… Produto criado a partir da nota: {novo_produto.codigo} - {novo_produto.nome}")
    
    return {
        "message": (
            f"Produto criado e vinculado com sucesso com SKU ajustado para {novo_produto.codigo}"
            if sku_ajustado_automaticamente
            else "Produto criado e vinculado com sucesso"
        ),
        "produto": {
            "id": novo_produto.id,
            "codigo": novo_produto.codigo,
            "nome": novo_produto.nome,
            "descricao_curta": novo_produto.descricao_curta,
            "descricao_completa": novo_produto.descricao_completa,
            "preco_custo": novo_produto.preco_custo,
            "preco_venda": novo_produto.preco_venda
        },
        "item_vinculado": True,
        "sku_ajustado_automaticamente": sku_ajustado_automaticamente
    }


# ============================================================================
# EXCLUIR NOTA
# ============================================================================

@router.delete("/{nota_id}")
def excluir_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exclui uma nota de entrada e seus itens (cascade)"""
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    # Verificar se jÃ¡ teve entrada no estoque
    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400, 
            detail="NÃ£o Ã© possÃ­vel excluir nota que jÃ¡ teve entrada no estoque"
        )
    
    numero_nota = nota.numero_nota
    total_itens = len(nota.itens)
    
    # Excluir contas a pagar vinculadas (se existirem)
    contas_pagar = db.query(ContaPagar).filter(
        ContaPagar.nota_entrada_id == nota.id
    ).all()
    
    contas_excluidas = 0
    pagamentos_excluidos = 0
    for conta in contas_pagar:
        # Excluir pagamentos da conta antes de excluir a conta
        from app.financeiro_models import Pagamento
        pagamentos = db.query(Pagamento).filter(Pagamento.conta_pagar_id == conta.id).all()
        for pagamento in pagamentos:
            db.delete(pagamento)
            pagamentos_excluidos += 1
        
        db.delete(conta)
        contas_excluidas += 1
    
    if contas_excluidas > 0:
        logger.info(f"ðŸ—‘ï¸ {contas_excluidas} contas a pagar e {pagamentos_excluidos} pagamentos excluÃ­dos junto com a nota")
    
    # Excluir nota (cascade deleta os itens automaticamente)
    db.delete(nota)
    db.commit()
    
    logger.info(f"ðŸ—‘ï¸ Nota excluÃ­da: {numero_nota} ({total_itens} itens)")
    
    return {
        "message": "Nota excluída com sucesso",
        "numero_nota": numero_nota,
        "itens_excluidos": total_itens,
        "contas_pagar_excluidas": contas_excluidas
    }


# ============================================================================
# IMPORTAÇÃO AUTOMÁTICA DE DOCS DA SEFAZ (chamado pelo loop do main.py)
# ============================================================================

def importar_docs_sefaz(docs: list, tenant_id_str: str, db) -> dict:
    """
    Importa documentos retornados pela SEFAZ para a tabela notas_entrada.

    Chamada pelo loop de sincronização automática no main.py.
    Cada `doc` é um dict com chaves: nsu, schema, xml.

    Só importa documentos com schema procNFe (XML completo).
    Documentos resNFe (resumo) são ignorados pois não têm itens.
    Documentos onde o CNPJ emitente == CNPJ do tenant (NF de saída) são descartados.

    Retorna: {"importadas": N, "duplicadas": N, "erros": N, "saidas_descartadas": N}
    """
    from uuid import UUID
    from app.models import User

    importadas = 0
    duplicadas = 0
    erros = 0
    saidas_descartadas = 0

    # Buscar CNPJ do tenant na config SEFAZ para identificar NF de saída
    tenant_cnpj = ""
    try:
        from app.services.sefaz_tenant_config_service import SefazTenantConfigService
        cfg_tenant = SefazTenantConfigService.load_config(UUID(tenant_id_str))
        tenant_cnpj = "".join(ch for ch in str(cfg_tenant.get("cnpj", "")) if ch.isdigit())
    except Exception as exc_cfg:
        logger.warning(f"[SEFAZ] Não foi possível carregar CNPJ do tenant {tenant_id_str}: {exc_cfg}")

    # Buscar um usuário sistema do tenant para associar as notas
    try:
        tenant_uuid = UUID(tenant_id_str)
    except ValueError:
        logger.warning(f"[SEFAZ] tenant_id inválido: {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs), "saidas_descartadas": 0}

    user_sistema = db.query(User).filter(
        User.tenant_id == tenant_id_str
    ).order_by(User.id).first()

    if not user_sistema:
        logger.warning(f"[SEFAZ] Nenhum usuário encontrado para tenant {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs)}

    for doc in docs:
        schema = doc.get("schema", "")
        xml_str = doc.get("xml", "")
        nsu = doc.get("nsu", "")

        # Só processa XML completo de NF-e (procNFe) — resNFe não tem itens nem XML da nota
        if "procNFe" not in schema and "nfeProc" not in xml_str[:200]:
            logger.debug(f"[SEFAZ] NSU {nsu} ignorado (schema: {schema})")
            continue

        try:
            dados_nfe = parse_nfe_xml(xml_str)
        except Exception as exc:
            logger.warning(f"[SEFAZ] NSU {nsu}: erro no parse do XML — {exc}")
            erros += 1
            continue

        # Descartar NF de saída (emitida pela própria empresa)
        # emit.CNPJ == tenant CNPJ significa que a empresa emitiu essa NF (saída/venda)
        if tenant_cnpj:
            cnpj_emitente = "".join(ch for ch in str(dados_nfe.get("fornecedor_cnpj", "")) if ch.isdigit())
            if cnpj_emitente and cnpj_emitente == tenant_cnpj:
                logger.debug(f"[SEFAZ] NSU {nsu}: NF de saída descartada (emitente == tenant)")
                saidas_descartadas += 1
                continue

        chave = dados_nfe.get("chave_acesso", "")
        if not chave:
            logger.warning(f"[SEFAZ] NSU {nsu}: chave de acesso não encontrada no XML")
            erros += 1
            continue

        # Verificar se já existe
        existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == chave
        ).first()
        if existente:
            duplicadas += 1
            continue

        try:
            # Buscar ou criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                Cliente.ativo == True
            ).first()

            if not fornecedor:
                fornecedor, _ = criar_fornecedor_automatico(dados_nfe, db, user_sistema, tenant_id_str)

            # Criar nota com status pendente
            nota = NotaEntrada(
                numero_nota=dados_nfe["numero_nota"],
                serie=dados_nfe["serie"],
                chave_acesso=chave,
                fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
                fornecedor_nome=dados_nfe["fornecedor_nome"],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe["data_emissao"],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe["valor_produtos"],
                valor_frete=dados_nfe["valor_frete"],
                valor_desconto=dados_nfe["valor_desconto"],
                valor_total=dados_nfe["valor_total"],
                xml_content=xml_str,
                status="pendente",
                user_id=user_sistema.id,
                tenant_id=tenant_id_str,
            )
            db.add(nota)
            db.flush()

            # Criar itens com matching automático
            vinculados = 0
            nao_vinculados = 0
            for item_data in dados_nfe["itens"]:
                produto, confianca, _, _, _ = encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id_str,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get("ean"),
                )
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data["numero_item"],
                    codigo_produto=item_data["codigo_produto"],
                    descricao=item_data["descricao"],
                    ncm=item_data.get("ncm"),
                    cest=item_data.get("cest"),
                    cfop=item_data.get("cfop"),
                    origem=item_data.get("origem", "0"),
                    aliquota_icms=item_data.get("aliquota_icms", 0),
                    aliquota_pis=item_data.get("aliquota_pis", 0),
                    aliquota_cofins=item_data.get("aliquota_cofins", 0),
                    unidade=item_data.get("unidade", "UN"),
                    quantidade=item_data["quantidade"],
                    valor_unitario=item_data["valor_unitario"],
                    valor_total=item_data["valor_total"],
                    ean=item_data.get("ean"),
                    lote=item_data.get("lote"),
                    data_validade=item_data.get("data_validade"),
                    produto_id=produto.id if produto else None,
                    vinculado=bool(produto),
                    confianca_vinculo=confianca if produto else 0,
                    status="vinculado" if produto else "nao_vinculado",
                    tenant_id=tenant_id_str,
                )
                db.add(item)
                if produto:
                    vinculados += 1
                else:
                    nao_vinculados += 1

            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            db.commit()

            importadas += 1
            logger.info(
                f"[SEFAZ] ✅ NF-e {dados_nfe['numero_nota']} importada "
                f"(chave: {chave[:10]}..., {vinculados} vinculados, {nao_vinculados} não vinculados)"
            )

        except Exception as exc:
            db.rollback()
            logger.warning(f"[SEFAZ] NSU {nsu}: erro ao salvar nota {chave[:10]}... — {exc}")
            erros += 1

    return {"importadas": importadas, "duplicadas": duplicadas, "erros": erros, "saidas_descartadas": saidas_descartadas}
