---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_servicos

Ver [[banho_tosa_agendamento_servicos]], [[banho_tosa_precos_servico]], [[banho_tosa_insumos_previstos]], [[banho_tosa_pacotes]].

## Definição
Catálogo de serviços de banho/tosa (banho, tosa, secagem etc.), com flags de composição.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/cadastros.py:64-84` (`BanhoTosaServico`).
- Colunas: `requer_banho`, `requer_tosa`, `requer_secagem`, `permite_pacote`, `categoria` (default "banho").

## Relacionamentos
- Referenciada por: [[banho_tosa_agendamento_servicos]]`.servico_id`, [[banho_tosa_precos_servico]]`.servico_id`, [[banho_tosa_insumos_previstos]]`.servico_id`, [[banho_tosa_pacotes]]`.servico_id`, [[banho_tosa_recorrencias]]`.servico_id`.

## Utilizado por
- Cadastro central do módulo.

## Não identificado
- Nada notável.
