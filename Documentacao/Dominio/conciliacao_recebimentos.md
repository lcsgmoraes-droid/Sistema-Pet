---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_recebimentos

Ver [[conciliacao_validacoes]], [[Venda]].

## Definição
Dados da planilha de recebimento Stone (Aba 2) amarrados a vendas do PDV (Aba 3) — conciliação de recebimento de cartão.

## Confirmado no código
- Modelo: `conciliacao_recebimento_models.py:44-153` (`ConciliacaoRecebimento`).
- Colunas: `nsu`, `tipo_recebimento` (antecipacao/parcela_individual), `lote_id`/`lote_valor`, `validado`/`amarrado` (flags de workflow).
- Sobrescreve `created_at`/`updated_at` do `BaseTenantModel` para `None`, usa campos próprios `criado_em`/`atualizado_em`.
- ⚠️ **FK fantasma confirmada (mesmo padrão de [[conciliacao_logs]])**: `validacao_id` é `Integer` (nullable) com comentário `"FK desabilitado - tabela conciliacao_validacoes não existe"` — **falso**: a tabela existe (ver [[conciliacao_validacoes]]). Erro repetido em dois arquivos diferentes do mesmo módulo.

## Relacionamentos
- FK de saída real: `venda_id → vendas.id` (nullable).
- `validacao_id` deveria referenciar [[conciliacao_validacoes]]`.id` mas não tem constraint real.

## Utilizado por
- `conciliacao_abas_routes.py`, `conciliacao_services_recebimentos.py`, `financeiro/recebimentos_vendas_queries.py`.

## Não identificado
- 🔴 Mesmo achado de [[conciliacao_validacoes]]/[[conciliacao_logs]] — FK deveria ser restaurada.
