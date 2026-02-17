"""adiciona dre_categorias e dre_subcategorias

Revision ID: 20260129_dre_plano_contas
Revises: 31c2dae52880
Create Date: 2026-01-29 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '20260129_dre_plano_contas'
down_revision: Union[str, Sequence[str], None] = '31c2dae52880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tabelas de plano de contas DRE (multi-tenant seguro)"""
    
    # 🔥 SOLUÇÃO DEFINITIVA: SQL PURO (SEM op.create_table)
    # SQLAlchemy Table objects disparam eventos que tentam criar ENUMs
    # Única forma garantida: DDL direto
    
    # 1️⃣ Criar ENUMs
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'naturezadre') THEN
            CREATE TYPE naturezadre AS ENUM ('RECEITA', 'CUSTO', 'DESPESA', 'RESULTADO');
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipocusto') THEN
            CREATE TYPE tipocusto AS ENUM ('DIRETO', 'INDIRETO_RATEAVEL', 'CORPORATIVO');
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'baserateio') THEN
            CREATE TYPE baserateio AS ENUM ('FATURAMENTO', 'PEDIDOS', 'PERCENTUAL', 'MANUAL');
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'escoporateio') THEN
            CREATE TYPE escoporateio AS ENUM ('LOJA_FISICA', 'ONLINE', 'AMBOS');
        END IF;
    END
    $$;
    """)

    # 2️⃣ Criar tabela dre_categorias (SQL puro) - DROP primeiro para garantir estrutura correta
    op.execute("""
        DROP TABLE IF EXISTS dre_categorias CASCADE;
        
        CREATE TABLE dre_categorias (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL,
            nome VARCHAR(100) NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            natureza naturezadre NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        
        CREATE INDEX ix_dre_categorias_tenant_id ON dre_categorias(tenant_id);
    """)

    # 3️⃣ Criar tabela dre_subcategorias (SQL puro) - DROP primeiro para garantir estrutura correta
    op.execute("""
        DROP TABLE IF EXISTS dre_subcategorias CASCADE;
        
        CREATE TABLE dre_subcategorias (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL,
            categoria_id INTEGER NOT NULL,
            nome VARCHAR(150) NOT NULL,
            tipo_custo tipocusto NOT NULL,
            base_rateio baserateio,
            escopo_rateio escoporateio NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        
        CREATE INDEX ix_dre_subcategorias_tenant_id ON dre_subcategorias(tenant_id);
        CREATE INDEX ix_dre_subcategorias_categoria_id ON dre_subcategorias(categoria_id);
    """)

    # 4️⃣ Adicionar coluna em categorias_financeiras
    op.execute("""
        ALTER TABLE categorias_financeiras
        ADD COLUMN IF NOT EXISTS dre_subcategoria_id INTEGER;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_categorias_financeiras_dre_subcategoria_id
        ON categorias_financeiras(dre_subcategoria_id);
    """)


def downgrade() -> None:
    """Remove estrutura do plano de contas DRE"""

    # Remove coluna e índice
    op.execute("""
        DROP INDEX IF EXISTS ix_categorias_financeiras_dre_subcategoria_id;
    """)
    
    op.execute("""
        ALTER TABLE categorias_financeiras DROP COLUMN IF EXISTS dre_subcategoria_id;
    """)

    # Remove tabelas
    op.execute("""
        DROP TABLE IF EXISTS dre_subcategorias;
    """)
    
    op.execute("""
        DROP TABLE IF EXISTS dre_categorias;
    """)

    # Remove ENUMs
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'escoporateio') THEN
            DROP TYPE escoporateio;
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'baserateio') THEN
            DROP TYPE baserateio;
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipocusto') THEN
            DROP TYPE tipocusto;
        END IF;
    END
    $$;
    """)
    
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'naturezadre') THEN
            DROP TYPE naturezadre;
        END IF;
    END
    $$;
    """)
