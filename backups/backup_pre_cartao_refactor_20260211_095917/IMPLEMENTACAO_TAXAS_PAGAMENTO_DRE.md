# Implementação: Taxas de Pagamento na DRE

**Data:** 09/02/2026  
**Status:** ✅ Implementado e Testado  
**Objetivo:** Lançar automaticamente as taxas de cartão, PIX e outras formas de pagamento na DRE quando vendas são finalizadas.

---

## 📋 Visão Geral

Quando uma venda é finalizada no PDV com formas de pagamento que possuem taxas (cartão de crédito, débito, PIX, etc.), o sistema agora cria **automaticamente contas a pagar** correspondentes às taxas, classificadas nas subcategorias DRE apropriadas.

**Nota importante:** PDV e Loja Física são a mesma coisa. As subcategorias usam "Loja Física" no nome.

### ✅ O que foi implementado:

1. **3 novas subcategorias DRE** (Custos Diretos de Venda):
   - Taxas de Cartão de Crédito - Loja Física
   - Taxas de Cartão de Débito - Loja Física
   - Taxa de PIX - Loja Física

2. **Função automática** `processar_contas_pagar_taxas()`:
   - Executada após finalização de venda
   - Calcula taxas baseado em configuração da forma de pagamento
   - Cria contas a pagar automaticamente
   - Vincula à subcategoria DRE correta

3. **Suporte a taxas por parcelas**:
   - Taxa diferente para cada número de parcelas
   - Configurado no campo `taxas_por_parcela` da forma de pagamento

---

## 🎯 Como Funciona

### Fluxo de Processamento:

```
1. Venda finalizada no PDV/Loja Física
   ↓
2. Sistema processa pagamentos
   ↓
3. Para cada forma de pagamento com taxa:
   ├── Busca configuração (taxa_percentual, taxa_fixa)
   ├── Calcula valor da taxa
   ├── Identifica subcategoria DRE (Loja Física)
   └── Cria conta a pagar
   ↓
4. Contas a pagar criadas e vinculadas à DRE
```

### Cálculo de Taxa:

```python
valor_taxa = (valor_pagamento × taxa_percentual / 100) + taxa_fixa
```

**Exemplos práticos:**
- Cartão Crédito (3.79%): R$ 100,00 → **Taxa: R$ 3,79**
- Cartão Débito (2.00%): R$ 50,00 → **Taxa: R$ 1,00**
- PIX com taxa fixa (R$ 0,50): R$ 75,00 → **Taxa: R$ 0,50**

---

## 🔧 Configuração

### 1. Formas de Pagamento Atuais

Verificar configuração:
```sql
SELECT nome, tipo, taxa_percentual, taxa_fixa, ativo 
FROM formas_pagamento 
WHERE ativo = TRUE 
ORDER BY nome;
```

**Configuração atual no sistema:**
| Forma de Pagamento | Taxa % | Taxa Fixa | Gera Conta a Pagar? |
|-------------------|--------|-----------|---------------------|
| Cartão Crédito | 3.79% | R$ 0,00 | ✅ Sim |
| Crédito à Vista | 3.00% | R$ 0,00 | ✅ Sim |
| Débito | 2.00% | R$ 0,00 | ✅ Sim |
| PIX | 0.00% | R$ 0,00 | ❌ Não (sem taxa) |
| Dinheiro | 0.00% | R$ 0,00 | ❌ Não (ignorado) |

### 2. Alterar Taxas

**Exemplo: Definir taxa de PIX de R$ 0,50:**
```sql
UPDATE formas_pagamento 
SET taxa_fixa = 0.50,
    taxa_percentual = 0.00
WHERE nome = 'PIX';
```

**Exemplo: Alterar taxa de cartão crédito para 4.5%:**
```sql
UPDATE formas_pagamento 
SET taxa_percentual = 4.50,
    taxa_fixa = 0.00
WHERE nome = 'Cartão Crédito';
```

### 3. Taxas por Parcela (Opcional)

Para configurar taxas diferentes por número de parcelas:

```sql
UPDATE formas_pagamento 
SET taxas_por_parcela = '{
  "1": {"taxa_percentual": 3.79, "taxa_fixa": 0},
  "2": {"taxa_percentual": 4.50, "taxa_fixa": 0},
  "3": {"taxa_percentual": 5.00, "taxa_fixa": 0},
  "6": {"taxa_percentual": 5.50, "taxa_fixa": 0},
  "12": {"taxa_percentual": 6.00, "taxa_fixa": 0}
}'::TEXT 
WHERE nome = 'Cartão Crédito';
```

---

## 📊 Subcategorias DRE

Todas as taxas das vendas PDV/Loja Física são lançadas em:

| Subcategoria | ID | Categoria Pai | Quando usar |
|--------------|-----|---------------|-------------|
| Taxas de Cartão de Crédito - Loja Física | 76 | Custos Diretos de Venda | Vendas com cartão crédito |
| Taxas de Cartão de Débito - Loja Física | 77 | Custos Diretos de Venda | Vendas com cartão débito |
| Taxa de PIX - Loja Física | 78 | Custos Diretos de Venda | Vendas com PIX (se houver taxa) |

### Verificar Subcategorias:

```sql
SELECT id, nome, categoria_id 
FROM dre_subcategorias 
WHERE nome LIKE '%Taxa%' 
  AND nome LIKE '%Loja Física%'
ORDER BY nome;
```

---

## 🧪 Como Testar

### Teste Rápido: Venda com Cartão de Crédito

1. **No PDV, fazer uma venda:**
   - Adicionar produto de R$ 100,00
   - Finalizar venda
   - Escolher "Cartão Crédito" como forma de pagamento
   - Confirmar

2. **Verificar conta a pagar criada:**
```sql
SELECT 
    cp.id,
    cp.descricao,
    cp.valor_original,
    cp.status,
    ds.nome AS subcategoria_dre
FROM contas_pagar cp
LEFT JOIN dre_subcategorias ds ON cp.dre_subcategoria_id = ds.id
WHERE cp.descricao LIKE '%Taxa%Cartão Crédito%'
ORDER BY cp.created_at DESC
LIMIT 1;
```

3. **Resultado esperado:**
```
id  | descricao                            | valor_original | status   | subcategoria_dre
----+--------------------------------------+----------------+----------+------------------------------------------
123 | Taxa Cartão Crédito - Venda #001234  | 3.79           | pendente | Taxas de Cartão de Crédito - Loja Física
```

### Verificar nos Logs

```powershell
docker logs petshop-dev-backend --tail 100 | Select-String "Taxa"
```

**Logs esperados:**
```
✅ Subcategoria DRE encontrada: Taxas de Cartão de Crédito - Loja Física (ID: 76)
✅ Conta a pagar criada: Taxa Cartão Crédito R$ 3.79
💳 Contas a pagar de taxas criadas: 1 conta(s), R$ 3.79
```

---

## ⚠️ Formas SEM Taxa

As seguintes formas **não geram** contas a pagar:

- ❌ **Dinheiro** (ignorado propositalmente - não tem taxa)
- ❌ **Crédito do Cliente** (não é pagamento externo)
- ❌ **PIX** (atualmente sem taxa no sistema - configure se necessário)

---

## 🔍 Troubleshooting

### ❓ Taxa não foi criada

**Checklist:**

1. ✅ A forma de pagamento tem taxa > 0?
```sql
SELECT nome, taxa_percentual, taxa_fixa 
FROM formas_pagamento 
WHERE nome = 'NOME_DA_FORMA';
```

2. ✅ A subcategoria DRE existe?
```sql
SELECT COUNT(*) FROM dre_subcategorias 
WHERE nome LIKE '%Taxa%' AND nome LIKE '%Loja Física%';
-- Deve retornar 3
```

3. ✅ Verificar logs de erro:
```powershell
docker logs petshop-dev-backend --tail 200 | Select-String -Pattern "Erro.*taxa|taxa.*não encontrada" -CaseSensitive:$false
```

### ❓ Subcategorias não existem

**Solução: Recriar subcategorias**
```powershell
Get-Content "c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\alembic\versions\criar_subcategorias_taxas_pdv.sql" | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev
```

### ❓ Valor da taxa está errado

**Verificar configuração:**
```sql
SELECT 
    nome,
    taxa_percentual,
    taxa_fixa,
    taxas_por_parcela
FROM formas_pagamento
WHERE nome = 'NOME_DA_FORMA';
```

Se usar parcelamento, `taxas_por_parcela` deve ser JSON válido.

---

## 📈 Impacto na DRE

### Antes:
```
Receita Bruta:              R$ 1.000,00
(-) CMV:                    R$ 600,00
(-) Descontos:              R$ 50,00
----------------------------------
= Margem de Contribuição:   R$ 350,00   ← Margem inflada
```

### Depois (correto):
```
Receita Bruta:              R$ 1.000,00
(-) CMV:                    R$ 600,00
(-) Descontos:              R$ 50,00
(-) Taxas de Cartão:        R$ 37,90   ← Novo custo
----------------------------------
= Margem de Contribuição:   R$ 312,10   ← Margem real
```

**Benefício:** DRE agora reflete o **custo real** das vendas!

---

## 🎓 Detalhes Técnicos

### Arquivos Modificados:

| Arquivo | Mudança |
|---------|---------|
| `backend/app/vendas/service.py` | + Função `processar_contas_pagar_taxas()` |
| `backend/app/vendas/service.py` | Chamada na função `finalizar_venda()` |
| `backend/alembic/versions/criar_subcategorias_taxas_pdv.sql` | Script de criação de subcategorias |

### Estrutura da Conta a Pagar:

```python
ContaPagar(
    descricao="Taxa [forma] - Venda #XXX",
    valor_original=valor_calculado,
    data_emissao=hoje,
    data_vencimento=hoje + prazo_dias,
    status='pendente',
    canal='loja_fisica',
    dre_subcategoria_id=76,  # ID da subcategoria
    observacoes="Detalhes do cálculo..."
)
```

### Mapeamento Canal → Subcategoria:

```python
# Código simplificado
MAPA_CANAIS = {
    'loja_fisica': 'Loja Física',
    'pdv': 'Loja Física',           # PDV = Loja Física
    'mercado_livre': 'Mercado Livre',
    'shopee': 'Shopee',
    'amazon': 'Amazon'
}
```

---

## 🚀 Próximas Melhorias

- [ ] Dashboard de análise de taxas por período
- [ ] Comparativo de custo entre formas de pagamento
- [ ] Alertas de taxas acima da média
- [ ] Sugestão de forma de pagamento mais econômica
- [ ] Integração com APIs das operadoras (taxas reais)

---

## ✅ Checklist de Validação

- [x] Subcategorias DRE criadas
- [x] Função `processar_contas_pagar_taxas()` implementada
- [x] Integração com `finalizar_venda()` concluída
- [x] Teste com Cartão Crédito realizado
- [x] Teste com Cartão Débito realizado
- [x] Logs de sucesso confirmados
- [x] Documentação completa
- [x] Correção: PDV = Loja Física (mesma subcategoria)

---

**Última atualização:** 09/02/2026 21:30  
**Responsável:** Sistema Pet - Implementação DRE
