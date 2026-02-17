"""
📜 HELPERS DE VALIDAÇÃO DE CONTRATOS

Funções para validar schemas Pydantic e estruturas de response.

Exemplo de uso:
    assert_contract(response, ["id", "nome", "data"])
    assert_date_format(response["data"])
    assert_non_negative(response["total"])
"""

from datetime import date, datetime
from typing import Any, List, Dict


def assert_contract(data: dict, required_fields: List[str]):
    """
    Valida que response contém todos os campos obrigatórios.
    
    Args:
        data: Dict retornado pela API
        required_fields: Lista de campos obrigatórios
    
    Raises:
        AssertionError: Se algum campo obrigatório estiver ausente
    
    Exemplo:
        response = client.get("/api/vendas/123").json()
        assert_contract(response, ["id", "cliente_nome", "total", "data"])
    """
    missing_fields = [field for field in required_fields if field not in data]
    assert len(missing_fields) == 0, \
        f"❌ CONTRATO QUEBRADO: Campos ausentes: {missing_fields}"


def assert_date_format(value: Any, field_name: str = "data"):
    """
    Valida que campo de data está no formato ISO 8601 (YYYY-MM-DD).
    
    Args:
        value: Valor a validar
        field_name: Nome do campo (para mensagem de erro)
    
    Raises:
        AssertionError: Se formato estiver incorreto
    
    Exemplo:
        assert_date_format(response["data_venda"])
        assert_date_format(response["created_at"], "created_at")
    """
    if isinstance(value, (date, datetime)):
        return  # Já é objeto date/datetime válido
    
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return
        except ValueError:
            pass
    
    raise AssertionError(
        f"❌ CONTRATO QUEBRADO: '{field_name}' deve estar no formato ISO 8601. "
        f"Recebido: {value} (tipo: {type(value).__name__})"
    )


def assert_non_negative(value: Any, field_name: str = "valor"):
    """
    Valida que valor numérico não é negativo.
    
    Args:
        value: Valor a validar
        field_name: Nome do campo (para mensagem de erro)
    
    Raises:
        AssertionError: Se valor for negativo
    
    Exemplo:
        assert_non_negative(response["total"], "total")
        assert_non_negative(response["quantidade"], "quantidade")
    """
    assert isinstance(value, (int, float)), \
        f"❌ '{field_name}' deve ser numérico. Recebido: {type(value).__name__}"
    
    assert value >= 0, \
        f"❌ CONTRATO QUEBRADO: '{field_name}' não pode ser negativo. Valor: {value}"


def assert_list_of_dicts(data: Any, min_length: int = 0):
    """
    Valida que response é lista de dicts.
    
    Args:
        data: Dados a validar
        min_length: Tamanho mínimo esperado (default: 0)
    
    Raises:
        AssertionError: Se não for lista de dicts
    
    Exemplo:
        response = client.get("/api/vendas").json()
        assert_list_of_dicts(response, min_length=1)
    """
    assert isinstance(data, list), \
        f"❌ CONTRATO QUEBRADO: Esperado list, recebido {type(data).__name__}"
    
    assert len(data) >= min_length, \
        f"❌ CONTRATO QUEBRADO: Esperado pelo menos {min_length} itens, recebido {len(data)}"
    
    if len(data) > 0:
        assert isinstance(data[0], dict), \
            f"❌ CONTRATO QUEBRADO: Esperado list[dict], primeiro item é {type(data[0]).__name__}"


def validate_schema(data: dict, schema: Dict[str, type]):
    """
    Valida que todos os campos têm os tipos corretos.
    
    Args:
        data: Dict retornado pela API
        schema: Dict mapeando campo -> tipo esperado
    
    Raises:
        AssertionError: Se algum campo tiver tipo incorreto
    
    Exemplo:
        response = client.get("/api/vendas/123").json()
        validate_schema(response, {
            "id": int,
            "cliente_nome": str,
            "total": float,
            "data": (str, date)
        })
    """
    for field, expected_type in schema.items():
        assert field in data, \
            f"❌ CONTRATO QUEBRADO: Campo '{field}' ausente"
        
        actual_value = data[field]
        
        # Se expected_type é tupla, valida qualquer um dos tipos
        if isinstance(expected_type, tuple):
            assert isinstance(actual_value, expected_type), \
                f"❌ CONTRATO QUEBRADO: '{field}' deve ser {expected_type}. " \
                f"Recebido: {type(actual_value).__name__}"
        else:
            assert isinstance(actual_value, expected_type), \
                f"❌ CONTRATO QUEBRADO: '{field}' deve ser {expected_type.__name__}. " \
                f"Recebido: {type(actual_value).__name__}"


def assert_response_structure(data: dict, required: List[str], optional: List[str] = None):
    """
    Valida estrutura completa de response (campos obrigatórios e opcionais).
    
    Args:
        data: Dict retornado pela API
        required: Lista de campos obrigatórios
        optional: Lista de campos opcionais (podem estar ausentes)
    
    Raises:
        AssertionError: Se estrutura estiver incorreta
    
    Exemplo:
        response = client.get("/api/vendas/123").json()
        assert_response_structure(
            response,
            required=["id", "cliente_nome", "total"],
            optional=["observacoes", "desconto"]
        )
    """
    # Valida campos obrigatórios
    assert_contract(data, required)
    
    # Valida que não há campos extras inesperados
    if optional:
        allowed_fields = set(required + optional)
        actual_fields = set(data.keys())
        unexpected_fields = actual_fields - allowed_fields
        
        assert len(unexpected_fields) == 0, \
            f"⚠️ Campos inesperados no response: {unexpected_fields}"


def assert_pagination_contract(data: dict):
    """
    Valida contrato de paginação padrão.
    
    Args:
        data: Dict retornado pela API
    
    Raises:
        AssertionError: Se contrato de paginação estiver incorreto
    
    Exemplo:
        response = client.get("/api/vendas?page=1&per_page=10").json()
        assert_pagination_contract(response)
    """
    required_pagination_fields = ["items", "total", "page", "per_page", "pages"]
    assert_contract(data, required_pagination_fields)
    
    assert_list_of_dicts(data["items"])
    assert_non_negative(data["total"], "total")
    assert_non_negative(data["page"], "page")
    assert_non_negative(data["per_page"], "per_page")
    assert_non_negative(data["pages"], "pages")
