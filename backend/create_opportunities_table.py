"""
Script para criar tabela opportunities diretamente no PostgreSQL
"""
import psycopg2

conn = psycopg2.connect('postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db')
cur = conn.cursor()

print("Criando enum tipo_oportunidade...")
# Criar enum
cur.execute("""
    DO $$ BEGIN
        CREATE TYPE tipo_oportunidade_enum AS ENUM ('cross_sell', 'up_sell', 'recorrencia');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
""")

print("Criando tabela opportunities...")
# Criar tabela
cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id SERIAL PRIMARY KEY,
        tenant_id UUID NOT NULL,
        cliente_id UUID,
        contexto VARCHAR(50) NOT NULL DEFAULT 'PDV',
        tipo tipo_oportunidade_enum NOT NULL,
        produto_origem_id UUID NOT NULL,
        produto_sugerido_id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        extra_data JSONB
    );
""")

print("Criando índices...")
# Criar índices
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_tenant_id ON opportunities(tenant_id);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_tenant_tipo ON opportunities(tenant_id, tipo);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_tenant_created ON opportunities(tenant_id, created_at);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_tenant_cliente ON opportunities(tenant_id, cliente_id);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_tenant_contexto ON opportunities(tenant_id, contexto);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunities_cliente_id ON opportunities(cliente_id);')

conn.commit()
print('✅ Tabela opportunities criada com sucesso!')
cur.close()
conn.close()
