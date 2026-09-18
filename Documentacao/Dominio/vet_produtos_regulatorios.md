---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_produtos_regulatorios

Ver [[vet_medicamentos_catalogo]].

## Definição
Catálogo regulatório oficial (bulas ANVISA/FDA etc.), **global** (não tenant-scoped) — compartilhado entre todos os tenants.

## Confirmado no código
- Modelo: `veterinario_models.py:30-69` (`ProdutoRegulatorioVet`). `Base` puro (sem `tenant_id`).
- Colunas: `fonte`/`fonte_id` (unique juntos), `jurisdicao`, `status_regulatorio`, `nome`, `principio_ativo`, `fabricante`, `especies_indicadas` (JSON), `bula_url`, `conteudo_bula` (JSON), `ativo`.

## Relacionamentos
- Sem FK de saída.
- Sem FK de entrada real — [[vet_medicamentos_catalogo]] só copia campos espelhados (`fonte`, `fonte_id`, `bula_url`) por convenção, sem `ForeignKey()` real ligando as duas tabelas.

## Utilizado por
- `services/vet_regulatory_catalog_import.py` (importação/sync de bulas), `veterinario_catalogo_routes.py` (busca).

## Não identificado
- Vínculo com [[vet_medicamentos_catalogo]] é só por dado copiado, não por FK — outra instância do padrão "ligação fantasma" já visto em outros módulos.
