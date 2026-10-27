"""Manutencao de lojas no OPS: quem e a loja, em que grupo esta e quais modulos tem.

Tela "Lojas e modulos" (separada da aba Tenants, que e voltada a cobranca).
Ligar/desligar um modulo aqui mexe no que a plataforma controla manualmente:
- ligar: ativacao manual (mesma regra de `POST /modulos/admin/ativar`);
- desligar: remove a ativacao manual e cancela as assinaturas de modulo ativas.
Modulo que vem do plano, do teste gratis (trial) ou do plano legado nao se
desliga por aqui: a resposta informa de onde ele vem.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Text, or_
from sqlalchemy.orm import Session

from app.models import AssinaturaModulo, Tenant
from app.routes.modulos_routes import (
    MODULOS_PREMIUM,
    _assinatura_resumo_tenant,
    _normalizar_modulos_ativos,
    _planos_segmento_tenant,
    _resolver_modulos_ativos,
    _trial_completo_ativo,
)
from app.services.business_audit_service import log_business_event
from app.services.modulo_activation_service import ativar_modulo_manual
from app.services.ops_tenant_log_service import (
    CATEGORIA_MODULO,
    registrar_alteracoes,
)
from app.services.ops_tenants_read_service import _grupo_comercial_info, _principal_user
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant

LIMITE_DE_LOJAS = 200

# Nome e descricao de cada modulo para as telas administrativas (todo modulo de
# MODULOS_PREMIUM precisa estar aqui; ha um teste que confere).
CATALOGO_DE_MODULOS: dict[str, tuple[str, str]] = {
    "app_mobile": (
        "App para clientes",
        "App mobile próprio para os clientes da loja comprarem e acompanharem pedidos.",
    ),
    "banho_tosa": (
        "Banho e tosa",
        "Agenda, fila do dia, serviços, pacotes, retornos e taxi dog.",
    ),
    "bling": (
        "Integração Bling",
        "Sincronização de pedidos, produtos, estoque e notas via Bling.",
    ),
    "campanhas": (
        "Campanhas",
        "Campanhas de marketing, promoções, cashback e fidelidade.",
    ),
    "comissoes": (
        "Comissões",
        "Regras, demonstrativos, provisões e fechamento de comissões.",
    ),
    "compras": (
        "Compras e entrada XML",
        "Pedidos de compra, entrada por XML e conferências de estoque.",
    ),
    "ecommerce": ("E-commerce", "Loja virtual integrada ao sistema."),
    "entregas": ("Entregas", "Rotas, rastreamento e app do entregador."),
    "financeiro_erp": (
        "Financeiro ERP",
        "Contas a pagar e receber, fluxo de caixa, DRE e conciliações.",
    ),
    "fiscal": ("Fiscal / NF", "Emissão e acompanhamento de notas fiscais."),
    "ia_avancada": (
        "IA avançada",
        "Previsões financeiras e assistentes especializados.",
    ),
    "integracoes": (
        "Integrações",
        "Conectores externos para automações, canais e plataformas.",
    ),
    "marketplaces": (
        "Marketplaces",
        "Venda em Mercado Livre, Shopee, Amazon e outros.",
    ),
    "rh": ("Recursos humanos", "Funcionários, cargos e departamentos."),
    "veterinario": (
        "Veterinário",
        "Agenda, consultas, prontuário, vacinas, exames e internações.",
    ),
    "whatsapp": ("WhatsApp", "Atendimento por WhatsApp com inteligência artificial."),
}


def catalogo_de_modulos() -> list[dict[str, str]]:
    return [
        {
            "codigo": codigo,
            "nome": CATALOGO_DE_MODULOS.get(codigo, (codigo, ""))[0],
            "descricao": CATALOGO_DE_MODULOS.get(codigo, (codigo, ""))[1],
        }
        for codigo in sorted(MODULOS_PREMIUM)
    ]


ORIGEM_MANUAL = "manual"
ORIGEM_ASSINATURA = "assinatura"
ORIGEM_PLANO = "plano"
ORIGEM_TRIAL = "trial"


class OpsLojaError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.status_code = status_code
        super().__init__(message)


def _agora() -> datetime:
    return datetime.now(tz=UTC)


def _assinaturas_ativas(db: Session, tenant_id: UUID) -> list[AssinaturaModulo]:
    return (
        db.query(AssinaturaModulo)
        .filter(
            AssinaturaModulo.tenant_id == tenant_id,
            AssinaturaModulo.status == "ativo",
        )
        .all()
    )


def _origens_por_modulo(
    tenant: Tenant, assinaturas: list[AssinaturaModulo], agora: datetime
) -> dict[str, list[str]]:
    """De onde vem cada modulo: ativacao manual, assinatura, plano ou teste gratis."""
    planos = _planos_segmento_tenant(tenant)
    fontes = {
        ORIGEM_MANUAL: set(_normalizar_modulos_ativos(tenant.modulos_ativos)),
        ORIGEM_ASSINATURA: set(_resolver_modulos_ativos(None, assinaturas, agora, ())),
        ORIGEM_PLANO: set(_resolver_modulos_ativos(None, [], agora, planos)),
        ORIGEM_TRIAL: set(
            _resolver_modulos_ativos(
                None,
                [],
                agora,
                (),
                liberar_trial_completo=_trial_completo_ativo(tenant, agora),
            )
        ),
    }
    origens: dict[str, list[str]] = {modulo: [] for modulo in MODULOS_PREMIUM}
    for origem, modulos in fontes.items():
        for modulo in modulos & MODULOS_PREMIUM:
            origens[modulo].append(origem)
    return origens


def _modulos_da_loja(db: Session, tenant: Tenant) -> dict[str, Any]:
    agora = _agora()
    tenant_id = UUID(str(tenant.id))
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        assinaturas = _assinaturas_ativas(db, tenant_id)
    resumo = _assinatura_resumo_tenant(tenant, agora)
    efetivos = set(
        _resolver_modulos_ativos(
            tenant.modulos_ativos,
            assinaturas,
            agora,
            _planos_segmento_tenant(tenant),
            liberar_trial_completo=_trial_completo_ativo(tenant, agora),
            acesso_liberado=resumo["acesso_operacional_ativo"],
        )
    )
    origens = _origens_por_modulo(tenant, assinaturas, agora)
    return {
        "acesso_bloqueado_por_cobranca": not resumo["acesso_operacional_ativo"],
        "modulos": [
            {
                "codigo": modulo,
                "ativo": modulo in efetivos,
                "origens": origens[modulo],
            }
            for modulo in sorted(MODULOS_PREMIUM)
        ],
    }


def listar_lojas(db: Session, search: str | None = None) -> dict[str, Any]:
    consulta = db.query(Tenant)
    termo = (search or "").strip()
    if termo:
        consulta = consulta.filter(
            or_(
                Tenant.name.ilike(f"%{termo}%"),
                Tenant.id.cast(Text).ilike(f"%{termo}%"),
            )
        )
    lojas = consulta.order_by(Tenant.name).limit(LIMITE_DE_LOJAS + 1).all()
    cortou = len(lojas) > LIMITE_DE_LOJAS
    from app.services.ops_lojas_detalhe_service import resumo_de_usuarios_por_loja

    usuarios = resumo_de_usuarios_por_loja(db)
    itens = []
    for tenant in lojas[:LIMITE_DE_LOJAS]:
        tenant_id = str(tenant.id)
        estado = _modulos_da_loja(db, tenant)
        itens.append(
            {
                "id": tenant_id,
                "nome": tenant.name,
                "status": tenant.status,
                "plano": getattr(tenant, "plan", None),
                "situacao_da_cobranca": getattr(tenant, "billing_status", None),
                "grupo": _grupo_comercial_info(db, tenant_id),
                "principal": _principal_user(db, tenant_id),
                "usuarios": usuarios.get(
                    tenant_id, {"total": 0, "ativos": 0, "ultimo_acesso": None}
                ),
                "total_de_modulos_ativos": sum(
                    1 for m in estado["modulos"] if m["ativo"]
                ),
                **estado,
            }
        )
    return {
        "items": itens,
        "limite": LIMITE_DE_LOJAS,
        "cortou": cortou,
        "catalogo_de_modulos": catalogo_de_modulos(),
    }


def _tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise OpsLojaError("Loja não encontrada", 404)
    return tenant


def alterar_modulo(
    db: Session,
    *,
    tenant_id: str,
    modulo: str,
    ativar: bool,
    admin: Any,
) -> dict[str, Any]:
    """Liga ou desliga um modulo da loja e devolve o estado novo dos modulos."""
    if modulo not in MODULOS_PREMIUM:
        raise OpsLojaError(f"Módulo desconhecido: {modulo}", 400)
    tenant = _tenant(db, tenant_id)
    tenant_uuid = UUID(str(tenant.id))
    admin_email = getattr(admin, "email", "desconhecido")
    estavam_ativos = {
        m["codigo"]: m["ativo"] for m in _modulos_da_loja(db, tenant)["modulos"]
    }

    with tenant_context(tenant_uuid):
        sync_rls_tenant(db, tenant_uuid)
        antes = sorted(_normalizar_modulos_ativos(tenant.modulos_ativos))
        if ativar:
            ativar_modulo_manual(
                db,
                tenant=tenant,
                modulo=modulo,
                modulos_premium=MODULOS_PREMIUM,
                ativado_por_user_id=None,
                commit=False,
            )
        else:
            atuais = [m for m in antes if m != modulo]
            tenant.modulos_ativos = json.dumps(atuais)
            for assinatura in _assinaturas_ativas(db, tenant_uuid):
                if assinatura.modulo == modulo:
                    assinatura.status = "cancelado"
                    assinatura.data_fim = _agora()
        log_business_event(
            db=db,
            tenant_id=str(tenant.id),
            user_id=None,
            event=(
                "config.module_activated" if ativar else "config.module_deactivated"
            ),
            entity_type="tenant_modules",
            entity_id=None,
            old_value={"modules": antes},
            metadata={"module": modulo, "by_platform_admin": admin_email},
            details=(
                f"Modulo {modulo} {'ativado' if ativar else 'desativado'} no OPS "
                f"por {admin_email}"
            ),
            commit=False,
        )
        db.flush()

    estado = _modulos_da_loja(db, tenant)
    item = next(m for m in estado["modulos"] if m["codigo"] == modulo)
    registrar_alteracoes(
        db,
        tenant_id=str(tenant.id),
        admin=admin,
        categoria=CATEGORIA_MODULO,
        antes={modulo: "ativo" if estavam_ativos[modulo] else "inativo"},
        depois={modulo: "ativo" if item["ativo"] else "inativo"},
    )
    return {
        "modulo": modulo,
        "ativo": item["ativo"],
        "origens": item["origens"],
        # Desligou mas ele continua ativo: vem do plano ou do teste gratis.
        "continua_ativo": (not ativar) and item["ativo"],
        **estado,
    }
