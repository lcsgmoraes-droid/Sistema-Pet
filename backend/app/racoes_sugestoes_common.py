"""Helpers compartilhados das sugestoes inteligentes de racoes."""

from app.produtos.racao import _produto_eh_racao_expr


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


__all__ = ["_produto_eh_racao_expr", "_validar_tenant_e_obter_usuario"]
