"""
Migration: Criar tabela empresa_config_geral

Cria tabela para armazenar configurações gerais da empresa,
incluindo parâmetros de margem para indicadores do PDV.

Usage:
    python backend/scripts/migrate_empresa_config_geral.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import SessionLocal, engine
from sqlalchemy import text

def run_migration():
    """Executa a migration"""
    db = SessionLocal()
    
    try:
        print("🚀 Criando tabela empresa_config_geral...\n")
        
        # SQL para criar a tabela
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS empresa_config_geral (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL,
            
            -- Dados básicos
            razao_social VARCHAR(200),
            nome_fantasia VARCHAR(200),
            cnpj VARCHAR(18),
            inscricao_estadual VARCHAR(20),
            inscricao_municipal VARCHAR(20),
            
            -- Endereço
            logradouro VARCHAR(200),
            numero VARCHAR(20),
            complemento VARCHAR(100),
            bairro VARCHAR(100),
            cidade VARCHAR(100),
            uf VARCHAR(2),
            cep VARCHAR(10),
            
            -- Contato
            telefone VARCHAR(20),
            email VARCHAR(100),
            site VARCHAR(100),
            
            -- Parâmetros de margem (PDV)
            margem_saudavel_minima NUMERIC(5, 2) DEFAULT 30.0,
            margem_alerta_minima NUMERIC(5, 2) DEFAULT 15.0,
            mensagem_venda_saudavel TEXT DEFAULT '✅ Venda Saudável! Margem excelente.',
            mensagem_venda_alerta TEXT DEFAULT '⚠️ ATENÇÃO: Margem reduzida! Revisar preço.',
            mensagem_venda_critica TEXT DEFAULT '🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!',
            
            -- Parâmetros financeiros
            dias_tolerancia_atraso INTEGER DEFAULT 5,
            meta_faturamento_mensal NUMERIC(12, 2) DEFAULT 0,
            
            -- Parâmetros de estoque
            alerta_estoque_percentual INTEGER DEFAULT 20,
            dias_produto_parado INTEGER DEFAULT 90,
            
            -- Configurações fiscais rápidas
            aliquota_imposto_padrao NUMERIC(5, 2) DEFAULT 7.0,
            
            -- Auditoria
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT empresa_config_geral_tenant_id_key UNIQUE (tenant_id)
        );
        
        -- Índices
        CREATE INDEX IF NOT EXISTS idx_empresa_config_geral_tenant_id 
            ON empresa_config_geral(tenant_id);
        
        CREATE INDEX IF NOT EXISTS idx_empresa_config_geral_ativo 
            ON empresa_config_geral(ativo);
        """
        
        db.execute(text(create_table_sql))
        db.commit()
        
        print("✅ Tabela empresa_config_geral criada com sucesso!")
        print("\n📋 Estrutura:")
        print("   • Dados básicos (razão social, CNPJ, etc)")
        print("   • Parâmetros de margem (saudável, alerta, crítico)")
        print("   • Mensagens personalizadas do PDV")
        print("   • Alíquota de imposto padrão")
        print("   • Multi-tenant (tenant_id)")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERRO ao criar tabela: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔨 MIGRATION: empresa_config_geral")
    print("="*60 + "\n")
    run_migration()
