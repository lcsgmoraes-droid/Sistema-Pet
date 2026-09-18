---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_protocolos_vacinas

Ver [[vet_vacinas_registros]].

## Definição
Protocolo de vacinação configurável por clínica (ex.: V10, Antirrábica), com intervalo entre doses e reforço.

## Confirmado no código
- Modelo: `veterinario_models.py:214-226` (`ProtocoloVacina`).
- Colunas: `intervalo_doses_dias`, `numero_doses_serie`, `reforco_anual`.

## Relacionamentos
- Referenciada por: [[vet_vacinas_registros]]`.protocolo_id` (nullable).

## Utilizado por
- `veterinario_catalogo_routes.py` (CRUD), `veterinario_clinico.py`, `veterinario_preventivo.py` (cálculo de próximas doses/lembretes preventivos).

## Não identificado
- Nada notável.
