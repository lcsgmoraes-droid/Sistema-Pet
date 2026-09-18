---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_config_fiscal

Ver [[Produto]], [[variacao_config_fiscal]], [[empresa_config_fiscal]].

## Definição
Config fiscal específica de um produto (1:1), 2º nível da cadeia de resolução fiscal do PDV (`KitConfigFiscal → VariacaoConfigFiscal → ProdutoConfigFiscal → EmpresaConfigFiscal`).

## Confirmado no código
- Modelo: `produto_config_fiscal_models.py:17-64` (`ProdutoConfigFiscal`). Docstring própria confirma que é a "definição ORM canônica e ÚNICA" — a cópia que existia em `fiscal_models/produto_config_fiscal.py` **já foi removida** (diferente do caso ainda-não-resolvido de [[fiscal_catalogo_produtos]]/[[fiscal_estado_padrao]]).
- Colunas: `herdado_da_empresa` (bool), `ncm`, `cest`, `origem_mercadoria`, `cst_icms`/`icms_aliquota`/`icms_st`, `cfop_venda`/`cfop_compra`, `pis_cst`/`pis_aliquota`, `cofins_cst`/`cofins_aliquota`, `observacao_fiscal`.

## Relacionamentos
- FK de saída: `produto_id → produtos.id` (unique — 1:1 produto↔config fiscal).
- Referenciada por: [[variacao_config_fiscal]]`.produto_config_fiscal_id` (nullable).

## Utilizado por
- 2º nível da cadeia: `services/pdv_fiscal_resolver.py`.
- CRUD: `api/v1/produto_fiscal_v2.py`.
- Sincronização com Bling: `bling_integration_fiscal.py` (busca/aplica NCM ao integrar produto).
- Merge de produtos duplicados: `services/produto_merge_service.py` (copia config fiscal).
- `services/produto_fiscal_apply_service.py` (aplicação de sugestão fiscal).

## Não identificado
- Nada notável — exemplo de duplicação já corrigida pelo próprio time (bom padrão de referência).
