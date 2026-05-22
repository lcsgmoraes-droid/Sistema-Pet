from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401
from app.comissoes_provisao import provisionar_comissoes_venda
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.utils.tenant_safe_sql import TenantSafeSQLError


TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SUBCATEGORIA_ID = 10
CANAL = "loja_fisica"
DATA_LANCAMENTO = date(2026, 5, 12)


@pytest.fixture()
def db_session():
    clear_current_tenant()

    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    _create_schema(session)
    _seed_dre_data(session)
    _seed_comissao_data(session)

    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _tenant_hex(tenant_id):
    return UUID(str(tenant_id)).hex


def _tenant_str(tenant_id):
    return str(UUID(str(tenant_id)))


def _same_tenant(value, tenant_id):
    return str(value).replace("-", "") == _tenant_hex(tenant_id)


def _create_schema(session):
    statements = [
        """
        CREATE TABLE dre_categorias (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            nome TEXT,
            ordem INTEGER,
            natureza TEXT,
            ativo BOOLEAN,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_subcategorias (
            id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            categoria_id INTEGER,
            nome TEXT,
            tipo_custo TEXT,
            base_rateio TEXT,
            escopo_rateio TEXT,
            ativo BOOLEAN,
            custo_pe TEXT,
            categoria_financeira_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_periodos (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT,
            usuario_id INTEGER,
            data_inicio DATE,
            data_fim DATE,
            mes INTEGER,
            ano INTEGER,
            canal TEXT,
            canais_incluidos TEXT,
            receita_bruta NUMERIC DEFAULT 0,
            deducoes_receita NUMERIC DEFAULT 0,
            receita_liquida NUMERIC DEFAULT 0,
            custo_produtos_vendidos NUMERIC DEFAULT 0,
            lucro_bruto NUMERIC DEFAULT 0,
            margem_bruta_percent NUMERIC DEFAULT 0,
            despesas_vendas NUMERIC DEFAULT 0,
            despesas_administrativas NUMERIC DEFAULT 0,
            despesas_financeiras NUMERIC DEFAULT 0,
            outras_despesas NUMERIC DEFAULT 0,
            total_despesas_operacionais NUMERIC DEFAULT 0,
            lucro_operacional NUMERIC DEFAULT 0,
            margem_operacional_percent NUMERIC DEFAULT 0,
            impostos NUMERIC DEFAULT 0,
            impostos_detalhamento TEXT,
            aliquota_efetiva_percent NUMERIC DEFAULT 0,
            regime_tributario TEXT,
            lucro_liquido NUMERIC DEFAULT 0,
            margem_liquida_percent NUMERIC DEFAULT 0,
            status TEXT,
            tendencia TEXT,
            score_saude INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_detalhe_canais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            data_inicio DATE,
            data_fim DATE,
            mes INTEGER,
            ano INTEGER,
            canal TEXT,
            receita_bruta NUMERIC DEFAULT 0,
            deducoes_receita NUMERIC DEFAULT 0,
            receita_liquida NUMERIC DEFAULT 0,
            custo_produtos_vendidos NUMERIC DEFAULT 0,
            lucro_bruto NUMERIC DEFAULT 0,
            margem_bruta_percent NUMERIC DEFAULT 0,
            despesas_vendas NUMERIC DEFAULT 0,
            despesas_pessoal NUMERIC DEFAULT 0,
            despesas_administrativas NUMERIC DEFAULT 0,
            despesas_financeiras NUMERIC DEFAULT 0,
            outras_despesas NUMERIC DEFAULT 0,
            total_despesas_operacionais NUMERIC DEFAULT 0,
            lucro_operacional NUMERIC DEFAULT 0,
            margem_operacional_percent NUMERIC DEFAULT 0,
            impostos NUMERIC DEFAULT 0,
            impostos_detalhamento TEXT,
            aliquota_efetiva_percent NUMERIC DEFAULT 0,
            regime_tributario TEXT,
            lucro_liquido NUMERIC DEFAULT 0,
            margem_liquida_percent NUMERIC DEFAULT 0,
            status TEXT,
            score_saude INTEGER DEFAULT 0,
            origem TEXT,
            origem_evento TEXT,
            referencia_id TEXT,
            observacao TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE dre_lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            usuario_id INTEGER,
            dre_detalhe_canal_id INTEGER,
            dre_subcategoria_id INTEGER,
            canal TEXT,
            valor NUMERIC,
            data_lancamento DATE,
            data_competencia DATE,
            origem TEXT,
            descricao TEXT
        )
        """,
        """
        CREATE TABLE vendas (
            id INTEGER NOT NULL,
            numero_venda TEXT,
            data_venda DATE,
            canal TEXT,
            cliente_id INTEGER,
            status TEXT,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE comissoes_itens (
            id INTEGER PRIMARY KEY,
            venda_id INTEGER,
            funcionario_id INTEGER,
            valor_comissao_gerada NUMERIC,
            produto_id INTEGER,
            status TEXT,
            tenant_id TEXT NOT NULL,
            comissao_provisionada BOOLEAN DEFAULT 0,
            conta_pagar_id INTEGER,
            data_provisao DATE
        )
        """,
        """
        CREATE TABLE users (
            id INTEGER NOT NULL,
            nome TEXT,
            data_fechamento_comissao INTEGER,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE clientes (
            id INTEGER NOT NULL,
            nome TEXT,
            data_fechamento_comissao INTEGER,
            parceiro_ativo BOOLEAN DEFAULT 0,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            fornecedor_id INTEGER,
            dre_subcategoria_id INTEGER,
            canal TEXT,
            valor_original NUMERIC,
            valor_pago NUMERIC,
            valor_final NUMERIC,
            data_emissao DATE,
            data_vencimento DATE,
            status TEXT,
            documento TEXT,
            observacoes TEXT,
            user_id INTEGER,
            tenant_id TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """,
    ]
    for statement in statements:
        session.execute(text(statement))
    session.commit()


def _seed_dre_data(session):
    session.execute(
        text("""
            INSERT INTO dre_periodos (
                id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal
            ) VALUES
                (1, :tenant_a, 501, '2026-05-01', '2026-05-31', 5, 2026, :canal),
                (2, :tenant_b, 501, '2026-05-01', '2026-05-31', 5, 2026, :canal)
        """),
        {"canal": CANAL, "tenant_a": _tenant_hex(TENANT_A), "tenant_b": _tenant_hex(TENANT_B)},
    )

    for categoria_id, tenant_id, categoria_nome, subcategoria_nome in (
        (1, TENANT_A, "Despesas Tenant A", "Comissoes Vendedores Tenant A"),
        (2, TENANT_B, "Despesas Tenant B", "Comissoes Vendedores Tenant B"),
    ):
        session.execute(
            text("""
                INSERT INTO dre_categorias (
                    id, tenant_id, nome, ordem, natureza, ativo
                ) VALUES (
                    :id, :tenant_id, :nome, 1, 'despesa', 1
                )
            """),
            {
                "id": categoria_id,
                "tenant_id": _tenant_hex(tenant_id),
                "nome": categoria_nome,
            },
        )
        session.execute(
            text("""
                INSERT INTO dre_subcategorias (
                    id, tenant_id, categoria_id, nome, tipo_custo,
                    escopo_rateio, ativo
                ) VALUES (
                    :id, :tenant_id, :categoria_id, :nome, 'DIRETO', 'AMBOS', 1
                )
            """),
            {
                "id": SUBCATEGORIA_ID,
                "tenant_id": _tenant_hex(tenant_id),
                "categoria_id": categoria_id,
                "nome": subcategoria_nome,
            },
        )

        # Alias only for SQLite tests that exercise raw SQL helpers using string UUIDs.
        session.execute(
            text("""
                INSERT INTO dre_subcategorias (
                    id, tenant_id, categoria_id, nome, tipo_custo,
                    escopo_rateio, ativo
                ) VALUES (
                    :id, :tenant_id, :categoria_id, :nome, 'DIRETO', 'AMBOS', 1
                )
            """),
            {
                "id": SUBCATEGORIA_ID,
                "tenant_id": _tenant_str(tenant_id),
                "categoria_id": categoria_id,
                "nome": subcategoria_nome,
            },
        )

    session.execute(
        text("""
            INSERT INTO dre_detalhe_canais (
                usuario_id, data_inicio, data_fim, mes, ano, canal,
                despesas_vendas, total_despesas_operacionais,
                lucro_operacional, lucro_liquido, status, tenant_id
            ) VALUES (
                501, '2026-05-01', '2026-05-31', 5, 2026, :canal,
                100, 100, -100, -100, 'prejuizo', :tenant_id
            )
        """),
        {"canal": CANAL, "tenant_id": _tenant_hex(TENANT_B)},
    )
    session.commit()


def _seed_comissao_data(session):
    session.execute(
        text("""
            INSERT INTO vendas (
                id, numero_venda, data_venda, canal, cliente_id, status, tenant_id
            ) VALUES (
                900, 'VA-900', NULL, :canal, 123, 'finalizada', :tenant_id
            )
        """),
        {"canal": CANAL, "tenant_id": _tenant_str(TENANT_A)},
    )
    session.execute(
        text("""
            INSERT INTO comissoes_itens (
                id, venda_id, funcionario_id, valor_comissao_gerada,
                produto_id, status, tenant_id, comissao_provisionada
            ) VALUES (
                1, 900, 77, 25, 55, 'pendente', :tenant_id, 0
            )
        """),
        {"tenant_id": _tenant_str(TENANT_A)},
    )
    session.execute(
        text("""
            INSERT INTO users (id, nome, data_fechamento_comissao, tenant_id)
            VALUES (77, 'Alice Tenant A', NULL, :tenant_id)
        """),
        {"tenant_id": _tenant_str(TENANT_A)},
    )
    session.execute(
        text("""
            INSERT INTO clientes (id, nome, data_fechamento_comissao, parceiro_ativo, tenant_id)
            VALUES (77, 'Alice Tenant A', NULL, 1, :tenant_id)
        """),
        {"tenant_id": _tenant_str(TENANT_A)},
    )
    session.commit()


def _detalhes(session):
    return session.execute(
        text("""
            SELECT tenant_id, canal, despesas_vendas, total_despesas_operacionais,
                   lucro_operacional, status
            FROM dre_detalhe_canais
            ORDER BY tenant_id
        """)
    ).fetchall()


def _lancamentos(session):
    return session.execute(
        text("""
            SELECT tenant_id, dre_subcategoria_id, canal, valor, origem, descricao
            FROM dre_lancamentos
            ORDER BY id
        """)
    ).fetchall()


def _valor_lucro_liquido(session, tenant_id):
    row = session.execute(
        text("""
            SELECT lucro_liquido
            FROM dre_detalhe_canais
            WHERE REPLACE(tenant_id, '-', '') = :tenant_id
              AND canal = :canal
        """),
        {"tenant_id": _tenant_hex(tenant_id), "canal": CANAL},
    ).fetchone()
    return float(row.lucro_liquido) if row else None


def test_lancamento_dre_tenant_a_nao_atualiza_tenant_b(db_session):
    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=TENANT_A,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("25.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )

    assert _valor_lucro_liquido(db_session, TENANT_A) == -25.0
    assert _valor_lucro_liquido(db_session, TENANT_B) == -100.0

    lancamentos = _lancamentos(db_session)
    assert len(lancamentos) == 1
    assert _same_tenant(lancamentos[0].tenant_id, TENANT_A)


def test_mesmo_dre_subcategoria_id_em_tenants_diferentes_nao_cruza(db_session):
    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=TENANT_A,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("25.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )
    db_session.expunge_all()

    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=TENANT_B,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("30.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )

    lancamentos = _lancamentos(db_session)
    assert "Tenant A" in lancamentos[0].descricao
    assert "Tenant B" in lancamentos[1].descricao
    assert _same_tenant(lancamentos[0].tenant_id, TENANT_A)
    assert _same_tenant(lancamentos[1].tenant_id, TENANT_B)


def test_mesmo_canal_periodo_em_tenants_diferentes_fica_separado(db_session):
    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=TENANT_A,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("25.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )
    db_session.expunge_all()

    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=TENANT_B,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("30.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )

    detalhes = _detalhes(db_session)
    assert sum(1 for row in detalhes if _same_tenant(row.tenant_id, TENANT_A)) == 1
    assert sum(1 for row in detalhes if _same_tenant(row.tenant_id, TENANT_B)) == 1
    assert _valor_lucro_liquido(db_session, TENANT_A) == -25.0
    assert _valor_lucro_liquido(db_session, TENANT_B) == -130.0


def test_funcao_sem_tenant_id_ou_contexto_falha(db_session):
    clear_current_tenant()

    with pytest.raises(TenantSafeSQLError, match="tenant_id ausente"):
        atualizar_dre_por_lancamento(
            db=db_session,
            dre_subcategoria_id=SUBCATEGORIA_ID,
            canal=CANAL,
            valor=Decimal("25.00"),
            data_lancamento=DATA_LANCAMENTO,
            tipo_movimentacao="DESPESA",
        )


def test_insert_update_dre_grava_tenant_id_correto(db_session):
    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=str(TENANT_A),
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("25.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )
    atualizar_dre_por_lancamento(
        db=db_session,
        tenant_id=str(TENANT_A),
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("10.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )

    assert _valor_lucro_liquido(db_session, TENANT_A) == -35.0
    lancamentos = _lancamentos(db_session)
    assert len(lancamentos) == 2
    assert all(_same_tenant(row.tenant_id, TENANT_A) for row in lancamentos)


def test_contexto_pode_resolver_tenant_id(db_session):
    set_current_tenant(TENANT_A)

    atualizar_dre_por_lancamento(
        db=db_session,
        dre_subcategoria_id=SUBCATEGORIA_ID,
        canal=CANAL,
        valor=Decimal("25.00"),
        data_lancamento=DATA_LANCAMENTO,
        tipo_movimentacao="DESPESA",
    )

    assert _valor_lucro_liquido(db_session, TENANT_A) == -25.0


def test_chamada_via_provisao_comissao_mantem_tenant_id(db_session):
    result = provisionar_comissoes_venda(
        venda_id=900,
        tenant_id=str(TENANT_A),
        db=db_session,
    )

    assert result["success"] is True
    assert result["comissoes_provisionadas"] == 1

    lancamentos = _lancamentos(db_session)
    assert len(lancamentos) == 1
    assert _same_tenant(lancamentos[0].tenant_id, TENANT_A)
    assert _valor_lucro_liquido(db_session, TENANT_A) == -25.0
