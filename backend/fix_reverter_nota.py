"""
Script para corrigir a função de reverter nota de entrada
Adiciona tratamento de erros robusto para evitar erro 500
"""
import re

arquivo = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app\notas_entrada_routes.py"

with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Padrão 1: Adicionar try-except no bloco de reversão de preços
padrao1 = r'(            if lote:\s+# REVERTER PRE.*?O DE CUSTO se foi alterado\s+)(historico_preco = db\.query)'
substituicao1 = r'\1try:\n                    \2'

conteudo = re.sub(padrao1, substituicao1, conteudo, flags=re.DOTALL)

# Padrão 2: Adicionar conversão para float e except após delete historico_preco
padrao2 = r'(preco_custo_revertido = )(historico_preco\.preco_custo_anterior if historico_preco\.preco_custo_anterior is not None else 0)'
substituicao2 = r'\1float(historico_preco.preco_custo_anterior) if historico_preco.preco_custo_anterior is not None else 0.0'

conteudo = re.sub(padrao2, substituicao2, conteudo)

# Padrão 3: Fazer o mesmo para preco_venda_revertido
padrao3 = r'(preco_venda_revertido = )(historico_preco\.preco_venda_anterior if historico_preco\.preco_venda_anterior is not None else 0)'
substituicao3 = r'\1float(historico_preco.preco_venda_anterior) if historico_preco.preco_venda_anterior is not None else 0.0'

conteudo = re.sub(padrao3, substituicao3, conteudo)

# Padrão 4: Adicionar proteção no log
padrao4 = r'(logger\.info\(f"  .*? Revertendo pre.*?o de custo: R\$ \{)(produto\.preco_custo)'
substituicao4 = r'\1float(produto.preco_custo) if produto.preco_custo is not None else 0.0'

conteudo = re.sub(padrao4, substituicao4, conteudo)

# Padrão 5: Adicionar except após db.delete(historico_preco)
padrao5 = r'(db\.delete\(historico_preco\)\s+)(# Remover quantidade do estoque)'
substituicao5 = r'\1except Exception as e:\n                    logger.warning(f"  ⚠️ Erro ao reverter preços do produto {produto.id}: {str(e)}")\n                \n                \2'

conteudo = re.sub(padrao5, substituicao5, conteudo)

# Padrão 6: Adicionar try-except na criação da movimentação de estorno
padrao6 = r'(# Registrar movimenta.*?o de estorno\s+)(movimentacao_estorno = EstoqueMovimentacao\()'
substituicao6 = r'\1try:\n                    \2'

conteudo = re.sub(padrao6, substituicao6, conteudo, flags=re.DOTALL)

# Padrão 7: Adicionar float() para custo_unitario e valor_total
conteudo = conteudo.replace(
    'custo_unitario=item.valor_unitario,',
    'custo_unitario=float(item.valor_unitario) if item.valor_unitario is not None else 0.0,'
)
conteudo = conteudo.replace(
    'valor_total=item.valor_total,',
    'valor_total=float(item.valor_total) if item.valor_total is not None else 0.0,'
)

# Padrão 8: Adicionar except após db.add(movimentacao_estorno)
padrao8 = r'(db\.add\(movimentacao_estorno\)\s+)(# Excluir lote)'
substituicao8 = r'\1except Exception as e:\n                    logger.warning(f"  ⚠️ Erro ao criar movimentação de estorno: {str(e)}")\n                \n                \2'

conteudo = re.sub(padrao8, substituicao8, conteudo)

# Salvar arquivo
with open(arquivo, 'w', encoding='utf-8') as f:
    f.write(conteudo)

print("✅ Correções aplicadas com sucesso!")
print("   - Adicionado tratamento de erros na reversão de preços")
print("   - Adicionado conversão para float em valores monetários")
print("   - Adicionado tratamento de erros na movimentação de estorno")
