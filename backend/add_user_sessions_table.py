"""
Adiciona tabela user_sessions para gerenciamento de sessões
"""
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, 
    Boolean, DateTime, Text, ForeignKey, inspect
)
from sqlalchemy.sql import func
import os

def get_database_url():
    """Lê a URL do banco de dados do .env ou usa o padrão"""
    # Tentar ler o .env
    db_url = None
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    
    # Se não encontrar, usa o padrão
    if not db_url:
        db_url = "sqlite:///./sistema_pet.db"
    
    return db_url

def add_user_sessions_table():
    """Cria a tabela user_sessions se não existir"""
    database_url = get_database_url()
    print(f"📦 Conectando ao banco: {database_url}")
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    # Verificar se a tabela já existe
    if 'user_sessions' in inspector.get_table_names():
        print("✅ Tabela user_sessions já existe")
        return
    
    # Criar a tabela
    print("📝 Criando tabela user_sessions...")
    
    metadata = MetaData()
    
    user_sessions = Table(
        'user_sessions',
        metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('user_id', Integer, nullable=False, index=True),
        Column('token_jti', String(36), unique=True, index=True, nullable=False),
        Column('ip_address', String(50), nullable=True),
        Column('user_agent', Text, nullable=True),
        Column('device_info', Text, nullable=True),
        Column('created_at', DateTime(timezone=True), server_default=func.now()),
        Column('last_activity_at', DateTime(timezone=True), server_default=func.now()),
        Column('expires_at', DateTime(timezone=True), nullable=False),
        Column('revoked', Boolean, default=False),
        Column('revoked_at', DateTime(timezone=True), nullable=True),
        Column('revoke_reason', String(255), nullable=True),
    )
    
    metadata.create_all(engine)
    print("✅ Tabela user_sessions criada com sucesso!")

if __name__ == "__main__":
    add_user_sessions_table()
