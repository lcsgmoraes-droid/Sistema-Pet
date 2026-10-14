"""Repara a baixa parcial da venda 1335187, com conferência antes de gravar.

Execução padrão apenas mostra o plano. --apply exige que todos os registros
continuem exatamente como estavam na investigação; qualquer diferença aborta.
"""

import argparse
import json
from decimal import Decimal

from sqlalchemy import text

from app.db import SessionLocal
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant


TENANT_ID = "c06e62ae-127c-4bf1-adb8-eeabf5d04596"
VENDA_ID = 1335187
CONTA_ORIGINAL_ID = 10923
CONTA_DUPLICADA_ID = 12563
RECEBIMENTO_ID = 8680
FLUXO_ID = 504
ACTION = "repair_sale_batch_cent"


def _dinheiro(valor):
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"))


def reparar(db, *, aplicar=False):
    params = {
        "tenant": TENANT_ID,
        "venda": VENDA_ID,
        "original": CONTA_ORIGINAL_ID,
        "duplicada": CONTA_DUPLICADA_ID,
        "recebimento": RECEBIMENTO_ID,
        "fluxo": FLUXO_ID,
    }
    lock = " FOR UPDATE" if aplicar and db.bind.dialect.name == "postgresql" else ""

    def linhas(sql):
        return [dict(row) for row in db.execute(text(sql + lock), params).mappings()]

    with tenant_context(TENANT_ID):
        sync_rls_tenant(db, TENANT_ID)
        audit = db.execute(
            text(
                "SELECT id FROM audit_logs WHERE tenant_id=:tenant AND action=:action "
                "AND entity_type='vendas' AND entity_id=:venda ORDER BY id DESC LIMIT 1"
            ),
            {**params, "action": ACTION},
        ).scalar()
        if audit:
            return {"ja_aplicado": True, "audit_id": audit, "venda_id": VENDA_ID}

        vendas = linhas(
            "SELECT id, total, status FROM vendas WHERE tenant_id=:tenant AND id=:venda"
        )
        pagamentos = linhas(
            "SELECT id, valor, status FROM venda_pagamentos "
            "WHERE tenant_id=:tenant AND venda_id=:venda ORDER BY id"
        )
        contas = linhas(
            "SELECT id, valor_final, valor_recebido, status, observacoes "
            "FROM contas_receber WHERE tenant_id=:tenant AND venda_id=:venda ORDER BY id"
        )
        recebimentos = linhas(
            "SELECT r.id, r.conta_receber_id, r.valor_recebido, r.data_recebimento "
            "FROM recebimentos r JOIN contas_receber c ON c.id=r.conta_receber_id "
            "AND c.tenant_id=r.tenant_id WHERE r.tenant_id=:tenant "
            "AND c.venda_id=:venda ORDER BY r.id"
        )
        fluxos = linhas(
            "SELECT id, origem_id, valor, status FROM fluxo_caixa "
            "WHERE tenant_id=:tenant AND origem_tipo='conta_receber' "
            "AND origem_id IN (:original, :duplicada) ORDER BY id"
        )

        if (
            len(vendas) != 1
            or vendas[0]["status"] != "finalizada"
            or _dinheiro(vendas[0]["total"]) != Decimal("334.46")
        ):
            raise ValueError("Venda diferente do caso conferido")
        if [(p["id"], _dinheiro(p["valor"]), p["status"]) for p in pagamentos] != [
            (234595, Decimal("168.00"), "aprovado"),
            (238199, Decimal("166.45"), "confirmado"),
        ]:
            raise ValueError("Pagamentos diferentes do caso conferido")
        if [c["id"] for c in contas] != [CONTA_ORIGINAL_ID, CONTA_DUPLICADA_ID]:
            raise ValueError("Contas diferentes do caso conferido")
        original, duplicada = contas
        if (
            original["status"] != "vencido"
            or _dinheiro(original["valor_final"]) != Decimal("166.46")
            or _dinheiro(original["valor_recebido"]) != 0
            or duplicada["status"] != "pago"
            or _dinheiro(duplicada["valor_final"]) != Decimal("334.46")
            or _dinheiro(duplicada["valor_recebido"]) != Decimal("334.45")
            or not (duplicada["observacoes"] or "").startswith(
                "Criada automaticamente pela baixa em lote"
            )
        ):
            raise ValueError("Saldos ou status das contas mudaram")
        if (
            len(recebimentos) != 1
            or recebimentos[0]["id"] != RECEBIMENTO_ID
            or recebimentos[0]["conta_receber_id"] != CONTA_DUPLICADA_ID
            or _dinheiro(recebimentos[0]["valor_recebido"]) != Decimal("166.45")
            or str(recebimentos[0]["data_recebimento"]) != "2026-10-03"
        ):
            raise ValueError("Recebimentos diferentes do caso conferido")
        if (
            len(fluxos) != 1
            or fluxos[0]["id"] != FLUXO_ID
            or fluxos[0]["origem_id"] != CONTA_DUPLICADA_ID
            or _dinheiro(fluxos[0]["valor"]) != Decimal("166.45")
            or fluxos[0]["status"] != "realizado"
        ):
            raise ValueError("Fluxo de caixa diferente do caso conferido")

        plano = {
            "tenant_id": TENANT_ID,
            "venda_id": VENDA_ID,
            "saldo_pendente": "0.01",
            "conta_original": CONTA_ORIGINAL_ID,
            "conta_a_cancelar": CONTA_DUPLICADA_ID,
            "recebimento_a_transferir": RECEBIMENTO_ID,
            "fluxo_a_referenciar": FLUXO_ID,
            "aplicado": aplicar,
        }
        if not aplicar:
            return plano

        db.execute(
            text(
                "UPDATE vendas SET status='baixa_parcial' WHERE tenant_id=:tenant AND id=:venda"
            ),
            params,
        )
        db.execute(
            text(
                "UPDATE contas_receber SET valor_recebido=166.45, status='parcial', "
                "data_recebimento=:data, updated_at=CURRENT_TIMESTAMP "
                "WHERE tenant_id=:tenant AND id=:original"
            ),
            {**params, "data": recebimentos[0]["data_recebimento"]},
        )
        db.execute(
            text(
                "UPDATE recebimentos SET conta_receber_id=:original "
                "WHERE tenant_id=:tenant AND id=:recebimento AND conta_receber_id=:duplicada"
            ),
            params,
        )
        db.execute(
            text(
                "UPDATE fluxo_caixa SET origem_id=:original, atualizado_em=CURRENT_TIMESTAMP "
                "WHERE tenant_id=:tenant AND id=:fluxo AND origem_id=:duplicada"
            ),
            params,
        )
        db.execute(
            text(
                "UPDATE contas_receber SET valor_recebido=0, status='cancelado', "
                "data_recebimento=NULL, updated_at=CURRENT_TIMESTAMP, "
                "observacoes=observacoes || ' Cancelada no reparo da baixa da venda 1335187.' "
                "WHERE tenant_id=:tenant AND id=:duplicada"
            ),
            params,
        )
        audit_id = db.execute(
            text(
                "INSERT INTO audit_logs "
                "(tenant_id, user_id, action, entity_type, entity_id, old_value, "
                "new_value, details, timestamp) VALUES "
                "(:tenant, NULL, :action, 'vendas', :venda, :old, :new, :details, "
                "CURRENT_TIMESTAMP) RETURNING id"
            ),
            {
                **params,
                "action": ACTION,
                "old": json.dumps(
                    {
                        "venda": vendas[0],
                        "pagamentos": pagamentos,
                        "contas": contas,
                        "recebimentos": recebimentos,
                        "fluxos": fluxos,
                    },
                    default=str,
                ),
                "new": json.dumps(plano),
                "details": "Reclassifica baixa de R$ 166,45 como parcial e vincula o recebimento à conta original vencida.",
            },
        ).scalar_one()
        db.commit()
        return {**plano, "audit_id": audit_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            print(json.dumps(reparar(db, aplicar=args.apply), ensure_ascii=False))
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
