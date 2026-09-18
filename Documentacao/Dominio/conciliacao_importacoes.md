---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_importacoes

Ver [[arquivos_evidencia]], [[adquirentes_templates]], [[conciliacao_lotes]], [[conciliacao_validacoes]].

## Definição
Registro de uma importação de dados de conciliação de cartão — armazena dados, mas **não altera o financeiro** (separação deliberada entre importar e processar, conforme comentário no código).

## Confirmado no código
- Modelo: `conciliacao_models.py:280-372` (`ConciliacaoImportacao`).
- Colunas: `tipo_importacao` (ofx_creditos/pagamentos_lotes/recebimentos_detalhados), `status_importacao` (pendente/processada/erro/cancelada), `resumo` (JSONB).
- 3 relationships nomeadas para o mesmo alvo ([[conciliacao_validacoes]]) via `foreign_keys=` distintos: `validacoes_ofx`, `validacoes_pagamentos`, `validacoes_recebimentos` — reflete que `ConciliacaoValidacao` tem 3 FKs separadas apontando de volta pra cá.

## Relacionamentos
- FKs de saída: `arquivo_evidencia_id → arquivos_evidencia.id` (RESTRICT), `adquirente_template_id → adquirentes_templates.id` (RESTRICT, nullable), `criado_por_id → users.id` (RESTRICT).
- Referenciada por: [[conciliacao_lotes]]`.importacao_pagamentos_id`/`.importacao_ofx_id`, [[conciliacao_validacoes]]`.importacao_ofx_id`/`.importacao_pagamentos_id`/`.importacao_recebimentos_id`.

## Utilizado por
- `conciliacao_aba1_operacoes_routes.py`, `conciliacao_aba1_routes.py`, `conciliacao_abas_routes.py`, `conciliacao_routes.py`, `conciliacao_services_importacao.py`.

## Não identificado
- Nada notável.
