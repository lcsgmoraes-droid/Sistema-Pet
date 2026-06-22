"""Rotas de Avise-me (Notificação de Estoque) — E-commerce.

Endpoints públicos para registro de interesse e função auxiliar
chamada por produtos_routes quando estoque volta ao positivo.
"""

import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import EcommerceNotifyRequest, Tenant
from app.tenancy.context import set_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecommerce-notify", tags=["ecommerce-notify"])


def _set_tenant_context(tenant_id: str) -> str:
    tenant_uuid = UUID(str(tenant_id))
    set_current_tenant(tenant_uuid)
    return str(tenant_uuid)


def _normalize_tenant_uuid(raw_tenant_id: str | None) -> str | None:
    if not raw_tenant_id:
        return None
    try:
        return str(UUID(str(raw_tenant_id).strip()))
    except Exception:
        return None


def _resolve_notify_tenant(db: Session, tenant_ref: str | None) -> Tenant | None:
    tenant_uuid = _normalize_tenant_uuid(tenant_ref)
    if tenant_uuid:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
        if tenant:
            return tenant

    slug = str(tenant_ref or "").strip().lower()
    if not slug:
        return None
    return db.query(Tenant).filter(Tenant.ecommerce_slug == slug).first()


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
    tenant = _resolve_notify_tenant(db, body.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Loja não encontrada")

    if str(tenant.status or "").strip().lower() not in {"active", "ativo"}:
        raise HTTPException(status_code=403, detail="Loja inativa")

    tenant_id = _set_tenant_context(str(tenant.id))
    email_lower = body.email.strip().lower()

    # Evitar duplicatas
    existing = (
        db.query(EcommerceNotifyRequest)
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.product_id == body.product_id,
            EcommerceNotifyRequest.email == email_lower,
            EcommerceNotifyRequest.notified.is_(False),
        )
        .first()
    )
    if existing:
        return NotifyMeResponse(
            ok=True, message="Você já está na lista de avisos para este produto."
        )

    entry = EcommerceNotifyRequest(
        tenant_id=tenant_id,
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
            EcommerceNotifyRequest.notified.is_(False),
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

    tenant_id = _set_tenant_context(tenant_id)

    # Buscar tenant para montar URL da loja
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    store_name = tenant.name if tenant else "Petshop"
    store_ref = (tenant.ecommerce_slug or tenant_id) if tenant else tenant_id
    base_url = os.getenv("ECOMMERCE_BASE_URL", "https://corepet.com.br")

    # Buscar SKU do produto para incluir na URL (link direto filtrado)
    from app.produtos_models import Produto

    produto_obj = (
        db.query(Produto)
        .filter(Produto.id == product_id, Produto.tenant_id == tenant_id)
        .first()
    )
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
            EcommerceNotifyRequest.notified.is_(False),
        )
        .all()
    )

    if not pending:
        return 0

    # Coletar push tokens dos usuários cadastrados para este produto
    from app.models import User
    from app.services.push_devices import load_user_push_targets
    import requests as http_requests

    def _send_expo_push(tokens: list, title: str, body: str, data: dict = None):
        """Envia push via Expo Push API para uma lista de tokens."""
        if not tokens:
            return
        seen_tokens = set()
        messages = []
        for token in tokens:
            token = str(token or "").strip()
            if (
                not token
                or not token.startswith("ExponentPushToken")
                or token in seen_tokens
            ):
                continue
            seen_tokens.add(token)
            messages.append(
                {
                    "to": token,
                    "sound": "default",
                    "title": title,
                    "body": body,
                    "data": data or {},
                }
            )
        if not messages:
            return
        try:
            http_requests.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as e_push:
            logger.warning("[AVISE-ME] Erro ao enviar push: %s", e_push)

    count = 0
    push_tokens = []

    for req in pending:
        # Enviar e-mail
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

        # Coletar push token do usuário (se tiver)
        user = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.email == req.email,
            )
            .first()
        )
        if user:
            push_tokens.extend(
                target.token
                for target in load_user_push_targets(
                    db,
                    tenant_id=tenant_id,
                    user_id=user.id,
                    legacy_push_token=getattr(user, "push_token", None),
                )
            )

    db.commit()

    # Enviar push em lote para todos que tinham token
    _send_expo_push(
        tokens=push_tokens,
        title="📦 Produto disponível!",
        body=f"{product_name or 'Produto'} voltou ao estoque. Corre antes que acabe!",
        data={"product_id": product_id, "type": "stock_available"},
    )
    if push_tokens:
        logger.info(
            "[AVISE-ME] %d push(es) enviado(s) para produto #%d (%s)",
            len(push_tokens),
            product_id,
            product_name,
        )

    logger.info(
        "[AVISE-ME] %d email(s) enviado(s) para produto #%d (%s)",
        count,
        product_id,
        product_name,
    )
    return count
