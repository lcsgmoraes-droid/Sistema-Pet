---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — formas_pagamento_comissoes

## Definição
⚠️ **Tabela órfã confirmada pelo próprio código-fonte.**

## Confirmado no código
- Modelo: `formas_pagamento_models.py:88-114` (`FormaPagamentoComissao`).
- Colunas: `nome` (unique), `descricao`, `ativo`. Herda `Base` puro (não `BaseTenantModel`) — tabela **global**, sem `tenant_id`, conforme comentário explícito no código (linhas 96-100).
- O cabeçalho da classe no código já se autodocumenta como órfã: `"FORMAS PAGAMENTO COMISSÕES (ÓRFÃ) — Schema baseado em RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4"` (linhas 88-91).

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- ❓ **Nenhum uso encontrado** além da criação via migração Alembic (`bda1c213cae2_base_inicial_completa.py:181-191`) e da definição do modelo. Nenhuma rota, service ou script instancia a classe ou consulta a tabela.

## Não identificado
- 🟡 Tabela sabidamente não utilizada em produção — candidata a remoção/arquivamento, conforme já sinalizado pelo próprio time no comentário do código-fonte.
