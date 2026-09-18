---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_agendamento_servicos

Ver [[banho_tosa_agendamentos]], [[banho_tosa_servicos]].

## Definição
Item de serviço de um agendamento de banho/tosa (linha do "carrinho" do agendamento).

## Confirmado no código
- Modelo: `banho_tosa_model_parts/agenda.py:74-96` (`BanhoTosaAgendamentoServico`).
- Colunas: `nome_servico_snapshot`, `quantidade`, `valor_unitario`, `desconto`, `tempo_previsto_minutos`.

## Relacionamentos
- FKs de saída: `agendamento_id → banho_tosa_agendamentos.id` (CASCADE), `servico_id → banho_tosa_servicos.id` (nullable — permite item avulso sem catálogo).

## Utilizado por
- `banho_tosa_api/agenda_routes.py` (montagem do total do agendamento), `banho_tosa_vendas.py:113-132` (origem dos itens da Venda gerada).

## Não identificado
- Nada notável.
