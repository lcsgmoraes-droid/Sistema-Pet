# Ficha de entrega — telemetria de jornadas críticas

## Identificação

| Campo | Valor |
|---|---|
| Título | Medição sanitizada de login, seleção de empresa e finalização de venda |
| Data | 2026-08-26 |
| Responsável de negócio | Responsável pelo Sistema Pet |
| Executor técnico | IA |
| Issue/PR | Branch `feat/20260826-1638-telemetria-jornadas-login-venda`; PR a registrar após o push |
| Prioridade | P1 |
| Risco | Médio: inclui middleware HTTP, migration e painel administrativo; a coleta é fail-open e não altera regras comerciais |
| Domínios afetados | Autenticação, vendas, observabilidade, dados técnicos e painel Ops |

## 1. Necessidade e requisitos

- Problema: havia logs e alertas, mas faltavam tentativa, denominador, taxa de
  sucesso e latência das jornadas críticas. Sem isso não era possível provar a
  qualidade percebida pelo cliente nem estabelecer SLOs com base real.
- Usuários afetados: empresas usuárias nas jornadas medidas e administração da
  plataforma no painel Ops.
- Resultado esperado: medir login, seleção de empresa e finalização de venda no
  web/app, distinguindo rejeição esperada de falha do sistema.
- Requisitos funcionais:
  - registrar um evento terminal por tentativa nas rotas selecionadas;
  - agrupar tentativas, sucessos, rejeições esperadas e falhas;
  - calcular taxa de sucesso, p50, p95, p99 e máximo;
  - exibir o resultado no painel Ops e disponibilizar lista/resumo na API admin;
  - identificar amostra pequena até 99 operações elegíveis;
  - reconhecer replay idempotente como conclusão bem-sucedida.
- Requisitos não funcionais: nenhum corpo de requisição, e-mail, documento,
  valor, item ou conteúdo livre; acesso administrativo; índices de agregação;
  coleta leve e fail-open; compatibilidade com múltiplas empresas.
- Comportamentos preservados: contratos HTTP, autenticação, seleção de tenant,
  transação/idempotência da venda e telas dos clientes.
- Fora do escopo: alertas automáticos por SLO, purge automatizado, agregação
  histórica, demais jornadas e aprovação definitiva de SLA.
- Critérios de aceite: migration chega a um único `head`; três jornadas são
  reconhecidas; evento é sanitizado; falha da telemetria não muda a resposta;
  rejeição 4xx não reduz o numerador elegível; painel compila; PostgreSQL e E2E
  de homologação passam.

## 2. Regras de negócio e dados

- Não foi alterada regra comercial. Resultado 2xx/3xx é sucesso, 4xx é rejeição
  esperada e 5xx/exceção é falha do sistema.
- A plataforma é responsável pela telemetria; a empresa continua responsável
  pelos dados comerciais de origem.
- O evento guarda somente jornada, resultado, motivo técnico, duração, status,
  template da rota e identificadores técnicos de tenant/request/operação.
- Não guarda payload, parâmetros de venda, credenciais nem identificação direta
  de cliente, funcionário ou usuário.
- `tenant_id` é uma etiqueta técnica opcional em tabela operacional global. A
  tabela está classificada nas catracas ORM/PostgreSQL e só é exposta em rota de
  administrador da plataforma.
- Migration `zxe20260826a1` cria `ops_journey_events` com chave única e índices
  por jornada/data, tenant/jornada/data e resultado/data.
- Retenção proposta: detalhe no banco por 90 dias, agregado anônimo por 24 meses
  e JSONL por 30 dias, conforme `docs/RETENCAO_LOGS_AUDITORIA.md`.
- Integridade: chave única evita importar duas vezes o mesmo evento; replay da
  venda mantém uma única operação comercial e é marcado tecnicamente.

## 3. Arquitetura e integrações

- O middleware comum mede o resultado depois da execução da rota, evitando
  duplicar código e alterar handlers de negócio.
- No caminho do cliente há somente append de uma linha JSONL sanitizada. O banco
  é sincronizado quando o módulo Ops consulta os dados, de modo que uma falha de
  banco de observabilidade não bloqueie login ou venda.
- O painel recebe a agregação pelo contrato já existente de `ops-summary`; os
  endpoints de lista/resumo permitem diagnóstico administrativo específico.
- Alternativa descartada nesta fatia: persistir sincronicamente no banco em toda
  request, pois adicionaria latência e dependência desnecessária à jornada.
- Sistemas externos: não se aplica. A entrega usa backend, PostgreSQL e frontend
  já existentes.
- Indisponibilidade da telemetria: o evento pode deixar de ser coletado, mas a
  operação do cliente termina normalmente; o diagnóstico usa logs/health.

## 4. Segurança e privacidade

- Rotas de observabilidade permanecem protegidas por `require_platform_admin`.
- O token usado apenas para extrair `tenant_id` é validado com assinatura; token
  inválido não produz identidade e nunca é gravado.
- A tabela é global por desenho para análise cross-tenant, com justificativa e
  testes nas três listas de controle multempresa.
- Segredos/configurações: apenas caminhos e limite de leitura configuráveis;
  nenhum segredo novo.
- Permitido: códigos técnicos fechados, duração, status, template e UUIDs
  técnicos. Proibido: body, e-mail, senha, documento, IP, user-agent, conteúdo do
  cliente/venda ou identificador numérico presente na URL real.
- Classificação: DAD-013 do catálogo de dados. Finalidade operacional de
  disponibilidade e diagnóstico; retenção ainda depende de validação jurídica e
  do job de purge previsto.
- Testes verificam sanitização, template sem ID real, autorização central das
  rotas, exceção global de tenant e comportamento fail-open.

## 5. Desenvolvimento e qualidade

- Fatia 1: modelo/migration e coletor sanitizado.
- Fatia 2: agregação, API administrativa e painel Ops.
- Fatia 3: classificação multempresa, documentação e homologação PostgreSQL/E2E.
- Testes unitários: rotas reconhecidas, classificação, percentis, meta, amostra,
  falha de escrita e middleware.
- Testes de integração/banco: cadeia completa de migrations em PostgreSQL limpo,
  sincronização real de quatro eventos e verificação do `head`.
- Testes de contrato/API: campos permitidos, ausência de payload, endpoints,
  painel, replay idempotente e documentação.
- Testes multiempresa/permissão: registro ORM e catraca RLS sem dívida inesperada;
  endpoints herdam a proteção global de administrador da plataforma.
- Testes E2E/regressão: plano básico com login, seleção de tenant e finalização
  de venda fictícia.
- Resultados em 2026-08-26: 40 testes focados aprovados após o reforço fail-open;
  Ruff aprovado; Prettier aprovado; ESLint aprovado; build Vite aprovado; E2E
  aprovado; PostgreSQL em `zxe20260826a1 (head)`.

## 6. Ambientes e homologação

- Variáveis: `JOURNEY_EVENT_LOG_PATH` e
  `JOURNEY_EVENT_REPORT_MAX_READ_LINES`, com defaults seguros documentados e
  passagem explícita no compose de produção.
- Ambiente: homologação Docker local isolada, PostgreSQL 14, imagens novas de
  backend/frontend e volume descartável, sem acesso à produção.
- Massa: tenant, usuário e venda fictícios criados pelo fluxo oficial.
- Registro: `docs/homologacoes/2026-08-26-telemetria-jornadas-login-venda.md`.
- Pendências não bloqueantes: criar purge/agregação, expandir jornadas e formar
  30 dias de linha de base antes de ratificar metas.

## 7. Publicação e rollback

- Tipo: backend, frontend, migration, configuração e documentação; sem alteração
  mobile nativa ou OTA.
- Commit/versão: será identificado no fechamento da branch e no PR.
- Ordem: backup/release check existente, migration aditiva, backend e frontend.
  Código anterior ignora a nova tabela; a migration não altera tabelas de negócio.
- Plano: merge após CI verde; pedir autorização explícita; executar deploy
  oficial; verificar health, `alembic current`, painel Ops e geração de evento
  controlado; monitorar logs.
- Abortar/reverter se migration falhar, health não ficar verde, houver erro de
  login/venda ou crescimento anormal do log.
- Rollback: restaurar a versão anterior do código/frontend. A tabela aditiva pode
  permanecer sem uso para preservar dados; downgrade que apaga a tabela somente
  com decisão explícita e backup.

## 8. Observabilidade e sustentação

- Sinais: JSONL, `ops_journey_events`, API admin e painel com tentativas,
  elegíveis, rejeições, falhas, taxa de sucesso e percentis.
- Sucesso da entrega: eventos reais começam a formar denominador sem alterar a
  jornada e o painel distingue amostra pequena de meta aprovada.
- Falhas previsíveis: disco indisponível perde telemetria sem bloquear cliente;
  banco indisponível usa leitura do JSONL no painel; linha corrompida é ignorada.
- Incidente: P1 se login/venda forem afetados; P2/P3 se apenas a medição estiver
  temporariamente incompleta, conforme impacto e duração.
- Alternativa operacional: health/logs/alertas anteriores continuam ativos.
- Recorrência vira melhoria estrutural se houver perda frequente, custo de
  sincronização, volume acima do limite ou necessidade de worker/fila dedicada.

## 9. Mudança, comunicação e treinamento

- Nenhuma rotina ou tela comum dos clientes muda.
- A administração ganha uma seção no painel Ops; a referência é
  `docs/SLOS_INDICADORES_JORNADAS.md`.
- Comunicação ao cliente e treinamento não são necessários nesta fatia.
- A operação deve saber que “amostra pequena” é esperado antes de 100 operações
  elegíveis e que 30 dias são necessários para consolidar a primeira linha base.

## 10. Fechamento

- [x] Critérios de aceite atendidos.
- [x] Testes e evidências registrados.
- [x] Tenant, permissões, dados e auditoria preservados.
- [x] Documentação oficial atualizada.
- [x] Homologação registrada.
- [x] Publicação, observabilidade e rollback definidos.
- [x] Comunicação/treinamento avaliados.
- [x] PR revisável, sem segredo, backup, dump ou artefato indevido.

Decisão final: aprovado tecnicamente para merge. Produção continua condicionada
à autorização explícita separada.

Pendências: PR/commit serão registrados no fechamento; purge/agregação, ampliação
das jornadas e revisão de metas seguem no backlog enterprise.
