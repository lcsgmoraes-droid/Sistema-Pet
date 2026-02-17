import re

# Ler o arquivo
file_path = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app\produtos_routes.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para encontrar funções com user_and_tenant mas sem extração de tenant_id
# Procurar por funções que têm user_and_tenant = Depends(get_current_user_and_tenant)
# e depois usam tenant_id sem declarar

def fix_function(match):
    """
    Adiciona a linha de extração de tenant_id logo após o fechamento dos parâmetros
    """
    func_text = match.group(0)
    
    # Verificar se já tem a extração
    if 'current_user, tenant_id = user_and_tenant' in func_text:
        return func_text
    
    # Verificar se usa tenant_id
    if 'tenant_id' not in func_text:
        return func_text
    
    # Encontrar o padrão: user_and_tenant = Depends(...)\n):\n
    pattern = r'(user_and_tenant\s*=\s*Depends\(get_current_user_and_tenant\)\s*\n\):\s*\n)'
    
    if re.search(pattern, func_text):
        # Adicionar a extração após o fechamento dos parâmetros
        replacement = r'\1    current_user, tenant_id = user_and_tenant\n'
        func_text = re.sub(pattern, replacement, func_text)
    
    return func_text

# Padrão para capturar funções completas
# Captura desde @router até o próximo @router ou final do arquivo
func_pattern = r'(@router\.[^\n]+\n(?:async )?def [^\n]+\([^)]*user_and_tenant[^)]*\)[^:]*:.*?)(?=\n@router|\n@app|\nclass |\Z)'

# Aplicar correção
content = re.sub(func_pattern, fix_function, content, flags=re.DOTALL)

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Arquivo corrigido com sucesso!")
