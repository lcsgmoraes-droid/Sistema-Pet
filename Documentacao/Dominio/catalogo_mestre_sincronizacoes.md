---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_sincronizacoes

## Definição
Auditoria de cada carga/sincronização do catálogo mestre.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:389-409` (`CatalogoMestreSincronizacao`).
- Colunas: `origem_tenant_id`, `modo`, `status`, `resumo` (JSON). Sem FK.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `catalogo_mestre_sync_service.py`, script `run_catalogo_mestre_sync.py`.

## Não identificado
- Ver achados gerais em [[catalogo_mestre_produtos]].
