"""Script para adicionar coluna dre_subcategoria_id"""
from app.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE categorias_financeiras ADD COLUMN IF NOT EXISTS dre_subcategoria_id INTEGER'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_categorias_financeiras_dre_subcategoria_id ON categorias_financeiras (dre_subcategoria_id)'))
        conn.commit()
        print('✅ Coluna dre_subcategoria_id adicionada com sucesso!')
    except Exception as e:
        print(f'⚠️  Erro ou coluna já existe: {e}')
