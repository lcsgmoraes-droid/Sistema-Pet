---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — notas_entrada

Ver [[pedidos_compra]], [[notas_entrada_itens]], [[ContaPagar]], [[produto_lotes]], [[produtos_historico_precos]], [[Cliente]].

## Definição
Nota fiscal de entrada (XML/SEFAZ) — hub central de integração real entre compras, estoque e financeiro.

## Confirmado no código
- Modelo: `produtos_compras_models.py:168-237` (`NotaEntrada`).
- Colunas: `numero_nota`, `serie`, `chave_acesso` (único), `status` (pendente/processada/erro), `conferencia_status`, `entrada_estoque_realizada` (bool), campos de rateio online/loja ("apenas informativo — estoque é UNIFICADO"), `xml_content`.
- ⚠️ FK fantasma: `fornecedor_id` é `Integer` sem `ForeignKey()`, resolvido em runtime contra [[Cliente]] (`compras_pendencias_notas.py:118-125`, `_buscar_fornecedor`).
- Nota de import: `notas_entrada/financeiro.py:17` importa esta classe via `app.produtos_models` (shim de compatibilidade que reexporta de `produtos_compras_models.py`) — não é duplicação real, mas espalha dois caminhos de import para o mesmo modelo pela base de código.

## Relacionamentos
- FKs de saída: `conferencia_user_id → users.id`, `user_id → users.id`.
- Referenciada por (hub — muitas): [[pedidos_compra]]`.nota_entrada_id`, [[pedidos_compra_notas_entrada]]`.nota_entrada_id`, [[notas_entrada_itens]]`.nota_entrada_id`, [[produtos_historico_precos]]`.nota_entrada_id`, [[ContaPagar]]`.nota_entrada_id`, [[compras_pendencias_fornecedor]]`.nota_entrada_id`.

## Utilizado por
- Import: `notas_entrada/upload_routes.py`, `notas_entrada/sefaz_importer.py`.
- Geração de conta a pagar a partir das duplicatas do XML: `notas_entrada/financeiro.py:53-130` (`criar_contas_pagar_da_nota`).
- Baixa de estoque: `notas_entrada/processamento_routes.py:362-382`.

## Não identificado
- Nada além do já citado.
