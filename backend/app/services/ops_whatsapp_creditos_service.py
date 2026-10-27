"""OPS: pacotes de creditos, pedidos de compra, controle e ajustes por loja.

O OPS monta o catalogo de pacotes, confirma os pagamentos (a cobranca automatica
entra depois) e liga o controle de creditos loja a loja. Toda alteracao fica no
historico (quem, quando e o valor anterior).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Tenant
from app.services.ops_tenant_log_service import registrar_alteracoes
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.whatsapp import creditos_service
from app.whatsapp.creditos_models import (
    COMPRA_CANCELADA,
    COMPRA_PENDENTE,
    WhatsAppCompraPacote,
    WhatsAppCustoCredito,
    WhatsAppPacote,
)
from app.whatsapp.models import TenantWhatsAppConfig

CATEGORIA_DO_LOG = "creditos_whatsapp"
LIMITE_DE_LOJAS = 500


class CreditosError(Exception):
    def __init__(self, mensagem: str, status_code: int = 422):
        self.status_code = status_code
        super().__init__(mensagem)


def _agora() -> datetime:
    return datetime.now(UTC)


def pacote_para_dict(p: WhatsAppPacote) -> dict[str, Any]:
    return {
        "id": p.id,
        "nome": p.nome,
        "creditos": p.creditos,
        "preco": float(p.preco),
        "ativo": p.ativo,
    }


def compra_para_dict(
    c: WhatsAppCompraPacote, loja_nome: str | None = None
) -> dict[str, Any]:
    return {
        "id": c.id,
        "loja_id": str(c.tenant_id),
        "loja_nome": loja_nome,
        "pacote_nome": c.pacote_nome,
        "creditos": c.creditos,
        "preco": float(c.preco),
        "status": c.status,
        "solicitado_por": c.solicitado_por,
        "solicitado_em": c.solicitado_em.isoformat() if c.solicitado_em else None,
        "confirmado_por": c.confirmado_por,
        "confirmado_em": c.confirmado_em.isoformat() if c.confirmado_em else None,
        "observacao": c.observacao,
    }


def custos_para_lista(db: Session) -> list[dict[str, Any]]:
    tabela = creditos_service.tabela_de_custos(db)
    return [
        {
            "chave": chave,
            "rotulo": creditos_service.ROTULO_DO_CUSTO[chave],
            "creditos": valor,
            "padrao": creditos_service.CUSTOS_PADRAO[chave],
        }
        for chave, valor in tabela.items()
    ]


# --- catalogo ---------------------------------------------------------------------


def criar_pacote(
    db: Session, *, nome: str, creditos: int, preco: Any, admin_email: str
) -> WhatsAppPacote:
    nome = (nome or "").strip()
    if not nome:
        raise CreditosError("Informe o nome do pacote.")
    if creditos < 1 or creditos > 10_000_000:
        raise CreditosError("A quantidade de créditos deve ser de 1 a 10.000.000.")
    valor = Decimal(str(preco))
    if valor <= 0 or valor > Decimal(1000000):
        raise CreditosError("Informe um preço maior que zero.")
    pacote = WhatsAppPacote(
        nome=nome, creditos=creditos, preco=valor, criado_por=admin_email
    )
    db.add(pacote)
    db.flush()
    return pacote


def alterar_pacote(db: Session, pacote_id: int, *, ativo: bool) -> WhatsAppPacote:
    pacote = db.get(WhatsAppPacote, pacote_id)
    if pacote is None:
        raise CreditosError("Pacote não encontrado.", 404)
    pacote.ativo = ativo
    db.flush()
    return pacote


def definir_custo(db: Session, chave: str, creditos: int, admin_email: str) -> None:
    if chave not in creditos_service.CUSTOS_PADRAO:
        raise CreditosError("Tipo de envio desconhecido.", 404)
    if creditos < 0 or creditos > 100_000:
        raise CreditosError("O custo deve ser de 0 a 100.000 créditos.")
    linha = db.get(WhatsAppCustoCredito, chave)
    if linha is None:
        db.add(
            WhatsAppCustoCredito(
                chave=chave, creditos=creditos, atualizado_por=admin_email
            )
        )
    else:
        linha.creditos = creditos
        linha.atualizado_por = admin_email
        linha.atualizado_em = _agora()
    db.flush()


# --- compras ----------------------------------------------------------------------


def solicitar_compra(
    db: Session, *, tenant_id: Any, pacote_id: int, solicitante: str
) -> WhatsAppCompraPacote:
    pacote = db.get(WhatsAppPacote, pacote_id)
    if pacote is None or not pacote.ativo:
        raise CreditosError("Este pacote não está disponível.", 404)
    pendentes = (
        db.query(WhatsAppCompraPacote)
        .filter(
            WhatsAppCompraPacote.tenant_id == tenant_id,
            WhatsAppCompraPacote.status == COMPRA_PENDENTE,
        )
        .count()
    )
    if pendentes >= 3:
        raise CreditosError(
            "Você já tem 3 pedidos aguardando pagamento. Aguarde a confirmação ou cancele um deles.",
            409,
        )
    compra = WhatsAppCompraPacote(
        tenant_id=tenant_id,
        pacote_id=pacote.id,
        pacote_nome=pacote.nome,
        creditos=pacote.creditos,
        preco=pacote.preco,
        solicitado_por=solicitante,
    )
    db.add(compra)
    db.flush()
    return compra


def cancelar_compra(
    db: Session,
    compra_id: int,
    *,
    tenant_id: Any = None,
    admin_email: str | None = None,
) -> WhatsAppCompraPacote:
    compra = db.get(WhatsAppCompraPacote, compra_id)
    if compra is None or (tenant_id is not None and compra.tenant_id != tenant_id):
        raise CreditosError("Pedido não encontrado.", 404)
    if compra.status != COMPRA_PENDENTE:
        raise CreditosError(
            "Só é possível cancelar um pedido que ainda está pendente.", 409
        )
    compra.status = COMPRA_CANCELADA
    if admin_email:
        compra.confirmado_por = admin_email
        compra.confirmado_em = _agora()
    db.flush()
    return compra


def confirmar_compra(
    db: Session, compra_id: int, *, admin: Any, observacao: str | None
) -> WhatsAppCompraPacote:
    """Pagamento recebido: libera os creditos (uma unica vez) e registra no historico."""
    compra = (
        db.query(WhatsAppCompraPacote)
        .filter(WhatsAppCompraPacote.id == compra_id)
        .with_for_update()
        .first()
    )
    if compra is None:
        raise CreditosError("Pedido não encontrado.", 404)
    if compra.status != COMPRA_PENDENTE:
        raise CreditosError("Este pedido já foi confirmado ou cancelado.", 409)
    tenant_id = UUID(str(compra.tenant_id))
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        creditos_service.creditar_compra(db, compra, admin.email)
    compra.confirmado_por = admin.email
    compra.confirmado_em = _agora()
    compra.observacao = (observacao or "").strip()[:1000] or None
    registrar_alteracoes(
        db,
        tenant_id=str(tenant_id),
        admin=admin,
        categoria=CATEGORIA_DO_LOG,
        antes={"pacote": None},
        depois={"pacote": f"{compra.pacote_nome}: +{compra.creditos} créditos"},
    )
    db.flush()
    return compra


# --- por loja -----------------------------------------------------------------------


def configurar_loja(
    db: Session, tenant_id: str, *, ativo: bool, franquia_mensal: int, admin: Any
) -> dict[str, Any]:
    if franquia_mensal < 0 or franquia_mensal > 10_000_000:
        raise CreditosError("A franquia mensal deve ser de 0 a 10.000.000 créditos.")
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise CreditosError("Loja não encontrada.", 404)
    tid = UUID(str(tenant.id))
    with tenant_context(tid):
        sync_rls_tenant(db, tid)
        config = (
            db.query(TenantWhatsAppConfig)
            .filter(TenantWhatsAppConfig.tenant_id == tid)
            .first()
        )
        if config is None:
            raise CreditosError(
                "A loja ainda não configurou o WhatsApp. Peça para ela salvar a configuração antes.",
                409,
            )
        antes = {
            "controle de créditos": "ligado"
            if config.creditos_controle_ativo
            else "desligado",
            "franquia mensal": config.creditos_franquia_mensal,
        }
        config.creditos_controle_ativo = ativo
        config.creditos_franquia_mensal = franquia_mensal
        registrar_alteracoes(
            db,
            tenant_id=str(tid),
            admin=admin,
            categoria=CATEGORIA_DO_LOG,
            antes=antes,
            depois={
                "controle de créditos": "ligado" if ativo else "desligado",
                "franquia mensal": franquia_mensal,
            },
        )
        db.flush()
        return creditos_service.saldo(db, tid, config)


def ajustar_loja(
    db: Session, tenant_id: str, *, quantidade: int, descricao: str, admin: Any
) -> dict[str, Any]:
    if quantidade == 0 or abs(quantidade) > 10_000_000:
        raise CreditosError("Informe uma quantidade diferente de zero.")
    if not (descricao or "").strip():
        raise CreditosError("Explique o motivo do ajuste.")
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise CreditosError("Loja não encontrada.", 404)
    tid = UUID(str(tenant.id))
    with tenant_context(tid):
        sync_rls_tenant(db, tid)
        antes = creditos_service.saldo(db, tid)["avulso"]
        creditos_service.ajustar(db, tid, quantidade, descricao, admin.email)
        db.flush()
        registrar_alteracoes(
            db,
            tenant_id=str(tid),
            admin=admin,
            categoria=CATEGORIA_DO_LOG,
            antes={"créditos avulsos": antes},
            depois={"créditos avulsos": antes + quantidade},
        )
        return creditos_service.saldo(db, tid)


def visao_geral(db: Session) -> dict[str, Any]:
    nomes: dict[str, str] = {}
    lojas = []
    for tenant in db.query(Tenant).order_by(Tenant.name).limit(LIMITE_DE_LOJAS).all():
        tid = UUID(str(tenant.id))
        nomes[str(tid)] = tenant.name
        with tenant_context(tid):
            sync_rls_tenant(db, tid)
            config = (
                db.query(TenantWhatsAppConfig)
                .filter(TenantWhatsAppConfig.tenant_id == tid)
                .first()
            )
            if config is None:
                continue
            lojas.append(
                {
                    "loja_id": str(tid),
                    "loja_nome": tenant.name,
                    **creditos_service.saldo(db, tid, config),
                }
            )
    compras = (
        db.query(WhatsAppCompraPacote)
        .order_by(WhatsAppCompraPacote.id.desc())
        .limit(100)
        .all()
    )
    return {
        "pacotes": [
            pacote_para_dict(p)
            for p in db.query(WhatsAppPacote).order_by(WhatsAppPacote.creditos).all()
        ],
        "custos": custos_para_lista(db),
        "compras": [compra_para_dict(c, nomes.get(str(c.tenant_id))) for c in compras],
        "lojas": lojas,
    }
