"""
Script para migrar modelos Pydantic v1 para v2
Substitui 'orm_mode = True' por 'from_attributes=True' em ConfigDict
"""
import os
import re

arquivos_para_migrar = [
    "app/categorias_routes.py",
    "app/chat_routes.py",
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
    "app/notas_entrada_routes.py",
    "app/pedidos_compra_routes.py",
    "app/produtos_routes.py",
    "app/tributacao_routes.py"
]

def migrar_arquivo(caminho):
    print(f"📝 Processando: {caminho}")
    
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Contar quantas vezes orm_mode aparece
    count_orm_mode = conteudo.count('orm_mode')
    
    if count_orm_mode == 0:
        print(f"  ✅ Já migrado (não contém orm_mode)")
        return 0
    
    # Substituir 'orm_mode = True' por 'from_attributes=True' dentro de class Config
    # Padrão para detectar class Config: seguido de orm_mode
    padrao = r'(\s+class Config:\s+)orm_mode\s*=\s*True'
    
    # Contar ocorrências
    matches = re.findall(padrao, conteudo)
    
    if matches:
        # Fazer a substituição
        conteudo_novo = re.sub(
            padrao,
            r'\1model_config = {"from_attributes": True}',
            conteudo
        )
        
        # Salvar o arquivo
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo_novo)
        
        print(f"  ✅ Migrado! ({len(matches)} ocorrências)")
        return len(matches)
    else:
        print(f"  ⚠️  Contém orm_mode mas não no padrão esperado - revisar manualmente")
        return 0

def main():
    print("🚀 Iniciando migração Pydantic v1 → v2\n")
    
    total_modificacoes = 0
    
    for arquivo in arquivos_para_migrar:
        if os.path.exists(arquivo):
            modificacoes = migrar_arquivo(arquivo)
            total_modificacoes += modificacoes
        else:
            print(f"❌ Arquivo não encontrado: {arquivo}")
    
    print(f"\n✨ Migração concluída!")
    print(f"📊 Total de substituições: {total_modificacoes}")
    print("\n⚠️  IMPORTANTE: Revise os arquivos e teste o sistema!")

if __name__ == "__main__":
    main()
