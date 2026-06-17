"""
Padrões Fiscais Inteligentes
Sistema de identificação e sugestão automática de dados fiscais
baseado em NCM, categoria e palavras-chave
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# PADRÕES FISCAIS POR NCM E CATEGORIA
# ============================================================================

PADROES_FISCAIS = {
    # RAÇÕES PARA ANIMAIS
    "2309": {  # NCM 2309 - Preparações para alimentação de animais
        "descricao": "Rações e alimentos para animais",
        "origem": "0",  # 0 - Nacional
        "cfop": "5102",  # Venda de mercadoria adquirida de terceiros
        "cest": "1701600",  # CEST para ração animal
        "aliquota_icms": 12.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": [
            "ração",
            "racao",
            "alimento animal",
            "pet food",
            "dog",
            "cat",
            "gato",
            "cachorro",
        ],
    },
    # ACESSÓRIOS PARA ANIMAIS
    "4201": {  # NCM 4201 - Artigos de selaria para animais
        "descricao": "Acessórios e artigos para animais",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["coleira", "guia", "peitoral", "focinheira", "enforcador"],
    },
    # BRINQUEDOS PARA ANIMAIS
    "9503": {  # NCM 9503 - Brinquedos
        "descricao": "Brinquedos para animais",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["brinquedo", "mordedor", "bolinha", "ossinho", "pelucia"],
    },
    # HIGIENE E LIMPEZA PARA ANIMAIS
    "3307": {  # NCM 3307 - Preparações para barbear, desodorantes, etc
        "descricao": "Produtos de higiene para animais",
        "origem": "0",
        "cfop": "5102",
        "cest": "2001100",
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": [
            "shampoo",
            "condicionador",
            "sabonete",
            "perfume",
            "colônia",
            "desodorante",
        ],
    },
    "3401": {  # NCM 3401 - Sabões, produtos de limpeza
        "descricao": "Produtos de limpeza",
        "origem": "0",
        "cfop": "5102",
        "cest": "2001100",
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": [
            "limpeza",
            "higienizante",
            "desinfetante",
            "neutralizador",
            "removedor",
        ],
    },
    # MEDICAMENTOS VETERINÁRIOS
    "3003": {  # NCM 3003 - Medicamentos
        "descricao": "Medicamentos veterinários",
        "origem": "0",
        "cfop": "5405",  # Venda de mercadoria adquirida de terceiros (substituição tributária)
        "cest": "2800200",
        "aliquota_icms": 0.0,  # Substituição tributária
        "aliquota_pis": 0.0,
        "aliquota_cofins": 0.0,
        "keywords": [
            "medicamento",
            "remedio",
            "antibiotico",
            "vermifugo",
            "antipulgas",
            "carrapaticida",
        ],
    },
    "3004": {  # NCM 3004 - Medicamentos
        "descricao": "Medicamentos veterinários",
        "origem": "0",
        "cfop": "5405",
        "cest": "2800200",
        "aliquota_icms": 0.0,
        "aliquota_pis": 0.0,
        "aliquota_cofins": 0.0,
        "keywords": ["vitamina", "suplemento", "fortificante"],
    },
    # ROUPAS PARA ANIMAIS
    "6211": {  # NCM 6211 - Vestuário
        "descricao": "Roupas e vestuário para animais",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["roupa", "camiseta", "casaco", "jaqueta", "fantasia"],
    },
    # CAMAS E CASINHAS
    "9404": {  # NCM 9404 - Artigos de cama
        "descricao": "Camas, almofadas e casinhas",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["cama", "almofada", "colchonete", "tapete", "casinha", "toca"],
    },
    # UTENSÍLIOS (COMEDOUROS, BEBEDOUROS)
    "3924": {  # NCM 3924 - Artefatos de plástico
        "descricao": "Utensílios plásticos",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["comedouro", "bebedouro", "pote", "tigela", "vasilha"],
    },
    "7323": {  # NCM 7323 - Artefatos de ferro ou aço
        "descricao": "Utensílios metálicos",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["comedouro", "bebedouro", "pote", "tigela", "vasilha", "inox"],
    },
    # AREIA E GRANULADO HIGIÊNICO
    "2508": {  # NCM 2508 - Argilas
        "descricao": "Areia e granulados higiênicos",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 12.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": [
            "areia",
            "granulado",
            "absorvente",
            "sanitario",
            "higienico",
            "sanitária",
        ],
    },
    # PETISCOS E SNACKS
    "1905": {  # NCM 1905 - Produtos de padaria
        "descricao": "Petiscos e snacks",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 12.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["petisco", "snack", "biscoito", "osso", "bastao", "palito"],
    },
    # AQUÁRIOS E ACESSÓRIOS
    "7010": {  # NCM 7010 - Garrafões, garrafas, frascos, boiões (vidro)
        "descricao": "Aquários e acessórios",
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "keywords": ["aquario", "aquário"],
    },
}


def identificar_padrao_fiscal(
    ncm: Optional[str] = None,
    descricao: Optional[str] = None,
    categoria: Optional[str] = None,
) -> Dict:
    """
    Identifica o padrão fiscal baseado em NCM, descrição e categoria

    Args:
        ncm: Código NCM do produto (4 ou 8 dígitos)
        descricao: Descrição do produto
        categoria: Categoria do produto

    Returns:
        Dict com dados fiscais sugeridos
    """
    resultado = {
        "origem": "0",
        "cfop": "5102",
        "cest": None,
        "aliquota_icms": 18.0,
        "aliquota_pis": 1.65,
        "aliquota_cofins": 7.6,
        "confianca": 0.0,
        "motivo": "Padrão genérico",
    }

    # 1. Tentar identificar por NCM (prioridade máxima)
    if ncm:
        ncm_4digitos = ncm[:4] if len(ncm) >= 4 else ncm

        if ncm_4digitos in PADROES_FISCAIS:
            padrao = PADROES_FISCAIS[ncm_4digitos]
            resultado.update(
                {
                    "origem": padrao["origem"],
                    "cfop": padrao["cfop"],
                    "cest": padrao["cest"],
                    "aliquota_icms": padrao["aliquota_icms"],
                    "aliquota_pis": padrao["aliquota_pis"],
                    "aliquota_cofins": padrao["aliquota_cofins"],
                    "confianca": 1.0,
                    "motivo": f"NCM {ncm_4digitos} - {padrao['descricao']}",
                }
            )
            logger.info(f"✅ Padrão fiscal identificado por NCM: {ncm_4digitos}")
            return resultado

    # 2. Tentar identificar por palavras-chave na descrição
    if descricao:
        descricao_lower = descricao.lower()

        for ncm_key, padrao in PADROES_FISCAIS.items():
            keywords = padrao.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in descricao_lower:
                    resultado.update(
                        {
                            "ncm_sugerido": ncm_key + "0000",  # Completar com zeros
                            "origem": padrao["origem"],
                            "cfop": padrao["cfop"],
                            "cest": padrao["cest"],
                            "aliquota_icms": padrao["aliquota_icms"],
                            "aliquota_pis": padrao["aliquota_pis"],
                            "aliquota_cofins": padrao["aliquota_cofins"],
                            "confianca": 0.8,
                            "motivo": f"Palavra-chave '{keyword}' - {padrao['descricao']}",
                        }
                    )
                    logger.info(
                        f"✅ Padrão fiscal identificado por palavra-chave: {keyword}"
                    )
                    return resultado

    # 3. Padrão genérico (baixa confiança)
    logger.info("⚠️ Usando padrão fiscal genérico")
    return resultado


def sugerir_ncm(descricao: str, categoria: Optional[str] = None) -> Optional[str]:
    """
    Sugere NCM baseado na descrição do produto

    Args:
        descricao: Descrição do produto
        categoria: Categoria do produto (opcional)

    Returns:
        Código NCM sugerido (8 dígitos) ou None
    """
    if not descricao:
        return None

    descricao_lower = descricao.lower()

    for ncm_key, padrao in PADROES_FISCAIS.items():
        keywords = padrao.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in descricao_lower:
                ncm_completo = ncm_key + "0000"  # Completar com zeros para 8 dígitos
                logger.info(
                    f"💡 NCM sugerido: {ncm_completo} (palavra-chave: {keyword})"
                )
                return ncm_completo

    return None


def aplicar_inteligencia_fiscal(
    produto_data: Dict, item_nf: Optional[Dict] = None
) -> Dict:
    """
    Aplica inteligência fiscal em dados de produto
    Preenche campos fiscais vazios com sugestões inteligentes

    Args:
        produto_data: Dicionário com dados do produto
        item_nf: Dados do item da NF (opcional, tem prioridade)

    Returns:
        Dict com dados fiscais preenchidos
    """
    # Se veio da NF, usar dados da NF (prioridade máxima)
    if item_nf:
        if item_nf.get("ncm"):
            produto_data["ncm"] = item_nf["ncm"]
        if item_nf.get("cfop"):
            produto_data["cfop"] = item_nf["cfop"]
        if item_nf.get("cest"):
            produto_data["cest"] = item_nf["cest"]
        if item_nf.get("origem"):
            produto_data["origem"] = item_nf["origem"]
        if item_nf.get("aliquota_icms") is not None:
            produto_data["aliquota_icms"] = item_nf["aliquota_icms"]
        if item_nf.get("aliquota_pis") is not None:
            produto_data["aliquota_pis"] = item_nf["aliquota_pis"]
        if item_nf.get("aliquota_cofins") is not None:
            produto_data["aliquota_cofins"] = item_nf["aliquota_cofins"]

    # Identificar padrão fiscal
    padrao = identificar_padrao_fiscal(
        ncm=produto_data.get("ncm"),
        descricao=produto_data.get("nome") or produto_data.get("descricao"),
        categoria=produto_data.get("categoria"),
    )

    # Preencher campos vazios com sugestões
    if not produto_data.get("ncm") and padrao.get("ncm_sugerido"):
        produto_data["ncm"] = padrao["ncm_sugerido"]
        produto_data["ncm_sugerido"] = True

    if not produto_data.get("origem"):
        produto_data["origem"] = padrao["origem"]

    if not produto_data.get("cfop"):
        produto_data["cfop"] = padrao["cfop"]

    if not produto_data.get("cest") and padrao.get("cest"):
        produto_data["cest"] = padrao["cest"]

    if not produto_data.get("aliquota_icms"):
        produto_data["aliquota_icms"] = padrao["aliquota_icms"]

    if not produto_data.get("aliquota_pis"):
        produto_data["aliquota_pis"] = padrao["aliquota_pis"]

    if not produto_data.get("aliquota_cofins"):
        produto_data["aliquota_cofins"] = padrao["aliquota_cofins"]

    produto_data["padrao_fiscal_confianca"] = padrao["confianca"]
    produto_data["padrao_fiscal_motivo"] = padrao["motivo"]

    return produto_data
