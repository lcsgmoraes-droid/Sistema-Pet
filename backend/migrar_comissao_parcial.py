"""
MIGRAÇÃO: Adicionar campos para comissão proporcional a pagamentos parciais

CAMPOS A ADICIONAR em comissoes_itens:
- valor_base_original: Valor total da venda
- valor_base_comissionada: Valor sobre o qual a comissão foi calculada
- percentual_aplicado: Percentual de comissão aplicado
- valor_pago_referencia: Valor do pagamento que gerou esta comissão
- parcela_numero: Número da parcela/pagamento

Sprint 3 - Passo 2
Data: 22/01/2026
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "pet_shop.db"

def campo_existe(cursor, tabela: str, campo: str) -> bool:
    """Verifica se um campo existe em uma tabela"""
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = [row[1] for row in cursor.fetchall()]
    return campo in colunas

def adicionar_campos_comissao_parcial():
    """Adiciona campos necessários para comissão proporcional"""
    
    print("=" * 80)
    print("🔧 MIGRAÇÃO: Comissão Proporcional a Pagamentos Parciais")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"❌ ERRO: Banco de dados não encontrado em {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comissoes_itens'")
        if not cursor.fetchone():
            print("❌ ERRO: Tabela comissoes_itens não existe!")
            sys.exit(1)
        
        print("\n📊 Verificando estrutura atual da tabela comissoes_itens...")
        cursor.execute("PRAGMA table_info(comissoes_itens)")
        campos_atuais = [row[1] for row in cursor.fetchall()]
        print(f"✅ Tabela possui {len(campos_atuais)} campos atualmente")
        
        # Campos a adicionar
        novos_campos = [
            ("valor_base_original", "DECIMAL(10,2)", "Valor total da venda"),
            ("valor_base_comissionada", "DECIMAL(10,2)", "Valor sobre o qual a comissão foi calculada"),
            ("percentual_aplicado", "DECIMAL(5,2)", "Percentual de comissão aplicado"),
            ("valor_pago_referencia", "DECIMAL(10,2)", "Valor do pagamento que gerou esta comissão"),
            ("parcela_numero", "INTEGER DEFAULT 1", "Número da parcela/pagamento")
        ]
        
        campos_adicionados = 0
        
        print("\n🔍 Verificando campos necessários...")
        
        for campo_nome, campo_tipo, descricao in novos_campos:
            if campo_existe(cursor, "comissoes_itens", campo_nome):
                print(f"⏭️  Campo '{campo_nome}' já existe - pulando")
            else:
                print(f"➕ Adicionando campo '{campo_nome}' ({campo_tipo})")
                print(f"   Descrição: {descricao}")
                
                sql = f"ALTER TABLE comissoes_itens ADD COLUMN {campo_nome} {campo_tipo}"
                cursor.execute(sql)
                campos_adicionados += 1
                print(f"   ✅ Campo '{campo_nome}' adicionado com sucesso")
        
        # Commit das alterações
        conn.commit()
        
        # Verificar estrutura final
        cursor.execute("PRAGMA table_info(comissoes_itens)")
        campos_finais = [row[1] for row in cursor.fetchall()]
        
        print("\n" + "=" * 80)
        print("📋 RESULTADO DA MIGRAÇÃO")
        print("=" * 80)
        print(f"Total de campos antes: {len(campos_atuais)}")
        print(f"Campos adicionados: {campos_adicionados}")
        print(f"Total de campos agora: {len(campos_finais)}")
        
        if campos_adicionados > 0:
            print("\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("\n📝 Campos adicionados:")
            for campo_nome, _, descricao in novos_campos:
                if campo_nome not in campos_atuais:
                    print(f"  • {campo_nome}: {descricao}")
        else:
            print("\n✅ ESTRUTURA JÁ ESTAVA ATUALIZADA!")
            print("Nenhum campo precisou ser adicionado.")
        
        print("\n🎯 Próximos passos:")
        print("  1. Modificar gerar_comissoes_venda() para usar novos campos")
        print("  2. Implementar cálculo proporcional de comissões")
        print("  3. Adicionar verificação de idempotência por parcela")
        print("  4. Executar testes de comissão parcial")
        
    except sqlite3.Error as e:
        print(f"\n❌ ERRO no banco de dados: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO inesperado: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    adicionar_campos_comissao_parcial()
