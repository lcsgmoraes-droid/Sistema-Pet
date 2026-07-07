import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.saneamento_nf_dre_historico import (
    CONFIRM_TOKEN_NF_DRE_HISTORICO,
    sanear_contas_pagar_nf_dre_historico,
)
from app.scripts import sanear_contas_pagar_nf_dre_historico as saneamento_cli


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
            CREATE TABLE contas_pagar (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                status TEXT NOT NULL,
                valor_final NUMERIC(10, 2) NOT NULL,
                data_emissao TEXT NOT NULL,
                nota_entrada_id INTEGER,
                nfe_numero TEXT,
                dre_subcategoria_id INTEGER,
                afeta_dre BOOLEAN NOT NULL DEFAULT 1,
                user_id INTEGER NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                id, tenant_id, descricao, status, valor_final, data_emissao,
                nota_entrada_id, nfe_numero, dre_subcategoria_id, afeta_dre, user_id
            )
            VALUES
              (10, :tenant_alvo, 'NF com DRE', 'pago', 100.00, '2026-06-10', 1000, '118340', 5, 1, 7),
              (11, :tenant_alvo, 'NF afeta DRE', 'pendente', 50.00, '2026-06-11', 1001, '118341', NULL, 1, 7),
              (12, :tenant_alvo, 'NF subcategoria antiga', 'pago', 25.00, '2026-06-12', 1002, '118342', 9, 0, 7),
              (13, :tenant_alvo, 'NF ja saneada', 'pago', 40.00, '2026-06-13', 1003, '118343', NULL, 0, 7),
              (14, :tenant_alvo, 'Despesa manual', 'pago', 30.00, '2026-06-14', NULL, 'NF-MANUAL', 8, 1, 7),
              (15, :tenant_alvo, 'NF fora periodo', 'pago', 70.00, '2026-07-02', 1004, '118344', 6, 1, 7),
              (20, :tenant_outro, 'Outro tenant', 'pago', 90.00, '2026-06-10', 2000, '218340', 5, 1, 8)
            """
        ),
        {"tenant_alvo": TENANT_ALVO, "tenant_outro": TENANT_OUTRO},
    )
    db.commit()
    return db


def _conta_flags(db, conta_id: int, tenant_id: str = TENANT_ALVO):
    return (
        db.execute(
            text(
                """
                SELECT dre_subcategoria_id, afeta_dre
                FROM contas_pagar
                WHERE id = :conta_id AND tenant_id = :tenant_id
                """
            ),
            {"conta_id": conta_id, "tenant_id": tenant_id},
        )
        .mappings()
        .one()
    )


def test_saneamento_nf_dre_dry_run_planeja_sem_persistir():
    db = _session()

    resultado = sanear_contas_pagar_nf_dre_historico(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=False,
    )

    assert resultado["dry_run"] is True
    assert resultado["resumo"]["contas_candidatas"] == 3
    assert resultado["resumo"]["valor_total"] == "175.00"
    assert resultado["resumo"]["saldo_bancario_alterado"] is False
    assert {item["conta_pagar_id"] for item in resultado["contas_pagar"]} == {
        10,
        11,
        12,
    }
    assert _conta_flags(db, 10)["dre_subcategoria_id"] == 5
    assert bool(_conta_flags(db, 10)["afeta_dre"]) is True
    db.close()


def test_saneamento_nf_dre_apply_blinda_apenas_nf_do_tenant_periodo():
    db = _session()

    resultado = sanear_contas_pagar_nf_dre_historico(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
        confirm_token=CONFIRM_TOKEN_NF_DRE_HISTORICO,
    )

    assert resultado["applied"] is True
    assert resultado["resumo"]["contas_candidatas"] == 3

    for conta_id in (10, 11, 12, 13):
        row = _conta_flags(db, conta_id)
        assert row["dre_subcategoria_id"] is None
        assert bool(row["afeta_dre"]) is False

    manual = _conta_flags(db, 14)
    assert manual["dre_subcategoria_id"] == 8
    assert bool(manual["afeta_dre"]) is True

    fora_periodo = _conta_flags(db, 15)
    assert fora_periodo["dre_subcategoria_id"] == 6
    assert bool(fora_periodo["afeta_dre"]) is True

    outro_tenant = _conta_flags(db, 20, TENANT_OUTRO)
    assert outro_tenant["dre_subcategoria_id"] == 5
    assert bool(outro_tenant["afeta_dre"]) is True

    segundo_dry_run = sanear_contas_pagar_nf_dre_historico(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=False,
    )
    assert segundo_dry_run["resumo"]["contas_candidatas"] == 0
    db.close()


def test_saneamento_nf_dre_apply_exige_token():
    db = _session()

    resultado = sanear_contas_pagar_nf_dre_historico(
        db,
        tenant_id=TENANT_ALVO,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
    )

    assert resultado["ok"] is False
    assert "confirm_token" in resultado["error"]
    assert _conta_flags(db, 10)["dre_subcategoria_id"] == 5
    db.close()


def test_cli_saneamento_nf_dre_bloqueia_apply_em_producao_sem_override(
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
            CONFIRM_TOKEN_NF_DRE_HISTORICO,
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "production/prod" in captured.err


def test_cli_saneamento_nf_dre_dry_run_emite_json(monkeypatch, capsys):
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
    assert payload["resumo"]["contas_candidatas"] == 3
    db.close()
