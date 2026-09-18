---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_itens_prescricao

Ver [[vet_prescricoes]], [[vet_medicamentos_catalogo]].

## Definição
Item de linha de uma [[vet_prescricoes|prescrição]] — medicamento e posologia. ⚠️ **Puramente informativo, não consome estoque**.

## Confirmado no código
- Modelo: `veterinario_models.py:442-468` (`ItemPrescricao`).
- `medicamento_catalogo_id` nullable — item pode ser texto livre via `nome_medicamento`, sem vínculo ao catálogo.

## Relacionamentos
- FKs de saída: `prescricao_id → vet_prescricoes.id`, `medicamento_catalogo_id → vet_medicamentos_catalogo.id` (nullable).
- Sem referências de entrada.

## Utilizado por
- `veterinario_consultas_routes.py` (criação), `veterinario_relatorios_routes.py`, `veterinario_serializers.py`.

## Não identificado
- ⚠️ **Achado de integração importante**: este item NÃO consome estoque de `produtos` — nenhuma referência a `produtos.id` ou baixa de [[estoque_movimentacoes]] encontrada aqui. Diferente de [[vet_procedimentos_consulta]] (que usa `insumos` JSON) e [[vet_orcamento_itens]] (que tem FK real para `produtos.id`), a prescrição em si é desconectada do estoque — o medicamento é só "recomendado", não "dado de baixa".
