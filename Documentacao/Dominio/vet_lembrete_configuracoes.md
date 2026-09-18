---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_lembrete_configuracoes

Ver [[Tenant]].

## Definição
Configuração (1:1 por tenant) de quando disparar lembretes de agendamento para o tutor no app (ex.: 1 dia antes / X horas antes).

## Confirmado no código
- Modelo: `veterinario_models.py:147-160` (`VeterinarioLembreteConfiguracao`). `UniqueConstraint("tenant_id", ...)`.
- Sem FKs.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `veterinario_lembrete_configuracoes.py` (get/create), `veterinario_agenda_routes_parts/cadastros_routes.py` (GET/PUT), `veterinario_clinico.py`.

## Não identificado
- Nada notável.
