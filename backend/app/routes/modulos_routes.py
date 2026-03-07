"""
Rotas para gerenciamento de módulos premium por tenant.

GET /modulos/status — retorna quais módulos estão ativos para o tenant logado.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.models import AssinaturaModulo, Tenant, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modulos", tags=["Módulos Premium"])

# Módulos que são premium (exigem assinatura)
MODULOS_PREMIUM = frozenset(["entregas", "campanhas", "whatsapp", "ecommerce", "app_mobile", "marketplaces"])


@router.get("/status")
def get_modulos_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    Retorna a lista de módulos premium ativos para o tenant do usuário logado.

    Resposta:
        {
            "modulos_ativos": ["entregas", "campanhas"],
            "plano": "base"
        }
    """
    tenant_id = str(current_user.tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    # Lê campo modulos_ativos do tenant (JSON salvo como Text)
    modulos_do_tenant: list[str] = []
    if tenant.modulos_ativos:
        try:
            modulos_do_tenant = json.loads(tenant.modulos_ativos)
        except (json.JSONDecodeError, TypeError):
            logger.warning("modulos_ativos inválido para tenant %s", tenant_id)
            modulos_do_tenant = []

    # Verifica também assinaturas ativas na tabela (mais confiável que o campo JSON)
    agora = datetime.now(tz=timezone.utc)
    assinaturas_ativas = (
        db.query(AssinaturaModulo)
        .filter(
            AssinaturaModulo.tenant_id == tenant_id,
            AssinaturaModulo.status == "ativo",
        )
        .all()
    )

    for assinatura in assinaturas_ativas:
        # Respeita data_fim se definida
        if assinatura.data_fim and assinatura.data_fim < agora:
            continue
        if assinatura.modulo not in modulos_do_tenant:
            modulos_do_tenant.append(assinatura.modulo)

    return {
        "modulos_ativos": modulos_do_tenant,
        "plano": tenant.plan or "base",
        "tenant_id": tenant_id,
    }


@router.post("/admin/ativar")
def ativar_modulo(
    modulo: str,
    tenant_id_alvo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    Ativa um módulo premium para um tenant (uso administrativo).
    Apenas admins do sistema podem chamar este endpoint.
    """
    # Apenas superadmin pode ativar módulos manualmente
    if not (current_user.is_superadmin or getattr(current_user, "is_system_admin", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    if modulo not in MODULOS_PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Módulo '{modulo}' não existe. Disponíveis: {sorted(MODULOS_PREMIUM)}",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id_alvo).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    # Atualiza campo JSON no tenant
    modulos_atuais: list[str] = []
    if tenant.modulos_ativos:
        try:
            modulos_atuais = json.loads(tenant.modulos_ativos)
        except (json.JSONDecodeError, TypeError):
            modulos_atuais = []

    if modulo not in modulos_atuais:
        modulos_atuais.append(modulo)
        tenant.modulos_ativos = json.dumps(modulos_atuais)
        db.commit()

    # Cria registro de assinatura manual
    existente = (
        db.query(AssinaturaModulo)
        .filter(
            AssinaturaModulo.tenant_id == tenant_id_alvo,
            AssinaturaModulo.modulo == modulo,
            AssinaturaModulo.status == "ativo",
        )
        .first()
    )
    if not existente:
        assinatura = AssinaturaModulo(
            tenant_id=tenant_id_alvo,
            modulo=modulo,
            status="ativo",
            gateway="manual",
            data_inicio=datetime.now(tz=timezone.utc),
        )
        db.add(assinatura)
        db.commit()

    return {"ok": True, "modulo": modulo, "tenant_id": tenant_id_alvo}
