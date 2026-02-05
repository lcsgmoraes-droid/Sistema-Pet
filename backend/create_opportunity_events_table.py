"""
Script para criar tabela opportunity_events diretamente no PostgreSQL
"""
import psycopg2

conn = psycopg2.connect('postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db')
cur = conn.cursor()

print("Criando enum opportunity_event_type_enum...")
# Criar enum
cur.execute("""
    DO $$ BEGIN
        CREATE TYPE opportunity_event_type_enum AS ENUM ('oportunidade_convertida', 'oportunidade_refinada', 'oportunidade_rejeitada');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
""")

print("Criando tabela opportunity_events...")
# Criar tabela
cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunity_events (
        id SERIAL PRIMARY KEY,
        tenant_id UUID NOT NULL,
        opportunity_id UUID NOT NULL,
        event_type opportunity_event_type_enum NOT NULL,
        user_id UUID NOT NULL,
        contexto VARCHAR(50) NOT NULL DEFAULT 'PDV',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        metadata JSONB
    );
""")

print("Criando índices...")
# Criar índices
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunity_events_tenant_id ON opportunity_events(tenant_id);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunity_events_tenant_type ON opportunity_events(tenant_id, event_type);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunity_events_tenant_created ON opportunity_events(tenant_id, created_at);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunity_events_tenant_user ON opportunity_events(tenant_id, user_id);')
cur.execute('CREATE INDEX IF NOT EXISTS ix_opportunity_events_opportunity_id ON opportunity_events(opportunity_id);')

conn.commit()
print('✅ Tabela opportunity_events criada com sucesso!')
cur.close()
conn.close()
