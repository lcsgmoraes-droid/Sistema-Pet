"""
Script para atualizar TODOS os arquivos *routes.py para usar get_current_user_and_tenant
"""
import os
import re

def atualizar_arquivo(filepath):
    """Atualiza um arquivo de rotas para usar get_current_user_and_tenant"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    mudou = False
    
    # 1. Adicionar import se não existir
    if 'get_current_user_and_tenant' not in content:
        if 'from app.auth import get_current_user' in content:
            content = content.replace(
                'from app.auth import get_current_user',
                'from app.auth import get_current_user\nfrom app.auth.dependencies import get_current_user_and_tenant'
            )
            mudou = True
        elif 'from app.auth.dependencies import' in content:
            # Já tem import de dependencies, só adicionar get_current_user_and_tenant
            content = re.sub(
                r'from app\.auth\.dependencies import ([^\n]+)',
                lambda m: f"from app.auth.dependencies import {m.group(1)}, get_current_user_and_tenant" if 'get_current_user_and_tenant' not in m.group(1) else m.group(0),
                content
            )
            mudou = True
    
    # 2. Substituir current_user: User = Depends(get_current_user)
    #    por user_and_tenant = Depends(get_current_user_and_tenant)
    pattern = r'(\s+)current_user:\s*User\s*=\s*Depends\(get_current_user\)'
    if re.search(pattern, content):
        content = re.sub(
            pattern,
            r'\1user_and_tenant = Depends(get_current_user_and_tenant)',
            content
        )
        mudou = True
    
    if mudou:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    total_atualizados = 0
    arquivos_atualizados = []
    
    for root, dirs, files in os.walk('app'):
        for file in files:
            if file.endswith('_routes.py') or file == 'routes.py':
                filepath = os.path.join(root, file)
                
                # Verificar se precisa atualizar
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'Depends(get_current_user)' in content and 'User = Depends(get_current_user)' in content:
                    print(f"🔄 Atualizando {filepath}...")
                    if atualizar_arquivo(filepath):
                        total_atualizados += 1
                        arquivos_atualizados.append(filepath)
                        print(f"   ✅ Atualizado!")
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMO:")
    print(f"   Total de arquivos atualizados: {total_atualizados}")
    if arquivos_atualizados:
        print(f"\n📁 Arquivos modificados:")
        for arq in arquivos_atualizados:
            print(f"   - {arq}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
