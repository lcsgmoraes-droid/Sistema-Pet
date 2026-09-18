---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — valor_empresa_configuracoes

Ver [[bens_imobilizados]], [[Tenant]].

## Definição
Configuração (singleton por tenant) de premissas usadas na avaliação de valuation do negócio.

## Confirmado no código
- Modelo: `financeiro/models_valor_empresa.py:17-45` (`ValorEmpresaConfiguracao`).
- `UniqueConstraint("tenant_id")` — 1 configuração por tenant, garantida no banco (diferente de [[campanha_validade_automatica]], que não tem essa garantia).
- Colunas: overrides de premissas financeiras (`folha_mensal_override`, `margem_contribuicao_override`, `desconto_estoque_*`, `multiplo_lucro_*`).
- Sem FKs.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `financeiro/valor_empresa_routes.py`, `financeiro/valor_empresa_service.py`.

## Não identificado
- Nada notável.
