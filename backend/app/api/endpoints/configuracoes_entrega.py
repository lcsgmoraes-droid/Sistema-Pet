"""
Endpoints para ConfiguracaoEntrega
Sprint 1 BLOCO 3 - Configuração Global de Entregas
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import ConfiguracaoEntrega, Tenant
from app.schemas.configuracao_entrega import (
    ConfiguracaoEntregaResponse,
    ConfiguracaoEntregaUpdate,
)

router = APIRouter(prefix="/configuracoes/entregas", tags=["Configurações - Entregas"])


def ensure_configuracoes_entrega_schema(db: Session) -> None:
    """Compatibilidade de schema em ambiente legado (sem migrations completas)."""
    db.execute(
        text(
            "ALTER TABLE configuracoes_entrega ADD COLUMN IF NOT EXISTS user_id INTEGER"
        )
    )
    db.execute(
        text(
            "ALTER TABLE configuracoes_entrega ADD COLUMN IF NOT EXISTS metodo_km_entrega VARCHAR(20) DEFAULT 'auto_rota'"
        )
    )
    delivery_columns = (
        "entrega_ativa BOOLEAN NOT NULL DEFAULT true",
        "retirada_ativa BOOLEAN NOT NULL DEFAULT true",
        "modalidade_cobranca VARCHAR(20) NOT NULL DEFAULT 'fixa'",
        "taxa_fixa NUMERIC(10, 2) NOT NULL DEFAULT 0",
        "valor_por_km_cobrado NUMERIC(10, 2)",
        "taxa_minima NUMERIC(10, 2) NOT NULL DEFAULT 0",
        "faixas_distancia JSONB NOT NULL DEFAULT '[]'::jsonb",
        "valor_km_excedente NUMERIC(10, 2)",
        "distancia_maxima_entrega_km NUMERIC(10, 2)",
        "frete_gratis_acima NUMERIC(10, 2)",
        "distancia_maxima_frete_gratis_km NUMERIC(10, 2)",
        "pedido_minimo NUMERIC(10, 2) NOT NULL DEFAULT 0",
        "prazo_entrega_texto VARCHAR(120)",
    )
    for column_definition in delivery_columns:
        db.execute(
            text(
                "ALTER TABLE configuracoes_entrega ADD COLUMN IF NOT EXISTS "
                + column_definition
            )
        )
    db.execute(text("""
        UPDATE configuracoes_entrega ce
        SET user_id = u.id
        FROM (
            SELECT DISTINCT ON (tenant_id) id, tenant_id
            FROM users
            ORDER BY tenant_id, id
        ) u
        WHERE ce.tenant_id = u.tenant_id
          AND ce.user_id IS NULL
    """))
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_configuracoes_entrega_user_id "
            "ON configuracoes_entrega (user_id)"
        )
    )
    db.commit()


def _legacy_delivery_defaults(tenant: Tenant) -> dict:
    return {
        "entrega_ativa": bool(getattr(tenant, "ecommerce_entrega_ativa", True)),
        "retirada_ativa": bool(getattr(tenant, "ecommerce_retirada_ativa", True)),
        "modalidade_cobranca": "fixa",
        "taxa_fixa": float(getattr(tenant, "ecommerce_taxa_entrega", 0) or 0),
        "frete_gratis_acima": getattr(tenant, "ecommerce_frete_gratis_acima", None),
        "pedido_minimo": float(getattr(tenant, "ecommerce_pedido_minimo", 0) or 0),
        "prazo_entrega_texto": getattr(tenant, "ecommerce_prazo_entrega_texto", None),
    }


def _sync_tenant_delivery_mirror(tenant: Tenant, config: ConfiguracaoEntrega) -> None:
    """Mantem os campos publicos legados alinhados durante a transicao."""

    tenant.ecommerce_entrega_ativa = bool(config.entrega_ativa)
    tenant.ecommerce_retirada_ativa = bool(config.retirada_ativa)
    tenant.ecommerce_taxa_entrega = (
        float(config.taxa_fixa or 0) if config.modalidade_cobranca == "fixa" else 0
    )
    tenant.ecommerce_frete_gratis_acima = (
        float(config.frete_gratis_acima)
        if config.frete_gratis_acima is not None
        else None
    )
    tenant.ecommerce_pedido_minimo = float(config.pedido_minimo or 0)
    tenant.ecommerce_prazo_entrega_texto = config.prazo_entrega_texto


@router.get("", response_model=ConfiguracaoEntregaResponse)
def get_configuracao_entrega(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna a configuração de entrega do tenant atual.
    Cria automaticamente se não existir.

    ✅ Multi-tenant: usa tenant_id do contexto
    ✅ Idempotente: cria se não existir
    """
    current_user, tenant_id = user_and_tenant
    ensure_configuracoes_entrega_schema(db)

    # Verifica se tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Busca ou cria configuração
    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config:
        # Buscar entregador padrão automaticamente
        from app.models import Cliente

        entregador_padrao = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.entregador_padrao.is_(True),
                Cliente.entregador_ativo.is_(True),
                Cliente.ativo.is_(True),
            )
            .first()
        )

        # Cria configuração padrão com entregador padrão se existir
        config = ConfiguracaoEntrega(
            tenant_id=tenant_id,
            user_id=current_user.id,
            entregador_padrao_id=entregador_padrao.id if entregador_padrao else None,
            logradouro=None,
            cep=None,
            numero=None,
            complemento=None,
            bairro=None,
            cidade=None,
            estado=None,
            **_legacy_delivery_defaults(tenant),
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    elif config.entregador_padrao_id is None or config.user_id is None:
        # Se já existe mas não tem entregador padrão definido, buscar automaticamente
        from app.models import Cliente

        entregador_padrao = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.entregador_padrao.is_(True),
                Cliente.entregador_ativo.is_(True),
                Cliente.ativo.is_(True),
            )
            .first()
        )

        updated = False
        if entregador_padrao:
            config.entregador_padrao_id = entregador_padrao.id
            updated = True
        if config.user_id is None:
            config.user_id = current_user.id
            updated = True
        if updated:
            db.commit()
            db.refresh(config)

    return config


@router.put("", response_model=ConfiguracaoEntregaResponse)
def update_configuracao_entrega(
    payload: ConfiguracaoEntregaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza a configuração de entrega do tenant atual.

    ✅ Multi-tenant: usa tenant_id do contexto
    ✅ Idempotente: cria se não existir
    ✅ Parcial: aceita campos opcionais
    """
    current_user, tenant_id = user_and_tenant
    ensure_configuracoes_entrega_schema(db)

    # Verifica se tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Busca ou cria configuração
    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config:
        # Cria se não existe
        config = ConfiguracaoEntrega(tenant_id=tenant_id, user_id=current_user.id)
        db.add(config)
    elif config.user_id is None:
        config.user_id = current_user.id

    # Atualiza apenas campos fornecidos
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    _sync_tenant_delivery_mirror(tenant, config)

    db.commit()
    db.refresh(config)

    return config
