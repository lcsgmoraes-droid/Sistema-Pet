import json
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.saneamento_caixa_bancario import sanear_movimentos_100x
from app.scripts import sanear_caixa_bancario_100x


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
                valor_pago NUMERIC(10, 2) NOT NULL
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
              (2, :tenant_alvo, 'Santander', -11067.00),
              (3, :tenant_alvo, 'Stone', -999.00),
              (4, :tenant_outro, 'Santander outro tenant', -6840.00)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar (id, tenant_id, valor_pago)
            VALUES
              (10, :tenant_alvo, 68.40),
              (11, :tenant_alvo, 42.17),
              (12, :tenant_alvo, 10.00),
              (20, :tenant_outro, 68.40)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_financeiras (
                id, tenant_id, conta_bancaria_id, tipo, valor, origem_tipo, origem_id, observacoes
            )
            VALUES
              (100, :tenant_alvo, 2, 'saida', 6840.00, 'conta_pagar', 10, NULL),
              (101, :tenant_alvo, 2, 'saida', 4217.00, 'conta_pagar', 11, 'manual'),
              (102, :tenant_alvo, 2, 'saida', 10.00, 'conta_pagar', 12, NULL),
              (103, :tenant_alvo, 3, 'saida', 6840.00, 'conta_pagar', 10, NULL),
              (200, :tenant_outro, 4, 'saida', 6840.00, 'conta_pagar', 20, NULL)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.commit()
    return db


def _scalar_decimal(db, sql: str, params: dict | None = None) -> Decimal:
    value = db.execute(text(sql), params or {}).scalar_one()
    return Decimal(str(value)).quantize(Decimal("0.01"))


def test_saneamento_dry_run_identifica_apenas_conta_e_tenant_alvo_sem_persistir():
    db = _session()

    resultado = sanear_movimentos_100x(
        db,
        tenant_id=TENANT_ALVO,
        conta_bancaria_id=2,
        apply_changes=False,
    )

    assert resultado["dry_run"] is True
    assert resultado["resumo"]["movimentos_candidatos"] == 2
    assert resultado["resumo"]["valor_movimentos_antes"] == "11057.00"
    assert resultado["resumo"]["valor_movimentos_depois"] == "110.57"
    assert resultado["contas"][0]["saldo_atual_antes"] == "-11067.00"
    assert resultado["contas"][0]["saldo_atual_depois"] == "-120.57"
    assert {mov["movimentacao_id"] for mov in resultado["movimentos"]} == {100, 101}

    saldo = _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 2 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    )
    valor_movimento = _scalar_decimal(
        db,
        "SELECT valor FROM movimentacoes_financeiras WHERE id = 100",
    )
    assert saldo == Decimal("-11067.00")
    assert valor_movimento == Decimal("6840.00")
    db.close()


def test_saneamento_apply_normaliza_movimentos_e_recalcula_saldo_da_conta():
    db = _session()

    resultado = sanear_movimentos_100x(
        db,
        tenant_id=TENANT_ALVO,
        conta_bancaria_id=2,
        apply_changes=True,
        confirm_token="NORMALIZAR_CAIXA_100X",
    )

    assert resultado["dry_run"] is False
    assert resultado["applied"] is True
    assert resultado["resumo"]["movimentos_candidatos"] == 2
    assert resultado["contas"][0]["saldo_atual_depois"] == "-120.57"

    saldo_alvo = _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 2 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    )
    saldo_outra_conta_mesmo_tenant = _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 3 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    )
    saldo_outro_tenant = _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 4 AND tenant_id = :tenant",
        {"tenant": TENANT_OUTRO},
    )
    valor_corrigido = _scalar_decimal(
        db,
        "SELECT valor FROM movimentacoes_financeiras WHERE id = 100",
    )
    valor_normal = _scalar_decimal(
        db,
        "SELECT valor FROM movimentacoes_financeiras WHERE id = 102",
    )

    assert saldo_alvo == Decimal("-120.57")
    assert saldo_outra_conta_mesmo_tenant == Decimal("-999.00")
    assert saldo_outro_tenant == Decimal("-6840.00")
    assert valor_corrigido == Decimal("68.40")
    assert valor_normal == Decimal("10.00")
    db.close()


def test_saneamento_apply_exige_token_de_confirmacao():
    db = _session()

    resultado = sanear_movimentos_100x(
        db,
        tenant_id=TENANT_ALVO,
        conta_bancaria_id=2,
        apply_changes=True,
    )

    assert resultado["ok"] is False
    assert "confirm_token" in resultado["error"]
    saldo = _scalar_decimal(
        db,
        "SELECT saldo_atual FROM contas_bancarias WHERE id = 2 AND tenant_id = :tenant",
        {"tenant": TENANT_ALVO},
    )
    assert saldo == Decimal("-11067.00")
    db.close()


def test_cli_saneamento_dry_run_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(sanear_caixa_bancario_100x, "SessionLocal", lambda: db)

    code = sanear_caixa_bancario_100x.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--conta-bancaria-id",
            "2",
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["resumo"]["movimentos_candidatos"] == 2


def test_cli_saneamento_bloqueia_apply_em_producao_sem_override(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = sanear_caixa_bancario_100x.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--conta-bancaria-id",
            "2",
            "--expected-saldo-atual",
            "-11067.00",
            "--apply",
            "--confirm-token",
            "NORMALIZAR_CAIXA_100X",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "production/prod" in captured.err
