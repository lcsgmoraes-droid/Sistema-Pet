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
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import AssinaturaModulo, Tenant, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modulos", tags=["Módulos Premium"])

# Modulos controlados por plano/assinatura. O plano basico deixa aberto o
# nucleo operacional e libera estes extras apenas quando forem contratados.
MODULOS_PREMIUM = frozenset(
    [
        "app_mobile",
        "banho_tosa",
        "bling",
        "campanhas",
        "comissoes",
        "compras",
        "ecommerce",
        "entregas",
        "financeiro_erp",
        "fiscal",
        "ia_avancada",
        "integracoes",
        "marketplaces",
        "rh",
        "veterinario",
        "whatsapp",
    ]
)

# Tenants criados antes da politica comercial ficavam com plan=free. Mantemos
# esse plano legado liberado para nao cortar fluxo real em uso.
PLANOS_LEGADO_LIBERADOS = frozenset(["free", "legacy", "legado"])
PLANOS_TODOS_MODULOS = frozenset(["premium", "enterprise", "full", "completo"])
PLANOS_BASICOS = frozenset(["basico", "básico", "base", "basic"])


def _normalizar_modulos_ativos(raw_modulos: str | None) -> list[str]:
    if not raw_modulos:
        return []

    try:
        modulos = json.loads(raw_modulos)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(modulos, list):
        return []

    return [modulo for modulo in modulos if isinstance(modulo, str)]


def _raw_modulos_ativos_valido(raw_modulos: str | None) -> bool:
    if not raw_modulos:
        return True

    try:
        return isinstance(json.loads(raw_modulos), list)
    except (json.JSONDecodeError, TypeError):
        return False


def _resolver_modulos_ativos(
    raw_modulos: str | None,
    assinaturas_ativas: list[AssinaturaModulo],
    agora: datetime,
    plano: str | None = None,
) -> list[str]:
    modulos_do_tenant = set(_normalizar_modulos_ativos(raw_modulos))
    plano_normalizado = (plano or "").strip().lower()

    for assinatura in assinaturas_ativas:
        # Respeita data_fim se definida
        if assinatura.data_fim and assinatura.data_fim < agora:
            continue
        modulos_do_tenant.add(assinatura.modulo)

    if plano_normalizado in PLANOS_LEGADO_LIBERADOS or plano_normalizado in PLANOS_TODOS_MODULOS:
        modulos_do_tenant.update(MODULOS_PREMIUM)

    return sorted(modulo for modulo in modulos_do_tenant if modulo in MODULOS_PREMIUM)


@router.get("/status")
def get_modulos_status(
    user_and_tenant=Depends(get_current_user_and_tenant),
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
    _current_user, tenant_id = user_and_tenant
    tenant_id = str(tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    if not _raw_modulos_ativos_valido(tenant.modulos_ativos):
        logger.warning("modulos_ativos inválido para tenant %s", tenant_id)

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

    modulos_do_tenant = _resolver_modulos_ativos(
        tenant.modulos_ativos,
        assinaturas_ativas,
        agora,
        tenant.plan,
    )

    return {
        "modulos_ativos": modulos_do_tenant,
        "plano": tenant.plan or "basico",
        "tenant_id": tenant_id,
        "modulos_controlados": sorted(MODULOS_PREMIUM),
        "plano_legado_liberado": (tenant.plan or "").strip().lower() in PLANOS_LEGADO_LIBERADOS,
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
