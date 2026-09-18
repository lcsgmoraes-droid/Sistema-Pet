---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_atendimentos

Ver [[banho_tosa_agendamentos]], [[Cliente]], [[Pet]], [[Venda]], [[ContaReceber]], [[banho_tosa_pacote_creditos]].

## Definição
Atendimento de banho/tosa em execução — hub do módulo, com controle de status (chegou → ... → pronto/entregue/cancelado/no_show) e ponto de integração com Venda, estoque e pacotes.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/operacional.py:21-79` (`BanhoTosaAtendimento`).
- Colunas: `status`, timestamps `checkin_em`/`inicio_em`/`fim_em`/`entregue_em`, snapshots `porte_snapshot`/`pelagem_snapshot`.
- ⚠️ FK fantasma: `custo_snapshot_id` (ver achado em [[banho_tosa_custos_snapshot]]).
- ✅ **Achado central de cobrança — padrão correto, diferente do módulo Veterinário**: Banho & Tosa usa o fluxo normal de Venda/PDV. `venda_id` é preenchido via `VendaService.criar_venda(...)` (`banho_tosa_vendas.py:56`), e `conta_receber_id` é apenas **sincronizado depois**, lendo as `ContaReceber` já geradas automaticamente pela Venda (`banho_tosa_fechamento.py:24-36`) — o módulo nunca instancia `ContaReceber(...)` diretamente. Exceção: se `pacote_credito_id` estiver setado, o atendimento foi pago via crédito de pacote pré-vendido e a geração de nova venda é bloqueada (`banho_tosa_vendas.py:27-31`).
- Consumo de estoque via `EstoqueService.baixar_estoque()` real (não SQL cru) — ver [[banho_tosa_insumos_usados]].

## Relacionamentos
- FKs de saída: `agendamento_id → banho_tosa_agendamentos.id` (nullable — permite atendimento avulso), `cliente_id → clientes.id`, `pet_id → pets.id`, `venda_id → vendas.id`, `conta_receber_id → contas_receber.id`, `pacote_credito_id → banho_tosa_pacote_creditos.id`, `pacote_movimento_id → banho_tosa_pacote_movimentos.id`.
- Referenciada por: [[banho_tosa_avaliacoes]], [[banho_tosa_custos_snapshot]], [[banho_tosa_etapas]], [[banho_tosa_fotos]], [[banho_tosa_insumos_usados]].

## Utilizado por
- `banho_tosa_vendas.py` (geração de venda), `banho_tosa_fechamento.py` (sincronização com contas a receber).

## Não identificado
- Nenhuma tabela fora de `banho_tosa_*` referencia este módulo — é um módulo "folha" (só consome outras entidades, nada depende dele).
