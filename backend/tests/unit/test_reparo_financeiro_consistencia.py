import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.reparos_consistencia import (
    CONFIRM_TOKEN_REPARO_FINANCEIRO,
    _is_recebimento_imediato,
    reparar_financeiro_consistencia,
)
from app.scripts import reparar_financeiro_consistencia as reparar_cli


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
                numero_venda TEXT NOT NULL,
                cliente_id INTEGER,
                vendedor_id INTEGER,
                user_id INTEGER NOT NULL,
                data_venda TEXT NOT NULL,
                total NUMERIC(10,2) NOT NULL,
                status TEXT NOT NULL,
                canal TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE venda_pagamentos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                venda_id INTEGER NOT NULL,
                forma_pagamento TEXT NOT NULL,
                valor NUMERIC(10,2) NOT NULL,
                numero_parcelas INTEGER,
                status TEXT,
                data_pagamento TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE formas_pagamento (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                prazo_dias INTEGER,
                prazo_recebimento INTEGER
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
                cliente_id INTEGER,
                categoria_id INTEGER,
                forma_pagamento_id INTEGER,
                dre_subcategoria_id INTEGER NOT NULL,
                canal TEXT NOT NULL,
                valor_original NUMERIC(10,2) NOT NULL,
                valor_recebido NUMERIC(10,2) NOT NULL DEFAULT 0,
                valor_desconto NUMERIC(10,2) NOT NULL DEFAULT 0,
                valor_juros NUMERIC(10,2) NOT NULL DEFAULT 0,
                valor_multa NUMERIC(10,2) NOT NULL DEFAULT 0,
                valor_final NUMERIC(10,2) NOT NULL,
                data_emissao TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                data_recebimento TEXT,
                status TEXT NOT NULL,
                conciliado BOOLEAN NOT NULL,
                eh_parcelado BOOLEAN,
                numero_parcela INTEGER,
                total_parcelas INTEGER,
                venda_id INTEGER,
                documento TEXT,
                observacoes TEXT,
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
                valor_recebido NUMERIC(10,2) NOT NULL,
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
            CREATE TABLE notas_entrada (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                numero_nota TEXT NOT NULL,
                fornecedor_id INTEGER,
                data_emissao TEXT NOT NULL,
                data_entrada TEXT NOT NULL,
                valor_total NUMERIC(10,2) NOT NULL,
                xml_content TEXT,
                status TEXT NOT NULL,
                percentual_online NUMERIC(5,2),
                percentual_loja NUMERIC(5,2),
                user_id INTEGER NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE tipo_despesas (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT 1
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
                fornecedor_id INTEGER,
                tipo_despesa_id INTEGER,
                descricao TEXT NOT NULL,
                valor_original NUMERIC(10,2) NOT NULL,
                valor_final NUMERIC(10,2) NOT NULL,
                valor_pago NUMERIC(10,2) NOT NULL DEFAULT 0,
                data_emissao TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT NOT NULL,
                eh_parcelado BOOLEAN,
                numero_parcela INTEGER,
                total_parcelas INTEGER,
                dre_subcategoria_id INTEGER,
                nota_entrada_id INTEGER,
                nfe_numero TEXT,
                documento TEXT,
                afeta_dre BOOLEAN NOT NULL DEFAULT 1,
                percentual_online NUMERIC(5,2),
                percentual_loja NUMERIC(5,2),
                user_id INTEGER NOT NULL
            )
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO vendas (
                id, tenant_id, numero_venda, cliente_id, vendedor_id, user_id,
                data_venda, total, status, canal
            )
            VALUES
              (1, :tenant, 'V-SCR', 10, 99, 99, '2026-06-05 10:00:00', 100.00, 'finalizada', 'loja_fisica'),
              (2, :tenant, 'V-CENT', 11, 99, 99, '2026-06-06 10:00:00', 30.02, 'finalizada', 'loja_fisica'),
              (3, :tenant, 'V-RECEBIDA', 12, 99, 99, '2026-06-07 10:00:00', 20.00, 'finalizada', 'loja_fisica'),
              (4, :outro, 'V-OUTRO', 13, 88, 88, '2026-06-05 10:00:00', 99.00, 'finalizada', 'loja_fisica')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO venda_pagamentos (
                id, tenant_id, venda_id, forma_pagamento, valor,
                numero_parcelas, status, data_pagamento
            )
            VALUES
              (10, :tenant, 1, 'pix', 100.00, 1, 'confirmado', '2026-07-02 09:00:00'),
              (11, :outro, 4, 'pix', 99.00, 1, 'confirmado', '2026-07-02 09:00:00')
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO formas_pagamento (
                id, tenant_id, nome, tipo, prazo_dias, prazo_recebimento
            )
            VALUES
              (7, :tenant, 'Pix', 'pix', 0, 0),
              (8, :outro, 'Pix', 'pix', 0, 0)
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO contas_receber (
                id, tenant_id, descricao, cliente_id, forma_pagamento_id,
                dre_subcategoria_id, canal, valor_original, valor_recebido,
                valor_final, data_emissao, data_vencimento, status, eh_parcelado,
                conciliado, numero_parcela, total_parcelas, venda_id, documento,
                user_id
            )
            VALUES
              (20, :tenant, 'parcela 1', 11, 7, 1, 'loja_fisica', 10.01, 0, 10.01, '2026-06-06', '2026-07-06', 'pendente', 0, 1, 1, 3, 2, 'VENDA-2', 99),
              (21, :tenant, 'parcela 2', 11, 7, 1, 'loja_fisica', 10.01, 0, 10.01, '2026-06-06', '2026-08-05', 'pendente', 0, 1, 2, 3, 2, 'VENDA-2', 99),
              (22, :tenant, 'parcela 3', 11, 7, 1, 'loja_fisica', 10.01, 0, 10.01, '2026-06-06', '2026-09-04', 'pendente', 0, 1, 3, 3, 2, 'VENDA-2', 99),
              (30, :tenant, 'recebida 1', 12, 7, 1, 'loja_fisica', 10.01, 10.01, 10.01, '2026-06-07', '2026-06-07', 'recebido', 0, 1, 1, 2, 3, 'VENDA-3', 99),
              (31, :tenant, 'recebida 2', 12, 7, 1, 'loja_fisica', 10.00, 10.00, 10.00, '2026-06-07', '2026-06-07', 'recebido', 0, 1, 2, 2, 3, 'VENDA-3', 99)
            """
        ),
        {"tenant": TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO recebimentos (
                id, tenant_id, conta_receber_id, forma_pagamento_id,
                valor_recebido, data_recebimento, observacoes, user_id
            )
            VALUES
              (40, :tenant, 30, 7, 10.01, '2026-06-07', 'ja recebido', 99),
              (41, :tenant, 31, 7, 10.00, '2026-06-07', 'ja recebido', 99)
            """
        ),
        {"tenant": TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO notas_entrada (
                id, tenant_id, numero_nota, fornecedor_id, data_emissao,
                data_entrada, valor_total, xml_content, status,
                percentual_online, percentual_loja, user_id
            )
            VALUES
              (100, :tenant, 'N-PROC', 50, '2026-06-10', '2026-06-11', 123.45, '<xml/>', 'processada', 0, 100, 99),
              (101, :tenant, 'N-PEND', 51, '2026-06-12', '2026-06-13', 88.00, '<xml/>', 'pendente', 0, 100, 99),
              (102, :outro, 'N-OUTRO', 52, '2026-06-10', '2026-06-11', 77.00, '<xml/>', 'processada', 0, 100, 88)
            """
        ),
        {"tenant": TENANT, "outro": OUTRO_TENANT},
    )
    db.execute(
        text(
            """
            INSERT INTO tipo_despesas (id, tenant_id, nome, ativo)
            VALUES (70, :tenant, 'Produto para Revenda', 1)
            """
        ),
        {"tenant": TENANT},
    )
    db.commit()
    return db


def _decimal_scalar(db, sql: str, params: dict | None = None) -> Decimal:
    return Decimal(str(db.execute(text(sql), params or {}).scalar_one())).quantize(
        Decimal("0.01")
    )


def _fake_parse_xml(xml_content: str):
    assert xml_content == "<xml/>"
    return {
        "duplicatas": [
            {"numero": "001", "vencimento": date(2026, 7, 10), "valor": 50.00},
            {"numero": "002", "vencimento": date(2026, 8, 10), "valor": 73.45},
        ]
    }


def test_reparo_financeiro_dry_run_planeja_sem_persistir(monkeypatch):
    db = _session()
    monkeypatch.setattr(
        "app.financeiro.reparos_consistencia.parse_nfe_xml", _fake_parse_xml
    )

    resultado = reparar_financeiro_consistencia(
        db,
        tenant_id=TENANT,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=False,
    )

    assert resultado["dry_run"] is True
    assert resultado["resumo"]["contas_receber_criadas"] == 1
    assert resultado["resumo"]["recebimentos_criados"] == 1
    assert resultado["resumo"]["ajustes_centavos_aplicaveis"] == 1
    assert resultado["resumo"]["ajustes_centavos_pulados"] == 1
    assert resultado["resumo"]["contas_pagar_criadas"] == 2
    assert resultado["resumo"]["notas_puladas"] == 1

    assert _decimal_scalar(
        db, "SELECT valor_final FROM contas_receber WHERE id = 22"
    ) == Decimal("10.01")
    assert (
        db.execute(
            text("SELECT COUNT(*) FROM contas_receber WHERE venda_id = 1")
        ).scalar_one()
        == 0
    )
    assert (
        db.execute(
            text("SELECT COUNT(*) FROM contas_pagar WHERE nota_entrada_id = 100")
        ).scalar_one()
        == 0
    )
    db.close()


def test_reparo_financeiro_apply_corrige_apenas_tenant_alvo(monkeypatch):
    db = _session()
    monkeypatch.setattr(
        "app.financeiro.reparos_consistencia.parse_nfe_xml", _fake_parse_xml
    )

    resultado = reparar_financeiro_consistencia(
        db,
        tenant_id=TENANT,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
        confirm_token=CONFIRM_TOKEN_REPARO_FINANCEIRO,
    )

    assert resultado["applied"] is True
    assert resultado["resumo"]["contas_receber_criadas"] == 1
    assert resultado["resumo"]["contas_pagar_criadas"] == 2

    nova_cr = (
        db.execute(
            text(
                """
            SELECT status, valor_final, valor_recebido, data_emissao,
                   data_vencimento, data_recebimento, forma_pagamento_id
            FROM contas_receber
            WHERE venda_id = 1 AND tenant_id = :tenant
            """
            ),
            {"tenant": TENANT},
        )
        .mappings()
        .one()
    )
    assert nova_cr["status"] == "recebido"
    assert Decimal(str(nova_cr["valor_final"])) == Decimal("100")
    assert Decimal(str(nova_cr["valor_recebido"])) == Decimal("100")
    assert str(nova_cr["data_emissao"]) == "2026-06-05"
    assert str(nova_cr["data_recebimento"]) == "2026-07-02"
    assert nova_cr["forma_pagamento_id"] == 7

    assert (
        db.execute(
            text("SELECT COUNT(*) FROM recebimentos WHERE tenant_id = :tenant"),
            {"tenant": TENANT},
        ).scalar_one()
        == 3
    )
    assert _decimal_scalar(
        db, "SELECT valor_final FROM contas_receber WHERE id = 22"
    ) == Decimal("10.00")
    assert _decimal_scalar(
        db, "SELECT valor_original FROM contas_receber WHERE id = 22"
    ) == Decimal("10.00")

    cps = (
        db.execute(
            text(
                """
            SELECT
                valor_final, data_vencimento, numero_parcela, total_parcelas,
                dre_subcategoria_id, afeta_dre
            FROM contas_pagar
            WHERE nota_entrada_id = 100 AND tenant_id = :tenant
            ORDER BY numero_parcela
            """
            ),
            {"tenant": TENANT},
        )
        .mappings()
        .all()
    )
    assert [Decimal(str(row["valor_final"])) for row in cps] == [
        Decimal("50"),
        Decimal("73.45"),
    ]
    assert [str(row["data_vencimento"]) for row in cps] == [
        "2026-07-10",
        "2026-08-10",
    ]
    assert [row["dre_subcategoria_id"] for row in cps] == [None, None]
    assert [bool(row["afeta_dre"]) for row in cps] == [False, False]

    assert (
        db.execute(
            text("SELECT COUNT(*) FROM contas_pagar WHERE nota_entrada_id = 101")
        ).scalar_one()
        == 0
    )
    assert (
        db.execute(
            text("SELECT COUNT(*) FROM contas_receber WHERE tenant_id = :tenant"),
            {"tenant": OUTRO_TENANT},
        ).scalar_one()
        == 0
    )
    db.close()


def test_reparo_financeiro_apply_exige_token(monkeypatch):
    db = _session()
    monkeypatch.setattr(
        "app.financeiro.reparos_consistencia.parse_nfe_xml", _fake_parse_xml
    )

    resultado = reparar_financeiro_consistencia(
        db,
        tenant_id=TENANT,
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 7, 1),
        apply_changes=True,
    )

    assert resultado["ok"] is False
    assert "confirm_token" in resultado["error"]
    assert (
        db.execute(
            text("SELECT COUNT(*) FROM contas_receber WHERE venda_id = 1")
        ).scalar_one()
        == 0
    )
    db.close()


def test_cli_reparo_bloqueia_apply_em_producao_sem_override(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = reparar_cli.main(
        [
            "--tenant-id",
            TENANT,
            "--data-inicio",
            "2026-06-01",
            "--data-fim",
            "2026-07-01",
            "--apply",
            "--confirm-token",
            CONFIRM_TOKEN_REPARO_FINANCEIRO,
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "production/prod" in captured.err


def test_cli_reparo_dry_run_emite_json(monkeypatch, capsys):
    db = _session()
    monkeypatch.setattr(reparar_cli, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        "app.financeiro.reparos_consistencia.parse_nfe_xml", _fake_parse_xml
    )

    code = reparar_cli.main(
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

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["resumo"]["contas_receber_criadas"] == 1
    db.close()


def test_forma_desconhecida_nao_e_recebimento_imediato():
    assert (
        _is_recebimento_imediato(
            forma_nome="boleto_sem_cadastro",
            forma=None,
            numero_parcelas=1,
        )
        is False
    )
