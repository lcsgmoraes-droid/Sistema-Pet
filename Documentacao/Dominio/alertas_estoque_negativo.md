---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — alertas_estoque_negativo

Ver [[Produto]], [[Venda]], [[estoque_movimentacoes]].

## Definição
Alerta gerado quando uma venda deixa o estoque de um produto negativo — usado para gestão/correção posterior.

## Confirmado no código
- Modelo: `estoque_models.py:11-57` (`AlertaEstoqueNegativo`).
- Colunas: `produto_id`, `produto_nome` (denormalizado, comentário explícito "para performance"), `estoque_anterior`, `quantidade_vendida`, `estoque_resultante` (negativo), `venda_id` (nullable), `venda_codigo`, `status` (pendente/resolvido/ignorado), `data_resolucao`, `usuario_resolucao_id`, `notificado`, `critico` (true se `estoque_resultante < -5`).

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `venda_id → vendas.id` (nullable), `usuario_resolucao_id → users.id` (nullable).
- Sem referências de outras tabelas.

## Utilizado por
- Escrita: `estoque/service.py` (`_validar_ou_registrar_estoque_negativo`, linha 147+).
- Leitura/gestão: `estoque_alertas_routes.py` (rotas `/pendentes`, `/todos`, `/dashboard`).

## Não identificado
- ⚠️ `estoque_alertas_routes.py:56` chama `AlertaEstoqueNegativo.__table__.create(bind=db.get_bind(), checkfirst=True)` dentro da própria rota — cria a tabela sob demanda em runtime em vez de depender só de migration Alembic. Padrão incomum, vale revisar.
