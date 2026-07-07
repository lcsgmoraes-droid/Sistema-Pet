import json
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.auditoria_consistencia import auditar_financeiro_tenant
from app.scripts import auditar_financeiro_consistencia


TENANT = "11111111-1111-1111-1111-111111111111"
OUTRO_TENANT = "22222222-2222-2222-2222-222222222222"


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
            CREATE TABLE vendas (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                numero_venda TEXT,
                data_venda TEXT NOT NULL,
                total NUMERIC(12,2) NOT NULL,
                status TEXT NOT NULL
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
                venda_id INTEGER,
                valor_final NUMERIC(12,2) NOT NULL,
                status TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE notas_entrada (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                numero_nota TEXT,
                data_entrada TEXT NOT NULL,
                valor_total NUMERIC(12,2) NOT NULL,
                fornecedor_id INTEGER,
                status TEXT
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
                descricao TEXT,
                data_pagamento TEXT,
                status TEXT,
                valor_final NUMERIC(12,2) NOT NULL,
                valor_pago NUMERIC(12,2) NOT NULL,
                nota_entrada_id INTEGER,
                documento TEXT,
                observacoes TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE movimentacoes_caixa (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                tipo TEXT,
                valor NUMERIC(12,2) NOT NULL,
                descricao TEXT,
                categoria TEXT,
                documento TEXT,
                data_movimento TEXT
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
                conta_pagar_id INTEGER,
                valor_pago NUMERIC(12,2) NOT NULL
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
                origem_tipo TEXT,
                origem_id INTEGER,
                tipo TEXT,
                valor NUMERIC(12,2) NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO vendas (id, tenant_id, numero_venda, data_venda, total, status)
            VALUES
              (1, :tenant, 'V1', '2026-06-01', 200.00, 'finalizada'),
              (2, :tenant, 'V2', '2026-06-02', 50.00, 'finalizada'),
              (3, :tenant, 'V3', '2026-06-03', 20.00, 'finalizada'),
              (4, :outro, 'VX', '2026-06-01', 999.00, 'finalizada')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_receber (id, tenant_id, venda_id, valor_final, status)
            VALUES
              (10, :tenant, 1, 66.67, 'pendente'),
              (11, :tenant, 1, 66.67, 'pendente'),
              (12, :tenant, 1, 66.67, 'pendente'),
              (13, :tenant, 3, 10.00, 'pendente'),
              (14, :outro, 4, 999.00, 'pendente')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO notas_entrada (
                id, tenant_id, numero_nota, data_entrada, valor_total, fornecedor_id, status
            )
            VALUES
              (100, :tenant, 'N1', '2026-06-04', 123.45, 7, 'processada'),
              (101, :outro, 'NX', '2026-06-04', 999.99, 8, 'processada')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                id, tenant_id, descricao, data_pagamento, status, valor_final, valor_pago,
                nota_entrada_id, documento, observacoes
            )
            VALUES
              (200, :tenant, 'legacy paid', '2026-06-05', 'pago', 80.00, 80.00, NULL, '', ''),
              (201, :tenant, 'ok paid', '2026-06-06', 'pago', 20.00, 20.00, NULL, '', ''),
              (203, :tenant, 'Despesa rapida caixa', '2026-06-07', 'pago', 42.50, 42.50, NULL, '', 'Gerada automaticamente pelo PDV (Caixa #12)'),
              (202, :outro, 'outro', '2026-06-05', 'pago', 90.00, 90.00, NULL, '', '')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_caixa (
                id, tenant_id, tipo, valor, descricao, categoria, documento, data_movimento
            )
            VALUES (
                400, :tenant, 'despesa', 42.50, 'Despesa rapida caixa', 'Outros', '', '2026-06-07 09:00:00'
            )
            """
        ),
        {"tenant": TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO pagamentos (id, tenant_id, conta_pagar_id, valor_pago)
            VALUES (300, :tenant, 201, 20.00)
            """
        ),
        {"tenant": TENANT},
    )
    db.commit()
    return db


def test_auditoria_financeira_classifica_inconsistencias_por_tenant_e_periodo():
    db = _session()

    resultado = auditar_financeiro_tenant(
        db,
        tenant_id=TENANT,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
    )

    vendas = resultado["vendas_contas_receber"]
    assert vendas["sem_contas_receber"]["quantidade"] == 1
    assert vendas["diferencas_centavos"]["quantidade"] == 1
    assert vendas["divergencias_maiores"]["quantidade"] == 1

    notas = resultado["notas_entrada_contas_pagar"]
    assert notas["sem_contas_pagar"]["quantidade"] == 1
    assert notas["sem_contas_pagar"]["valor_total"] == "123.45"

    contas_pagar = resultado["contas_pagar_pagamentos"]
    assert contas_pagar["valor_pago_sem_pagamento"]["quantidade"] == 1
    assert contas_pagar["valor_pago_sem_pagamento"]["valor_total"] == "80.00"
    assert resultado["tenant_id"] == TENANT
    db.close()


def test_cli_auditoria_financeira_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(auditar_financeiro_consistencia, "SessionLocal", lambda: db)

    code = auditar_financeiro_consistencia.main(
        [
            "--tenant-id",
            TENANT,
            "--data-inicio",
            "2026-06-01",
            "--data-fim",
            "2026-07-01",
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["mode"] == "read_only"
    assert payload["vendas_contas_receber"]["sem_contas_receber"]["quantidade"] == 1
    db.close()
