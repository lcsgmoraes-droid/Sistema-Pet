# 🚚 Lógica da Taxa de Entrega - Distribuição Correta

## 🎯 Problema Identificado

**ANTES** (❌ Incorreto):
- Taxa de entrega = Receita da empresa
- Custo operacional = Despesa da empresa
- Lucro entrega = Taxa - Custo operacional

**Problema**: A taxa de entrega **NÃO** fica toda com a empresa!

---

## ✅ Lógica Correta

### 1. Taxa de Entrega Cobrada do Cliente

```
Cliente paga: R$ 15,00 de entrega
```

Esta taxa de **R$ 15** pode ser distribuída de 3 formas:

#### Cenário A: Empresa fica com tudo (100%)
```
├─ Empresa recebe: R$ 15,00 (100%)
└─ Entregador recebe: R$ 0,00 (salário fixo)
```

#### Cenário B: Divisão parcial
```
├─ Empresa recebe: R$ 5,00 (33%)
└─ Entregador recebe: R$ 10,00 (67%) ← Comissão
```

#### Cenário C: Entregador fica com tudo (100%)
```
├─ Empresa recebe: R$ 0,00
└─ Entregador recebe: R$ 15,00 (100%) ← Comissão total
```

### 2. Custo Operacional (SEMPRE da Empresa)

```
Custo operacional: R$ 8,00
├─ Combustível: R$ 5,00
├─ Depreciação veículo: R$ 2,00
└─ Tempo/desgaste: R$ 1,00
```

Este custo é **SEMPRE da empresa**, independente da distribuição da taxa.

---

## 📊 Exemplo Real: Cenário B (Divisão)

### Dados:
- Cliente paga: **R$ 15** de entrega
- Empresa fica com: **R$ 5** (RECEITA)
- Entregador fica com: **R$ 10** (COMISSÃO - DESPESA)
- Custo operacional: **R$ 8** (DESPESA)

### Cálculo Correto:

#### Receita da Empresa:
```
Receita entrega = R$ 5,00  (não R$ 15!)
```

#### Custos da Empresa:
```
Custo operacional:     R$  8,00
Comissão entregador:   R$ 10,00
───────────────────────────────
Total custos entrega:  R$ 18,00
```

#### Resultado da Entrega:
```
Receita:  R$  5,00
Custos:  -R$ 18,00
───────────────────────────────
RESULTADO: -R$ 13,00  ← PREJUÍZO!
```

**Conclusão**: A empresa está **pagando R$ 13** para fazer a entrega!

---

## 🔴 Exemplo Crítico: Cenário C (Entregador 100%)

### Dados:
- Cliente paga: **R$ 15**
- Empresa fica com: **R$ 0**
- Entregador fica com: **R$ 15**
- Custo operacional: **R$ 8**

### Resultado:
```
Receita:  R$  0,00
Custos:  -R$ 23,00  (R$ 8 operacional + R$ 15 comissão)
───────────────────────────────
RESULTADO: -R$ 23,00  ← PREJUÍZO MAIOR!
```

A empresa está **pagando R$ 23** para fazer a entrega!

---

## 🟢 Exemplo Saudável: Cenário A (Empresa 100%)

### Dados:
- Cliente paga: **R$ 15**
- Empresa fica com: **R$ 15**
- Entregador: salário fixo (não recebe comissão)
- Custo operacional: **R$ 8**

### Resultado:
```
Receita:  R$ 15,00
Custos:  -R$  8,00  (apenas operacional)
───────────────────────────────
RESULTADO: +R$  7,00  ← LUCRO!
```

A empresa **lucra R$ 7** com a entrega.

---

## 🛠️ Implementação na API

### Parâmetros Necessários:

```json
{
  "taxa_entrega_cobrada": 15.00,
  "taxa_entrega_receita_empresa": 5.00,
  "custo_operacional_entrega": 8.00
}
```

### Cálculo Automático:

```python
# Receita da empresa com entrega
receita_entrega = taxa_entrega_receita_empresa  # R$ 5

# Comissão do entregador (diferença)
comissao_entregador = taxa_entrega_cobrada - taxa_entrega_receita_empresa  # R$ 10

# Custos totais da empresa relacionados à entrega
custos_entrega = custo_operacional_entrega + comissao_entregador  # R$ 18

# Resultado da entrega
resultado_entrega = receita_entrega - custos_entrega  # -R$ 13
```

---

## 📋 Configurações Possíveis

### 1. Sem Entrega
```json
{
  "taxa_entrega_cobrada": 0,
  "taxa_entrega_receita_empresa": 0,
  "custo_operacional_entrega": 0
}
```
**Resultado**: Sem impacto na margem

### 2. Entrega Lucrativa (Empresa 100%)
```json
{
  "taxa_entrega_cobrada": 15.00,
  "taxa_entrega_receita_empresa": 15.00,  // Empresa fica com tudo
  "custo_operacional_entrega": 8.00
}
```
**Resultado**: +R$ 7 de lucro

### 3. Entrega Equilibrada (50/50)
```json
{
  "taxa_entrega_cobrada": 15.00,
  "taxa_entrega_receita_empresa": 7.50,  // 50% empresa
  "custo_operacional_entrega": 8.00
}
```
**Resultado**: -R$ 8 de prejuízo (empresa paga R$ 0,50)

### 4. Entrega com Comissão Total
```json
{
  "taxa_entrega_cobrada": 15.00,
  "taxa_entrega_receita_empresa": 0,  // Tudo pro entregador
  "custo_operacional_entrega": 8.00
}
```
**Resultado**: -R$ 23 de prejuízo

---

## 🎯 Estratégias Recomendadas

### Opção 1: Empresa Lucra com Entrega
```
Taxa cobrada:     R$ 15,00
Empresa fica:     R$ 12,00 (80%)
Entregador:       R$  3,00 (20%)
Custo operacional: R$  8,00
───────────────────────────────
Resultado:        +R$  4,00 ✅
```

### Opção 2: Entrega Neutra (Zero)
```
Taxa cobrada:     R$ 15,00
Empresa fica:     R$  8,00 (custo)
Entregador:       R$  7,00
Custo operacional: R$  8,00
───────────────────────────────
Resultado:         R$  0,00 ⚖️
```

### Opção 3: Entrega como Serviço (Prejuízo Controlado)
```
Taxa cobrada:     R$ 10,00 (baixa para atrair)
Empresa fica:     R$  5,00
Entregador:       R$  5,00
Custo operacional: R$  8,00
───────────────────────────────
Resultado:        -R$  8,00 ⚠️
(Compensa no volume de vendas)
```

---

## 📱 Como Usar no PDV

### 1. Configurar Política de Entrega

Definir na configuração da empresa:
- **Taxa padrão de entrega**: R$ 15
- **% empresa**: 60% (R$ 9)
- **% entregador**: 40% (R$ 6)
- **Custo operacional médio**: R$ 8

### 2. Na Venda com Entrega

O sistema calcula automaticamente:
```javascript
// Frontend envia:
{
  "taxa_entrega_cobrada": 15.00,
  "taxa_entrega_receita_empresa": 9.00,  // 60%
  "custo_operacional_entrega": 8.00
}

// Backend calcula:
- Receita empresa: R$ 9
- Comissão entregador: R$ 6 (15 - 9)
- Custo operacional: R$ 8
- Resultado entrega: +R$ 1 (lucro pequeno)
```

### 3. Alerta no PDV

Se resultado da entrega for negativo:
```
⚠️ ATENÇÃO: Entrega está dando prejuízo!
- Cliente paga: R$ 15
- Custos totais: R$ 18
- Prejuízo: R$ 3

Sugestões:
✓ Aumentar taxa de entrega
✓ Aumentar % empresa (reduzir comissão)
✓ Avaliar custo operacional
```

---

## ✅ Checklist de Validação

- [ ] Taxa cobrada ≥ 0
- [ ] Receita empresa ≥ 0
- [ ] Receita empresa ≤ Taxa cobrada
- [ ] Custo operacional ≥ 0
- [ ] Comissão entregador = Taxa cobrada - Receita empresa
- [ ] Resultado entrega = Receita empresa - (Custo operacional + Comissão)

---

## 📚 Arquivos Relacionados

- `backend/app/utils/pdv_indicadores.py` - Lógica de cálculo
- `backend/app/pdv_indicadores_routes.py` - Endpoints REST
- `backend/scripts/exemplo_calculo_margem_completo.py` - Exemplos práticos
- `CALCULO_MARGEM_COMPLETO.md` - Documentação geral

---

## 🎓 Conceitos Importantes

### Taxa de Entrega ≠ Receita da Entrega

**Taxa de Entrega** (R$ 15):
- Valor cobrado do cliente
- **Total recebido** pela venda

**Receita da Entrega** (R$ 5):
- Valor que **REALMENTE** fica com a empresa
- **Receita líquida** após distribuição

**Comissão do Entregador** (R$ 10):
- Diferença entre taxa e receita empresa
- É uma **DESPESA** da empresa
- Não é "lucro do entregador" para a empresa!

### Custo Operacional é SEMPRE Despesa

O custo operacional (combustível, depreciação) é **SEMPRE** da empresa, mesmo que:
- Entregador receba 100% da taxa
- Entrega seja "grátis" para o cliente
- Empresa use veículo próprio ou do entregador

**É impossível eliminar esse custo!**

---

**Versão**: 2.0  
**Data**: Fevereiro 2026  
**Autor**: Sistema Pet - Módulo Financeiro  
