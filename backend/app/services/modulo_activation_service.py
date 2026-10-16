"""Ativação manual de módulo premium por tenant.

Extraído de ``POST /modulos/admin/ativar`` (``app/routes/modulos_routes.py``)
para ser reaproveitado também pelo onboarding assistido de ops, que precisa
ativar módulo extra (ex.: banho_tosa além de um plano vet-*) para uma loja
recém-provisionada, na mesma transação atômica do lote — daí o parâmetro
``commit``, ausente na rota original (que sempre fecha a própria transação).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AssinaturaModulo, Tenant
from app.services.business_audit_service import (
    build_module_activation_metadata,
    log_business_event,
)


class ModuloActivationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def ativar_modulo_manual(
    db: Session,
    *,
    tenant: Tenant,
    modulo: str,
    modulos_premium: frozenset[str],
    ativado_por_user_id: int | None,
    commit: bool = True,
) -> dict:
    """Ativa ``modulo`` para ``tenant`` (gateway ``"manual"``): atualiza
    ``Tenant.modulos_ativos`` (JSON) e cria um ``AssinaturaModulo`` se ainda
    não houver um ativo. Pressupõe que o tenant context já está setado para
    ``tenant.id`` — quem chama é responsável por isso (``AssinaturaModulo`` é
    tenant-scoped).
    """
    if modulo not in modulos_premium:
        raise ModuloActivationError(
            400, f"Módulo '{modulo}' não existe. Disponíveis: {sorted(modulos_premium)}"
        )

    tenant_id = str(tenant.id)
    tenant_uuid = UUID(tenant_id)

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

    existente = (
        db.query(AssinaturaModulo)
        .filter(
            AssinaturaModulo.tenant_id == tenant_uuid,
            AssinaturaModulo.modulo == modulo,
            AssinaturaModulo.status == "ativo",
        )
        .first()
    )
    assinatura_criada = False
    if not existente:
        assinatura = AssinaturaModulo(
            tenant_id=tenant_uuid,
            modulo=modulo,
            status="ativo",
            gateway="manual",
            data_inicio=datetime.now(tz=timezone.utc),
        )
        db.add(assinatura)
        assinatura_criada = True

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=ativado_por_user_id,
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
        details=f"Modulo {modulo} ativado manualmente para tenant {tenant_id}",
        commit=False,
    )
    if commit:
        db.commit()

    return {"ok": True, "modulo": modulo, "tenant_id": tenant_id}
