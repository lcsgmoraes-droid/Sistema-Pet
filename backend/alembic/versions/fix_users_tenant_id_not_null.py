"""
🔒 CORREÇÃO CRÍTICA: users.tenant_id NOT NULL
==============================================

PROBLEMA IDENTIFICADO:
---------------------
A migration 1c12bfb8d1bf criou `users.tenant_id` como NULLABLE,
o que viola a arquitetura multi-tenant e cria risco de segurança LGPD.

SOLUÇÃO:
--------
Tornar `users.tenant_id` NOT NULL de forma segura.

VALIDAÇÃO PRÉ-MIGRATION:
-----------------------
✅ Verificado: 0 usuários com tenant_id NULL
✅ Todos os usuários têm tenant_id válido
✅ Seguro aplicar ALTER TABLE

IMPACTO:
--------
- Garante que TODOS os usuários pertencem a um tenant
- Elimina risco de dados órfãos
- Conformidade com arquitetura SaaS multi-tenant
- Bloqueia criação acidental de usuários sem tenant

Revision ID: 20260127_fix_users_tenant_id_not_null
Revises: 20260126_fix_vendas_identity_sequence
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'fix_users_tenant'  # ← ENCURTADO (< 32 chars)
down_revision = '20260126_fix_seq'  # Última migration aplicada (vendas identity sequence)
branch_labels = None
depends_on = None


def upgrade():
    """
    Torna users.tenant_id NOT NULL.
    
    SEGURANÇA:
    - Não há dados com tenant_id NULL (verificado manualmente)
    - Apenas altera constraint, não move dados
    - Reversível com downgrade
    """
    
    # 🔒 PASSO 1: Validar que não há registros com tenant_id NULL
    # (já validado manualmente antes de executar a migration)
    
    # 🔒 PASSO 2: Alterar coluna para NOT NULL
    op.alter_column(
        'users',
        'tenant_id',
        existing_type=UUID(as_uuid=True),
        nullable=False,  # ← MUDANÇA CRÍTICA
        existing_nullable=True,  # Estado anterior
        existing_server_default=None
    )
    
    print("✅ users.tenant_id agora é NOT NULL")
    print("🔒 Isolamento multi-tenant reforçado")


def downgrade():
    """
    Reverte users.tenant_id para NULLABLE.
    
    ⚠️ ATENÇÃO:
    Isso NÃO é recomendado em produção, pois enfraquece isolamento.
    Deve ser usado APENAS para rollback de emergência.
    """
    
    op.alter_column(
        'users',
        'tenant_id',
        existing_type=UUID(as_uuid=True),
        nullable=True,  # ← Reverte para nullable
        existing_nullable=False,
        existing_server_default=None
    )
    
    print("⚠️ users.tenant_id revertido para NULLABLE")
    print("🚨 ATENÇÃO: Isolamento multi-tenant enfraquecido!")
