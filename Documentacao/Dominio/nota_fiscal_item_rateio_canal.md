---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — nota_fiscal_item_rateio_canal

Ver [[nota_fiscal_rateio_canal]].

## Definição
⚠️ Rateio percentual de um item de nota fiscal entre múltiplos canais — mesmo padrão morto de [[nota_fiscal_rateio_canal]], mas com um agravante adicional (ver abaixo).

## Confirmado no código
- Modelo: `nf_item_rateio_canal_models.py:5-22` (`NotaFiscalItemRateioCanal`).
- Colunas: `nota_fiscal_item_id` (String, sem FK), `canal`, `quantidade` ("fonte da verdade", comentário no código), `valor_calculado`/`percentual_calculado` (calculados no backend).

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- 🔴 **Único consumidor é `nota_fiscal_item_rateio_routes.py`, router não registrado em `main.py`/`main_routers.py`** — inalcançável via HTTP. Só aparece na allowlist `utils/tenant_safe_sql.py:75`.

## Não identificado
- 🔴 **Achado mais grave deste bloco**: dentro do próprio handler morto, há um comentário `🔴 AQUI assumimos que você já tem...` seguido de SQL cru (`db.execute("SELECT ... FROM nota_fiscal_itens WHERE id = :id", ...)`) contra uma tabela `nota_fiscal_itens` que **não existe em nenhum model/migration do projeto**. Além disso, passar string SQL crua direto pro `db.execute()` sem `text()` é inválido no SQLAlchemy 2.x usado no projeto. É claramente um rascunho nunca finalizado nem testado — recomenda-se remover ou completar antes que alguém tente reativar essa rota.
