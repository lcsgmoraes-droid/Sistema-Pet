---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_taxi_dog

Ver [[Cliente]], [[Pet]], [[banho_tosa_agendamentos]].

## Definição
Serviço de busca e entrega (taxi dog) vinculado a um agendamento de banho/tosa.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/custos.py:52-81` (`BanhoTosaTaxiDog`).
- `motorista_id → clientes.id` — motorista modelado como [[Cliente]] (mesmo padrão de reaproveitamento de cadastro já visto no veterinário para profissionais).
- ⚠️ FK fantasma: `rota_entrega_id`, `Integer` sem `ForeignKey()`, provável referência a uma tabela de rotas de entrega do módulo de logística/vendas.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `pet_id → pets.id`, `agendamento_id → banho_tosa_agendamentos.id`, `motorista_id → clientes.id`.

## Utilizado por
- Itens de taxi dog somados na venda gerada (`banho_tosa_vendas.py:153-167`, `_itens_taxi_dog`), rotas próprias em `banho_tosa_api/taxi_routes.py`.

## Não identificado
- `rota_entrega_id` deveria ser FK real e não é.
