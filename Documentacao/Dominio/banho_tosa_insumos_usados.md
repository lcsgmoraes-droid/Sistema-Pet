---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_insumos_usados

Ver [[banho_tosa_atendimentos]], [[Produto]], [[estoque_movimentacoes]], [[banho_tosa_insumos_previstos]].

## Definição
Insumo efetivamente consumido num atendimento — gera baixa real de estoque.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/operacional.py:170-202` (`BanhoTosaInsumoUsado`).
- ⚠️ FKs fantasmas: `movimentacao_estoque_id` e `movimentacao_estorno_id`, `Integer` sem `ForeignKey()`, apontando para o id retornado por `EstoqueService`.
- ✅ **Consumo de estoque confirmado como correto**: `banho_tosa_api/insumos_routes.py:114` chama `baixar_estoque_insumo(...)` → `insumos_helpers.py:94-119`, que delega para `EstoqueService.baixar_estoque(motivo="banho_tosa_insumo", referencia_tipo="banho_tosa_atendimento", ...)` — uso correto do serviço de domínio real (ORM), sem SQL cru em paralelo. Há também fluxo de estorno (`estornar_estoque_insumo_registrado`).

## Relacionamentos
- FKs de saída: `atendimento_id → banho_tosa_atendimentos.id` (CASCADE), `produto_id → produtos.id`, `responsavel_id → clientes.id`.
- `movimentacao_estoque_id`/`movimentacao_estorno_id` referenciam informalmente [[estoque_movimentacoes]]`.id`.

## Utilizado por
- `banho_tosa_api/insumos_routes.py`, `insumos_helpers.py`.

## Não identificado
- `movimentacao_estoque_id`/`movimentacao_estorno_id` deveriam ser FK real e não são — único ponto fraco deste fluxo, que é por outro lado bem implementado.
