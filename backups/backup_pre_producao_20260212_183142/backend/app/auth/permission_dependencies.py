"""
Sistema de Permissões Automáticas (Auto-Imply)

Define dependências entre permissões. Quando uma permissão é atribuída,
suas dependências são automaticamente incluídas.

Exemplo: vendas.criar automaticamente inclui clientes.visualizar e produtos.visualizar
"""

from app.utils.logger import logger


# Mapa de dependências: chave = permissão principal, valor = lista de dependências
PERMISSION_DEPENDENCIES = {
    # PDV precisa ver clientes e produtos
    "vendas.criar": ["clientes.visualizar", "produtos.visualizar"],
    "vendas.editar": ["vendas.visualizar", "clientes.visualizar", "produtos.visualizar"],
    "vendas.excluir": ["vendas.visualizar"],
    
    # Editar/Excluir precisa de Visualizar
    "clientes.editar": ["clientes.visualizar"],
    "clientes.excluir": ["clientes.visualizar"],
    "produtos.editar": ["produtos.visualizar"],
    "produtos.excluir": ["produtos.visualizar"],
    
    # Relatórios financeiros precisam de visualização de dados
    "relatorios.financeiro": ["vendas.visualizar", "produtos.visualizar", "clientes.visualizar"],
    "relatorios.gerencial": ["vendas.visualizar", "produtos.visualizar", "clientes.visualizar"],
    
    # IA - Fluxo de Caixa precisa de acesso a relatórios financeiros
    "ia.fluxo_caixa": ["relatorios.financeiro"],
    
    # Compras precisa de visualização de produtos
    "compras.gerenciar": ["produtos.visualizar"],
    
    # Administração de usuários
    "usuarios.manage": ["configuracoes.editar"],
}


def get_all_required_permissions(permission_code: str) -> list[str]:
    """
    Retorna lista completa de permissões incluindo dependências.
    
    Args:
        permission_code: Código da permissão principal
        
    Returns:
        Lista de códigos de permissão (incluindo a principal e dependências)
    """
    permissions = {permission_code}  # Set para evitar duplicatas
    
    # Adicionar dependências diretas
    if permission_code in PERMISSION_DEPENDENCIES:
        for dep in PERMISSION_DEPENDENCIES[permission_code]:
            permissions.add(dep)
            # Recursivamente adicionar dependências das dependências
            sub_deps = get_all_required_permissions(dep)
            permissions.update(sub_deps)
    
    return list(permissions)


def expand_permissions(permission_codes: list[str]) -> list[str]:
    """
    Expande uma lista de permissões incluindo todas as dependências.
    
    Args:
        permission_codes: Lista de códigos de permissão
        
    Returns:
        Lista expandida com todas as dependências
    """
    expanded = set()
    for code in permission_codes:
        expanded.update(get_all_required_permissions(code))
    return list(expanded)


# Exemplo de uso:
if __name__ == "__main__":
    logger.info("🔑 Sistema de Permissões Automáticas\n")
    
    # Testar vendas.criar
    logger.info("📦 vendas.criar inclui:")
    for perm in get_all_required_permissions("vendas.criar"):
        logger.info(f"   ✅ {perm}")
    
    logger.info("\n📊 relatorios.financeiro inclui:")
    for perm in get_all_required_permissions("relatorios.financeiro"):
        logger.info(f"   ✅ {perm}")
    
    logger.info("\n🔧 Expandindo lista [vendas.criar, produtos.editar]:")
    expanded = expand_permissions(["vendas.criar", "produtos.editar"])
    for perm in sorted(expanded):
        logger.info(f"   ✅ {perm}")
