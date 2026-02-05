"""
Script para editar migration que adiciona tenant_id e role em users
"""
import os
from pathlib import Path
import re

versions_path = Path("alembic/versions")
files = sorted(versions_path.glob("*.py"), key=os.path.getmtime, reverse=True)

if not files:
    print("❌ Nenhuma migration encontrada.")
    exit(1)

migration_file = files[0]
print(f"📄 EDITANDO MIGRATION: {migration_file.name}")

content = migration_file.read_text(encoding="utf-8")

upgrade_block = '''def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects.postgresql import UUID
    import sqlalchemy as sa

    op.add_column(
        "users",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True)
    )

    op.add_column(
        "users",
        sa.Column("role", sa.String(length=50), nullable=True)
    )

    op.create_foreign_key(
        "fk_users_tenant",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT"
    )'''

downgrade_block = '''def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_users_tenant", "users", type_="foreignkey")
    op.drop_column("users", "role")
    op.drop_column("users", "tenant_id")'''

content = re.sub(
    r"def upgrade\(\) -> None:.*?(?=\n\ndef|\Z)",
    upgrade_block,
    content,
    count=1,
    flags=re.DOTALL
)

content = re.sub(
    r"def downgrade\(\) -> None:.*?(?=\Z)",
    downgrade_block,
    content,
    count=1,
    flags=re.DOTALL
)

migration_file.write_text(content, encoding="utf-8")

print("✅ Migration users ajustada com tenant_id e role")
print("------------------------------------------------------------------")
print("CONTEÚDO FINAL DA MIGRATION:\n")
print(content)
print("------------------------------------------------------------------")
print("AGORA:")
print("- COPIE TODO O OUTPUT")
print("- COLE NO CHAT PARA VALIDAÇÃO")
print("- NÃO RODE alembic upgrade ainda")
print("------------------------------------------------------------------")
