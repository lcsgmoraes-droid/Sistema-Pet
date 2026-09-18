---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — padroes_categorizacao_ia

Ver [[Usuario]], [[categorias_financeiras]], [[lancamentos_importados]].

## Definição
Padrão aprendido para categorização automática de lançamentos importados de extrato bancário.

## Confirmado no código
- Modelo: `ia/aba7_extrato_models.py:33-85` (`PadraoCategorizacaoIA`).
- Relationship com `User` está comentada/desabilitada no código.

## Relacionamentos
- FKs de saída: `usuario_id → users.id`, `categoria_financeira_id → categorias_financeiras.id` (correta).
- Referenciada por: [[lancamentos_importados]]`.padrao_sugerido_id`.

## Utilizado por
- Pipeline de importação de extrato bancário com IA.

## Não identificado
- Nada notável.
