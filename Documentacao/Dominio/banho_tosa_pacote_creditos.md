---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_pacote_creditos

Ver [[banho_tosa_pacotes]], [[Cliente]], [[Pet]], [[Venda]], [[banho_tosa_pacote_movimentos]].

## Definição
Saldo de créditos de um pacote comprado por um cliente.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/pacotes.py:41-69` (`BanhoTosaPacoteCredito`).
- Colunas: `status`, `creditos_total`/`usados`/`cancelados`, `data_validade`.
- ✅ Confirma que **a compra do pacote em si passa pela Venda normal** — `venda_id` liga o crédito à venda que o originou; é só o *uso* posterior do crédito no atendimento que não gera nova cobrança (comportamento correto e consistente).

## Relacionamentos
- FKs de saída: `pacote_id → banho_tosa_pacotes.id`, `cliente_id → clientes.id`, `pet_id → pets.id` (nullable), `venda_id → vendas.id`.
- Referenciada por: [[banho_tosa_pacote_movimentos]]`.credito_id`, [[banho_tosa_atendimentos]]`.pacote_credito_id`, [[banho_tosa_recorrencias]]`.pacote_credito_id`.

## Utilizado por
- `banho_tosa_vendas.py` (bloqueio de nova venda quando pago via crédito).

## Não identificado
- Nada notável.
