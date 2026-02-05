from app.config import get_database_url
from sqlalchemy import create_engine, text

engine = create_engine(get_database_url())

sqls = [
    # Criar ENUMs (usando DO block para verificar existência)
    """
    DO $$ BEGIN
        CREATE TYPE tipocusto AS ENUM ('DIRETO', 'INDIRETO_RATEAVEL', 'CORPORATIVO');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """,
    """
    DO $$ BEGIN
        CREATE TYPE baserateio AS ENUM ('FATURAMENTO', 'PEDIDOS', 'PERCENTUAL', 'MANUAL');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """,
    """
    DO $$ BEGIN
        CREATE TYPE escoporateio AS ENUM ('LOJA_FISICA', 'ONLINE', 'AMBOS');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """,
    
    # Criar tabela dre_subcategorias
    """
    CREATE TABLE IF NOT EXISTS dre_subcategorias (
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
    )
    """,
    
    # Criar índices
    "CREATE INDEX IF NOT EXISTS ix_dre_subcategorias_tenant_id ON dre_subcategorias(tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_dre_subcategorias_categoria_id ON dre_subcategorias(categoria_id)",
]

with engine.begin() as conn:
    for sql in sqls:
        print(f"Executando: {sql[:80]}...")
        conn.execute(text(sql))
    print("✅ Tabela dre_subcategorias criada com sucesso!")
