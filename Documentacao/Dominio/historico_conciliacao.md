---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — historico_conciliacao

Ver [[conciliacao_recebimentos]], [[conciliacao_metricas]].

## Definição
1 registro = 1 execução completa de conciliação de recebimento (3 abas: OFX, pagamentos, recebimentos).

## Confirmado no código
- Modelo: `conciliacao_recebimento_models.py:285-408` (`HistoricoConciliacao`).
- Colunas: `status` (em_andamento/concluida/reprocessada/cancelada), flags `aba1_concluida`/`aba2_concluida`/`aba3_concluida` + timestamps próprios, `arquivos_processados`/`totais` (JSONB), `taxa_amarracao`.
- Sem FK (nenhum `ForeignKey` na classe).

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `conciliacao_abas_routes.py`, `conciliacao_historico_routes.py`.

## Não identificado
- Nada notável.
