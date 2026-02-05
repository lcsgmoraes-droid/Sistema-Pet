"""
OPCIONAL: Remover tabela comissoes_audit_log (DEPRECIADA)
Data: 2026-01-23

Esta tabela está vazia e não é usada em nenhum lugar do código.
A auditoria agora é feita via JSON em campos observacoes.

AVISO: Execute este script apenas se tiver certeza!
"""

import sqlite3
import sys
from pathlib import Path


def main():
    print("="*80)
    print("REMOÇÃO DE TABELA DEPRECIADA: comissoes_audit_log")
    print("="*80)
    
    # Conectar ao banco
    db_path = Path(__file__).parent / "petshop.db"
    
    if not db_path.exists():
        print(f"\n❌ ERRO: Banco de dados não encontrado em {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Verificar se tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='comissoes_audit_log'
        """)
        
        if not cursor.fetchone():
            print("\n✓ Tabela comissoes_audit_log não existe (já foi removida)")
            return True
        
        # Verificar se há registros
        cursor.execute("SELECT COUNT(*) FROM comissoes_audit_log")
        count = cursor.fetchone()[0]
        
        print(f"\nTabela encontrada: comissoes_audit_log")
        print(f"Registros no banco: {count}")
        
        if count > 0:
            print("\n⚠️  AVISO: Tabela contém registros!")
            print("Deseja continuar mesmo assim? (digite 'SIM' para confirmar)")
            resposta = input("> ").strip().upper()
            
            if resposta != "SIM":
                print("\n❌ Operação cancelada pelo usuário")
                return False
        
        # Confirmar remoção
        print("\n" + "="*80)
        print("⚠️  ATENÇÃO: Esta operação é IRREVERSÍVEL!")
        print("="*80)
        print("\nA tabela comissoes_audit_log será REMOVIDA permanentemente.")
        print("Digite 'REMOVER' para confirmar:")
        
        confirmacao = input("> ").strip().upper()
        
        if confirmacao != "REMOVER":
            print("\n❌ Operação cancelada - confirmação não recebida")
            return False
        
        # Fazer backup da estrutura antes de remover
        print("\n1. Fazendo backup da estrutura...")
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='comissoes_audit_log'")
        estrutura = cursor.fetchone()
        
        if estrutura:
            backup_file = Path(__file__).parent / "backup_comissoes_audit_log_schema.sql"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("-- Backup da estrutura de comissoes_audit_log\n")
                f.write("-- Data: 2026-01-23\n\n")
                f.write(estrutura[0] + ";\n")
            print(f"   ✓ Backup salvo em: {backup_file}")
        
        # Remover tabela
        print("\n2. Removendo tabela...")
        cursor.execute("DROP TABLE comissoes_audit_log")
        conn.commit()
        
        print("   ✓ Tabela comissoes_audit_log removida com sucesso!")
        
        # Verificar remoção
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='comissoes_audit_log'
        """)
        
        if not cursor.fetchone():
            print("\n" + "="*80)
            print("✅ REMOÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*80)
            print("\n✓ Tabela comissoes_audit_log foi removida")
            print("✓ Backup da estrutura foi salvo")
            print("\nAuditoria agora é feita via JSON em campos observacoes")
            return True
        else:
            print("\n❌ ERRO: Tabela ainda existe após remoção")
            return False
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("""
⚠️  AVISO IMPORTANTE ⚠️

Este script irá REMOVER a tabela 'comissoes_audit_log' do banco de dados.

A tabela está DEPRECIADA porque:
- Não é usada em nenhum lugar do código
- Está vazia (0 registros)
- Auditoria agora é feita via JSON em observacoes

Deseja continuar? (digite 'SIM' para continuar)
    """)
    
    resposta = input("> ").strip().upper()
    
    if resposta == "SIM":
        sucesso = main()
        sys.exit(0 if sucesso else 1)
    else:
        print("\n❌ Operação cancelada pelo usuário")
        sys.exit(1)
