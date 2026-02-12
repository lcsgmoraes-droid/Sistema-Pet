"""
Helper: Auditoria de Compensação via JSON
Data: 2026-01-23

Funções utilitárias para criar JSON estruturado de auditoria
em campos observacoes, sem necessidade de tabela comissoes_audit_log
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from app.utils.logger import logger


def decimal_to_float(obj):
    """Converter Decimal para float no JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def criar_json_auditoria_compensacao(
    fechamento_id: int,
    funcionario_id: int,
    funcionario_nome: str,
    valor_bruto_comissao: float,
    valor_compensado: float,
    valor_liquido_pago: float,
    dividas_compensadas: List[Dict[str, Any]],
    usuario_id: int,
    ip_address: Optional[str] = None
) -> str:
    """
    Cria JSON estruturado para auditoria de compensação
    
    Args:
        fechamento_id: ID do fechamento de comissão
        funcionario_id: ID do funcionário/parceiro
        funcionario_nome: Nome do funcionário
        valor_bruto_comissao: Valor total da comissão (antes da compensação)
        valor_compensado: Valor total compensado em dívidas
        valor_liquido_pago: Valor efetivamente pago (bruto - compensado)
        dividas_compensadas: Lista de dívidas compensadas com detalhes
        usuario_id: ID do usuário que executou a operação
        ip_address: IP do usuário (opcional)
    
    Returns:
        String JSON formatada
    
    Example:
        >>> dividas = [
        ...     {
        ...         "divida_id": 45,
        ...         "valor_original": 800.00,
        ...         "valor_compensado": 800.00,
        ...         "tipo": "estorno_venda",
        ...         "venda_id": 148
        ...     }
        ... ]
        >>> json_str = criar_json_auditoria_compensacao(
        ...     fechamento_id=90,
        ...     funcionario_id=25,
        ...     funcionario_nome="João Silva",
        ...     valor_bruto_comissao=1500.00,
        ...     valor_compensado=800.00,
        ...     valor_liquido_pago=700.00,
        ...     dividas_compensadas=dividas,
        ...     usuario_id=1
        ... )
    """
    auditoria = {
        "tipo": "compensacao_automatica",
        "fechamento_id": fechamento_id,
        "data_compensacao": datetime.now().isoformat(),
        "funcionario": {
            "id": funcionario_id,
            "nome": funcionario_nome
        },
        "valores": {
            "bruto_comissao": float(valor_bruto_comissao) if isinstance(valor_bruto_comissao, Decimal) else valor_bruto_comissao,
            "compensado": float(valor_compensado) if isinstance(valor_compensado, Decimal) else valor_compensado,
            "liquido_pago": float(valor_liquido_pago) if isinstance(valor_liquido_pago, Decimal) else valor_liquido_pago
        },
        "dividas_compensadas": dividas_compensadas,
        "auditoria": {
            "usuario_id": usuario_id,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if ip_address:
        auditoria["auditoria"]["ip_address"] = ip_address
    
    return json.dumps(auditoria, ensure_ascii=False, indent=2, default=decimal_to_float)


def criar_json_estorno_comissao(
    venda_id: int,
    comissao_item_id: int,
    valor_estornado: float,
    motivo: str,
    usuario_id: int,
    ip_address: Optional[str] = None
) -> str:
    """
    Cria JSON para auditoria de estorno de comissão
    
    Args:
        venda_id: ID da venda estornada
        comissao_item_id: ID do item de comissão
        valor_estornado: Valor da comissão estornada
        motivo: Motivo do estorno
        usuario_id: ID do usuário
        ip_address: IP (opcional)
    
    Returns:
        String JSON formatada
    """
    auditoria = {
        "tipo": "estorno_comissao",
        "venda_id": venda_id,
        "comissao_item_id": comissao_item_id,
        "data_estorno": datetime.now().isoformat(),
        "valor_estornado": float(valor_estornado) if isinstance(valor_estornado, Decimal) else valor_estornado,
        "motivo": motivo,
        "auditoria": {
            "usuario_id": usuario_id,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if ip_address:
        auditoria["auditoria"]["ip_address"] = ip_address
    
    return json.dumps(auditoria, ensure_ascii=False, indent=2, default=decimal_to_float)


def criar_json_ajuste_retroativo(
    funcionario_id: int,
    valor_ajuste: float,
    motivo: str,
    usuario_id: int,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> str:
    """
    Cria JSON para auditoria de ajuste retroativo
    
    Args:
        funcionario_id: ID do funcionário
        valor_ajuste: Valor do ajuste (positivo ou negativo)
        motivo: Motivo do ajuste
        usuario_id: ID do usuário
        referencia_tipo: Tipo da referência (opcional)
        referencia_id: ID da referência (opcional)
        ip_address: IP (opcional)
    
    Returns:
        String JSON formatada
    """
    auditoria = {
        "tipo": "ajuste_retroativo",
        "funcionario_id": funcionario_id,
        "data_ajuste": datetime.now().isoformat(),
        "valor_ajuste": float(valor_ajuste) if isinstance(valor_ajuste, Decimal) else valor_ajuste,
        "motivo": motivo,
        "auditoria": {
            "usuario_id": usuario_id,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if referencia_tipo and referencia_id:
        auditoria["referencia"] = {
            "tipo": referencia_tipo,
            "id": referencia_id
        }
    
    if ip_address:
        auditoria["auditoria"]["ip_address"] = ip_address
    
    return json.dumps(auditoria, ensure_ascii=False, indent=2, default=decimal_to_float)


def extrair_info_compensacao(observacoes_json: str) -> Optional[Dict]:
    """
    Extrai informações de compensação de um JSON em observacoes
    
    Args:
        observacoes_json: String JSON de observações
    
    Returns:
        Dicionário com dados ou None se não for JSON válido
    """
    if not observacoes_json:
        return None
    
    try:
        data = json.loads(observacoes_json)
        if isinstance(data, dict) and data.get("tipo") == "compensacao_automatica":
            return data
        return None
    except json.JSONDecodeError:
        return None


def formatar_observacao_simples_compensacao(
    valor_compensado: float,
    divida_ids: List[int]
) -> str:
    """
    Cria observação simples em texto para campos que não suportam JSON complexo
    
    Args:
        valor_compensado: Valor compensado
        divida_ids: Lista de IDs das dívidas
    
    Returns:
        String formatada para exibição
    """
    dividas_str = ", ".join([f"#{id}" for id in divida_ids])
    return f"Compensação automática: R$ {valor_compensado:.2f} (dívidas: {dividas_str})"


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    logger.info("EXEMPLOS DE USO - Helper Auditoria Compensação")
    print("="*80)
    
    # Exemplo 1: Compensação
    logger.info("\n1. JSON de Compensação:")
    print("-"*80)
    
    dividas_exemplo = [
        {
            "divida_id": 45,
            "valor_original": 800.00,
            "valor_compensado": 800.00,
            "saldo_restante": 0.00,
            "tipo": "estorno_venda",
            "venda_id": 148
        }
    ]
    
    json_comp = criar_json_auditoria_compensacao(
        fechamento_id=90,
        funcionario_id=25,
        funcionario_nome="João Silva",
        valor_bruto_comissao=1500.00,
        valor_compensado=800.00,
        valor_liquido_pago=700.00,
        dividas_compensadas=dividas_exemplo,
        usuario_id=1,
        ip_address="192.168.1.100"
    )
    
    print(json_comp)
    
    # Exemplo 2: Estorno
    logger.info("\n\n2. JSON de Estorno:")
    print("-"*80)
    
    json_estorno = criar_json_estorno_comissao(
        venda_id=148,
        comissao_item_id=101,
        valor_estornado=300.00,
        motivo="Devolução total da venda",
        usuario_id=1
    )
    
    print(json_estorno)
    
    # Exemplo 3: Ajuste Retroativo
    logger.info("\n\n3. JSON de Ajuste Retroativo:")
    print("-"*80)
    
    json_ajuste = criar_json_ajuste_retroativo(
        funcionario_id=25,
        valor_ajuste=-150.00,
        motivo="Correção de cálculo de comissão do mês anterior",
        usuario_id=1,
        referencia_tipo="fechamento",
        referencia_id=85
    )
    
    print(json_ajuste)
    
    # Exemplo 4: Observação Simples
    logger.info("\n\n4. Observação Simples (texto):")
    print("-"*80)
    
    obs_simples = formatar_observacao_simples_compensacao(
        valor_compensado=800.00,
        divida_ids=[45, 46]
    )
    
    print(obs_simples)
    
    print("\n" + "="*80)
