-- ========================================
-- Criar Produto: Special Dog Carne 15kg
-- Com tabela de consumo para testes
-- ========================================

-- Inserir produto (ajuste o tenant_id conforme necessário)
INSERT INTO produtos (
    nome,
    descricao,
    preco_custo,
    preco_venda,
    margem_lucro,
    quantidade_estoque,
    estoque_minimo,
    codigo_barras,
    categoria,
    fornecedor,
    peso_embalagem,
    unidade_medida,
    ativo,
    classificacao_racao,
    categoria_racao,
    especies_indicadas,
    tabela_consumo,
    tenant_id,
    created_at,
    updated_at
) VALUES (
    'Special Dog Carne 15kg',
    'Ração Special Dog Sabor Carne para Cães Adultos - Embalagem 15kg',
    85.00,  -- Preço de custo
    149.90,  -- Preço de venda
    43.23,  -- Margem de lucro %
    50,  -- Estoque inicial
    5,  -- Estoque mínimo
    '7896181207931',  -- Código de barras real da Special Dog
    'Alimentos',  -- Categoria
    'Special Dog',  -- Fornecedor
    15.0,  -- Peso da embalagem em KG
    'kg',  -- Unidade
    true,  -- Produto ativo
    'standard',  -- Classificação (standard/premium/super_premium)
    'adulto',  -- Categoria de ração (filhote/adulto/senior)
    'dog',  -- Espécie indicada
    '{
  "tipo": "peso_adulto",
  "dados": {
    "5kg": {
      "adulto": 110
    },
    "10kg": {
      "adulto": 185
    },
    "15kg": {
      "adulto": 250
    },
    "20kg": {
      "adulto": 310
    },
    "25kg": {
      "adulto": 365
    },
    "30kg": {
      "adulto": 420
    },
    "35kg": {
      "adulto": 470
    },
    "40kg": {
      "adulto": 520
    },
    "45kg": {
      "adulto": 565
    }
  }
}',  -- Tabela de consumo baseada em dados reais da Special Dog
    1,  -- tenant_id (ajuste conforme seu sistema)
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

-- Verificar se foi criado
SELECT 
    id,
    nome,
    preco_venda,
    peso_embalagem,
    classificacao_racao,
    categoria_racao,
    tabela_consumo
FROM produtos
WHERE nome LIKE '%Special Dog%'
ORDER BY id DESC
LIMIT 1;
