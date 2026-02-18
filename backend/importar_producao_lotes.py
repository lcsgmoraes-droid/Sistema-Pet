#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para importar produtos para PRODUÇÃO em lotes controlados
"""

import sys
from importador_produtos import ImportadorProdutos

# CONFIGURAÇÕES DE PRODUÇÃO
DATABASE_URL_PROD = "postgresql://postgres:sua_senha@localhost:5432/petshop_prod"
TENANT_ID_PROD = "seu-tenant-id-producao"
USER_ID_PROD = 1

def importar_em_lotes():
    """Importa produtos em lotes pequenos para controle"""
    
    print("="*80)
    print("IMPORTAÇÃO PARA PRODUÇÃO - MODO SEGURO")
    print("="*80)
    print()
    print("⚠️  ATENÇÃO: Este script irá importar para o banco de PRODUÇÃO!")
    print()
    
    # Solicitar confirmação
    resposta = input("Deseja continuar? (digite 'SIM' para confirmar): ")
    if resposta.upper() != 'SIM':
        print("Operação cancelada.")
        return
    
    # Solicitar número de registros
    try:
        limite = int(input("\nQuantos produtos deseja importar neste lote? (recomendado: 50-100): "))
    except ValueError:
        print("Número inválido. Usando 50 como padrão.")
        limite = 50
    
    # Confirmar configurações
    print(f"\n📊 Configurações:")
    print(f"   - Banco: {DATABASE_URL_PROD}")
    print(f"   - Tenant: {TENANT_ID_PROD}")
    print(f"   - Limite: {limite} produtos")
    print()
    
    confirmacao = input("Confirma estas configurações? (SIM/não): ")
    if confirmacao.upper() != 'SIM':
        print("Operação cancelada.")
        return
    
    # Executar importação
    print("\n🚀 Iniciando importação...\n")
    
    importador = ImportadorProdutos(
        database_url=DATABASE_URL_PROD,
        tenant_id=TENANT_ID_PROD,
        user_id=USER_ID_PROD,
        dry_run=False  # PRODUÇÃO - vai gravar de verdade!
    )
    
    try:
        importador.importar_produtos(limite=limite)
        print("\n✅ Importação concluída!")
        print(f"\n📄 Verifique os logs em: {importador.log_file}")
    except Exception as e:
        print(f"\n❌ ERRO durante importação: {e}")
        sys.exit(1)


def dry_run_producao():
    """Simula importação para ver o que aconteceria"""
    
    print("="*80)
    print("SIMULAÇÃO DE IMPORTAÇÃO PARA PRODUÇÃO (DRY-RUN)")
    print("="*80)
    print()
    
    # Solicitar número de registros
    try:
        limite = int(input("Quantos produtos deseja simular? (padrão: 100): ") or "100")
    except ValueError:
        limite = 100
    
    print(f"\n🔍 Simulando importação de {limite} produtos...\n")
    
    importador = ImportadorProdutos(
        database_url=DATABASE_URL_PROD,
        tenant_id=TENANT_ID_PROD,
        user_id=USER_ID_PROD,
        dry_run=True  # SIMULAÇÃO - não grava nada
    )
    
    try:
        importador.importar_produtos(limite=limite)
        print("\n✅ Simulação concluída!")
        print(f"\n📄 Verifique os logs em: {importador.log_file}")
    except Exception as e:
        print(f"\n❌ ERRO durante simulação: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🐾 IMPORTADOR DE PRODUTOS - PRODUÇÃO\n")
    print("Escolha uma opção:")
    print("  1) Simular importação (dry-run - recomendado)")
    print("  2) Importar para PRODUÇÃO (cuidado!)")
    print("  0) Sair")
    print()
    
    opcao = input("Opção: ").strip()
    
    if opcao == "1":
        dry_run_producao()
    elif opcao == "2":
        importar_em_lotes()
    else:
        print("Saindo...")
