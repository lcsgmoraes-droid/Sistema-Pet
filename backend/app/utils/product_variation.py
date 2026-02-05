"""
🎯 SPRINT 2: UTILIDADES PARA PRODUTOS COM VARIAÇÃO
Funções auxiliares para gerenciamento de variações
"""

from typing import Dict


def build_variation_signature(attributes: Dict[str, str]) -> str:
    """
    Gera assinatura única da variação.
    
    A assinatura é usada para:
    - Garantir unicidade de variações
    - Evitar duplicações
    - Indexação no banco
    
    Args:
        attributes: Dicionário de atributos da variação
                   Ex: {"cor": "Azul", "tamanho": "G"}
    
    Returns:
        String com assinatura normalizada
        Ex: "cor:azul|tamanho:g"
    
    Regras:
        - Chaves ordenadas alfabeticamente
        - Valores normalizados (lowercase, sem espaços extras)
        - Separador: pipe (|)
        - Formato: chave:valor
    
    Exemplos:
        >>> build_variation_signature({"cor": "Azul", "tamanho": "G"})
        'cor:azul|tamanho:g'
        
        >>> build_variation_signature({"tamanho": "M", "cor": "Vermelho"})
        'cor:vermelho|tamanho:m'
        
        >>> build_variation_signature({"voltagem": "220V", "cor": "Branco"})
        'cor:branco|voltagem:220v'
    """
    parts = []
    for key in sorted(attributes.keys()):
        value = str(attributes[key]).strip().lower()
        parts.append(f"{key.lower()}:{value}")
    return "|".join(parts)


def validate_variation_attributes(attributes: Dict[str, str]) -> bool:
    """
    Valida se os atributos de variação são válidos.
    
    Args:
        attributes: Dicionário de atributos
    
    Returns:
        True se válido
    
    Raises:
        ValueError: Se atributos inválidos
    """
    if not attributes:
        raise ValueError("Atributos de variação não podem estar vazios")
    
    if not isinstance(attributes, dict):
        raise ValueError("Atributos devem ser um dicionário")
    
    for key, value in attributes.items():
        if not key or not str(key).strip():
            raise ValueError("Chave de atributo não pode estar vazia")
        
        if not value or not str(value).strip():
            raise ValueError(f"Valor do atributo '{key}' não pode estar vazio")
    
    return True


def format_variation_name(base_name: str, attributes: Dict[str, str]) -> str:
    """
    Formata o nome completo da variação.
    
    Args:
        base_name: Nome do produto pai
        attributes: Atributos da variação
    
    Returns:
        Nome formatado
        Ex: "Camiseta - Azul M"
    
    Exemplos:
        >>> format_variation_name("Camiseta", {"cor": "Azul", "tamanho": "M"})
        'Camiseta - Azul M'
    """
    attr_values = [str(v).title() for v in attributes.values()]
    return f"{base_name} - {' '.join(attr_values)}"
