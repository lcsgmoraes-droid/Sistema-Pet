---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_conhecimento_documentos

Ver [[vet_conhecimento_fontes]].

## Definição
Artigo/diretriz clínica recuperável, usado como contexto para IA clínica veterinária. Global (não tenant-scoped).

## Confirmado no código
- Modelo: `veterinario_models.py:96-144` (`DocumentoConhecimentoVet`).
- Colunas: `status_revisao` (default pendente), `hash_conteudo`.
- ⚠️ FK fantasma: `revisado_por_id` é `Integer` (nullable) sem `ForeignKey()`, apesar de semanticamente apontar para `users.id`.

## Relacionamentos
- FK de saída: `fonte_id → vet_conhecimento_fontes.id` (CASCADE).

## Utilizado por
- `services/vet_clinical_evidence.py`, `veterinario_ia_routes.py`.

## Não identificado
- `revisado_por_id` deveria ser FK real e não é.
