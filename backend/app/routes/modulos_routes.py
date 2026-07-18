"""
Rotas para gerenciamento de módulos premium por tenant.

GET /modulos/status — retorna quais módulos estão ativos para o tenant logado.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import AssinaturaModulo, Tenant, User
from app.services.business_audit_service import (
    build_module_activation_metadata,
    build_plan_activation_metadata,
    log_business_event,
)
from app.tenancy.context import set_current_tenant

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

# Bling/webhooks seguem disponiveis apenas para tenants explicitamente
# configurados. Nao entram na vitrine publica nem no piloto Beta.
MODULOS_FORA_DA_OFERTA_PUBLICA = frozenset(["bling"])
MODULOS_BETA_PUBLICOS = frozenset(MODULOS_PREMIUM - MODULOS_FORA_DA_OFERTA_PUBLICA)
MODULOS_TRIAL_COMPLETO = frozenset(MODULOS_PREMIUM - MODULOS_FORA_DA_OFERTA_PUBLICA)

# Tenants criados antes da politica comercial ficavam com plan=free. Mantemos
# esse plano legado liberado para nao cortar fluxo real em uso.
PLANOS_LEGADO_LIBERADOS = frozenset(["free", "legacy", "legado"])
PLANOS_TODOS_MODULOS = frozenset(["premium", "enterprise", "full", "completo"])
PLANOS_BASICOS = frozenset(["basico", "básico", "base", "basic"])
TRIAL_DIAS_PADRAO = 30
ASSINATURA_STATUS_VALIDOS = frozenset(
    ["trial", "active", "expired", "blocked", "canceled"]
)


def _set_tenant_context_for_target(tenant_id: str) -> str:
    tenant_uuid = UUID(str(tenant_id))
    set_current_tenant(tenant_uuid)
    return str(tenant_uuid)


def _datetime_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_datetime(value: datetime | None) -> str | None:
    value = _datetime_utc(value)
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _dias_restantes_trial(
    trial_ends_at: datetime | None, agora: datetime
) -> int | None:
    trial_ends_at = _datetime_utc(trial_ends_at)
    if trial_ends_at is None:
        return None

    segundos = (trial_ends_at - agora).total_seconds()
    if segundos <= 0:
        return 0
    return int((segundos + 86399) // 86400)


def _assinatura_resumo_tenant(tenant: Tenant, agora: datetime) -> dict:
    status_raw = (getattr(tenant, "billing_status", None) or "active").strip().lower()
    if status_raw not in ASSINATURA_STATUS_VALIDOS:
        status_raw = "active"

    trial_ends_at = _datetime_utc(getattr(tenant, "trial_ends_at", None))
    status_efetivo = status_raw
    if status_raw == "trial" and trial_ends_at and trial_ends_at < agora:
        status_efetivo = "expired"

    return {
        "status": status_raw,
        "status_efetivo": status_efetivo,
        "origem": getattr(tenant, "subscription_source", None) or "manual",
        "trial_inicio": _iso_datetime(getattr(tenant, "trial_started_at", None)),
        "trial_fim": _iso_datetime(trial_ends_at),
        "dias_restantes_trial": _dias_restantes_trial(trial_ends_at, agora),
        "trial_expirado": status_efetivo == "expired",
        "acesso_completo_durante_trial": status_efetivo == "trial"
        and trial_ends_at is not None,
        "ativada_em": _iso_datetime(getattr(tenant, "subscription_activated_at", None)),
        "pagamento_integrado": False,
        "contratacao": {
            "modelo": "manual_assistida",
            "canal": "whatsapp",
            "acao_cliente": "falar_com_atendimento",
        },
    }


def _trial_completo_ativo(tenant: Tenant, agora: datetime) -> bool:
    return _assinatura_resumo_tenant(tenant, agora)["acesso_completo_durante_trial"]


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
    liberar_trial_completo: bool = False,
) -> list[str]:
    modulos_do_tenant = set(_normalizar_modulos_ativos(raw_modulos))
    plano_normalizado = (plano or "").strip().lower()

    for assinatura in assinaturas_ativas:
        # Respeita data_fim se definida
        if assinatura.data_fim and assinatura.data_fim < agora:
            continue
        modulos_do_tenant.add(assinatura.modulo)

    if (
        plano_normalizado in PLANOS_LEGADO_LIBERADOS
        or plano_normalizado in PLANOS_TODOS_MODULOS
    ):
        modulos_do_tenant.update(MODULOS_PREMIUM)

    if liberar_trial_completo:
        modulos_do_tenant.update(MODULOS_TRIAL_COMPLETO)

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado"
        )

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
        liberar_trial_completo=_trial_completo_ativo(tenant, agora),
    )

    return {
        "modulos_ativos": modulos_do_tenant,
        "plano": tenant.plan or "basico",
        "tenant_id": tenant_id,
        "modulos_controlados": sorted(MODULOS_PREMIUM),
        "modulos_beta": sorted(MODULOS_BETA_PUBLICOS),
        "modulos_fora_oferta_publica": sorted(MODULOS_FORA_DA_OFERTA_PUBLICA),
        "trial_padrao": {
            "plano": "experiencia_completa",
            "dias": TRIAL_DIAS_PADRAO,
            "escopo": "todos_modulos_corepet",
            "libera_premium_automaticamente": True,
            "integracoes_terceiras_exigem_configuracao": True,
        },
        "assinatura": _assinatura_resumo_tenant(tenant, agora),
        "plano_legado_liberado": (tenant.plan or "").strip().lower()
        in PLANOS_LEGADO_LIBERADOS,
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
    if not (
        current_user.is_superadmin or getattr(current_user, "is_system_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado"
        )

    if modulo not in MODULOS_PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Módulo '{modulo}' não existe. Disponíveis: {sorted(MODULOS_PREMIUM)}",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id_alvo).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado"
        )

    tenant_id_alvo = _set_tenant_context_for_target(str(tenant.id))

    # Atualiza campo JSON no tenant
    modulos_atuais: list[str] = []
    if tenant.modulos_ativos:
        try:
            modulos_atuais = json.loads(tenant.modulos_ativos)
        except (json.JSONDecodeError, TypeError):
            modulos_atuais = []

    modulos_anteriores = sorted(
        modulo_atual for modulo_atual in modulos_atuais if isinstance(modulo_atual, str)
    )
    if modulo not in modulos_atuais:
        modulos_atuais.append(modulo)
        tenant.modulos_ativos = json.dumps(modulos_atuais)

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
    assinatura_criada = False
    if not existente:
        assinatura = AssinaturaModulo(
            tenant_id=tenant_id_alvo,
            modulo=modulo,
            status="ativo",
            gateway="manual",
            data_inicio=datetime.now(tz=timezone.utc),
        )
        db.add(assinatura)
        assinatura_criada = True

    log_business_event(
        db=db,
        tenant_id=tenant_id_alvo,
        user_id=current_user.id,
        event="config.module_activated",
        entity_type="tenant_modules",
        entity_id=None,
        old_value={"modules": modulos_anteriores},
        metadata=build_module_activation_metadata(
            tenant=tenant,
            module=modulo,
            previous_modules=modulos_anteriores,
            current_modules=modulos_atuais,
            subscription_created=assinatura_criada,
        ),
        details=f"Modulo {modulo} ativado manualmente para tenant {tenant_id_alvo}",
        commit=False,
    )
    db.commit()

    return {"ok": True, "modulo": modulo, "tenant_id": tenant_id_alvo}


@router.post("/admin/plano-basico/ativar")
def ativar_plano_basico_manual(
    tenant_id_alvo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    Marca manualmente o Plano Basico como ativo apos confirmacao externa de pagamento.
    Este endpoint nao processa pagamento; ele apenas registra a ativacao operacional.
    """
    if not (
        current_user.is_superadmin or getattr(current_user, "is_system_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado"
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id_alvo).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant nao encontrado"
        )

    agora = datetime.now(tz=timezone.utc)
    previous_state = {
        "plan": tenant.plan,
        "billing_status": tenant.billing_status,
        "subscription_source": tenant.subscription_source,
        "subscription_activated_at": tenant.subscription_activated_at.isoformat()
        if tenant.subscription_activated_at
        else None,
        "trial_started_at": tenant.trial_started_at.isoformat()
        if tenant.trial_started_at
        else None,
        "trial_ends_at": tenant.trial_ends_at.isoformat()
        if tenant.trial_ends_at
        else None,
    }
    tenant.plan = "basico"
    tenant.billing_status = "active"
    tenant.subscription_source = "manual"
    tenant.subscription_activated_at = agora
    if not tenant.trial_started_at:
        tenant.trial_started_at = agora
    if not tenant.trial_ends_at:
        tenant.trial_ends_at = agora

    log_business_event(
        db=db,
        tenant_id=tenant_id_alvo,
        user_id=current_user.id,
        event="config.plan_activated",
        entity_type="tenants",
        entity_id=None,
        old_value=previous_state,
        metadata=build_plan_activation_metadata(
            tenant=tenant,
            previous_state=previous_state,
        ),
        details=f"Plano basico ativado manualmente para tenant {tenant_id_alvo}",
        commit=False,
    )
    db.commit()
    db.refresh(tenant)

    return {
        "ok": True,
        "tenant_id": tenant_id_alvo,
        "plano": tenant.plan,
        "assinatura": _assinatura_resumo_tenant(tenant, agora),
    }
