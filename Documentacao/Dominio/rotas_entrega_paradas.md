---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — rotas_entrega_paradas

Ver [[rotas_entrega]], [[Venda]].

## Definição
Parada de uma rota de entrega — sempre ligada a uma [[Venda]] do PDV, nunca a um [[pedidos|Pedido]] de e-commerce diretamente.

## Confirmado no código
- Modelo: `rotas_entrega_models.py:126-172` (`RotaEntregaParada`).
- Colunas: `ordem`, `endereco`, `distancia_acumulada`/`tempo_acumulado`, `status` (pendente/entregue/tentativa), `data_entrega`, `km_entrega`, snapshot de custo operacional congelado (`modelo_custo_operacional`, `valor_base_custo_operacional`, `custo_operacional`, `custo_moto_rateado`, `custo_calculado_em`).
- ⚠️ **Confirma conexão rota↔venda sempre via [[Venda]]**: `venda_id` NOT NULL, nenhuma FK para tabelas de e-commerce — pedidos de e-commerce só entram no roteamento depois de virarem Venda no checkout.
- ⚠️ Mesmo padrão de colunas fantasma de [[rotas_entrega]]: `lat_entrega`, `lon_entrega`, `distancia_trecho_real_km`, `distancia_acumulada_real_km` existem no banco (DDL de compatibilidade) mas não no ORM — lidas via SQL cru e atribuídas como atributos dinâmicos.

## Relacionamentos
- FKs de saída: `rota_id → rotas_entrega.id`, `venda_id → vendas.id`.
- Sem referências de entrada reais (só o código morto `aba8_models.py` referencia conceitos parecidos, tabelas próprias diferentes).

## Utilizado por
- `rotas_entrega_paradas_routes.py` (reordenar, marcar entregue/não entregue, registrar recebimento do entregador).

## Não identificado
- Mesmo achado de colunas fantasma de [[rotas_entrega]].
