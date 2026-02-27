"""Rotas de Avise-me (Notificação de Estoque) — E-commerce.

Endpoints públicos para registro de interesse e função auxiliar
chamada por produtos_routes quando estoque volta ao positivo.
"""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import EcommerceNotifyRequest, Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecommerce-notify", tags=["ecommerce-notify"])


# ─── Schemas ───────────────────────────────────────────────────────────────

class NotifyMeRequest(BaseModel):
    email: str
    product_id: int
    product_name: str
    tenant_id: str  # UUID ou slug — resolvido pelo frontend


class NotifyMeResponse(BaseModel):
    ok: bool
    message: str


# ─── Endpoint público — registrar interesse ────────────────────────────────

@router.post("/registrar", response_model=NotifyMeResponse)
def registrar_avise_me(
    body: NotifyMeRequest,
    db: Session = Depends(get_session),
):
    """Salva uma solicitação de 'Avise-me quando chegar' para um produto."""
    # Resolver tenant (aceita UUID ou slug)
    tenant = (
        db.query(Tenant).filter(Tenant.id == body.tenant_id).first()
        or db.query(Tenant).filter(Tenant.ecommerce_slug == body.tenant_id).first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Loja não encontrada")

    email_lower = body.email.strip().lower()

    # Evitar duplicatas
    existing = (
        db.query(EcommerceNotifyRequest)
        .filter(
            EcommerceNotifyRequest.tenant_id == str(tenant.id),
            EcommerceNotifyRequest.product_id == body.product_id,
            EcommerceNotifyRequest.email == email_lower,
            EcommerceNotifyRequest.notified == False,
        )
        .first()
    )
    if existing:
        return NotifyMeResponse(ok=True, message="Você já está na lista de avisos para este produto.")

    entry = EcommerceNotifyRequest(
        tenant_id=str(tenant.id),
        product_id=body.product_id,
        product_name=body.product_name,
        email=email_lower,
        notified=False,
    )
    db.add(entry)
    db.commit()

    return NotifyMeResponse(
        ok=True,
        message="Pronto! Te avisaremos por email quando o produto voltar ao estoque.",
    )


# ─── Admin — listar solicitações pendentes ─────────────────────────────────

@router.get("/pendentes")
def listar_pendentes(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Lista todas as solicitações de aviso ainda não enviadas para o tenant."""
    _, tenant_id = user_and_tenant
    items = (
        db.query(EcommerceNotifyRequest)
        .filter(
            EcommerceNotifyRequest.tenant_id == str(tenant_id),
            EcommerceNotifyRequest.notified == False,
        )
        .order_by(EcommerceNotifyRequest.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "product_id": r.product_id,
            "product_name": r.product_name,
            "email": r.email,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in items
    ]


# ─── Função auxiliar — chamada pelo produtos_routes ────────────────────────

def notificar_clientes_estoque_disponivel(
    db: Session,
    tenant_id: str,
    product_id: int,
    product_name: str,
) -> int:
    """
    Envia e-mail para todos os clientes que pediram aviso para este produto.
    Retorna a quantidade de notificações enviadas.
    """
    from app.services.email_service import send_notify_me_email

    # Buscar tenant para montar URL da loja
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    store_name = tenant.name if tenant else "Petshop"
    store_ref = (tenant.ecommerce_slug or tenant_id) if tenant else tenant_id
    base_url = os.getenv("ECOMMERCE_BASE_URL", "https://mlprohub.com.br")

    # Buscar SKU do produto para incluir na URL (link direto filtrado)
    from app.produtos_models import Produto
    produto_obj = db.query(Produto).filter(Produto.id == product_id).first()
    sku_param = produto_obj.codigo if produto_obj else None
    if sku_param:
        store_url = f"{base_url}/{store_ref}?busca={sku_param}"
    else:
        store_url = f"{base_url}/{store_ref}"

    pending = (
        db.query(EcommerceNotifyRequest)
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.product_id == product_id,
            EcommerceNotifyRequest.notified == False,
        )
        .all()
    )

    if not pending:
        return 0

    count = 0
    for req in pending:
        sent = send_notify_me_email(
            to=req.email,
            product_name=product_name or req.product_name or "Produto",
            store_name=store_name,
            store_url=store_url,
        )
        if sent:
            req.notified = True
            req.notified_at = datetime.now(timezone.utc)
            count += 1

    db.commit()
    logger.info(
        "[AVISE-ME] %d email(s) enviado(s) para produto #%d (%s)",
        count,
        product_id,
        product_name,
    )
    return count
