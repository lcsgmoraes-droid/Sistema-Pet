# Plano mestre de maturidade 10/10

Atualizado em: 2026-05-16

Este e o guia vivo para acompanhar a analise inicial completa de maturidade do Sistema Pet. Ele existe para nao deixar nenhum bloco para tras.

Regra de uso:

- Atualizar este arquivo a cada PR relevante.
- Marcar itens com `[x]` somente quando houver PR mergeado, validacao local ou evidencia operacional registrada.
- Quando uma nota mudar, registrar o motivo na secao da area.
- Nao confundir "feito para uso interno" com "hyperscale 10/10"; cada area tem criterio proprio.

## Placar geral

| Area | Nota inicial | Nota atual | Meta | Status |
|---|---:|---:|---:|---|
| MCP Frontend | 5,5/10 | 10/10 | 10/10 | Fechado para uso interno profissional |
| MCP Ops/API | 3,5/10 | 10/10 | 10/10 | Fechado para uso interno profissional |
| Estrutura geral | 5/10 | 10/10 | 10/10 | Fechado para uso interno profissional |
| Seguranca operacional | 2,5/10 | 9,9/10 | 10/10 | Em andamento |
| Testes/CI | 1/10 | 9/10 | 10/10 | Em andamento |
| Observabilidade/auditoria | 2/10 | 9,9/10 | 10/10 | Em andamento prioritario |
| Portabilidade/configuracao | 3/10 | 10/10 | 10/10 | Fechado para uso interno profissional |
| Documentacao | 4/10 | 8/10 | 10/10 | Em andamento |

## Ordem recomendada

1. Observabilidade/auditoria.
2. Portabilidade/configuracao.
3. Estrutura geral.
4. Seguranca operacional fina.
5. Testes/CI avancado.
6. Documentacao como governanca continua.

Motivo da ordem: primeiro precisamos enxergar, auditar e reproduzir o sistema com confianca; depois fica mais seguro refatorar e endurecer.

## 1. MCP Frontend

Nota inicial: 5,5/10.

Nota atual: 10/10.

Referencia principal: `docs/MCP_MATURIDADE_GUIA.md`.

Fechado:

- [x] Configuracao por variaveis de ambiente.
- [x] Allowlist de hosts HTTP locais.
- [x] Redaction basica de secrets.
- [x] Auditoria local JSONL.
- [x] Testes unitarios.
- [x] Teste de protocolo MCP via stdio.
- [x] Script unico `scripts/test_mcp.ps1`.
- [x] CI `MCP tests` rodando em todo PR.
- [x] Documentacao em `mcp/README.md` e README interno.

Para manter 10/10:

- [ ] Revisar Dependabot quando abrir PR de dependencia MCP.
- [ ] Reauditar quando adicionar ferramenta nova.

## 2. MCP Ops/API

Nota inicial: 3,5/10.

Nota atual: 10/10.

Referencia principal: `docs/MCP_MATURIDADE_GUIA.md`.

Fechado:

- [x] Separacao de services: API, campanhas, Docker, logs e comandos.
- [x] Trava de seguranca para comandos sensiveis.
- [x] Remocao de hardcode de usuario Postgres DEV.
- [x] Configuracao por env.
- [x] Redaction de secrets.
- [x] Auditoria local JSONL.
- [x] Ferramenta `mcp_audit_report`.
- [x] Testes unitarios.
- [x] Teste de protocolo MCP via stdio.
- [x] CI e branch protection exigindo `MCP tests`.

Para manter 10/10:

- [ ] Classificar risco em qualquer ferramenta nova antes do merge.
- [ ] Manter timeout, truncamento e redaction obrigatorios.

## 3. Estrutura geral

Nota inicial: 5/10.

Nota atual: 10/10.

Referencia principal: `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md`.

Ja feito:

- [x] Documentos enterprise/UI/refatoracao consolidados no PR #67.
- [x] Plano Basico concentrado em checklist vivo: `docs/auditorias/plano-basico-tenant-checklist.md`.
- [x] Separacao operacional inicial de MCPs e services.
- [x] Alguns componentes globais ja existem no frontend.
- [x] Inventario de estrutura geral criado em `docs/auditorias/estrutura-geral-inventario.md`.
- [x] Top 10 arquivos de maior risco definidos com primeira fatia recomendada.
- [x] Definition of Done de refatoracao modular criada em `docs/auditorias/estrutura-geral-definition-of-done.md`.
- [x] Primeira fatia piloto de Produtos extrai helpers de busca para `backend/app/produtos/search.py` sem mudar endpoints.
- [x] Segunda fatia piloto de Produtos extrai helpers de validade/listagem para `backend/app/produtos/validade.py` sem mudar endpoints.
- [x] Terceira fatia piloto de Produtos extrai helpers de racao/classificacao para `backend/app/produtos/racao.py` sem mudar endpoints.
- [x] Primeira fatia de Estoque extrai helpers de granel para `backend/app/estoque/granel.py` sem mudar endpoints.
- [x] Primeira fatia de PDV/vendas extrai regras puras para `backend/app/vendas/regras.py` sem mudar endpoints.
- [x] Primeira fatia de campanhas/cupons extrai regras puras para `backend/app/campaigns/coupon_rules.py` sem mudar contratos.
- [x] Primeira fatia de financeiro extrai origem de contas a pagar para `backend/app/financeiro/contas_pagar_origem.py` sem mudar endpoints.
- [x] Varredura final de hotspots registrada e criterio de manutencao modular consolidado.

Falta para 10/10:

- [x] Inventariar arquivos frontend e backend mais longos e mais alterados.
- [x] Definir top 10 arquivos de maior risco para quebra gradual.
- [x] Criar padrao de modulo: rotas, services, schemas, testes e docs.
- [x] Quebrar 1 modulo piloto sem mudar comportamento.
- [x] Aplicar o padrao tambem em financeiro com uma fatia pequena e testada.
- [x] Fazer varredura final dos hotspots e registrar criterio de manutencao para manter Estrutura geral em 10/10.
- [x] Definir criterio para remover duplicacao de regras de negocio em telas quando houver service central.
- [x] Registrar Definition of Done para refatoracao segura.

Para manter 10/10:

- [ ] Toda nova refatoracao estrutural deve seguir `docs/auditorias/estrutura-geral-definition-of-done.md`.
- [ ] Hotspot novo ou arquivo acima de 2.000 linhas deve ter plano de fatia antes de receber regra de negocio nova.
- [ ] Rotas criticas devem mover regras puras para pacote dedicado quando a regra passar a ser reutilizada ou testavel isoladamente.
- [ ] Duplicacao nova de regra de negocio em tela deve ser bloqueada ou movida para service/helper testado.

## 4. Seguranca operacional

Nota inicial: 2,5/10.

Nota atual: 9,9/10.

Referencia principal: `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.

Ja feito:

- [x] Branch protection na `main`.
- [x] PR obrigatorio antes de merge.
- [x] Checks obrigatorios: `MCP tests`, `Fluxo unico safety`, `Quality Gate`, `Smoke test`.
- [x] Validador local bloqueia multiplas heads Alembic, artefatos e arquivos proibidos.
- [x] Deploy seguro documentado.
- [x] Deploy real validado com backup, migrations, health e watchdog.
- [x] SSH deste PC configurado para producao.
- [x] Script oficial de deploy registra linha do tempo auditavel das etapas sensiveis em `backend/logs/deploy_events.jsonl`.
- [x] Wrapper `scripts/auditar_comando_producao.sh` registra comandos manuais sensiveis fora do deploy oficial em `backend/logs/ops_command_events.jsonl`.
- [x] Usuario operacional `petdeploy` criado em producao com SSH por chave deste PC, wrappers root-owned de deploy/status e sudo restrito a esses wrappers.
- [x] Deploy completo em producao executado via `petdeploy` em 2026-05-17 para o commit `520f8a2b`, com backup operacional `/opt/petshop/backups/deploy_20260517_133717` e containers finais saudaveis.
- [x] Rotacao de SSH/secrets documentada em `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md`.
- [x] Checklist de rollback inclui responsaveis e tempos alvo em `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.
- [x] Scripts e roteiro de backup/restore smoke controlado criados para validar dump real sem tocar o banco de producao.
- [x] Restore smoke de dump real executado em producao sem tocar o banco principal: backup `/opt/petshop/backups/db/restore_smoke_20260517_135920.dump.gz`, `public_tables=217`, `alembic_rows=1`, container temporario removido e health/watchdog saudaveis depois do teste.
- [x] Deploy seguro passa a detectar mudancas sem impacto de runtime e pular rebuild/restart quando o diff for apenas docs/workflows/Markdown.

Falta para 10/10:

- [x] Criar caminho de deploy/status por usuario operacional com privilegio minimo e root apenas como fallback.
- [x] Documentar rotacao de SSH/secrets.
- [x] Testar restore real de backup em ambiente controlado.
- [x] Criar checklist de rollback com tempo alvo e responsavel.
- [x] Separar ainda mais deploy de runtime e docs/workflows sem impacto de servidor.

Proxima acao concreta:

- [ ] Depois do merge/deploy, rodar um deploy sem mudanca de runtime e registrar a evidencia do caminho sem rebuild.

## 5. Testes/CI

Nota inicial: 1/10.

Nota atual: 9/10.

Referencia principal: `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.

Ja feito:

- [x] Backend CI roda em todo PR para `main` e `develop`.
- [x] MCP CI roda em todo PR.
- [x] Deploy Safety roda em todo PR para `main`.
- [x] Smoke CI valida backend, auth basico e build frontend.
- [x] Branch protection exige checks principais.
- [x] Dependabot de GitHub Actions revisado e mergeado.
- [x] Suites focadas de MCP e Plano Basico registradas nos guias.
- [x] Plano E2E minimo do Plano Basico definido com dados descartaveis e suites separadas.

Falta para 10/10:

- [x] Desenhar E2E autenticado minimo para fluxo de login, tenant, clientes, produtos e PDV.
- [ ] Implementar E2E autenticado minimo com skip seguro quando variaveis estiverem ausentes.
- [ ] Smoke controlado contra staging ou producao sem dados sensiveis.
- [ ] Teste automatizado de migrations em banco limpo e banco com historico.
- [ ] Teste de rollback/restore em ambiente controlado.
- [ ] Relatorio de cobertura por areas criticas, sem perseguir porcentagem cega.
- [ ] Separar testes rapidos obrigatorios de suites longas agendadas.

Proxima acao concreta:

- [ ] Implementar `TestPlanoBasicoMinimo` lendo `E2E_*` de ambiente e marcando a suite como longa.

## 6. Observabilidade/auditoria

Nota inicial: 2/10.

Nota atual: 9,9/10.

Referencia principal: `docs/roadmaps/FASE2_OBSERVABILIDADE.md`, `docs/RETENCAO_LOGS_AUDITORIA.md` e secoes de Ops em `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md`.

Ja feito:

- [x] Health publico e watchdog publico validados.
- [x] Ops possui historico e direcao documentada.
- [x] MCPs geram auditoria local JSONL.
- [x] Incidentes e watchdog aparecem no material enterprise consolidado.
- [x] Primeiro corte de `request_id`: header seguro `X-Request-ID`, UUID automatico para valor inseguro, propagacao para `trace_id` e log HTTP estruturado.
- [x] Trilha inicial de auditoria de negocio para cupom consumido, desconto manual efetivado e reabertura de venda com reversao de cupom/carimbo.
- [x] Auditoria de login/logout enriquecida com `request_id`.
- [x] Auditoria de acesso para criacao, vinculo, ativacao/desativacao e logout forcado de usuarios.
- [x] Auditoria de configuracao sensivel para ativacao manual de modulo e ativacao manual do Plano Basico.
- [x] Smoke CI confirma gravacao real de evento de auditoria com `request_id`.
- [x] Painel `/ops/incidentes` filtra incidentes por `request_id` no backend e mostra trilha de auditoria correlacionada ao evento selecionado.
- [x] Eventos de negocio de campanhas/cupons/carimbos registram chaves de reconciliacao: cupom criado/consumido/anulado/revertido, carimbo manual, estorno de carimbo e sincronizacao automatica de fidelidade.
- [x] Politica operacional de retencao de logs e dados de auditoria documentada em `docs/RETENCAO_LOGS_AUDITORIA.md`.
- [x] `correlation_id` aplicado aos jobs criticos do scheduler Bling: fila de webhooks, auditoria de fluxo, status de pedidos, NFs pendentes/autorizadas e duplicidades.
- [x] `correlation_id` aplicado nas integracoes externas restantes de WhatsApp, SEFAZ e e-mail transacional.
- [x] Eventos de negocio auditaveis tambem emitem log estruturado JSON via caminho central de auditoria.
- [x] Deploy oficial registra eventos `running`, `success` e `failed` por etapa sensivel, preservando falhas finais mesmo apos eventos intermediarios.
- [x] Comandos manuais sensiveis podem ser executados com auditoria `started`, `success` e `failed`, motivo obrigatorio e redaction basica de argumentos.
- [x] Painel Ops gera alertas acionaveis para 5xx recorrente, lentidao recorrente, falhas recorrentes do watchdog externo e worker/job Bling degradado.
- [x] Alertas Ops criticos possuem notifier externo opcional por webhook configuravel via env, com payload minimo e deduplicacao local em JSONL.
- [x] Script `scripts/test_ops_alert_webhook.py` valida disparo controlado do notifier sem imprimir a URL secreta do webhook.

Falta para 10/10:

- [ ] Configurar canal real de notificacao Ops em producao e testar disparo controlado sem expor secrets.

Proxima acao concreta:

- [ ] Configurar `OPS_ALERT_WEBHOOK_URL` no ambiente seguro de producao e validar um alerta controlado.

## 7. Portabilidade/configuracao

Nota inicial: 3/10.

Nota atual: 10/10.

Referencia principal: `docs/MCP_LOCAL_SETUP.md`, `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` e scripts de fluxo.

Ja feito:

- [x] MCPs usam env/config em vez de hardcode principal.
- [x] Script `scripts/test_mcp.ps1` cria `.venv` com `-InstallDevDependencies`.
- [x] Fluxo Git padronizado em scripts.
- [x] SSH de producao deste PC configurado.
- [x] Guia local de MCP existe.
- [x] Script `scripts/check_dev_environment.ps1` diagnostica ambiente DEV sem expor secrets.
- [x] Dependencias locais e correcoes comuns documentadas em `docs/DEV_ENVIRONMENT_CHECK.md`.
- [x] Bootstrap `scripts/bootstrap_dev_environment.ps1` prepara PC novo com dry-run, JSON e modo sem rede.
- [x] Fluxo para segundo computador documentado com `scripts/git_check_updates.ps1` e `scripts/git_start_task.ps1`.
- [x] Portas locais padrao (`8000`, `5173`, `5433`) diagnosticadas no check e documentadas com fallback.

Fechado:

- [x] Criar bootstrap de PC novo em um comando para DEV.
- [x] Validar `.env` com mensagem clara de variaveis faltantes.
- [x] Documentar dependencias locais: Python, Node, Docker, GitHub CLI, SSH.
- [x] Criar check de ambiente que nao exponha secrets.
- [x] Documentar fluxo para segundo computador atualizar `main` antes de tarefa.
- [x] Padronizar portas locais e fallback quando porta estiver ocupada.
- [x] Criar troubleshooting de setup local inicial.

Para manter 10/10:

- [ ] Atualizar `scripts/check_dev_environment.ps1` e `docs/DEV_ENVIRONMENT_CHECK.md` quando novas dependencias, portas ou MCPs entrarem no projeto.

## 8. Documentacao

Nota inicial: 4/10.

Nota atual: 8/10.

Referencias principais:

- `docs/MCP_MATURIDADE_GUIA.md`
- `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`
- `docs/MATURIDADE_GERAL_10_10_GUIA.md`
- `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md`
- `docs/auditorias/plano-basico-tenant-checklist.md`

Ja feito:

- [x] Guia MCP vivo.
- [x] Guia CI/CD/deploy seguro vivo.
- [x] Documentos enterprise/UI/refatoracao consolidados.
- [x] Checklist do Plano Basico atualizado com producao real.
- [x] PRs antigos de documentacao revisados, mergeados ou fechados.

Falta para 10/10:

- [ ] Adicionar este guia como indice oficial nos READMEs relevantes.
- [ ] Criar rotina de atualizacao obrigatoria no fim de cada frente.
- [ ] Remover ou consolidar docs obsoletas restantes.
- [ ] Criar indice curto para "por onde comecar" em DEV, PROD, MCP, CI e Produto.
- [ ] Padronizar formato de evidencia: comando, resultado, data, PR e impacto.

Proxima acao concreta:

- [x] Linkar este guia em `mcp/README.md`, `docs/MCP_MATURIDADE_GUIA.md` e `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.
- [ ] Linkar este guia em `README.md` depois de corrigir o encoding/mojibake do arquivo para nao piorar a legibilidade.

## Historico de PRs relevantes

| PR | Area | Resultado |
|---|---|---|
| #44 | MCPs | Hardening dos MCPs |
| #45 | MCPs/CI | CI dos MCPs e bootstrap de venv |
| #47 | MCPs/CI | MCP CI em todo PR |
| #48 | MCPs | Guia atualizado com branch protection |
| #49 | MCPs | Testes de protocolo MCP |
| #50 | MCPs/auditoria | Relatorio local de auditoria |
| #52 | CI | `actions/setup-node` v6 |
| #53 | CI | `actions/checkout` v6 |
| #54 | CI | `actions/setup-python` v6 |
| #55 | CI/CD | Deploy Safety e Backend CI |
| #57 | CI | Smoke CI |
| #58 | CI/protecao | `Smoke test` obrigatorio |
| #64 | Seguranca operacional/produto | Cupom/carimbos/reabertura de venda corrigidos e deployados |
| #65 | MCPs/docs | Guia MCP atualizado apos Dependabot |
| #66 | CI/CD/docs | Deploy real registrado no guia |
| #38 | Produto/docs | Checklist pos-deploy do Plano Basico atualizado |
| #67 | Documentacao | Docs enterprise/UI/refatoracao consolidados |
| #68 | Documentacao/governanca | Plano mestre de maturidade geral criado |
| #69 | Observabilidade/auditoria | `request_id` seguro e log HTTP estruturado |
| #70 | Observabilidade/auditoria | Auditoria de negocio para cupom, desconto manual e reabertura |
| #71 | Observabilidade/auditoria | Auditoria de acesso, login e configuracoes sensiveis |
| #72 | Observabilidade/auditoria | Smoke CI confirma auditoria gravada com `request_id` |
| #73 | Observabilidade/auditoria | Painel de incidentes com filtro por `request_id` e auditoria correlacionada |
| #74 | Observabilidade/auditoria | Eventos de negocio de campanhas, cupons e carimbos para reconciliacao |
| #75 | Observabilidade/auditoria | Politica de retencao de logs e dados de auditoria |
| #76 | Observabilidade/auditoria | Correlacao para jobs criticos do scheduler Bling |
| #77 | Observabilidade/auditoria | Correlacao para WhatsApp, SEFAZ e e-mail |
| #78 | Observabilidade/auditoria | Logs estruturados de eventos de negocio |
| #79 | Observabilidade/auditoria/seguranca operacional | Linha do tempo auditavel das etapas sensiveis do deploy |
| #80 | Observabilidade/auditoria/seguranca operacional | Auditoria de comandos manuais sensiveis em producao |
| #81 | Observabilidade/auditoria | Alertas acionaveis para 5xx, lentidao, falhas recorrentes e worker/job degradado |
| #82 | Observabilidade/auditoria | Notifier externo opcional para alertas Ops criticos |
| #83 | Observabilidade/auditoria | Script de teste controlado do notifier Ops |
| #84 | Portabilidade/configuracao | Check seguro de ambiente DEV e guia de correcao |
| #85 | Portabilidade/configuracao | Bootstrap de PC novo para ambiente DEV |
| #86 | Portabilidade/configuracao | Fluxo de segundo PC e diagnostico de portas locais |
| #87 | Estrutura geral | Inventario de hotspots e primeira fatia de refatoracao |
| #88 | Estrutura geral | Definition of Done para refatoracao modular |
| #89 | Estrutura geral | Primeira fatia piloto de Produtos sem mudar contrato |
| #90 | Estrutura geral | Segunda fatia piloto de Produtos para validade/listagem |
| #91 | Estrutura geral | Terceira fatia piloto de Produtos para racao/classificacao |
| #92 | Estrutura geral | Primeira fatia de Estoque para granel |
| #93 | Estrutura geral | Primeira fatia de PDV/vendas para regras puras |
| #94 | Estrutura geral | Primeira fatia de campanhas/cupons para regras puras |
| #95 | Estrutura geral | Primeira fatia de financeiro para origem de contas a pagar |
| #96 | Estrutura geral | Fechamento 10/10 com varredura final e criterio de manutencao |
| #97 | Testes/CI | Plano E2E minimo do Plano Basico com dados descartaveis |
| #98 | Seguranca operacional | Usuario operacional `petdeploy` e deploy sem root direto |
| #99 | Seguranca operacional | Deploy via `petdeploy`, rotacao de SSH/secrets e rollback com responsaveis |
| #100 | Seguranca operacional | Scripts de backup e restore smoke controlado do banco |
| #101 | Seguranca operacional | Evidencia de restore smoke real do banco em producao |
| #102 | Seguranca operacional | Deploy sem rebuild para mudancas sem impacto de runtime |

## Criterio para declarar 10/10 geral

So declarar 10/10 geral quando todos os itens abaixo estiverem marcados:

- [ ] Todas as areas do placar geral com nota 10/10.
- [ ] Nenhum item "Falta para 10/10" aberto sem justificativa.
- [ ] `release-check` passando na `main`.
- [ ] GitHub sem PR antigo pendente ou conflito esquecido.
- [ ] Evidencia registrada para deploy, testes, observabilidade e auditoria.
- [ ] Guia atualizado no mesmo PR que fecha cada etapa.
