"""add_tenant_integrity_constraints

Revision ID: 643784162d15
Revises: 8cf34a927c2e
Create Date: 2026-01-26 20:55:49.439420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '643784162d15'
down_revision: Union[str, Sequence[str], None] = '8cf34a927c2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona constraints de integridade tenant-aware.
    
    Validações implementadas:
    - Vendas só podem referenciar clientes do mesmo tenant
    - Venda_itens só podem referenciar vendas do mesmo tenant
    - Protege contra cross-tenant data leaks
    
    Suporta PostgreSQL (triggers) e SQLite (validação em código)
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    print(f"📋 Detectado banco de dados: {dialect}")
    
    if dialect == 'postgresql':
        print("🔧 Criando triggers PostgreSQL para validação tenant-aware...")
        
        # VENDAS -> CLIENTES
        op.execute("""
            CREATE OR REPLACE FUNCTION check_venda_cliente_tenant()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM clientes c
                    WHERE c.id = NEW.cliente_id
                    AND c.tenant_id <> NEW.tenant_id
                ) THEN
                    RAISE EXCEPTION 'Tenant mismatch: venda x cliente';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER trg_venda_cliente_tenant
            BEFORE INSERT OR UPDATE ON vendas
            FOR EACH ROW
            EXECUTE FUNCTION check_venda_cliente_tenant();
        """)
        print("✅ Trigger: vendas <-> clientes")
        
        # VENDA_ITENS -> VENDAS
        op.execute("""
            CREATE OR REPLACE FUNCTION check_venda_item_tenant()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM vendas v
                    WHERE v.id = NEW.venda_id
                    AND v.tenant_id <> NEW.tenant_id
                ) THEN
                    RAISE EXCEPTION 'Tenant mismatch: venda_item x venda';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER trg_venda_item_tenant
            BEFORE INSERT OR UPDATE ON venda_itens
            FOR EACH ROW
            EXECUTE FUNCTION check_venda_item_tenant();
        """)
        print("✅ Trigger: venda_itens <-> vendas")
        
        # VENDA_ITENS -> PRODUTOS
        op.execute("""
            CREATE OR REPLACE FUNCTION check_venda_item_produto_tenant()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM produtos p
                    WHERE p.id = NEW.produto_id
                    AND p.tenant_id <> NEW.tenant_id
                ) THEN
                    RAISE EXCEPTION 'Tenant mismatch: venda_item x produto';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER trg_venda_item_produto_tenant
            BEFORE INSERT OR UPDATE ON venda_itens
            FOR EACH ROW
            EXECUTE FUNCTION check_venda_item_produto_tenant();
        """)
        print("✅ Trigger: venda_itens <-> produtos")
        
        # PETS -> CLIENTES
        op.execute("""
            CREATE OR REPLACE FUNCTION check_pet_cliente_tenant()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM clientes c
                    WHERE c.id = NEW.cliente_id
                    AND c.tenant_id <> NEW.tenant_id
                ) THEN
                    RAISE EXCEPTION 'Tenant mismatch: pet x cliente';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER trg_pet_cliente_tenant
            BEFORE INSERT OR UPDATE ON pets
            FOR EACH ROW
            EXECUTE FUNCTION check_pet_cliente_tenant();
        """)
        print("✅ Trigger: pets <-> clientes")
        
        print("✅ PostgreSQL: 4 triggers criados com sucesso")
        
    elif dialect == 'sqlite':
        print("ℹ️  SQLite: Triggers não implementados (validação em código)")
        print("ℹ️  A validação tenant-aware será feita no ORM e middleware")
        
    else:
        print(f"⚠️  Dialeto {dialect} não suportado para triggers tenant-aware")


def downgrade() -> None:
    """Remove constraints de integridade tenant-aware."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        print("🔧 Removendo triggers PostgreSQL...")
        
        op.execute("DROP TRIGGER IF EXISTS trg_pet_cliente_tenant ON pets")
        op.execute("DROP FUNCTION IF EXISTS check_pet_cliente_tenant")
        
        op.execute("DROP TRIGGER IF EXISTS trg_venda_item_produto_tenant ON venda_itens")
        op.execute("DROP FUNCTION IF EXISTS check_venda_item_produto_tenant")
        
        op.execute("DROP TRIGGER IF EXISTS trg_venda_item_tenant ON venda_itens")
        op.execute("DROP FUNCTION IF EXISTS check_venda_item_tenant")
        
        op.execute("DROP TRIGGER IF EXISTS trg_venda_cliente_tenant ON vendas")
        op.execute("DROP FUNCTION IF EXISTS check_venda_cliente_tenant")
        
        print("✅ PostgreSQL: Triggers removidos")
    else:
        print(f"ℹ️  {dialect}: Nenhuma operação necessária")

