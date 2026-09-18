---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — empresa_config_fiscal

Ver [[Tenant]], [[fiscal_estado_padrao]], [[produto_config_fiscal]], [[variacao_config_fiscal]], [[simples_nacional_mensal]].

## Definição
Config fiscal "raiz" do tenant — último nível (fallback final) da cadeia de resolução fiscal do PDV: `KitConfigFiscal → VariacaoConfigFiscal → ProdutoConfigFiscal → EmpresaConfigFiscal`.

## Confirmado no código
- Modelo: `empresa_config_fiscal_models.py:6-80` (`EmpresaConfigFiscal`).
- Colunas: `fiscal_estado_padrao_id` (FK fantasma, ver [[fiscal_estado_padrao]]), `uf`, `regime_tributario`, `cnae_principal`, `contribuinte_icms`, alíquotas ICMS/CFOPs, `pis_cst_padrao`/`pis_aliquota`, `cofins_cst_padrao`/`cofins_aliquota`, `municipio_iss`/`iss_aliquota`/`iss_retido`, `herdado_do_estado`; bloco Simples Nacional (`simples_ativo`, `simples_anexo`, `aliquota_simples_vigente`, `aliquota_simples_sugerida`); bloco provisões trabalhistas (`folha_valor_base_mensal`, `inss_patronal_percentual`, `fgts_percentual`); `cnaes_secundarios` (JSONB).
- Diferente de [[fiscal_catalogo_produtos]]/[[fiscal_estado_padrao]]: a cópia divergente que existia em `fiscal_models/` (com `tenant_id` Integer) **já foi removida** — hoje `fiscal_models/__init__.py` só reexporta a classe canônica, sem duplicação real.

## Relacionamentos
- FK de saída real: só a fantasma `fiscal_estado_padrao_id` (ver [[fiscal_estado_padrao]] para o achado de que ela fica sempre NULL na prática).
- Sem referências de entrada declaradas via FK ([[produto_config_fiscal]] e [[variacao_config_fiscal]] são consultadas separadamente pela cadeia de resolução, não por FK direta a esta tabela).

## Utilizado por
- CRUD: `empresa_routes.py`, `api/v1/empresa_fiscal.py`.
- DRE/canais (`dre_canais/agregacao.py`), comissões (`comissoes_geracao_service.py`), rentabilidade de venda (`services/venda_rentabilidade_snapshot_service.py`), fechamento/provisão/reconciliação do Simples (`fechamento_simples_service.py`, `provisao_simples_service.py`, `reconciliacao_simples_service.py`).
- Resolução fiscal do PDV: `services/pdv_fiscal_resolver.py` (fallback final da cadeia, via `obter_ou_criar_config_fiscal_empresa_padrao`).

## Não identificado
- Ver achado de [[fiscal_estado_padrao]]: `fiscal_estado_padrao_id` fica sempre NULL no fluxo real de criação.
