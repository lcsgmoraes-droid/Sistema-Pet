"""
🏢 HELPERS DE TENANT

Funções para manipular contexto de tenant e validar isolamento.

Exemplo de uso:
    tenant_id = get_default_tenant_id()
    assert_tenant_isolation(response1, response2)
"""

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
ALTERNATE_TENANT_ID = "99999999-9999-9999-9999-999999999999"


def get_default_tenant_id() -> str:
    """
    Retorna ID do tenant padrão usado nos testes.
    
    Returns:
        UUID string do tenant de teste padrão
    
    Exemplo:
        tenant_id = get_default_tenant_id()
        headers = create_auth_header(tenant_id=tenant_id)
    """
    return DEFAULT_TENANT_ID


def get_alternate_tenant_id() -> str:
    """
    Retorna ID de tenant alternativo para testes de isolamento.
    
    Returns:
        UUID string de tenant alternativo
    
    Exemplo:
        tenant_id = get_alternate_tenant_id()
        token = create_token_for_different_tenant(tenant_id)
    """
    return ALTERNATE_TENANT_ID


def create_tenant_context(tenant_id: str = None):
    """
    Cria contexto de tenant para uso em testes.
    
    Args:
        tenant_id: ID do tenant (default: DEFAULT_TENANT_ID)
    
    Returns:
        Dict com tenant_id pronto para injeção
    
    Exemplo:
        context = create_tenant_context("abc-123")
        # Usar em mocks ou fixtures
    """
    return {
        "tenant_id": tenant_id or DEFAULT_TENANT_ID
    }


def assert_tenant_isolation(response_tenant_1: dict, response_tenant_2: dict):
    """
    Valida que dois responses de tenants diferentes não compartilham dados.
    
    Args:
        response_tenant_1: Response data do tenant 1
        response_tenant_2: Response data do tenant 2
    
    Raises:
        AssertionError: Se houver vazamento de dados entre tenants
    
    Exemplo:
        # Token tenant 1
        headers1 = create_auth_header(tenant_id=get_default_tenant_id())
        response1 = client.get("/api/vendas", headers=headers1).json()
        
        # Token tenant 2
        headers2 = create_auth_header(tenant_id=get_alternate_tenant_id())
        response2 = client.get("/api/vendas", headers=headers2).json()
        
        # Valida isolamento
        assert_tenant_isolation(response1, response2)
    """
    # Se response é lista, compara IDs
    if isinstance(response_tenant_1, list) and isinstance(response_tenant_2, list):
        ids_tenant_1 = {item.get("id") for item in response_tenant_1 if "id" in item}
        ids_tenant_2 = {item.get("id") for item in response_tenant_2 if "id" in item}
        
        # IDs não podem se sobrepor
        overlap = ids_tenant_1.intersection(ids_tenant_2)
        assert len(overlap) == 0, f"❌ VAZAMENTO DE DADOS: IDs compartilhados entre tenants: {overlap}"
    
    # Se response é dict com tenant_id, valida
    if isinstance(response_tenant_1, dict) and "tenant_id" in response_tenant_1:
        assert response_tenant_1["tenant_id"] != response_tenant_2.get("tenant_id"), \
            "❌ VAZAMENTO: Mesmo tenant_id retornado para tokens diferentes"


def extract_tenant_ids_from_list(data: list) -> set:
    """
    Extrai todos os tenant_ids únicos de uma lista de dicts.
    
    Args:
        data: Lista de dicts com tenant_id
    
    Returns:
        Set de tenant_ids encontrados
    
    Exemplo:
        response = client.get("/api/vendas").json()
        tenant_ids = extract_tenant_ids_from_list(response)
        assert len(tenant_ids) == 1  # Apenas 1 tenant nos dados
    """
    tenant_ids = set()
    for item in data:
        if isinstance(item, dict) and "tenant_id" in item:
            tenant_ids.add(item["tenant_id"])
    return tenant_ids


def assert_single_tenant_in_response(data: list, expected_tenant_id: str):
    """
    Valida que todos os registros pertencem ao mesmo tenant.
    
    Args:
        data: Lista de dicts retornados pela API
        expected_tenant_id: ID do tenant esperado
    
    Raises:
        AssertionError: Se encontrar tenant_id diferente
    
    Exemplo:
        response = client.get("/api/vendas", headers=headers).json()
        assert_single_tenant_in_response(response, get_default_tenant_id())
    """
    tenant_ids = extract_tenant_ids_from_list(data)
    
    assert len(tenant_ids) <= 1, f"❌ Múltiplos tenants encontrados: {tenant_ids}"
    
    if len(tenant_ids) == 1:
        actual_tenant_id = list(tenant_ids)[0]
        assert actual_tenant_id == expected_tenant_id, \
            f"❌ Tenant errado: esperado {expected_tenant_id}, encontrado {actual_tenant_id}"
