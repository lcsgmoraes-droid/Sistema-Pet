"""Historico de alteracoes do cadastro base do produto."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import User
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission

router = APIRouter()


@router.get("/{produto_id}/historico-alteracoes")
@require_permission("produtos.visualizar")
def listar_historico_produto(
    produto_id: int,
    limite: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Alteracoes do cadastro base do produto: data, usuario, campo, valor anterior e novo."""
    from app.produtos_catalogo_models import ProdutoHistoricoAlteracao

    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    produto = db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    linhas = (
        db.query(ProdutoHistoricoAlteracao, User.nome, User.email)
        .outerjoin(User, User.id == ProdutoHistoricoAlteracao.user_id)
        .filter(ProdutoHistoricoAlteracao.produto_id == produto_id)
        .order_by(ProdutoHistoricoAlteracao.alterado_em.desc(), ProdutoHistoricoAlteracao.id.desc())
        .limit(limite)
        .all()
    )
    return {
        "items": [
            {
                "campo": registro.campo,
                "valor_anterior": registro.valor_anterior,
                "valor_novo": registro.valor_novo,
                "alterado_em": registro.alterado_em.isoformat() if registro.alterado_em else None,
                "usuario": nome or email,
            }
            for registro, nome, email in linhas
        ]
    }
