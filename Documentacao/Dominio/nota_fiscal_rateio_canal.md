---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — nota_fiscal_rateio_canal

Ver [[bling_notas_fiscais_cache]], [[nota_fiscal_item_rateio_canal]].

## Definição
⚠️ Rateio percentual de uma nota fiscal entre múltiplos canais de venda — desenhada mas **nunca conectada** a nenhum fluxo real.

## Confirmado no código
- Modelo: `nf_rateio_canal_models.py:5-17` (`NotaFiscalRateioCanal`).
- Colunas: `nota_fiscal_id` (String livre, sem FK), `canal`, `percentual` (Numeric 5,2), `observacao`.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- 🔴 **Único consumidor é `nota_fiscal_rateio_routes.py`, mas esse router não está registrado em nenhum lugar** (`main.py`/`main_routers.py`) — endpoint inalcançável via HTTP, código morto. A tabela só aparece adicionalmente numa allowlist de SQL tenant-safe (`utils/tenant_safe_sql.py:76`), que não é via de escrita/leitura de negócio real.

## Não identificado
- 🟡 Observação de design: [[bling_notas_fiscais_cache]] (tabela real e usada) já guarda um único `canal`/`canal_label` por NF, enquanto esta tabela foi desenhada para múltiplos canais por percentual — desenho paralelo nunca plugado ao fluxo vivo.
