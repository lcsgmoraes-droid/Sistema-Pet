"""
Controle de Permissões Multi-Tenant
====================================

OBJETIVO DESTE MÓDULO
----------------------
Criar o mecanismo que controla O QUE cada usuário pode acessar
com base no papel (role) dele dentro da empresa (tenant).

Isso prepara o sistema para:
- Limitar telas
- Limitar ações
- Diferenciar owner / admin / staff / viewer

IMPORTANTE
----------
- NÃO cria tabelas
- NÃO altera banco
- NÃO muda JWT ainda
- Apenas cria uma dependency reutilizável

EXEMPLOS DE USO FUTURO
-----------------------
@router.delete("/produtos/{id}")
def deletar_produto(
    id: int,
    user: CurrentUser = Depends(require_roles(["owner", "admin"]))
):
    # Apenas owner e admin podem deletar produtos
    ...

@router.get("/relatorios/financeiro")
def relatorio_financeiro(
    user: CurrentUser = Depends(require_roles(["owner"]))
):
    # Apenas owner pode ver relatórios financeiros
    ...
"""

from fastapi import Depends, HTTPException, status
from app.security.context import CurrentUser, get_current_user


def require_roles(allowed_roles: list[str]):
    """
    Dependency para proteger rotas por papel do usuário.

    Exemplo de uso futuro:
    Depends(require_roles(["owner", "admin"]))
    """
    def dependency(user: CurrentUser = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta ação",
            )
        return user

    return dependency
