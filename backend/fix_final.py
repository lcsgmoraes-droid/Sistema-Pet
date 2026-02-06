"""
Script final para corrigir APENAS a seção problemática (linhas 1990-2060)
Mantém o resto do arquivo intacto
"""

arquivo = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\app\notas_entrada_routes.py"

# Ler arquivo
with open(arquivo, 'r', encoding='utf-8') as f:
    linhas = f.readlines()

# Código correto para substituir linhas 1990-2060
secao_correta = """            # Buscar lote criado para esta entrada
            nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
            lote = db.query(ProdutoLote).filter(
                ProdutoLote.produto_id == produto.id,
                ProdutoLote.nome_lote == nome_lote,
                ProdutoLote.tenant_id == tenant_id
            ).first()
            
            if lote:
                # REVERTER PREÇO DE CUSTO se foi alterado
                historico_preco = db.query(ProdutoHistoricoPreco).filter(
                    ProdutoHistoricoPreco.produto_id == produto.id,
                    ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                    ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                    ProdutoHistoricoPreco.tenant_id == tenant_id
                ).first()
                
                if historico_preco:
                    # Reverter preços anteriores (com fallback para 0 se None)
                    preco_custo_revertido = historico_preco.preco_custo_anterior if historico_preco.preco_custo_anterior is not None else 0
                    preco_venda_revertido = historico_preco.preco_venda_anterior if historico_preco.preco_venda_anterior is not None else 0
                    
                    try:
                        logger.info(f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo or 0):.2f} → R$ {float(preco_custo_revertido):.2f}")
                    except:
                        logger.info(f"  💰 Revertendo preços do produto {produto.id}")
                    
                    produto.preco_custo = preco_custo_revertido
                    produto.preco_venda = preco_venda_revertido
                    
                    # Excluir histórico
                    db.delete(historico_preco)
                
                # Remover quantidade do estoque
                estoque_anterior = produto.estoque_atual or 0
                produto.estoque_atual = max(0, estoque_anterior - item.quantidade)
                
                # Registrar movimentação de estorno
                movimentacao_estorno = EstoqueMovimentacao(
                    produto_id=produto.id,
                    lote_id=lote.id,
                    tipo="saida",
                    motivo="ajuste",
                    quantidade=item.quantidade,
                    quantidade_anterior=estoque_anterior,
                    quantidade_nova=produto.estoque_atual,
                    custo_unitario=float(item.valor_unitario or 0),
                    valor_total=float(item.valor_total or 0),
                    documento=nota.chave_acesso,
                    referencia_tipo="estorno_nota_entrada",
                    referencia_id=nota.id,
                    observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao}",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(movimentacao_estorno)
                
                # Excluir lote
                db.delete(lote)
"""

# Substituir linhas 1984-2059 (índices 1983-2058)
novas_linhas = linhas[:1983] + [secao_correta + "\n"] + linhas[2059:]

# Salvar
with open(arquivo, 'w', encoding='utf-8') as f:
    f.writelines(novas_linhas)

print("✅ Seção corrigida!")
print("   Linhas 1984-2059 substituídas por código limpo e funcional")
