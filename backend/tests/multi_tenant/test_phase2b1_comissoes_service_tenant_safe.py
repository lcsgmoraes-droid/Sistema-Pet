from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.comissoes_service import buscar_configuracao_comissao, gerar_comissoes_venda
from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
FUNCIONARIO_ID = 77
PRODUTO_ID = 101
VENDA_ID = 500


@pytest.fixture()
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    _create_schema(session)
    _seed_base_data(session)

    import app.comissoes_provisao as comissoes_provisao

    def fake_provisionar_comissoes_venda(venda_id, tenant_id, db):
        result = db.execute(
            text("""
                INSERT INTO contas_pagar (tenant_id, descricao, valor_final)
                VALUES (:tenant_id, :descricao, :valor_final)
            """),
            {
                "tenant_id": str(tenant_id),
                "descricao": f"Comissao fake venda {venda_id}",
                "valor_final": 10.0,
            },
        )
        return {
            "success": True,
            "comissoes_provisionadas": 1,
            "valor_total": 10.0,
            "contas_criadas": [result.lastrowid],
            "message": "fake provisionada",
        }

    monkeypatch.setattr(
        comissoes_provisao,
        "provisionar_comissoes_venda",
        fake_provisionar_comissoes_venda,
    )

    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _create_schema(session):
    statements = [
        """
        CREATE TABLE vendas (
            id INTEGER NOT NULL,
            total NUMERIC,
            status TEXT,
            desconto_valor NUMERIC,
            taxa_entrega NUMERIC,
            tem_entrega BOOLEAN,
            data_venda TEXT,
            tenant_id TEXT NOT NULL,
            entregador_id INTEGER,
            valor_taxa_entregador NUMERIC
        )
        """,
        """
        CREATE TABLE venda_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade NUMERIC,
            preco_unitario NUMERIC,
            subtotal NUMERIC,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE produtos (
            id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            categoria_id INTEGER,
            preco_custo NUMERIC,
            nome TEXT
        )
        """,
        """
        CREATE TABLE categorias (
            id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            categoria_pai_id INTEGER
        )
        """,
        """
        CREATE TABLE comissoes_configuracao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            tipo TEXT,
            referencia_id INTEGER,
            tipo_calculo TEXT,
            percentual NUMERIC,
            percentual_loja NUMERIC,
            desconta_taxa_cartao BOOLEAN,
            desconta_impostos BOOLEAN,
            desconta_custo_entrega BOOLEAN,
            comissao_venda_parcial BOOLEAN,
            permite_edicao_venda BOOLEAN,
            observacoes TEXT,
            data_criacao TEXT,
            ativo BOOLEAN,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE formas_pagamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT,
            taxa_percentual NUMERIC,
            taxas_por_parcela TEXT
        )
        """,
        """
        CREATE TABLE venda_pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            venda_id INTEGER,
            forma_pagamento TEXT,
            numero_parcelas INTEGER
        )
        """,
        """
        CREATE TABLE clientes (
            id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            taxa_fixa_entrega NUMERIC,
            nome TEXT
        )
        """,
        """
        CREATE TABLE comissoes_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            venda_item_id INTEGER,
            funcionario_id INTEGER,
            produto_id INTEGER,
            data_venda TEXT,
            quantidade NUMERIC,
            valor_venda NUMERIC,
            valor_custo NUMERIC,
            tipo_calculo TEXT,
            valor_base_calculo NUMERIC,
            percentual_comissao NUMERIC,
            valor_comissao NUMERIC,
            valor_comissao_gerada NUMERIC,
            percentual_pago NUMERIC,
            status TEXT,
            valor_base_original NUMERIC,
            valor_base_comissionada NUMERIC,
            percentual_aplicado NUMERIC,
            valor_pago_referencia NUMERIC,
            parcela_numero INTEGER,
            tenant_id TEXT NOT NULL,
            taxa_cartao_item NUMERIC,
            impostos_item NUMERIC,
            taxa_entregador_item NUMERIC,
            custo_operacional_item NUMERIC,
            receita_taxa_entrega_item NUMERIC,
            percentual_impostos NUMERIC,
            forma_pagamento TEXT,
            data_criacao TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            descricao TEXT,
            valor_final NUMERIC
        )
        """,
    ]
    for statement in statements:
        session.execute(text(statement))
    session.commit()


def _seed_base_data(session):
    for tenant_id, percentual in ((TENANT_A, 10), (TENANT_B, 90)):
        session.execute(
            text("""
                INSERT INTO vendas (
                    id, total, status, desconto_valor, taxa_entrega, tem_entrega,
                    data_venda, tenant_id, entregador_id, valor_taxa_entregador
                )
                VALUES (:id, 100, 'finalizada', 0, 0, 0, '2026-05-12', :tenant_id, NULL, 0)
            """),
            {"id": VENDA_ID, "tenant_id": tenant_id},
        )
        session.execute(
            text("""
                INSERT INTO venda_itens (
                    venda_id, produto_id, quantidade, preco_unitario, subtotal, tenant_id
                )
                VALUES (:venda_id, :produto_id, 1, 100, 100, :tenant_id)
            """),
            {"venda_id": VENDA_ID, "produto_id": PRODUTO_ID, "tenant_id": tenant_id},
        )
        session.execute(
            text("""
                INSERT INTO produtos (id, tenant_id, categoria_id, preco_custo, nome)
                VALUES (:produto_id, :tenant_id, 10, 0, :nome)
            """),
            {
                "produto_id": PRODUTO_ID,
                "tenant_id": tenant_id,
                "nome": f"Produto {tenant_id[:4]}",
            },
        )
        session.execute(
            text("""
                INSERT INTO categorias (id, tenant_id, categoria_pai_id)
                VALUES (10, :tenant_id, NULL)
            """),
            {"tenant_id": tenant_id},
        )
        session.execute(
            text("""
                INSERT INTO comissoes_configuracao (
                    funcionario_id, tipo, referencia_id, tipo_calculo, percentual,
                    percentual_loja, desconta_taxa_cartao, desconta_impostos,
                    desconta_custo_entrega, comissao_venda_parcial,
                    permite_edicao_venda, observacoes, data_criacao, ativo, tenant_id
                )
                VALUES (
                    :funcionario_id, 'produto', :produto_id, 'percentual', :percentual,
                    0, 1, 0, 0, 1, 0, '', '2026-05-12', 1, :tenant_id
                )
            """),
            {
                "funcionario_id": FUNCIONARIO_ID,
                "produto_id": PRODUTO_ID,
                "percentual": percentual,
                "tenant_id": tenant_id,
            },
        )

    session.execute(
        text("""
            INSERT INTO formas_pagamento (tenant_id, nome, taxa_percentual, taxas_por_parcela)
            VALUES (:tenant_id, 'Cartao', 0, '{"2": "0"}')
        """),
        {"tenant_id": TENANT_A},
    )
    session.execute(
        text("""
            INSERT INTO formas_pagamento (tenant_id, nome, taxa_percentual, taxas_por_parcela)
            VALUES (:tenant_id, 'Cartao', 50, '{"2": "50"}')
        """),
        {"tenant_id": TENANT_B},
    )
    session.execute(
        text("""
            INSERT INTO venda_pagamentos (tenant_id, venda_id, forma_pagamento, numero_parcelas)
            VALUES (:tenant_id, :venda_id, 'Cartao', 2)
        """),
        {"tenant_id": TENANT_A, "venda_id": VENDA_ID},
    )
    session.execute(
        text("""
            INSERT INTO venda_pagamentos (tenant_id, venda_id, forma_pagamento, numero_parcelas)
            VALUES (:tenant_id, :venda_id, 'Cartao', 2)
        """),
        {"tenant_id": TENANT_B, "venda_id": VENDA_ID},
    )
    session.execute(
        text("""
            INSERT INTO vendas (
                id, total, status, desconto_valor, taxa_entrega, tem_entrega,
                data_venda, tenant_id, entregador_id, valor_taxa_entregador
            )
            VALUES (999, 100, 'finalizada', 0, 0, 0, '2026-05-12', :tenant_id, NULL, 0)
        """),
        {"tenant_id": TENANT_B},
    )
    session.commit()


def _commission_rows(session):
    return session.execute(
        text("""
            SELECT tenant_id, valor_comissao_gerada, parcela_numero, valor_pago_referencia
            FROM comissoes_itens
            ORDER BY id
        """)
    ).fetchall()


def test_query_comissao_para_tenant_a_nao_enxerga_venda_tenant_b(db_session):
    set_current_tenant(TENANT_A)

    result = gerar_comissoes_venda(
        venda_id=999,
        funcionario_id=FUNCIONARIO_ID,
        db=db_session,
    )

    assert result["success"] is False
    assert "Venda" in result["error"]
    assert _commission_rows(db_session) == []


def test_geracao_nao_usa_pagamento_de_outro_tenant_com_mesmo_venda_id(db_session):
    set_current_tenant(TENANT_A)

    result = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        db=db_session,
    )

    assert result["success"] is True
    rows = _commission_rows(db_session)
    assert len(rows) == 1
    assert rows[0].tenant_id == TENANT_A
    assert float(rows[0].valor_comissao_gerada) == pytest.approx(10.0)


def test_provisao_conta_pagar_recebe_tenant_correto(db_session):
    set_current_tenant(TENANT_A)

    result = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        db=db_session,
    )

    assert result["provisao"]["provisionada"] is True
    contas = db_session.execute(
        text("SELECT tenant_id FROM contas_pagar ORDER BY id")
    ).fetchall()
    assert [row.tenant_id for row in contas] == [TENANT_A]


def test_gerar_comissao_sem_tenant_contexto_falha(db_session):
    clear_current_tenant()

    result = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        db=db_session,
    )

    assert result["success"] is False
    assert "tenant_id ausente" in result["error"]


def test_pagamento_parcial_mantem_parcela_numero(db_session):
    set_current_tenant(TENANT_A)

    result = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        valor_pago=Decimal("50"),
        forma_pagamento="Cartao",
        parcela_numero=2,
        db=db_session,
    )

    assert result["success"] is True
    rows = _commission_rows(db_session)
    assert len(rows) == 1
    assert rows[0].parcela_numero == 2
    assert float(rows[0].valor_pago_referencia) == pytest.approx(50.0)
    assert float(rows[0].valor_comissao_gerada) == pytest.approx(5.0)


def test_pagamento_total_gera_comissao_mesmo_com_parcial_desativada(db_session):
    set_current_tenant(TENANT_A)
    db_session.execute(
        text("""
            UPDATE comissoes_configuracao
            SET comissao_venda_parcial = 0
            WHERE funcionario_id = :funcionario_id
              AND tenant_id = :tenant_id
        """),
        {"funcionario_id": FUNCIONARIO_ID, "tenant_id": TENANT_A},
    )
    db_session.commit()

    result = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        valor_pago=Decimal("100"),
        forma_pagamento="Cartao",
        parcela_numero=1,
        db=db_session,
    )

    assert result["success"] is True
    rows = _commission_rows(db_session)
    assert len(rows) == 1
    assert float(rows[0].valor_pago_referencia) == pytest.approx(100.0)
    assert float(rows[0].valor_comissao_gerada) == pytest.approx(10.0)


def test_reexecucao_nao_duplica_comissao_no_mesmo_tenant(db_session):
    set_current_tenant(TENANT_A)

    first = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        parcela_numero=1,
        db=db_session,
    )
    second = gerar_comissoes_venda(
        venda_id=VENDA_ID,
        funcionario_id=FUNCIONARIO_ID,
        parcela_numero=1,
        db=db_session,
    )

    assert first["success"] is True
    assert second["success"] is True
    assert second["duplicated"] is True
    assert len(_commission_rows(db_session)) == 1


def test_mesmo_funcionario_e_referencia_em_tenants_diferentes_nao_cruza_config(
    db_session,
):
    config_a = buscar_configuracao_comissao(
        db_session,
        FUNCIONARIO_ID,
        PRODUTO_ID,
        tenant_id=TENANT_A,
    )
    config_b = buscar_configuracao_comissao(
        db_session,
        FUNCIONARIO_ID,
        PRODUTO_ID,
        tenant_id=TENANT_B,
    )

    assert float(config_a["percentual"]) == pytest.approx(10.0)
    assert float(config_b["percentual"]) == pytest.approx(90.0)


def test_comissao_configuracao_model_declares_tenant_id():
    from app.comissoes_models import ComissaoConfiguracao

    assert "tenant_id" in ComissaoConfiguracao.__table__.columns


def test_legacy_comissoes_config_busca_respeita_tenant_explicito(
    db_session, monkeypatch
):
    import app.comissoes_models as comissoes_models

    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(comissoes_models, "SessionLocal", lambda: db_session)

    config_a = comissoes_models.ComissoesConfig.buscar_configuracao(
        FUNCIONARIO_ID,
        PRODUTO_ID,
        tenant_id=TENANT_A,
    )
    config_b = comissoes_models.ComissoesConfig.buscar_configuracao(
        FUNCIONARIO_ID,
        PRODUTO_ID,
        tenant_id=TENANT_B,
    )

    assert float(config_a["percentual"]) == pytest.approx(10.0)
    assert float(config_b["percentual"]) == pytest.approx(90.0)


def _method_source(source: str, method_name: str, next_marker: str) -> str:
    start = source.index(f"def {method_name}")
    end = source.index(next_marker, start)
    return source[start:end]


def test_legacy_comissoes_config_route_methods_use_tenant_safe_sql():
    source = (
        Path(__file__).resolve().parents[2] / "app" / "comissoes_models.py"
    ).read_text(encoding="utf-8")

    route_method_blocks = [
        _method_source(source, "buscar_configuracao", "def criar_ou_atualizar"),
        _method_source(source, "deletar", "def duplicar_configuracao"),
        _method_source(source, "duplicar_configuracao", "class ComissoesItens"),
    ]
    for method_block in route_method_blocks:
        assert "tenant_id" in method_block
        assert "execute_tenant_safe" in method_block
        assert "db.execute(" not in method_block
