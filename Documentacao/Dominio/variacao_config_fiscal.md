---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — variacao_config_fiscal

Ver [[produto_config_fiscal]], [[kit_composicao]].

## Definição
Config fiscal específica de uma variação de produto, nível mais específico (1º) da cadeia de resolução fiscal do PDV — só consultada quando `variacao_id` é passado, tem prioridade sobre produto/empresa.

## Confirmado no código
- Modelo: `variacao_config_fiscal_models.py:17-77` (`VariacaoConfigFiscal`).
- Docstring própria documenta duas correções/decisões de design: (1) `tenant_id` era `Integer` originalmente (incompatível com o resto do sistema, UUID), corrigido via mixin `TenantScoped`; (2) ⚠️ `variacao_id` aponta para uma tabela `produto_variacao` que **não tem model ORM nem migration** — por isso é `Integer` sem `ForeignKey()` (mesmo padrão do achado em [[kit_composicao]], citado no próprio comentário do código).
- Colunas: `variacao_id` (unique, FK fantasma), `herdado_do_produto`, mesmo conjunto de campos fiscais de [[produto_config_fiscal]] (ncm/cest/cst_icms/icms_aliquota/icms_st/cfops/pis/cofins/observacao_fiscal), `configuracao_sugerida` (bool).
- Não tem cópia órfã em `fiscal_models/` — o próprio `db/base.py` comenta isso e importa o módulo canônico direto para o Alembic.

## Relacionamentos
- FK de saída real: `produto_config_fiscal_id → produto_config_fiscal.id` (nullable).
- `variacao_id` referencia informalmente uma tabela inexistente (`produto_variacao`).
- Sem referências de entrada.

## Utilizado por
- 1º nível da cadeia de resolução fiscal do PDV: `services/pdv_fiscal_resolver.py`.

## Não identificado
- `variacao_id` aponta para uma tabela conceitual sem representação real no banco — vale confirmar com o time se `produto_variacao` deveria existir ou se o campo é vestigial (variações hoje são modeladas como `Produto.tipo_produto='VARIACAO'`, conforme já visto em [[produto_lotes]] e [[venda_itens]]).
