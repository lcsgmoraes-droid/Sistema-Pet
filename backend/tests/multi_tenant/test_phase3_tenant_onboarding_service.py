import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db  # noqa: F401 - registra hooks multitenant
from app.services.tenant_onboarding_service import (
    TenantOnboardingError,
    onboard_tenant_defaults,
)
from app.scripts import run_tenant_onboarding


TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


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


def test_onboarding_dry_run_does_not_create_tenant_data(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["would_create"]["payment_methods"] == 4
    assert result["would_create"]["dre_categories"] == 3
    assert result["would_create"]["dre_subcategories"] == 4
    assert result["would_create"]["financial_categories"] == 2
    assert result["would_create"]["expense_types"] == 2
    assert result["would_create"]["product_departments"] == 1
    assert result["would_create"]["product_categories"] == 2
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 0
    assert _count(onboarding_session, "tenant_template_installs") == 0


def test_onboarding_apply_creates_default_copy_for_tenant(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
    )
    onboarding_session.commit()

    assert result["created"]["payment_methods"] == 4
    assert result["created"]["dre_categories"] == 3
    assert result["created"]["dre_subcategories"] == 4
    assert result["created"]["financial_categories"] == 2
    assert result["created"]["expense_types"] == 2
    assert result["created"]["product_departments"] == 1
    assert result["created"]["product_categories"] == 2
    assert result["template_source"] == "database"
    assert _count(onboarding_session, "template_items") >= 1
    assert _count(onboarding_session, "tenant_template_installs") == 1
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 3
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 2
    assert _count(onboarding_session, "categorias", TENANT_A) == 2
    assert _count(onboarding_session, "produtos", TENANT_A) == 0
    enum_values = onboarding_session.execute(
        text("SELECT DISTINCT tipo_custo, escopo_rateio FROM dre_subcategorias WHERE tenant_id = :tenant_id"),
        {"tenant_id": TENANT_A},
    ).all()
    assert enum_values
    assert all(tipo_custo == "DIRETO" for tipo_custo, _escopo in enum_values)
    assert all(escopo == "AMBOS" for _tipo_custo, escopo in enum_values)


def test_onboarding_is_idempotent_for_same_tenant(onboarding_session):
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()

    second = onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["payment_methods"] == 4
    assert second["skipped"]["dre_categories"] == 3
    assert second["skipped"]["dre_subcategories"] == 4
    assert second["skipped"]["financial_categories"] == 2
    assert second["skipped"]["expense_types"] == 2
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 3
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 2
    assert _count(onboarding_session, "tenant_template_installs") == 1


def test_onboarding_item_mapping_survives_tenant_payment_edit(onboarding_session):
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_B, user_id=2, dry_run=False)
    onboarding_session.commit()

    pix_id = onboarding_session.execute(
        text(
            """
            SELECT id
            FROM formas_pagamento
            WHERE tenant_id = :tenant_id AND tipo = 'pix'
            """
        ),
        {"tenant_id": TENANT_A},
    ).scalar_one()
    onboarding_session.execute(
        text("UPDATE formas_pagamento SET nome = 'PIX Loja Centro' WHERE id = :id"),
        {"id": pix_id},
    )
    onboarding_session.commit()

    second = onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 4
    assert (
        onboarding_session.execute(
            text("SELECT COUNT(*) FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"),
            {"tenant_id": TENANT_A},
        ).scalar()
        == 1
    )
    assert (
        onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"),
            {"tenant_id": TENANT_A},
        ).scalar()
        == "PIX Loja Centro"
    )
    assert (
        onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"),
            {"tenant_id": TENANT_B},
        ).scalar()
        == "PIX"
    )
    assert (
        onboarding_session.execute(
            text("SELECT name FROM template_items WHERE template_code = 'payment_pix'")
        ).scalar()
        == "PIX"
    )
    assert (
        onboarding_session.execute(
            text(
                """
                SELECT target_table, target_id
                FROM tenant_template_item_installs
                WHERE tenant_id IN (:tenant_id, :tenant_id_hex)
                  AND template_code = 'payment_pix'
                """
            ),
            _tenant_params(TENANT_A),
        ).one()
        == ("formas_pagamento", pix_id)
    )


def test_onboarding_item_mapping_survives_tenant_dre_category_edit(onboarding_session):
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()

    receitas_id = onboarding_session.execute(
        text(
            """
            SELECT target_id
            FROM tenant_template_item_installs
            WHERE tenant_id IN (:tenant_id, :tenant_id_hex)
              AND template_code = 'dre_receitas'
            """
        ),
        _tenant_params(TENANT_A),
    ).scalar_one()
    onboarding_session.execute(
        text("UPDATE dre_categorias SET nome = 'Receitas Loja Principal' WHERE id = :id"),
        {"id": receitas_id},
    )
    onboarding_session.commit()

    second = onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["dre_categories"] == 3
    assert second["skipped"]["dre_subcategories"] == 4
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 3
    assert _count(onboarding_session, "dre_subcategorias", TENANT_A) == 4
    assert (
        onboarding_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM dre_subcategorias
                WHERE tenant_id = :tenant_id AND categoria_id = :categoria_id
                """
            ),
            {"tenant_id": TENANT_A, "categoria_id": receitas_id},
        ).scalar()
        == 2
    )


def test_onboarding_creates_isolated_copies_for_each_tenant(onboarding_session):
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_B, user_id=2, dry_run=False)
    onboarding_session.commit()

    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 4
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 3
    assert _count(onboarding_session, "dre_categorias", TENANT_B) == 3
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 2
    assert _count(onboarding_session, "tipo_despesas", TENANT_B) == 2

    names_a = {
        row[0]
        for row in onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id"),
            {"tenant_id": TENANT_A},
        )
    }
    names_b = {
        row[0]
        for row in onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id"),
            {"tenant_id": TENANT_B},
        )
    }
    assert names_a == names_b


def test_onboarding_include_products_dry_run_does_not_create_catalog(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=True,
        include_products=True,
    )

    assert result["would_create"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 0


def test_onboarding_include_products_apply_creates_inactive_reference_catalog(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
        include_products=True,
    )
    onboarding_session.commit()

    assert result["created"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 3
    products = onboarding_session.execute(
        text(
            """
            SELECT codigo, ativo, situacao, estoque_atual
            FROM produtos
            WHERE tenant_id = :tenant_id
            ORDER BY codigo
            """
        ),
        {"tenant_id": TENANT_A},
    ).all()
    assert {row[0] for row in products} == {
        "TPL-BRINQUEDO",
        "TPL-PETISCO-100G",
        "TPL-RACAO-ADULTO-1KG",
    }
    assert not any(bool(row[1]) for row in products)
    assert not any(bool(row[2]) for row in products)
    assert all(float(row[3]) == 0 for row in products)

    second = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
        include_products=True,
    )
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 3


def test_onboarding_requires_tenant_and_user(onboarding_session):
    with pytest.raises(TenantOnboardingError, match="tenant_id"):
        onboard_tenant_defaults(onboarding_session, tenant_id=None, user_id=1)

    with pytest.raises(TenantOnboardingError, match="user_id"):
        onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=None)


def test_onboarding_skips_sections_when_operational_schema_is_absent():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        result = onboard_tenant_defaults(
            session,
            tenant_id=TENANT_A,
            user_id=1,
            dry_run=False,
        )
    finally:
        session.close()

    assert result["created"] == {}
    assert result["would_create"] == {}
    assert any("schema ausente" in warning for warning in result["warnings"])
    assert any("tenant_template_installs" in warning for warning in result["warnings"])


def test_onboarding_strict_required_fails_when_operational_schema_is_absent():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        with pytest.raises(TenantOnboardingError, match="Onboarding obrigatorio incompleto"):
            onboard_tenant_defaults(
                session,
                tenant_id=TENANT_A,
                user_id=1,
                dry_run=False,
                strict_required=True,
            )
    finally:
        session.close()


def test_onboarding_script_defaults_to_dry_run(monkeypatch, capsys, onboarding_session):
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--tenant-id", TENANT_A, "--user-id", "1"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["would_create"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_apply_persists(monkeypatch, capsys, onboarding_session):
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(
        ["--tenant-id", TENANT_A, "--user-id", "1", "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is False
    assert payload["created"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4


def test_onboarding_script_all_active_tenants_dry_run(monkeypatch, capsys, onboarding_session):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_B})
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'inactive')"), {"id": "33333333-3333-3333-3333-333333333333"})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_B})
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--all-active-tenants"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["mode"] == "all_active_tenants"
    assert payload["tenant_count"] == 2
    assert payload["totals"]["would_create"]["payment_methods"] == 8
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 0


def test_onboarding_script_future_tenant_check_does_not_read_or_update_existing_tenants(
    monkeypatch,
    capsys,
    onboarding_session,
):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--future-tenant-check"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["mode"] == "future_tenant_check"
    assert payload["tenant_scope"] == "synthetic_future_tenant"
    assert payload["dry_run"] is True
    assert payload["result"]["would_create"]["payment_methods"] == 4
    assert payload["result"]["would_create"]["dre_categories"] == 3
    assert payload["result"]["would_create"]["product_categories"] == 2
    assert TENANT_A not in captured.out
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "tenant_template_installs") == 0


def test_onboarding_script_all_active_tenants_apply_blocks_bulk_existing_by_default(
    monkeypatch,
    capsys,
    onboarding_session,
):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--all-active-tenants", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "tenants existentes" in payload["error"]
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_all_active_tenants_apply_with_explicit_override(monkeypatch, capsys, onboarding_session):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'ativo')"), {"id": TENANT_B})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_B})
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(
        ["--all-active-tenants", "--apply", "--allow-existing-tenant-apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is False
    assert payload["tenant_count"] == 2
    assert payload["totals"]["created"]["payment_methods"] == 8
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 4


def test_onboarding_script_health_check_reports_incomplete_and_complete(monkeypatch, capsys, onboarding_session):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_B})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_B})
    onboarding_session.commit()
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--health-check"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["mode"] == "health_check"
    assert payload["dry_run"] is True
    assert payload["tenant_count"] == 2
    assert payload["complete_count"] == 1
    assert payload["incomplete_count"] == 1
    assert payload["complete_tenants"] == [TENANT_A]
    assert payload["incomplete_tenants"][0]["tenant_id"] == TENANT_B
    assert payload["incomplete_tenants"][0]["would_create"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 0


def test_onboarding_script_health_check_can_include_optional_products(monkeypatch, capsys, onboarding_session):
    onboarding_session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TENANT_A})
    onboarding_session.execute(text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"), {"tenant_id": TENANT_A})
    onboarding_session.commit()
    onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False)
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--health-check", "--include-products"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["include_products"] is True
    assert payload["incomplete_count"] == 1
    assert payload["incomplete_tenants"][0]["would_create"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 0


def test_onboarding_script_blocks_production_apply(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = run_tenant_onboarding.main(
        ["--tenant-id", TENANT_A, "--user-id", "1", "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "production/prod" in payload["error"]


def test_onboarding_script_health_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--health-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]


def test_onboarding_script_future_tenant_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--future-tenant-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]
