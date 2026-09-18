---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — templates_adquirentes

Ver [[adquirentes_templates]].

## Definição
Template para importar planilhas de diferentes adquirentes de cartão (mapeamento de colunas, parser CSV) — módulo de conciliação **bancária genérica**.

## Confirmado no código
- Modelo: `financeiro/models_conciliacao.py:175-190` (`TemplateAdquirente`).
- Colunas: `nome_adquirente`, `tipo_relatorio`, `mapeamento`/`palavras_chave`/`colunas_obrigatorias` (JSON em `Text`, não `JSONB`), `auto_aplicar`.
- Sem FKs próprias.

## Relacionamentos
- Sem FK de saída nem de entrada confirmada.

## Utilizado por
- `conciliacao_bancaria_routes.py`.

## Não identificado
- ⚠️ **Ambiguidade de nomenclatura importante**: NÃO confundir com [[adquirentes_templates]] (`AdquirenteTemplate`, `conciliacao_models.py`) — são duas classes/tabelas **diferentes**, com nomes quase espelhados (`TemplateAdquirente`→`templates_adquirentes` vs `AdquirenteTemplate`→`adquirentes_templates`), cada uma no seu próprio módulo de conciliação (bancária genérica vs. cartões/Fase 1). Fácil de confundir ao buscar no código ou na documentação.
