#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para LIMPAR códigos de barras de produtos PAI e VARIAÇÕES em PRODUÇÃO.

AVISO: Este script opera em produção. Use com cuidado.
- Remove códigos de barras de todos os produtos PAI
- Remove códigos de barras de todas as VARIAÇÕES
- Move dados antigos para backup em JSON para auditoria

Uso:
  python limpar_codigo_barras_producao.py --visualizar     (só mostra quantos vão ser afetados)
  python limpar_codigo_barras_producao.py --executar       (faz as mudanças, cria backup)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Tenta carregar .env, mas não falha se não existir (em Docker não existe)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import Session
from app.produtos_models import Produto

def get_database_url():
    """Detecta automaticamente se está em DEV ou PRODUÇÃO"""
    db_url = os.getenv("DATABASE_URL", "")
    
    # Se a variável aponta para 5433, é DEV
    if "5433" in db_url:
        return db_url  # Usa a URL do .env
    
    # Caso contrário, retorna a URL de PRODUÇÃO
    return "postgresql://postgres:postgres@localhost:5432/petshop_prod"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Limpar códigos de barras de produtos PAI e VARIAÇÕES"
    )
    parser.add_argument(
        "--visualizar",
        action="store_true",
        help="Apenas visualiza os registros que serão afetados (sem fazer mudanças)"
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Executa as remoções com segurança (cria backup JSON primeiro)"
    )
    
    args = parser.parse_args()
    
    if not args.visualizar and not args.executar:
        parser.print_help()
        print("\n⚠️  Escolha --visualizar ou --executar")
        sys.exit(1)
    
    db_url = get_database_url()
    ambiente = "PRODUÇÃO" if "5432" in db_url else "DESENVOLVIMENTO"
    
    print(f"\n🔗 Conectando ao banco de {ambiente}...")
    print(f"   URL: {db_url.split('@')[-1]}")
    
    engine = create_engine(db_url)
    
    with Session(engine) as session:
        # Query: Produtos PAI
        produtos_pai = session.query(
            Produto
        ).filter(
            (Produto.tipo_produto == 'PAI') | (Produto.is_parent == True)
        ).all()
        
        # Query: Produtos VARIAÇÃO
        produtos_variacao = session.query(
            Produto
        ).filter(
            (Produto.tipo_produto == 'VARIACAO') | (Produto.produto_pai_id != None)
        ).all()
        
        # Remover duplicatas (um produto pode ser PAI e já estar em variação)
        produtos_variacao = [p for p in produtos_variacao if p not in produtos_pai]
        
        total_pai = len(produtos_pai)
        total_variacao = len(produtos_variacao)
        total_com_codigo = sum(1 for p in produtos_pai + produtos_variacao if p.codigo_barras)
        
        print(f"\n📊 RELATÓRIO:")
        print(f"   Produtos PAI encontrados:        {total_pai}")
        print(f"   Produtos VARIAÇÃO encontrados:   {total_variacao}")
        print(f"   Total para processar:             {total_pai + total_variacao}")
        print(f"   Com código de barras atualmente:  {total_com_codigo}")
        
        if args.visualizar:
            print(f"\n📋 MODO VISUALIZAR - Nenhuma mudança será feita")
            
            if produtos_pai:
                print(f"\n🔴 Produtos PAI que perderão código de barras:")
                for p in produtos_pai[:10]:  # Mostrar apenas primeiros 10
                    if p.codigo_barras:
                        print(f"   [{p.id}] {p.codigo} - {p.nome}: '{p.codigo_barras}'")
                if total_pai > 10:
                    print(f"   ... e mais {total_pai - 10}")
            
            if produtos_variacao:
                print(f"\n🟡 Produtos VARIAÇÃO que perderão código de barras:")
                for p in produtos_variacao[:10]:  # Mostrar apenas primeiros 10
                    if p.codigo_barras:
                        print(f"   [{p.id}] {p.codigo} - {p.nome}: '{p.codigo_barras}'")
                if total_variacao > 10:
                    print(f"   ... e mais {total_variacao - 10}")
            
            print(f"\n✅ Use --executar para realmente fazer as mudanças")
        
        elif args.executar:
            print(f"\n⏳ MODO EXECUÇÃO - Preparando limpeza segura...")
            
            # Criar backup JSON com todos os dados antes da mudança
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "ambiente": ambiente,
                "total_produtos_pai": total_pai,
                "total_produtos_variacao": total_variacao,
                "produtos_pai": [
                    {
                        "id": p.id,
                        "codigo": p.codigo,
                        "nome": p.nome,
                        "codigo_barras_anterior": p.codigo_barras,
                        "tipo_produto": p.tipo_produto,
                    }
                    for p in produtos_pai if p.codigo_barras
                ],
                "produtos_variacao": [
                    {
                        "id": p.id,
                        "codigo": p.codigo,
                        "nome": p.nome,
                        "codigo_barras_anterior": p.codigo_barras,
                        "tipo_produto": p.tipo_produto,
                        "produto_pai_id": p.produto_pai_id,
                    }
                    for p in produtos_variacao if p.codigo_barras
                ]
            }
            
            # Salvar backup
            backup_dir = Path("backups_codigo_barras_limpeza")
            backup_dir.mkdir(exist_ok=True)
            backup_file = backup_dir / f"backup_codigo_barras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Backup criado: {backup_file}")
            
            # Confirmação final
            print(f"\n⚠️  CONFIRMAÇÃO FINAL:")
            print(f"    Vou limpar {total_com_codigo} código(s) de barras")
            print(f"    PAI: {sum(1 for p in produtos_pai if p.codigo_barras)}")
            print(f"    VARIAÇÕES: {sum(1 for p in produtos_variacao if p.codigo_barras)}")
            response = input("\n   Digita 'SIM' para continuar: ").strip().upper()
            
            if response != "SIM":
                print("❌ Operação cancelada pelo usuário")
                sys.exit(0)
            
            # EXECUTAR A LIMPEZA
            print(f"\n🧹 Limpando códigos de barras...")
            
            count_pai = 0
            for produto in produtos_pai:
                if produto.codigo_barras:
                    produto.codigo_barras = None
                    count_pai += 1
            
            count_variacao = 0
            for produto in produtos_variacao:
                if produto.codigo_barras:
                    produto.codigo_barras = None
                    count_variacao += 1
            
            # Commit
            try:
                session.commit()
                print(f"\n✅ SUCESSO!")
                print(f"   ✓ {count_pai} código(s) de barras removido(s) de produtos PAI")
                print(f"   ✓ {count_variacao} código(s) de barras removido(s) de VARIAÇÕES")
                print(f"   ✓ Total: {count_pai + count_variacao} registros atualizados")
                print(f"\n📌 Backup disponível em: {backup_file}")
                print(f"   Use este arquivo para auditoria ou reversão se necessário")
            except Exception as e:
                session.rollback()
                print(f"\n❌ ERRO durante execução!")
                print(f"   {str(e)}")
                sys.exit(1)

if __name__ == "__main__":
    main()
