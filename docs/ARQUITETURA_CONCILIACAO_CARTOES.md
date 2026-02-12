# 🏗️ ARQUITETURA - CONCILIAÇÃO DE CARTÕES

**Documento Técnico de Requisitos Obrigatórios**

---

## 📣 ALERTAS CRÍTICOS DE ARQUITETURA

### ⚠️ 1. NÃO realizar baixa automática no upload

**Upload de arquivos ≠ Conciliação**

```
❌ ERRADO:
Upload OFX → Liquidar ContaReceber automaticamente

✅ CORRETO:
Upload OFX → Armazenar dados → Exibir para revisão → Usuário confirma → Processar
```

**Motivo:** Sistema deve permitir revisão antes de liquidar títulos.

---

### ⚠️ 2. Separar IMPORTAÇÃO de PROCESSAMENTO

**Duas etapas DISTINTAS e independentes:**

#### **ETAPA 1: IMPORTAÇÃO**
```python
# Apenas lê e armazena - NÃO toca no financeiro
def importar_arquivos():
    - Ler OFX
    - Ler pagamentos operadora
    - Ler recebimentos detalhados
    - Salvar dados CRUS no banco
    - NÃO alterar ContaReceber
    - NÃO alterar FluxoCaixa
```

#### **ETAPA 2: PROCESSAMENTO**
```python
# Executado APENAS após confirmação do usuário
def processar_conciliacao():
    - Fazer vínculos
    - Liquidar contas
    - Gerar movimentos de caixa
    - Atualizar DRE
```

**Motivo:** Misturar essas fases torna impossível auditar.

---

### ⚠️ 3. Trabalhar com ESTADOS (status)

**Sistema orientado a STATUS:**

#### **Parcelas (ContaReceber)**
```
prevista             → Criada no PDV
confirmada_operadora → Apareceu no relatório recebimentos
aguardando_lote      → Confirmada pela operadora, mas lote ainda não informado
em_lote              → Incluída no comprovante pagamentos
liquidada            → Crédito confirmado no OFX
```

**⚠️ Nota:** O estado `aguardando_lote` é importante porque operadoras costumam liberar o detalhamento de recebimentos antes de agrupar em lotes de pagamento.

#### **Lotes (ConciliacaoCartaoLote)**
```
previsto    → Aguardando arquivo da operadora
informado   → Arquivo pagamentos importado
creditado   → Confirmado no OFX
divergente  → Valores não batem
```

#### **Conciliação do Dia**
```
pendente   → Arquivos não importados
parcial    → Alguns arquivos faltando
concluída  → Todos arquivos, validação OK
```

**Motivo:** Sem isso o sistema vira caos rapidamente.

---

### ⚠️ 4. O banco NÃO possui NSU

```
❌ NUNCA tentar conciliar:
NSU ↔ OFX

✅ RELAÇÃO CORRETA:
Parcelas (NSU) → Lote (operadora) → Crédito banco (OFX)
```

**Exemplo:**
```
26 parcelas com NSU → 16 lotes Stone → 16 créditos OFX
```

---

### ⚠️ 5. Permitir conciliação PARCIAL

**Sistema deve funcionar com informação incompleta:**

```
Cenário 1:
✅ OFX
❌ Pagamentos
❌ Recebimentos
→ Apenas registra crédito bancário

Cenário 2:
✅ OFX
✅ Pagamentos
❌ Recebimentos
→ Valida OFX vs Pagamentos, mas não liquida parcelas

Cenário 3 (completo):
✅ OFX
✅ Pagamentos
✅ Recebimentos
→ Validação cascata + liquidação de parcelas
```

**Motivo:** Usuário pode ter arquivos em momentos diferentes.

---

### ⚠️ 6. Nunca apagar informações importadas

**Arquivos são EVIDÊNCIAS.**

```python
# Ao importar, guardar:
{
    "arquivo_original": "recebimentos_20260210.csv",
    "data_importacao": "2026-02-11 10:00:00",
    "usuario": "admin",
    "hash_md5": "a1b2c3d4...",
    "caminho_storage": "uploads/conciliacao/2026/02/..."
}
```

**Necessário para:**
- ✅ Auditoria
- ✅ Conferência futura
- ✅ Reprocessamento
- ✅ Rastreabilidade contábil

---

### ⚠️ 7. Conciliação precisa ser REVERSÍVEL

**Usuário pode descobrir que importou arquivo errado.**

```python
def reverter_conciliacao(conciliacao_id):
    """
    Permite desfazer conciliação completa ou parcial
    """
    - Retornar parcelas para status "prevista"
    - Remover vínculo com lotes
    - Remover vínculo com OFX
    - Manter arquivo original (evidência)
    - Gerar log de reversão
    - Reverter FluxoCaixa
```

**Motivo:** Sem reversão = risco operacional grave.

---

### ⚠️ 8. Guardar LOG completo

**Obrigatório em sistemas financeiros:**

```python
# Tabela: conciliacao_logs
{
    "id": 123,
    "conciliacao_id": 456,
    "versao_conciliacao": 1,  # ⚠️ Versionamento obrigatório
    "data_hora": "2026-02-11 10:05:33",
    "usuario_id": 1,
    "acao": "processar_conciliacao",
    "arquivos_utilizados": {
        "ofx": "extrato_20260210.ofx",
        "pagamentos": "pagamentos_09_10_fev.csv",
        "recebimentos": "recebimentos_fev.csv"
    },
    "quantidades": {
        "parcelas_liquidadas": 26,
        "lotes_conciliados": 16,
        "creditos_ofx": 16
    },
    "valores": {
        "total_ofx": 1820.00,
        "total_pagamentos": 1820.00,
        "total_recebimentos": 1820.01,
        "diferenca": 0.01
    },
    "status_final": "concluida",
    "divergencias": []
}
```

---

### ⚠️ 9. Diferenças devem gerar ALERTAS, não bloqueio

**Sistema deve sinalizar e permitir decisão manual:**

```python
# Ao validar totais
# ⚠️ TOLERÂNCIA É PARÂMETRO CONFIGURÁVEL POR EMPRESA
tolerance = empresa.parametros.tolerancia_conciliacao  # Ex: 0.01, 0.50, 5.00
tolerance_media = empresa.parametros.tolerancia_conciliacao_media  # Ex: 10.00

if diferenca <= tolerance:
    status = "concluida_com_tolerancia"
    alerta = f"Diferença de R$ {diferenca:.2f} - dentro da tolerância (R$ {tolerance:.2f})"
    permitir_processamento = True
    requer_confirmacao = False

elif diferenca <= tolerance_media:
    status = "divergencia_media"
    alerta = f"Diferença de R$ {diferenca:.2f} - requer verificação"
    permitir_processamento = True
    requer_confirmacao = True  # Confirmação simples

else:
    status = "divergencia_grave"
    alerta = f"Diferença de R$ {diferenca:.2f} - verificar arquivos"
    permitir_processamento = True  # NUNCA bloquear totalmente
    requer_confirmacao = True  # Confirmação EXPLÍCITA + log reforçado
    gerar_log_auditoria_critico(diferenca, motivo_usuario)
```

**⚠️ Nota Crítica:** Redes grandes trabalham com arredondamentos pesados. Cada empresa decide sua tolerância. Sistema JAMAIS deve bloquear - apenas exigir confirmação e registrar decisão do usuário.

**Motivo:** ERP não pode travar operação - usuário decide.

---

### ⚠️ 10. Frontend é consequência, não regra

**Toda inteligência no BACKEND (services):**

```
❌ Frontend:
- Fazer cálculos
- Validar regras de negócio
- Definir fluxos

✅ Frontend apenas:
- Mostrar dados
- Organizar visualmente
- Disparar processamento
- Exibir alertas
```

**Motivo:** Regras de negócio devem estar centralizadas e testáveis.

---

### ⚠️ 11. Templates por adquirente são obrigatórios

**Cada operadora tem formatos diferentes:**

```python
# Tabela: adquirentes_templates
{
    "nome": "Stone",
    "tipo_arquivo": "recebimentos",
    "mapeamento": {
        "nsu": "STONE ID",
        "valor_bruto": "VALOR BRUTO",
        "valor_liquido": "VALOR LÍQUIDO",
        "taxa_mdr": "DESCONTO DE MDR",
        "taxa_antecipacao": "DESCONTO DE ANTECIPAÇÃO",
        "data_venda": "DATA DA VENDA",
        "data_vencimento": "DATA DE VENCIMENTO",
        "bandeira": "BANDEIRA",
        "status": "ÚLTIMO STATUS"
    },
    "separador": ";",
    "encoding": "utf-8",
    "tem_header": true
}
```

**Suportar:**
- Stone
- Cielo
- Rede
- Getnet
- SafraPay
- PagSeguro
- Mercado Pago
- Outros

---

### ⚠️ 12. Antes de liquidar, validar totais

**Executar cascata de validação:**

```python
# VALIDAÇÃO EM 3 CAMADAS
def validar_cascata(data):
    # Camada 1: OFX vs Pagamentos
    if abs(total_ofx - total_pagamentos) <= 0.10:
        camada1 = "OK"
    else:
        camada1 = "DIVERGENTE"
        alertas.append(f"OFX ({total_ofx}) != Pagamentos ({total_pagamentos})")
    
    # Camada 2: Pagamentos vs Recebimentos
    if abs(total_pagamentos - total_recebimentos) <= 0.10:
        camada2 = "OK"
    else:
        camada2 = "DIVERGENTE"
        alertas.append(f"Pagamentos ({total_pagamentos}) != Recebimentos ({total_recebimentos})")
    
    # Decisão
    if camada1 == "OK" and camada2 == "OK":
        confianca = "ALTA"
        pode_liquidar = True
        requer_confirmacao = False
    elif camada1 == "OK" or camada2 == "OK":
        confianca = "MÉDIA"
        pode_liquidar = True
        requer_confirmacao = True  # Confirmação simples
    else:
        confianca = "BAIXA"
        pode_liquidar = True  # ⚠️ NUNCA bloquear totalmente
        requer_confirmacao = True  # Confirmação EXPLÍCITA + log crítico
        # ERP profissional deixa usuário assumir o risco
    
    return {
        "confianca": confianca,
        "pode_liquidar": pode_liquidar,
        "alertas": alertas
    }
```

---

### ⚠️ 13. Atualizar estimativas para valores reais

**Após confirmar operadora:**

```python
# No PDV → taxas ESTIMADAS
conta_receber = {
    "valor_bruto": 100.00,
    "taxa_mdr_estimada": 3.79,
    "taxa_antecipacao_estimada": 0.00,
    "valor_liquido_estimado": 96.21,
    "data_vencimento_estimada": "2026-03-12"
}

# Após importar recebimentos → taxas REAIS
conta_receber.update({
    "taxa_mdr_real": 3.79,
    "taxa_antecipacao_real": 1.50,
    "valor_liquido_real": 94.71,
    "data_vencimento_real": "2026-02-10",  # Antecipação
    "status": "confirmada_operadora",
    "diferenca_taxa": 1.50  # Alerta: antecipação não prevista
})
```

**Motivo:** Projeções precisas para fluxo de caixa e DRE.

---

### ⚠️ 14. Isso alimenta automaticamente

**Após liquidação, atualizar EM CASCATA:**

```python
def processar_conciliacao_completa(conciliacao_id):
    # 1. Liquidar ContaReceber
    for parcela in parcelas:
        parcela.status = "liquidada"
        parcela.data_liquidacao = data_credito_ofx
        parcela.valor_liquido_final = valor_real
    
    # 2. Atualizar FluxoCaixa
    fluxo_caixa.registrar_entrada(
        data=data_credito_ofx,
        valor=total_liquido,
        categoria="Recebimento Cartão",
        origem="Conciliação"
    )
    
    # 3. ⚠️ NÃO atualizar DRE diretamente!
    # DRE deve ser CALCULADA a partir das movimentações
    # Motivos:
    #   - Evita duplicidade
    #   - Reversão fica simples (só desfaz movimentos)
    #   - Reprocessamento de histórico possível
    #   - DRE é reflexo, não tabela viva
    
    # Correto: apenas garantir que movimentações existem
    # DRE será recalculada no próximo processamento de relatórios
    
    # 4. Atualizar Indicadores
    indicadores.recalcular_diario(data_credito_ofx)
    
    # 5. Gerar notificação
    notificar_usuario(
        "Conciliação processada com sucesso",
        f"{len(parcelas)} parcelas liquidadas - R$ {total_liquido}"
    )
```

**Subsistemas impactados:**
- ✅ Contas a Receber
- ✅ Fluxo de Caixa
- ✅ DRE Regime de Caixa
- ✅ Indicadores financeiros
- ✅ Dashboard

---

## 🏛️ ARQUITETURA PROPOSTA

### **Camadas do Sistema**

```
┌─────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                        │
│ - Upload de arquivos                                    │
│ - Visualização de dados importados                     │
│ - Dashboard de validação                                │
│ - Botão "Processar" (após revisão)                     │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ API ROUTES (FastAPI)                                    │
│ /importar-ofx                                           │
│ /importar-pagamentos                                    │
│ /importar-recebimentos                                  │
│ /validar-conciliacao                                    │
│ /processar-conciliacao (requer confirmação)            │
│ /reverter-conciliacao                                   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ SERVICES (Python)                                       │
│                                                          │
│ ConciliacaoImportService                                │
│ ├─ importar_ofx()                                       │
│ ├─ importar_pagamentos()                                │
│ └─ importar_recebimentos()                              │
│                                                          │
│ ConciliacaoValidacaoService                             │
│ ├─ validar_cascata()                                    │
│ ├─ calcular_diferencas()                                │
│ └─ gerar_alertas()                                      │
│                                                          │
│ ConciliacaoProcessamentoService                         │
│ ├─ processar_conciliacao()                              │
│ ├─ liquidar_parcelas()                                  │
│ ├─ atualizar_fluxo_caixa()                              │
│ └─ atualizar_subsistemas()                              │
│                                                          │
│ ConciliacaoReversaoService                              │
│ ├─ reverter_conciliacao()                               │
│ └─ gerar_log_reversao()                                 │
│                                                          │
│ AdquirenteTemplateService                               │
│ ├─ carregar_template()                                  │
│ └─ parsear_arquivo()                                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ DATABASE (PostgreSQL)                                   │
│                                                          │
│ conciliacao_importacoes                                 │
│ conciliacao_lotes                                       │
│ conciliacao_validacoes                                  │
│ conciliacao_logs                                        │
│ adquirentes_templates                                   │
│ contas_receber (atualizado)                             │
│ fluxo_caixa (gerado)                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### **Fase 1: Estrutura Base**
- [ ] Criar tabelas no banco
- [ ] Criar models (SQLAlchemy)
- [ ] Criar services básicos
- [ ] Criar routes de importação

### **Fase 2: Importação**
- [ ] Parser OFX genérico
- [ ] Parser CSV com templates
- [ ] Armazenamento de arquivos originais
- [ ] Sistema de templates configuráveis
- [ ] Endpoints de importação

### **Fase 3: Validação**
- [ ] Validação em cascata (3 camadas)
- [ ] Cálculo de diferenças
- [ ] Sistema de alertas
- [ ] Dashboard de revisão

### **Fase 4: Processamento**
- [ ] Liquidação de parcelas
- [ ] Atualização FluxoCaixa
- [ ] Atualização DRE Caixa
- [ ] Atualização Indicadores
- [ ] Sistema de logs

### **Fase 5: Reversão**
- [ ] Reverter liquidação
- [ ] Reverter vínculos
- [ ] Manter evidências
- [ ] Log de reversão

### **Fase 6: Frontend**
- [ ] Página ConciliacaoCartoes
- [ ] Upload sequencial
- [ ] Visualização de dados
- [ ] Dashboard de validação
- [ ] Confirmação de processamento

### **Fase 7: Testes**
- [ ] Testes unitários services
- [ ] Testes integração
- [ ] Testes com dados reais
- [ ] Teste de reversão

---

## 🎯 PRINCÍPIOS FUNDAMENTAIS

1. **Separação de responsabilidades:** Importação ≠ Processamento
2. **Reversibilidade:** Tudo pode ser desfeito
3. **Auditabilidade:** Log completo de tudo
4. **Flexibilidade:** Sistema funciona com dados parciais
5. **Confiabilidade:** Validação antes de alterar financeiro
6. **Extensibilidade:** Suporta múltiplas adquirentes
7. **Transparência:** Usuário vê e confirma antes de executar

---

**Documento criado em:** 11/02/2026  
**Versão:** 1.0  
**Status:** Aprovado para implementação
