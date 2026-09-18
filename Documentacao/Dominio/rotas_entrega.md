---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — rotas_entrega

Ver [[Venda]], [[Cliente]], [[rotas_entrega_paradas]], [[rotas_entrega_rastreio_tokens]], [[banho_tosa_taxi_dog]].

## Definição
Rota de entrega, agrupando uma ou mais vendas (via paradas) atribuídas a um entregador.

## Confirmado no código
- Modelo: `rotas_entrega_models.py:29-105` (`RotaEntrega`).
- Colunas: `numero` (único), `venda_id` (nullable — rota pode agrupar várias vendas via paradas), `entregador_id` (**entregador é modelado como [[Cliente]]**, não User/funcionário, validado via perfil de app "entregador"), `endereco_destino`, `distancia_prevista`/`real`, `custo_previsto`/`real`/`custo_moto`, `taxa_entrega_cliente`, `valor_repasse_entregador`, `status` (pendente/em_rota/concluida/cancelada), `created_by`.
- 🔴 **ORM incompleto — colunas reais do banco não declaradas no modelo**: `token_rastreio`, `lat_atual`, `lon_atual`, `localizacao_atualizada_em`, `distancia_total_km_real`, `distancia_retorno_km_real` existem fisicamente (adicionadas via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` em runtime, `rotas_entrega_schema.py:79-93`), mas não são `Column` no ORM. São lidas/escritas via SQL cru e depois "penduradas" como atributos Python dinâmicos na instância (`rota.lat_atual = ...`) só para alimentar a resposta da API — SQLAlchemy não valida esses atributos, risco de typo silencioso.
- ⚠️ FK redundante em [[Venda]]: `Venda.entregador_id`/`status_entrega`/`data_entrega` duplicam conceito já existente aqui, sincronizados manualmente em código (`_sincronizar_venda_entregue_por_parada`), não por constraint/trigger de banco.

## Relacionamentos
- FKs de saída: `venda_id → vendas.id` (nullable), `entregador_id → clientes.id`, `created_by → users.id`.
- Referenciada por: [[rotas_entrega_rastreio_tokens]]`.rota_id` (CASCADE, unique), [[rotas_entrega_paradas]]`.rota_id`.
- ⚠️ FK fantasma de entrada: [[banho_tosa_taxi_dog]]`.rota_entrega_id`, sem `ForeignKey()` real nem `relationship()`.
- 🔴 **Duplicação de tabela morta confirmada**: `app/ia/aba8_models.py` define uma segunda classe `Rota` com `__tablename__ = "rotas_entrega"` e schema de colunas totalmente diferente (mais `Entrega`/`historico_entregas` também duplicadas). O módulo inteiro nunca é importado em produção (só um placeholder vazio de `app/ia/__init__.py` é importado) — o conflito de metadata nunca dispara em runtime, mas é risco latente se alguém importar `aba8_models` por engano (quebraria o boot por `__tablename__` duplicado).

## Utilizado por
- `api/endpoints/rotas_entrega.py` (routers agregados: core/otimização/paradas/criação/estado), registrados em `main_routers.py:139-142,584-586`.

## Não identificado
- 🔴 Recomenda-se remover `app/ia/aba8_models.py` (código morto de alto risco) e formalizar as colunas fantasma no ORM.
