"""
Script para corrigir indentação do try-except na função reverter_entrada_estoque
"""
import re

arquivo = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app\notas_entrada_routes.py"

with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Encontrar e corrigir o bloco problemático
padrao_errado = r'(if lote:\s+# REVERTER PRE.*?O DE CUSTO se foi alterado\s+try:\s+)(historico_preco = db\.query\(ProdutoHistoricoPreco\)\.filter\(\s+)(ProdutoHistoricoPreco\.produto_id)'

substituicao = r'\1\2                    \3'

conteudo = re.sub(padrao_errado, substituicao, conteudo, flags=re.DOTALL)

# Corrigir todas as linhas do query que estão com indentação errada
conteudo = conteudo.replace(
    """                try:
                    historico_preco = db.query(ProdutoHistoricoPreco).filter(
                    ProdutoHistoricoPreco.produto_id""",
    """                try:
                    historico_preco = db.query(ProdutoHistoricoPreco).filter(
                        ProdutoHistoricoPreco.produto_id"""
)

conteudo = conteudo.replace(
    """                    ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                    ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                    ProdutoHistoricoPreco.tenant_id == tenant_id
                ).first()""",
    """                        ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                        ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                        ProdutoHistoricoPreco.tenant_id == tenant_id
                    ).first()"""
)

# Corrigir o if historico_preco
conteudo = conteudo.replace(
    """                ).first()
                
                if historico_preco:""",
    """                    ).first()
                    
                    if historico_preco:"""
)

# Corrigir indentação das linhas dentro do if
conteudo = conteudo.replace(
    """                    if historico_preco:
                    # Reverter pre""",
    """                    if historico_preco:
                        # Reverter pre"""
)

conteudo = conteudo.replace(
    """                        # Reverter preços anteriores (com fallback para 0 se None)
                    preco_custo_revertido = float""",
    """                        # Reverter preços anteriores (com fallback para 0 se None)
                        preco_custo_revertido = float"""
)

conteudo = conteudo.replace(
    """                        preco_custo_revertido = float(historico_preco.preco_custo_anterior) if historico_preco.preco_custo_anterior is not None else 0.0
                    preco_venda_revertido = float""",
    """                        preco_custo_revertido = float(historico_preco.preco_custo_anterior) if historico_preco.preco_custo_anterior is not None else 0.0
                        preco_venda_revertido = float"""
)

conteudo = conteudo.replace(
    """                        preco_venda_revertido = float(historico_preco.preco_venda_anterior) if historico_preco.preco_venda_anterior is not None else 0.0
                    
                    logger.info(f"  💰 Revertendo pre""",
    """                        preco_venda_revertido = float(historico_preco.preco_venda_anterior) if historico_preco.preco_venda_anterior is not None else 0.0
                        
                        logger.info(f"  💰 Revertendo pre"""
)

conteudo = conteudo.replace(
    """                        logger.info(f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo) if produto.preco_custo is not None else 0.0:.2f} → R$ {preco_custo_revertido:.2f}")
                    produto.preco_custo = preco_custo_revertido
                    produto.preco_venda = preco_venda_revertido
                    
                    # Excluir histórico
                    db.delete(historico_preco)""",
    """                        logger.info(f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo) if produto.preco_custo is not None else 0.0:.2f} → R$ {preco_custo_revertido:.2f}")
                        produto.preco_custo = preco_custo_revertido
                        produto.preco_venda = preco_venda_revertido
                        
                        # Excluir histórico
                        db.delete(historico_preco)"""
)

# Salvar
with open(arquivo, 'w', encoding='utf-8') as f:
    f.write(conteudo)

print("✅ Indentação corrigida!")
