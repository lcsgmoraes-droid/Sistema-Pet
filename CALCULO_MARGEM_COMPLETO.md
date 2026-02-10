# 📊 Cálculo Completo de Margem com TODOS os Custos

## 🎯 Objetivo

Calcular a **margem líquida REAL** de cada venda, considerando **TODOS** os custos operacionais, não apenas impostos e taxas de pagamento.

---

## ✅ Custos Considerados

### 1. **Custo dos Produtos**
```
custo_total = Σ (produto.preco_custo × quantidade)
```
- ✅ Já multiplicado pela quantidade
- ✅ Considera custo de TODOS os itens da venda

### 2. **Taxa de Entrega**
```
taxa_entrega = valor cobrado do cliente (RECEITA)
```
- Cliente paga R$ 10 de entrega → adiciona R$ 10 na receita

### 3. **Custo Operacional da Entrega**
```
custo_operacional_entrega = despesas reais (CUSTO)
```
- Combustível: ~R$ 5 por entrega
- Tempo do entregador: ~R$ 3 (proporcional ao salário)
- **TOTAL**: ~R$ 8 de custo real

**Importante**: Taxa de entrega ≠ Lucro da entrega!
- Cliente paga R$ 10
- Custo real R$ 8
- **Lucro da entrega**: R$ 2

### 4. **Taxa da Forma de Pagamento**
```
taxa_pagamento = total_venda × (taxa_percentual / 100)
```
- Dinheiro: 0%
- PIX: 0%
- Débito: 2%
- Crédito 1x: 2.5%
- Crédito 3x: 4%
- Crédito 12x: 8%

### 5. **Impostos**
```
imposto_valor = total_venda × (aliquota_imposto / 100)
```
- Simples Nacional: 7%
- Lucro Presumido: 11.33%
- Lucro Real: 32%

### 6. **Comissões**
```
comissao = max(
    total_venda × (comissao_percentual / 100),
    comissao_valor
)
```
- Vendedor: geralmente 2-5% sobre a venda
- Entregador: geralmente R$ 3-5 por entrega OU 1-2%
- Usa o **maior valor** entre percentual e fixo

### 7. **Descontos**
```
desconto = valor reduzido do total
```
- Diminui a receita
- Não diminui os custos!

---

## 📐 Fórmula Completa

### **Receita Total**
```
receita_total = (subtotal - desconto) + taxa_entrega
```

### **Custo Total**
```
custo_total = custo_produtos + custo_operacional_entrega
```

### **Lucro Bruto**
```
lucro_bruto = receita_total - custo_total
margem_bruta_% = (lucro_bruto / receita_total) × 100
```

### **Custos Fiscais/Financeiros**
```
custos_fiscais = taxa_pagamento + imposto + comissao
```

### **Lucro Líquido (REAL)**
```
lucro_liquido = lucro_bruto - custos_fiscais
margem_liquida_% = (lucro_liquido / receita_total) × 100
```

---

## 🎨 Exemplo Prático

### Cenário: Venda de Ração com Entrega

**Dados da Venda:**
- 2 sacos de ração: R$ 100 cada = **R$ 200**
- Desconto: **R$ 10**
- Taxa de entrega cobrada: **R$ 15**
- Forma de pagamento: Cartão crédito 3x
- Custo da ração: R$ 60/saco = **R$ 120 total**
- Custo operacional entrega: **R$ 8**
- Comissão vendedor: **2%**

**Cálculo Passo a Passo:**

#### 1. Receita Total
```
Subtotal:           R$ 200,00
Desconto:          -R$  10,00
Valor produtos:     R$ 190,00
Taxa entrega:      +R$  15,00
─────────────────────────────
RECEITA TOTAL:      R$ 205,00
```

#### 2. Custo Total
```
Custo produtos:     R$ 120,00
Custo entrega:     +R$   8,00
─────────────────────────────
CUSTO TOTAL:        R$ 128,00
```

#### 3. Lucro Bruto
```
Receita:            R$ 205,00
Custo:             -R$ 128,00
─────────────────────────────
LUCRO BRUTO:        R$  77,00
Margem Bruta:       37,6%
```

#### 4. Custos Fiscais/Financeiros
```
Taxa cartão 3x (4%): R$   8,20
Imposto SN (7%):     R$  14,35
Comissão (2%):       R$   4,10
─────────────────────────────
CUSTOS FISCAIS:      R$  26,65
```

#### 5. Lucro Líquido REAL
```
Lucro Bruto:        R$  77,00
Custos Fiscais:    -R$  26,65
─────────────────────────────
LUCRO LÍQUIDO:      R$  50,35
Margem Líquida:     24,6%
```

**Status**: 🟡 **ALERTA** - Margem abaixo de 30% (saudável)

### 💡 Análise
- Margem **parece boa** (24,6%)
- MAS: poderia ser **melhor** se:
  - Pagamento à vista ou PIX (economiza R$ 8,20)
  - Sem desconto (aumenta R$ 10)
  - Margem subiria para **33%** → 🟢 Saudável!

---

## 🚨 Cenários Perigosos

### ❌ Venda que Parece Lucrativa mas NÃO É

```
Subtotal:           R$ 100,00
Custo produto:      R$  75,00  ← Custo alto (75%)
Desconto:          -R$   5,00  ← Ainda dá desconto!
Entrega:           +R$  10,00
Custo entrega:     -R$   8,00
Cartão 12x (8%):   -R$   8,40
Imposto (7%):      -R$   7,35
Comissão (3%):     -R$   3,15
─────────────────────────────
LUCRO LÍQUIDO:      R$   3,10  ← Apenas 3%!
```

**Status**: 🔴 **CRÍTICO** - Venda quase sem lucro!

---

## 📱 Usando no PDV

### Endpoint Atualizado
```
POST /pdv/indicadores/analisar-venda
```

### Request Completo
```json
{
  "subtotal": 200.00,
  "custo_total": 120.00,
  "desconto": 10.00,
  "forma_pagamento_id": 4,
  "parcelas": 3,
  "taxa_entrega": 15.00,
  "custo_operacional_entrega": 8.00,
  "comissao_percentual": 2.0,
  "comissao_valor": 0
}
```

### Response Completo
```json
{
  "valores": {
    "subtotal": 200.00,
    "desconto": 10.00,
    "valor_produtos": 190.00,
    "taxa_entrega": 15.00,
    "total_venda": 205.00,
    "valor_liquido": 179.65
  },
  "custos": {
    "custo_produtos": 120.00,
    "custo_operacional_entrega": 8.00,
    "custo_total": 128.00,
    "taxa_pagamento": 8.20,
    "imposto": 14.35,
    "comissao": 4.10,
    "custos_fiscais_totais": 26.65
  },
  "margens": {
    "lucro_bruto": 77.00,
    "lucro_liquido": 50.35,
    "margem_bruta_percentual": 37.56,
    "margem_liquida_percentual": 24.56
  },
  "detalhamento_taxas": {
    "forma_pagamento": "Cartão de Crédito",
    "parcelas": 3,
    "taxa_percentual": 4.0,
    "aliquota_imposto": 7.0,
    "comissao_percentual": 2.0
  },
  "status": {
    "status": "alerta",
    "mensagem": "⚠️ ATENÇÃO: Margem reduzida! Revisar preço.",
    "cor": "warning",
    "icone": "⚠️"
  },
  "referencias": {
    "margem_saudavel_minima": 30.0,
    "margem_alerta_minima": 15.0
  }
}
```

---

## 🎯 Indicadores no PDV

### 🟢 Venda Saudável
- **Margem ≥ 30%**
- Todos os custos cobertos
- Lucro satisfatório
- **Pode aprovar a venda!**

### 🟡 Venda em Alerta
- **Margem entre 15% e 30%**
- Sugestões:
  - Oferecer pagamento à vista (elimina taxa cartão)
  - Reduzir desconto
  - Oferecer produtos com mais margem
- **Aprovar com cautela**

### 🔴 Venda Crítica
- **Margem < 15%**
- Lucro muito baixo ou prejuízo!
- **Ações necessárias:**
  - Revisar preço de venda
  - Remover desconto
  - Exigir pagamento à vista
  - Considerar não fazer a venda

---

## 🛠️ Implementação no Frontend

### Exibir Alerta em Tempo Real
```javascript
// Ao adicionar produto ou mudar forma de pagamento
async function calcularIndicadores() {
  const response = await fetch('/pdv/indicadores/analisar-venda', {
    method: 'POST',
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subtotal: calcularSubtotal(),
      custo_total: calcularCustoTotal(),
      desconto: obterDesconto(),
      forma_pagamento_id: obterFormaPagamentoId(),
      parcelas: obterParcelas(),
      taxa_entrega: obterTaxaEntrega(),
      custo_operacional_entrega: 8.00, // Configurável
      comissao_percentual: 2.0,         // Configurável
      comissao_valor: 0
    })
  });
  
  const resultado = await response.json();
  
  // Exibir alerta colorido
  exibirAlert(resultado.status);
  exibirMargem(resultado.margens.margem_liquida_percentual);
  exibirLucro(resultado.margens.lucro_liquido);
}
```

### Componente de Alerta
```html
<!-- Badge flutuante no PDV -->
<div class="pdv-margem-indicator" 
     :class="resultado.status.cor">
  <span class="icon">{{ resultado.status.icone }}</span>
  <span class="margem">{{ resultado.margens.margem_liquida_percentual }}%</span>
  <span class="lucro">R$ {{ resultado.margens.lucro_liquido }}</span>
</div>

<div v-if="resultado.status.status !== 'saudavel'" 
     class="alert" 
     :class="resultado.status.cor">
  {{ resultado.status.mensagem }}
</div>
```

---

## ✅ Checklist de Implementação

- [x] Atualizar `pdv_indicadores.py` com novos parâmetros
- [x] Atualizar schema `AnaliseVendaRequest`
- [x] Atualizar endpoint `/analisar-venda`
- [x] Criar exemplos de uso
- [x] Documentar fórmulas
- [ ] **Integrar no frontend**:
  - [ ] Capturar custo_operacional_entrega da config
  - [ ] Capturar comissao_percentual da config
  - [ ] Enviar todos os parâmetros na análise
  - [ ] Exibir alerta colorido em tempo real
- [ ] **Configurar:**
  - [ ] Executar migration: `python backend/scripts/migrate_empresa_config_geral.py`
  - [ ] Popular formas pagamento: `python backend/scripts/seed_formas_pagamento.py`
  - [ ] Configurar empresa via `/empresa/config`
  - [ ] Definir custo operacional entrega padrão
  - [ ] Definir % de comissão padrão
- [ ] **Testar:**
  - [ ] Venda simples sem entrega
  - [ ] Venda com entrega
  - [ ] Venda parcelada
  - [ ] Venda com comissão
  - [ ] Venda com todos os custos
  - [ ] Verificar alertas (saudável/alerta/crítico)

---

## 📚 Arquivos Relacionados

- `backend/app/utils/pdv_indicadores.py` - Lógica de cálculo
- `backend/app/pdv_indicadores_routes.py` - Endpoints REST
- `backend/app/empresa_config_geral_models.py` - Configuração de margens
- `backend/scripts/exemplo_calculo_margem_completo.py` - Exemplos práticos
- `PARAMETRIZACAO_E_INDICADORES_PDV.md` - Documentação geral

---

## 🎓 Conceitos Importantes

### Margem Bruta vs Margem Líquida

**Margem Bruta**:
- Receita - Custo direto (produtos + entrega)
- **Não considera** impostos, taxas, comissões
- Útil para avaliar o produto isoladamente

**Margem Líquida**:
- Margem bruta - Todos os custos fiscais/financeiros
- **Considera** TUDO que reduz o lucro
- **É o que realmente importa!**

### Taxa de Entrega vs Lucro da Entrega

**Taxa de Entrega** (R$ 10):
- Valor cobrado do cliente
- **Aumenta a receita**

**Custo Operacional** (R$ 8):
- Combustível, tempo, desgaste
- **Aumenta o custo**

**Lucro da Entrega** (R$ 2):
- Taxa - Custo operacional
- Pode ser **positivo, zero ou negativo!**

### Comissão

**Tipos de comissão**:
1. **Percentual**: 2% do valor da venda
2. **Fixo**: R$ 5 por venda
3. **Híbrido**: Usa o maior dos dois

**Importante**: Comissão é calculada sobre o **total da venda** (com entrega), não apenas produtos.

---

## 🚀 Próximos Passos

1. **Executar migrations** para criar tabelas
2. **Popular formas de pagamento** com taxas corretas
3. **Configurar empresa** com margens desejadas
4. **Integrar frontend** para capturar todos os parâmetros
5. **Treinar equipe** sobre interpretação dos indicadores
6. **Monitorar vendas** e ajustar margens conforme necessário

---

**Versão**: 1.0  
**Data**: {{ data_atual }}  
**Autor**: Sistema Pet - Módulo Financeiro  
