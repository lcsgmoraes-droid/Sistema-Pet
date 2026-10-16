"""Usuario MASTER do grupo comercial + permissao de gestao do grupo +
remocao do fluxo de convite/codigo mensal entre empresas independentes
(decisao de produto: grupo so cresce por "adicionar loja" na propria tela
de gestao, dai em diante).

- `users.master_grupo_id`: FK opcional para o grupo comercial do qual este
  usuario e o master permanente (acesso total, sempre, a todas as lojas do
  proprio grupo). Nunca setado por nenhuma rota - so aqui, no backfill, e
  em `GrupoComercialService.criar_grupo`.
- `grupo_comercial_gestores`: usuarios com acesso a tela de gestao do grupo
  (ver/gerenciar lojas, billing consolidado), concedido/revogado somente
  pelo master.
- Backfill: todo grupo ja existente ganha seu master a partir do
  `GrupoComercialMembro` com `papel='responsavel'`. Usa
  `usuario_referencia_id` quando presente; como esse campo so existe desde
  22/08/2026 (zwx20260822a1) e nunca foi backfillado, cai para o usuario
  mais antigo com vinculo ativo em `user_tenants` para aquela empresa -
  mesma logica ja usada no backfill de grupo-de-1 (zzx20260918a1).
- Dropa `grupo_comercial_codigos`/`grupo_comercial_convites`: sem nenhum
  usuario, o fluxo de convite deixou de existir; as tabelas ficariam orfas.

Revision ID: zzzd20260920a1
Revises: zzzc20260920a1
Create Date: 2026-09-20
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzd20260920a1"
down_revision = "zzzc20260920a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("master_grupo_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_master_grupo_id_grupos_comerciais",
        "users",
        "grupos_comerciais",
        ["master_grupo_id"],
        ["id"],
    )
    op.create_index(
        "ix_users_master_grupo_id", "users", ["master_grupo_id"], unique=False
    )

    op.create_table(
        "grupo_comercial_gestores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concedido_por_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="ativo"
        ),
        sa.Column(
            "concedido_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "grupo_id", "user_id", name="uq_grupo_comercial_gestor_usuario"
        ),
    )
    op.create_index(
        "ix_grupo_comercial_gestores_grupo_id",
        "grupo_comercial_gestores",
        ["grupo_id"],
    )
    op.create_index(
        "ix_grupo_comercial_gestores_user_id",
        "grupo_comercial_gestores",
        ["user_id"],
    )

    connection = op.get_bind()
    responsaveis = connection.execute(
        sa.text(
            """
            SELECT grupo_id, empresa_id, usuario_referencia_id
            FROM grupo_comercial_membros
            WHERE papel = 'responsavel' AND status = 'ativo'
            """
        )
    ).mappings()

    grupos_sem_master = []
    for linha in responsaveis:
        usuario_id = linha["usuario_referencia_id"]
        if usuario_id is None:
            fallback = connection.execute(
                sa.text(
                    """
                    SELECT user_id
                    FROM user_tenants
                    WHERE tenant_id = :tenant_id
                    ORDER BY is_active DESC, created_at ASC
                    LIMIT 1
                    """
                ),
                {"tenant_id": linha["empresa_id"]},
            ).first()
            if fallback is None:
                grupos_sem_master.append(linha["grupo_id"])
                continue
            usuario_id = fallback[0]

        connection.execute(
            sa.text(
                "UPDATE users SET master_grupo_id = :grupo_id "
                "WHERE id = :usuario_id AND master_grupo_id IS NULL"
            ),
            {"grupo_id": linha["grupo_id"], "usuario_id": usuario_id},
        )

    if grupos_sem_master:
        print(
            f"[backfill master grupo comercial] {len(grupos_sem_master)} grupo(s) "
            f"sem nenhum usuario em user_tenants, pulados: {grupos_sem_master}"
        )

    op.drop_table("grupo_comercial_codigos")
    op.drop_table("grupo_comercial_convites")


def downgrade() -> None:
    # Downgrade nao recria grupo_comercial_codigos/grupo_comercial_convites
    # nem restaura os dados que estavam la - remocao deliberada de feature,
    # nao reversivel via migration (mesma decisao ja tomada em
    # zzx20260918a1 para o backfill de grupo-de-1).
    op.drop_index(
        "ix_grupo_comercial_gestores_user_id", table_name="grupo_comercial_gestores"
    )
    op.drop_index(
        "ix_grupo_comercial_gestores_grupo_id", table_name="grupo_comercial_gestores"
    )
    op.drop_table("grupo_comercial_gestores")
    op.drop_index("ix_users_master_grupo_id", table_name="users")
    op.drop_constraint(
        "fk_users_master_grupo_id_grupos_comerciais", "users", type_="foreignkey"
    )
    op.drop_column("users", "master_grupo_id")
