---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — nao_vendas

Ver [[Cliente]], [[nao_venda_itens]].

## Definição
Registro de "cliente saiu sem comprar" no PDV — captura motivo e valor estimado perdido, para análise de oportunidades não convertidas.

## Confirmado no código
- Modelo: `nao_venda_models.py:9-34` (`NaoVenda`).
- Colunas: `cliente_id` (opcional, SET NULL), `usuario_registrou_id` (obrigatória, RESTRICT), `cliente_nome`/`cliente_telefone` (denormalizado, permite cliente não cadastrado), `motivo` (indexado), `valor_estimado_total`, `origem` (default `pdv`).

## Relacionamentos
- FKs de saída: `clientes.id` (SET NULL), `users.id` (RESTRICT).
- Referenciada por: [[nao_venda_itens]]`.nao_venda_id` (CASCADE).

## Utilizado por
- `nao_venda_routes.py` — `POST /nao-vendas/` (via `services/nao_venda_service.py:86`), `GET /nao-vendas/relatorio` (via `services/nao_venda_relatorio.py`).

## Não identificado
- Nada notável — módulo pequeno e coeso.
