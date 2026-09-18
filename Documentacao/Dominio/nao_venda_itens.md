---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — nao_venda_itens

Ver [[nao_vendas]], [[Produto]], [[Cliente]].

## Definição
Item que o cliente buscava numa oportunidade não convertida ([[nao_vendas]]) — permite registrar produto não cadastrado no catálogo via campos denormalizados.

## Confirmado no código
- Modelo: `nao_venda_models.py:37-68` (`NaoVendaItem`).
- Colunas: `nao_venda_id`, `produto_id` (opcional, SET NULL — permite item sem produto cadastrado), `marca_id` (opcional, SET NULL), `fornecedor_id` (opcional, SET NULL, **aponta para `clientes.id`**, não uma tabela de fornecedores — mesmo padrão de [[produto_fornecedores]]), `produto_nome`/`sku`/`marca_nome`/`fornecedor_nome` (denormalizados), `adicionado_lista_espera` (bool).

## Relacionamentos
- FKs de saída: `nao_vendas.id` (CASCADE), `produtos.id` (SET NULL), `marcas.id` (SET NULL), `clientes.id` (SET NULL, via `fornecedor_id`).
- Sem referências de entrada.

## Utilizado por
- `services/nao_venda_service.py:117`, populado junto com [[nao_vendas]] na mesma rota `nao_venda_routes.py:25`.

## Não identificado
- `fornecedor_id` apontando para `clientes.id` é o ponto mais enganoso desta tabela para quem não conhece o padrão do sistema (fornecedor = cliente com flag).
