---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_produtos

Ver [[Produto]], [[catalogo_mestre_imagens]], [[catalogo_mestre_pendencias]].

## Definição
Produto do catálogo mestre global — deliberadamente desacoplado do cadastro operacional de produtos por tenant (comentário explícito no módulo). Ficha rica: GTIN, dados fiscais, dados veterinários (registro MAPA, princípio ativo), qualidade de imagem.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:32-122` (`CatalogoMestreProduto`).
- `origem_tenant_id`/`origem_produto_id` **não são FK** — valores soltos, com `UniqueConstraint`.
- `proveniencia`/`snapshot_origem`/`snapshot_origem_hash` (auditoria de origem, NOT NULL).
- Métricas de qualidade com `CheckConstraint`s no próprio banco.

## Relacionamentos
- Referenciada por: [[catalogo_mestre_imagens]]`.produto_id` (cascade delete-orphan), [[catalogo_mestre_pendencias]]`.produto_id`, `CatalogoMestreProdutoCandidato.produto_mestre_id` (SET NULL), `CatalogoMestreEnriquecimentoExecucao.produto_id` (SET NULL).

## Utilizado por
- `services/catalogo_mestre_service.py`, `catalogo_mestre_sync_service.py`, `catalogo_mestre_enrichment_worker.py`, `catalogo_mestre_image_import.py`, scripts `run_catalogo_mestre_sync.py`/`run_catalogo_mestre_image_import.py`.

## Não identificado
- ⚠️ **Não existe rota HTTP** para o catálogo mestre — operação 100% via scripts/serviços, sem interface administrativa.
- 🔴 O scheduler que dispararia o enriquecimento automático (`CatalogMasterScheduler`) **nunca é instanciado** em lugar nenhum — todo o pipeline só roda manualmente.
