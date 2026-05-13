from datetime import date
from decimal import Decimal
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.comissoes_provisao import provisionar_comissoes_venda
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.utils.tenant_safe_sql import TenantSafeSQLError


TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
VENDA_ID = 900
FUNCIONARIO_ID = 77


@pytest.fixture()
def db_session(monkeypatch):
    clear_current_tenant()

    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    _create_schema(session)
    _seed_data(session)

    dre_calls = []

    def fake_atualizar_dre_por_lancamento(**kwargs):
        dre_calls.append(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "app.domain.dre.lancamento_dre_sync",
        SimpleNamespace(atualizar_dre_por_lancamento=fake_atualizar_dre_por_lancamento),
    )
    session.dre_calls = dre_calls

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
        CREATE TABLE dre_subcategorias (
            id INTEGER NOT NULL,
            nome TEXT,
            ativo BOOLEAN,
            tenant_id TEXT NOT NULL
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


def _seed_data(session):
    for tenant_id, numero_venda, comissao_id, subcat_id, user_name, valor in (
        (TENANT_A, "VA-900", 1, 10, "Alice Tenant A", 25),
        (TENANT_B, "VB-900", 2, 20, "Bob Tenant B", 250),
    ):
        session.execute(
            text("""
                INSERT INTO vendas (id, numero_venda, data_venda, canal, cliente_id, status, tenant_id)
                VALUES (:id, :numero_venda, NULL, 'loja_fisica', 123, 'finalizada', :tenant_id)
            """),
            {"id": VENDA_ID, "numero_venda": numero_venda, "tenant_id": tenant_id},
        )
        session.execute(
            text("""
                INSERT INTO comissoes_itens (
                    id, venda_id, funcionario_id, valor_comissao_gerada, produto_id,
                    status, tenant_id, comissao_provisionada
                )
                VALUES (:id, :venda_id, :funcionario_id, :valor, 55, 'pendente', :tenant_id, 0)
            """),
            {
                "id": comissao_id,
                "venda_id": VENDA_ID,
                "funcionario_id": FUNCIONARIO_ID,
                "valor": valor,
                "tenant_id": tenant_id,
            },
        )
        session.execute(
            text("""
                INSERT INTO dre_subcategorias (id, nome, ativo, tenant_id)
                VALUES (:id, 'Comissoes de Vendas - Vendedores', 1, :tenant_id)
            """),
            {"id": subcat_id, "tenant_id": tenant_id},
        )
        session.execute(
            text("""
                INSERT INTO users (id, nome, data_fechamento_comissao, tenant_id)
                VALUES (:id, :nome, NULL, :tenant_id)
            """),
            {"id": FUNCIONARIO_ID, "nome": user_name, "tenant_id": tenant_id},
        )
    session.commit()


def _contas(session):
    return session.execute(
        text("""
            SELECT tenant_id, descricao, fornecedor_id, dre_subcategoria_id, valor_final
            FROM contas_pagar
            ORDER BY id
        """)
    ).fetchall()


def _comissoes(session):
    return session.execute(
        text("""
            SELECT id, tenant_id, comissao_provisionada, conta_pagar_id
            FROM comissoes_itens
            ORDER BY id
        """)
    ).fetchall()


def test_provisao_tenant_a_nao_enxerga_comissoes_tenant_b(db_session):
    result = provisionar_comissoes_venda(
        venda_id=VENDA_ID,
        tenant_id=TENANT_A,
        db=db_session,
    )

    assert result["success"] is True
    assert result["comissoes_provisionadas"] == 1
    assert result["valor_total"] == pytest.approx(25.0)

    comissoes = _comissoes(db_session)
    assert comissoes[0].tenant_id == TENANT_A
    assert comissoes[0].comissao_provisionada in (1, True)
    assert comissoes[1].tenant_id == TENANT_B
    assert comissoes[1].comissao_provisionada in (0, False)


def test_provisao_tenant_a_cria_contas_pagar_somente_tenant_a(db_session):
    provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)

    contas = _contas(db_session)
    assert len(contas) == 1
    assert contas[0].tenant_id == TENANT_A
    assert float(contas[0].valor_final) == pytest.approx(25.0)


def test_mesmo_venda_id_em_tenants_diferentes_nao_cruza_provisao(db_session):
    result_a = provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)
    result_b = provisionar_comissoes_venda(VENDA_ID, TENANT_B, db_session)

    assert result_a["comissoes_provisionadas"] == 1
    assert result_b["comissoes_provisionadas"] == 1
    assert [row.tenant_id for row in _contas(db_session)] == [TENANT_A, TENANT_B]


def test_reexecucao_nao_duplica_provisao_no_mesmo_tenant(db_session):
    first = provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)
    second = provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)

    assert first["comissoes_provisionadas"] == 1
    assert second["success"] is True
    assert second["comissoes_provisionadas"] == 0
    assert len(_contas(db_session)) == 1


def test_funcao_sem_tenant_id_ou_contexto_falha(db_session):
    clear_current_tenant()

    with pytest.raises(TenantSafeSQLError, match="tenant_id ausente"):
        provisionar_comissoes_venda(VENDA_ID, tenant_id=None, db=db_session)


def test_funcao_pode_resolver_tenant_pelo_contexto(db_session):
    set_current_tenant(TENANT_A)

    result = provisionar_comissoes_venda(VENDA_ID, tenant_id=None, db=db_session)

    assert result["success"] is True
    assert [row.tenant_id for row in _contas(db_session)] == [TENANT_A]


def test_dre_subcategoria_usada_pertence_ao_mesmo_tenant(db_session):
    provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)

    assert db_session.dre_calls
    assert db_session.dre_calls[0]["tenant_id"] == TENANT_A
    assert db_session.dre_calls[0]["dre_subcategoria_id"] == 10

    contas = _contas(db_session)
    assert contas[0].dre_subcategoria_id == 10


def test_conta_pagar_nao_usa_funcionario_de_outro_tenant(db_session):
    provisionar_comissoes_venda(VENDA_ID, TENANT_A, db_session)

    conta = _contas(db_session)[0]
    assert "Alice Tenant A" in conta.descricao
    assert "Bob Tenant B" not in conta.descricao
    assert conta.fornecedor_id == FUNCIONARIO_ID
