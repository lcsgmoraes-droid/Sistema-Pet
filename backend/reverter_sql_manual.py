#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reverter a alteração SQL manual e voltar para VARCHAR(13)
para então aplicar corretamente via Alembic
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text

# Conexão com o banco LOCAL (porta 5433 do Docker)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"

def main():
    """Reverte alteração manual para aplicar via Alembic"""
    print("🔄 Revertendo alteração SQL manual...")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("📊 Voltando coluna codigo_barras para VARCHAR(13)...")
        conn.execute(text("ALTER TABLE produtos ALTER COLUMN codigo_barras TYPE VARCHAR(13);"))
        conn.commit()
        print("✅ Revertido! Agora vamos aplicar via Alembic (forma correta)")

if __name__ == "__main__":
    main()
