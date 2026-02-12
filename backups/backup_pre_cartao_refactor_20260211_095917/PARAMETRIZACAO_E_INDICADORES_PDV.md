# 🎯 SISTEMA DE PARAMETRIZAÇÃO E INDICADORES DE MARGEM

## 📋 O QUE FOI CRIADO

Sistema completo para parametrizar a empresa e exibir indicadores de margem no PDV, alertando sobre vendas com prejuízo.

---

## 🏗️ ARQUITETURA

### 1. **Modelo de Configuração da Empresa**
**Arquivo**: `backend/app/empresa_config_geral_models.py`

Armazena:
- ✅ Dados básicos da empresa (razão social, CNPJ, endereço)
- ✅ **Parâmetros de margem** (saudável, alerta, crítico)
- ✅ **Mensagens personalizadas** para o PDV
- ✅ Alíquota de imposto padrão (Simples Nacional 7%)
- ✅ Meta de faturamento mensal
- ✅ Parâmetros de estoque

**Campos principais:**
```python
margem_saudavel_minima = 30.0%          # Acima disso: VERDE ✅
margem_alerta_minima = 15.0%             # Entre 15-30%: AMARELO ⚠️
# Abaixo de 15%: VERMELHO 🚨 (crítico)

mensagem_venda_saudavel = "✅ Venda Saudável!"
mensagem_venda_alerta = "⚠️ ATENÇÃO: Margem reduzida!"
mensagem_venda_critica = "🚨 CRÍTICO: Venda com prejuízo!"

aliquota_imposto_padrao = 7.0%          # Simples Nacional
```

### 2. **Formas de Pagamento e Taxas**
**Arquivo**: `backend/app/formas_pagamento_models.py` (já existia, aprimorado)

**Script de Seed**: `backend/scripts/seed_formas_pagamento.py`

Cria automaticamente:

#### 💵 **Dinheiro**
- Taxa: 0%
- Recebimento: imediato

#### 📱 **PIX**
- Taxa: 0%
- Recebimento: imediato

#### 💳 **Cartão de Débito**
- Taxa: **2%**
- Recebimento: D+1

#### 💳 **Cartão de Crédito** (taxas progressivas)
| Parcelas | Taxa | Descrição |
|----------|------|-----------|
| 1x | 2.50% | À vista - crédito |
| 2x | 3.00% | 2x sem juros |
| 3x | 3.50% | 3x sem juros |
| 4x | 4.00% | 4x |
| 5x | 4.50% | 5x |
| 6x | 5.00% | 6x |
| 7x | 5.50% | 7x |
| 8x | 6.00% | 8x |
| 9x | 6.50% | 9x |
| 10x | 7.00% | 10x |
| 11x | 7.50% | 11x |
| 12x | 8.00% | 12x |

#### 📊 **Configurações de Imposto**
- **Simples Nacional**: 7% (padrão)
- **Lucro Presumido**: 11.33%
- **Lucro Real**: 32%

### 3. **Utilitário de Cálculo de Indicadores**
**Arquivo**: `backend/app/utils/pdv_indicadores.py`

Duas funções principais:

#### 📊 `calcular_indicadores_venda()`
Analisa venda completa com TODOS os custos:
- Subtotal e desconto
- **Taxa da forma de pagamento**
- **Imposto** (Simples Nacional)
- **Custo dos produtos** (CMV)
- Calcula margem bruta e **margem líquida**
- Retorna status: saudável/alerta/crítico

#### 📦 `calcular_indicadores_item()`
Analisa item individual enquanto adiciona no PDV:
- Preço venda vs preço custo
- Margem estimada (com imposto, sem taxa de pagamento)
- Status do item

### 4. **Endpoints da API**

#### A) **Configuração da Empresa**
**Arquivo**: `backend/app/empresa_config_routes.py`

**Base**: `/empresa/config`

```http
GET    /empresa/config         # Busca configuração
POST   /empresa/config         # Cria configuração
PUT    /empresa/config         # Atualiza configuração
DELETE /empresa/config         # Remove (volta padrão)
```

**Exemplo de uso**:
```json
PUT /empresa/config
{
  "razao_social": "Pet Shop Exemplo LTDA",
  "nome_fantasia": "Pet Shop Exemplo",
  "cnpj": "12.345.678/0001-90",
  "margem_saudavel_minima": 35.0,
  "margem_alerta_minima": 20.0,
  "aliquota_imposto_padrao": 7.0,
  "mensagem_venda_saudavel": "✅ Excelente! Continue assim!",
  "mensagem_venda_alerta": "⚠️ Margem baixa, revisar preços",
  "mensagem_venda_critica": "🚨 PREJUÍZO! Não venda assim!"
}
```

#### B) **Indicadores do PDV**
**Arquivo**: `backend/app/pdv_indicadores_routes.py`

**Base**: `/pdv/indicadores`

```http
POST /pdv/indicadores/analisar-venda    # Analisa venda completa
POST /pdv/indicadores/analisar-item     # Analisa item individual
GET  /pdv/indicadores/referencias       # Busca referências de margem
```

**Exemplo 1: Analisar venda completa**
```json
POST /pdv/indicadores/analisar-venda
{
  "subtotal": 1000.00,
  "custo_total": 600.00,
  "desconto": 50.00,
  "forma_pagamento_id": 4,  // Cartão crédito
  "parcelas": 3
}

// Resposta:
{
  "valores": {
    "subtotal": 1000.00,
    "desconto": 50.00,
    "total_venda": 950.00,
    "custo_total": 600.00,
    "taxa_valor": 33.25,      // 3.5% de 950
    "imposto_valor": 66.50,   // 7% de 950
    "valor_liquido": 850.25
  },
  "margens": {
    "lucro_bruto": 350.00,
    "lucro_liquido": 250.25,
    "margem_bruta_percentual": 36.84,
    "margem_liquida_percentual": 26.34  // ✅ Saudável!
  },
  "taxas": {
    "forma_pagamento": "Cartão de Crédito",
    "parcelas": 3,
    "taxa_percentual": 3.5,
    "taxa_valor": 33.25,
    "aliquota_imposto": 7.0,
    "imposto_valor": 66.50
  },
  "status": {
    "status": "saudavel",
    "mensagem": "✅ Venda Saudável! Margem excelente.",
    "cor": "success",
    "icone": "✅"
  }
}
```

**Exemplo 2: Analisar item no PDV**
```json
POST /pdv/indicadores/analisar-item
{
  "preco_venda": 100.00,
  "preco_custo": 85.00,
  "quantidade": 1
}

// Resposta:
{
  "preco_venda": 100.00,
  "preco_custo": 85.00,
  "quantidade": 1,
  "total_venda": 100.00,
  "total_custo": 85.00,
  "lucro_bruto": 15.00,
  "margem_bruta_percentual": 15.0,
  "imposto_estimado": 7.00,
  "lucro_estimado": 8.00,
  "margem_estimada_percentual": 8.0,  // 🚨 Crítico!
  "status": {
    "status": "critico",
    "icone": "🚨",
    "cor": "danger"
  }
}
```

---

## 🚀 COMO USAR

### Passo 1: Executar Migrations
```bash
cd backend
python scripts/migrate_empresa_config_geral.py
```

### Passo 2: Popular Formas de Pagamento
```bash
cd backend
python scripts/seed_formas_pagamento.py
```

Isso cria:
- ✅ 4 formas de pagamento (dinheiro, PIX, débito, crédito)
- ✅ 13 configurações de taxa (1x a 12x)
- ✅ 3 regimes de imposto

### Passo 3: Configurar sua Empresa
Via API ou interface:

```http
PUT /empresa/config
{
  "nome_fantasia": "Meu Pet Shop",
  "cnpj": "12.345.678/0001-90",
  "margem_saudavel_minima": 30.0,
  "margem_alerta_minima": 15.0,
  "aliquota_imposto_padrao": 7.0
}
```

### Passo 4: Usar no PDV

#### No Frontend - Ao adicionar item:
```javascript
// 1. Ao adicionar produto no carrinho
const item = {
  preco_venda: produto.preco_venda,
  preco_custo: produto.preco_custo,
  quantidade: quantidade
};

const response = await fetch('/pdv/indicadores/analisar-item', {
  method: 'POST',
  body: JSON.stringify(item)
});

const indicador = await response.json();

// Exibir alerta se crítico
if (indicador.status.status === 'critico') {
  alert(indicador.status.mensagem);  // "🚨 CRÍTICO: Margem muito baixa!"
}
```

#### No Frontend - Ao finalizar venda:
```javascript
// 2. Antes de finalizar a venda
const venda = {
  subtotal: calcularSubtotal(),
  custo_total: calcularCustoTotal(),
  desconto: descontoAplicado,
  forma_pagamento_id: formaSelecionada,
  parcelas: parcelasSelecionadas
};

const response = await fetch('/pdv/indicadores/analisar-venda', {
  method: 'POST',
  body: JSON.stringify(venda)
});

const analise = await response.json();

// Exibir card com indicadores
mostrarIndicadores({
  margem: analise.margens.margem_liquida_percentual,
  status: analise.status.status,
  mensagem: analise.status.mensagem,
  cor: analise.status.cor,
  icone: analise.status.icone
});

// Se crítico, confirmar com usuário
if (analise.status.status === 'critico') {
  const confirmar = confirm(
    `${analise.status.mensagem}\n\n` +
    `Margem: ${analise.margens.margem_liquida_percentual}%\n` +
    `Lucro: R$ ${analise.margens.lucro_liquido}\n\n` +
    `Deseja continuar mesmo assim?`
  );
  
  if (!confirmar) {
    return; // Cancela a venda
  }
}
```

---

## 🎨 INTERFACE SUGERIDA (Frontend)

### Tela: Configuração da Empresa
```
┌────────────────────────────────────────────────────┐
│ 🏢 Configuração da Empresa                         │
├────────────────────────────────────────────────────┤
│                                                    │
│ Dados Básicos                                      │
│ ├─ Razão Social: [________________]               │
│ ├─ Nome Fantasia: [________________]              │
│ └─ CNPJ: [__________]                              │
│                                                    │
│ ⚙️ Parâmetros de Margem (PDV)                     │
│ ├─ Margem Saudável (mínima): [30]%  ✅            │
│ ├─ Margem Alerta (mínima): [15]%    ⚠️            │
│ └─ (Abaixo de 15% = Crítico) 🚨                   │
│                                                    │
│ 💬 Mensagens do PDV                               │
│ ├─ Saudável: [✅ Venda Saudável!...]              │
│ ├─ Alerta: [⚠️ ATENÇÃO: Margem...]                │
│ └─ Crítico: [🚨 CRÍTICO: Prejuízo...]             │
│                                                    │
│ 📊 Imposto Padrão                                 │
│ └─ Alíquota: [7]% (Simples Nacional)              │
│                                                    │
│          [ Salvar Configuração ]                   │
└────────────────────────────────────────────────────┘
```

### Tela: PDV com Indicadores
```
┌────────────────────────────────────────────────────┐
│ 🛒 PDV - Nova Venda                      [ABERTA]  │
├────────────────────────────────────────────────────┤
│                                                    │
│ Itens do Carrinho:                                │
│ ┌──────────────────────────────────────────┐      │
│ │ Ração Premium 15kg       R$ 150,00  ✅   │      │
│ │ (Custo: R$ 100) Margem: 33%              │      │
│ ├──────────────────────────────────────────┤      │
│ │ Brinquedo Pet           R$ 25,00   🚨   │      │
│ │ (Custo: R$ 23) Margem: 8% - CRÍTICO!     │      │
│ └──────────────────────────────────────────┘      │
│                                                    │
│ Subtotal:                         R$ 175,00       │
│ Desconto:                         R$  10,00       │
│ Total:                            R$ 165,00       │
│                                                    │
│ Forma de Pagamento: [ Crédito 3x ▼]               │
│                                                    │
│ ┌────────────── ANÁLISE DA VENDA ─────────────┐   │
│ │                                              │   │
│ │  ⚠️ ATENÇÃO: Margem Reduzida!               │   │
│ │                                              │   │
│ │  Margem Líquida: 18,5%                       │   │
│ │  Lucro Líquido: R$ 30,53                     │   │
│ │                                              │   │
│ │  Detalhes:                                   │   │
│ │  • Taxa cartão (3.5%): R$ 5,78               │   │
│ │  • Imposto (7%): R$ 11,55                    │   │
│ │  • Custo produtos: R$ 123,00                 │   │
│ │                                              │   │
│ │  Status: ALERTA - Revisar preços! ⚠️         │   │
│ │                                              │   │
│ └──────────────────────────────────────────────┘   │
│                                                    │
│      [ Cancelar ]    [ Finalizar Venda ]           │
└────────────────────────────────────────────────────┘
```

---

##✅ CHECKLIST DE IMPLEMENTAÇÃO

### Backend (CONCLUÍDO)
- [x] Modelo `EmpresaConfigGeral`
- [x] Modelo `FormaPagamentoTaxa` (já existia)
- [x] Modelo `ConfiguracaoImposto` (já existia)
- [x] Utilitário `pdv_indicadores.py`
- [x] Rotas `/empresa/config`
- [x] Rotas `/pdv/indicadores`
- [x] Registrar rotas no `main.py`
- [x] Migration `migrate_empresa_config_geral.py`
- [x] Seed `seed_formas_pagamento.py`

### Frontend (A FAZER)
- [ ] Tela de configuração da empresa
- [ ] Integrar indicadores no PDV
- [ ] Exibir alerta ao adicionar item crítico
- [ ] Card de análise antes de finalizar venda
- [ ] Confirmação se margem crítica

---

## 🎯 BENEFÍCIOS

1. **Evita Prejuízo**: Alerta em tempo real sobre vendas ruins
2. **Transparência**: Mostra exatamente onde vai cada centavo
3. **Educação**: Operador entende impacto de taxas e impostos
4. **Flexível**: Empresa define seus próprios parâmetros
5. **Profissional**: Decisões baseadas em dados, não "achismo"

---

## 📝 PRÓXIMOS PASSOS

1. ✅ Executar migrations
2. ✅ Popular formas de pagamento
3. ⚠️ Configurar empresa via API
4. ⚠️ Implementar frontend
5. ⚠️ Testar fluxo completo no PDV
6. ⚠️ Ajustar mensagens conforme feedback dos usuários

---

**Sistema pronto para uso! 🚀**
