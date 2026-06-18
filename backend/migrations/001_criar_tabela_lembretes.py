"""
Migração para adicionar tabela de Lembretes (Fase 1 - Sistema de Recorrência)
Autor: Sistema
Data: 2026-01-13

NOTA: Esta migração é aplicada automaticamente quando o backend inicia.
O SQLAlchemy detecta novos modelos e cria as tabelas automaticamente.
"""

import sys
from pathlib import Path

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect
from app.db import engine, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def criar_tabela_lembretes():
    """Criar tabela de lembretes se não existir"""
    try:
        # Importar TODOS os modelos para garantir que estão registrados
        from app.produtos_models import Lembrete

        inspector = inspect(engine)
        tabelas_existentes = inspector.get_table_names()

        logger.info(f"📋 Tabelas existentes: {len(tabelas_existentes)}")

        if "lembretes" not in tabelas_existentes:
            logger.info("📝 Criando tabela 'lembretes'...")
            Base.metadata.create_all(engine, tables=[Lembrete.__table__])
            logger.info("✅ Tabela 'lembretes' criada com sucesso!")
        else:
            logger.info("ℹ️  Tabela 'lembretes' já existe")

        # Verificar novamente
        inspector = inspect(engine)
        if "lembretes" in inspector.get_table_names():
            colunas = [col["name"] for col in inspector.get_columns("lembretes")]
            logger.info(f"✅ Colunas da tabela lembretes: {', '.join(colunas)}")

        return True

    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    sucesso = criar_tabela_lembretes()
    sys.exit(0 if sucesso else 1)
