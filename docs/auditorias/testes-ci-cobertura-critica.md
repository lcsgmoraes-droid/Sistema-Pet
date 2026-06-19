# Matriz de cobertura critica de Testes/CI

Data: 2026-06-19

Objetivo: manter Testes/CI em 10/10 por cobertura de risco real, sem perseguir
porcentagem cega. A regra e simples: toda area que pode quebrar seguranca,
dinheiro, tenant, deploy ou operacao precisa ter pelo menos uma protecao
automatica obrigatoria em PR ou uma suite longa controlada.

## Resumo executivo

| Area critica | Risco principal | Protecao rapida obrigatoria | Protecao longa/manual |
|---|---|---|---|
| Multitenant e isolamento | Vazamento entre lojas/tenants | `Quality Gate`, `backend/tests/multi_tenant` | Plano Basico E2E seleciona tenant real de teste |
| Auth, permissoes e modulos | Acesso indevido ou plano liberado errado | `backend/tests/unit/test_module_access_dependency.py`, `backend/tests/unit/test_permissions_service.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Plano Basico E2E valida barreira de modulo |
| PDV, vendas e pagamentos | Venda incorreta, pagamento errado ou estoque sem baixa | `backend/tests/domain/test_venda_service.py`, `backend/tests/unit/test_venda_finalizacao_pagamentos.py`, `backend/tests/unit/test_vendas_regras_helpers.py` | Plano Basico E2E cria produto, estoque, venda e pagamento |
| Campanhas, cupons e fidelidade | Cupom/carimbo duplicado, nao consumido ou nao revertido | `backend/tests/domain/test_coupon_service.py`, `backend/tests/domain/test_loyalty_service.py`, `backend/tests/unit/test_campaign_coupon_rules.py`, `backend/tests/unit/test_campaigns_routes_cupom_anulacao.py` | Smoke controlado quando houver mudanca de contrato real |
| Estoque e produtos | Estoque negativo, lote errado ou busca inconsistente | `backend/tests/unit/test_estoque_*`, `backend/tests/unit/test_produtos_*` | Plano Basico E2E confirma baixa de estoque |
| Financeiro e comissoes | Conta, DRE ou comissao fora de transacao | `backend/tests/integration/test_transaction_*.py`, `backend/tests/unit/test_contas_pagar_origem_helpers.py` | Restore smoke valida base restauravel antes de operacoes grandes |
| Auditoria e request/correlation id | Incidente sem trilha rastreavel | `backend/tests/test_audit_api.py`, `backend/tests/unit/test_*audit*`, `backend/tests/unit/test_correlation_context.py` | Painel Ops e notifier externo em ambiente controlado |
| Integracoes externas | Webhook ou API externa quebrando fluxo principal | `backend/tests/unit/test_bling_*`, `backend/tests/unit/test_ecommerce_webhooks_signature.py`, `backend/tests/unit/test_whatsapp_*`, `backend/tests/unit/test_sefaz_service.py` | Testes controlados por segredo quando a integracao exigir ambiente real |
| Migrations e banco | Deploy quebrado por Alembic ou schema incompleto | `Migration Smoke` no `Backend CI` | Restore smoke de dump real em ambiente isolado |
| Deploy e rollback | Push inseguro, deploy sem evidencia ou rollback improvisado | `Fluxo unico safety`, `Smoke test`, `scripts/validar_fluxo.ps1` | Deploy real via `petdeploy` somente com autorizacao explicita |
| MCPs | Ferramenta local insegura ou quebrada | `MCP tests`, `scripts/test_mcp.ps1` | Reauditoria quando uma ferramenta nova entra |

## Separacao das suites

Obrigatorio em todo PR para `main`:

- `MCP tests`: valida os MCPs locais e protocolo via stdio.
- `Fluxo unico safety`: valida guardrails DEV -> PROD.
- `Quality Gate`: valida multitenant hardening, import smoke, Migration Smoke
  e check externo `SonarCloud Code Analysis`.
- `Smoke test`: valida testes raiz, smoke de backend/auth, audit/lint/format
  core do frontend e build frontend.

Longo, manual ou agendado:

- `E2E Long`: roda a suite `e2e_long` do Plano Basico por `workflow_dispatch` e
  agenda semanal. Se `E2E_*` nao estiver configurado, a suite pula com mensagem
  clara; contra producao, so roda quando `E2E_ALLOW_PRODUCTION=true`.
- Restore smoke real: continua sendo operacional e controlado, com evidencia em
  `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`.
- Teste de notifier Ops real: depende de webhook seguro configurado em producao.

## Criterio de manutencao

- Mudanca em regra de negocio critica deve apontar para uma linha desta matriz.
- Se a mudanca criar area critica nova, este arquivo deve ganhar uma linha nova
  no mesmo PR.
- Teste lento nao deve entrar como check obrigatorio sem necessidade. Primeiro
  entra como manual/agendado, depois vira obrigatorio apenas se for rapido,
  estavel e sem dependencia secreta.
- Credenciais de E2E ficam somente em GitHub Secrets ou ambiente local seguro.
  Nao registrar senha, token ou URL secreta em docs ou logs.

## Evidencia atual

- Suite E2E longa do Plano Basico: `backend/tests/test_plano_basico_e2e.py`.
- Marcador pytest: `e2e_long` em `backend/pytest.ini`.
- Workflow agendado/manual: `.github/workflows/e2e-long.yml`.
- Smoke controlado executado em 2026-05-17 contra tenant de teste, registrado em
  `docs/auditorias/testes-ci-e2e-plano-basico.md`.
- Migration Smoke automatizado no Backend CI, cobrindo banco limpo e historico
  controlado.
- Rodada 0.5 de 2026-06-18/19 fechou lint e format bloqueantes no Backend CI
  ate `ruff check .` e `ruff format --check .`.
- PR #658 confirmou SonarCloud/Quality Gate verdes com configuracao automatica
  alinhada aos caminhos sem runtime.
