---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — comissoes_vendas

Ver [[Venda]], [[Cliente]], [[ContaPagar]], [[comissoes_itens]].

## Definição
Consolidação da comissão de uma venda completa (soma dos itens) — gera conta a pagar quando a comissão é aprovada.

## Confirmado no código
- Modelo ORM: `comissoes_models.py:767-805` (`ComissaoVenda`).
- Colunas: `status` (pendente/pago/estornado).
- ⚠️ FK fantasma: `user_id` é `Integer` sem `ForeignKey("users.id")`.

## Relacionamentos
- FKs de saída: `venda_id → vendas.id` (NOT NULL), `funcionario_id → clientes.id` (NOT NULL), `conta_pagar_id → contas_pagar.id` (nullable).

## Utilizado por
- ⚠️ **Nenhuma rota/service Python usa a classe ORM diretamente.** A tabela só aparece em scripts de seed (`scripts/seed_demo_operacional_*.py`) e em `services/tenant_onboarding_financial_templates.py` — mecanismo exato (ORM ou SQL cru) não confirmado nesta pesquisa.

## Não identificado
- ❓ Mecanismo real de escrita em produção não confirmado — mesma situação de possível "ORM não usado" de [[comissoes_configuracao]].
