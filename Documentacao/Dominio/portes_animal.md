---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — portes_animal

Ver [[linhas_racao]], [[Pet]].

## Definição
Porte de animal (Pequeno, Médio, Grande, Gigante, Todos), por tenant — catálogo auxiliar para classificação de ração.

## Confirmado no código
- Modelo: `opcoes_racao_models.py:38-56` (`PorteAnimal`). Mesmo padrão de [[linhas_racao]] (`nome`, `descricao`, `ordem`, `ativo`).

## Relacionamentos
- Sem FK.

## Utilizado por
- CRUD em `opcoes_racao_routes.py` (`/opcoes-racao/portes`).

## Não identificado
- Nada notável.
