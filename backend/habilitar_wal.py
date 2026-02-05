"""
Script para habilitar WAL mode no banco SQLite
Resolve problemas de database locked
"""
import sqlite3
import os

DB_PATH = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\petshop.db"

print("🔧 Habilitando WAL mode no SQLite...\n")

if not os.path.exists(DB_PATH):
    print(f"❌ Banco não encontrado: {DB_PATH}")
    exit(1)

try:
    # Conectar ao banco
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    # Verificar modo atual
    cursor.execute("PRAGMA journal_mode")
    modo_atual = cursor.fetchone()[0]
    print(f"📊 Modo atual: {modo_atual}")
    
    # Habilitar WAL mode
    cursor.execute("PRAGMA journal_mode=WAL")
    novo_modo = cursor.fetchone()[0]
    print(f"✅ Novo modo: {novo_modo}")
    
    # Configurar busy timeout
    cursor.execute("PRAGMA busy_timeout=30000")
    print("✅ Busy timeout: 30000ms")
    
    # Verificar configurações
    cursor.execute("PRAGMA journal_mode")
    confirmacao = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    if confirmacao == 'wal':
        print("✅ WAL MODE HABILITADO COM SUCESSO!")
        print("   - Permite leituras durante escritas")
        print("   - Reduz locks drasticamente")
        print("   - Melhor performance")
    else:
        print(f"⚠️ Modo ficou como: {confirmacao}")
    print(f"{'='*50}\n")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
