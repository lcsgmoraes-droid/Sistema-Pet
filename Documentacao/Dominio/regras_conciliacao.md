---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — regras_conciliacao

Ver [[movimentacoes_bancarias]], [[provisoes_automaticas]], [[regras_classificacao_dre]].

## Definição
Regra de aprendizado para classificação/conciliação automática de movimentações bancárias (padrão de memo → fornecedor/categoria DRE). Motor paralelo ao de [[regras_classificacao_dre]] (que classifica contas a pagar/receber, não movimentações bancárias).

## Confirmado no código
- Modelo: `financeiro/models_conciliacao.py:112-145` (`RegraConciliacao`).
- Colunas: `padrao_memo` (ex.: "%MANFRIM%"), `confianca` = (confirmada/aplicada)×100, `prioridade`, `vezes_aplicada`/`vezes_confirmada`.
- Campo `centro_custo_id` (Integer) sem FK — mesmo placeholder "futuro" de [[movimentacoes_bancarias]].

## Relacionamentos
- FKs de saída: `fornecedor_id → clientes.id`, `categoria_dre_id → dre_subcategorias.id`.
- Referenciada por: [[movimentacoes_bancarias]]`.regra_aplicada_id`, [[provisoes_automaticas]]`.regra_id`.

## Utilizado por
- `conciliacao_bancaria_routes.py`.

## Não identificado
- Nada notável além do placeholder de centro de custo.
