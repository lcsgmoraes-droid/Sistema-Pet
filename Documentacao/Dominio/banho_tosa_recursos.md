---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_recursos

Ver [[banho_tosa_agendamentos]], [[banho_tosa_etapas]].

## Definição
Recurso físico usado em banho/tosa (secador, banheira, mesa de tosa), com capacidade simultânea e custo de manutenção.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/cadastros.py:50-61` (`BanhoTosaRecurso`).
- Colunas: `nome`, `tipo`, `capacidade_simultanea`, `potencia_watts`, `custo_manutencao_hora`, `ativo`.

## Relacionamentos
- Referenciada por: [[banho_tosa_agendamentos]]`.recurso_id`, [[banho_tosa_etapas]]`.recurso_id`.

## Utilizado por
- Cadastro/agenda do módulo.

## Não identificado
- Nada notável.
