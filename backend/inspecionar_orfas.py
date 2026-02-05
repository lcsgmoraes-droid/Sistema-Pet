"""
Script para inspecionar schema real das tabelas órfãs ativas
"""
from app.db import engine
from sqlalchemy import text

TABELAS_ORFAS = [
    'cargos',
    'comissoes_itens',
    'comissoes_configuracao',
    'comissoes_vendas',
    'formas_pagamento_comissoes',
    'cliente_segmentos'
]

def verificar_existencia(conn, tabela):
    """Verifica se tabela existe"""
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = :tabela
    """)
    result = conn.execute(query, {"tabela": tabela}).fetchone()
    return result is not None

def obter_colunas(conn, tabela):
    """Obtém colunas e tipos"""
    query = text("""
        SELECT
          column_name,
          data_type,
          is_nullable,
          column_default,
          character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :tabela
        ORDER BY ordinal_position
    """)
    return conn.execute(query, {"tabela": tabela}).fetchall()

def obter_primary_keys(conn, tabela):
    """Obtém primary keys"""
    query = text("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = :tabela
          AND tc.constraint_type = 'PRIMARY KEY'
    """)
    return conn.execute(query, {"tabela": tabela}).fetchall()

def obter_foreign_keys(conn, tabela):
    """Obtém foreign keys"""
    query = text("""
        SELECT
          kcu.column_name,
          ccu.table_name AS foreign_table,
          ccu.column_name AS foreign_column,
          tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = :tabela
    """)
    return conn.execute(query, {"tabela": tabela}).fetchall()

def obter_indices(conn, tabela):
    """Obtém índices"""
    query = text("""
        SELECT
          indexname,
          indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = :tabela
    """)
    return conn.execute(query, {"tabela": tabela}).fetchall()

def inspecionar_tabela(conn, tabela):
    """Inspeciona uma tabela completa"""
    print(f"\n{'='*60}")
    print(f"INSPECIONANDO: {tabela}")
    print(f"{'='*60}")
    
    # Verificar existência
    existe = verificar_existencia(conn, tabela)
    print(f"Existe no banco: {'SIM' if existe else 'NAO'}")
    
    if not existe:
        print(f"[SKIP] Tabela {tabela} nao encontrada")
        return None
    
    # Colunas
    print(f"\n--- COLUNAS ---")
    colunas = obter_colunas(conn, tabela)
    for col in colunas:
        tipo = col.data_type
        if col.character_maximum_length:
            tipo = f"{tipo}({col.character_maximum_length})"
        print(f"  {col.column_name:30} {tipo:20} nullable={col.is_nullable:3} default={col.column_default}")
    
    # Primary Keys
    print(f"\n--- PRIMARY KEYS ---")
    pks = obter_primary_keys(conn, tabela)
    if pks:
        for pk in pks:
            print(f"  - {pk.column_name}")
    else:
        print("  (nenhuma)")
    
    # Foreign Keys
    print(f"\n--- FOREIGN KEYS ---")
    fks = obter_foreign_keys(conn, tabela)
    if fks:
        for fk in fks:
            print(f"  {fk.column_name} -> {fk.foreign_table}.{fk.foreign_column} ({fk.constraint_name})")
    else:
        print("  (nenhuma)")
    
    # Índices
    print(f"\n--- INDICES ---")
    indices = obter_indices(conn, tabela)
    if indices:
        for idx in indices:
            print(f"  {idx.indexname}")
            print(f"    {idx.indexdef}")
    else:
        print("  (nenhum)")
    
    return {
        'existe': existe,
        'colunas': colunas,
        'primary_keys': pks,
        'foreign_keys': fks,
        'indices': indices
    }

def main():
    print("="*60)
    print("FASE 5.4 - INSPECAO DE TABELAS ORFAS")
    print("="*60)
    
    resultados = {}
    
    with engine.connect() as conn:
        for tabela in TABELAS_ORFAS:
            resultado = inspecionar_tabela(conn, tabela)
            resultados[tabela] = resultado
    
    print(f"\n{'='*60}")
    print("INSPECAO CONCLUIDA")
    print(f"{'='*60}")
    print(f"\nTabelas encontradas: {sum(1 for r in resultados.values() if r and r['existe'])}/{len(TABELAS_ORFAS)}")
    
    return resultados

if __name__ == "__main__":
    main()
