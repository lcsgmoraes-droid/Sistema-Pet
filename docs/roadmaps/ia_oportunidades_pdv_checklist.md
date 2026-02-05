# Checklist Oficial — Implantação IA de Oportunidades no PDV

Este documento é a fonte oficial de execução, auditoria e validação do projeto de IA de Oportunidades no PDV do ERP Pet Shop.

**Regras de Execução:**
- Itens devem ser executados sequencialmente dentro de cada fase
- Nenhum item pode ser marcado sem validação técnica
- Multi-tenant obrigatório em todas as implementações
- PDV nunca pode depender da IA para funcionar
- Nenhuma métrica para silêncio do usuário

---

## FASE 0 — BASE E SEGURANÇA

### Validação de Pré-Requisitos

- [ ] Validar isolamento multi-tenant em todas as queries
- [ ] Confirmar testes multi-tenant passando (11/11)
- [ ] Verificar guardrails de segurança documentados
- [ ] Validar PDV funcional sem dependência de IA
- [ ] Confirmar estrutura de banco de dados para métricas

### Preparação de Ambiente

- [ ] Criar diretório de módulos IA no backend
- [ ] Definir interfaces de eventos de oportunidade
- [ ] Configurar logs estruturados para auditoria
- [ ] Estabelecer limites de timeout para chamadas IA
- [ ] Documentar contrato de API para oportunidades

---

## FASE 1 — UX DO PDV

### Ajustes de Interface

- [ ] Implementar sidebar fechada por padrão no PDV
- [ ] Implementar painel direito fechado por padrão
- [ ] Tornar painéis laterais expansíveis
- [ ] Validar foco no carrinho ao abrir PDV
- [ ] Testar performance de renderização com painéis fechados

### Botão de Oportunidades Inteligentes

- [ ] Criar componente de botão único "Oportunidades Inteligentes"
- [ ] Implementar lógica de visibilidade condicional
- [ ] Adicionar badge com contador de oportunidades (máx 3)
- [ ] Criar painel leve de oportunidades (não chat)
- [ ] Implementar CTAs: Adicionar, Ver Alternativa, Ignorar
- [ ] Validar que botão só aparece com oportunidades relevantes
- [ ] Testar integração visual com layout do PDV

---

## FASE 2 — MÉTRICAS DE OPORTUNIDADE

### Modelo de Dados

- [ ] Criar tabela/log de oportunidades com campos:
  - oportunidade_id (UUID)
  - tenant_id (obrigatório, indexado)
  - cliente_id
  - contexto (PDV)
  - tipo (cross_sell, up_sell, recorrencia)
  - produto_origem_id
  - produto_sugerido_id
  - timestamp
  - metadados (JSON)
- [ ] Criar índices para queries de performance
- [ ] Validar isolamento de dados por tenant_id
- [ ] Implementar migration com rollback

### Sistema de Eventos

- [ ] Implementar evento: oportunidade_convertida
- [ ] Implementar evento: oportunidade_refinada
- [ ] Implementar evento: oportunidade_rejeitada
- [ ] Criar serviço de registro de eventos com tenant_id
- [ ] Validar que silêncio do usuário não gera métrica
- [ ] Implementar timestamps precisos nos eventos
- [ ] Criar endpoint de consulta de métricas por tenant

### Validação de Métricas

- [ ] Testar query: "Quantas oportunidades foram convertidas hoje?"
- [ ] Testar query: "Qual a taxa de conversão por tipo de oportunidade?"
- [ ] Testar query: "Quanto a IA vendeu no último mês?"
- [ ] Validar isolamento de métricas entre tenants
- [ ] Documentar estrutura de relatórios

---

## FASE 3 — IA EM BACKGROUND

### Processamento Passivo

- [ ] Implementar listener de evento: cliente selecionado
- [ ] Implementar listener de evento: produto adicionado
- [ ] Implementar listener de evento: produto removido
- [ ] Criar fila de processamento assíncrono por tenant_id
- [ ] Implementar timeout de 3 segundos para análise IA
- [ ] Garantir que falha da IA não afeta PDV
- [ ] Validar que nenhuma sugestão aparece automaticamente

### Backend de Oportunidades

- [ ] Criar serviço de análise de contexto de venda
- [ ] Implementar regras de cross-sell baseadas em histórico
- [ ] Implementar regras de up-sell baseadas em margem
- [ ] Implementar detecção de recorrência de compra
- [ ] Criar cache de oportunidades por sessão de venda
- [ ] Validar isolamento de dados por tenant_id
- [ ] Implementar fallback para regras estáticas

### Chat IA (Interface)

- [ ] Criar botão de expansão do chat no PDV
- [ ] Implementar carregamento de contexto ao abrir chat
- [ ] Exibir insights pré-calculados no primeiro load
- [ ] Implementar interface de consulta livre
- [ ] Adicionar capacidade de comparação de produtos
- [ ] Adicionar consulta de histórico do cliente
- [ ] Validar que chat não bloqueia operações do PDV

---

## FASE 4 — CALCULADORA DE RAÇÃO

### Componente Global

- [ ] Criar botão flutuante global acessível em todo sistema
- [ ] Implementar modal de calculadora
- [ ] Adicionar funcionalidade de minimizar modal
- [ ] Persistir estado minimizado na sessão
- [ ] Validar comportamento em diferentes telas

### Lógica de Cálculo

- [ ] Implementar cálculo de custo-benefício por ração
- [ ] Criar comparação automática entre rações da mesma linha
- [ ] Adicionar cálculo de duração estimada
- [ ] Implementar ajuste por peso do pet
- [ ] Validar fórmulas com especialista
- [ ] Adicionar tooltips explicativos

### Integração com PDV

- [ ] Detectar adição de ração no carrinho
- [ ] Abrir modal automaticamente com cálculo pré-carregado
- [ ] Preencher dados do produto automaticamente
- [ ] Permitir comparação via chat
- [ ] Permitir ajuste manual na calculadora
- [ ] Implementar botão de adicionar outra opção ao carrinho
- [ ] Validar tenant_id em todas as queries de produtos

---

## FASE 5 — APRENDIZADO E EVOLUÇÃO

### Relatórios de Performance

- [ ] Criar relatório: Receita gerada por oportunidades (por tenant)
- [ ] Criar relatório: Taxa de conversão por tipo
- [ ] Criar relatório: Top 10 produtos mais aceitos
- [ ] Criar relatório: Top 10 produtos mais ignorados
- [ ] Criar relatório: Performance do assistente por operador
- [ ] Implementar filtros por período
- [ ] Implementar exportação de dados (CSV/Excel)
- [ ] Validar isolamento de dados entre tenants

### Análise e Otimização

- [ ] Criar dashboard de métricas da IA
- [ ] Implementar alertas de performance degradada
- [ ] Identificar padrões de rejeição de sugestões
- [ ] Ajustar pesos de regras baseado em conversão
- [ ] Documentar evolução de performance ao longo do tempo
- [ ] Criar processo de revisão mensal de métricas

### Feedback Loop (Preparação)

- [ ] Estruturar dados para treinamento futuro
- [ ] Documentar casos de sucesso e falha
- [ ] Criar base de conhecimento de produtos
- [ ] Preparar pipeline de refinamento de regras
- [ ] Definir critérios de A/B testing
- [ ] Documentar roadmap para IA generativa

---

## VALIDAÇÃO FINAL

### Critérios de Aceite do Projeto

- [ ] PDV funciona 100% sem IA disponível
- [ ] Todas as queries incluem tenant_id
- [ ] Nenhuma métrica registrada para silêncio
- [ ] Taxa de resposta da IA < 2 segundos (p95)
- [ ] Zero vazamento de dados entre tenants
- [ ] Documentação técnica completa
- [ ] Testes de integração cobrindo fluxos principais
- [ ] Rollback plan documentado e testado

### Auditoria de Segurança

- [ ] Revisar todos os endpoints com tenant_id
- [ ] Validar permissões de acesso aos dados de IA
- [ ] Testar isolamento em ambiente de produção
- [ ] Revisar logs para detecção de anomalias
- [ ] Documentar política de retenção de dados
- [ ] Validar conformidade com LGPD

---

**Data de Criação:** 2026-01-27  
**Versão:** 1.0  
**Responsável:** Equipe de Desenvolvimento

**Regra Final:** Nada entra no PDV se não deixar o caixa mais rápido ou vender mais.
