"""
Script para corrigir TODOS os usos incorretos de current_user no código
"""
import re
from pathlib import Path

# Diretório backend
backend_dir = Path(r"C:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app")

# Arquivos a verificar (excluindo backups)
arquivos_routes = [
    "produtos_routes.py",
    # Adicione outros se necessário
]

def encontrar_problemas(arquivo_path):
    """Encontra todos os usos incorretos de current_user.id"""
    with open(arquivo_path, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    problemas = []
    
    for i, linha in enumerate(linhas, 1):
        # Buscar current_user.id ou current_user.tenant_id sendo usado diretamente
        if 'current_user.id' in linha and '==' in linha:
            problemas.append({
                'linha': i,
                'conteudo': linha.strip(),
                'tipo': 'filtro_incorreto'
            })
        elif 'current_user.id' in linha and ('user_id=' in linha or 'tenant_id=' in linha):
            problemas.append({
                'linha': i,
                'conteudo': linha.strip(),
                'tipo': 'criacao_incorreta'
            })
    
    return problemas

# Executar busca
print("=" * 70)
print("🔍 BUSCANDO PROBLEMAS COM current_user.id")
print("=" * 70)
print()

total_problemas = 0

for arquivo in arquivos_routes:
    arquivo_path = backend_dir / arquivo
    
    if not arquivo_path.exists():
        continue
    
    problemas = encontrar_problemas(arquivo_path)
    
    if problemas:
        print(f"📄 {arquivo}")
        print("-" * 70)
        for p in problemas:
            print(f"   Linha {p['linha']:4d} | {p['tipo']:20s} | {p['conteudo']}")
            total_problemas += 1
        print()

print("=" * 70)
print(f"✅ Total de problemas encontrados: {total_problemas}")
print("=" * 70)
