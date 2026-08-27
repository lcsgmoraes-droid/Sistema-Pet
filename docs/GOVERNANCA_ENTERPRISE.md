# Governança enterprise do Sistema Pet

Atualizado em: 2026-08-27

Status: fonte oficial para avaliar a preparação organizacional e técnica do
Sistema Pet nas 14 áreas de governança enterprise.

## Resultado executivo

O Sistema Pet possui código-fonte versionado, arquitetura documentada e uma base
técnica que pode evoluir. O diagnóstico não sustenta a ideia de que um sistema
feito com assistência de IA seja, por definição, impossível de manter ou
escalar. A origem do código não substitui os controles de engenharia; são esses
controles que tornam a evolução segura.

Na avaliação atual:

- 3 áreas estão **sólidas** para o estágio atual;
- 9 áreas estão **parcialmente fortes**, com controles reais e pontos de
  consolidação;
- 2 áreas estão **parciais** e entram no plano prioritário de evolução;
- nenhuma área exige reescrita total do sistema.

Esta avaliação complementa o placar técnico de
`docs/MATURIDADE_GERAL_10_10_GUIA.md`. O placar 10/10 registra o fechamento de
frentes internas de engenharia; esta matriz verifica uma camada mais ampla de
governança necessária para crescer com mais clientes, integrações e pessoas.

## Responsabilidades enquanto não houver equipe técnica

Até existir uma equipe de desenvolvimento formal:

- a IA executa análise, implementação, testes, documentação e preparação do PR
  seguindo `AGENTS.md`, `CONTRIBUTING.md` e os gates do repositório;
- o responsável pelo negócio confirma prioridade, regra de negócio e aceite
  quando houver decisão que não possa ser deduzida com segurança;
- produção continua exigindo autorização explícita e separada;
- Git, Pull Requests, CI e evidências formam a trilha auditável do trabalho;
- uma futura pessoa desenvolvedora deve conseguir localizar decisões e provas
  sem depender do histórico de conversas com a IA.

## Significado dos status

| Status | Significado |
|---|---|
| Sólido | Há processo documentado, execução real e validação proporcional ao risco atual. |
| Parcial forte | A capacidade existe, mas falta centralização, meta, responsável ou cobertura completa. |
| Parcial | Há elementos úteis, porém existe uma lacuna que precisa entrar no plano prioritário. |

## Matriz das 14 áreas

| Nº | Área | Status | O que já está coberto | Lacuna e próxima decisão |
|---:|---|---|---|---|
| 1 | Necessidade e requisitos | Parcial | Existem specs por funcionalidade, regras de domínio, `CONTRIBUTING.md` e Definition of Done. | O formato não era único. A ficha `docs/templates/FICHA_ENTREGA.md` passa a registrar problema, usuários, prioridade, requisitos, não funcionais e aceite. |
| 2 | Documentação | Parcial forte | Há índice oficial, mapa do código-fonte, arquitetura, ADRs, guias operacionais, evidências e histórico Git. | Manter novos ADRs para decisões duradouras e aposentar documentos históricos quando forem substituídos. |
| 3 | Arquitetura e tecnologia | Parcial forte | O monólito modular, componentes, multiempresa, dados, worker, deploy e evolução incremental estão em `docs/ARQUITETURA.md`. O catálogo de SLOs define metas técnicas e por jornada; a primeira carga autenticada passou em homologação. | Ampliar volume fictício, medir recursos do host/banco e exercitar integrações antes de aprovar novas faixas de clientes. |
| 4 | Segurança e privacidade | Parcial forte | Autenticação, permissões, tenant, RLS, regras de segredos, logs seguros, alertas e política de privacidade possuem controles reais. O inventário `docs/CATALOGO_DADOS_CRITICOS_LGPD.md` centraliza dados pessoais, finalidade proposta, direitos, retenção, papéis, controles e lacunas. | Aprovar hipóteses legais e papéis por tratamento com apoio jurídico, nomear responsáveis, registrar operadores/suboperadores e ampliar o fluxo de direitos além de clientes. |
| 5 | Dados e banco de dados | Parcial forte | PostgreSQL, SQLAlchemy, migrations Alembic, transações, isolamento, backup, restore smoke, auditoria e retenção técnica estão documentados. O catálogo de dados classifica 16 domínios, criticidade, responsáveis propostos e ciclo de vida. O acompanhamento dos pilotos passa a manter agenda atual e histórico imutável com autor e data. | Aprovar proprietários, retenção por domínio e RPO/RTO; provar backup de arquivos/cópia externa e automatizar descarte/anonimização. |
| 6 | Integrações | Parcial forte | O catálogo `docs/CATALOGO_INTEGRACOES.md` centraliza finalidade, autenticação, timeout, retry, idempotência, fallback, reconciliação, observabilidade, responsáveis, evidências e lacunas das integrações reais. | Corrigir autenticação fail-closed dos webhooks prioritários, exercitar indisponibilidade/replay em homologação e acumular evidência operacional antes de considerar a área sólida. |
| 7 | Desenvolvimento | Sólido | Branch por tarefa, PR, revisão, padrões backend/frontend, migrations, pequenas fatias, regras para IA e Definition of Done estão em `AGENTS.md` e `CONTRIBUTING.md`. | Manter os gates e impedir exceções informais conforme o volume de mudanças crescer. |
| 8 | Qualidade e testes | Sólido | CI de backend, frontend, segurança, smoke, migrations, multiempresa e E2E longo; matriz de testes por risco e evidência obrigatória. | Ampliar regressão funcional e testes de desempenho em homologação sem transformar produção em ambiente de teste. |
| 9 | Ambientes e configuração | Parcial forte | DEV local, homologação descartável, CI e produção estão separados; variáveis e segredos ficam fora do Git; há bootstrap e verificação de ambiente. A homologação já foi usada em entregas reais e na primeira carga autenticada. | Criar staging remoto apenas quando acesso compartilhado, webhooks, HTTPS ou carga contínua justificarem o custo. |
| 10 | Homologação | Parcial forte | Há ambiente isolado com PostgreSQL próprio, build de produção, migrations, tenant fictício, E2E, capacidade autenticada, modelo de aceite e evidências reais. | Repetir o processo nas entregas relevantes e acompanhar inconsistências antes de mudar o status para sólido. |
| 11 | Gestão da mudança e treinamento | Parcial | Há Central de Ajuda, novidades, onboarding, guias de implantação e materiais por funcionalidade. | Tornar obrigatória a avaliação de impacto, comunicação, manual e treinamento em cada mudança visível ao usuário. A ficha de entrega inclui esse gate. |
| 12 | Publicação e versões | Sólido | CI/CD, proteção de branch, commit identificável, deploy por usuário restrito, health, backup, migrations, evidência e rollback estão documentados e exercitados. | Manter aprovação explícita de produção e registrar toda exceção ou correção emergencial. |
| 13 | Produção e observabilidade | Parcial forte | Health/watchdog, logs estruturados, `request_id`, auditoria, painel Ops, alertas externos e trilha de deploy estão implementados. O catálogo define objetivos e `ops_journey_events` começa o denominador sanitizado de login, seleção de tenant e venda. | Ampliar a instrumentação às demais jornadas, consolidar disponibilidade externa e criar 30 dias de linha de base antes de aprovar percentuais ou SLA. |
| 14 | Sustentação e incidentes | Parcial forte | A política geral, o registro padrão, P0/P1/P2/P3, responsáveis, comunicação, causa raiz, MTTD/MTTR e melhoria estrutural estão consolidados em `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`; painel Ops, rollback e evidências apoiam a execução. A fila dos pilotos agora agenda contatos e preserva notas internas por empresa. | Usar o processo no próximo incidente real, revisar métricas mensalmente e registrar a primeira evidência antes de mudar o status para sólido. |

## Evidências principais usadas na avaliação

- Código-fonte e histórico: `docs/MAPA_CODIGO_FONTE.md`.
- Arquitetura e escala: `docs/ARQUITETURA.md` e
  `docs/TESTE_CAPACIDADE_SEGURO.md`.
- Desenvolvimento: `AGENTS.md`, `CONTRIBUTING.md` e
  `.github/pull_request_template.md`.
- Testes e segurança: `.github/workflows/`,
  `docs/auditorias/testes-ci-cobertura-critica.md` e
  `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`.
- Produção: `docs/PRODUCAO_DEPLOY_SSH.md`,
  `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` e
  `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`.
- Logs e auditoria: `docs/RETENCAO_LOGS_AUDITORIA.md` e
  `docs/PADRAO_EVIDENCIA.md`.
- Multiempresa: `docs/CONTRATO_MULTITENANT_E_ONBOARDING.md`.
- Suporte e aceite inicial:
  `docs/comercial/PACOTE_PILOTO_PLANO_BASICO.md` e
  `docs/implantacao/CHECKLIST_PLANO_BASICO_PILOTO.md`.
- Treinamento e comunicação: `docs/CENTRAL_AJUDA_E_NOVIDADES.md`.
- Integrações e modos de falha: `docs/CATALOGO_INTEGRACOES.md`.
- Dados críticos e privacidade: `docs/CATALOGO_DADOS_CRITICOS_LGPD.md`.
- SLOs e indicadores por jornada: `docs/SLOS_INDICADORES_JORNADAS.md`.

## Gate proporcional por mudança

Nem todo PR precisa produzir a mesma quantidade de documentação.

| Tipo de mudança | Controle mínimo |
|---|---|
| Correção pequena sem mudança de regra | Problema, causa, teste de regressão, risco e rollback no PR. |
| Nova funcionalidade ou mudança de regra | `docs/templates/FICHA_ENTREGA.md` preenchida e critérios de aceite testáveis. |
| Integração, migration, segurança ou arquitetura | Ficha completa, decisão técnica, falhas esperadas, observabilidade, rollback e homologação. |
| Mudança visível ao usuário | Avaliação de comunicação, Ajuda, manual e treinamento. |
| Correção emergencial | Evidência do incidente e ficha completada antes de encerrar a causa raiz. |
| Apenas documentação | PR curto, validação de links/estrutura e indicação clara de que não altera runtime. |

O preenchimento técnico é responsabilidade da IA ou da pessoa que implementa. O
responsável pelo negócio não precisa traduzir a solicitação para termos de
programação.

## Plano priorizado

### P0 — antes de acelerar a entrada de clientes

1. **Padronizar requisitos e homologação.** Implantado neste pacote documental
   pela ficha de entrega, registro de homologação e checklist de PR.
2. **Criar homologação separada de produção.** Implementada como ambiente local,
   isolado e descartável em `docs/HOMOLOGACAO_LOCAL_ISOLADA.md`, respeitando a
   decisão de não contratar um segundo servidor neste estágio. Falta acumular
   evidência de uso em entregas reais.
3. **Consolidar incidentes e sustentação.** Política e modelo implantados em
   `docs/GESTAO_INCIDENTES_SUSTENTACAO.md` e
   `docs/templates/REGISTRO_INCIDENTE.md`. Falta acumular evidência do primeiro
   uso real e da revisão mensal.

### P1 — preparar crescimento controlado

4. **Criar catálogo único de integrações e seus modos de falha.** Implantado em
   `docs/CATALOGO_INTEGRACOES.md`, com controles e lacunas verificados no código.
   Falta executar o endurecimento dos webhooks prioritários e testes de
   indisponibilidade/replay em homologação.
5. **Criar catálogo de dados críticos e inventário LGPD.** Implantado em
   `docs/CATALOGO_DADOS_CRITICOS_LGPD.md`, com 16 domínios, classificação,
   finalidade proposta, papéis, direitos, retenção, continuidade e lacunas
   verificadas no código. Faltam as aprovações jurídica/contábil, responsáveis
   formais, RPO/RTO e automações de descarte antes de considerar a área sólida.
6. **Definir SLOs técnicos e indicadores de negócio por jornada.** Implantado em
   `docs/SLOS_INDICADORES_JORNADAS.md`, com objetivos de plataforma, oito
   jornadas críticas, indicadores de negócio, orçamento de erro, alertas,
   privacidade e plano de instrumentação. Falta coletar o denominador completo,
   formar linha de base de 30 dias e aprovar as metas antes de tratá-las como
   compromisso.
7. **Executar capacidade autenticada em homologação.** Executor somente leitura,
   bloqueio de produção e degraus iniciais 320/8 e 396/12 implantados. Faltam
   massa representativa, recursos do host/banco e degraus maiores antes de
   prometer nova faixa de escala.

### P2 — preparar entrada de mais pessoas e processos

8. **Criar registro curto de decisões arquiteturais duradouras.** Índice e três
   ADRs iniciais implantados em `docs/adr/README.md`; novos registros seguem o
   mesmo formato quando uma decisão for transversal ou difícil de reverter.
9. Formalizar comunicação, treinamento e notas de versão para mudanças de maior
   impacto.
10. Revisar a matriz a cada trimestre ou antes de uma expansão relevante de
    clientes, equipe, infraestrutura ou integrações.

## Critério de avanço

Uma ação desta matriz só muda para sólida quando houver:

1. documento oficial e responsável definido;
2. processo usado em uma entrega real;
3. evidência verificável no Git, CI ou operação;
4. rotina de manutenção;
5. ausência de dependência em memória ou conversa privada.

