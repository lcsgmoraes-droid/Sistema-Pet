# 🎯 Conciliação de Cartões - Definições e Fluxo

**Data:** 11/02/2026  
**Status:** Em Discussão (Pendências Críticas Identificadas)

---

## ✅ DEFINIÇÕES APROVADAS

### 1️⃣ Ordem de Operação

**Rotina Padrão D+1:**
```
Dia X (Terça 10/02):
└─ Vendas PDV com NSU registrado

Dia X+1 (Quarta 11/02):
└─ Manhã: Baixar e importar tudo junto:
   ├─ VENDAS.xlsx (Stone)
   ├─ RECEBIMENTOS.xlsx (Stone)
   └─ EXTRATO.ofx (Banco)
```

**Razão:** Cada empresa tem sua rotina, sistema define o fluxo ideal.

---

### 2️⃣ Antecipações

**Cenário:** Venda 3x de R$ 300 antecipada

**Sistema:**
```sql
-- PDV cria 3 registros
ContaReceber #1: R$ 100 | Parcela 1/3 | Venc: 12/03
ContaReceber #2: R$ 100 | Parcela 2/3 | Venc: 12/04
ContaReceber #3: R$ 100 | Parcela 3/3 | Venc: 12/05
```

**Importação RECEBIMENTOS Stone:**
```
Stone ID: 123456 | Parcela 1/3 | R$ 95 | Pago 12/03
Stone ID: 123456 | Parcela 2/3 | R$ 95 | Pago 12/03 ✅ Antecipado
Stone ID: 123456 | Parcela 3/3 | R$ 95 | Pago 12/03 ✅ Antecipado
```

**Ação Sistema:**
- ✅ Baixa os 3 ContaReceber juntos
- ✅ Marca com tag "ANTECIPADO" (visual diferenciado)
- ✅ Confere taxa de cada parcela
- ✅ Cria lançamento de taxa no DRE

---

### 3️⃣ Divergências de Taxa

**Exemplo:**
- Taxa Esperada (cadastro): 3,5% a.m.
- Taxa Real (Stone): 4,2% a.m.
- Divergência: +0,7% (R$ 0,70 a mais cobrado)

**Ações:**
1. ✅ **Aceitar taxa real** (prevalece sobre configurada)
2. ✅ **Criar relatório de divergências** (para revisão)
3. ✅ **Sugerir atualização do cadastro:**
   ```
   ┌────────────────────────────────────────────┐
   │ ⚠️ Taxa Divergente Detectada              │
   ├────────────────────────────────────────────┤
   │ Visa Crédito 3x                            │
   │ Configurado: 3,5% a.m.                     │
   │ Real (Stone): 4,2% a.m.                    │
   │                                            │
   │ Atualizar cadastro para 4,2%?             │
   │                                            │
   │ [Sim] [Não]                                │
   │                                            │
   │ Alertar novamente em:                      │
   │ ( ) 7 dias  (*) 15 dias  ( ) 30 dias      │
   └────────────────────────────────────────────┘
   ```
   
**Controle:**
- Se usuário clicar "Não", sistema aguarda X dias para sugerir novamente
- Evita 100 alertas repetidos na mesma importação
- Mantém histórico de divergências para análise

---

### 4️⃣ NSUs Órfãos (Stone sem PDV)

**Cenário:** RECEBIMENTOS.xlsx tem NSU que não existe no sistema

**Ações Possíveis:**

#### **Opção A: Vincular a Venda Existente**
```
Sistema busca vendas sem NSU com:
- Mesmo valor (±R$ 0,50)
- Mesma data (±3 dias)
- Mesma bandeira

Sugestões:
┌─────────────────────────────────────────┐
│ NSU Órfão: 999888 | R$ 50,00 | 10/02  │
├─────────────────────────────────────────┤
│ Possíveis matches:                      │
│ [ ] Venda #0045 | R$ 50,00 | 10/02    │
│ [ ] Venda #0052 | R$ 49,50 | 11/02    │
│                                         │
│ [Vincular] [Criar Nova] [Ignorar]      │
└─────────────────────────────────────────┘
```

**Risco:** Usuário pode vincular errado, mas é decisão dele.

#### **Opção B: Criar Contas a Receber**
```
[x] Criar ContaReceber
[x] Gerar Fluxo de Caixa
[x] Marcar como "Venda Externa"
```

#### **Opção C: Baixar Sem Criar**
```
Motivo: Já existe ContaReceber em aberto
        (venda foi lançada mas esqueceu NSU)

[ ] Criar ContaReceber (NÃO)
[ ] Gerar Fluxo (NÃO)
[x] Apenas registrar recebimento
```

---

### 5️⃣ Validação do OFX

**STATUS:** ❌ **BLOQUEADO** (ver seção Pendências)

---

### 6️⃣ Estrutura de ContaReceber

**DEFINIÇÃO:** Opção A - Parcelado (registros separados)

```sql
-- Venda 3x gera 3 registros
INSERT INTO contas_receber (venda_id, nsu, parcela, valor)
VALUES 
  (123, '999888', '1/3', 33.33),
  (123, '999888', '2/3', 33.33),
  (123, '999888', '3/3', 33.34);
```

**Motivo:** Facilita conciliação parcela por parcela via Stone ID.

---

### 7️⃣ Interface - Visão do Usuário

**Layout Híbrido:**

```
┌──────────────────────────────────────────────────────────┐
│ 📊 DASHBOARD (Clicável - Opção C)                       │
├──────────────────────────────────────────────────────────┤
│ 🟢 Conciliado      │ 🟡 Pend. OFX      │ 🔴 Divergências │
│    156 vendas      │    23 vendas      │    4 vendas     │
│    R$ 15.442       │    R$ 2.340       │    R$ 380       │
│                                                           │
│ ⚪ Órfãos Stone                  │ ⚠️ Taxas Divergentes │
│    2 vendas                      │    18 ocorrências    │
│    R$ 70                         │    +R$ 45 (total)    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ 📅 VISÃO POR DIA (Expansível - Opção B + A)            │
├──────────────────────────────────────────────────────────┤
│ ► 12/03/26  │ 47 vendas │ R$ 5.432 │ Divergência: -R$ 2│
│ ▼ 13/03/26  │ 52 vendas │ R$ 6.120 │ ✅ OK             │
│   ├─ 123456 1/3 │ Venda #45 │ R$ 30 │ ✅ Conciliado    │
│   ├─ 123456 2/3 │ Venda #45 │ R$ 30 │ 🏷️ Antecipado    │
│   ├─ 789012     │ Venda #46 │ R$ 50 │ ⚠️ Taxa +0,5%    │
│   └─ 555444     │ ❌ Órfão   │ R$ 20 │ 🔴 Ação Req.     │
│ ► 14/03/26  │ 38 vendas │ R$ 3.890 │ ⏳ Pendente       │
└──────────────────────────────────────────────────────────┘
```

---

## 🚧 PENDÊNCIAS CRÍTICAS

### ❌ **PROBLEMA 1: Rastreamento OFX × NSU**

**Descrição:**  
Extrato OFX não contém Stone ID nem nenhum identificador que vincule ao NSU da transação.

**Impacto:**
- Impossível conciliação 1:1 (venda ↔ crédito bancário)
- Antecipações variadas quebram qualquer padrão:
  - Cai na hora
  - Cai no primeiro dia da semana (automático)
  - Cai quando empresa solicita (pontual)
- Múltiplas vendas mesmo valor/dia = indistinguível

**Status:** 🔴 **BLOQUEADOR**

---

### ❌ **PROBLEMA 2: Validação Diária (Agregada)**

**Descrição:**  
Tentar bater total Stone × total OFX por dia não funciona devido a:
- Antecipações desalinhadas (venda dia X, crédito dia Y)
- Parcelas pagas em dias diferentes
- Pagamentos agrupados por lote (Stone agrupa vários dias em 1 crédito)

**Status:** 🔴 **BLOQUEADOR**

---

## 🎯 PRÓXIMOS PASSOS

1. **Discutir solução para rastreamento OFX**
2. **Definir alternativa de validação bancária**
3. **Implementar fluxo sem dependência do OFX (apenas Stone)**
4. **Adicionar OFX como validação opcional (manual)**

---

## 📝 NOTAS

- Sistema deve funcionar **sem OFX** (Stone VENDAS + RECEBIMENTOS suficiente)
- OFX serve para **outras despesas/receitas** (não cartão)
- Usuário pode conferir saldo manualmente (reconciliação manual)
