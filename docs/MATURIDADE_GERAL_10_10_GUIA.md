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
| Estrutura geral | 5/10 | 6,5/10 | 10/10 | Em andamento |
| Seguranca operacional | 2,5/10 | 8/10 | 10/10 | Em andamento |
| Testes/CI | 1/10 | 8,5/10 | 10/10 | Em andamento |
| Observabilidade/auditoria | 2/10 | 8/10 | 10/10 | Em andamento prioritario |
| Portabilidade/configuracao | 3/10 | 6,5/10 | 10/10 | Em andamento |
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

Nota atual: 6,5/10.

Referencia principal: `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md`.

Ja feito:

- [x] Documentos enterprise/UI/refatoracao consolidados no PR #67.
- [x] Plano Basico concentrado em checklist vivo: `docs/auditorias/plano-basico-tenant-checklist.md`.
- [x] Separacao operacional inicial de MCPs e services.
- [x] Alguns componentes globais ja existem no frontend.

Falta para 10/10:

- [ ] Inventariar arquivos frontend e backend mais longos e mais alterados.
- [ ] Definir top 10 arquivos de maior risco para quebra gradual.
- [ ] Criar padrao de modulo: rotas, services, schemas, testes e docs.
- [ ] Quebrar 1 modulo piloto sem mudar comportamento.
- [ ] Repetir o padrao em PDV/vendas, campanhas/cupons, produtos/estoque e financeiro.
- [ ] Remover duplicacao de regras de negocio em telas quando houver service central.
- [ ] Registrar Definition of Done para refatoracao segura.

Proxima acao concreta:

- [ ] Criar relatorio `docs/auditorias/estrutura-geral-inventario.md` com maiores arquivos, hotspots e primeira fatia de refatoracao.

## 4. Seguranca operacional

Nota inicial: 2,5/10.

Nota atual: 8/10.

Referencia principal: `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.

Ja feito:

- [x] Branch protection na `main`.
- [x] PR obrigatorio antes de merge.
- [x] Checks obrigatorios: `MCP tests`, `Fluxo unico safety`, `Quality Gate`, `Smoke test`.
- [x] Validador local bloqueia multiplas heads Alembic, artefatos e arquivos proibidos.
- [x] Deploy seguro documentado.
- [x] Deploy real validado com backup, migrations, health e watchdog.
- [x] SSH deste PC configurado para producao.

Falta para 10/10:

- [ ] Trocar deploy root por usuario operacional com privilegio minimo.
- [ ] Documentar rotacao de SSH/secrets.
- [ ] Testar restore real de backup em ambiente controlado.
- [ ] Criar checklist de rollback com tempo alvo e responsavel.
- [ ] Registrar auditoria de comandos sensiveis executados em producao.
- [ ] Separar ainda mais deploy de runtime e docs/workflows sem impacto de servidor.

Proxima acao concreta:

- [ ] Criar plano de hardening SSH/producao sem interromper o deploy atual.

## 5. Testes/CI

Nota inicial: 1/10.

Nota atual: 8,5/10.

Referencia principal: `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.

Ja feito:

- [x] Backend CI roda em todo PR para `main` e `develop`.
- [x] MCP CI roda em todo PR.
- [x] Deploy Safety roda em todo PR para `main`.
- [x] Smoke CI valida backend, auth basico e build frontend.
- [x] Branch protection exige checks principais.
- [x] Dependabot de GitHub Actions revisado e mergeado.
- [x] Suites focadas de MCP e Plano Basico registradas nos guias.

Falta para 10/10:

- [ ] E2E autenticado minimo para fluxo de login, tenant, clientes, produtos e PDV.
- [ ] Smoke controlado contra staging ou producao sem dados sensiveis.
- [ ] Teste automatizado de migrations em banco limpo e banco com historico.
- [ ] Teste de rollback/restore em ambiente controlado.
- [ ] Relatorio de cobertura por areas criticas, sem perseguir porcentagem cega.
- [ ] Separar testes rapidos obrigatorios de suites longas agendadas.

Proxima acao concreta:

- [ ] Desenhar E2E minimo do Plano Basico com usuario de teste e dados descartaveis.

## 6. Observabilidade/auditoria

Nota inicial: 2/10.

Nota atual: 8/10.

Referencia principal: `docs/roadmaps/FASE2_OBSERVABILIDADE.md` e secoes de Ops em `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md`.

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

Falta para 10/10:

- [ ] Estender `request_id`/`correlation_id` para jobs, workers e integracoes externas.
- [ ] Garantir logs estruturados JSON nas rotas criticas com eventos de negocio, nao apenas log HTTP.
- [ ] Estender trilha de auditoria para deploy, integracoes externas e demais alteracoes sensiveis fora das rotas ja cobertas.
- [ ] Alertar falhas recorrentes, lentidao, 5xx e falha de jobs.
- [ ] Documentar retencao de logs e dados de auditoria.

Proxima acao concreta:

- [ ] Documentar retencao de logs e dados de auditoria.

## 7. Portabilidade/configuracao

Nota inicial: 3/10.

Nota atual: 6,5/10.

Referencia principal: `docs/MCP_LOCAL_SETUP.md`, `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` e scripts de fluxo.

Ja feito:

- [x] MCPs usam env/config em vez de hardcode principal.
- [x] Script `scripts/test_mcp.ps1` cria `.venv` com `-InstallDevDependencies`.
- [x] Fluxo Git padronizado em scripts.
- [x] SSH de producao deste PC configurado.
- [x] Guia local de MCP existe.

Falta para 10/10:

- [ ] Criar bootstrap de PC novo em um comando para DEV.
- [ ] Validar `.env` com mensagem clara de variaveis faltantes.
- [ ] Documentar dependencias locais: Python, Node, Docker, GitHub CLI, SSH.
- [ ] Criar check de ambiente que nao exponha secrets.
- [ ] Documentar fluxo para segundo computador atualizar `main` antes de tarefa.
- [ ] Padronizar portas locais e fallback quando porta estiver ocupada.
- [ ] Criar troubleshooting de setup local.

Proxima acao concreta:

- [ ] Criar `scripts/check_dev_environment.ps1` com diagnostico seguro e guia de correcao.

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
| PR atual | Observabilidade/auditoria | Eventos de negocio de campanhas, cupons e carimbos para reconciliacao |

## Criterio para declarar 10/10 geral

So declarar 10/10 geral quando todos os itens abaixo estiverem marcados:

- [ ] Todas as areas do placar geral com nota 10/10.
- [ ] Nenhum item "Falta para 10/10" aberto sem justificativa.
- [ ] `release-check` passando na `main`.
- [ ] GitHub sem PR antigo pendente ou conflito esquecido.
- [ ] Evidencia registrada para deploy, testes, observabilidade e auditoria.
- [ ] Guia atualizado no mesmo PR que fecha cada etapa.
