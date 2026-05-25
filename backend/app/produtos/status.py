from datetime import datetime
from typing import Any, Callable

from fastapi import HTTPException


def validar_pode_inativar_produto(db, produto: Any, tenant_id, produto_model=None):
    """Bloqueia inativacao de produto pai com variacoes ativas."""
    if not produto.is_parent:
        return

    if produto_model is None:
        from app.produtos_models import Produto

        produto_model = Produto

    variacoes_ativas = db.query(produto_model).filter(
        produto_model.produto_pai_id == produto.id,
        produto_model.tenant_id == tenant_id,
        produto_model.ativo == True,
    ).count()

    if variacoes_ativas > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"âŒ Produto '{produto.nome}' possui {variacoes_ativas} variaÃ§Ã£o(Ãµes) ativa(s) "
                "e nÃ£o pode ser desativado. Desative primeiro todas as variaÃ§Ãµes."
            ),
        )


def aplicar_status_ativo_produto(
    produto: Any,
    ativo: bool,
    agora_provider: Callable[[], datetime] = datetime.now,
):
    """Mantem ativo e situacao sincronizados."""
    produto.ativo = ativo
    produto.situacao = ativo
    if not ativo:
        produto.anunciar_ecommerce = False
        produto.anunciar_app = False
    produto.updated_at = agora_provider()
