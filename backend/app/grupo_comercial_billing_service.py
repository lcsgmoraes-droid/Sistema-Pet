"""Visao consolidada de cobranca (Asaas) das lojas de um grupo comercial.

Cada loja continua sendo cobrada de forma 100% independente (ver
Documentacao/Dominio/EmpresaGrupo.md, secao "Relacao com licenciamento") -
este modulo so agrega, para leitura, o status ja calculado por
``asaas_billing_service.subscription_status`` de cada loja do grupo. Nao
existe nenhuma nocao de "assinatura de grupo".
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.grupo_comercial_service import GrupoComercialService
from app.models import Tenant, User
from app.services.asaas_billing_service import (
    AsaasBillingError,
    refresh_subscription_payment,
    subscription_status,
)


ADIMPLENTE_STATUSES = {"active"}


class GrupoComercialBillingService:
    def __init__(self, db: Session):
        self.db = db
        self.grupos = GrupoComercialService(db)

    def _exigir_acesso(self, grupo_id: int, usuario: User) -> GrupoComercial:
        grupo = self.db.query(GrupoComercial).filter(GrupoComercial.id == grupo_id).first()
        if grupo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo Comercial não encontrado.",
            )
        self.grupos.exigir_acesso_gestao(grupo_id, usuario)
        return grupo

    def _resumo_loja(self, tenant: Tenant) -> dict:
        resultado = subscription_status(tenant)
        adimplente = resultado["billing_status"] in ADIMPLENTE_STATUSES
        return {
            "tenant_id": str(tenant.id),
            "nome": tenant.name,
            "billing_status": resultado["billing_status"],
            "payment_status": resultado["payment_status"],
            "billing_type": resultado["billing_type"],
            "next_due_date": resultado["next_due_date"],
            "checkout_url": resultado["checkout_url"],
            "adimplente": adimplente,
        }

    def listar(self, grupo_id: int, usuario: User) -> dict:
        self._exigir_acesso(grupo_id, usuario)
        tenants = (
            self.db.query(Tenant)
            .join(GrupoComercialMembro, GrupoComercialMembro.empresa_id == Tenant.id)
            .filter(
                GrupoComercialMembro.grupo_id == grupo_id,
                GrupoComercialMembro.status == "ativo",
            )
            .order_by(Tenant.name.asc())
            .all()
        )
        return {"lojas": [self._resumo_loja(tenant) for tenant in tenants]}

    def sincronizar_loja(self, grupo_id: int, tenant_id: str, usuario: User) -> dict:
        self._exigir_acesso(grupo_id, usuario)
        membro = (
            self.db.query(GrupoComercialMembro)
            .filter(
                GrupoComercialMembro.grupo_id == grupo_id,
                GrupoComercialMembro.empresa_id == str(tenant_id),
                GrupoComercialMembro.status == "ativo",
            )
            .first()
        )
        if membro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Esta loja não participa deste grupo.",
            )
        tenant = self.db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Loja não encontrada."
            )
        try:
            refresh_subscription_payment(self.db, tenant=tenant)
        except AsaasBillingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        return self._resumo_loja(tenant)
