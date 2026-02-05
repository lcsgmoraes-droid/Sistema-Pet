# TRANSACTION_CANDIDATES.md

**Fase:** 2.2 - Mapeamento de Transactions  
**Data:** 2026-02-05  
**Tipo:** Análise de Fluxos Críticos  

---

## 🎯 OBJETIVO

Mapear todos os fluxos do sistema que realizam **MÚLTIPLAS OPERAÇÕES DE ESCRITA** dependentes e que **DEVEM** usar transaction explícita para garantir atomicidade.

---

## 📊 TABELA RESUMO

| # | Fluxo | Arquivo | Função | Prioridade | Classificação | Operações |
|---|-------|---------|--------|------------|---------------|-----------|
| 1 | **Exclusão de Venda** | `vendas_routes.py` | `excluir_venda` | **P0** | 🔴 **OBRIGATÓRIO** | 8+ DELETE/UPDATE |
| 2 | **Cancelamento de Venda** | `vendas/service.py` | `cancelar_venda` | **P0** | 🔴 **OBRIGATÓRIO** | 6+ DELETE/UPDATE |
| 3 | **Provisão de Comissões** | `comissoes_provisao.py` | `provisionar_comissoes_venda` | **P0** | 🔴 **OBRIGATÓRIO** | INSERT + UPDATE + DRE |
| 4 | **Geração de Comissões** | `comissoes_service.py` | `gerar_comissoes_venda` | **P0** | 🔴 **OBRIGATÓRIO** | N INSERT + UPDATE |
| 5 | **Estorno de Comissões** | `comissoes_estorno.py` | `estornar_comissoes_venda` | **P0** | 🔴 **OBRIGATÓRIO** | N UPDATE |
| 6 | **Transferência de Estoque** | `estoque_transferencia_service.py` | `transferir` | **P0** | 🔴 **OBRIGATÓRIO** | 2 UPDATE + COMMIT |
| 7 | **Upload Nota Fiscal** | `notas_entrada_routes.py` | `upload_xml` | **P0** | 🔴 **OBRIGATÓRIO** | INSERT Nota + N Itens |
| 8 | **Config Batch Comissões** | `comissoes_routes.py` | `salvar_batch_configuracoes` | **P0** | 🔴 **OBRIGATÓRIO** | N INSERT/UPDATE |
| 9 | **Criar Venda** | `vendas/service.py` | `criar_venda` | **P0** | 🔴 **OBRIGATÓRIO** | Venda + Itens + Contas |
| 10 | **Recorrência Contas a Receber** | `contas_receber_routes.py` | `processar_recorrencias` | **P1** | 🟡 **RECOMENDADO** | N INSERT |
| 11 | **Movimentação Estoque Kit** | `estoque_routes.py` | `dar_baixa_kit` | **P1** | 🟡 **RECOMENDADO** | N UPDATE |
| 12 | **Transferência Estoque** | `estoque_routes.py` | `transferir_estoque` | **P1** | 🟡 **RECOMENDADO** | 2 INSERT |
| 13 | **Cancelamento de Pedido** | `pedidos_compra_routes.py` | `cancelar_pedido` | **P2** | 🟢 **NÃO NECESSÁRIO** | UPDATE status |

---

## 🔴 FLUXOS OBRIGATÓRIOS (P0)

### 1. Exclusão de Venda (`vendas_routes.py::excluir_venda`)

**Arquivo:** `backend/app/vendas_routes.py`  
**Linhas:** 1237-1370  
**Função:** `excluir_venda`

#### Entidades Afetadas
- `vendas` (DELETE)
- `vendas_itens` (DELETE)
- `movimentacoes_caixa` (DELETE)
- `movimentacoes_financeiras` (DELETE + UPDATE saldo)
- `lancamentos_manuais` (DELETE ou UPDATE status)
- `contas_receber` (DELETE ou UPDATE status)
- `vendas_pagamentos` (DELETE)
- `estoque_movimentacoes` (INSERT - estorno)

#### Operações Executadas
```
1. DELETE múltiplas movimentações de caixa
2. DELETE movimentações bancárias
3. UPDATE saldo de contas bancárias (débito/crédito)
4. DELETE ou UPDATE lancamentos (status = cancelado)
5. DELETE ou UPDATE contas a receber (status = cancelado)
6. DELETE pagamentos
7. DELETE itens da venda
8. DELETE venda
9. INSERT movimentações de estoque (estorno)
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - PERDA DE INTEGRIDADE FINANCEIRA**
- Venda deletada mas pagamentos permanecem
- Caixa com movimentações órfãs
- Saldo bancário incorreto (não estornado)
- Contas a receber duplicadas
- Estoque não estornado

#### Justificativa Técnica
Operação financeira que **DEVE SER ATÔMICA**. Se qualquer passo falhar (DELETE de caixa, UPDATE de saldo bancário, etc), TODAS as operações devem ser revertidas. Caso contrário, o sistema ficará com dados inconsistentes irrecuperáveis.

---

### 2. Cancelamento de Venda (`vendas/service.py::cancelar_venda`)

**Arquivo:** `backend/app/vendas/service.py`  
**Linhas:** ~500-800 (orquestrador)  
**Função:** `cancelar_venda`

#### Entidades Afetadas
- `vendas` (UPDATE status)
- `contas_receber` (UPDATE status)
- `estoque_movimentacoes` (INSERT - estorno)
- `comissoes_itens` (UPDATE status via service)
- `movimentacoes_financeiras` (UPDATE ou DELETE)

#### Operações Executadas
```
1. Validar venda e status
2. Estornar estoque (múltiplas movimentações)
3. Cancelar contas a receber (UPDATE status)
4. Remover movimentações financeiras
5. Estornar comissões (via comissoes_estorno.py)
6. UPDATE venda.status = 'cancelada'
7. Auditoria (INSERT)
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - INCONSISTÊNCIA OPERACIONAL**
- Venda cancelada mas estoque não devolvido
- Comissões não estornadas (funcionário recebe indevidamente)
- Contas a receber ativas de venda cancelada
- Relatórios DRE incorretos

#### Justificativa Técnica
Orquestração complexa que coordena múltiplos services (EstoqueService, ComissoesService). Se um service falhar (ex: estorno de estoque), a venda não pode ficar marcada como cancelada. Transaction explícita garante atomicidade de todo o fluxo.

---

### 3. Provisão de Comissões (`comissoes_provisao.py::provisionar_comissoes_venda`)

**Arquivo:** `backend/app/comissoes_provisao.py`  
**Linhas:** 1-330  
**Função:** `provisionar_comissoes_venda`

#### Entidades Afetadas
- `comissoes_itens` (UPDATE comissao_provisionada)
- `contas_pagar` (INSERT)
- `dre_periodos` (UPDATE via função)
- `lancamentos_manuais` (INSERT - DRE)

#### Operações Executadas
```
Para cada comissão pendente:
1. Buscar dados da venda e funcionário
2. Buscar subcategoria DRE "Comissões"
3. INSERT conta a pagar (fornecedor = funcionário)
4. INSERT lançamento DRE
5. UPDATE dre_periodos (consolidação)
6. UPDATE comissoes_itens.comissao_provisionada = 1
7. Repetir para N comissões
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - INCONSISTÊNCIA CONTÁBIL**
- Conta a pagar criada sem comissão marcada como provisionada
- DRE atualizada mas comissão não marcada (dupla provisão futura)
- Funcionário com conta a pagar sem comissão vinculada
- Balanço DRE incorreto

#### Justificativa Técnica
Operação contábil que cria **passivos financeiros** (contas a pagar) e atualiza **demonstrativos oficiais** (DRE). Se falhar parcialmente, o sistema terá obrigações financeiras inconsistentes. Transaction garante que TODAS as comissões sejam provisionadas atomicamente.

---

### 4. Geração de Comissões (`comissoes_service.py::gerar_comissoes_venda`)

**Arquivo:** `backend/app/comissoes_service.py`  
**Linhas:** ~450-650  
**Função:** `gerar_comissoes_venda`

#### Entidades Afetadas
- `comissoes_itens` (INSERT múltiplos)
- `comissoes_provisao` (via função - INSERT contas a pagar)
- `contas_pagar` (INSERT indiretamente)
- `dre_periodos` (UPDATE indiretamente)

#### Operações Executadas
```
Para cada item da venda:
1. Calcular valor base (lucro/faturamento)
2. Aplicar percentual de comissão
3. Deduzir taxas/impostos/custos
4. INSERT comissao_item com snapshot completo
5. Acumular total
6. COMMIT
7. Chamar provisionar_comissoes_venda (opcional)
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - COMISSÕES PARCIAIS**
- Funcionário recebe comissão de apenas alguns itens
- Total de comissões incorreto
- Provisões incompletas
- Relatórios gerenciais errados

#### Justificativa Técnica
Geração de comissões de **MÚLTIPLOS ITENS** de uma venda deve ser atômica. Se o cálculo de um item falhar, NENHUMA comissão deve ser registrada. Caso contrário, o funcionário terá comissões parciais e incorretas.

---

### 5. Estorno de Comissões (`comissoes_estorno.py::estornar_comissoes_venda`)

**Arquivo:** `backend/app/comissoes_estorno.py`  
**Linhas:** 1-160  
**Função:** `estornar_comissoes_venda`

#### Entidades Afetadas
- `comissoes_itens` (UPDATE status = 'estornado')
- `contas_pagar` (UPDATE status = 'cancelado' - opcional)

#### Operações Executadas
```
1. Buscar todas as comissões da venda
2. Filtrar comissões estornáveis (status pendente/gerada)
3. UPDATE status = 'estornado' para cada comissão
4. UPDATE data_estorno e motivo
5. (Opcional) Cancelar contas a pagar vinculadas
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - ESTORNO PARCIAL**
- Algumas comissões estornadas, outras não
- Funcionário recebe pagamento de comissão estornada
- Conta a pagar ativa de comissão estornada
- Total de comissões incorreto

#### Justificativa Técnica
Estorno deve ser **ALL or NOTHING**. Todas as comissões da venda devem ser estornadas atomicamente. Estorno parcial causa pagamentos indevidos e inconsistência contábil.

---

### 6. Transferência de Estoque (`estoque_transferencia_service.py::transferir`)

**Arquivo:** `backend/app/estoque_transferencia_service.py`  
**Linhas:** 1-70  
**Função:** `transferir`

#### Entidades Afetadas
- `estoque_local` (UPDATE origem - decremento)
- `estoque_local` (UPDATE/INSERT destino - incremento)

#### Operações Executadas
```
1. Validar quantidade e locais
2. Buscar estoque origem
3. UPDATE origem.quantidade -= X
4. Buscar ou criar estoque destino
5. UPDATE destino.quantidade += X
6. COMMIT
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - PERDA DE ESTOQUE**
- Origem decrementada mas destino não incrementado = **PERDA REAL DE MERCADORIA NO SISTEMA**
- Destino incrementado mas origem não decrementada = **DUPLICAÇÃO DE ESTOQUE**
- Inventário incorreto
- Contagem física divergente

#### Justificativa Técnica
Transferência é operação de **DÉBITO E CRÉDITO** simultâneos. Se apenas um lado for executado, o estoque total do sistema ficará INCORRETO. Equivale a uma transferência bancária - ambos os lados devem ocorrer atomicamente.

---

### 7. Upload de Nota Fiscal XML (`notas_entrada_routes.py::upload_xml`)

**Arquivo:** `backend/app/notas_entrada_routes.py`  
**Linhas:** 620-750  
**Função:** `upload_xml`

#### Entidades Afetadas
- `notas_entrada` (INSERT)
- `notas_entrada_itens` (INSERT múltiplos)
- `pessoas` (INSERT fornecedor - condicional)
- `produtos` (UPDATE SKU - condicional)

#### Operações Executadas
```
1. Parse do XML
2. Buscar ou criar fornecedor (INSERT se novo)
3. INSERT nota fiscal
4. Para cada item do XML:
   - Matching automático de produto
   - INSERT nota_entrada_item
   - UPDATE produto (SKU se necessário)
5. UPDATE nota.produtos_vinculados/nao_vinculados
6. COMMIT
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - NOTA FISCAL INCOMPLETA**
- Nota criada mas itens não inseridos
- Fornecedor criado mas nota não vinculada
- Alguns itens inseridos, outros não
- Impossível rastrear entrada de mercadorias

#### Justificativa Técnica
Upload de nota fiscal com **MÚLTIPLOS ITENS** deve ser atômico. Uma nota sem todos os seus itens é **INVÁLIDA** legalmente e contabilmente. Transaction garante que a nota só exista se todos os itens forem inseridos corretamente.

---

### 8. Configuração em Batch de Comissões (`comissoes_routes.py::salvar_batch_configuracoes`)

**Arquivo:** `backend/app/comissoes_routes.py`  
**Linhas:** 440-500  
**Função:** `salvar_batch_configuracoes`

#### Entidades Afetadas
- `comissoes_configuracao` (INSERT/UPDATE múltiplos)

#### Operações Executadas
```
Para cada configuração no batch:
1. Validar tipo e percentual
2. Buscar se já existe (SELECT)
3. Se existe: UPDATE percentual e ativo
4. Se não existe: INSERT nova configuração
5. Repetir para N configurações
6. COMMIT
```

#### Risco se Falhar no Meio
🚨 **ALTO - CONFIGURAÇÃO PARCIAL**
- Funcionário com configurações incompletas
- Algumas categorias configuradas, outras não
- Comissões calculadas incorretamente
- Funcionário prejudicado ou beneficiado indevidamente

#### Justificativa Técnica
Configuração de comissões deve ser **COMPLETA** para ser válida. Se um funcionário tem 10 configurações mas apenas 5 são salvas, suas comissões serão calculadas incorretamente. Transaction garante que TODAS as configurações sejam salvas juntas.

---

### 9. Criação de Venda (`vendas/service.py::criar_venda`)

**Arquivo:** `backend/app/vendas/service.py`  
**Linhas:** 120-400  
**Função:** `criar_venda`

#### Entidades Afetadas
- `vendas` (INSERT)
- `vendas_itens` (INSERT múltiplos)
- `lancamentos_manuais` (INSERT)
- `contas_receber` (INSERT)
- `categorias_financeiras` (INSERT - condicional)

#### Operações Executadas
```
1. Validar payload (itens, cliente, etc)
2. Gerar número sequencial da venda
3. Calcular totais
4. INSERT venda
5. Para cada item:
   - Validar produto/variação
   - INSERT venda_item
6. Buscar ou criar categoria "Vendas"
7. INSERT lançamento previsto (fluxo de caixa)
8. INSERT conta a receber
9. COMMIT
```

#### Risco se Falhar no Meio
🚨 **CRÍTICO - VENDA INCOMPLETA**
- Venda criada mas sem itens = **VENDA FANTASMA**
- Itens inseridos mas conta a receber não criada = **RECEITA NÃO RASTREADA**
- Lançamento criado mas venda não = **FLUXO DE CAIXA INCORRETO**
- Número de venda consumido sem venda real

#### Justificativa Técnica
Criação de venda é operação **FUNDAMENTAL** que envolve múltiplas entidades dependentes. Uma venda sem itens ou sem conta a receber é **INVÁLIDA** operacionalmente. Transaction garante que a venda só exista se TODOS os seus componentes forem criados.

---

## 🟡 FLUXOS RECOMENDADOS (P1)

### 10. Processamento de Recorrências (`contas_receber_routes.py::processar_recorrencias`)

**Arquivo:** `backend/app/contas_receber_routes.py`  
**Linhas:** 730-820  
**Função:** `processar_recorrencias`

#### Entidades Afetadas
- `contas_receber` (INSERT múltiplas + UPDATE próxima recorrência)
- `lancamentos_manuais` (INSERT múltiplos)

#### Operações Executadas
```
Para cada conta recorrente vencida:
1. Validar se já foi processada
2. INSERT nova conta a receber
3. INSERT lançamento no fluxo de caixa
4. UPDATE conta_origem.proxima_recorrencia
5. Repetir para N contas
6. COMMIT
```

#### Risco se Falhar no Meio
🟡 **MÉDIO - RECORRÊNCIA PARCIAL**
- Algumas contas criadas, outras não
- Conta origem atualizada mas nova conta não criada
- Lançamento criado sem conta vinculada
- Relatórios de recorrência inconsistentes

#### Justificativa Técnica
Processamento de recorrências deve ser **ATÔMICO POR CONTA**. Se múltiplas contas são processadas, é aceitável que uma falhe e outras sejam criadas (não é crítico). Mas para CADA conta, a criação da nova conta + atualização da origem deve ser atômica.

**Recomendação:** Transaction para cada conta individualmente, não para todo o batch.

---

### 11. Baixa de Estoque de Kit (`estoque_routes.py::dar_baixa_kit`)

**Arquivo:** `backend/app/estoque_routes.py`  
**Linhas:** ~250-310  
**Função:** `dar_baixa_kit` (inferido)

#### Entidades Afetadas
- `estoque_movimentacoes` (INSERT kit)
- `estoque_movimentacoes` (INSERT múltiplos componentes)

#### Operações Executadas
```
1. INSERT movimentação do kit (saída)
2. Para cada componente:
   - INSERT movimentação de saída
   - UPDATE estoque do componente
3. COMMIT
```

#### Risco se Falhar no Meio
🟡 **MÉDIO - BAIXA PARCIAL**
- Kit baixado mas componentes não
- Alguns componentes baixados, outros não
- Estoque inconsistente entre kit e componentes

#### Justificativa Técnica
Baixa de kit envolve **MÚLTIPLAS MOVIMENTAÇÕES** relacionadas. Se falhar no meio, o estoque de componentes ficará incorreto. Transaction garante que kit e TODOS os componentes sejam baixados juntos.

---

### 12. Transferência de Estoque (Rota) (`estoque_routes.py::transferir_estoque`)

**Arquivo:** `backend/app/estoque_routes.py`  
**Linhas:** ~580-620  
**Função:** `transferir_estoque`

#### Entidades Afetadas
- `estoque_movimentacoes` (INSERT saída + INSERT entrada)

#### Operações Executadas
```
1. Validar local origem e destino
2. INSERT movimentação de saída (origem)
3. INSERT movimentação de entrada (destino)
4. COMMIT
```

#### Risco se Falhar no Meio
🟡 **MÉDIO - TRANSFERÊNCIA INCOMPLETA**
- Saída registrada mas entrada não = **PERDA DE ESTOQUE**
- Entrada registrada mas saída não = **DUPLICAÇÃO**

#### Justificativa Técnica
Similar ao service de transferência (#6), mas usa movimentações ao invés de atualizar diretamente o saldo. Transaction garante que ambas as movimentações (saída + entrada) sejam criadas juntas.

---

## 🟢 FLUXOS NÃO NECESSÁRIOS (P2)

### 13. Cancelamento de Pedido de Compra (`pedidos_compra_routes.py::cancelar_pedido`)

**Arquivo:** `backend/app/pedidos_compra_routes.py`  
**Linhas:** 513-550  
**Função:** `cancelar_pedido`

#### Entidades Afetadas
- `pedidos_compra` (UPDATE status)
- `pedidos_compra_itens` (UPDATE status)

#### Operações Executadas
```
1. Buscar pedido
2. Validar status
3. UPDATE pedido.status = 'cancelado'
4. Para cada item:
   - UPDATE item.status = 'cancelado'
5. COMMIT
```

#### Risco se Falhar no Meio
🟢 **BAIXO - UPDATE SIMPLES**
- Pedido cancelado mas itens não = **NÃO CRÍTICO** (consultas podem filtrar por status do pedido)
- Pior caso: pedido fica inconsistente mas não afeta estoque/financeiro

#### Justificativa Técnica
Cancelamento de pedido é **OPERAÇÃO DE ATUALIZAÇÃO DE STATUS** que não afeta diretamente estoque ou financeiro. Se falhar, pode ser reexecutado manualmente. Transaction não é obrigatória mas recomendável para consistência.

**Decisão:** NÃO NECESSÁRIO para transaction explícita (SQLAlchemy já gerencia).

---

## 📋 ORDEM SUGERIDA DE IMPLEMENTAÇÃO

### Sprint 1 (Semana 1) - Operações Financeiras Críticas
1. ✅ **Exclusão de Venda** (`vendas_routes.py::excluir_venda`)
2. ✅ **Cancelamento de Venda** (`vendas/service.py::cancelar_venda`)
3. ✅ **Estorno de Comissões** (`comissoes_estorno.py::estornar_comissoes_venda`)

**Justificativa:** Fluxos que **REMOVEM/CANCELAM** dados devem ser priorizados pois têm maior risco de inconsistência se falharem parcialmente.

---

### Sprint 2 (Semana 2) - Operações de Criação Financeira
4. ✅ **Provisão de Comissões** (`comissoes_provisao.py::provisionar_comissoes_venda`)
5. ✅ **Geração de Comissões** (`comissoes_service.py::gerar_comissoes_venda`)
6. ✅ **Criação de Venda** (`vendas/service.py::criar_venda`)

**Justificativa:** Fluxos que **CRIAM PASSIVOS FINANCEIROS** (comissões, contas a pagar) devem ser atômicos para garantir contabilidade correta.

---

### Sprint 3 (Semana 3) - Operações de Estoque e Configuração
7. ✅ **Transferência de Estoque** (`estoque_transferencia_service.py::transferir`)
8. ✅ **Upload Nota Fiscal** (`notas_entrada_routes.py::upload_xml`)
9. ✅ **Config Batch Comissões** (`comissoes_routes.py::salvar_batch_configuracoes`)

**Justificativa:** Operações de estoque e configuração têm impacto operacional mas não são críticas para fechamento financeiro.

---

### Sprint 4 (Opcional) - Melhorias de Consistência
10. ⚠️ **Recorrência Contas** (`contas_receber_routes.py::processar_recorrencias`)
11. ⚠️ **Baixa de Kit** (`estoque_routes.py::dar_baixa_kit`)
12. ⚠️ **Transferência Estoque (Rota)** (`estoque_routes.py::transferir_estoque`)

**Justificativa:** Fluxos recomendados mas não críticos. Podem ser implementados após os P0.

---

## 🔍 CRITÉRIOS DE CLASSIFICAÇÃO

### 🔴 OBRIGATÓRIO (P0)
- Envolve múltiplas tabelas financeiras (vendas, pagamentos, caixa, contas)
- Falha parcial causa **PERDA DE DINHEIRO** ou **INCONSISTÊNCIA CONTÁBIL**
- Operações dependentes que devem ser **ALL or NOTHING**
- Afeta relatórios oficiais (DRE, Balanço)
- Envolve estoque com risco de perda real

### 🟡 RECOMENDADO (P1)
- Envolve múltiplas tabelas operacionais
- Falha parcial causa **INCONSISTÊNCIA DE DADOS** mas não perda financeira imediata
- Pode ser corrigido manualmente mas com esforço significativo
- Afeta relatórios gerenciais mas não oficiais

### 🟢 NÃO NECESSÁRIO (P2)
- Atualização de status simples
- Operações que podem ser reexecutadas sem risco
- Não afeta diretamente financeiro ou estoque
- SQLAlchemy já gerencia adequadamente

---

## ⚠️ NOTAS IMPORTANTES

### 1. Commits Manuais Existentes
Muitos fluxos já possuem `db.commit()` manual. Estes commits devem ser **REMOVIDOS** quando a transaction explícita for implementada, pois o context manager `transactional_session` já faz o commit automaticamente.

### 2. Nested Transactions
Alguns fluxos chamam outros services que também fazem commit. Será necessário refatorar para que:
- **Orquestrador (rota/service principal)** gerencia a transaction
- **Services chamados** fazem apenas `flush()`, não `commit()`

### 3. Idempotência
Fluxos como `estornar_comissoes_venda` já são idempotentes (verificam se já foram executados). Esta característica deve ser **MANTIDA** após implementar transactions.

### 4. Operações Pós-Commit
Alguns fluxos executam operações "secundárias" após commit (ex: envio de lembretes, comissões). Estas operações devem permanecer **FORA** da transaction crítica para não causar rollback por falhas não críticas.

---

## ✅ CONCLUSÃO

**Total de Fluxos Identificados:** 13  
**Obrigatórios (P0):** 9  
**Recomendados (P1):** 3  
**Não Necessários (P2):** 1  

**Estimativa de Implementação:**
- Sprint 1: 3 fluxos críticos (5-7 dias)
- Sprint 2: 3 fluxos financeiros (5-7 dias)
- Sprint 3: 3 fluxos operacionais (5-7 dias)
- Sprint 4: 3 fluxos opcionais (3-5 dias)

**Próximo Passo:** Iniciar implementação seguindo a ordem sugerida, começando pelos fluxos de exclusão e cancelamento (Sprint 1).
