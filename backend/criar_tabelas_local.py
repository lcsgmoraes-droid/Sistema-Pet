#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para criar todas as tabelas no banco local usando SQLAlchemy (sem Alembic)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Importar PRIMEIRO o base.py para garantir que todos os models sejam carregados
import app.db.base  # noqa - força carregamento de todos os models

from app.db.base_class import Base
from sqlalchemy import create_engine

# Conexão com o banco LOCAL (porta 5433 do Docker)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"


def main():
    """Cria todas as tabelas no banco"""
    print("🔧 Criando todas as tabelas no banco local...")
    print(f"📦 Models carregados: {len(Base.metadata.tables)}")

    engine = create_engine(DATABASE_URL)

    # Criar todas as tabelas definidas nos models
    Base.metadata.create_all(bind=engine)

    print(f"✅ {len(Base.metadata.tables)} tabelas criadas:")
    for table_name in sorted(Base.metadata.tables.keys()):
        print(f"   - {table_name}")


if __name__ == "__main__":
    main()
