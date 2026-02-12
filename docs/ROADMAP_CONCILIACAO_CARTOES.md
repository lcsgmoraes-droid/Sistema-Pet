# 🗓️ ROADMAP - IMPLEMENTAÇÃO CONCILIAÇÃO CARTÕES

**Baseado em:** [ARQUITETURA_CONCILIACAO_CARTOES.md](ARQUITETURA_CONCILIACAO_CARTOES.md)

---

## 📊 VISÃO GERAL

**Objetivo:** Implementar sistema completo de conciliação de cartões com validação em cascata, seguindo todos os 14 alertas de arquitetura.

**Duração Estimada:** 5 fases  
**Status:** 🟡 Planejamento concluído - Aguardando início

---

## 🎯 FASE 1: FUNDAÇÃO (Database + Models)

### **Objetivos:**
- Criar estrutura de dados
- Implementar models
- Preparar sistema de templates

### **Tasks:**

#### 1.1 Criar Tabelas SQL
```sql
-- conciliacao_importacoes
-- conciliacao_lotes
-- conciliacao_validacoes
-- conciliacao_logs
-- adquirentes_templates
-- arquivos_evidencia
```

#### 1.2 Criar Models SQLAlchemy
- `ConciliacaoImportacao`
- `ConciliacaoLote`
- `ConciliacaoValidacao`
- `ConciliacaoLog`
- `AdquirenteTemplate`
- `ArquivoEvidencia`

#### 1.3 Adicionar Campos em Tabelas Existentes
```python
# ContaReceber - adicionar:
- status_conciliacao (prevista|confirmada_operadora|aguardando_lote|em_lote|liquidada)
- taxa_mdr_estimada / taxa_mdr_real
- taxa_antecipacao_estimada / taxa_antecipacao_real
- valor_liquido_estimado / valor_liquido_real
- data_vencimento_estimada / data_vencimento_real
- conciliacao_lote_id (FK)
- versao_conciliacao (INT default 0)  # ⚠️ Rastreamento de reprocessamentos
```

#### 1.4 Migration
- Criar migration Alembic
- Testar upgrade/downgrade
- Validar constraints

**Entrega:** Database pronta + Models funcionando

---

## 🎯 FASE 2: IMPORTAÇÃO (Services + API)

### **Objetivos:**
- Implementar parsers
- Armazenar dados sem alterar financeiro
- Sistema de templates

### **Tasks:**

#### 2.1 ConciliacaoImportService
```python
class ConciliacaoImportService:
    def importar_ofx(arquivo, conta_bancaria_id):
        """
        - Parse OFX
        - Salvar em conciliacao_importacoes
        - Salvar arquivo em arquivos_evidencia
        - NÃO tocar em MovimentacaoBancaria
        - Retornar resumo
        """
    
    def importar_pagamentos(arquivo, adquirente_id, data):
        """
        - Carregar template adquirente
        - Parse CSV com template
        - Agrupar lotes
        - Salvar em conciliacao_lotes
        - Salvar arquivo evidência
        - Retornar resumo
        """
    
    def importar_recebimentos(arquivo, adquirente_id, data):
        """
        ⚠️ IMPORTANTE: Apenas ENRIQUECE dados, NÃO realiza financeiramente
        
        - Carregar template adquirente
        - Parse CSV detalhado
        - Buscar ContaReceber por NSU
        - Atualizar status → confirmada_operadora (depois aguardando_lote)
        - Atualizar taxas REAIS (estimada → real)
        - Atualizar datas REAIS (estimada → real)
        - NÃO criar Recebimento
        - NÃO tocar em FluxoCaixa
        - NÃO marcar como liquidada
        - Salvar arquivo evidência
        - Retornar resumo + alertas
        
        Realização financeira só acontece no PROCESSAMENTO
        """
```

#### 2.2 AdquirenteTemplateService
```python
class AdquirenteTemplateService:
    def carregar_template(adquirente_nome, tipo_arquivo):
        """Busca template configurado"""
    
    def parsear_csv(arquivo, template):
        """Converte CSV → dados padronizados"""
    
    def criar_template_stone():
        """Template default Stone"""
```

#### 2.3 ArquivoEvidenciaService
```python
class ArquivoEvidenciaService:
    def salvar_arquivo(arquivo, tipo, data, usuario_id):
        """
        - Gerar hash MD5
        - Salvar em storage seguro
        - Registrar metadados
        - Retornar ID
        """
    
    def recuperar_arquivo(arquivo_id):
        """Para reprocessamento"""
```

#### 2.4 Routes de Importação
```python
# backend/app/conciliacao_cartao_import_routes.py

@router.post("/importar-ofx")
async def importar_ofx_route():
    """Upload OFX → importação apenas"""

@router.post("/importar-pagamentos")
async def importar_pagamentos_route():
    """Upload pagamentos → salvar lotes"""

@router.post("/importar-recebimentos")
async def importar_recebimentos_route():
    """Upload recebimentos → atualizar taxas (sem liquidar)"""
```

**Entrega:** Sistema de importação completo (sem processamento financeiro)

---

## 🎯 FASE 3: VALIDAÇÃO (Cascata + Alertas)

### **Objetivos:**
- Validação em 3 camadas
- Sistema de alertas
- Dashboard de revisão

### **Tasks:**

#### 3.1 ConciliacaoValidacaoService
```python
class ConciliacaoValidacaoService:
    def validar_cascata(data, ofx_id, pagamentos_id, recebimentos_id):
        """
        Camada 1: OFX vs Pagamentos
        Camada 2: Pagamentos vs Recebimentos
        Camada 3: Recebimentos vs ContaReceber
        
        Retorna:
        {
            "confianca": "ALTA|MEDIA|BAIXA",
            "pode_processar": true|false,
            "totais": {...},
            "diferencas": {...},
            "alertas": [...]
        }
        """
    
    def calcular_diferencas(total1, total2, limite_tolerancia=0.10):
        """Calcula diferença e classifica gravidade"""
    
    def gerar_alertas(validacao):
        """
        - NSUs órfãos (no arquivo mas não no sistema)
        - NSUs faltando (no sistema mas não no arquivo)
        - Divergências de valor
        - Divergências de taxa
        - Antecipações não previstas
        """
```

#### 3.2 Route de Validação
```python
@router.post("/validar-conciliacao")
async def validar_conciliacao_route(
    data: date,
    ofx_id: int,
    pagamentos_id: int = None,
    recebimentos_id: int = None
):
    """
    Executa validação completa
    Retorna dashboard de revisão
    Usuário vê TUDO antes de processar
    """
```

#### 3.3 Dashboard de Revisão (Backend Response)
```json
{
    "data": "2026-02-10",
    "status_geral": "concluida",
    "confianca": "ALTA",
    
    "totais": {
        "ofx": 1820.00,
        "pagamentos": 1820.00,
        "recebimentos": 1820.01
    },
    
    "validacoes": {
        "ofx_vs_pagamentos": {
            "diferenca": 0.00,
            "percentual": 0.00,
            "status": "OK"
        },
        "pagamentos_vs_recebimentos": {
            "diferenca": 0.01,
            "percentual": 0.0005,
            "status": "OK_TOLERANCIA"
        }
    },
    
    "parcelas": {
        "total": 26,
        "confirmadas": 26,
        "em_lote": 26,
        "orfas": 0
    },
    
    "lotes": {
        "total": 16,
        "conciliados": 16,
        "divergentes": 0
    },
    
    "alertas": [
        {
            "tipo": "info",
            "mensagem": "Diferença de R$ 0,01 entre totais - dentro da tolerância"
        }
    ],
    
    "pode_processar": true,
    "requer_confirmacao": false
}
```

**Entrega:** Sistema de validação + Dashboard de revisão

---

## 🎯 FASE 4: PROCESSAMENTO (Liquidação + Cascata)

### **Objetivos:**
- Liquidar contas
- Atualizar subsistemas
- Log completo

### **Tasks:**

#### 4.1 ConciliacaoProcessamentoService
```python
class ConciliacaoProcessamentoService:
    def processar_conciliacao(
        conciliacao_id,
        usuario_id,
        confirmacao_manual=False
    ):
        """
        Executa processamento financeiro APENAS após validação
        
        1. Verifica se validação foi aprovada
        2. Liquida parcelas (ContaReceber)
        3. Marca lotes como creditados
        4. Cria MovimentacaoBancaria (se OFX presente)
        5. Atualiza FluxoCaixa
        6. Atualiza DRE Caixa
        7. Recalcula indicadores
        8. Gera log completo
        9. Notifica usuário
        
        Tudo em transação - rollback se falhar
        """
    
    def liquidar_parcelas(parcelas_ids, data_liquidacao):
        """
        - Atualizar status → liquidada
        - Registrar data_liquidacao
        - Criar Recebimento
        """
    
    def atualizar_fluxo_caixa(data, valor, descricao):
        """Registra entrada no fluxo"""
    
    def atualizar_dre_caixa(data, valor):
        """Atualiza receita realizada"""
    
    def gerar_log_processamento(conciliacao_id, detalhes):
        """Log completo para auditoria"""
```

#### 4.2 Route de Processamento
```python
@router.post("/processar-conciliacao")
async def processar_conciliacao_route(
    conciliacao_id: int,
    confirmacao: bool = False
):
    """
    ENDPOINT CRÍTICO
    
    - Requer validação prévia
    - Requer confirmação se divergências
    - Executa em transação
    - Retorna resultado completo
    """
```

#### 4.3 Sistema de Notificações
```python
# Notificar usuário após processamento
{
    "titulo": "Conciliação processada com sucesso",
    "mensagem": "26 parcelas liquidadas - R$ 1.820,00",
    "tipo": "success",
    "acao": {
        "texto": "Ver detalhes",
        "link": "/conciliacao-cartoes/historico/123"
    }
}
```

**Entrega:** Sistema de processamento completo + Logs

---

## 🎯 FASE 5: REVERSÃO + FRONTEND

### **Objetivos:**
- Permitir desfazer conciliação
- Interface completa
- Histórico

### **Tasks:**

#### 5.1 ConciliacaoReversaoService
```python
class ConciliacaoReversaoService:
    def reverter_conciliacao(conciliacao_id, usuario_id, motivo):
        """
        REVERSÃO COMPLETA
        
        1. Verifica se pode reverter
        2. Retorna parcelas para "prevista"
        3. Remove vínculos com lotes
        4. Remove MovimentacaoBancaria vinculada
        5. Reverte FluxoCaixa
        6. Reverte DRE Caixa
        7. MANTÉM arquivos originais (evidência)
        8. Gera log de reversão
        9. Marca conciliacao como "revertida"
        
        Tudo em transação
        """
    
    def pode_reverter(conciliacao_id):
        """
        Verifica se:
        - Conciliação existe
        - Não foi revertida antes
        - Não tem dependências críticas
        """
```

#### 5.2 Frontend - ConciliacaoCartoes.jsx
```jsx
// Página principal
<ConciliacaoCartoes>
  <TopBar>
    <SeletorAdquirente />
    <SeletorData />
  </TopBar>
  
  <UploadSection>
    <UploadOFX />
    <UploadPagamentos />
    <UploadRecebimentos />
  </UploadSection>
  
  <DashboardValidacao>
    <ResumoTotais />
    <GraficoValidacao />
    <ListaAlertasPendentes />
  </DashboardValidacao>
  
  <BotaoProcessar disabled={!validacaoOK} />
  
  <HistoricoConciliacoes />
</ConciliacaoCartoes>
```

#### 5.3 Componentes Detalhados
- `UploadComValidacao.jsx` - Upload + preview
- `DashboardCascata.jsx` - Visualização 3 camadas
- `TabelaParcelas.jsx` - Lista parcelas com status
- `ModalConfirmacao.jsx` - Confirmação processamento
- `HistoricoReversoes.jsx` - Log de reversões

#### 5.4 Routes Frontend
```javascript
/conciliacao-cartoes
/conciliacao-cartoes/importar
/conciliacao-cartoes/validar/:id
/conciliacao-cartoes/historico
/conciliacao-cartoes/historico/:id
/conciliacao-cartoes/templates
```

**Entrega:** Sistema completo funcional + Interface

---

## 📈 CRONOGRAMA ESTIMADO

| Fase | Descrição | Duração Idealizada | Duração Realista | Status |
|------|-----------|-------------------|------------------|--------|
| 1 | Fundação (DB + Models) | 2-3h | 4-8h | 🔴 Pendente |
| 2 | Importação (Services) | 4-5h | 10-15h | 🔴 Pendente |
| 3 | Validação (Cascata) | 3-4h | 6-10h | 🔴 Pendente |
| 4 | Processamento | 3-4h | 6-12h | 🔴 Pendente |
| 5 | Reversão + Frontend | 5-6h | 10-20h | 🔴 Pendente |
| **TOTAL** | | **17-22h (ideal)** | **36-65h (real)** | |

**⚠️ Nota:** Conciliação sempre tem surpresas: encoding diferente, planilhas mal formadas, NSU inexistente, duplicidades, datas erradas, estornos, cancelamentos, antecipações parciais, etc.

---

## ✅ CRITÉRIOS DE ACEITE

### Fase 1
- [ ] Tabelas criadas no banco
- [ ] Models funcionando
- [ ] Migration testada
- [ ] Campos adicionados em ContaReceber

### Fase 2
- [ ] OFX importado corretamente
- [ ] Pagamentos parseados com template
- [ ] Recebimentos vinculados a ContaReceber
- [ ] Arquivos salvos como evidência
- [ ] NÃO alterou financeiro

### Fase 3
- [ ] Validação em cascata funcionando
- [ ] Alertas gerados corretamente
- [ ] Dashboard de revisão completo
- [ ] Diferenças calculadas com precisão

### Fase 4
- [ ] Liquidação de parcelas OK
- [ ] FluxoCaixa atualizado
- [ ] DRE Caixa atualizada
- [ ] Log completo gerado
- [ ] Rollback funciona em caso de erro

### Fase 5
- [ ] Reversão completa funcional
- [ ] Evidências preservadas
- [ ] Interface completa
- [ ] Histórico funcionando
- [ ] Templates configuráveis

---

## 🎯 PRÓXIMO PASSO IMEDIATO

**Iniciar Fase 1:**
1. Criar arquivo de migration
2. Definir estrutura das tabelas
3. Implementar models
4. Testar localmente

**Comando para iniciar:**
```bash
cd backend
alembic revision -m "add_conciliacao_cartoes_tables"
```

---

**Documento criado em:** 11/02/2026  
**Última atualização:** 11/02/2026 10:05  
**Status:** ✅ Pronto para execução
