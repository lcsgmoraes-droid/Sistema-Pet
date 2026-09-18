---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_conhecimento_fontes

Ver [[vet_conhecimento_documentos]].

## Definição
Fonte de conhecimento clínico (ex.: PubMed, diretrizes) usada para alimentar a IA clínica do módulo veterinário. Global (não tenant-scoped).

## Confirmado no código
- Modelo: `veterinario_models.py:72-93` (`FonteConhecimentoVet`). `Base` puro.
- Colunas: `codigo` (unique), `requer_revisao`, `ativo`, `ultimo_status`/`ultimo_erro` (auditoria de sync).

## Relacionamentos
- Referenciada por: [[vet_conhecimento_documentos]]`.fonte_id`.

## Utilizado por
- `services/vet_clinical_evidence.py`, `veterinario_ia_routes.py` (contexto de IA clínica).

## Não identificado
- Nada notável.
