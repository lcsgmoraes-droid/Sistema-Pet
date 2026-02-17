from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    count = conn.execute(text('SELECT COUNT(*) FROM produto_config_fiscal')).scalar()
    print(f'Total de registros em produto_config_fiscal: {count}')
    
    sample = conn.execute(text('''
        SELECT id, produto_id, ncm, cfop_venda, origem_mercadoria, herdado_da_empresa 
        FROM produto_config_fiscal 
        LIMIT 5
    ''')).fetchall()
    
    print('\n=== Amostra dos dados migrados ===')
    for r in sample:
        print(f'ID: {r[0]}, Produto ID: {r[1]}, NCM: {r[2]}, CFOP: {r[3]}, Origem: {r[4]}, Herdado: {r[5]}')
