import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.scripts import reparar_venda_tecnopet_202610100007 as repair


@pytest.fixture
def repair_db():
    """Small SQL schema: exercises the real SQL transaction, without production data."""
    engine = create_engine("sqlite://")
    schemas = {
        "caixas": "numero_caixa INTEGER, status TEXT, valor_esperado NUMERIC, valor_informado NUMERIC, diferenca NUMERIC",
        "vendas": "numero_venda TEXT, cliente_id INTEGER, caixa_id INTEGER, status TEXT, total NUMERIC",
        "clientes": "credito NUMERIC, updated_at TEXT",
        "venda_pagamentos": "venda_id INTEGER, caixa_id INTEGER, forma_pagamento TEXT, forma_pagamento_id INTEGER, valor NUMERIC, status TEXT",
        "movimentacoes_caixa": "venda_id INTEGER, caixa_id INTEGER, tipo TEXT, forma_pagamento TEXT, valor NUMERIC, descricao TEXT, documento TEXT, updated_at TEXT",
        "contas_receber": "venda_id INTEGER, cliente_id INTEGER, status TEXT, valor_original NUMERIC, valor_final NUMERIC, valor_recebido NUMERIC, observacoes TEXT, updated_at TEXT",
        "recebimentos": "conta_receber_id INTEGER, valor_recebido NUMERIC, forma_pagamento_id INTEGER, observacoes TEXT, user_id INTEGER, data_recebimento TEXT",
        "lancamentos_manuais": "documento TEXT, valor NUMERIC, tipo TEXT, status TEXT, observacoes TEXT, updated_at TEXT",
        "credito_logs": "cliente_id INTEGER, tipo TEXT, valor NUMERIC, saldo_anterior NUMERIC, saldo_atual NUMERIC, motivo TEXT, referencia_id INTEGER, usuario_nome TEXT",
        "vendas_devolucoes": "venda_id INTEGER",
        "audit_logs": "user_id INTEGER, action TEXT, entity_type TEXT, entity_id INTEGER, old_value TEXT, new_value TEXT, details TEXT",
    }
    with engine.begin() as conn:
        for table, columns in schemas.items():
            conn.execute(
                text(
                    f"CREATE TABLE {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, {columns})"
                )
            )
    with Session(engine) as db:

        def insert(table, **values):
            values = {"tenant_id": repair.TENANT_ID, **values}
            db.execute(
                text(
                    f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join(':' + key for key in values)})"
                ),
                values,
            )

        insert(
            "caixas",
            id=378,
            numero_caixa=9,
            status="aberto",
            valor_esperado=None,
            valor_informado=None,
            diferenca=None,
        )
        insert(
            "vendas",
            id=repair.SALE_ID,
            numero_venda=repair.SALE_NUMBER,
            cliente_id=16685,
            caixa_id=378,
            status="finalizada",
            total="115.00",
        )
        insert("clientes", id=16685, credito="0.33", updated_at="2026-10-10")
        insert(
            "venda_pagamentos",
            id=260970,
            venda_id=repair.SALE_ID,
            caixa_id=378,
            forma_pagamento="dinheiro",
            forma_pagamento_id=74,
            valor="115.00",
            status="pendente",
        )
        for row_id in (3606, 3608, 3609):
            insert(
                "movimentacoes_caixa",
                id=row_id,
                venda_id=repair.SALE_ID,
                caixa_id=378,
                tipo="venda",
                forma_pagamento="dinheiro",
                valor="115.00",
                descricao="Venda #202610100007",
            )
        insert(
            "movimentacoes_caixa",
            id=3613,
            venda_id=None,
            caixa_id=378,
            tipo="sangria",
            forma_pagamento="dinheiro",
            valor="230.00",
            descricao="NÃO FOI SANGRIA EM DINHEIRO - VENDA MARINA FRANCO TRIPLICADA",
        )
        # Another legitimate sale must remain unchanged by the repair.
        insert(
            "movimentacoes_caixa",
            id=3500,
            venda_id=99,
            caixa_id=378,
            tipo="venda",
            forma_pagamento="dinheiro",
            valor="71.00",
            descricao="Outra venda",
        )
        insert(
            "contas_receber",
            id=14870,
            venda_id=repair.SALE_ID,
            cliente_id=16685,
            status="recebido",
            valor_original="115.00",
            valor_final="115.00",
            valor_recebido="115.00",
            observacoes="Quitacao original",
        )
        insert(
            "recebimentos",
            id=10047,
            conta_receber_id=14870,
            valor_recebido="115.00",
            forma_pagamento_id=74,
            observacoes="Baixa original",
            user_id=74,
            data_recebimento="2026-10-10",
        )
        for row_id, value, status, document in (
            (13067, "115.00", "realizado", "VENDA-1365844"),
            (13068, "115.00", "previsto", "VENDA-1365844-SALDO"),
            (13069, "4.90", "realizado", "VENDA-1365844-REALIZADO"),
        ):
            insert(
                "lancamentos_manuais",
                id=row_id,
                documento=document,
                valor=value,
                tipo="entrada",
                status=status,
                observacoes="Original",
                updated_at="2026-10-10",
            )
        for row_id, payment_id, amount, method in (
            (64287, 260765, "4.90", "Crédito Cliente"),
            (64288, 260964, "115.00", "dinheiro"),
            (64303, 260968, "115.00", "dinheiro"),
        ):
            insert(
                "audit_logs",
                id=row_id,
                action="delete",
                entity_type="venda_pagamentos",
                entity_id=payment_id,
                details=f"Excluído pagamento de R$ {amount} ({method}) da venda #1365844",
            )
        db.commit()
        yield db
    engine.dispose()


def all_rows(db, table):
    return [
        dict(row)
        for row in db.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings()
    ]


def capture(db):
    return {
        table: all_rows(db, table)
        for table in (
            "caixas",
            "vendas",
            "clientes",
            "movimentacoes_caixa",
            "lancamentos_manuais",
            "venda_pagamentos",
            "contas_receber",
            "recebimentos",
            "credito_logs",
            "audit_logs",
            "vendas_devolucoes",
        )
    }


def test_dry_run_changes_nothing(repair_db):
    before = capture(repair_db)
    result = repair.repair_sale(repair_db)
    assert result["status"] == "planned"
    assert result["cash_net_before"] == result["cash_net_after"] == "115.00"
    assert result["credit_after"] == "5.23"
    assert capture(repair_db) == before


@pytest.mark.parametrize("closed", [False, True])
def test_apply_preserves_cash_and_quitation_restores_credit_and_has_reversible_audit(
    repair_db, closed
):
    if closed:
        repair_db.execute(
            text(
                "UPDATE caixas SET status='fechado', valor_esperado=286, valor_informado=286, diferenca=0"
            )
        )
        repair_db.commit()
    before = capture(repair_db)
    result = repair.repair_sale(repair_db, apply=True)
    assert result["status"] == "applied"
    after = capture(repair_db)
    assert after["caixas"] == before["caixas"]
    assert after["vendas"] == before["vendas"]
    assert after["venda_pagamentos"] == before["venda_pagamentos"]
    assert (
        after["contas_receber"][0]["observacoes"]
        == "Quitacao original [venda_pagamento:260970]"
    )
    assert (
        after["recebimentos"][0]["observacoes"]
        == "Baixa original [venda_pagamento:260970]"
    )
    assert after["movimentacoes_caixa"][-1]["documento"] == "PAGAMENTO-260970"
    assert [row["id"] for row in after["movimentacoes_caixa"]] == [3500, 3609]
    assert repair._cash_net(after["movimentacoes_caixa"]) == repair._cash_net(
        before["movimentacoes_caixa"]
    )
    assert repair._money(after["clientes"][0]["credito"]) == repair.Decimal("5.23")
    assert [row["status"] for row in after["lancamentos_manuais"]] == [
        "realizado",
        "cancelado",
        "cancelado",
    ]
    assert len(after["credito_logs"]) == 1
    assert after["credito_logs"][0]["tipo"] == "estorno_venda"
    assert after["vendas_devolucoes"] == []
    audit = after["audit_logs"][-1]
    old = json.loads(audit["old_value"])
    saved = json.loads(audit["new_value"])
    assert saved["repair_key"] == repair.REPAIR_KEY
    assert saved["status"] == "applied"
    assert {row["id"] for row in old["movements"]} == {3606, 3608, 3609, 3613}
    assert old["customer"]["credito"] == before["clientes"][0]["credito"]
    assert old["cash_register"] == before["caixas"][0]


def test_retry_does_not_restore_credit_twice(repair_db):
    first = repair.repair_sale(repair_db, apply=True)
    after = capture(repair_db)
    second = repair.repair_sale(repair_db, apply=True)
    assert second["status"] == "already_applied"
    assert second["audit_id"] == first["audit_id"]
    assert capture(repair_db) == after


def test_failure_writing_audit_rolls_back_all_other_writes(repair_db):
    before = capture(repair_db)
    repair_db.execute(
        text(
            "CREATE TRIGGER reject_repair_audit BEFORE INSERT ON audit_logs "
            "WHEN NEW.action='business.sale.payment_repair' "
            "BEGIN SELECT RAISE(ABORT, 'forced audit failure'); END"
        )
    )
    repair_db.commit()
    with pytest.raises(Exception, match="forced audit failure"):
        repair.repair_sale(repair_db, apply=True)
    assert capture(repair_db) == before


@pytest.mark.parametrize(
    "changed_sql",
    [
        "UPDATE clientes SET credito=5.23 WHERE id=16685",
        "DELETE FROM movimentacoes_caixa WHERE id=3613",
        "UPDATE movimentacoes_caixa SET descricao='Sangria real de dinheiro' WHERE id=3613",
        "UPDATE venda_pagamentos SET valor=100 WHERE id=260970",
        "UPDATE vendas SET status='cancelada' WHERE id=1365844",
        "UPDATE vendas SET tenant_id='outra-empresa' WHERE id=1365844",
        "DELETE FROM audit_logs WHERE id=64287",
        "UPDATE recebimentos SET valor_recebido=114 WHERE id=10047",
        "UPDATE recebimentos SET observacoes='[venda_pagamento:260765]' WHERE id=10047",
        "UPDATE contas_receber SET observacoes='[venda_pagamento:260765]' WHERE id=14870",
        "UPDATE movimentacoes_caixa SET documento='PAGAMENTO-260765' WHERE id=3609",
        "INSERT INTO vendas_devolucoes (tenant_id,venda_id) VALUES ('86219670-d501-4f43-8042-85d78c4de353',1365844)",
        "INSERT INTO credito_logs (tenant_id,cliente_id,tipo,referencia_id) VALUES ('86219670-d501-4f43-8042-85d78c4de353',16685,'adicao_manual',1365844)",
    ],
)
def test_changed_state_aborts_without_any_repair_write(repair_db, changed_sql):
    repair_db.execute(text(changed_sql))
    repair_db.commit()
    before = capture(repair_db)
    with pytest.raises(repair.RepairStateChanged):
        repair.repair_sale(repair_db, apply=True)
    assert capture(repair_db) == before
