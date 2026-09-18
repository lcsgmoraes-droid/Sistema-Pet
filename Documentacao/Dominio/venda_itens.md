---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — venda_itens

Ver [[Venda]], [[Produto]], [[produto_lotes]], [[Pet]], [[EmpresaGrupo]].

## Definição
Item de linha de uma [[Venda]] — produto ou serviço vendido, com vínculo opcional a lote (FIFO), pet e estoque compartilhado entre empresas do grupo.

## Confirmado no código
- Modelo: `vendas_models.py:345-577` (`VendaItem`).
- Colunas: `venda_id`, `tipo` (produto/servico), `produto_id` (opcional), `estoque_origem_tenant_id` (estoque compartilhado — ver [[EmpresaGrupo]]), `estoque_compartilhado_id`, `lote_id` (FIFO), `pet_id`, `protocolo_recorrencia_id`, `racao_data_prevista_fim`/`racao_prazo_estimado_dias` (mutuamente exclusivos só por convenção, sem constraint de banco). Sem `updated_at`.
- ⚠️ Campo morto: `product_variation_id` (linhas 373-375) — comentário explícito no código confirma que não existe tabela `product_variations`; variação é `produtos.tipo_produto='VARIACAO'` + `produto_id`.

## Relacionamentos
- FKs de saída: `vendas.id` (CASCADE), `produtos.id`, `tenants.id` (RESTRICT), `empresa_grupo_estoques_compartilhados.id` (SET NULL), `produto_lotes.id`, `pets.id`, `produto_protocolos_recorrencia.id` (SET NULL).
- Referências de entrada: nenhuma FK de outra tabela. `Venda.itens` é relationship 1:N com cascade delete-orphan.

## Utilizado por
- `ai/context_builder.py:288-291` (produto mais vendido), `analise_racoes_routes_parts/segmentos_routes.py` (analítico de ração), `api/whatsapp_data_internal_routes.py:107`.

## Não identificado
- ⚠️ Composição de KIT é resolvida via query direta a `ProdutoKitComponente` dentro do próprio `to_dict()` (linhas 540-561), não via relationship — acoplamento de serialização com lógica de negócio, vale revisar.
