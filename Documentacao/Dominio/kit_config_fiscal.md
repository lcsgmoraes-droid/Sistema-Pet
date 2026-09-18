---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — kit_config_fiscal

Ver [[Produto]], [[produto_config_fiscal]], [[variacao_config_fiscal]], [[kit_composicao]].

## Definição
Configuração fiscal de um produto do tipo KIT — análoga a [[produto_config_fiscal]]/[[variacao_config_fiscal]]. ✅ **Caso raro de duplicação corretamente resolvida pelo próprio time.**

## Confirmado no código
- Modelo: `kit_config_fiscal_models.py:17-66` (`KitConfigFiscal`). O próprio docstring afirma ser a versão canônica única após consolidação; a cópia divergente antiga em `app/fiscal_models/kit_config_fiscal.py` **hoje não existe mais como arquivo** — `app/fiscal_models/__init__.py` apenas reexporta esta classe (`# noqa`), confirmando que a duplicação foi de fato eliminada. Contraste positivo com [[fiscal_catalogo_produtos]]/[[fiscal_estado_padrao]] (duplicações ainda ativas e não resolvidas).
- Colunas: `herdado_da_empresa` (default True), `ncm`, `cest`, `origem_mercadoria`, `cst_icms`/`icms_aliquota`/`icms_st`, `cfop_venda`/`cfop_compra` (campos separados), `pis_cst`/`pis_aliquota`, `cofins_cst`/`cofins_aliquota`, `observacao_fiscal`.

## Relacionamentos
- FK de saída: `produto_kit_id → produtos.id` (NOT NULL).
- Sem referências de entrada.

## Utilizado por
- `services/pdv_fiscal_resolver.py` (resolução fiscal no PDV), `api/v1/produto_fiscal_v2.py` (GET/PUT), `bling_integration_fiscal.py`.

## Não identificado
- Não confundir com [[kit_composicao]] (tabela órfã/duplicada, sem relação de FK com esta).
