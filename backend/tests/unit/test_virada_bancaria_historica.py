import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.virada_bancaria_historica import (
    CONFIRM_TOKEN_VIRADA_BANCARIA,
    executar_virada_bancaria_historica,
)
from app.scripts import virada_bancaria_historica as virada_cli


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
                saldo_inicial NUMERIC(15, 2) NOT NULL,
                saldo_atual NUMERIC(15, 2) NOT NULL,
                observacoes TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE contas_receber (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                status TEXT NOT NULL,
                valor_final NUMERIC(10, 2) NOT NULL,
                valor_recebido NUMERIC(10, 2) NOT NULL,
                data_vencimento TEXT NOT NULL,
                data_recebimento TEXT,
                forma_pagamento_id INTEGER,
                user_id INTEGER NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE recebimentos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                conta_receber_id INTEGER NOT NULL,
                forma_pagamento_id INTEGER,
                valor_recebido NUMERIC(10, 2) NOT NULL,
                data_recebimento TEXT NOT NULL,
                observacoes TEXT,
                user_id INTEGER NOT NULL
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
                data_vencimento TEXT NOT NULL,
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
                origem_id INTEGER
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO contas_bancarias (
                id, tenant_id, nome, saldo_inicial, saldo_atual, observacoes
            )
            VALUES
              (2, :tenant_alvo, 'Santander', -1000.00, -110572.49, 'saldo antigo'),
              (3, :tenant_outro, 'Santander outro', 0.00, 500.00, NULL)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_receber (
                id, tenant_id, descricao, status, valor_final, valor_recebido,
                data_vencimento, data_recebimento, forma_pagamento_id, user_id
            )
            VALUES
              (10, :tenant_alvo, 'CR aberto', 'pendente', 100.00, 0.00, '2026-07-05', NULL, 2, 7),
              (11, :tenant_alvo, 'CR parcial', 'parcial', 50.00, 20.00, '2026-06-30', NULL, 2, 7),
              (12, :tenant_alvo, 'CR futuro', 'pendente', 90.00, 0.00, '2026-07-06', NULL, 2, 7),
              (13, :tenant_alvo, 'CR recebido', 'recebido', 40.00, 40.00, '2026-07-04', '2026-07-04', 2, 7),
              (14, :tenant_outro, 'CR outro', 'pendente', 999.00, 0.00, '2026-07-05', NULL, 2, 8)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                id, tenant_id, descricao, status, valor_final, valor_pago,
                data_vencimento, data_pagamento, user_id
            )
            VALUES
              (20, :tenant_alvo, 'CP aberto', 'pendente', 80.00, 0.00, '2026-07-05', NULL, 7),
              (21, :tenant_alvo, 'CP parcial', 'parcial', 70.00, 30.00, '2026-06-30', NULL, 7),
              (22, :tenant_alvo, 'CP futuro', 'pendente', 700.00, 0.00, '2026-07-06', NULL, 7),
              (23, :tenant_alvo, 'CP pago', 'pago', 60.00, 60.00, '2026-07-04', '2026-07-04', 7),
              (24, :tenant_outro, 'CP outro', 'pendente', 888.00, 0.00, '2026-07-05', NULL, 8)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_financeiras (
                id, tenant_id, conta_bancaria_id, tipo, valor, origem_tipo, origem_id
            )
            VALUES (100, :tenant_alvo, 2, 'saida', 10.00, 'manual', 1)
            """
        ),
        {"tenant_alvo": TENANT_ALVO},
    )
    db.commit()
    return db


def _decimal(db, sql: str, params: dict | None = None) -> Decimal:
    value = db.execute(text(sql), params or {}).scalar_one()
    return Decimal(str(value)).quantize(Decimal("0.01"))


def test_virada_dry_run_planeja_baixas_e_saldo_sem_persistir():
    db = _session()

    resultado = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
        conta_bancaria_id=2,
        saldo_real=Decimal("1234.56"),
        apply_baixas=False,
        apply_saldo=False,
    )

    assert resultado["dry_run"] is True
    assert resultado["resumo"]["contas_receber_baixadas"] == 2
    assert resultado["resumo"]["valor_receber_baixado"] == "130.00"
    assert resultado["resumo"]["contas_pagar_baixadas"] == 2
    assert resultado["resumo"]["valor_pagar_baixado"] == "120.00"
    assert resultado["resumo"]["movimentacoes_criadas"] == 0
    assert resultado["resumo"]["saldo_bancario_alterado"] is False
    assert resultado["saldo_bancario"]["saldo_atual_antes"] == "-110572.49"
    assert resultado["saldo_bancario"]["saldo_atual_depois"] == "1234.56"

    assert db.execute(text("SELECT COUNT(*) FROM recebimentos")).scalar_one() == 0
    assert db.execute(text("SELECT COUNT(*) FROM pagamentos")).scalar_one() == 0
    assert _decimal(
        db, "SELECT saldo_atual FROM contas_bancarias WHERE id = 2"
    ) == Decimal("-110572.49")
    db.close()


def test_virada_apply_baixas_nao_movimenta_banco_nem_altera_saldo():
    db = _session()

    resultado = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
        apply_baixas=True,
        confirm_token=CONFIRM_TOKEN_VIRADA_BANCARIA,
    )

    assert resultado["applied"]["baixas"] is True
    assert resultado["applied"]["saldo"] is False

    recebimentos = (
        db.execute(
            text(
                """
                SELECT conta_receber_id, valor_recebido, data_recebimento
                FROM recebimentos
                WHERE tenant_id = :tenant
                ORDER BY conta_receber_id
                """
            ),
            {"tenant": TENANT_ALVO},
        )
        .mappings()
        .all()
    )
    assert [
        (
            row["conta_receber_id"],
            Decimal(str(row["valor_recebido"])).quantize(Decimal("0.01")),
        )
        for row in recebimentos
    ] == [(10, Decimal("100.00")), (11, Decimal("30.00"))]
    assert {str(row["data_recebimento"]) for row in recebimentos} == {"2026-07-05"}

    pagamentos = (
        db.execute(
            text(
                """
                SELECT conta_pagar_id, valor_pago, data_pagamento
                FROM pagamentos
                WHERE tenant_id = :tenant
                ORDER BY conta_pagar_id
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
    ] == [(20, Decimal("80.00")), (21, Decimal("40.00"))]
    assert {str(row["data_pagamento"]) for row in pagamentos} == {"2026-07-05"}

    assert _decimal(
        db, "SELECT valor_recebido FROM contas_receber WHERE id = 11"
    ) == Decimal("50.00")
    assert _decimal(db, "SELECT valor_pago FROM contas_pagar WHERE id = 21") == Decimal(
        "70.00"
    )
    assert (
        db.execute(text("SELECT COUNT(*) FROM movimentacoes_financeiras")).scalar_one()
        == 1
    )
    assert _decimal(
        db, "SELECT saldo_atual FROM contas_bancarias WHERE id = 2"
    ) == Decimal("-110572.49")

    segundo_dry_run = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
    )
    assert segundo_dry_run["resumo"]["contas_receber_baixadas"] == 0
    assert segundo_dry_run["resumo"]["contas_pagar_baixadas"] == 0
    db.close()


def test_virada_apply_saldo_exige_saldo_esperado_e_token():
    db = _session()

    sem_token = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
        conta_bancaria_id=2,
        saldo_real=Decimal("1234.56"),
        expected_saldo_atual=Decimal("-110572.49"),
        apply_saldo=True,
    )

    assert sem_token["ok"] is False
    assert "confirm_token" in sem_token["error"]

    divergente = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
        conta_bancaria_id=2,
        saldo_real=Decimal("1234.56"),
        expected_saldo_atual=Decimal("0.00"),
        apply_saldo=True,
        confirm_token=CONFIRM_TOKEN_VIRADA_BANCARIA,
    )

    assert divergente["ok"] is False
    assert "Saldo atual divergente" in divergente["error"]
    assert _decimal(
        db, "SELECT saldo_atual FROM contas_bancarias WHERE id = 2"
    ) == Decimal("-110572.49")
    db.close()


def test_virada_apply_saldo_atualiza_conta_sem_movimentacao():
    db = _session()

    resultado = executar_virada_bancaria_historica(
        db,
        tenant_id=TENANT_ALVO,
        data_corte=date(2026, 7, 5),
        conta_bancaria_id=2,
        saldo_real=Decimal("1234.56"),
        expected_saldo_atual=Decimal("-110572.49"),
        apply_saldo=True,
        confirm_token=CONFIRM_TOKEN_VIRADA_BANCARIA,
    )

    assert resultado["applied"]["saldo"] is True
    assert resultado["saldo_bancario"]["saldo_atual_depois"] == "1234.56"
    assert _decimal(
        db, "SELECT saldo_atual FROM contas_bancarias WHERE id = 2"
    ) == Decimal("1234.56")
    assert _decimal(
        db, "SELECT saldo_inicial FROM contas_bancarias WHERE id = 2"
    ) == Decimal("1234.56")
    assert (
        db.execute(text("SELECT COUNT(*) FROM movimentacoes_financeiras")).scalar_one()
        == 1
    )
    db.close()


def test_cli_virada_bloqueia_apply_em_producao_sem_override(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = virada_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-corte",
            "2026-07-05",
            "--apply-baixas",
            "--confirm-token",
            CONFIRM_TOKEN_VIRADA_BANCARIA,
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "production/prod" in captured.err


def test_cli_virada_dry_run_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(virada_cli, "SessionLocal", lambda: db)

    code = virada_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-corte",
            "2026-07-05",
            "--conta-bancaria-id",
            "2",
            "--saldo-real",
            "1234.56",
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["resumo"]["contas_receber_baixadas"] == 2
    db.close()
