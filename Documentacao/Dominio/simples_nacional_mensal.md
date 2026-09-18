---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — simples_nacional_mensal

Ver [[empresa_config_fiscal]].

## Definição
Apuração mensal do Simples Nacional por tenant (faturamento, imposto estimado vs. real, alíquota efetiva).

## Confirmado no código
- Modelo: `simples_nacional_models.py:19-76` (`SimplesNacionalMensal`, `TenantScoped`+`Base`).
- Colunas: `mes`/`ano` (competência), `faturamento_sistema` vs `faturamento_contador` (prioritário — property `faturamento_final`), `imposto_estimado` vs `imposto_real` (property `diferenca_imposto`), `aliquota_efetiva`, `aliquota_sugerida`, `fechado` (trava edição), `observacoes`.
- `UniqueConstraint(tenant_id, ano, mes)` — um registro por competência/tenant.

## Relacionamentos
- Sem FK de saída nem de entrada declaradas.

## Utilizado por
- CRUD: `simples_routes.py` (rota registrada e ativa via `main_routers.py:126,546`).
- Apuração/fechamento: `services/fechamento_simples_service.py` (grava `aliquota_simples_vigente` na [[empresa_config_fiscal]] a partir da sugestão).
- `services/projecao_caixa_service.py` (lê histórico).

## Não identificado
- Nada notável.
