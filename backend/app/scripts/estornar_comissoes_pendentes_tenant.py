"""Estorno auditável e restrito das comissões pendentes de um único tenant.

Execução padrão é somente prévia. A aplicação exige nome, quantidade e total
esperados; qualquer divergência interrompe a transação sem alterar dados.
"""

import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.comissoes_financeiro_service import cancelar_provisoes_comissao_venda
from app.comissoes_models import ComissaoItem, ComissaoVenda
from app.db import SessionLocal
from app.financeiro_models import ContaPagar
from app.models import Tenant
from app.tenancy.context import tenant_context
from app.utils.tenant_safe_sql import execute_tenant_safe


STATUS_ALVO = ("pendente",)
MOTIVO = "Zeramento das comissões pendentes solicitado pela Tecno Agropet em 17/10/2026"


def valor_total(itens):
    return sum(
        (Decimal(str(item.valor_comissao_gerada or 0)) for item in itens),
        Decimal("0"),
    ).quantize(Decimal("0.01"))


def validar_plano(itens, *, quantidade_esperada, total_esperado):
    if len(itens) != quantidade_esperada or valor_total(itens) != total_esperado:
        raise ValueError(
            f"Prévia mudou: {len(itens)} comissões, R$ {valor_total(itens)}. "
            "Nenhuma alteração foi aplicada."
        )
    if any(
        Decimal(str(item.valor_pago or 0)) > 0 or item.data_fechamento for item in itens
    ):
        raise ValueError(
            "Há comissão pendente com pagamento ou fechamento; revisão manual necessária."
        )


def identificar_provisoes_orfas(db, *, tenant_id, itens):
    """Confirma que uma marcação órfã não representa dívida ou DRE ativa."""
    orfaos = [
        item
        for item in itens
        if item.comissao_provisionada and item.conta_pagar_id is None
    ]
    for item in orfaos:
        documento = f"COMISSAO-VENDA-{item.venda_id}-{item.id}"
        conta = (
            db.query(ContaPagar.id)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.documento == documento,
            )
            .first()
        )
        venda = execute_tenant_safe(
            db,
            """
            SELECT data_venda FROM vendas
            WHERE id = :venda_id AND {tenant_filter}
            LIMIT 1
            """,
            {"venda_id": item.venda_id},
            tenant_id=tenant_id,
        ).first()
        if conta or not venda or not venda[0]:
            raise ValueError(
                f"Provisão órfã {item.id} tem conta ou venda inconclusiva; revisão manual necessária."
            )
        data_venda = venda[0].date()
        periodo_dre = execute_tenant_safe(
            db,
            """
            SELECT id FROM dre_periodos
            WHERE data_inicio <= :data_venda
              AND data_fim >= :data_venda
              AND {tenant_filter}
            LIMIT 1
            """,
            {"data_venda": data_venda},
            tenant_id=tenant_id,
        ).first()
        if periodo_dre:
            raise ValueError(
                f"Provisão órfã {item.id} coincide com período DRE; revisão manual necessária."
            )
    return orfaos


def validar_orfaos_esperados(orfaos, ids_esperados):
    if sorted(item.id for item in orfaos) != sorted(ids_esperados):
        raise ValueError(
            "As provisões órfãs diferem da prévia. Nenhuma alteração foi aplicada."
        )


def executar(
    *,
    tenant_nome,
    aplicar,
    tenant_id_esperado=None,
    quantidade_esperada=None,
    total_esperado=None,
    ids_orfaos_esperados=(),
):
    with SessionLocal() as db:
        tenants = db.query(Tenant).filter(Tenant.name == tenant_nome).all()
        if len(tenants) != 1:
            raise ValueError("O nome informado não identifica exatamente um tenant.")
        tenant = tenants[0]
        tenant_id = UUID(str(tenant.id))
        if aplicar and tenant_id != tenant_id_esperado:
            raise ValueError(
                "O ID do tenant difere da prévia. Nenhuma alteração foi aplicada."
            )

        with tenant_context(tenant_id):
            itens = (
                db.query(ComissaoItem)
                .filter(
                    ComissaoItem.tenant_id == tenant_id,
                    ComissaoItem.status.in_(STATUS_ALVO),
                )
                .with_for_update()
                .all()
            )
            venda_ids = {item.venda_id for item in itens}
            orfaos = identificar_provisoes_orfas(db, tenant_id=tenant_id, itens=itens)
            ids_orfaos = sorted(item.id for item in orfaos)
            resumo = {
                "tenant": tenant.name,
                "tenant_id": str(tenant.id),
                "quantidade": len(itens),
                "valor": str(valor_total(itens)),
                "status": dict(Counter(item.status for item in itens)),
                "vendas": len(venda_ids),
                "provisoes_orfas": ids_orfaos,
            }
            print(resumo)
            if not aplicar:
                return resumo

            validar_plano(
                itens,
                quantidade_esperada=quantidade_esperada,
                total_esperado=total_esperado,
            )
            validar_orfaos_esperados(orfaos, ids_orfaos_esperados)
            outros_status = (
                db.query(ComissaoItem.id)
                .filter(
                    ComissaoItem.tenant_id == tenant_id,
                    ComissaoItem.venda_id.in_(venda_ids),
                    ~ComissaoItem.status.in_(STATUS_ALVO + ("estornado",)),
                )
                .first()
            )
            if outros_status:
                raise ValueError(
                    "Há comissão fechada ou paga nas mesmas vendas; revisão manual necessária."
                )
            consolidada = (
                db.query(ComissaoVenda.id)
                .filter(
                    ComissaoVenda.tenant_id == tenant_id,
                    ComissaoVenda.venda_id.in_(venda_ids),
                )
                .first()
            )
            if consolidada:
                raise ValueError(
                    "Há comissão consolidada nessas vendas; revisão manual necessária."
                )

            for item in orfaos:
                item.comissao_provisionada = False
            db.flush()
            for venda_id in sorted(venda_ids):
                cancelar_provisoes_comissao_venda(
                    db, venda_id=venda_id, tenant_id=tenant_id, motivo=MOTIVO
                )
            for item in itens:
                item.status = "estornado"
                item.data_estorno = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
                item.motivo_estorno = (
                    f"{MOTIVO}; marcação órfã sem conta ou DRE saneada"
                    if item.id in ids_orfaos
                    else MOTIVO
                )
            db.flush()
            restantes = (
                db.query(ComissaoItem.id)
                .filter(
                    ComissaoItem.tenant_id == tenant_id,
                    ComissaoItem.status.in_(STATUS_ALVO),
                )
                .count()
            )
            if restantes:
                raise ValueError(
                    f"Restaram {restantes} comissões pendentes; transação cancelada."
                )
            db.commit()
            print(f"Estornadas {len(itens)} comissões. Itens com status pendente: 0.")
            return resumo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-tenant-id", type=UUID)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--expected-total", type=Decimal)
    parser.add_argument("--expected-orphan-ids", nargs="*", type=int, default=[])
    args = parser.parse_args()
    if args.apply and (
        args.expected_tenant_id is None
        or args.expected_count is None
        or args.expected_total is None
    ):
        parser.error(
            "--apply exige --expected-tenant-id, --expected-count e --expected-total"
        )
    executar(
        tenant_nome=args.tenant_name,
        aplicar=args.apply,
        tenant_id_esperado=args.expected_tenant_id,
        quantidade_esperada=args.expected_count,
        total_esperado=args.expected_total,
        ids_orfaos_esperados=args.expected_orphan_ids,
    )


if __name__ == "__main__":
    main()
