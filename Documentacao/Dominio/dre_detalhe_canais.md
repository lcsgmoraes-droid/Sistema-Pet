---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_detalhe_canais

Ver [[Usuario]], [[dre_consolidado]], [[cargos]].

## Definição
Uma linha por canal de venda (loja_fisica/mercado_livre/shopee/amazon) do DRE — **a tabela mais usada de todo o módulo `ia/`**, hub real de integração financeira/operacional apesar de não estar registrada no Alembic.

## Confirmado no código
- Modelo: `ia/aba7_dre_detalhada_models.py:26-94` (`DREDetalheCanal`).
- `usuario_id` sem FK (apenas index).
- Campos de auditoria: `origem`/`origem_evento`/`referencia_id`.
- ⚠️ Duplica `created_at`/`updated_at` **e** `criado_em`/`atualizado_em` no mesmo modelo — campo redundante notável.

## Relacionamentos
- Sem FK de saída real.

## Utilizado por
- Extensivo e real: `dashboard/ponto_equilibrio_margem.py`, `ponto_equilibrio_routes.py`, `domain/dre/fechamento_engine.py`, `lancamento_dre_sync.py`, `rateio_engine.py`, `domain/ia/dre_context_provider.py`, `dre/helpers.py`, `dre_canais/folha.py`, `services/decimo_terceiro_service.py`, `ferias_service.py` (ver [[cargos]]), `projecao_caixa_service.py`, `provisao_beneficios_service.py`.

## Não identificado
- 🔴 **Não está listada em `alembic/env.py` nem em `db/base.py`**, apesar de ser a tabela mais usada de todo o módulo `ia/` — risco real de drift no autogenerate. Recomenda-se ao time priorizar a correção deste registro.
- Duplicação de colunas de timestamp (português/inglês) — vestígio de refactor.
