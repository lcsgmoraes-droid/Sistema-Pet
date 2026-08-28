import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.whatsapp.models import WhatsAppMessage


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic/versions/zxj20260827a1_whatsapp_message_idempotency.py"
)
INDEX_NAME = "ux_whatsapp_ia_messages_tenant_provider_message"


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "whatsapp_idempotency_migration", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_model_declara_indice_unico_por_empresa_e_id_do_provedor():
    index = next(
        item for item in WhatsAppMessage.__table__.indexes if item.name == INDEX_NAME
    )

    assert index.unique is True
    assert [column.name for column in index.columns] == [
        "tenant_id",
        "whatsapp_message_id",
    ]


def test_migration_preserva_historico_e_bloqueia_nova_duplicacao():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("""
                CREATE TABLE whatsapp_ia_messages (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    whatsapp_message_id TEXT NULL
                )
                """)
        )
        connection.execute(
            text("""
                INSERT INTO whatsapp_ia_messages (id, tenant_id, whatsapp_message_id)
                VALUES
                    ('1', 'tenant-a', 'wamid.same'),
                    ('2', 'tenant-a', 'wamid.same'),
                    ('3', 'tenant-b', 'wamid.same'),
                    ('4', 'tenant-a', NULL),
                    ('5', 'tenant-a', NULL)
                """)
        )

        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        rows = connection.execute(
            text("""
                SELECT id, tenant_id, whatsapp_message_id
                FROM whatsapp_ia_messages
                ORDER BY id
                """)
        ).all()
        assert rows == [
            ("1", "tenant-a", "wamid.same"),
            ("2", "tenant-a", None),
            ("3", "tenant-b", "wamid.same"),
            ("4", "tenant-a", None),
            ("5", "tenant-a", None),
        ]

        with pytest.raises(IntegrityError):
            connection.execute(
                text("""
                    INSERT INTO whatsapp_ia_messages
                        (id, tenant_id, whatsapp_message_id)
                    VALUES ('6', 'tenant-a', 'wamid.same')
                    """)
            )

        migration.downgrade()
        connection.execute(
            text("""
                INSERT INTO whatsapp_ia_messages
                    (id, tenant_id, whatsapp_message_id)
                VALUES ('7', 'tenant-a', 'wamid.same')
                """)
        )


def test_migration_fica_na_unica_linha_de_evolucao_do_banco():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "zxj20260827a1"' in source
    assert 'down_revision = "zxi20260827a1"' in source
    assert "SET whatsapp_message_id = NULL" in source
    assert "GROUP BY tenant_id, whatsapp_message_id" in source
    assert INDEX_NAME in source
