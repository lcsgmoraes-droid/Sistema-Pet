# PDV Assistant - IA Contextual para Ponto de Venda

Sistema de IA que analisa o contexto de uma venda em andamento no PDV e gera **sugestões inteligentes em tempo real** para o operador.

## 🎯 Objetivo

**IA como ASSISTENTE, não como AUTOMAÇÃO.**

O PDV Assistant:
- ✅ Analisa contexto da venda EM ANDAMENTO
- ✅ Consome Insights + Read Models
- ✅ Gera SUGESTÕES para o operador
- ❌ NÃO executa ações
- ❌ NÃO fala com o cliente
- ❌ NÃO altera regras de negócio

## 📦 Componentes

### 1. `models.py` - Estruturas de Dados

**PDVContext**
- Contexto completo da venda em andamento
- Itens adicionados
- Cliente (opcional)
- Vendedor
- Total parcial
- Metadata

**ItemVendaPDV**
- Representa um produto na venda
- Quantidade, valores, categoria, etc.

**PDVSugestao**
- Sugestão gerada pela IA
- Tipo, prioridade, mensagem
- Acionável ou informativa
- Confiança e dados contextuais

**Enums:**
- `TipoPDVSugestao`: Cross-sell, Kit, Cliente VIP, etc.
- `PrioridadeSugestao`: Alta, Média, Baixa

### 2. `selector.py` - PDVInsightSelector

**Responsabilidades:**
- Filtra insights relevantes ao contexto do PDV
- Prioriza por severidade e relevância
- Limita quantidade (máximo 3 sugestões)
- Remove insights não aplicáveis

**Lógica de Filtragem:**
- Insights de cliente requerem cliente identificado
- Insights de produtos requerem produtos na venda
- Filtra por tenant
- Considera recência dos insights

### 3. `prompts.py` - PDVPromptLibrary

**Características:**
- Linguagem curta e direta
- Tom de apoio (não imperativo)
- Sem termos técnicos
- Máximo 150-200 caracteres
- Foco em ação imediata

**Tipos de Prompts:**
- Cross-sell
- Kit vantajoso
- Cliente recorrente
- Cliente inativo
- Cliente VIP
- Recompra prevista
- Estoque crítico

### 4. `service.py` - PDVAIService

**Fluxo Principal:**

```python
async def sugerir_para_pdv(pdv_context: PDVContext) -> List[PDVSugestao]:
    1. Validar contexto
    2. Buscar insights disponíveis (últimos 30 dias)
    3. Selecionar insights relevantes (via PDVInsightSelector)
    4. Converter insights em sugestões
    5. Ordenar por prioridade
    6. Retornar lista de sugestões
```

**Características:**
- Multi-tenant obrigatório
- Logging completo
- Tratamento de erros
- Máximo 3 sugestões
- Sem persistência

### 5. `examples.py` - Exemplos Funcionais

**Cenários Demonstrados:**
1. Venda Simples (1 produto)
2. Cliente Recorrente
3. Oportunidade de Kit
4. Cross-sell
5. Cliente VIP
6. Venda Vazia (início)

## 🚀 Como Usar

### Uso Básico

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.ai.pdv_assistant import PDVContext, ItemVendaPDV, PDVAIService

# 1. Criar contexto da venda
pdv_context = PDVContext(
    tenant_id=1,
    timestamp=datetime.now(),
    itens=[
        ItemVendaPDV(
            produto_id=101,
            nome_produto="Ração Premium 15kg",
            quantidade=1,
            valor_unitario=Decimal("159.90"),
            valor_total=Decimal("159.90"),
            categoria="Alimentação"
        )
    ],
    total_parcial=Decimal("159.90"),
    vendedor_id=1,
    vendedor_nome="João Silva",
    cliente_id=50,  # Opcional
    cliente_nome="Maria Oliveira"  # Opcional
)

# 2. Criar serviço
service = PDVAIService(db=db_session, use_mock=True)

# 3. Gerar sugestões
sugestoes = await service.sugerir_para_pdv(pdv_context)

# 4. Usar sugestões
for sugestao in sugestoes:
    print(f"[{sugestao.prioridade.value}] {sugestao.mensagem}")
    if sugestao.acao_sugerida:
        print(f"  → {sugestao.acao_sugerida}")
```

### Executar Exemplos

```bash
# Exemplo direto (sem banco)
python -m app.ai.pdv_assistant.examples

# Com banco de dados (ajustar conforme necessário)
# Ver examples.py para detalhes
```

## 📊 Tipos de Sugestões

### 1. Cross-sell
**Quando:** Produto na venda costuma ser comprado junto com outro  
**Exemplo:** _"Antipulgas costuma ser comprado junto com Shampoo."_  
**Ação:** Oferecer produto complementar

### 2. Kit Vantajoso
**Quando:** Produtos na venda fazem parte de um kit  
**Exemplo:** _"Kit Premium sai 12% mais barato que os itens separados."_  
**Ação:** Sugerir kit ao cliente

### 3. Cliente Recorrente
**Quando:** Cliente identificado com padrão de compra  
**Exemplo:** _"Cliente costuma comprar a cada 30 dias."_  
**Ação:** Informativa

### 4. Cliente Inativo
**Quando:** Cliente há muito tempo sem comprar  
**Exemplo:** _"Cliente está há 65 dias sem comprar."_  
**Ação:** Oferecer promoção especial

### 5. Cliente VIP
**Quando:** Cliente de alto valor  
**Exemplo:** _"Cliente VIP - 50 compras realizadas."_  
**Ação:** Oferecer atendimento premium

### 6. Produto Popular
**Quando:** Produto está entre os mais vendidos  
**Exemplo:** _"Este produto está em alta nas vendas."_  
**Ação:** Destacar popularidade

### 7. Estoque Crítico
**Quando:** Produto com estoque baixo  
**Exemplo:** _"Estoque: apenas 5 unidades disponíveis."_  
**Ação:** Informativa

## 🔒 Regras de Segurança

### O que a IA NUNCA faz:
- ❌ Executar ações automaticamente
- ❌ Alterar valores da venda
- ❌ Criar descontos sem aprovação
- ❌ Modificar estoque
- ❌ Falar diretamente com o cliente
- ❌ Tomar decisões de negócio

### O que a IA FAZ:
- ✅ Sugere ações para o operador
- ✅ Fornece informações contextuais
- ✅ Destaca oportunidades
- ✅ Alerta sobre padrões relevantes

## 🏗️ Arquitetura

```
PDVContext (input)
    ↓
PDVAIService
    ↓
1. Buscar Insights (InsightService)
    ↓
2. Selecionar Relevantes (PDVInsightSelector)
    ↓
3. Converter em Sugestões
    ↓
4. Ordenar por Prioridade
    ↓
List[PDVSugestao] (output)
```

### Dependências
- `app.insights` - Insights determinísticos (Sprint 5)
- `app.ai.engine` - AI Engine base (Sprint 6, Passo 1)
- `app.ai.contracts` - Contratos de IA

### Multi-Tenancy
- ✅ Todos os métodos validam tenant_id
- ✅ Insights filtrados por tenant
- ✅ Contexto sempre contém tenant_id

## 📈 Métricas e Logging

O serviço loga automaticamente:
- Quantidade de insights disponíveis
- Insights selecionados
- Sugestões geradas
- Erros e exceções

```python
logger.info(
    f"[PDVAIService] Gerando sugestões para PDV "
    f"(tenant={pdv_context.tenant_id}, "
    f"vendedor={pdv_context.vendedor_nome}, "
    f"itens={pdv_context.quantidade_itens})"
)
```

## 🔄 Próximos Passos (Futuro)

**Este passo NÃO inclui:**
- Endpoints FastAPI
- Integração com frontend
- Persistência de sugestões
- Feedback do usuário
- Aprendizado de máquina

**Esses recursos serão implementados em passos futuros.**

## ✅ Checklist de Implementação

- [x] Estrutura do módulo `pdv_assistant/`
- [x] `models.py` - PDVContext e PDVSugestao
- [x] `selector.py` - PDVInsightSelector
- [x] `prompts.py` - Biblioteca de prompts
- [x] `service.py` - PDVAIService
- [x] `examples.py` - Exemplos funcionais
- [x] Documentação (README.md)

## 📝 Exemplos de Saída

### Exemplo 1: Venda com Cliente VIP

**Input:**
- Cliente: Roberto Santos (VIP)
- Produto: Ração Super Premium (R$ 599.80)

**Output:**
```
[ALTA] Cliente VIP
Cliente VIP - 50 compras realizadas.
→ Oferecer atendimento premium
Confiança: 90%
```

### Exemplo 2: Oportunidade de Kit

**Input:**
- Produtos: Ração Premium + Shampoo Antipulgas

**Output:**
```
[ALTA] Kit Mais Vantajoso
Kit Higiene Completa sai 12% mais barato que os itens separados.
→ Sugerir kit ao cliente
Confiança: 85%
```

### Exemplo 3: Cross-sell

**Input:**
- Produto: Shampoo Antipulgas

**Output:**
```
[MEDIA] Cross-sell
Antipulgas em spray costuma ser comprado junto com este produto.
→ Oferecer produto complementar
Confiança: 80%
```

## 🎓 Conceitos-chave

### Assistência vs. Automação
Este sistema é de **assistência inteligente**, não automação:
- Humano SEMPRE toma a decisão final
- IA apenas fornece informação contextual
- Transparência total sobre fonte dos dados

### Contextualização
As sugestões são baseadas em:
- Produtos já adicionados à venda
- Cliente identificado (se houver)
- Insights determinísticos existentes
- Read Models atualizados
- Padrões históricos

### Simplicidade
- Código simples e auditável
- Classes pequenas e focadas
- Métodos explícitos
- Fácil de plugar no frontend

---

**Desenvolvido como parte do Sprint 6 - Passo 3**  
**Sistema Pet Shop - ERP com IA Integrada**
