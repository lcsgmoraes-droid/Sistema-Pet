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
from app.services.billing_access import overdue_grace_state
from app.services.modulo_activation_service import (
    ModuloActivationError,
    ativar_modulo_manual,
)
from app.services.plan_catalog import PLAN_CATALOG, get_plan, segment_plan_field
from app.services.plan_limits import active_session_usage, monthly_sales_usage
from app.tenancy.context import set_current_tenant
from app.utils.timezone import BRASILIA_TZ

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

# Bling/webhooks e emissao fiscal seguem disponiveis apenas para tenants
# explicitamente configurados. Nao entram na vitrine publica nem no piloto Beta.
MODULOS_FORA_DA_OFERTA_PUBLICA = frozenset(["bling", "fiscal"])
MODULOS_CONTRATACAO_SEPARADA = frozenset(["fiscal"])
MODULOS_BETA_PUBLICOS = frozenset(MODULOS_PREMIUM - MODULOS_FORA_DA_OFERTA_PUBLICA)
MODULOS_TRIAL_COMPLETO = frozenset(MODULOS_PREMIUM - MODULOS_FORA_DA_OFERTA_PUBLICA)

# Tenants criados antes da politica comercial ficavam com plan=free. Mantemos
# esse plano legado liberado para nao cortar fluxo real em uso.
PLANOS_LEGADO_LIBERADOS = frozenset(["free", "legacy", "legado"])
PLANOS_TODOS_MODULOS = frozenset(["premium", "enterprise", "full", "completo"])
PLANOS_BASICOS = frozenset(["basico", "básico", "base", "basic"])
TRIAL_DIAS_PADRAO = 30
ASSINATURA_STATUS_VALIDOS = frozenset(
    [
        "trial",
        "pending",
        "active",
        "past_due",
        "expired",
        "blocked",
        "refunded",
        "canceled",
    ]
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
    trial_completo_ativo = trial_ends_at is not None and trial_ends_at > agora
    status_efetivo = status_raw
    if status_raw == "trial" and trial_ends_at and trial_ends_at < agora:
        status_efetivo = "expired"

    data_brasilia = (
        agora.astimezone(BRASILIA_TZ).date()
        if agora.tzinfo is not None
        else agora.date()
    )
    tolerancia = overdue_grace_state(tenant, data_brasilia)
    acesso_operacional_ativo = (
        status_efetivo in {"active", "trial"} or tolerancia["access_allowed"]
    )

    origem = getattr(tenant, "subscription_source", None) or "manual"
    pagamento_integrado = bool(
        getattr(tenant, "billing_provider_subscription_id", None)
        or getattr(tenant, "billing_provider_payment_id", None)
    )

    return {
        "status": status_raw,
        "status_efetivo": status_efetivo,
        "acesso_operacional_ativo": acesso_operacional_ativo,
        "tolerancia_atraso": {
            "em_vigor": tolerancia["in_grace"],
            "dias_restantes": tolerancia["days_until_block"],
            "bloqueio_em": tolerancia["block_on"],
        },
        "origem": origem,
        "trial_inicio": _iso_datetime(getattr(tenant, "trial_started_at", None)),
        "trial_fim": _iso_datetime(trial_ends_at),
        "dias_restantes_trial": _dias_restantes_trial(trial_ends_at, agora),
        "trial_expirado": status_efetivo == "expired",
        # Os 30 dias completos continuam mesmo se o cliente pagar antes do fim.
        "acesso_completo_durante_trial": trial_completo_ativo,
        "ativada_em": _iso_datetime(getattr(tenant, "subscription_activated_at", None)),
        "pagamento_integrado": pagamento_integrado,
        "pagamento": {
            "provedor": "asaas"
            if getattr(tenant, "subscription_source", None) == "asaas"
            else None,
            "status": getattr(tenant, "billing_payment_status", None),
            "tipo": getattr(tenant, "billing_type", None),
            "proximo_vencimento": (
                tenant.billing_next_due_date.isoformat()
                if getattr(tenant, "billing_next_due_date", None)
                else None
            ),
            "checkout_url": getattr(tenant, "billing_checkout_url", None),
        },
        "contratacao": {
            "modelo": "pagamento_integrado"
            if pagamento_integrado
            else "manual_assistida",
            "canal": "asaas" if origem == "asaas" else "equipe_corepet",
            "acao_cliente": "abrir_checkout"
            if pagamento_integrado
            else "solicitar_ativacao",
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
    planos: tuple[str | None, ...] = (),
    liberar_trial_completo: bool = False,
    acesso_liberado: bool = True,
) -> list[str]:
    """Une as 3 fontes de modulo liberado (manual, AssinaturaModulo, planos de
    segmento). Quando `acesso_liberado` e False (cobranca com problema), nenhuma
    das 3 fontes libera nada — so o trial completo (ortogonal a billing) segue
    valendo. `planos` e a lista dos ate-3 codigos de segmento do tenant
    (plan_pet/plan_vet/plan_grooming), filtrando os vazios.
    """
    modulos_do_tenant: set[str] = set()

    if acesso_liberado:
        modulos_do_tenant |= set(_normalizar_modulos_ativos(raw_modulos))

        for assinatura in assinaturas_ativas:
            # Respeita data_fim se definida
            if assinatura.data_fim and assinatura.data_fim < agora:
                continue
            modulos_do_tenant.add(assinatura.modulo)

        for plano in planos:
            plano_normalizado = (plano or "").strip().lower()
            if not plano_normalizado:
                continue
            if (
                plano_normalizado in PLANOS_LEGADO_LIBERADOS
                or plano_normalizado in PLANOS_TODOS_MODULOS
            ):
                modulos_do_tenant.update(MODULOS_PREMIUM - MODULOS_CONTRATACAO_SEPARADA)

            plano_catalogo = get_plan(plano)
            if plano_catalogo:
                modulos_do_tenant.update(plano_catalogo.modules)

    if liberar_trial_completo:
        modulos_do_tenant.update(MODULOS_TRIAL_COMPLETO)

    return sorted(modulo for modulo in modulos_do_tenant if modulo in MODULOS_PREMIUM)


def _planos_segmento_tenant(tenant: Tenant) -> tuple[str, ...]:
    """Ate-3 codigos de plano de segmento do tenant (plan_pet/plan_vet/
    plan_grooming), filtrando os vazios. Fallback para o `plan` legado quando
    nenhum dos 3 campos novos esta preenchido (tenants ainda nao migrados)."""
    segmentos = tuple(
        codigo
        for codigo in (
            getattr(tenant, "plan_pet", None),
            getattr(tenant, "plan_vet", None),
            getattr(tenant, "plan_grooming", None),
        )
        if codigo
    )
    if segmentos:
        return segmentos
    plano_legado = getattr(tenant, "plan", None)
    return (plano_legado,) if plano_legado else ()


def _planos_catalogo_segmento(tenant: Tenant) -> list:
    return [
        plano_catalogo
        for codigo in _planos_segmento_tenant(tenant)
        if (plano_catalogo := get_plan(codigo))
    ]


def _atribuir_plano_segmento(tenant: Tenant, plano_catalogo) -> None:
    """Grava o codigo do plano no campo do segmento correspondente
    (plan_pet/plan_vet/plan_grooming), alem do `plan` legado (mantido em
    paralelo nesta fase)."""
    campo = segment_plan_field(plano_catalogo)
    if campo:
        setattr(tenant, campo, plano_catalogo.code)


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

    assinatura_resumo = _assinatura_resumo_tenant(tenant, agora)
    # acesso_operacional_ativo ja incorpora a tolerancia de 15 dias pra
    # cobranca em atraso (ver billing_access.overdue_grace_state) — e esse,
    # nao o status_efetivo cru, que deve gatear as 3 fontes de modulo.
    acesso_liberado = assinatura_resumo["acesso_operacional_ativo"]
    planos_segmento = _planos_segmento_tenant(tenant)

    modulos_do_tenant = _resolver_modulos_ativos(
        tenant.modulos_ativos,
        assinaturas_ativas,
        agora,
        planos_segmento,
        liberar_trial_completo=_trial_completo_ativo(tenant, agora),
        acesso_liberado=acesso_liberado,
    )

    planos_catalogo = _planos_catalogo_segmento(tenant)
    plano_catalogo = planos_catalogo[0] if planos_catalogo else None
    trial_completo = assinatura_resumo["acesso_completo_durante_trial"]
    plano_ativo = acesso_liberado
    recursos_trial = sorted(
        {recurso for plano in PLAN_CATALOG.values() for recurso in plano.entitlements}
    )
    recursos_ativos = (
        recursos_trial
        if trial_completo
        else sorted({recurso for plano in planos_catalogo for recurso in plano.entitlements})
        if planos_catalogo and plano_ativo
        else []
    )

    # Planos legados nao possuem limites comerciais no catalogo publico.
    plano_publico_canonico = any(
        codigo.strip().lower() in PLAN_CATALOG for codigo in planos_segmento
    )
    uso_vendas = monthly_sales_usage(db, tenant_id) if plano_publico_canonico else 0
    uso_sessoes = active_session_usage(db, tenant_id) if plano_publico_canonico else 0
    # Combinacao "mais generosa" entre os planos de segmento simultaneos: se
    # algum plano ativo nao define limite (ilimitado), o combinado fica
    # ilimitado; senao, usa o maior limite numerico entre os planos presentes.
    limites_vendas = [plano.monthly_sales_limit for plano in planos_catalogo]
    limites_sessoes = [plano.simultaneous_sessions_limit for plano in planos_catalogo]
    limites_apos_trial = {
        "vendas_mensais": (
            None
            if not limites_vendas or any(limite is None for limite in limites_vendas)
            else max(limites_vendas)
        ),
        "acessos_simultaneos": (
            None
            if not limites_sessoes or any(limite is None for limite in limites_sessoes)
            else max(limites_sessoes)
        ),
    }
    limites_aplicados = (
        {"vendas_mensais": None, "acessos_simultaneos": None}
        if trial_completo
        else limites_apos_trial
    )

    return {
        "modulos_ativos": modulos_do_tenant,
        "plano": tenant.plan or "basico",
        "plano_pet": tenant.plan_pet,
        "plano_vet": tenant.plan_vet,
        "plano_grooming": tenant.plan_grooming,
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
        "assinatura": assinatura_resumo,
        "plano_catalogo": plano_catalogo.to_public_dict() if plano_catalogo else None,
        "planos_catalogo": [plano.to_public_dict() for plano in planos_catalogo],
        "recursos_ativos": recursos_ativos,
        "limites": {
            "aplicados": limites_aplicados,
            "apos_trial": limites_apos_trial,
        },
        "uso": {
            "vendas_no_mes": uso_vendas,
            "acessos_simultaneos": uso_sessoes,
        },
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

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id_alvo).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado"
        )

    _set_tenant_context_for_target(str(tenant.id))

    try:
        return ativar_modulo_manual(
            db,
            tenant=tenant,
            modulo=modulo,
            modulos_premium=MODULOS_PREMIUM,
            ativado_por_user_id=current_user.id,
        )
    except ModuloActivationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/admin/plano/ativar")
def ativar_plano_manual(
    tenant_id_alvo: str,
    plano: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    Ativa manualmente qualquer plano publico apos confirmacao externa de pagamento.
    Este endpoint nao processa pagamento; ele apenas registra a ativacao operacional.
    """
    if not (
        current_user.is_superadmin or getattr(current_user, "is_system_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado"
        )

    plano_catalogo = get_plan(plano)
    if plano_catalogo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plano publico invalido",
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
    tenant.plan = plano_catalogo.code
    _atribuir_plano_segmento(tenant, plano_catalogo)
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
        details=(
            f"Plano {plano_catalogo.code} ativado manualmente para tenant "
            f"{tenant_id_alvo}"
        ),
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


@router.post("/admin/plano-basico/ativar")
def ativar_plano_basico_manual(
    tenant_id_alvo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Compatibilidade para a antiga ativacao manual do Plano Basico."""
    return ativar_plano_manual(
        tenant_id_alvo=tenant_id_alvo,
        plano="pet-basico",
        current_user=current_user,
        db=db,
    )
