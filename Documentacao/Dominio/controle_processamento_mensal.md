---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — controle_processamento_mensal

## Definição
🔴 **Código morto confirmado.** Tabela de idempotência para processos mensais recorrentes (provisão trabalhista, fechamento).

## Confirmado no código
- Modelo: `controle_processamento_models.py:11-35` (`ControleProcessamentoMensal`).
- Colunas: `tenant_id` (String solto, não `TenantScoped`, sem filtro automático de tenant), `tipo` (PROVISAO_TRABALHISTA/PROVISAO_COMISSOES/FECHAMENTO_MENSAL), `mes`/`ano`, `processado_em`.
- `services/processamento_mensal_service.py` define `executar_provisao_trabalhista_mensal`, `verificar_periodo_ja_processado`, `remover_registro_processamento` usando esta tabela.

## Relacionamentos
- Sem FK.

## Utilizado por
- 🔴 **Nenhum caller encontrado** — nem rota, nem outro service, nem script chama as funções do serviço em todo o backend. Feature implementada mas nunca conectada.

## Não identificado
- 🟡 Se o serviço for ativado no futuro, atenção: `tenant_id` como String solto (não `TenantScoped`) não recebe filtro automático de isolamento multi-tenant.
