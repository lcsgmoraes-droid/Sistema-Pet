---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — lancamentos_importados

Ver [[padroes_categorizacao_ia]], [[categorias_financeiras]], [[ContaPagar]], [[ContaReceber]], [[lancamentos_manuais]].

## Definição
Lançamento importado de extrato bancário, com sugestão de categorização por IA e fluxo de validação (pendente/aprovado/editado/rejeitado).

## Confirmado no código
- Modelo: `ia/aba7_extrato_models.py:94-168` (`LancamentoImportado`). O modelo mais rico em FKs deste submódulo.
- Colunas: `status_validacao` (pendente/aprovado/editado/rejeitado).
- Relationship com `User` comentada/desabilitada.

## Relacionamentos
- FKs de saída (todas conferidas contra tabelas reais): `categoria_financeira_id → categorias_financeiras.id`, `padrao_sugerido_id → padroes_categorizacao_ia.id`, `categoria_usuario_id → categorias_financeiras.id`, `conta_pagar_id → contas_pagar.id`, `conta_receber_id → contas_receber.id` (SET NULL), `lancamento_manual_id → lancamentos_manuais.id`.

## Utilizado por
- Pipeline de importação de extrato bancário com IA.

## Não identificado
- Nada notável — FKs corretamente formadas, ao contrário de vários outros modelos deste bloco.
