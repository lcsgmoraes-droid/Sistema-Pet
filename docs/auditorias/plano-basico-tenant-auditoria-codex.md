# Auditoria Codex - plano basico e isolamento tenant

Branch: `test/20260514-2259-auditoria-plano-basico-isolamento-ab`

## Validado automaticamente

| Area | Validacao | Resultado |
| --- | --- | --- |
| Auth/tenant | Rotas criticas do plano basico usando `get_current_user_and_tenant` | OK |
| Auth/tenant | Membership ativa, tenant ativo e sessao/JTI revalidados nas dependencias centrais | OK pela suite existente |
| Modulos premium | Gate `require_active_module` atualizado e testado com token/tenant atual | OK |
| Modulos premium | Routers premium principais continuam protegidos por `_module_dependencies(...)` | OK |
| Plano basico | `/modulos/status` usa tenant selecionado no token, nao tenant legado do usuario | Corrigido e testado |
| Produtos/racao | Calculadora interna de racao usa tenant selecionado no token | Corrigido e testado |
| SQL tenant-safe | Helper e runtime guard de SQL bruto continuam bloqueando query sem tenant | OK |
| Onboarding tenant | Criacao/base de tenant e dados padrao cobertos pela suite multi-tenant | OK |
| Mobile/entregas | Contexto tenant do entregador/e-commerce e status de entrega | OK |
| Frontend | Build de producao Vite | OK |

## Comandos executados

```powershell
$env:APP_ENV='test'; $env:ENVIRONMENT='test'; $env:ENV='test'; $env:DATABASE_URL='sqlite:///./test.db'; $env:DEBUG='false'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\unit\test_plano_basico_tenant_contract.py backend\tests\unit\test_module_access_dependency.py backend\tests\unit\test_tenant_security_middleware.py backend\tests\unit\test_sql_audit_config.py backend\tests\multi_tenant\test_phase1_tenant_hardening.py backend\tests\multi_tenant\test_phase1_1_runtime_validation.py backend\tests\multi_tenant\test_phase2b_tenant_safe_sql.py backend\tests\multi_tenant\test_phase3_tenant_onboarding_service.py -q
```

Resultado: `74 passed`.

```powershell
$env:APP_ENV='test'; $env:ENVIRONMENT='test'; $env:ENV='test'; $env:DATABASE_URL='sqlite:///./test.db'; $env:DEBUG='false'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\unit\test_ecommerce_mobile_tenant_context.py backend\tests\unit\test_entrega_status_contract.py -q
```

Resultado: `14 passed`.

```powershell
npm --prefix frontend run build
```

Resultado: build concluido com sucesso.

## Correcoes aplicadas nesta rodada

- `backend/app/api/racao_calculadora_routes.py`: trocado `get_current_user` por `get_current_user_and_tenant`.
- `backend/app/routes/modulos_routes.py`: `/modulos/status` agora resolve o tenant pelo token selecionado.
- `backend/tests/unit/test_module_access_dependency.py`: testes ajustados ao contrato atual da dependency assíncrona com credenciais.
- `backend/tests/unit/test_plano_basico_tenant_contract.py`: novo contrato automatizado para evitar regressao no plano basico/tenant.

## Ainda precisa de teste manual em tela

| Fluxo | Motivo |
| --- | --- |
| Editar/excluir cliente | O checklist anterior marcou como nao testado por MCP. |
| Financeiro do cliente | Validar tela real com cliente do tenant novo. |
| Editar/excluir pet | O checklist anterior marcou como nao testado. |
| Cadastro rapido de especie/raca | Houve erro anterior com `especie_id`; precisa reteste real. |
| Editar produto com todos os campos | Endpoint protegido, mas tela completa ainda precisa passada manual. |
| Calculadora de racao na UI | Backend corrigido; falta confirmar fluxo visual completo. |
| Catalogos auxiliares de produto | Conferir selects/departamentos/marcas/opcoes em tenant novo. |
| Formas de pagamento CRUD | Formas padrao foram usadas, mas CRUD completo ainda nao foi testado. |
| Operadoras de cartao | Ainda nao testado no checklist anterior. |
| Configuracao da empresa | Ainda nao testado no checklist anterior. |
| Usuarios/admin | Ainda nao testado no checklist anterior. |
| A/B real no navegador | Teste automatico cobre contrato; ainda vale conferir dois tenants reais lado a lado antes de vender. |
