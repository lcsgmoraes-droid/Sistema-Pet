"""Backfill: cria um grupo-de-1 para cada tenant ativo que nunca teve grupo.

A partir de agora, todo tenant nasce automaticamente dentro de um grupo
comercial (ver GrupoComercialService.criar_grupo, chamado pelo cadastro
publico). Esta migration cobre os tenants que ja existiam antes dessa
mudanca e nunca interagiram com o recurso.

So cria grupo para tenant com ZERO linha em grupo_comercial_membros — se o
tenant ja tem qualquer historico de grupo (inclusive membro removido), nao
mexe nele, para nao duplicar/conflitar com o que ja existe. Idempotente:
pode ser reexecutada com seguranca (reexecutar so preenche o que ainda
falta).

Downgrade e um no-op deliberado, nao silencioso: apagar os grupos-de-1
criados aqui e mais arriscado do que deixa-los, ja que a esta altura a
aplicacao ja pode estar usando-os (grupo comercial virou infraestrutura
obrigatoria, nao um recurso opcional que se possa simplesmente desligar).

Revision ID: zzx20260918a1
Revises: zzw20260918a1
Create Date: 2026-09-18
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "zzx20260918a1"
down_revision = "zzw20260918a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    agora = datetime.now(timezone.utc)

    tenants_sem_grupo = connection.execute(
        sa.text(
            """
            SELECT t.id, t.name
            FROM tenants t
            WHERE t.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM grupo_comercial_membros m
                  WHERE m.empresa_id = t.id
              )
            """
        )
    ).mappings()

    criados = 0
    pulados_sem_usuario = []

    for tenant in tenants_sem_grupo:
        usuario = connection.execute(
            sa.text(
                """
                SELECT user_id
                FROM user_tenants
                WHERE tenant_id = :tenant_id
                ORDER BY is_active DESC, created_at ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant["id"]},
        ).first()

        if usuario is None:
            pulados_sem_usuario.append(tenant["id"])
            continue

        usuario_id = usuario[0]
        grupo_id = connection.execute(
            sa.text(
                """
                INSERT INTO grupos_comerciais
                    (nome, criado_por_empresa_id, criado_por_usuario_id,
                     status, versao_membros, criado_em, atualizado_em)
                VALUES
                    (:nome, :empresa_id, :usuario_id, 'ativo', 1, :agora, :agora)
                RETURNING id
                """
            ),
            {
                "nome": tenant["name"] or "Grupo comercial",
                "empresa_id": tenant["id"],
                "usuario_id": usuario_id,
                "agora": agora,
            },
        ).scalar_one()

        connection.execute(
            sa.text(
                """
                INSERT INTO grupo_comercial_membros
                    (grupo_id, empresa_id, papel, status, usuario_referencia_id,
                     entrou_em)
                VALUES
                    (:grupo_id, :empresa_id, 'responsavel', 'ativo', :usuario_id,
                     :agora)
                """
            ),
            {
                "grupo_id": grupo_id,
                "empresa_id": tenant["id"],
                "usuario_id": usuario_id,
                "agora": agora,
            },
        )
        criados += 1

    if pulados_sem_usuario:
        print(
            f"[backfill grupo comercial] {len(pulados_sem_usuario)} tenant(s) sem "
            f"nenhum usuario em user_tenants, pulados: {pulados_sem_usuario}"
        )
    print(f"[backfill grupo comercial] {criados} grupo(s)-de-1 criado(s).")


def downgrade() -> None:
    # No-op deliberado — ver docstring do modulo.
    pass
