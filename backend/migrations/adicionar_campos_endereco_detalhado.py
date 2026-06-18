"""
Migration: Adicionar campos detalhados de endereço em configuracoes_entrega
Data: 2026-02-01
Descrição: Adiciona CEP, número, complemento, bairro, cidade e estado separados
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DB_NAME = os.getenv("POSTGRES_DB", "pet_shop_pro")


def run_migration():
    """Adiciona campos de endereço detalhado"""
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )

    try:
        cursor = conn.cursor()

        print("📍 Adicionando campos de endereço detalhado em configuracoes_entrega...")

        # Adicionar novos campos
        cursor.execute("""
            ALTER TABLE configuracoes_entrega
            ADD COLUMN IF NOT EXISTS cep VARCHAR(9),
            ADD COLUMN IF NOT EXISTS numero VARCHAR(20),
            ADD COLUMN IF NOT EXISTS complemento VARCHAR(100),
            ADD COLUMN IF NOT EXISTS bairro VARCHAR(100),
            ADD COLUMN IF NOT EXISTS cidade VARCHAR(100),
            ADD COLUMN IF NOT EXISTS estado VARCHAR(2);
        """)

        # Renomear ponto_inicial_rota para logradouro (mais semântico)
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'configuracoes_entrega' 
                    AND column_name = 'ponto_inicial_rota'
                ) THEN
                    ALTER TABLE configuracoes_entrega 
                    RENAME COLUMN ponto_inicial_rota TO logradouro;
                END IF;
            END $$;
        """)

        # Adicionar comentários
        cursor.execute("""
            COMMENT ON COLUMN configuracoes_entrega.logradouro IS 'Rua/Avenida do ponto inicial';
            COMMENT ON COLUMN configuracoes_entrega.cep IS 'CEP do ponto inicial (formato: 00000-000)';
            COMMENT ON COLUMN configuracoes_entrega.numero IS 'Número do endereço';
            COMMENT ON COLUMN configuracoes_entrega.complemento IS 'Complemento (opcional)';
            COMMENT ON COLUMN configuracoes_entrega.bairro IS 'Bairro do ponto inicial';
            COMMENT ON COLUMN configuracoes_entrega.cidade IS 'Cidade do ponto inicial';
            COMMENT ON COLUMN configuracoes_entrega.estado IS 'Estado (UF) - 2 caracteres';
        """)

        conn.commit()
        print("✅ Campos de endereço detalhado adicionados com sucesso!")

        # Verificar colunas
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'configuracoes_entrega'
            AND column_name IN ('logradouro', 'cep', 'numero', 'complemento', 'bairro', 'cidade', 'estado')
            ORDER BY column_name;
        """)

        print("\n📋 Colunas criadas:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}" + (f"({row[2]})" if row[2] else ""))

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro na migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
