---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — empresa_parametros

Ver [[Tenant]], [[operadoras_cartao]].

## Definição
Parâmetros de tolerância e taxas MDR estimadas do tenant, usados no módulo de conciliação de cartões (Fase 1) — não confundir com o módulo de conciliação bancária genérica em `financeiro/models_conciliacao.py`.

## Confirmado no código
- Modelo: `conciliacao_models.py:55-121` (`EmpresaParametros`). Não herda `BaseTenantModel` propositalmente — usa mixin `TenantScoped` + `Base` cru (comentário explícito no código, linhas 62-65).
- Colunas: `tolerancia_conciliacao`/`tolerancia_conciliacao_media`, `taxa_mdr_debito_estimada` (e afins), `dias_vencimento_cartao_debito`/`credito_av`.
- Sem FK.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `conciliacao_services_importacao.py`.

## Não identificado
- Nada notável.
