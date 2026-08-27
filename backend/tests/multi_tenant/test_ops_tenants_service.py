from datetime import datetime, timedelta, timezone

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
            onboarding_owner_name TEXT,
            onboarding_unblocked_on TEXT,
            onboarding_next_contact_on TEXT,
            onboarding_satisfaction TEXT NOT NULL DEFAULT 'not_collected',
            onboarding_follow_up_updated_at TEXT,
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
            email_verified BOOLEAN,
            last_login_at TEXT,
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
        "CREATE TABLE vet_agendamentos (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, created_at TEXT)",
        "CREATE TABLE vet_consultas (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, created_at TEXT)",
        "CREATE TABLE produto_imagens (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, tamanho INTEGER)",
        """
        CREATE TABLE ops_error_events (
            id INTEGER PRIMARY KEY, tenant_id TEXT, status_code INTEGER, created_at TEXT
        )
        """,
        """
        CREATE TABLE ops_alerts (
            id INTEGER PRIMARY KEY, tenant_id TEXT, severity TEXT, status TEXT
        )
        """,
        """
        CREATE TABLE ops_tenant_onboarding_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            note TEXT NOT NULL,
            next_contact_on TEXT,
            created_by_platform_admin_id INTEGER NOT NULL,
            created_by_label TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
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
        text("""
            INSERT INTO tenants (
                id, name, status, plan, billing_status, subscription_source,
                subscription_activated_at, organization_type,
                onboarding_owner_name, onboarding_unblocked_on,
                onboarding_satisfaction, created_at
            ) VALUES
            (:source, 'Atacadao das Racoes Pet', 'active', 'premium', 'active', 'manual', '2026-05-01', 'petshop', 'Lucas', NULL, 'not_collected', '2026-05-01'),
            (:target, 'Clinica Veterinaria Sao Jose', 'active', 'basico', 'past_due', 'manual', '2026-05-17', 'veterinary_clinic', 'Lucas', '2026-05-20', 'satisfied', '2026-05-17')
            """),
        {"source": SOURCE_TENANT, "target": TARGET_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO users (
                id, email, tenant_id, nome, is_active, is_admin,
                email_verified, last_login_at, created_at
            )
            VALUES
            (1, 'atacadaopetpp@gmail.com', :source, 'Lucas Admin', 1, 1, 1, '2026-07-12 10:00:00', '2026-05-01'),
            (10, 'maiaraalmeidaa42@hotmail.com', :target, 'Maiara Almeida', 1, 1, 1, '2026-07-13 09:00:00', '2026-05-17'),
            (11, 'vet@clinica.test', :target, 'Veterinario', 1, 0, 1, '2026-07-13 08:00:00', '2026-05-18')
            """),
        {"source": SOURCE_TENANT, "target": TARGET_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO user_tenants (id, tenant_id, user_id, role_id, is_active)
            VALUES (1, :target, 10, 1, 1), (2, :target, 11, 2, 1)
            """),
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
        text("""
            INSERT INTO produto_imagens (id, tenant_id, tamanho)
            VALUES (1, :target, 1048576), (2, :target, 524288)
            """),
        {"target": TARGET_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO tenant_template_installs (
                id, tenant_id, bundle_code, bundle_version, status, dry_run,
                created_by_user_id, summary, created_at, updated_at
            ) VALUES (
                1, :target, 'catalogo-base-loja-lucas', 'v1', 'completed', 0,
                10, :summary, '2026-05-19', '2026-05-19'
            )
            """),
        {"target": TARGET_TENANT, "summary": '{"created":{"produtos":3}}'},
    )
    session.execute(
        text("""
            INSERT INTO vet_agendamentos (id, tenant_id, created_at)
            VALUES (1, :target, '2026-07-12 14:00:00'), (2, :target, '2026-07-13 10:00:00')
            """),
        {"target": TARGET_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO vet_consultas (id, tenant_id, created_at)
            VALUES (1, :target, '2026-07-13 11:00:00')
            """),
        {"target": TARGET_TENANT},
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
        "agendamentos_vet": 2,
        "consultas_vet": 1,
        "usuarios": 2,
    }
    assert tenant["usage"] == {
        "records_total": 21,
        "image_count": 2,
        "image_bytes": 1572864,
        "image_mb": 1.5,
    }
    assert result["summary"]["billing_attention"] == 1
    assert result["summary"]["records_total"] == 21
    assert result["summary"]["image_bytes"] == 1572864
    assert tenant["base_catalog"]["installed"] is True
    assert tenant["base_catalog"]["status"] == "completed"
    assert tenant["pilot"]["kind"] == "veterinario"
    assert tenant["pilot"]["status"] == "active"
    assert tenant["pilot"]["access_confirmed"] is True
    assert tenant["pilot"]["operational_events"] == 8
    assert tenant["pilot"]["last_activity_at"] == "2026-07-13 11:00:00"
    assert tenant["pilot"]["errors_7d"] == 0
    assert tenant["pilot"]["critical_alerts_open"] == 0
    assert tenant["pilot"]["attention_level"] == "healthy"
    assert tenant["pilot"]["needs_follow_up"] is False
    assert tenant["pilot"]["attention_reasons"] == []
    assert tenant["pilot"]["next_action"] == "Manter acompanhamento semanal."
    assert tenant["onboarding_follow_up"] == {
        "owner_name": "Lucas",
        "unblocked_on": "2026-05-20",
        "next_contact_on": None,
        "satisfaction": "satisfied",
        "updated_at": None,
    }
    assert result["summary"]["pilots_active"] == 1
    assert result["summary"]["pilots_blocked"] == 0


def test_apply_base_catalog_import_requires_explicit_confirmation(ops_tenants_session):
    from app.services.ops_tenants_service import (
        OpsTenantActionError,
        apply_base_catalog_import,
    )

    with pytest.raises(OpsTenantActionError, match="confirmacao"):
        apply_base_catalog_import(
            ops_tenants_session,
            tenant_id=TARGET_TENANT,
            confirm=False,
        )


def test_list_ops_tenants_blocks_pilot_with_critical_alert(ops_tenants_session):
    from app.services.ops_tenants_service import list_ops_tenants

    ops_tenants_session.execute(
        text("""
            INSERT INTO ops_alerts (id, tenant_id, severity, status)
            VALUES (1, :target, 'critical', 'open')
            """),
        {"target": TARGET_TENANT},
    )
    ops_tenants_session.execute(
        text("""
            INSERT INTO ops_error_events (id, tenant_id, status_code, created_at)
            VALUES (1, :target, 500, :created_at)
            """),
        {"target": TARGET_TENANT, "created_at": datetime.now(timezone.utc)},
    )
    ops_tenants_session.commit()

    result = list_ops_tenants(ops_tenants_session, search="clinica")

    assert result["items"][0]["pilot"]["status"] == "blocked"
    assert result["items"][0]["pilot"]["critical_alerts_open"] == 1
    assert result["items"][0]["pilot"]["errors_7d"] == 1
    assert result["items"][0]["pilot"]["attention_level"] == "critical"
    assert result["items"][0]["pilot"]["needs_follow_up"] is True
    assert "alerta critico" in result["items"][0]["pilot"]["next_action"]
    assert result["summary"]["pilots_active"] == 0
    assert result["summary"]["pilots_blocked"] == 1


def test_list_ops_tenants_explains_overdue_onboarding_next_action(
    ops_tenants_session,
):
    from app.services.ops_tenants_service import list_ops_tenants

    result = list_ops_tenants(ops_tenants_session, search="Atacadao")

    pilot = result["items"][0]["pilot"]
    assert pilot["status"] == "pending"
    assert pilot["attention_level"] == "high"
    assert pilot["needs_follow_up"] is True
    assert pilot["overdue_milestones"] == ["D3", "D7"]
    assert [reason["code"] for reason in pilot["attention_reasons"]] == [
        "setup_pending",
        "first_operation_pending",
    ]
    assert "cadastros iniciais" in pilot["next_action"]
    assert result["summary"]["pilots_need_follow_up"] == 1


def test_active_pilot_with_recent_errors_gets_investigation_action(
    ops_tenants_session,
):
    from app.services.ops_tenants_service import list_ops_tenants

    ops_tenants_session.execute(
        text("""
            INSERT INTO ops_error_events (id, tenant_id, status_code, created_at)
            VALUES (2, :target, 500, :created_at)
            """),
        {"target": TARGET_TENANT, "created_at": datetime.now(timezone.utc)},
    )
    ops_tenants_session.commit()

    result = list_ops_tenants(ops_tenants_session, search="clinica")

    pilot = result["items"][0]["pilot"]
    assert pilot["status"] == "active"
    assert pilot["attention_level"] == "high"
    assert pilot["needs_follow_up"] is True
    assert pilot["attention_reasons"][0]["code"] == "recent_server_errors"
    assert "erros 5xx" in pilot["next_action"]


def test_active_pilot_without_owner_gets_follow_up_action(ops_tenants_session):
    from app.services.ops_tenants_service import list_ops_tenants

    ops_tenants_session.execute(
        text("""
            UPDATE tenants
            SET onboarding_owner_name = NULL,
                onboarding_satisfaction = 'not_collected'
            WHERE id = :tenant_id
            """),
        {"tenant_id": TARGET_TENANT},
    )
    ops_tenants_session.commit()

    pilot = list_ops_tenants(ops_tenants_session, search="clinica")["items"][0]["pilot"]

    assert pilot["attention_level"] == "normal"
    assert pilot["needs_follow_up"] is True
    assert [reason["code"] for reason in pilot["attention_reasons"]] == [
        "owner_pending",
        "initial_satisfaction_pending",
    ]
    assert "Definir o responsavel" in pilot["next_action"]


def test_dissatisfied_pilot_gets_recovery_action(ops_tenants_session):
    from app.services.ops_tenants_service import list_ops_tenants

    ops_tenants_session.execute(
        text("""
            UPDATE tenants
            SET onboarding_satisfaction = 'dissatisfied'
            WHERE id = :tenant_id
            """),
        {"tenant_id": TARGET_TENANT},
    )
    ops_tenants_session.commit()

    pilot = list_ops_tenants(ops_tenants_session, search="clinica")["items"][0]["pilot"]

    assert pilot["attention_level"] == "high"
    assert pilot["attention_reasons"][0]["code"] == "initial_dissatisfaction"
    assert "insatisfacao" in pilot["next_action"]


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

    row = (
        ops_tenants_session.execute(
            text("""
            SELECT status, plan, billing_status, subscription_source
            FROM tenants
            WHERE id = :tenant_id
            """),
            {"tenant_id": TARGET_TENANT},
        )
        .mappings()
        .first()
    )
    assert dict(row) == {
        "status": "suspended",
        "plan": "premium",
        "billing_status": "past_due",
        "subscription_source": "manual",
    }


def test_update_ops_tenant_commercial_state_rejects_invalid_values(ops_tenants_session):
    from app.services.ops_tenants_service import (
        OpsTenantActionError,
        update_ops_tenant_commercial_state,
    )

    with pytest.raises(OpsTenantActionError, match="Plano invalido"):
        update_ops_tenant_commercial_state(
            ops_tenants_session,
            tenant_id=TARGET_TENANT,
            changes={"plan": "plano sem cadastro"},
        )


def test_update_ops_tenant_onboarding_follow_up_saves_safe_fields(
    ops_tenants_session,
):
    from app.services.ops_tenants_service import (
        _business_today,
        update_ops_tenant_onboarding_follow_up,
    )

    next_contact_on = (_business_today() + timedelta(days=7)).isoformat()
    tenant = update_ops_tenant_onboarding_follow_up(
        ops_tenants_session,
        tenant_id=TARGET_TENANT,
        changes={
            "onboarding_owner_name": "  Ana Operacoes  ",
            "onboarding_unblocked_on": "2026-08-27",
            "onboarding_next_contact_on": next_contact_on,
            "onboarding_satisfaction": "neutral",
        },
    )

    assert tenant["onboarding_follow_up"]["owner_name"] == "Ana Operacoes"
    assert tenant["onboarding_follow_up"]["unblocked_on"] == "2026-08-27"
    assert tenant["onboarding_follow_up"]["next_contact_on"] == next_contact_on
    assert tenant["onboarding_follow_up"]["satisfaction"] == "neutral"
    assert tenant["onboarding_follow_up"]["updated_at"] is not None
    assert tenant["pilot"]["attention_level"] == "normal"
    assert "empresa ficar satisfeita" in tenant["pilot"]["next_action"]


def test_update_ops_tenant_onboarding_follow_up_rejects_invalid_satisfaction(
    ops_tenants_session,
):
    from app.services.ops_tenants_service import (
        OpsTenantActionError,
        update_ops_tenant_onboarding_follow_up,
    )

    with pytest.raises(OpsTenantActionError, match="Satisfacao inicial invalida"):
        update_ops_tenant_onboarding_follow_up(
            ops_tenants_session,
            tenant_id=TARGET_TENANT,
            changes={"onboarding_satisfaction": "excelente"},
        )


def test_overdue_scheduled_contact_enters_follow_up_queue(ops_tenants_session):
    from app.services.ops_tenants_service import _business_today, list_ops_tenants

    overdue_on = (_business_today() - timedelta(days=1)).isoformat()
    ops_tenants_session.execute(
        text("""
            UPDATE tenants
            SET onboarding_next_contact_on = :overdue_on
            WHERE id = :tenant_id
            """),
        {"tenant_id": TARGET_TENANT, "overdue_on": overdue_on},
    )
    ops_tenants_session.commit()

    pilot = list_ops_tenants(ops_tenants_session, search="clinica")["items"][0]["pilot"]

    assert pilot["attention_level"] == "high"
    assert pilot["attention_reasons"][0]["code"] == "follow_up_overdue"
    assert "contato de acompanhamento" in pilot["next_action"]


def test_onboarding_notes_are_append_only_scoped_and_keep_author_snapshot(
    ops_tenants_session,
):
    from app.services.ops_tenants_service import (
        _business_today,
        create_ops_tenant_onboarding_note,
        list_ops_tenant_onboarding_notes,
        update_ops_tenant_onboarding_follow_up,
    )

    next_contact_on = (_business_today() + timedelta(days=3)).isoformat()
    update_ops_tenant_onboarding_follow_up(
        ops_tenants_session,
        tenant_id=TARGET_TENANT,
        changes={"onboarding_next_contact_on": next_contact_on},
    )
    created = create_ops_tenant_onboarding_note(
        ops_tenants_session,
        tenant_id=TARGET_TENANT,
        note="  Primeiro contato realizado; acesso validado.  ",
        platform_admin_id=7,
        platform_admin_label="Lucas Operacoes",
    )
    create_ops_tenant_onboarding_note(
        ops_tenants_session,
        tenant_id=SOURCE_TENANT,
        note="Contato de outra empresa.",
        platform_admin_id=7,
        platform_admin_label="Lucas Operacoes",
    )
    ops_tenants_session.commit()

    notes = list_ops_tenant_onboarding_notes(
        ops_tenants_session,
        tenant_id=TARGET_TENANT,
    )

    assert created["note"] == "Primeiro contato realizado; acesso validado."
    assert created["next_contact_on"] == next_contact_on
    assert created["created_by"] == {
        "platform_admin_id": 7,
        "label": "Lucas Operacoes",
    }
    assert [item["id"] for item in notes] == [created["id"]]


def test_onboarding_note_rejects_blank_or_oversized_text(ops_tenants_session):
    from app.services.ops_tenants_service import (
        OpsTenantActionError,
        create_ops_tenant_onboarding_note,
    )

    common = {
        "db": ops_tenants_session,
        "tenant_id": TARGET_TENANT,
        "platform_admin_id": 7,
        "platform_admin_label": "Lucas Operacoes",
    }
    with pytest.raises(OpsTenantActionError, match="pelo menos 3"):
        create_ops_tenant_onboarding_note(note="   ", **common)
    with pytest.raises(OpsTenantActionError, match="no maximo 1000"):
        create_ops_tenant_onboarding_note(note="x" * 1001, **common)


def test_preview_base_catalog_import_uses_lucas_store_as_source(
    ops_tenants_session, monkeypatch
):
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

    monkeypatch.setattr(
        ops_tenants_service, "import_base_catalog", fake_import_base_catalog
    )

    result = ops_tenants_service.preview_base_catalog_import(
        ops_tenants_session, tenant_id=TARGET_TENANT
    )

    assert result["dry_run"] is True
    assert calls[0]["source_tenant_id"] == SOURCE_TENANT
    assert calls[0]["target_tenant_id"] == TARGET_TENANT
    assert calls[0]["user_id"] == 10
