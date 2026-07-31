import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.reversao_virada_transferencia_parceiro import (
    CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO,
    OBSERVACAO_VIRADA_RECEBIMENTO,
    reverter_virada_transferencia_parceiro,
)
from app.scripts import (
    reverter_virada_transferencia_parceiro as reversao_cli,
)


TENANT_ALVO = "11111111-1111-1111-1111-111111111111"
TENANT_OUTRO = "22222222-2222-2222-2222-222222222222"


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db = sessionmaker(bind=engine)()
    db.execute(
        text(
            """
            CREATE TABLE contas_receber (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                cliente_id INTEGER,
                documento TEXT,
                descricao TEXT NOT NULL,
                canal TEXT NOT NULL,
                status TEXT NOT NULL,
                valor_final NUMERIC(10, 2) NOT NULL,
                valor_recebido NUMERIC(10, 2) NOT NULL,
                data_vencimento TEXT NOT NULL,
                data_recebimento TEXT,
                observacoes TEXT
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
                valor_recebido NUMERIC(10, 2) NOT NULL,
                data_recebimento TEXT NOT NULL,
                observacoes TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO contas_receber (
                id, tenant_id, cliente_id, documento, descricao, canal, status,
                valor_final, valor_recebido, data_vencimento, data_recebimento,
                observacoes
            ) VALUES
              (10, :tenant, 1, 'TRP-10', 'Parceiro A', 'transferencia_parceiro',
               'recebido', 100.00, 100.00, '2026-07-05', '2026-07-05', 'original'),
              (11, :tenant, 2, 'TRP-11', 'Parceiro B', 'transferencia_parceiro',
               'recebido', 80.00, 80.00, '2026-07-05', '2026-07-30', NULL),
              (12, :tenant, 3, 'FIN-12', 'Financeiro', 'financeiro',
               'recebido', 40.00, 40.00, '2026-07-05', '2026-07-05', NULL),
              (13, :outro, 4, 'TRP-13', 'Outro tenant', 'transferencia_parceiro',
               'recebido', 90.00, 90.00, '2026-07-05', '2026-07-05', NULL)
            """
        ),
        {"tenant": TENANT_ALVO, "outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            INSERT INTO recebimentos (
                id, tenant_id, conta_receber_id, valor_recebido,
                data_recebimento, observacoes
            ) VALUES
              (100, :tenant, 10, 100.00, '2026-07-05', :marker),
              (101, :tenant, 11, 30.00, '2026-07-05', :marker),
              (102, :tenant, 11, 50.00, '2026-07-30', 'Recebimento normal'),
              (103, :tenant, 12, 40.00, '2026-07-05', :marker),
              (104, :outro, 13, 90.00, '2026-07-05', :marker)
            """
        ),
        {
            "tenant": TENANT_ALVO,
            "outro": TENANT_OUTRO,
            "marker": OBSERVACAO_VIRADA_RECEBIMENTO,
        },
    )
    db.commit()
    return db


def test_dry_run_isola_transferencias_e_nao_persiste():
    db = _session()

    result = reverter_virada_transferencia_parceiro(
        db,
        tenant_id=TENANT_ALVO,
        data_virada=date(2026, 7, 5),
    )

    assert result["dry_run"] is True
    assert result["resumo"] == {
        "recebimentos_revertidos": 2,
        "contas_reabertas": 2,
        "valor_reaberto": "130.00",
        "movimentacoes_bancarias_alteradas": 0,
    }
    assert db.execute(text("SELECT COUNT(*) FROM recebimentos")).scalar_one() == 5
    db.close()


def test_apply_preserva_baixa_normal_e_recalcula_contas():
    db = _session()

    result = reverter_virada_transferencia_parceiro(
        db,
        tenant_id=TENANT_ALVO,
        data_virada=date(2026, 7, 5),
        apply=True,
        confirm_token=CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO,
        expected_count=2,
        expected_total=Decimal("130.00"),
    )

    assert result["ok"] is True
    assert result["applied"] is True
    conta_10 = db.execute(
        text(
            "SELECT valor_recebido, status, data_recebimento, observacoes "
            "FROM contas_receber WHERE id = 10"
        )
    ).mappings().one()
    assert Decimal(str(conta_10["valor_recebido"])) == Decimal("0.00")
    assert conta_10["status"] == "vencido"
    assert conta_10["data_recebimento"] is None
    assert "Reversao da virada bancaria" in conta_10["observacoes"]

    conta_11 = db.execute(
        text(
            "SELECT valor_recebido, status, data_recebimento "
            "FROM contas_receber WHERE id = 11"
        )
    ).mappings().one()
    assert Decimal(str(conta_11["valor_recebido"])) == Decimal("50.00")
    assert conta_11["status"] == "parcial"
    assert str(conta_11["data_recebimento"]) == "2026-07-30"
    assert db.execute(
        text("SELECT COUNT(*) FROM recebimentos WHERE id IN (100, 101)")
    ).scalar_one() == 0
    assert db.execute(text("SELECT COUNT(*) FROM recebimentos")).scalar_one() == 3

    second = reverter_virada_transferencia_parceiro(
        db,
        tenant_id=TENANT_ALVO,
        data_virada=date(2026, 7, 5),
    )
    assert second["resumo"]["recebimentos_revertidos"] == 0
    db.close()


def test_apply_bloqueia_token_ou_totais_divergentes():
    db = _session()
    sem_token = reverter_virada_transferencia_parceiro(
        db,
        tenant_id=TENANT_ALVO,
        data_virada=date(2026, 7, 5),
        apply=True,
        expected_count=2,
        expected_total=Decimal("130.00"),
    )
    assert sem_token["ok"] is False

    divergente = reverter_virada_transferencia_parceiro(
        db,
        tenant_id=TENANT_ALVO,
        data_virada=date(2026, 7, 5),
        apply=True,
        confirm_token=CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO,
        expected_count=39,
        expected_total=Decimal("18481.42"),
    )
    assert divergente["ok"] is False
    assert "Quantidade divergente" in divergente["error"]
    assert db.execute(text("SELECT COUNT(*) FROM recebimentos")).scalar_one() == 5
    db.close()


def test_cli_bloqueia_apply_em_producao_sem_override(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = reversao_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-virada",
            "2026-07-05",
            "--apply",
            "--expected-count",
            "2",
            "--expected-total",
            "130.00",
            "--confirm-token",
            CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO,
        ]
    )

    assert code == 1
    assert "production/prod" in capsys.readouterr().err


def test_cli_dry_run_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(reversao_cli, "SessionLocal", lambda: db)

    code = reversao_cli.main(
        [
            "--tenant-id",
            TENANT_ALVO,
            "--data-virada",
            "2026-07-05",
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["resumo"]["recebimentos_revertidos"] == 2
