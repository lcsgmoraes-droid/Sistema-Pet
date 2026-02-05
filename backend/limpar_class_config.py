"""
Script para remover estruturas 'class Config:' duplicadas
e garantir uso correto do model_config
"""
import os
import re

def limpar_class_config(caminho):
    print(f"📝 Processando: {caminho}")
    
    if not os.path.exists(caminho):
        print(f"  ❌ Arquivo não encontrado!")
        return 0
    
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo_original = f.read()
    
    # Padrão: class Config: seguido de model_config (ERRADO)
    # Deve ser apenas model_config
    padrao = r'(\s+)class Config:\s+model_config\s*=\s*({[^}]+})'
    
    conteudo_novo = re.sub(
        padrao,
        r'\1model_config = \2',
        conteudo_original
    )
    
    modificacoes = len(re.findall(padrao, conteudo_original))
    
    if modificacoes > 0:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo_novo)
        print(f"  ✅ Corrigido! ({modificacoes} ocorrências)")
        return modificacoes
    else:
        print(f"  ℹ️  Nenhuma correção necessária")
        return 0

def main():
    print("🚀 Limpando estruturas class Config duplicadas\n")
    
    arquivos = [
        "app/clientes_routes.py",
        "app/contas_bancarias_routes.py",
        "app/contas_pagar_routes.py",
        "app/contas_receber_routes.py",
        "app/dre_ia_routes.py",
        "app/dre_routes.py",
        "app/estoque_routes.py",
        "app/financeiro_routes.py",
        "app/formas_pagamento_routes.py",
        "app/lancamentos_routes.py",
        "app/pedidos_compra_routes.py",
        "app/produtos_routes.py",
        "app/tributacao_routes.py"
    ]
    
    total_modificacoes = 0
    
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            mods = limpar_class_config(arquivo)
            total_modificacoes += mods
        else:
            print(f"❌ Arquivo não encontrado: {arquivo}")
    
    print(f"\n" + "="*60)
    print(f"✨ Limpeza concluída!")
    print(f"🔢 Total de correções: {total_modificacoes}")
    print(f"="*60)

if __name__ == "__main__":
    main()
