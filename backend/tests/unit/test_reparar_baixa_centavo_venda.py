"""Garante que o reparo pontual preserva a baixa e reabre apenas o centavo."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.scripts.reparar_baixa_centavo_venda_1335187 import TENANT_ID, reparar


def _cenario():
    db = Session(create_engine("sqlite:///:memory:"))
    for sql in (
        "CREATE TABLE vendas (id INTEGER, tenant_id TEXT, total NUMERIC, status TEXT)",
        "CREATE TABLE venda_pagamentos (id INTEGER, tenant_id TEXT, venda_id INTEGER, valor NUMERIC, status TEXT)",
        "CREATE TABLE contas_receber (id INTEGER, tenant_id TEXT, venda_id INTEGER, valor_final NUMERIC, valor_recebido NUMERIC, status TEXT, observacoes TEXT, data_recebimento TEXT, updated_at TEXT)",
        "CREATE TABLE recebimentos (id INTEGER, tenant_id TEXT, conta_receber_id INTEGER, valor_recebido NUMERIC, data_recebimento TEXT)",
        "CREATE TABLE fluxo_caixa (id INTEGER, tenant_id TEXT, origem_tipo TEXT, origem_id INTEGER, valor NUMERIC, status TEXT, atualizado_em TEXT)",
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, tenant_id TEXT, user_id INTEGER, action TEXT, entity_type TEXT, entity_id INTEGER, old_value TEXT, new_value TEXT, details TEXT, timestamp TEXT)",
    ):
        db.execute(text(sql))
    db.execute(
        text("INSERT INTO vendas VALUES (1335187, :tenant, 334.46, 'finalizada')"),
        {"tenant": TENANT_ID},
    )
    for pagamento_id, valor, status in (
        (234595, 168, "aprovado"),
        (238199, 166.45, "confirmado"),
    ):
        db.execute(
            text(
                "INSERT INTO venda_pagamentos VALUES (:id, :tenant, 1335187, :valor, :status)"
            ),
            {"id": pagamento_id, "tenant": TENANT_ID, "valor": valor, "status": status},
        )
    db.execute(
        text(
            "INSERT INTO contas_receber VALUES (10923, :tenant, 1335187, 166.46, 0, 'vencido', 'Conta original', NULL, NULL)"
        ),
        {"tenant": TENANT_ID},
    )
    db.execute(
        text(
            "INSERT INTO contas_receber VALUES (12563, :tenant, 1335187, 334.46, 334.45, 'pago', 'Criada automaticamente pela baixa em lote', '2026-10-03', NULL)"
        ),
        {"tenant": TENANT_ID},
    )
    db.execute(
        text(
            "INSERT INTO recebimentos VALUES (8680, :tenant, 12563, 166.45, '2026-10-03')"
        ),
        {"tenant": TENANT_ID},
    )
    db.execute(
        text(
            "INSERT INTO fluxo_caixa VALUES (504, :tenant, 'conta_receber', 12563, 166.45, 'realizado', NULL)"
        ),
        {"tenant": TENANT_ID},
    )
    db.commit()
    return db


def test_reparo_dry_run_e_aplicacao_preservam_recebimento():
    with _cenario() as db:
        plano = reparar(db)
        assert plano["aplicado"] is False
        assert (
            db.execute(text("SELECT status FROM vendas WHERE id=1335187")).scalar()
            == "finalizada"
        )

        resultado = reparar(db, aplicar=True)
        assert resultado["audit_id"]
        assert (
            db.execute(text("SELECT status FROM vendas WHERE id=1335187")).scalar()
            == "baixa_parcial"
        )
        assert (
            db.execute(
                text("SELECT valor_recebido FROM contas_receber WHERE id=10923")
            ).scalar()
            == 166.45
        )
        assert (
            db.execute(
                text("SELECT status FROM contas_receber WHERE id=12563")
            ).scalar()
            == "cancelado"
        )
        assert (
            db.execute(
                text("SELECT conta_receber_id FROM recebimentos WHERE id=8680")
            ).scalar()
            == 10923
        )
        assert (
            db.execute(text("SELECT origem_id FROM fluxo_caixa WHERE id=504")).scalar()
            == 10923
        )
        assert reparar(db, aplicar=True)["ja_aplicado"] is True


def test_reparo_recusa_registros_alterados():
    with _cenario() as db:
        db.execute(text("UPDATE contas_receber SET valor_recebido=10 WHERE id=10923"))
        db.commit()

        with pytest.raises(ValueError, match="Saldos ou status"):
            reparar(db, aplicar=True)
        assert (
            db.execute(text("SELECT status FROM vendas WHERE id=1335187")).scalar()
            == "finalizada"
        )
