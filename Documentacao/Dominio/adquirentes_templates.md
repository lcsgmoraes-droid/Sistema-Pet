---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — adquirentes_templates

Ver [[templates_adquirentes]], [[conciliacao_importacoes]], [[operadoras_cartao]].

## Definição
Template de importação de planilha de uma adquirente de cartão específica (Stone, Cielo, Rede...) — módulo de conciliação de **cartões (Fase 1)**.

## Confirmado no código
- Modelo: `conciliacao_models.py:129-195` (`AdquirenteTemplate`).
- Colunas: `nome` (Stone/Cielo/Rede...), `tipo_arquivo`, `separador`/`encoding`/`tem_header`/`pular_linhas` (parser CSV), `mapeamento`/`transformacoes` (JSONB).

## Relacionamentos
- FK de saída: `criado_por_id → users.id` (SET NULL).
- Referenciada por: [[conciliacao_importacoes]]`.adquirente_template_id`, `operadoras_cartao.template_id` (só existe no modelo órfão `operadoras_cartao_models.py` — ver [[operadoras_cartao]] para o achado de dead code).

## Utilizado por
- `admin_routes.py`, `conciliacao_helpers.py`, `conciliacao_routes.py`, `conciliacao_services_importacao.py`, `conciliacao_services_stone.py`.

## Não identificado
- ⚠️ **Ambiguidade de nomenclatura importante**: NÃO confundir com [[templates_adquirentes]] (`TemplateAdquirente`, `financeiro/models_conciliacao.py`) — nomes quase espelhados, tabelas e módulos de conciliação diferentes (cartões Fase 1 vs. bancária genérica).
