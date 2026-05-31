import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"
TARGET_TENANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def ops_tenants_session():
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
            name TEXT NOT NULL,
            status TEXT,
            plan TEXT,
            billing_status TEXT,
            subscription_source TEXT,
            subscription_activated_at TEXT,
            organization_type TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            tenant_id TEXT,
            nome TEXT,
            is_active BOOLEAN,
            is_admin BOOLEAN,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE user_tenants (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role_id INTEGER,
            is_active BOOLEAN
        )
        """,
        "CREATE TABLE produtos (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL)",
        "CREATE TABLE clientes (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL)",
        "CREATE TABLE pets (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL)",
        "CREATE TABLE vendas (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, total REAL)",
        "CREATE TABLE produto_imagens (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, tamanho INTEGER)",
        """
        CREATE TABLE tenant_template_installs (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            status TEXT NOT NULL,
            dry_run BOOLEAN NOT NULL,
            created_by_user_id INTEGER,
            summary TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
    ]
    for statement in ddl:
        session.execute(text(statement))

    session.execute(
        text(
            """
            INSERT INTO tenants (
                id, name, status, plan, billing_status, subscription_source,
                subscription_activated_at, organization_type, created_at
            ) VALUES
            (:source, 'Atacadao das Racoes Pet', 'active', 'premium', 'active', 'manual', '2026-05-01', 'petshop', '2026-05-01'),
            (:target, 'Clinica Veterinaria Sao Jose', 'active', 'basico', 'past_due', 'manual', '2026-05-17', 'veterinary_clinic', '2026-05-17')
            """
        ),
        {"source": SOURCE_TENANT, "target": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO users (id, email, tenant_id, nome, is_active, is_admin, created_at)
            VALUES
            (1, 'atacadaopetpp@gmail.com', :source, 'Lucas Admin', 1, 1, '2026-05-01'),
            (10, 'maiaraalmeidaa42@hotmail.com', :target, 'Maiara Almeida', 1, 1, '2026-05-17'),
            (11, 'vet@clinica.test', :target, 'Veterinario', 1, 0, '2026-05-18')
            """
        ),
        {"source": SOURCE_TENANT, "target": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO user_tenants (id, tenant_id, user_id, role_id, is_active)
            VALUES (1, :target, 10, 1, 1), (2, :target, 11, 2, 1)
            """
        ),
        {"target": TARGET_TENANT},
    )
    for table_name, rows in {
        "produtos": 3,
        "clientes": 2,
        "pets": 4,
        "vendas": 5,
    }.items():
        for row_id in range(1, rows + 1):
            session.execute(
                text(f"INSERT INTO {table_name} (id, tenant_id) VALUES (:id, :tenant)"),
                {"id": row_id, "tenant": TARGET_TENANT},
            )
    session.execute(
        text(
            """
            INSERT INTO produto_imagens (id, tenant_id, tamanho)
            VALUES (1, :target, 1048576), (2, :target, 524288)
            """
        ),
        {"target": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO tenant_template_installs (
                id, tenant_id, bundle_code, bundle_version, status, dry_run,
                created_by_user_id, summary, created_at, updated_at
            ) VALUES (
                1, :target, 'catalogo-base-loja-lucas', 'v1', 'completed', 0,
                10, :summary, '2026-05-19', '2026-05-19'
            )
            """
        ),
        {"target": TARGET_TENANT, "summary": '{"created":{"produtos":3}}'},
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_list_ops_tenants_returns_counts_and_catalog_status(ops_tenants_session):
    from app.services.ops_tenants_service import list_ops_tenants

    result = list_ops_tenants(ops_tenants_session, search="clinica")

    assert result["summary"]["total"] == 1
    assert result["summary"]["active"] == 1
    tenant = result["items"][0]
    assert tenant["id"] == TARGET_TENANT
    assert tenant["name"] == "Clinica Veterinaria Sao Jose"
    assert tenant["plan"] == "basico"
    assert tenant["billing_status"] == "past_due"
    assert tenant["principal_user"]["email"] == "maiaraalmeidaa42@hotmail.com"
    assert tenant["counts"] == {
        "produtos": 3,
        "clientes": 2,
        "pets": 4,
        "vendas": 5,
        "produto_imagens": 2,
        "usuarios": 2,
    }
    assert tenant["usage"] == {
        "records_total": 18,
        "image_count": 2,
        "image_bytes": 1572864,
        "image_mb": 1.5,
    }
    assert result["summary"]["billing_attention"] == 1
    assert result["summary"]["records_total"] == 18
    assert result["summary"]["image_bytes"] == 1572864
    assert tenant["base_catalog"]["installed"] is True
    assert tenant["base_catalog"]["status"] == "completed"


def test_apply_base_catalog_import_requires_explicit_confirmation(ops_tenants_session):
    from app.services.ops_tenants_service import OpsTenantActionError, apply_base_catalog_import

    with pytest.raises(OpsTenantActionError, match="confirmacao"):
        apply_base_catalog_import(
            ops_tenants_session,
            tenant_id=TARGET_TENANT,
            actor_user_id=99,
            confirm=False,
        )


def test_update_ops_tenant_commercial_state_changes_safe_fields(ops_tenants_session):
    from app.services.ops_tenants_service import update_ops_tenant_commercial_state

    tenant = update_ops_tenant_commercial_state(
        ops_tenants_session,
        tenant_id=TARGET_TENANT,
        changes={
            "status": "suspended",
            "plan": "premium",
            "billing_status": "past_due",
            "subscription_source": "manual",
        },
    )

    assert tenant["id"] == TARGET_TENANT
    assert tenant["status"] == "suspended"
    assert tenant["plan"] == "premium"
    assert tenant["billing_status"] == "past_due"
    assert tenant["subscription_source"] == "manual"

    row = ops_tenants_session.execute(
        text(
            """
            SELECT status, plan, billing_status, subscription_source
            FROM tenants
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": TARGET_TENANT},
    ).mappings().first()
    assert dict(row) == {
        "status": "suspended",
        "plan": "premium",
        "billing_status": "past_due",
        "subscription_source": "manual",
    }


def test_update_ops_tenant_commercial_state_rejects_invalid_values(ops_tenants_session):
    from app.services.ops_tenants_service import OpsTenantActionError, update_ops_tenant_commercial_state

    with pytest.raises(OpsTenantActionError, match="Plano invalido"):
        update_ops_tenant_commercial_state(
            ops_tenants_session,
            tenant_id=TARGET_TENANT,
            changes={"plan": "plano sem cadastro"},
        )


def test_preview_base_catalog_import_uses_lucas_store_as_source(ops_tenants_session, monkeypatch):
    from app.services import ops_tenants_service

    calls = []

    def fake_import_base_catalog(**kwargs):
        calls.append(kwargs)
        return {
            "ok": True,
            "dry_run": kwargs["dry_run"],
            "source_tenant_id": kwargs["source_tenant_id"],
            "target_tenant_id": kwargs["target_tenant_id"],
            "would_create": {"produtos": 1},
            "created": {},
            "skipped": {},
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr(ops_tenants_service, "import_base_catalog", fake_import_base_catalog)

    result = ops_tenants_service.preview_base_catalog_import(ops_tenants_session, tenant_id=TARGET_TENANT)

    assert result["dry_run"] is True
    assert calls[0]["source_tenant_id"] == SOURCE_TENANT
    assert calls[0]["target_tenant_id"] == TARGET_TENANT
    assert calls[0]["user_id"] == 10
