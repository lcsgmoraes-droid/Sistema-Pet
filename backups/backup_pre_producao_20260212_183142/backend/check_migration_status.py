"""Check current migration status"""
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:postgres@localhost:5433/petshop_dev')

with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.scalar()
    print(f"Current migration version: {version}")
    
    # Check if our tables exist
    tables_to_check = [
        'empresa_parametros',
        'adquirentes_templates',
        'arquivos_evidencia',
        'conciliacao_importacoes',
        'conciliacao_lotes',
        'conciliacao_validacoes', 
        'conciliacao_logs'
    ]
    
    print("\nChecking if tables exist:")
    for table in tables_to_check:
        result = conn.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table}'
            )
        """))
        exists = result.scalar()
        status = "✓" if exists else "✗"
        print(f"{status} {table}")
