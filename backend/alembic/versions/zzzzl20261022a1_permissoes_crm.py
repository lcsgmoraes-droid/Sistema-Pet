"""permissoes do modulo CRM e backfill para quem ja usa o WhatsApp

Revision ID: zzzzl20261022a1
Revises: zzzzk20261022a1
Create Date: 2026-10-22

CRM etapa 1.3. Cria as permissoes do modulo e libera, sem bloquear ninguem,
quem hoje ja opera o WhatsApp (perfis com `ia.whatsapp`):

- `crm.visualizar`, `crm.atender`, `crm.leads`: todo perfil com `ia.whatsapp`;
- `crm.configurar`: so perfis com `ia.whatsapp` que tambem administram
  (`usuarios.manage` ou `configuracoes.editar`);
- `crm.todas_lojas` nao e concedida automaticamente (decisao do gestor).

As permissoes nao se propagam sozinhas para perfis existentes; por isso o backfill.
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzzl20261022a1"
down_revision = "zzzzk20261022a1"
branch_labels = None
depends_on = None

PERMISSION_CATALOG = (
    ("crm.visualizar", "Ver o CRM: funil de leads, ficha do tutor e conversas"),
    ("crm.atender", "Atender tutores no CRM: responder conversas e assumir da IA"),
    ("crm.leads", "Criar, mover e encerrar leads e oportunidades no CRM"),
    ("crm.configurar", "Configurar o CRM: funil, canal de WhatsApp e automacoes"),
    ("crm.todas_lojas", "Ver o CRM de todas as lojas a que o usuario tem acesso"),
)

_CONCESSOES = (
    ("crm.visualizar", ("ia.whatsapp",), ()),
    ("crm.atender", ("ia.whatsapp",), ()),
    ("crm.leads", ("ia.whatsapp",), ()),
    ("crm.configurar", ("ia.whatsapp",), ("usuarios.manage", "configuracoes.editar")),
)


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
            for code, description in PERMISSION_CATALOG
        ],
    )

    for nova, exige_todas, exige_alguma in _CONCESSOES:
        filtro_alguma = ""
        if exige_alguma:
            filtro_alguma = """
              AND EXISTS (
                SELECT 1 FROM role_permissions rp2
                JOIN permissions p2 ON p2.id = rp2.permission_id
                WHERE rp2.role_id = rp.role_id
                  AND rp2.tenant_id = rp.tenant_id
                  AND p2.code IN :exige_alguma
              )"""
        comando = sa.text(
            f"""
            INSERT INTO role_permissions (role_id, permission_id, tenant_id)
            SELECT DISTINCT rp.role_id, nova.id, rp.tenant_id
            FROM role_permissions rp
            JOIN permissions base ON base.id = rp.permission_id
            JOIN permissions nova ON nova.code = :nova
            WHERE base.code IN :exige_todas
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions ja
                WHERE ja.role_id = rp.role_id
                  AND ja.permission_id = nova.id
                  AND ja.tenant_id = rp.tenant_id
              ){filtro_alguma}
            """
        )
        parametros = {"nova": nova, "exige_todas": tuple(exige_todas)}
        comando = comando.bindparams(sa.bindparam("exige_todas", expanding=True))
        if exige_alguma:
            parametros["exige_alguma"] = tuple(exige_alguma)
            comando = comando.bindparams(sa.bindparam("exige_alguma", expanding=True))
        bind.execute(comando, parametros)


def downgrade() -> None:
    """Preserva as permissoes: perfis dos clientes podem ja referencia-las."""
