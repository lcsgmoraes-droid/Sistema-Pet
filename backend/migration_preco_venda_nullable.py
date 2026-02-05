"""
Migração: Tornar coluna preco_venda nullable para produtos PAI
Data: 2026-01-24
"""
import sqlite3
import os
from datetime import datetime

def migrar_preco_venda_nullable():
    """Altera a coluna preco_venda para aceitar NULL"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'petshop.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    print(f"📂 Banco de dados: {db_path}")
    print(f"🕐 Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Backup da tabela
        print("📋 Criando backup da tabela produtos...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos_backup_20260124 AS 
            SELECT * FROM produtos
        """)
        conn.commit()
        print("✅ Backup criado: produtos_backup_20260124")
        print()
        
        # SQLite não suporta ALTER COLUMN diretamente, precisamos recriar a tabela
        print("🔄 Recriando tabela com preco_venda nullable...")
        
        # 1. Obter estrutura da tabela atual
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = cursor.fetchall()
        
        # 2. Criar nova tabela temporária
        cursor.execute("""
            CREATE TABLE produtos_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                codigo VARCHAR(50) NOT NULL UNIQUE,
                nome VARCHAR(200) NOT NULL,
                descricao_curta TEXT,
                descricao_completa TEXT,
                tags TEXT,
                codigo_barras VARCHAR(13),
                codigos_barras_alternativos TEXT,
                categoria_id INTEGER,
                subcategoria VARCHAR(100),
                marca_id INTEGER,
                fornecedor_id INTEGER,
                departamento_id INTEGER,
                preco_custo FLOAT DEFAULT 0,
                preco_venda FLOAT DEFAULT 0,
                preco_promocional FLOAT,
                promocao_inicio DATETIME,
                promocao_fim DATETIME,
                promocao_ativa BOOLEAN DEFAULT 0,
                estoque_atual FLOAT DEFAULT 0,
                estoque_minimo FLOAT DEFAULT 0,
                estoque_maximo FLOAT DEFAULT 0,
                estoque_fisico FLOAT DEFAULT 0,
                estoque_ecommerce FLOAT DEFAULT 0,
                localizacao VARCHAR(50),
                crossdocking_dias INTEGER DEFAULT 0,
                controle_lote BOOLEAN DEFAULT 0,
                peso_bruto FLOAT,
                peso_liquido FLOAT,
                unidade VARCHAR(10) DEFAULT 'UN',
                tipo VARCHAR(20) DEFAULT 'produto',
                ncm VARCHAR(10),
                cest VARCHAR(10),
                origem VARCHAR(2),
                cfop VARCHAR(10),
                aliquota_icms FLOAT,
                aliquota_pis FLOAT,
                aliquota_cofins FLOAT,
                perecivel BOOLEAN DEFAULT 0,
                dias_validade INTEGER,
                imagem_url TEXT,
                ativo BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                tem_recorrencia BOOLEAN DEFAULT 0,
                tipo_recorrencia VARCHAR(50),
                intervalo_dias INTEGER,
                numero_doses INTEGER,
                especie_compativel VARCHAR(50),
                observacoes_recorrencia TEXT,
                classificacao_racao VARCHAR(50),
                peso_embalagem FLOAT,
                tabela_nutricional TEXT,
                categoria_racao VARCHAR(50),
                especies_indicadas VARCHAR(50),
                tabela_consumo TEXT,
                tipo_produto VARCHAR(20) DEFAULT 'SIMPLES',
                produto_pai_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (categoria_id) REFERENCES categorias (id),
                FOREIGN KEY (marca_id) REFERENCES marcas (id),
                FOREIGN KEY (fornecedor_id) REFERENCES clientes (id),
                FOREIGN KEY (departamento_id) REFERENCES departamentos (id),
                FOREIGN KEY (produto_pai_id) REFERENCES produtos (id)
            )
        """)
        
        # 3. Copiar dados (convertendo NULL para 0 onde necessário para compatibilidade)
        print("📊 Copiando dados da tabela antiga...")
        cursor.execute("""
            INSERT INTO produtos_new 
            SELECT * FROM produtos
        """)
        
        # 4. Dropar tabela antiga
        print("🗑️  Removendo tabela antiga...")
        cursor.execute("DROP TABLE produtos")
        
        # 5. Renomear nova tabela
        print("📝 Renomeando nova tabela...")
        cursor.execute("ALTER TABLE produtos_new RENAME TO produtos")
        
        # 6. Recriar índices
        print("🔍 Recriando índices...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_user ON produtos(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos(codigo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_tipo_produto ON produtos(tipo_produto)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_produto_pai ON produtos(produto_pai_id)")
        
        # Commit das alterações
        conn.commit()
        
        # Verificar migração
        print()
        print("🔍 Verificando migração...")
        cursor.execute("PRAGMA table_info(produtos)")
        colunas_novas = cursor.fetchall()
        
        preco_venda_info = [col for col in colunas_novas if col[1] == 'preco_venda']
        if preco_venda_info:
            col_info = preco_venda_info[0]
            nullable = "Sim" if col_info[3] == 0 else "Não"
            print(f"   Coluna: preco_venda")
            print(f"   Tipo: {col_info[2]}")
            print(f"   Nullable: {nullable}")
            print(f"   Default: {col_info[4]}")
        
        print()
        print("✅ Migração concluída com sucesso!")
        print()
        print("📊 Resumo:")
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total = cursor.fetchone()[0]
        print(f"   Total de produtos: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE tipo_produto = 'PAI'")
        total_pai = cursor.fetchone()[0]
        print(f"   Produtos PAI: {total_pai}")
        
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE preco_venda IS NULL OR preco_venda = 0")
        sem_preco = cursor.fetchone()[0]
        print(f"   Produtos sem preço: {sem_preco}")
        
        conn.close()
        
        print()
        print(f"🕐 Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRAÇÃO: preco_venda NULLABLE para produtos PAI")
    print("=" * 60)
    print()
    
    sucesso = migrar_preco_venda_nullable()
    
    if not sucesso:
        print()
        print("⚠️  A migração falhou! Verifique os erros acima.")
        exit(1)
    
    print()
    print("🎉 Pronto! Agora produtos PAI podem ser criados sem preço.")
