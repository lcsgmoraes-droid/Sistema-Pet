"""
Script para corrigir linha por linha
"""

arquivo = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app\notas_entrada_routes.py"

with open(arquivo, 'r', encoding='utf-8') as f:
    linhas = f.readlines()

# Encontrar a linha problemática e corrigir
for i in range(len(linhas)):
    # Linha 2004 (índice 2003) - comentário
    if i == 2003 and 'Reverter preços anteriores' in linhas[i]:
        # Garantir que tem indentação correta (24 espaços)
        linhas[i] = ' ' * 24 + linhas[i].lstrip()
    
    # Linhas 2005-2011 - código dentro do if historico_preco
    if 2004 <= i <= 2010:
        # Se a linha não começa com 24 ou mais espaços e não está vazia
        if linhas[i].strip() and not linhas[i].startswith(' ' * 24):
            # Adicionar indentação correta
            linhas[i] = ' ' * 24 + linhas[i].lstrip()

with open(arquivo, 'w', encoding='utf-8') as f:
    f.writelines(linhas)

print("✅ Linhas corrigidas!")
