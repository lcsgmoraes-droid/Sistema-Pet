---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_medicamentos_catalogo

Ver [[vet_produtos_regulatorios]], [[vet_itens_prescricao]], [[Produto]].

## Definição
Catálogo de medicamentos por clínica (manual ou espelhado de bulas regulatórias). ⚠️ **Desconectado do catálogo de produtos/estoque** — é um mundo paralelo sem FK para `produtos`.

## Confirmado no código
- Modelo: `veterinario_models.py:168-206` (`MedicamentoCatalogo`).
- Colunas: `dose_min_mgkg`/`dose_max_mgkg`, `eh_antibiotico`, `eh_controlado` (receituário especial), `verificacao_status` (default `nao_revisado`).
- Campos espelhados de [[vet_produtos_regulatorios]] (`fonte`, `fonte_id`, `bula_url`, `publicado_em`) — ligação por convenção, sem `ForeignKey()` real.

## Relacionamentos
- Sem FK de saída real.
- Referenciada por: [[vet_itens_prescricao]]`.medicamento_catalogo_id` (nullable).

## Utilizado por
- `routes/app_vet_routes.py`, `veterinario_catalogo_routes.py` (CRUD), `veterinario_ia.py`/`veterinario_ia_routes.py` (sugestão de posologia via IA), `scripts/seed_veterinario_base.py`.

## Não identificado
- ⚠️ Nenhuma FK liga este catálogo ao catálogo de produtos/estoque ([[Produto]]) — medicamento prescrito não é o mesmo registro que produto vendável, mesmo que se refiram à mesma coisa fisicamente.
