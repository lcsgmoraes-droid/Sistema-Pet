import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.saneamento_baixas_historicas import (
    CONFIRM_TOKEN_BAIXAS_HISTORICAS,
    sanear_baixas_historicas_contas_pagar,
)
from app.scripts import sanear_baixas_historicas_contas_pagar as saneamento_cli


TENANT_ALVO = "11111111-1111-1111-1111-111111111111"
TENANT_OUTRO = "22222222-2222-2222-2222-222222222222"


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    db.execute(
        text(
            """
            CREATE TABLE contas_bancarias (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                saldo_atual NUMERIC(15, 2) NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE contas_pagar (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                status TEXT NOT NULL,
                valor_final NUMERIC(10, 2) NOT NULL,
                valor_pago NUMERIC(10, 2) NOT NULL,
                data_pagamento TEXT,
                user_id INTEGER NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE pagamentos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                conta_pagar_id INTEGER NOT NULL,
                forma_pagamento_id INTEGER,
                valor_pago NUMERIC(10, 2) NOT NULL,
                data_pagamento TEXT NOT NULL,
                observacoes TEXT,
                user_id INTEGER NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE movimentacoes_financeiras (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                conta_bancaria_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                valor NUMERIC(15, 2) NOT NULL,
                origem_tipo TEXT,
                origem_id INTEGER,
                observacoes TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO contas_bancarias (id, tenant_id, nome, saldo_atual)
            VALUES
              (1, :tenant_alvo, 'Santander', -110572.49),
              (2, :tenant_outro, 'Santander outro', 500.00)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                id, tenant_id, descricao, status, valor_final, valor_pago,
                data_pagamento, user_id
            )
            VALUES
              (10, :tenant_alvo, 'legacy sem baixa', 'pago', 80.00, 80.00, '2026-06-05', 7),
              (11, :tenant_alvo, 'legacy parcial', 'pago', 50.00, 50.00, '2026-06-06', 7),
              (12, :tenant_alvo, 'ja consistente', 'pago', 40.00, 40.00, '2026-06-07', 7),
              (13, :tenant_alvo, 'pendente', 'pendente', 25.00, 25.00, '2026-06-08', 7),
              (14, :tenant_alvo, 'fora periodo', 'pago', 15.00, 15.00, '2026-07-02', 7),
              (20, :tenant_outro, 'outro tenant', 'pago', 90.00, 90.00, '2026-06-05', 8)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO pagamentos (
                id, tenant_id, conta_pagar_id, valor_pago, data_pagamento,
                observacoes, user_id
            )
            VALUES
              (100, :tenant_alvo, 11, 20.00, '2026-06-06', 'baixa parcial existente', 7),
              (101, :tenant_alvo, 12, 40.00, '2026-06-07', 'baixa completa existente', 7)
            """
        ),
        {"tenant_alvo": TENANT_ALVO},
    )
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_financeiras (
                id, tenant_id, conta_bancaria_id, tipo, valor, origem_tipo, origem_id
            )
            VALUES
              (200, :tenant_alvo, 1, 'saida', 80.00, 'conta_pagar', 10)
            """
        ),
        {"tenant_alvo": TENANT_ALVO},
    )
    db.commit()
    return db


def _scalar_decimal(db, sql: str, params: dict | None = None) -> Decimal:
    value = db.execute(text(sql), params or {}).scalar_one()
    return Decimal(str(value)).quantize(Decimal("0.01"))


def test_saneamento_baixas_dry_run_planeja_sem_persistir():
    db = _session()

    resultado = sanear_baixas_historicas_contas_pagar(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=False,
    )

    assert resultado["dry_run"] is True
    assert resultado["resumo"]["pagamentos_candidatos"] == 2
    assert resultado["resumo"]["valor_pagamentos_planejado"] == "110.00"
    assert {item["conta_pagar_id"] for item in resultado["pagamentos"]} == {10, 11}
    assert db.execute(text("SELECT COUNT(*) FROM pagamentos")).scalar_one() == 2
    assert _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 1 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    ) == Decimal("-110572.49")
    db.close()


def test_saneamento_baixas_apply_cria_pagamentos_sem_movimentar_banco():
    db = _session()

    resultado = sanear_baixas_historicas_contas_pagar(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
        confirm_token=CONFIRM_TOKEN_BAIXAS_HISTORICAS,
    )

    assert resultado["applied"] is True
    assert resultado["resumo"]["pagamentos_candidatos"] == 2

    pagamentos = (
        db.execute(
            text(
                """
                SELECT conta_pagar_id, valor_pago, data_pagamento, observacoes
                FROM pagamentos
                WHERE tenant_id = :tenant
                ORDER BY id
                """
            ),
            {"tenant": TENANT_ALVO},
        )
        .mappings()
        .all()
    )
    assert [
        (
            row["conta_pagar_id"],
            Decimal(str(row["valor_pago"])).quantize(Decimal("0.01")),
        )
        for row in pagamentos
    ] == [
        (11, Decimal("20.00")),
        (12, Decimal("40.00")),
        (10, Decimal("80.00")),
        (11, Decimal("30.00")),
    ]
    assert "historico" in pagamentos[-1]["observacoes"].lower()

    assert (
        db.execute(text("SELECT COUNT(*) FROM movimentacoes_financeiras")).scalar_one()
        == 1
    )
    assert _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 1 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    ) == Decimal("-110572.49")

    segundo_dry_run = sanear_baixas_historicas_contas_pagar(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=False,
    )
    assert segundo_dry_run["resumo"]["pagamentos_candidatos"] == 0
    db.close()


def test_saneamento_baixas_apply_exige_token():
    db = _session()

    resultado = sanear_baixas_historicas_contas_pagar(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
    )

    assert resultado["ok"] is False
    assert "confirm_token" in resultado["error"]
    assert db.execute(text("SELECT COUNT(*) FROM pagamentos")).scalar_one() == 2
    db.close()


def test_cli_saneamento_baixas_bloqueia_apply_em_producao_sem_override(
    monkeypatch, capsys
):
    monkeypatch.setenv("APP_ENV", "production")

    code = saneamento_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-inicio",
            "2026-06-01",
            "--data-fim",
            "2026-07-01",
            "--apply",
            "--confirm-token",
            CONFIRM_TOKEN_BAIXAS_HISTORICAS,
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "production/prod" in captured.err


def test_cli_saneamento_baixas_dry_run_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(saneamento_cli, "SessionLocal", lambda: db)

    code = saneamento_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-inicio",
            "2026-06-01",
            "--data-fim",
            "2026-07-01",
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["resumo"]["pagamentos_candidatos"] == 2
    db.close()
