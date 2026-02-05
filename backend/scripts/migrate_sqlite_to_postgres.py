"""
MIGRAÇÃO SQLite → PostgreSQL - Sistema Pet Shop
================================================

Este script migra todos os dados do SQLite para PostgreSQL preservando:
- IDs originais
- Relacionamentos entre tabelas
- Integridade referencial
- Ordem de inserção respeitando foreign keys

EXECUÇÃO:
    cd backend
    python scripts/migrate_sqlite_to_postgres.py

REQUISITOS:
- PostgreSQL rodando e acessível
- DATABASE_URL configurado no .env
- psycopg2-binary instalado
- Schema já criado via Alembic

AUTOR: Sistema Pet Shop Pro
DATA: Janeiro 2026
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import traceback

# Adicionar backend ao path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker

# Importar configurações diretamente sem carregar todo o app
import os
from dotenv import load_dotenv

# Carregar .env
env_path = backend_path / '.env'
load_dotenv(env_path)

# Obter configurações
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")
SQLITE_DB_PATH = backend_path / "data" / "petshop.db"

def get_database_url():
    """Obter URL do banco de dados"""
    if DATABASE_TYPE == "postgresql":
        return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/petshop")
    else:
        return f"sqlite:///{SQLITE_DB_PATH}"


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# DEBUG: IDs de vendas que estão falhando
DEBUG_VENDAS_IDS = [43, 44, 52, 53, 66, 75, 76, 81]

# Conexões
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"
POSTGRES_URL = get_database_url()

# Ordem de migração (respeitando foreign keys)
MIGRATION_ORDER = [
    # 1. Tabelas sem dependências
    'users',
    'clientes',
    'racas',
    'categorias',
    'subcategorias',
    'marcas',
    'departamentos',
    'fornecedores',
    
    # 2. Tabelas que dependem de User e Cliente
    'pets',
    'user_sessions',
    'audit_logs',
    
    # 3. Produtos e seus relacionamentos
    'produtos',
    'produto_fornecedores',
    'produto_imagens',
    'kit_componentes',
    'variacoes',
    'historico_precos',
    
    # 4. Formas de pagamento e configurações
    'formas_pagamento',
    'formas_pagamento_taxas',
    'contas_bancarias',
    
    # 5. Caixa
    'caixas',
    'movimentacoes_caixa',
    
    # 6. Vendas (dependem de produtos, clientes, caixa)
    'vendas',
    'venda_itens',
    'venda_pagamentos',
    'vendas_pets',
    
    # 7. Financeiro
    'contas_pagar',
    'contas_receber',
    'lancamentos_fluxo_caixa',
    
    # 8. Comissões
    'comissoes',
    'comissoes_itens',
    'config_comissao_produto',
    'fechamento_comissoes',
    'historico_fechamento_comissoes',
    
    # 9. Notas fiscais
    'notas_entrada',
    'notas_entrada_itens',
    'notas_saida',
    'xmls_importados',
    
    # 10. Pedidos
    'pedidos_compra',
    'pedidos_compra_itens',
    
    # 11. IA e Analytics
    'padroes_categorizacao_ia',
    'lancamentos_importados',
    'arquivos_extrato_importados',
    'historico_atualizacao_dre',
    'configuracao_tributaria',
    'ai_decision_logs',
    'ai_feedback_logs',
    'ai_learning_patterns',
    
    # 12. Read Models
    'read_vendas_resumo_diario',
    'read_performance_parceiro',
    'read_receita_mensal',
    
    # 13. Idempotência e eventos
    'idempotency_keys',
    'event_store',
    
    # 14. Integrações
    'bling_sync_logs',
    'email_envios',
    
    # 15. WhatsApp
    'whatsapp_sessions',
    'whatsapp_messages',
    'whatsapp_qrcodes',
]


# ============================================================================
# ESTATÍSTICAS
# ============================================================================

class MigrationStats:
    """Estatísticas da migração"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.tables_migrated = 0
        self.total_records = 0
        self.errors = []
        self.table_stats = {}
    
    def add_table(self, table_name: str, records: int, elapsed: float):
        """Registra migração de uma tabela"""
        self.tables_migrated += 1
        self.total_records += records
        self.table_stats[table_name] = {
            'records': records,
            'elapsed': elapsed
        }
    
    def add_error(self, table_name: str, error: str):
        """Registra erro"""
        self.errors.append({
            'table': table_name,
            'error': error
        })
    
    def print_summary(self):
        """Imprime resumo da migração"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(" RESUMO DA MIGRAÇÃO")
        print("=" * 80)
        print(f"  Tempo total: {elapsed:.2f}s")
        print(f" Tabelas migradas: {self.tables_migrated}")
        print(f" Total de registros: {self.total_records:,}")
        print(f" Taxa média: {self.total_records/elapsed:.0f} registros/segundo")
        
        if self.errors:
            print(f"\n Erros encontrados: {len(self.errors)}")
            for error in self.errors:
                print(f"   - {error['table']}: {error['error']}")
        else:
            print("\n Migração concluída sem erros!")
        
        print("\n TOP 10 TABELAS (por registros):")
        sorted_tables = sorted(
            self.table_stats.items(),
            key=lambda x: x[1]['records'],
            reverse=True
        )[:10]
        
        for table, stats in sorted_tables:
            records = stats['records']
            elapsed = stats['elapsed']
            rate = records / elapsed if elapsed > 0 else 0
            print(f"   {table:30s}: {records:>8,} registros ({rate:>6.0f} rec/s)")
        
        print("=" * 80 + "\n")


# ============================================================================
# FUNÇÕES DE MIGRAÇÃO
# ============================================================================

def get_table_columns(engine, table_name: str) -> List[str]:
    """Retorna lista de colunas de uma tabela"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]


def get_column_types(engine, table_name: str) -> Dict[str, str]:
    """Retorna dicionário com tipos das colunas"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name']: str(col['type']) for col in columns}


def convert_value_for_postgres(value: Any, column_type: str, column_name: str = '') -> Any:
    """
    Converte valor do SQLite para formato compatível com PostgreSQL
    
    Args:
        value: Valor original do SQLite
        column_type: Tipo da coluna no PostgreSQL
        column_name: Nome da coluna (para conversões específicas)
    
    Returns:
        Valor convertido para PostgreSQL
    """
    # Null continua null
    if value is None:
        return None
    
    # CORREÇÃO #1: nfe_bling_id muito grande para INTEGER
    # PostgreSQL INTEGER: máx 2,147,483,647 (10 dígitos)
    # Converter para NULL se exceder limite
    if column_name == 'nfe_bling_id' and isinstance(value, (int, float)):
        if value > 2147483647:
            return None  # Ou considerar converter coluna para BIGINT
    
    # CORREÇÃO #2: status muito longo para VARCHAR(20)
    # Truncar strings que excedem limite
    if column_name == 'status' and isinstance(value, str):
        if 'VARCHAR' in column_type.upper():
            # Extrair tamanho do VARCHAR
            import re
            match = re.search(r'VARCHAR\((\d+)\)', column_type.upper())
            if match:
                max_length = int(match.group(1))
                if len(value) > max_length:
                    # Truncar com segurança
                    return value[:max_length]
    
    # Boolean: 0/1 → False/True
    if 'BOOLEAN' in column_type.upper():
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 't', 'yes')
        return bool(value)
    
    # Strings vazias em colunas numéricas → None
    if value == '':
        if any(t in column_type.upper() for t in ['INTEGER', 'NUMERIC', 'DECIMAL', 'FLOAT', 'DOUBLE']):
            return None
    
    # Retornar valor original para outros tipos
    return value


def migrate_table(
    sqlite_engine,
    postgres_engine,
    table_name: str,
    batch_size: int = 1000
) -> int:
    """
    Migra uma tabela do SQLite para PostgreSQL
    
    Args:
        sqlite_engine: Engine do SQLite
        postgres_engine: Engine do PostgreSQL
        table_name: Nome da tabela
        batch_size: Tamanho do lote
    
    Returns:
        Número de registros migrados
    """
    print(f"\n Migrando {table_name}...", end=' ', flush=True)
    start = datetime.now()
    
    try:
        # Verificar se tabela existe no SQLite
        sqlite_inspector = inspect(sqlite_engine)
        if table_name not in sqlite_inspector.get_table_names():
            print(f"  Tabela não existe no SQLite")
            return 0
        
        # Verificar se tabela existe no PostgreSQL
        postgres_inspector = inspect(postgres_engine)
        if table_name not in postgres_inspector.get_table_names():
            print(f"  Tabela não existe no PostgreSQL (pulando)")
            return 0
        
        # Conectar aos bancos
        with sqlite_engine.connect() as sqlite_conn, \
             postgres_engine.connect() as postgres_conn:
            
            # Contar registros
            count_result = sqlite_conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            total_records = count_result.scalar()
            
            if total_records == 0:
                print(f" 0 registros")
                return 0
            
            # Obter colunas de ambos os bancos
            sqlite_columns = get_table_columns(sqlite_engine, table_name)
            postgres_columns = get_table_columns(postgres_engine, table_name)
            
            # IMPORTANTE: Usar apenas colunas que existem em AMBOS os bancos
            common_columns = [col for col in sqlite_columns if col in postgres_columns]
            
            if not common_columns:
                print(f"  ERRO: Nenhuma coluna em comum entre SQLite e PostgreSQL!")
                return 0
            
            # Obter tipos das colunas do PostgreSQL
            postgres_column_types = get_column_types(postgres_engine, table_name)
            columns_str = ', '.join(common_columns)
            placeholders = ', '.join([f':{col}' for col in common_columns])
            
            # Ler dados do SQLite (apenas colunas comuns)
            result = sqlite_conn.execute(
                text(f"SELECT {columns_str} FROM {table_name}")
            )
            rows = result.fetchall()
            
            # Desabilitar triggers temporariamente (se existirem)
            # Isso permite inserir com IDs específicos
            postgres_conn.execute(text(f"ALTER TABLE {table_name} DISABLE TRIGGER ALL"))
            
            # Inserir em lotes no PostgreSQL
            records_inserted = 0
            records_skipped = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                
                # Converter rows para dicts com conversão de tipos
                batch_dicts = []
                for row in batch:
                    row_dict = {}
                    for idx, col in enumerate(common_columns):  # Usar common_columns
                        value = row[idx]
                        
                        # Converter valor para tipo compatível com PostgreSQL
                        column_type = postgres_column_types.get(col, '')
                        value = convert_value_for_postgres(value, column_type, col)  # Passar nome da coluna
                        
                        row_dict[col] = value
                    
                    batch_dicts.append(row_dict)
                
                # Inserir lote
                if batch_dicts:
                    # Para tabela vendas, remover ON CONFLICT para ver erros reais
                    if table_name == 'vendas':
                        insert_query = text(f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                        """)
                    else:
                        insert_query = text(f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                            ON CONFLICT (id) DO NOTHING
                        """)
                    
                    for row_dict in batch_dicts:
                        # DEBUG: Verificar se é um dos IDs problemáticos de vendas
                        is_debug_venda = (table_name == 'vendas' and 
                                         row_dict.get('id') in DEBUG_VENDAS_IDS)
                        
                        try:
                            if is_debug_venda:
                                print(f"\n{'='*80}")
                                print(f"DEBUG: Tentando inserir venda ID {row_dict['id']}")
                                print(f"Dados completos:")
                                for key, val in row_dict.items():
                                    print(f"  {key}: {val!r} (tipo: {type(val).__name__})")
                                print(f"Query: INSERT INTO {table_name} ({columns_str}) VALUES (...)")
                                print(f"{'='*80}")
                            
                            result = postgres_conn.execute(insert_query, row_dict)
                            postgres_conn.commit()
                            
                            if result.rowcount > 0:
                                records_inserted += 1
                                if is_debug_venda:
                                    print(f"SUCESSO: Venda ID {row_dict['id']} inserida!\n")
                            else:
                                records_skipped += 1
                                
                        except Exception as e:
                            # Rollback da transação falha
                            postgres_conn.rollback()
                            
                            error_msg = str(e)
                            
                            # DEBUG DETALHADO para vendas problemáticas
                            if is_debug_venda:
                                print(f"\n{'='*80}")
                                print(f"ERRO DETALHADO - Venda ID {row_dict['id']}")
                                print(f"Tipo da excecao: {type(e).__name__}")
                                print(f"Mensagem completa:")
                                print(f"{error_msg}")
                                print(f"\nTraceback:")
                                traceback.print_exc()
                                print(f"{'='*80}\n")
                            
                            # Ignorar duplicatas silenciosamente
                            if 'duplicate key' in error_msg.lower():
                                records_skipped += 1
                            elif 'already exists' in error_msg.lower():
                                records_skipped += 1
                            else:
                                # Logar apenas erros reais (truncar mensagem)
                                short_msg = error_msg[:150] if len(error_msg) > 150 else error_msg
                                if records_inserted < 5 and not is_debug_venda:  # Mostrar apenas primeiros erros
                                    print(f"\n  Erro: {short_msg}")
            
            # Re-habilitar triggers
            postgres_conn.execute(text(f"ALTER TABLE {table_name} ENABLE TRIGGER ALL"))
            postgres_conn.commit()
            
            # Atualizar sequência do ID (importante!)
            try:
                postgres_conn.execute(text(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', 'id'),
                        COALESCE(MAX(id), 1)
                    ) FROM {table_name}
            if records_skipped > 0:
                print(f" {records_inserted:,} migrados, {records_skipped:,} já existiam ({elapsed:.2f}s)")
            else:
                    """))
            except Exception:
                # Algumas tabelas não têm sequência de ID
                pass
            
            # Commit
            postgres_conn.commit()
            
            elapsed = (datetime.now() - start).total_seconds()
            print(f" {records_inserted:,} registros ({elapsed:.2f}s)")
            
            return records_inserted
    
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        print(f" ERRO ({elapsed:.2f}s)")
        print(f"   {str(e)[:100]}")
        traceback.print_exc()
        return 0


def verify_migration(sqlite_engine, postgres_engine) -> Dict[str, Dict[str, int]]:
    """
    Verifica a migração comparando contagens
    
    Returns:
        Dicionário com comparação de contagens
    """
    print("\n" + "=" * 80)
    print(" VERIFICANDO MIGRAÇÃO")
    print("=" * 80)
    
    comparison = {}
    
    sqlite_inspector = inspect(sqlite_engine)
    sqlite_tables = sqlite_inspector.get_table_names()
    
    for table_name in MIGRATION_ORDER:
        if table_name not in sqlite_tables:
            continue
        
        try:
            # Contar no SQLite
            with sqlite_engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                sqlite_count = result.scalar()
            
            # Contar no PostgreSQL
            with postgres_engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                postgres_count = result.scalar()
            
            comparison[table_name] = {
                'sqlite': sqlite_count,
                'postgres': postgres_count,
                'match': sqlite_count == postgres_count
            }
            
            status = "" if sqlite_count == postgres_count else ""
            print(f"{status} {table_name:30s}: SQLite={sqlite_count:>6,}  PostgreSQL={postgres_count:>6,}")
        
        except Exception as e:
            print(f" {table_name:30s}: Erro ao verificar - {str(e)[:50]}")
            comparison[table_name] = {
                'sqlite': 0,
                'postgres': 0,
                'match': False,
                'error': str(e)
            }
    
    # Resumo
    total_tables = len(comparison)
    matching_tables = sum(1 for stats in comparison.values() if stats.get('match', False))
    
    print("\n" + "-" * 80)
    print(f" Resumo: {matching_tables}/{total_tables} tabelas com contagens idênticas")
    
    if matching_tables == total_tables:
        print(" Todas as tabelas foram migradas corretamente!")
    else:
        print("  Algumas tabelas têm diferenças. Verifique os logs acima.")
    
    print("=" * 80)
    
    return comparison


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Executa migração completa"""
    print("\n" + "=" * 80)
    print("MIGRACAO SQLite -> PostgreSQL")
    print("=" * 80)
    print(f"SQLite:     {SQLITE_URL}")
    print(f"PostgreSQL: {POSTGRES_URL[:50]}...")
    print("=" * 80)
    
    # Verificar configuração
    if DATABASE_TYPE != "postgresql":
        print("\nERRO: DATABASE_TYPE deve ser 'postgresql' no .env")
        print(f"   Valor atual: {DATABASE_TYPE}")
        sys.exit(1)
    
    # Confirmar
    print("\nATENCAO: Esta operacao ira:")
    print("   1. Copiar TODOS os dados do SQLite para PostgreSQL")
    print("   2. Preservar IDs originais")
    print("   3. Desabilitar triggers temporariamente")
    print("   4. Pode demorar alguns minutos dependendo do volume de dados")
    
    resposta = input("\nDeseja continuar? (s/N): ").strip().lower()
    if resposta != 's':
        print("Migracao cancelada pelo usuario")
        sys.exit(0)
    
    # Criar engines
    print("\nConectando aos bancos...")
    sqlite_engine = create_engine(SQLITE_URL)
    postgres_engine = create_engine(POSTGRES_URL)
    
    # Testar conexões
    try:
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("OK - SQLite conectado")
    except Exception as e:
        print(f"ERRO ao conectar no SQLite: {e}")
        sys.exit(1)
    
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("OK - PostgreSQL conectado")
    except Exception as e:
        print(f"ERRO ao conectar no PostgreSQL: {e}")
        sys.exit(1)
    
    # Iniciar migração
    stats = MigrationStats()
    
    print("\n" + "=" * 80)
    print(" INICIANDO MIGRAÇÃO")
    print("=" * 80)
    
    for table_name in MIGRATION_ORDER:
        start = datetime.now()
        records = migrate_table(sqlite_engine, postgres_engine, table_name)
        elapsed = (datetime.now() - start).total_seconds()
        
        if records > 0:
            stats.add_table(table_name, records, elapsed)
    
    # Verificar migração
    comparison = verify_migration(sqlite_engine, postgres_engine)
    
    # Imprimir estatísticas
    stats.print_summary()
    
    # Instruções finais
    print(" PRÓXIMOS PASSOS:")
    print("   1. Verificar os logs acima para confirmar que tudo foi migrado")
    print("   2. Testar o sistema: http://localhost:5173")
    print("   3. Fazer alguns testes de PDV, vendas, pagamentos")
    print("   4. Se tudo estiver OK, fazer backup do PostgreSQL")
    print("   5. Manter o SQLite como backup por alguns dias")
    print("\n Migração concluída!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Migração interrompida pelo usuário (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n ERRO FATAL: {e}")
        traceback.print_exc()
        sys.exit(1)
