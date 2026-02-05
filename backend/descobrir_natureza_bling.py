"""
Script para descobrir o ID correto da natureza de operação no Bling
Execute: python descobrir_natureza_bling.py
"""
import os
import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.bling_integration import BlingAPI

def main():
    print("\n" + "="*70)
    print("  DESCOBRIR NATUREZA DE OPERAÇÃO - BLING")
    print("="*70)
    
    try:
        bling = BlingAPI()
        print("\n🔍 Buscando naturezas de operação...")
        
        resultado = bling.listar_naturezas_operacoes()
        naturezas = resultado.get('data', [])
        
        if not naturezas:
            print("❌ Nenhuma natureza encontrada!")
            return
        
        print(f"\n✅ Encontradas {len(naturezas)} naturezas:\n")
        print("-" * 70)
        
        # Listar todas
        for nat in naturezas:
            nat_id = nat.get('id')
            descricao = nat.get('descricao', 'Sem descrição')
            tipo = nat.get('tipo', '')
            
            print(f"ID: {nat_id:3d}  |  {descricao}")
            if tipo:
                print(f"         Tipo: {tipo}")
            print("-" * 70)
        
        print("\n" + "="*70)
        print("📋 INSTRUÇÕES:")
        print("="*70)
        print("1. Copie o ID da natureza desejada")
        print("2. Abra o arquivo: backend/app/bling_integration.py")
        print("3. Encontre a linha: \"naturezaOperacao\": {\"id\": 1}")
        print("4. Substitua '1' pelo ID correto")
        print("5. Salve e reinicie o backend")
        print("="*70)
        
        print("\n💡 SUGESTÕES:")
        print("   - Para NFC-e de venda presencial, procure:")
        print("     'Venda de mercadoria', 'Venda ao consumidor', ou 'Venda presencial'")
        print()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\n⚠️  Verifique se:")
        print("   1. O token do Bling está configurado no .env")
        print("   2. O token não está expirado")
        print("   3. Se expirado, execute: python renovar_bling.py")

if __name__ == "__main__":
    main()
