"""
Script para migrar .dict() para .model_dump() (Pydantic v2)
"""
import os
import re

arquivos_com_dict = [
    "app/categorias_routes.py",
    "app/clientes_routes.py",
    "app/contas_bancarias_routes.py",
    "app/lancamentos_routes.py",
    "app/notas_entrada_routes.py",
    "app/produtos_routes.py"
]

def migrar_dict_para_model_dump(caminho):
    print(f"📝 Processando: {caminho}")
    
    if not os.path.exists(caminho):
        print(f"  ❌ Arquivo não encontrado!")
        return 0
    
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Padrões a substituir:
    # 1. .dict() -> .model_dump()
    # 2. .dict(exclude_unset=True) -> .model_dump(exclude_unset=True)
    # 3. .dict(exclude_none=True) -> .model_dump(exclude_none=True)
    # etc.
    
    modificacoes = 0
    
    # Substituir .dict( por .model_dump(
    count_dict_paren = conteudo.count('.dict(')
    if count_dict_paren > 0:
        conteudo = conteudo.replace('.dict(', '.model_dump(')
        modificacoes += count_dict_paren
        print(f"  ✅ Substituído .dict( → .model_dump( ({count_dict_paren}x)")
    
    if modificacoes > 0:
        # Salvar arquivo
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        return modificacoes
    else:
        print(f"  ℹ️  Nenhuma ocorrência de .dict( encontrada")
        return 0

def main():
    print("🚀 Migrando .dict() → .model_dump() (Pydantic v2)\n")
    
    total_modificacoes = 0
    arquivos_alterados = 0
    
    for arquivo in arquivos_com_dict:
        if os.path.exists(arquivo):
            mods = migrar_dict_para_model_dump(arquivo)
            if mods > 0:
                arquivos_alterados += 1
                total_modificacoes += mods
        else:
            print(f"❌ Arquivo não encontrado: {arquivo}")
    
    print(f"\n" + "="*60)
    print(f"✨ Migração .dict() → .model_dump() concluída!")
    print(f"📊 Arquivos alterados: {arquivos_alterados}")
    print(f"🔢 Total de substituições: {total_modificacoes}")
    print(f"="*60)

if __name__ == "__main__":
    main()
