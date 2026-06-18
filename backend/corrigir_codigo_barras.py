#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para aumentar limite da coluna codigo_barras de VARCHAR(13) para VARCHAR(20)
"""

import os
import sys

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text

# Conexão com o banco LOCAL (porta 5433 do Docker)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"


def main():
    """Aumenta limite da coluna codigo_barras"""
    print("🔧 Conectando ao banco LOCAL (petshop_dev)...")

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("📊 Alterando coluna codigo_barras de VARCHAR(13) para VARCHAR(20)...")
        conn.execute(
            text("ALTER TABLE produtos ALTER COLUMN codigo_barras TYPE VARCHAR(20);")
        )
        conn.commit()
        print("✅ Coluna codigo_barras aumentada com sucesso!")
        print("   → Agora aceita códigos de barras com até 20 caracteres")


if __name__ == "__main__":
    main()
