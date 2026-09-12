---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 1 — CI/CD, Boas Práticas, Padronização e Componentização

Parte de [[Roadmap]]. Base: [[CI-CD]], [[Arquitetura]], [[Matriz-de-Riscos]] (item R09).

## Objetivo da fase

Consolidar a fundação de engenharia antes de mapear telas ou mexer em integrações: pipeline confiável, código padronizado, e — o ponto mais importante — arquivos e módulos do tamanho certo, para que a Fase 2 (mapeamento por tela) descreva uma estrutura que vai ficar estável, não uma que está prestes a ser reorganizada.

## 1.1 — CI/CD: consolidar o que já existe, fechar as lacunas conhecidas

O pipeline já é maduro (ver [[CI-CD]]: 8 workflows, gate de release, deploy com backup pré-migration e rollback). Não precisa ser recriado. Ações:

- [ ] **CODEOWNERS** — não existe hoje. Criar mapeando pelo menos: `backend/app/financeiro/` → dono financeiro, `backend/app/intnfe/`+`nfe*` → dono fiscal, `frontend/src/` → dono frontend, `.github/workflows/` + `scripts/deploy_*` → dono de infra/deploy. Vira obrigatório assim que houver mais de uma pessoa commitando com regularidade.
- [ ] **GitHub Environments** para `production` com required reviewers — formaliza em configuração do GitHub a regra que hoje só existe em texto (`AGENTS.md`: "nunca fazer deploy sem autorização explícita").
- [ ] **Deploy automático de homologação** pós-merge em `main` — o workflow `homologacao-isolada.yml` já monta o ambiente completo; falta automatizar o gatilho (hoje é manual/por mudança de infra). Produção continua manual.
- [ ] **Hook local de lint pré-commit** — hoje `.githooks/pre-commit` só bloqueia commit direto em `main`; considerar adicionar `ruff check`/`eslint` rápido como segunda checagem local, para pegar erro antes mesmo do PR (CI já bloqueia, isso só antecipa o feedback).
- [ ] Manter o gate de release e o rollback exatamente como estão — já é o padrão correto para deploy sem Kubernetes (ver [[CI-CD]] "Proposta de evolução").

## 1.2 — Padronização de código: expandir o que já é bloqueante

Confirmado: `ruff check`/`ruff format` já são bloqueantes no backend CI; ESLint/Prettier já configurados no frontend (`npm run lint:core`, `npm run format:core:check`). Ações para aprofundar:

- [ ] **Type checking real no backend** — ⚠️ não identificado uso de `mypy`/`pyright` no `backend-ci.yml`. Avaliar adicionar ao menos em modo não-bloqueante inicialmente, dado o volume de arquivos (~300+).
- [ ] **TypeScript no frontend** — hoje majoritariamente `.jsx`; `frontend/src/stores/whatsappStore.ts` e `services/api.ts` são exceções isoladas. Não propor migração total (custo alto sem evidência de necessidade); propor que **código novo** em áreas críticas (pagamento, fiscal, autenticação) seja escrito em `.tsx`/`.ts` a partir de agora, migrando organicamente.
- [ ] **Convenção de nomenclatura de arquivo por domínio** — hoje mistura `banho_tosa_agenda_capacity.py` (snake_case longo, flat) com `vendas/` (pasta por domínio). Definir formalmente em `docs/BLUEPRINT_BACKEND.md` (já existe o padrão-alvo) que todo domínio **novo ou refatorado** vai para pasta própria — não é preciso reescrever o que já funciona, só não adicionar mais arquivos flat nas áreas legadas.

## 1.3 — Componentização: consolidar a campanha que já existe, não começar do zero

**Achado confirmado nesta rodada, com histórico detalhado em `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md` (3.365 linhas):** já existe uma campanha extensa e ativa de redução de arquivos grandes, com régua própria (>700 linhas = atenção, >1000 = prioridade, >1500 = crítico), validada por teste automatizado, em backend, frontend e app-mobile.

**Linha do tempo confirmada:**
- 2026-06-24: pico de **144 arquivos** acima de 700 linhas (58 acima de 1000, 12 acima de 1500).
- 2026-07-07 (batch 56/57): campanha zera o inventário — **0 arquivos** acima de 700 linhas nos 3 produtos. Nasce o teste de guarda `backend/tests/unit/test_application_large_files_guard.py` (`assert oversized == {}`), e o gate ainda mais rígido `test_backend_zero_large_files_refactor.py` (nenhum arquivo do backend acima de **1000** linhas, sem exceção, com testes de identidade de objeto `is` provando que a extração não duplicou lógica).
- 2026-08-22: após novas funcionalidades, o número naturalmente volta a **22-23 arquivos** (entropia esperada de desenvolvimento contínuo, já reconhecida no próprio documento).
- **2026-09-12 (contagem ao vivo feita nesta análise, replicando a lógica exata do teste):** o número subiu para **46 arquivos** ≥700 linhas (24 backend, 17 frontend, **5 app-mobile** — antes zerado). ⚠️ **Nada está acima de 1000 linhas** (o gate mais rígido do backend continua válido), mas o teste de 700 linhas provavelmente **falharia se rodado hoje** — não foi confirmado se ele está ativo/passando no CI atual ou se foi ajustado.

Isso significa: **o problema de "arquivo grande demais" já tem processo, métrica e teste de regressão** — só precisa de mais uma rodada de manutenção, igual às duas anteriores. A ação desta fase não é criar isso — é **retomar a limpeza e dar direção estrutural** a ela:

- [ ] **Confirmar o status atual do teste `test_application_large_files_guard.py` no CI** (passando, falhando, ou desabilitado) — primeira ação concreta, antes de qualquer outra, já que o número real (46) diverge do último registro documentado (22).
- [ ] Priorizar os 5 arquivos mais próximos de 1000 linhas como primeira fatia da nova rodada: `backend/app/clientes/crud_routes.py` (966), `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js` (952), `app-mobile/src/screens/funcionario/pdv/FuncionarioPdvContent.tsx` (945), `backend/app/services/base_catalog_enrichment_service.py` (887), `backend/app/routes/ecommerce_public.py` (885).

- [ ] Ao dividir um arquivo grande, preferir o padrão de pasta por domínio (`routes.py` / `schemas.py` / `services.py` / `queries.py` / `events.py`, já documentado em `docs/BLUEPRINT_BACKEND.md`) em vez de só cortar em pedaços menores sem organização temática. Um arquivo dividido em 3 arquivos igualmente "flat" resolve o teste de linha, mas não resolve a navegabilidade.
- [ ] Escolher 2-3 domínios legados mais "flat" como piloto do padrão de pasta ao serem refatorados: candidatos por volume de arquivos soltos — `banho_tosa_*` (~30 arquivos), `veterinario_*` (~25 arquivos), `estoque_*` (~20 arquivos). `campaigns/`, `vendas/`, `clientes/`, `produtos/`, `intnfe/` já são bons exemplos a copiar (já seguem pasta por domínio).
- [ ] Documentar a decisão como atualização de `docs/BLUEPRINT_BACKEND.md` ou um ADR novo se a régua mudar (critério do próprio `docs/adr/README.md`: "decisão que afeta vários módulos ou PRs").
- [ ] Ao terminar cada domínio migrado para o padrão de pasta, atualizar a [[Matriz-de-Cobertura]] e o respectivo documento em [[Funcionalidades]] com a nova localização de arquivo (evita a documentação da Fase 2 ficar desatualizada).

## 1.4 — Auditoria de duplicação e over-parametrização (preparação para a Fase 2)

Esta análise (fase de reconhecimento) mapeou **estrutura**, não duplicação de lógica linha a linha — isso é trabalho novo desta fase:

- [ ] **Duplicação:** revisar especificamente os arquivos "facade de compatibilidade" já identificados (`produtos_models.py`, `financeiro_models.py`, `estoque_models.py` como agregadores que reexportam de arquivos menores) — confirmar que são *apenas* reexportação (padrão aceitável, documentado em [[Arquitetura]]: "arquivos de compatibilidade podem reexportar nomes antigos... devem ser pequenos e apontar para a implementação modular") e não têm lógica de negócio duplicada dentro deles.
- [ ] Rodar uma ferramenta de detecção de código duplicado (ex.: `jscpd` para frontend, algo equivalente para Python) como checagem pontual — não precisa virar gate de CI imediatamente, mas gera uma lista priorizada de onde a mesma regra de negócio existe em mais de um lugar.
- [ ] **Over-parametrização (o oposto):** ao dividir os arquivos grandes da campanha 700-linhas, identificar funções/serviços com muitos parâmetros booleanos/flags de comportamento (sinal comum de que deveriam ser métodos separados em vez de um método genérico com `if/else` por flag) — não foi feito levantamento específico disso nesta rodada; tratar como parte do trabalho de cada domínio migrado para pasta, não como tarefa isolada.

## 1.5 — Confiabilidade e observabilidade (proposta nova, fora da auditoria original)

A auditoria de 2026-09-12 cobriu segurança, arquitetura e funcionalidades, mas não observabilidade/confiabilidade em produção — é uma lacuna própria, não um risco já catalogado em [[Matriz-de-Riscos]]. Faz sentido tratar aqui, na fase de fundação, porque monitoramento é infraestrutura que as fases seguintes (mapeamento de tela, integrações, segurança) vão depender para saber se algo quebrou:

- [ ] **Error tracking em produção** (ex.: Sentry) — já está listado como "próxima feature" desde `docs/PROXIMO_PASSO.md` (fevereiro/2026) e ainda não foi implementado. Sem isso, bugs em produção só aparecem quando um usuário reclama.
- [ ] **Alerta quando um worker de background para** (`worker-bling`, `worker-catalogo`, ver [[Arquitetura]]) — hoje o sintoma de um worker parado (estoque/catálogo desatualizado) só aparece dias depois. Reaproveitar a integração WhatsApp/WAHA já existente no projeto para notificar o responsável.
- [ ] **Conectar `docs/SLOS_INDICADORES_JORNADAS.md` a dados reais** — confirmar se os indicadores ali definidos já são medidos (dashboard) ou se é só a meta declarada; se for só a meta, é o passo natural depois do error tracking.
- [ ] **Testar restauração de backup, não só a rotina de backup** — [[Pendencias]] já lista RPO/RTO formal como não encontrado. Agendar um exercício periódico de restauração real em ambiente isolado (o workflow `homologacao-isolada.yml` já existe e pode ser reaproveitado para isso). Backup nunca restaurado de verdade é uma suposição, não uma garantia.
- [ ] **Teste de carga básico antes de crescer a base de tenants** — não encontrado em nenhum dos 8 workflows de CI hoje (cobrem lint/teste/segurança/E2E, não carga). Simular picos reais de PDV (ex.: sábado de manhã, múltiplos tenants simultâneos) com uma ferramenta simples (k6, Locust) antes que o volume real force essa descoberta em produção.
- [ ] **Painel de status público, ainda que simples** (ex.: `status.corepet.com.br`, mesmo que atualizado manualmente no início) — reduz o volume de "o sistema caiu?" chegando por canais informais quando um pet shop depende do sistema no caixa.

## Critério de avanço para a Fase 2

- CI/CD com CODEOWNERS e Environments configurados.
- Pelo menos 1 domínio legado piloto migrado para o padrão de pasta (prova de conceito do processo).
- Lista inicial de duplicações confirmadas (mesmo que pequena) registrada em [[Pendencias]] ou nova seção deste roadmap.
- Error tracking em produção ativo (item 1.5) — recomendado, não bloqueante.

## Não identificado

- ❓ Se há alguma ferramenta de análise de complexidade ciclomática já configurada (não encontrada nesta análise) — útil para achar candidatos a "over-parametrização" de forma objetiva em vez de manual.
