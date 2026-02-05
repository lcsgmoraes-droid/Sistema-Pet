"""
Script para corrigir erros de sintaxe causados pelo unpacking incorreto
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).parent / "app"

def corrigir_arquivo(filepath):
    """Corrige o padrão problemático no arquivo"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Padrão problemático:
    # db: Session = Depends(...),
    # user_and_tenant = Depends(...),
    # current_user, tenant_id = user_and_tenant
    # algum_parametro: Type = ...
    
    # Precisamos encontrar e reorganizar esses casos
    
    # Padrão regex mais abrangente
    pattern = r"""
    (def\s+\w+\([^)]*?)                           # Início da função até antes dos parâmetros problemáticos
    (\s+user_and_tenant\s*=\s*Depends\([^)]+\),) # user_and_tenant = Depends(...)
    (\s+current_user,\s*tenant_id\s*=\s*user_and_tenant\n) # unpacking errado
    (\s*\w+:.*?=.*?)                              # parâmetro que veio depois (o problema!)
    (\):)                                         # Fechamento da função
    """
    
    mudou = False
    
    # Buscar todas as ocorrências do padrão problemático
    # db: Session = Depends(...),
    # user_and_tenant = Depends(...),
    # current_user, tenant_id = user_and_tenant
    # param: Type = ...
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar linha com unpacking problemático
        if re.match(r'^\s+current_user,\s*tenant_id\s*=\s*user_and_tenant\s*$', line):
            # Essa linha não deve estar aqui, deve ir para dentro da função
            # Pular essa linha por enquanto (vamos adicionar depois)
            unpacking_line = line
            i += 1
            
            # Próxima linha deve ser um parâmetro (o problema!)
            if i < len(lines) and re.match(r'^\s*\w+:', lines[i]):
                # Coletar todos os parâmetros restantes
                params_after = []
                while i < len(lines) and not lines[i].strip().startswith('):'):
                    params_after.append(lines[i])
                    i += 1
                
                # Adicionar fechamento
                if i < len(lines) and lines[i].strip().startswith('):'):
                    new_lines.append(lines[i])  # ):
                    i += 1
                    
                    # Agora adicionar os parâmetros antes do user_and_tenant
                    # Voltar e reorganizar
                    # Na verdade, já passamos do ponto...
                    # Vamos marcar para correção manual
                    print(f"⚠️  Encontrado padrão problemático em linha ~{i}: necessita correção manual")
                    for p in params_after:
                        new_lines.append(p)
                    mudou = True
                    continue
        else:
            new_lines.append(line)
            i += 1
    
    if mudou:
        content = '\n'.join(new_lines)
    
    # Abordagem mais direta: remover linhas de unpacking mal posicionadas
    # e adicionar no lugar certo (após docstring)
    
    # Padrão: função com docstring
    func_pattern = r'(def \w+\([^)]+user_and_tenant[^)]+\):\s*"""[^"]*""")'
    
    def add_unpacking(match):
        func_sig = match.group(0)
        if 'current_user, tenant_id = user_and_tenant' not in func_sig:
            # Adicionar após docstring
            return func_sig + '\n    current_user, tenant_id = user_and_tenant'
        return func_sig
    
    # Esta abordagem não funciona bem com regex...
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    print("=" * 60)
    print("CORRIGINDO ERROS DE SINTAXE")
    print("=" * 60)
    
    # Arquivos mencionados no erro
    arquivos_problema = [
        "ia_routes.py",
        # Adicionar outros conforme necessário
    ]
    
    for filename in arquivos_problema:
        filepath = BACKEND_DIR / filename
        if filepath.exists():
            print(f"\n📄 {filename}")
            # Por enquanto, apenas reportar
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                if re.match(r'^\s+current_user,\s*tenant_id\s*=\s*user_and_tenant\s*$', line):
                    print(f"   Linha {i}: {line.strip()}")
                    # Ver contexto
                    start = max(0, i-5)
                    end = min(len(lines), i+3)
                    print(f"   Contexto (linhas {start+1}-{end}):")
                    for j in range(start, end):
                        marker = ">>>" if j == i-1 else "   "
                        print(f"   {marker} {j+1:4d}: {lines[j].rstrip()}")

if __name__ == "__main__":
    main()
