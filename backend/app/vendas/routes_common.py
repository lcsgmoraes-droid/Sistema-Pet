"""Helpers compartilhados pelas rotas de vendas."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Cliente
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.vendas_models import Venda


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrão repetido nas rotas)."""
    from app.tenancy.context import set_current_tenant

    current_user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)
    return current_user, tenant_id


def _obter_venda_ou_404(db: Session, venda_id: int, tenant_id: str):
    """Busca venda com validação de tenant e retorna 404 se não encontrada."""
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    return venda


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validação de tenant e retorna 404 se não encontrado."""
    cliente = db.query(Cliente).filter_by(id=cliente_id, tenant_id=tenant_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return cliente


def _remover_provisoes_comissao_venda(db: Session, venda_id: int, tenant_id) -> None:
    execute_tenant_safe(
        db,
        """
        DELETE FROM contas_pagar
        WHERE {tenant_filter}
          AND descricao LIKE :descricao
          AND status = 'pendente'
    """,
        {"descricao": f"%Comissão - Venda #{venda_id}%"},
        tenant_id=tenant_id,
    )


def _normalizar_motivo_exclusao_venda(motivo: Optional[str]) -> str:
    motivo_normalizado = (motivo or "").strip()
    if len(motivo_normalizado) < 10:
        raise HTTPException(
            status_code=400,
            detail="Informe uma justificativa com pelo menos 10 caracteres para excluir/cancelar a venda.",
        )
    return motivo_normalizado
