# 🏦 Sistema de Conciliação Bancária - Guia Completo

## 📋 Visão Geral

Sistema inteligente de conciliação bancária com **aprendizado automático** que classifica movimentações bancárias baseado em padrões históricos.

### ✨ Principais Funcionalidades

- ✅ **Upload de arquivos OFX** (Banco do Brasil, Santander, Itaú, Bradesco, Stone)
- 🤖 **Classificação automática** com motor de aprendizado
- 📊 **Dashboard em tempo real** com estatísticas
- 🎯 **Sistema de regras inteligentes** (confidence scoring)
- 🔄 **Detecção de recorrências** para provisões futuras
- 🏷️ **Templates para adquirentes** (Stone, Cielo, Rede, PagSeguro, Mercado Pago)

---

## 🚀 Como Usar

### 1️⃣ **Primeira Vez - Preparação**

```bash
# 1. Executar seed de templates (já vem pronto!)
docker exec petshop-dev-backend bash -c "cd /app && python scripts/seed_templates_adquirentes.py"
```

Isso cria templates para:
- 🏦 **Bancos**: BB, Santander, Itaú, Bradesco (OFX)
- 💳 **Adquirentes**: Stone, Cielo, Rede, PagSeguro, Mercado Pago (CSV)

### 2️⃣ **Acessar Sistema**

1. Entre no sistema PetShop ERP
2. Menu lateral: **Financeiro/Contábil** → **Conciliação Bancária (OFX)**
3. Selecione uma **Conta Bancária** no filtro superior

### 3️⃣ **Upload de Extrato OFX**

1. Clique em **"Upload OFX"**
2. Selecione seu arquivo `.ofx` (baixado do internet banking)
3. Sistema vai:
   - ✅ Parsear todas as transações
   - 🤖 Aplicar regras automáticas existentes
   - 📊 Mostrar estatísticas (Total, Conciliadas, Pendentes)

### 4️⃣ **Classificação de Movimentações**

#### **Automático** (Confiança ≥ 80%)
- Sistema já classificou sozinho! ✅
- Aparece como **"Conciliado"** em verde

#### **Sugerido** (Confiança 50-80%)
- Sistema sugere classificação com % de confiança
- Badge amarelo: **"Sugerido (75%)"**
- Clique em **"Classificar"** para confirmar ou corrigir

#### **Pendente** (Confiança < 50%)
- Badge vermelho: **"Pendente"**
- Clique em **"Classificar"** e escolha:
  - 🏢 **Pagamento a Fornecedor**
  - 💰 **Taxa Bancária**
  - ↔️ **Transferência Entre Contas**
  - 💵 **Recebimento de Cliente**

#### **Opções ao Classificar:**
- ✅ **Criar regra automática** - Sistema aprende e classifica automaticamente no futuro
- 🔄 **Movimentação recorrente** - Cria provisões para próximos meses
  - Periodicidade: Mensal, Trimestral, Semestral, Anual

---

## 🧠 Como Funciona o Motor de Aprendizado

### **Sistema de Confiança (Confidence Scoring)**

```python
confianca = (vezes_confirmada / vezes_aplicada) * 100
```

#### Exemplo Real:
```
Movimentação: "MANFRIM INDUSTRIAL - Pagamento"
Valor: R$ 1.500,00

1ª vez: Sistema não reconhece → Você classifica manualmente
2ª vez: Sistema sugere (50% confiança) → Você confirma
3ª vez: Sistema AUTO-CLASSIFICA (100% confiança) ✅
```

### **Regras Criadas Automaticamente:**

Quando você classifica uma movimentação marcando **"Criar regra automática"**, o sistema:

1. Extrai **palavra-chave** do MEMO (ex: "MANFRIM")
2. Cria **padrão SQL LIKE** (`%MANFRIM%`)
3. Vincula ao **fornecedor/tipo** que você escolheu
4. **Próximas movimentações** com "MANFRIM" serão auto-classificadas!

---

## 📊 Dashboard de Estatísticas

### **Cards Principais:**
- 📝 **Total** - Todas as movimentações importadas
- ✅ **Conciliadas** - Já classificadas (verde)
- ⚠️ **Sugeridas** - Sistema sugeriu, aguardando confirmação (amarelo)
- ⏳ **Pendentes** - Precisam de classificação manual (vermelho)
- 📈 **Taxa de Automação** - % de movimentações auto-classificadas

### **Filtros Disponíveis:**
- 🏦 Conta Bancária
- 📅 Período (Data Início/Fim)
- 🎯 Status (Todos, Pendente, Sugerido, Conciliado)
- 👁️ Ocultar Conciliadas (padrão: SIM)

---

## 🔧 Gerenciamento de Regras

### **Visualizar Regras Criadas:**
1. Clique em **"Regras (X)"** no canto superior direito
2. Veja todas as regras ativas com:
   - 🎯 Padrão de reconhecimento (ex: `%ENERGIA%`)
   - 📊 Barra de confiança (0-100%)
   - 📈 Vezes aplicada / confirmada
   - 🏢 Fornecedor vinculado

### **Desativar Regra:**
- Se uma regra está classificando errado
- Clique em **"Desativar"** na regra específica
- Ela para de ser aplicada automaticamente

---

## 🎯 Casos de Uso Práticos

### **Caso 1: Conta de Luz Mensal**
```
1. Upload OFX com: "CPFL ENERGIA - Pagamento Fatura"
2. Classifica manualmente:
   - Tipo: Pagamento a Fornecedor
   - ✅ Criar regra automática
   - ✅ Movimentação recorrente (Mensal)
3. Resultado:
   - Sistema cria regra para %CPFL%
   - Próximo mês: AUTO-CLASSIFICA ✅
   - Cria provisões para próximos 12 meses
```

### **Caso 2: Recebimentos Stone**
```
1. Upload OFX da Stone com várias vendas
2. Descrição: "Recebimento vendas - Antecipação"
3. Classifica primeira vez:
   - Tipo: Recebimento de Cliente
   - ✅ Criar regra %Recebimento vendas%
4. Resultado:
   - Todas as próximas são auto-classificadas
   - Taxa de automação sobe para 80%+
```

### **Caso 3: Taxas Bancárias Variadas**
```
1. Aparece: "TAR PACOTE SERV PJ"
2. Classificar como: Taxa Bancária
3. Sistema aprende padrão %TAR%
4. Próximas taxas: auto-classificadas
```

---

## 🔍 Estrutura de Dados

### **Tabelas Criadas:**

```sql
-- Extratos importados
extratos_bancarios (
  id, tenant_id, conta_bancaria_id,
  arquivo_nome, periodo_inicio/fim,
  total_movimentacoes, conciliadas, pendentes
)

-- Cada linha do extrato
movimentacoes_bancarias (
  id, extrato_id, conta_bancaria_id,
  fitid, data_movimento, valor, tipo, memo,
  status_conciliacao, confianca_sugestao,
  fornecedor_id, conta_pagar_id, etc
)

-- Motor de aprendizado
regras_conciliacao (
  id, padrao_memo, tipo_operacao,
  vezes_aplicada, vezes_confirmada, confianca,
  fornecedor_id, categoria_dre_id
)

-- Provisões automáticas
provisoes_automaticas (
  id, regra_id, conta_pagar_id,
  data_vencimento, valor, status
)

-- Templates de adquirentes
templates_adquirentes (
  id, nome_adquirente, tipo_relatorio,
  mapeamento (JSON), palavras_chave
)
```

---

## 📦 Formatos Suportados

### **OFX (Open Financial Exchange)**
- ✅ **OFX 1.x** (SGML) - Mais comum no Brasil
- ✅ **OFX 2.x** (XML) - Padrão internacional
- 🏦 **Bancos**: BB, Santander, Itaú, Bradesco, Stone, etc

### **Campos Extraídos do OFX:**
```xml
<STMTTRN>
  <TRNTYPE>DEBIT</TRNTYPE>           <!-- Tipo: CREDIT/DEBIT -->
  <DTPOSTED>20260201</DTPOSTED>      <!-- Data -->
  <TRNAMT>-150.00</TRNAMT>           <!-- Valor -->
  <FITID>202602011234567</FITID>     <!-- ID único do banco -->
  <MEMO>CPFL ENERGIA - Pagamento</MEMO>  <!-- Descrição (KEY!) -->
</STMTTRN>
```

O campo **MEMO** é a chave para o aprendizado automático! 🔑

---

## 🎓 Dicas Pro

### **Para Maximizar Automação:**

1. **Primeira vez com OFX novo:**
   - Classifique TODAS as pendentes no primeiro mês
   - Marque sempre "Criar regra automática"
   - Resultado: Próximo mês será 80%+ automático

2. **Fornecedores recorrentes:**
   - Sempre marque "Movimentação recorrente"
   - Sistema cria provisões automáticas
   - Previsibilidade no fluxo de caixa

3. **Templates de adquirentes:**
   - Use planilhas CSV específicas (Stone Recebimentos)
   - Mais detalhado que OFX genérico
   - Melhor rastreabilidade (NSU, Stone ID)

4. **Gerenciar regras:**
   - Revise regras periodicamente
   - Desative as que classificam errado
   - Confiança < 70%? Precisa mais confirmações

---

## 🐛 Troubleshooting

### **Upload OFX falha:**
```
❌ Erro: "Arquivo OFX vazio ou inválido"
```
**Solução:** 
- Verifique se é arquivo OFX mesmo (não PDF/HTML)
- Baixe novamente do banco
- Tente encoding diferente (UTF-8, Latin-1)

### **Nenhuma transação detectada:**
```
⚠️ Upload OK mas 0 transações
```
**Solução:**
- OFX pode estar sem tag `<STMTTRN>`
- Verifique período: OFX vazio nesse range
- Banco pode ter formato proprietário

### **Regra classifica errado:**
```
🔧 Regra aplica em movimentações erradas
```
**Solução:**
- Abra modal "Regras"
- Encontre a regra problemática
- Clique "Desativar"
- Reclassifique manualmente as erradas

---

## 📈 Roadmap Futuro

- [ ] **Parser CSV** para Stone/Cielo/Rede
- [ ] **Machine Learning** avançado (similaridade semântica)
- [ ] **Integração API Stone** (webhook conciliation)
- [ ] **Categorização automática DRE**
- [ ] **Detecção de duplicatas** entre adquirentes
- [ ] **Reconciliação com vendas** (NSU matching)
- [ ] **Dashboard analítico** avançado

---

## 🔗 Links Úteis

- **Swagger API:** http://localhost:8000/docs#/Conciliação%20Bancária%20-%20OFX
- **Endpoints:**
  - `POST /api/conciliacao/upload-ofx`
  - `GET /api/conciliacao/movimentacoes`
  - `POST /api/conciliacao/movimentacoes/{id}/classificar`
  - `GET /api/conciliacao/regras`
  - `GET /api/conciliacao/estatisticas`

---

## 👥 Suporte

Dúvidas ou problemas? 
- 📧 Abra uma issue no repositório
- 💬 Documente o OFX que deu problema
- 🔍 Verifique logs: `docker logs petshop-dev-backend`

---

**Desenvolvido com ❤️ para automatizar seu financeiro!** 🚀
