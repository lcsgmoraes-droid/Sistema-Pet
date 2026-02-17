"""add_opcoes_racao_tables

Revision ID: 20260215_add_opcoes_racao_tables
Revises: 20260215_add_racao_jsonb_fields
Create Date: 2026-02-15 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260215_add_opcoes_racao_tables'
down_revision: Union[str, Sequence[str], None] = '20260215_add_racao_jsonb_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_linhas_racao() -> None:
    op.create_table(
        'linhas_racao',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_linhas_racao_tenant_id', 'linhas_racao', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_linhas_racao_nome', 'linhas_racao', ['nome'], if_not_exists=True)


def _create_portes_animal() -> None:
    op.create_table(
        'portes_animal',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_portes_animal_tenant_id', 'portes_animal', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_portes_animal_nome', 'portes_animal', ['nome'], if_not_exists=True)


def _create_fases_publico() -> None:
    op.create_table(
        'fases_publico',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_fases_publico_tenant_id', 'fases_publico', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_fases_publico_nome', 'fases_publico', ['nome'], if_not_exists=True)


def _create_tipos_tratamento() -> None:
    op.create_table(
        'tipos_tratamento',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_tipos_tratamento_tenant_id', 'tipos_tratamento', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_tipos_tratamento_nome', 'tipos_tratamento', ['nome'], if_not_exists=True)


def _create_sabores_proteina() -> None:
    op.create_table(
        'sabores_proteina',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_sabores_proteina_tenant_id', 'sabores_proteina', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_sabores_proteina_nome', 'sabores_proteina', ['nome'], if_not_exists=True)


def _create_apresentacoes_peso() -> None:
    op.create_table(
        'apresentacoes_peso',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('peso_kg', sa.Float, nullable=False),
        sa.Column('descricao', sa.String(100), nullable=True),
        sa.Column('ordem', sa.Integer, server_default='0'),
        sa.Column('ativo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_apresentacoes_peso_tenant_id', 'apresentacoes_peso', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_apresentacoes_peso_peso_kg', 'apresentacoes_peso', ['peso_kg'], if_not_exists=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('linhas_racao'):
        _create_linhas_racao()

    if not inspector.has_table('portes_animal'):
        _create_portes_animal()

    if not inspector.has_table('fases_publico'):
        _create_fases_publico()

    if not inspector.has_table('tipos_tratamento'):
        _create_tipos_tratamento()

    if not inspector.has_table('sabores_proteina'):
        _create_sabores_proteina()

    if not inspector.has_table('apresentacoes_peso'):
        _create_apresentacoes_peso()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('apresentacoes_peso'):
        op.drop_index('ix_apresentacoes_peso_peso_kg', table_name='apresentacoes_peso', if_exists=True)
        op.drop_index('ix_apresentacoes_peso_tenant_id', table_name='apresentacoes_peso', if_exists=True)
        op.drop_table('apresentacoes_peso')

    if inspector.has_table('sabores_proteina'):
        op.drop_index('ix_sabores_proteina_nome', table_name='sabores_proteina', if_exists=True)
        op.drop_index('ix_sabores_proteina_tenant_id', table_name='sabores_proteina', if_exists=True)
        op.drop_table('sabores_proteina')

    if inspector.has_table('tipos_tratamento'):
        op.drop_index('ix_tipos_tratamento_nome', table_name='tipos_tratamento', if_exists=True)
        op.drop_index('ix_tipos_tratamento_tenant_id', table_name='tipos_tratamento', if_exists=True)
        op.drop_table('tipos_tratamento')

    if inspector.has_table('fases_publico'):
        op.drop_index('ix_fases_publico_nome', table_name='fases_publico', if_exists=True)
        op.drop_index('ix_fases_publico_tenant_id', table_name='fases_publico', if_exists=True)
        op.drop_table('fases_publico')

    if inspector.has_table('portes_animal'):
        op.drop_index('ix_portes_animal_nome', table_name='portes_animal', if_exists=True)
        op.drop_index('ix_portes_animal_tenant_id', table_name='portes_animal', if_exists=True)
        op.drop_table('portes_animal')

    if inspector.has_table('linhas_racao'):
        op.drop_index('ix_linhas_racao_nome', table_name='linhas_racao', if_exists=True)
        op.drop_index('ix_linhas_racao_tenant_id', table_name='linhas_racao', if_exists=True)
        op.drop_table('linhas_racao')
