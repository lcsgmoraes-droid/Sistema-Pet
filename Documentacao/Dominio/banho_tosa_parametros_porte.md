---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_parametros_porte

Ver [[banho_tosa_precos_servico]], [[banho_tosa_insumos_previstos]].

## Definição
Parâmetros de tempo/água/energia por porte do pet (P/M/G) e multiplicadores de preço por pelagem curta/longa.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/cadastros.py:87-110` (`BanhoTosaParametroPorte`).

## Relacionamentos
- Referenciada por: [[banho_tosa_precos_servico]]`.porte_id`, [[banho_tosa_insumos_previstos]]`.porte_id`.

## Utilizado por
- Cálculo de precificação e custo do módulo.

## Não identificado
- Nada notável.
