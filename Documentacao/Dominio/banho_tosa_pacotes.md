---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_pacotes

Ver [[banho_tosa_servicos]], [[banho_tosa_pacote_creditos]].

## Definição
Catálogo de pacotes de crédito (ex.: "10 banhos"), com validade e preço.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/pacotes.py:20-38` (`BanhoTosaPacote`).
- Colunas: `quantidade_creditos`, `validade_dias`, `preco`.

## Relacionamentos
- FK de saída: `servico_id → banho_tosa_servicos.id` (nullable).
- Referenciada por: [[banho_tosa_pacote_creditos]]`.pacote_id`.

## Utilizado por
- Cadastro de pacotes do módulo.

## Não identificado
- Nada notável.
