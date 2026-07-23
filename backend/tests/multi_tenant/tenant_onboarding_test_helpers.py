import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db  # noqa: F401 - registra hooks multitenant


TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"
BASE_EXPECTED_COUNTS = {
    "payment_methods": 4,
    "bank_accounts": 2,
    "pet_species": 2,
    "pet_breeds": 2,
    "dre_categories": 3,
    "dre_subcategories": 4,
    "financial_categories": 2,
    "expense_types": 2,
    "product_departments": 1,
    "product_categories": 2,
    "ration_lines": 4,
    "animal_sizes": 6,
    "life_stages": 4,
    "treatment_types": 9,
    "protein_flavors": 10,
    "package_weights": 11,
    "vet_procedures": 70,
}


class _SessionProxy:
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self):
        # The fixture owns the wrapped session; callers may close the proxy safely.
        return None


@pytest.fixture()
def onboarding_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    ddl = [
        """
        CREATE TABLE tenants (
            id TEXT PRIMARY KEY,
            status TEXT
        )
        """,
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            is_active BOOLEAN
        )
        """,
        """
        CREATE TABLE template_bundles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_code TEXT NOT NULL,
            version TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            active BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            item_type TEXT NOT NULL,
            template_code TEXT NOT NULL,
            name TEXT NOT NULL,
            payload JSON NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tenant_template_installs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            status TEXT NOT NULL,
            dry_run BOOLEAN NOT NULL,
            created_by_user_id INTEGER,
            summary JSON NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tenant_template_item_installs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            item_type TEXT NOT NULL,
            template_code TEXT NOT NULL,
            target_table TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_by_user_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE formas_pagamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            taxa_percentual NUMERIC,
            taxa_fixa NUMERIC,
            prazo_dias INTEGER,
            prazo_recebimento INTEGER,
            operadora TEXT,
            gera_contas_receber BOOLEAN,
            split_parcelas BOOLEAN,
            requer_nsu BOOLEAN,
            tipo_cartao TEXT,
            bandeira TEXT,
            ativo BOOLEAN,
            permite_parcelamento BOOLEAN,
            max_parcelas INTEGER,
            parcelas_maximas INTEGER,
            icone TEXT,
            cor TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE contas_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            banco TEXT,
            agencia TEXT,
            conta TEXT,
            saldo_inicial NUMERIC,
            saldo_atual NUMERIC,
            cor TEXT,
            icone TEXT,
            instituicao_bancaria BOOLEAN,
            ativa BOOLEAN,
            observacoes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE especies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE racas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            especie TEXT,
            especie_id INTEGER NOT NULL,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE dre_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            ordem INTEGER,
            natureza TEXT NOT NULL,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE dre_subcategorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            categoria_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo_custo TEXT NOT NULL,
            base_rateio TEXT,
            escopo_rateio TEXT NOT NULL,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE categorias_financeiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            cor TEXT,
            icone TEXT,
            descricao TEXT,
            ativo BOOLEAN,
            dre_subcategoria_id INTEGER,
            tipo_custo TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tipo_despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            e_custo_fixo BOOLEAN NOT NULL,
            dre_subcategoria_id INTEGER NOT NULL,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE departamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            categoria_pai_id INTEGER,
            departamento_id INTEGER,
            descricao TEXT,
            icone TEXT,
            cor TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE linhas_racao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE portes_animal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE fases_publico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tipos_tratamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE sabores_proteina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE apresentacoes_peso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            peso_kg NUMERIC NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE vet_catalogo_procedimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            valor_padrao NUMERIC,
            duracao_minutos INTEGER,
            requer_anestesia BOOLEAN,
            observacoes TEXT,
            insumos JSON,
            ativo BOOLEAN NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT,
            situacao BOOLEAN,
            tipo_produto TEXT NOT NULL,
            is_parent BOOLEAN NOT NULL,
            is_sellable BOOLEAN NOT NULL,
            descricao_curta TEXT,
            categoria_id INTEGER,
            departamento_id INTEGER,
            preco_custo NUMERIC,
            preco_venda NUMERIC,
            estoque_atual NUMERIC,
            estoque_minimo NUMERIC,
            estoque_maximo NUMERIC,
            unidade TEXT,
            condicao TEXT,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
    ]
    for statement in ddl:
        session.execute(text(statement))
    session.commit()

    try:
        yield session
    finally:
        session.close()


def _count(session, table, tenant_id=None):
    if tenant_id is None:
        return session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    return session.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    ).scalar()


def _tenant_params(tenant_id: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "tenant_id_hex": tenant_id.replace("-", "")}
