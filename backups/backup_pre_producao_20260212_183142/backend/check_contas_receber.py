"""Check if ContaReceber columns were added"""
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:postgres@localhost:5433/petshop_dev')

expected_columns = [
    'status_conciliacao',
    'taxa_mdr_estimada',
    'taxa_antecipacao_estimada',
    'taxa_mdr_real',
    'taxa_antecipacao_real',
    'valor_liquido_estimado',
    'valor_liquido_real',
    'data_vencimento_estimada',
    'data_vencimento_real',
    'diferenca_taxa',
    'diferenca_valor',
    'conciliacao_lote_id',
    'versao_conciliacao',
    'data_liquidacao'
]

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'contas_receber'
        AND column_name IN :columns
        ORDER BY column_name
    """), {"columns": tuple(expected_columns)})
    
    found_columns = {row[0]: row[1] for row in result}
    
    print("Verificando colunas adicionadas em contas_receber:\n")
    for col in expected_columns:
        if col in found_columns:
            print(f"✓ {col} ({found_columns[col]})")
        else:
            print(f"✗ {col} - NÃO ENCONTRADA")
    
    print(f"\n{len(found_columns)}/{len(expected_columns)} colunas criadas")
