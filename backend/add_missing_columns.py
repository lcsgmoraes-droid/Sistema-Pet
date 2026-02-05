"""
Adiciona colunas faltantes na tabela cliente_segmentos
"""
from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    print("Adicionando colunas faltantes...")
    
    # Adicionar user_id
    db.execute(text("ALTER TABLE cliente_segmentos ADD COLUMN IF NOT EXISTS user_id INTEGER"))
    print("✅ user_id")
    
    # Adicionar metricas
    db.execute(text("ALTER TABLE cliente_segmentos ADD COLUMN IF NOT EXISTS metricas JSONB NOT NULL DEFAULT '{}'::jsonb"))
    print("✅ metricas")
    
    # Adicionar tags
    db.execute(text("ALTER TABLE cliente_segmentos ADD COLUMN IF NOT EXISTS tags JSONB"))
    print("✅ tags")
    
    # Adicionar observacoes
    db.execute(text("ALTER TABLE cliente_segmentos ADD COLUMN IF NOT EXISTS observacoes TEXT"))
    print("✅ observacoes")
    
    # Atualizar user_id com base no cliente_id
    db.execute(text("""
        UPDATE cliente_segmentos cs
        SET user_id = c.user_id
        FROM clientes c
        WHERE cs.cliente_id = c.id AND cs.user_id IS NULL
    """))
    print("✅ user_id atualizado")
    
    # Tornar user_id NOT NULL
    db.execute(text("ALTER TABLE cliente_segmentos ALTER COLUMN user_id SET NOT NULL"))
    print("✅ user_id NOT NULL")
    
    db.commit()
    print("\n✅ Todas as colunas foram adicionadas com sucesso!")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    db.rollback()
finally:
    db.close()
