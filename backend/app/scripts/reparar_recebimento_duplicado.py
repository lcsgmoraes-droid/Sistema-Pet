"""Reparo pontual e auditado de duas baixas automaticas para um pagamento.

Dry-run por padrao. Exige IDs explicitos; recusa pagamentos, valores ou vinculos
que nao correspondam ao caso conferido. Nao simula devolucao de dinheiro.
"""

import argparse
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import inspect, text

from app.db import SessionLocal
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant

ACTION = "repair_duplicate_sale_receipt"


def _verificar_vinculos(db, conta_id, recebimento_id):
    inspector = inspect(db.get_bind())
    quote = db.get_bind().dialect.identifier_preparer.quote
    for tabela in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(tabela):
            alvo = fk["referred_table"]
            if alvo not in {"contas_receber", "recebimentos"}:
                continue
            if tabela == "recebimentos" and alvo == "contas_receber":
                continue  # As duas baixas sao conferidas integralmente no plano.
            colunas = fk["constrained_columns"]
            if len(colunas) != 1:
                raise ValueError("Vinculo composto exige revisao manual")
            ident = conta_id if alvo == "contas_receber" else recebimento_id
            sql = f"SELECT count(*) FROM {quote(tabela)} WHERE {quote(colunas[0])}=:id"
            if db.execute(text(sql), {"id": ident}).scalar():
                raise ValueError(f"Reparo recusado: registro referenciado em {tabela}")


def reparar(
    db,
    *,
    tenant_id,
    venda_id,
    conta_original_id,
    conta_duplicada_id,
    recebimento_duplicado_id,
    motivo,
    aplicar=False,
):
    tenant = UUID(str(tenant_id))
    if not motivo.strip() or conta_original_id == conta_duplicada_id:
        raise ValueError("Informe motivo e contas distintas")
    params = {
        "t": tenant.hex if db.bind.dialect.name == "sqlite" else str(tenant),
        "v": venda_id,
        "dup": conta_duplicada_id,
        "r": recebimento_duplicado_id,
    }
    lock = " FOR UPDATE" if db.bind.dialect.name == "postgresql" else ""

    def rows(sql, bloquear=False):
        return [
            dict(row)
            for row in db.execute(
                text(sql + (lock if bloquear else "")), params
            ).mappings()
        ]

    with tenant_context(tenant):
        sync_rls_tenant(db, tenant)
        vendas = rows(
            "SELECT id, numero_venda, total, status FROM vendas WHERE tenant_id=:t AND id=:v",
            True,
        )
        if len(vendas) != 1:
            raise ValueError("Venda nao encontrada no tenant informado")
        venda = vendas[0]
        contas = rows(
            "SELECT * FROM contas_receber WHERE tenant_id=:t AND venda_id=:v ORDER BY id",
            True,
        )
        pagamentos = rows(
            "SELECT id, valor, forma_pagamento FROM venda_pagamentos WHERE tenant_id=:t AND venda_id=:v ORDER BY id",
            True,
        )
        recebimentos = rows(
            "SELECT r.* FROM recebimentos r WHERE r.tenant_id=:t AND r.conta_receber_id IN (SELECT c.id FROM contas_receber c WHERE c.tenant_id=:t AND c.venda_id=:v) ORDER BY r.id",
            True,
        )
        auditorias = rows(
            "SELECT id, new_value FROM audit_logs WHERE tenant_id=:t AND action='repair_duplicate_sale_receipt' AND entity_id=:v"
        )
        for auditoria in auditorias:
            novo = json.loads(auditoria["new_value"] or "{}")
            if (
                novo.get("recebimento_removido") == recebimento_duplicado_id
                and novo.get("conta_cancelada") == conta_duplicada_id
            ):
                return {
                    "ja_aplicado": True,
                    "audit_id": auditoria["id"],
                    "venda_id": venda_id,
                }

        if {c["id"] for c in contas} != {conta_original_id, conta_duplicada_id}:
            raise ValueError("Contas diferentes do par conferido")
        if (
            len(pagamentos) != 1
            or len(recebimentos) != 2
            or venda["status"] != "finalizada"
        ):
            raise ValueError(
                "Esperado um pagamento e exatamente duas baixas em venda finalizada"
            )
        valor = Decimal(str(pagamentos[0]["valor"])).quantize(Decimal("0.01"))
        if valor <= 0 or Decimal(str(venda["total"])) != valor:
            raise ValueError("Total da venda nao corresponde ao unico pagamento")
        for conta in contas:
            if conta["status"] != "recebido" or any(
                Decimal(str(conta[campo])) != valor
                for campo in ("valor_original", "valor_final", "valor_recebido")
            ):
                raise ValueError(
                    "Conta possui valores ou status diferentes do esperado"
                )
            if (
                conta.get("conciliado")
                or conta.get("conciliacao_recebimento_id")
                or conta.get("conciliacao_lote_id")
                or conta.get("data_liquidacao")
            ):
                raise ValueError("Conta conciliada exige revisao especifica")
        if contas[0]["forma_pagamento_id"] != contas[1]["forma_pagamento_id"]:
            raise ValueError("Formas de pagamento diferentes")
        original = next(
            (r for r in recebimentos if r["conta_receber_id"] == conta_original_id),
            None,
        )
        duplicado = next(
            (
                r
                for r in recebimentos
                if r["id"] == recebimento_duplicado_id
                and r["conta_receber_id"] == conta_duplicada_id
            ),
            None,
        )
        if not original or not duplicado or original["id"] >= duplicado["id"]:
            raise ValueError("Identificacao das baixas divergente")
        if original["data_recebimento"] != duplicado["data_recebimento"]:
            raise ValueError("Datas de recebimento diferentes")
        for baixa in recebimentos:
            if Decimal(
                str(baixa["valor_recebido"])
            ) != valor or "Venda à vista #" + venda["numero_venda"] not in (
                baixa["observacoes"] or ""
            ):
                raise ValueError(
                    "Baixa nao corresponde ao recebimento automatico conferido"
                )
        _verificar_vinculos(db, conta_duplicada_id, recebimento_duplicado_id)
        params.update({"doc": f"VENDA-{venda_id}", "saldo": f"VENDA-{venda_id}-SALDO"})
        previsoes = rows(
            "SELECT * FROM lancamentos_manuais WHERE tenant_id=:t AND documento IN (:doc,:saldo) AND tipo='entrada' AND status='previsto' ORDER BY id",
            True,
        )
        plano = {
            "tenant_id": str(tenant),
            "venda_id": venda_id,
            "numero_venda": venda["numero_venda"],
            "recebimento_removido": recebimento_duplicado_id,
            "conta_cancelada": conta_duplicada_id,
            "recebimento_preservado": original["id"],
            "valor_corrigido": str(valor),
            "previsoes_canceladas": [p["id"] for p in previsoes],
            "aplicado": aplicar,
        }
        if not aplicar:
            return plano
        antes = {
            "venda": venda,
            "contas": contas,
            "pagamentos": pagamentos,
            "recebimentos": recebimentos,
            "previsoes": previsoes,
        }
        db.execute(
            text(
                "DELETE FROM recebimentos WHERE tenant_id=:t AND id=:r AND conta_receber_id=:dup"
            ),
            params,
        )
        db.execute(
            text(
                "UPDATE contas_receber SET status='cancelado', valor_recebido=0, data_recebimento=NULL, updated_at=CURRENT_TIMESTAMP WHERE tenant_id=:t AND id=:dup"
            ),
            params,
        )
        db.execute(
            text(
                "UPDATE lancamentos_manuais SET status='cancelado' WHERE tenant_id=:t AND documento IN (:doc,:saldo) AND tipo='entrada' AND status='previsto'"
            ),
            params,
        )
        audit_id = db.execute(
            text(
                "INSERT INTO audit_logs (tenant_id,user_id,action,entity_type,entity_id,old_value,new_value,details,timestamp) VALUES (:t,NULL,:action,'vendas',:v,:old,:new,:details,CURRENT_TIMESTAMP) RETURNING id"
            ),
            {
                **params,
                "action": ACTION,
                "old": json.dumps(antes, default=str),
                "new": json.dumps(plano),
                "details": motivo,
            },
        ).scalar_one()
        db.commit()
        return {**plano, "audit_id": audit_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True)
    for campo in (
        "venda-id",
        "conta-original-id",
        "conta-duplicada-id",
        "recebimento-duplicado-id",
    ):
        parser.add_argument(f"--{campo}", type=int, required=True)
    parser.add_argument("--motivo", required=True)
    parser.add_argument("--apply", action="store_true")
    args = vars(parser.parse_args())
    args["aplicar"] = args.pop("apply")
    with SessionLocal() as db:
        try:
            resultado = reparar(db, **args)
            print(json.dumps(resultado, ensure_ascii=False))
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
