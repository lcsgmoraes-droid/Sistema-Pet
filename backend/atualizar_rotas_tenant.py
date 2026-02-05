"""
Script para atualizar TODAS as rotas do sistema para usar get_current_user_and_tenant
"""
import os
import re
from pathlib import Path

# Diretório raiz do backend
BACKEND_DIR = Path(__file__).parent / "app"

# Padrões a buscar e substituir
PATTERNS = [
    # Padrão 1: current_user: User = Depends(get_current_user) seguido de get_current_tenant()
    {
        "old": r"(\s+)current_user:\s*User\s*=\s*Depends\(get_current_user\)",
        "new": r"\1user_and_tenant = Depends(get_current_user_and_tenant)",
        "add_unpack": True
    }
]

def encontrar_arquivos_routes():
    """Encontra todos os arquivos *routes*.py no diretório app/"""
    routes_files = []
    for file in BACKEND_DIR.glob("**/*routes*.py"):
        if "test" not in str(file).lower() and "__pycache__" not in str(file):
            routes_files.append(file)
    return routes_files

def precisa_atualizar(filepath):
    """Verifica se o arquivo precisa de atualização"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica se já usa get_current_user_and_tenant
    if "get_current_user_and_tenant" in content:
        # Conta quantas vezes usa cada padrão
        uses_new = content.count("get_current_user_and_tenant")
        uses_old = content.count("Depends(get_current_user)")
        
        if uses_old == 0:
            return False  # Já está totalmente atualizado
    
    # Verifica se usa get_current_user
    if "Depends(get_current_user)" in content:
        return True
    
    return False

def atualizar_imports(content):
    """Adiciona import de get_current_user_and_tenant se necessário"""
    if "get_current_user_and_tenant" in content:
        return content  # Já tem o import
    
    # Encontrar linha de import do get_current_user
    import_pattern = r"from\s+\.auth\s+import\s+([^\n]+)"
    match = re.search(import_pattern, content)
    
    if match:
        imports = match.group(1)
        if "get_current_user" in imports and "get_current_user_and_tenant" not in imports:
            # Adicionar o import da dependency
            new_import = "from .auth.dependencies import get_current_user_and_tenant\n"
            # Inserir após os imports do .auth
            content = re.sub(
                r"(from\s+\.auth\s+import\s+[^\n]+\n)",
                r"\1" + new_import,
                content,
                count=1
            )
    
    return content

def atualizar_funcao(content):
    """Atualiza a assinatura da função"""
    # Padrão: current_user: User = Depends(get_current_user)
    pattern = r"(\s+)current_user:\s*User\s*=\s*Depends\(get_current_user\)([,\)])"
    replacement = r"\1user_and_tenant = Depends(get_current_user_and_tenant)\2"
    
    content = re.sub(pattern, replacement, content)
    
    return content

def adicionar_unpacking(content):
    """Adiciona a linha de unpacking após a assinatura da função"""
    # Encontrar funções que usam user_and_tenant = Depends(...)
    # e adicionar current_user, tenant_id = user_and_tenant logo após
    
    # Padrão: def função(...\n    user_and_tenant = Depends...\n):
    # Queremos adicionar o unpacking logo após o """docstring""" ou após o ):
    
    pattern = r"(user_and_tenant\s*=\s*Depends\(get_current_user_and_tenant\)[,\)][^\n]*\n)([ \t]+)(\"\"\"[^\"]*\"\"\"\n)?"
    
    def replacer(match):
        full_match = match.group(0)
        indent = match.group(2)
        docstring = match.group(3) or ""
        
        # Se já tem o unpacking, não adiciona de novo
        if "current_user, tenant_id = user_and_tenant" in full_match:
            return full_match
        
        # Adicionar unpacking após docstring (se houver) ou após a assinatura
        if docstring:
            return match.group(1) + indent + docstring + indent + "current_user, tenant_id = user_and_tenant\n"
        else:
            return match.group(1) + indent + "current_user, tenant_id = user_and_tenant\n"
    
    content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    
    return content

def remover_get_current_tenant_calls(content):
    """Remove chamadas a get_current_tenant() já que temos tenant_id"""
    # Padrão: tenant_id = get_current_tenant()
    content = re.sub(
        r"[ \t]*tenant_id\s*=\s*get_current_tenant\(\)\s*\n",
        "",
        content
    )
    
    # Padrão: if tenant_id is None: raise HTTPException...
    content = re.sub(
        r"[ \t]*if\s+tenant_id\s+is\s+None:\s*\n[ \t]*raise\s+HTTPException[^\n]+\n",
        "",
        content
    )
    
    return content

def processar_arquivo(filepath):
    """Processa um arquivo de rotas"""
    print(f"\n📄 Processando: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    content = original_content
    
    # 1. Atualizar imports
    content = atualizar_imports(content)
    
    # 2. Atualizar assinatura das funções
    content = atualizar_funcao(content)
    
    # 3. Adicionar unpacking
    content = adicionar_unpacking(content)
    
    # 4. Remover chamadas antigas
    content = remover_get_current_tenant_calls(content)
    
    if content != original_content:
        # Salvar arquivo atualizado
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ Atualizado!")
        return True
    else:
        print(f"   ⏭️  Nenhuma mudança necessária")
        return False

def main():
    print("=" * 60)
    print("🔧 ATUALIZANDO ROTAS PARA MULTI-TENANT")
    print("=" * 60)
    
    routes_files = encontrar_arquivos_routes()
    print(f"\n📁 Encontrados {len(routes_files)} arquivos de rotas")
    
    to_update = []
    for filepath in routes_files:
        if precisa_atualizar(filepath):
            to_update.append(filepath)
    
    print(f"\n🎯 {len(to_update)} arquivos precisam de atualização")
    
    if not to_update:
        print("\n✅ Todos os arquivos já estão atualizados!")
        return
    
    print("\nArquivos a atualizar:")
    for fp in to_update:
        print(f"  - {fp.name}")
    
    input("\n⏸️  Pressione ENTER para continuar...")
    
    updated = 0
    for filepath in to_update:
        if processar_arquivo(filepath):
            updated += 1
    
    print("\n" + "=" * 60)
    print(f"✅ CONCLUÍDO! {updated} arquivos atualizados")
    print("=" * 60)
    print("\n🔄 Aguarde o backend recarregar automaticamente (--reload)")

if __name__ == "__main__":
    main()
