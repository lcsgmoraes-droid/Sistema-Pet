"""add explicit access permissions for clinical modules

Revision ID: zxm20260828a1
Revises: zxl20260828a1
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "zxm20260828a1"
down_revision = "zxl20260828a1"
branch_labels = None
depends_on = None


MODULE_PERMISSIONS = (
    ("banho_tosa.acessar", "Acessar modulo de banho e tosa"),
    ("veterinario.acessar", "Acessar modulo veterinario"),
)

ROLE_NAMES_BY_PERMISSION = {
    "banho_tosa.acessar": (
        "admin",
        "administrador",
        "gerente",
        "banho & tosa",
        "banho e tosa",
        "banhista",
        "tosador",
    ),
    "veterinario.acessar": (
        "admin",
        "administrador",
        "gerente",
        "veterinario",
        "veterinário",
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (code, description)
            VALUES (:code, :description)
            ON CONFLICT (code) DO UPDATE
            SET description = EXCLUDED.description
            """
        ),
        [
            {"code": code, "description": description}
            for code, description in MODULE_PERMISSIONS
        ],
    )

    for permission_code, role_names in ROLE_NAMES_BY_PERMISSION.items():
        bind.execute(
            sa.text(
                """
                INSERT INTO role_permissions (tenant_id, role_id, permission_id)
                SELECT roles.tenant_id, roles.id, permissions.id
                  FROM roles
                  JOIN permissions ON permissions.code = :permission_code
                 WHERE lower(roles.name) IN :role_names
                   AND NOT EXISTS (
                       SELECT 1
                         FROM role_permissions existing
                        WHERE existing.tenant_id = roles.tenant_id
                          AND existing.role_id = roles.id
                          AND existing.permission_id = permissions.id
                   )
                """
            ).bindparams(sa.bindparam("role_names", expanding=True)),
            {
                "permission_code": permission_code,
                "role_names": tuple(role_names),
            },
        )


def downgrade() -> None:
    """Preserve permission rows because tenant roles may already reference them."""
