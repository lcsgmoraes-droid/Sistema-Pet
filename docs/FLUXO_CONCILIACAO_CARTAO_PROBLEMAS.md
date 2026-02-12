# 🗺️ Fluxo Completo: Conciliação de Cartões
## Mapeamento de Sucessos e Bloqueios

---

## 📊 LEGENDA
- ✅ **Verde**: Funciona perfeitamente
- ⚠️ **Amarelo**: Funciona com limitações
- 🔴 **Vermelho**: BLOQUEADO - Não funciona
- 🤔 **Azul**: Em discussão

---

## 🔄 FLUXO PONTA A PONTA

```
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 1: VENDA NO PDV                                           │
├─────────────────────────────────────────────────────────────────┤
│ Status: ✅ FUNCIONA                                             │
│                                                                 │
│ Cliente compra: R$ 300,00                                       │
│ Forma: Cartão Crédito Visa 3x                                   │
│ Terminal Stone gera NSU: 1416215E+13                            │
│                                                                 │
│ Sistema registra:                                               │
│ ✅ Venda #0123                                                 │
│    ├─ NSU: 1416215E+13                                         │
│    ├─ Valor Total: R$ 300,00                                   │
│    ├─ Forma: Crédito Visa 3x                                   │
│    └─ Data: 10/02/2026 14:35                                   │
│                                                                 │
│ ✅ ContaReceber #1 (Parcela 1/3)                              │
│    ├─ NSU: 1416215E+13                                         │
│    ├─ Valor: R$ 100,00                                         │
│    ├─ Vencimento: 12/03/2026 (D+30)                           │
│    └─ Status: pendente                                          │
│                                                                 │
│ ✅ ContaReceber #2 (Parcela 2/3)                              │
│    ├─ NSU: 1416215E+13                                         │
│    ├─ Valor: R$ 100,00                                         │
│    ├─ Vencimento: 12/04/2026 (D+60)                           │
│    └─ Status: pendente                                          │
│                                                                 │
│ ✅ ContaReceber #3 (Parcela 3/3)                              │
│    ├─ NSU: 1416215E+13                                         │
│    ├─ Valor: R$ 100,00                                         │
│    ├─ Vencimento: 12/05/2026 (D+90)                           │
│    └─ Status: pendente                                          │
│                                                                 │
│ ✅ Taxa Esperada (cadastro formas_pagamento):                 │
│    Visa Crédito 3x = 3,5% a.m. × 3 = 10,5%                    │
│    Valor esperado líquido = R$ 268,50                          │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
                     [Passa 1 dia]
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 2: IMPORTAÇÃO VENDAS.xlsx (Stone)                        │
├─────────────────────────────────────────────────────────────────┤
│ Status: ✅ FUNCIONA                                             │
│                                                                 │
│ Usuário baixa VENDAS.xlsx da Stone (D+1):                      │
│                                                                 │
│ STONE ID     │ VALOR BRUTO │ BANDEIRA │ N PARCELAS │ DATA     │
│ 1416215E+13  │ 300,00      │ VISA     │ 3          │ 10/02/26 │
│                                                                 │
│ Sistema processa:                                               │
│ ✅ Busca Venda pelo NSU: 1416215E+13                          │
│ ✅ Encontrado: Venda #0123                                     │
│ ✅ Valida Valor: R$ 300,00 = R$ 300,00 ✓                      │
│ ✅ Valida Bandeira: VISA = VISA ✓                              │
│ ✅ Valida Parcelas: 3 = 3 ✓                                    │
│ ✅ Cria/Atualiza rastreamento_cartao:                          │
│    ├─ nsu: 1416215E+13                                         │
│    ├─ venda_id: 0123                                           │
│    ├─ stone_valor_bruto: 300.00                                │
│    ├─ stone_bandeira: VISA                                     │
│    ├─ stone_parcelas: 3                                        │
│    ├─ status: "importado_vendas"                               │
│    └─ data_importacao_vendas: 11/02/2026 08:00                │
│                                                                 │
│ ✅ Resultado: 100% das vendas confirmadas com Stone            │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 3: IMPORTAÇÃO RECEBIMENTOS.xlsx (Stone)                  │
├─────────────────────────────────────────────────────────────────┤
│ Status: ✅ FUNCIONA (fonte primária de conciliação)            │
│                                                                 │
│ Usuário baixa RECEBIMENTOS.xlsx da Stone (D+1 ou D+30):        │
│                                                                 │
│ STONE ID    │ PARC │ VL BRUTO │ DESCONTO │ VL LÍQ │ DT PGTO  │
│ 1416215E+13 │ 1/3  │ 100,00   │ 3,50     │ 96,50  │ 12/03/26 │
│ 1416215E+13 │ 2/3  │ 100,00   │ 3,50     │ 96,50  │ 12/04/26 │
│ 1416215E+13 │ 3/3  │ 100,00   │ 3,50     │ 96,50  │ 12/05/26 │
│                                                                 │
│ Sistema processa LINHA 1 (Parcela 1/3):                        │
│ ✅ Busca rastreamento_cartao pelo NSU                          │
│ ✅ Encontrado: nsu=1416215E+13, venda_id=0123                 │
│ ✅ Busca ContaReceber (venda_id + parcela 1/3)                │
│ ✅ Encontrado: ContaReceber #1                                 │
│                                                                 │
│ ✅ Valida Valor:                                               │
│    - Esperado: R$ 100,00                                       │
│    - Stone Bruto: R$ 100,00 ✓                                  │
│                                                                 │
│ ✅ Valida Taxa:                                                │
│    - Esperada: R$ 10,50 (10,5% de R$ 100)                     │
│    - Stone Real: R$ 3,50 (3,5% de R$ 100)                     │
│    - ✓ Taxa correta (é por parcela, não total!)               │
│                                                                 │
│ ✅ Baixa ContaReceber #1:                                      │
│    ├─ status: "recebido"                                       │
│    ├─ valor_recebido: R$ 96,50                                 │
│    ├─ data_recebimento: 12/03/2026                             │
│    └─ conciliado: true                                          │
│                                                                 │
│ ✅ Cria Lançamento DRE (Taxa):                                 │
│    ├─ categoria: "Taxas de Cartão - Visa"                     │
│    ├─ valor: R$ 3,50                                           │
│    ├─ data: 12/03/2026                                         │
│    └─ tipo: despesa                                             │
│                                                                 │
│ ✅ Atualiza rastreamento_cartao:                               │
│    ├─ conta_receber_id: [#1, #2, #3]                          │
│    ├─ stone_valor_liquido: 96,50 (por parcela)                │
│    ├─ stone_desconto_mdr: 3,50                                 │
│    ├─ taxa_esperada_valor: 3,50                                │
│    ├─ taxa_real_valor: 3,50                                    │
│    ├─ divergencia_taxa: false ✅                               │
│    ├─ status: "conciliado_stone"                               │
│    └─ data_importacao_recebimentos: 11/02/2026 08:05          │
│                                                                 │
│ [REPETE para Parcela 2/3 e 3/3]                                │
│                                                                 │
│ ✅ Resultado Final:                                            │
│    - 3 ContaReceber baixados                                   │
│    - 3 lançamentos de taxa no DRE                              │
│    - Valor total líquido: R$ 289,50                            │
│    - Status: "conciliado_stone" ✅                             │
│                                                                 │
│ 💡 PONTO CHAVE: Esta é a conciliação oficial!                  │
│    Stone confirma recebimento, sistema baixa contas.           │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
        [Sistema funciona até aqui PERFEITAMENTE]
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ ETAPA 4: ANTECIPAÇÕES (Cenário Complexo)                    │
├─────────────────────────────────────────────────────────────────┤
│ Status: ⚠️ FUNCIONA com tag especial                           │
│                                                                 │
│ Empresa solicita antecipação no dia 12/03/2026:                │
│                                                                 │
│ RECEBIMENTOS.xlsx (atualizado):                                │
│ STONE ID    │ PARC │ VL LÍQ │ DT PGTO  │ ANTECIPADO          │
│ 1416215E+13 │ 1/3  │ 96,50  │ 12/03/26 │ Não                  │
│ 1416215E+13 │ 2/3  │ 94,00  │ 12/03/26 │ Sim (taxa -R$ 2,50) │
│ 1416215E+13 │ 3/3  │ 94,00  │ 12/03/26 │ Sim (taxa -R$ 2,50) │
│                                                                 │
│ Sistema detecta:                                                │
│ ⚠️ Parcela 2/3: data_pgto != data_vencimento original         │
│    └─ Esperado: 12/04/26, Real: 12/03/26                      │
│    └─ TAG: "ANTECIPADO" + Taxa adicional de R$ 2,50           │
│                                                                 │
│ ✅ Baixa ContaReceber #2 e #3 antecipadamente                 │
│ ✅ Cria lançamentos de taxa de antecipação (DRE)              │
│ ✅ Marca visualmente na interface 🏷️                          │
│                                                                 │
│ ✅ Resultado: Funciona! Sistema adaptou.                       │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
      [Agora vem o problema crítico]
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│ 🔴 ETAPA 5: EXTRATO BANCÁRIO OFX                               │
├─────────────────────────────────────────────────────────────────┤
│ Status: 🔴 BLOQUEADO - Rastreamento impossível                 │
│                                                                 │
│ Usuário importa EXTRATO.ofx do banco:                          │
│                                                                 │
│ <STMTTRN>                                                       │
│   <TRNTYPE>CREDIT</TRNTYPE>                                    │
│   <DTPOSTED>20260312080000</DTPOSTED>                          │
│   <TRNAMT>289.50</TRNAMT>                                      │
│   <FITID>c8743e0a-6fbf-4069-b688-22c85186ca3d</FITID>          │
│   <MEMO>Recebimento vendas - Antecipação</MEMO>               │
│ </STMTTRN>                                                      │
│                                                                 │
│ Sistema tenta processar:                                        │
│ 🔴 PROBLEMA 1: Sem NSU                                         │
│    - Não tem Stone ID                                           │
│    - Não tem número da venda                                    │
│    - Não tem identificador único                                │
│                                                                 │
│ 🔴 PROBLEMA 2: Valor agregado                                  │
│    - R$ 289,50 = Soma de 3 parcelas                            │
│    - Mas pode ser:                                              │
│      • 3 parcelas da Venda #0123? ✓                            │
│      • 1 parcela de R$ 289,50?                                 │
│      • 5 parcelas de valores diferentes que somam R$ 289,50?  │
│    └─ IMPOSSÍVEL SABER!                                         │
│                                                                 │
│ 🔴 PROBLEMA 3: Antecipações desalinhadas                       │
│    Empresa X: Cai na hora (mesmo dia da venda)                 │
│    Empresa Y: Cai toda segunda-feira (agrupado)                │
│    Empresa Z: Cai quando solicita (imprevisível)               │
│    └─ Nenhum padrão confiável por data                          │
│                                                                 │
│ 🔴 PROBLEMA 4: Múltiplas vendas mesmo valor                    │
│    No dia 10/02 tivemos:                                        │
│    - Venda #0120: R$ 50,00 (NSU 111111)                        │
│    - Venda #0125: R$ 50,00 (NSU 222222)                        │
│    - Venda #0130: R$ 50,00 (NSU 333333)                        │
│                                                                 │
│    OFX no dia 12/03:                                            │
│    <TRNAMT>150.00</TRNAMT>                                     │
│    <MEMO>Recebimento vendas</MEMO>                             │
│                                                                 │
│    Qual das vendas? As 3 juntas? Outras vendas?                │
│    └─ IMPOSSÍVEL VINCULAR! 🔴                                  │
│                                                                 │
│ 🔴 TENTATIVA 1: Buscar por valor                               │
│    SELECT * FROM rastreamento_cartao                            │
│    WHERE stone_valor_liquido_total = 289.50                    │
│    AND data_pagamento = '2026-03-12'                           │
│    └─ Retorna 15 registros diferentes! ❌                      │
│                                                                 │
│ 🔴 TENTATIVA 2: Buscar por data + faixa de valor              │
│    SELECT * FROM rastreamento_cartao                            │
│    WHERE data_pagamento BETWEEN '2026-03-11' AND '2026-03-13' │
│    AND stone_valor_liquido_total BETWEEN 289.00 AND 290.00    │
│    └─ Retorna 8 registros! Qual é o certo? ❌                  │
│                                                                 │
│ 🔴 TENTATIVA 3: Somar créditos OFX do dia                     │
│    Total OFX 12/03: R$ 15.432,10                               │
│    Total RECEBIMENTOS Stone 12/03: R$ 15.450,00               │
│    Divergência: R$ 17,90                                        │
│    └─ Mas não diz QUAIS vendas! ❌                             │
│                                                                 │
│ 💀 CONCLUSÃO: RASTREAMENTO 1:1 IMPOSSÍVEL                      │
│                                                                 │
│ ❌ Não dá pra vincular movimentacao_bancaria_id                │
│ ❌ Não dá pra confirmar "tripla conciliação"                   │
│ ❌ Não dá pra marcar status "validado_ofx"                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 ANÁLISE DE IMPACTO

### ✅ **O QUE FUNCIONA SEM OFX:**

```
1. ✅ Venda PDV registra NSU
2. ✅ Stone VENDAS confirma transação processada
3. ✅ Stone RECEBIMENTOS baixa ContaReceber
4. ✅ Sistema registra taxas no DRE
5. ✅ Antecipações são detectadas e marcadas
6. ✅ Divergências de taxa são alertadas
7. ✅ NSUs órfãos são listados para ação manual
8. ✅ Relatórios de conciliação completos
```

**Confiabilidade: 99%** (Stone é a fonte oficial)

---

### 🔴 **O QUE NÃO FUNCIONA (Dependência OFX):**

```
1. ❌ Vincular crédito bancário à venda específica
2. ❌ Confirmar que valor "realmente" entrou na conta
3. ❌ Detectar divergências banco × Stone
4. ❌ Tripla validação (PDV × Stone × Banco)
5. ❌ Rastreamento completo ponta-a-ponta
```

**Impacto Real: Baixo!**  
Motivo: Stone já é a confirmação oficial de recebimento.

---

## 💡 ALTERNATIVAS PROPOSTAS

### **Opção A: OFX para Saldo Geral**
```
Usar OFX apenas para:
✅ Conferir saldo da conta bancária
✅ Detectar débitos (taxas bancárias, IOF, etc)
✅ Detectar créditos não-cartão (transferências, PIX, etc)

❌ NÃO tentar vincular créditos de cartão
```

### **Opção B: Validação Agregada (Por Período)**
```
Relatório Mensal:
- Total Stone RECEBIMENTOS março: R$ 145.320,00
- Total OFX CREDIT março: R$ 145.318,50
- Divergência: -R$ 1,50 (0,001%) ✅ Aceitável

Se divergência > 0,5%: ⚠️ Alerta para investigação
```

### **Opção C: Marcação Manual (Interface)**
```
Tela de MovimentacoesBancarias:
┌────────────────────────────────────────────┐
│ 12/03 │ CREDIT │ R$ 289,50 │ Stone       │
├────────────────────────────────────────────┤
│ Possíveis origens:                         │
│ [ ] Venda #0123 (3x R$ 96,50)             │
│ [ ] Venda #0130 (2x R$ 144,75)            │
│ [ ] Múltiplas vendas                       │
│                                            │
│ [Vincular] [Ignorar] [Já Conciliado]      │
└────────────────────────────────────────────┘
```

### **Opção D: Não Usar OFX para Cartões** ⭐ **RECOMENDADO**
```
Fluxo simplificado:
1. PDV → NSU registrado
2. Stone RECEBIMENTOS → Baixa + Taxas
3. OFX → Apenas outras movimentações

Cartões ficam 100% conciliados por Stone.
OFX para PIX, transferências, tarifas, etc.
```

---

## 🤔 DISCUSSÃO ABERTA

### **Pergunta Central:**
> Vale a pena tentar forçar vinculação OFX × Cartão?

**Prós de usar OFX:**
- ✅ "Confirmação" extra que entrou no banco
- ✅ Auditoria completa

**Contras de usar OFX:**
- ❌ Impossível rastrear individualmente
- ❌ Antecipações quebram qualquer lógica
- ❌ Aumenta complexidade sem ganho real
- ❌ Stone já é fonte confiável (oficial)

### **Proposta de Consenso:**
Stone RECEBIMENTOS = **Conciliação Final**  
OFX = **Validação de Saldo Agregado** (opcional)

---

## 📌 DECISÃO NECESSÁRIA

Escolher 1 das opções:
- [ ] A) OFX para saldo geral (sem vínculo)
- [ ] B) Validação agregada mensal (%)
- [ ] C) Marcação manual na interface
- [ ] D) Não usar OFX para cartões ⭐

---

**Aguardando decisão do Lucas!** 🚀
