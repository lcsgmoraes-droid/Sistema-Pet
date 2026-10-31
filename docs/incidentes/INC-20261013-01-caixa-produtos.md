# Registro de incidente: caixa e listagem de produtos

## Identificação

| Campo | Valor |
|---|---|
| Incidente | INC-20261013-01 |
| Título factual | Falhas intermitentes em consultas autenticadas e aviso incorreto de caixa fechado |
| Ambiente | Produção; investigação por leitura e mitigações publicadas após autorização explícita de Lucas |
| Severidade atual | P1 no período relatado, por bloqueio da jornada de caixa; serviço atualmente recuperado, causa interna ainda em investigação |
| Estado | Em observação; mitigações publicadas, causa histórica não confirmada |
| Coordenador | Lucas |
| Executor técnico | Codex |
| Responsável do negócio | Lucas |

## Impacto confirmado

- Início observado nos registros de exceção: 13/10/2026 às 14:33:45 BRT.
- Última exceção observada no intervalo investigado: 15:45:17 BRT.
- Detecção e reconhecimento: relato de Lucas na conversa de 13/10/2026; horário formal não registrado.
- Jornadas afetadas: consulta do caixa no PDV, listagem e busca de produtos, outras rotas autenticadas.
- Alcance: registros em várias empresas; 28 exceções em `/caixas/aberto` na empresa do relato de caixa e três na listagem `/produtos/`. Não equivalem a contagem de usuários nem comprovam 28/741 respostas HTTP 500.
- O caixa aberto do dia na empresa consultada não tinha registro de fechamento. O modo é individual: a existência de caixa de um operador não autoriza outro operador a utilizá-lo.
- Alternativa segura: nova consulta autenticada; não reabrir ou lançar recebimentos supondo um fechamento que não foi confirmado.
- Não foi identificado, nesta investigação, fechamento automático, perda de dados ou acesso entre empresas. Essa leitura não constitui auditoria completa dessas condições.

## Linha do tempo

| Data/hora BRT | Estado/ação | Evidência | Responsável |
|---|---|---|---|
| 13/10/2026 14:33:45–15:45:17 | Exceções internas registradas | `backend/logs/error_events.jsonl` | Sistema |
| 13/10/2026 15:45–15:46 | Interrupção durante atualização já realizada antes desta investigação | 78 respostas 502 no nginx e início dos novos processos | Histórico operacional |
| 13/10/2026 após 15:46 | Sem novas exceções do mesmo tipo até a última leitura desta investigação | Logs persistentes; health; containers | Codex, leitura autorizada |
| 13/10/2026, durante a tarefa | Correções e testes em cópia isolada | Branch `codex/caixa-monitoramento` | Codex |
| 13/10/2026 16:48:58 | PR #1492 mergeado após aprovação de Lucas para merge e deploy | Commit `a2f9f63b4822e0cea71e0dc7f8457f57c06afcd5` | Lucas/Codex |
| 13/10/2026 16:54–17:00:53 | Publicação pelo script oficial concluída com código zero | Backup operacional `/opt/petshop/backups/deploy_20261013_165414`; evento `success/concluido` | Codex, execução autorizada |
| 13/10/2026 17:01–17:03 | Serviços saudáveis e jornadas publicadas verificadas por leitura | Containers, watchdog interno, readiness, PDV, produtos e painéis Ops | Codex |
| 13/10/2026 17:04 | Escopo individual do caixa confirmado por leitura com RLS | Caixa #387 aberto para operador 84; operador 83 recebe `null` legítimo | Codex |
| 13/10/2026 17:06:14 | Checagem final de estabilidade, mais de cinco minutos após o deploy | Backend saudável, sem reinício/OOM; zero novos 5xx e Git limpo | Codex, leitura auditada |

## Evidências técnicas

- Request de caixa exemplificativo: `d3d77550-5819-45bf-b48b-2bad70a1c2ad`, às 15:42:37 BRT.
- Request de listagem exemplificativo: `641159ec-14f4-43ca-a940-4da61e259589`, às 15:41:53 BRT.
- Versão durante a investigação inicial: `1bc5bb221851fbe14538202edb80b95dbd70e1bc`; versão publicada nesta entrega: `a2f9f63b4822e0cea71e0dc7f8457f57c06afcd5`.
- 741 exceções no intervalo de hoje: 727 `RuntimeError` e 14 `InvalidRequestError`. Os eventos legados omitem status HTTP, mensagem e origem.
- `/api/health/ready` retornou HTTP 200 e banco `ok`; os containers atuais estavam saudáveis, sem OOM ou reinício desde a atualização. Recursos de memória e disco disponíveis.
- Nenhuma ação de reinício dos watchdogs nos últimos sete dias. Paradas/inícios registrados coincidiram com atualizações.
- Evidência preservada: logs originais no servidor, sem edição/purga; script local de reprodução em `runtime/repro_auth_state.py`, ignorado pelo Git, com dados sintéticos.
- Hipóteses não reproduzidas: autenticação sem contexto, inicialização de mappers, consultas fiscais com tabela opcional ausente, campos obrigatórios nulos em produtos, cancelamentos de sockets como explicação dos 727 registros.
- Validação após publicação, 17:01–17:03 BRT: todos os containers saudáveis, zero reinícios e `OOMKilled=false`; watchdog interno com banco conectado e latência de 4,4 ms; readiness HTTP 200 com banco `ok`; Git do servidor limpo.
- Schema existente preservado em `zzzn20261009a1`, sem migration nova nesta entrega; validação RLS no-debt aprovada.
- Navegador, sessão autorizada do Atacadão: PDV com caixa #230 aberto, menu apontando para o mesmo caixa e recebimento habilitado; GET compacto HTTP 200. Listagem de produtos HTTP 200, com 100 produtos renderizados de 6.897 totais. Nenhuma venda ou recebimento foi criado na validação.
- Ops e Incidentes exibem as novas categorias. Foram observados 770 registros sem status na janela de 24 horas, mais ampla que o intervalo de 741 exceções investigado hoje; nenhuma dessas contagens significa 741/770 respostas HTTP 500 comprovadas.
- Desde o início do backend em `2026-10-13T19:59:55.825751245Z` (16:59:55 BRT), até a leitura de 17:03 BRT: 11 eventos de lentidão, zero 5xx registrados pela aplicação, zero falhas sem status, zero respostas incompletas e zero cancelamentos registrados. Essa janela curta não confirma resolução da causa histórica.
- A janela desta publicação teve 68 respostas 502 transitórias no nginx durante a inicialização. Elas pertencem à camada de proxy e não devem ser confundidas com a contagem de exceções/5xx da aplicação. Após a inicialização, os serviços estavam saudáveis e sem reinícios.
- Watchdog externo: às 17:01:03 BRT registrou `2/3` durante `health=starting`; às 17:02:03, checagens pública e interna aprovadas, sem ações, com aviso de 5xx recentes sem falha ativa. O contador voltou a zero e nenhum reinício foi executado.
- Leitura de 17:04 BRT com RLS: `caixa_compartilhado=false`, caixa #387 ainda aberto para o operador 84; o operador 83 recebe `null` legítimo, enquanto o operador 84 vê seu caixa. Confirmação de ausência para outro operador não deve ser confundida com fechamento do caixa do dono.
- Checagem final às 17:06:14 BRT, mais de cinco minutos após a conclusão do deploy: 12 eventos novos desde o início do backend, todos de lentidão; zero 5xx, falhas sem status, respostas incompletas ou cancelamentos registrados pela aplicação. Logs do nginx desde `2026-10-13T20:00:53Z` (17:00:53 BRT, fim do deploy) também sem HTTP 5xx.
- Na checagem final, backend saudável, zero reinícios, `OOMKilled=false` e mesmo `StartedAt`; watchdog interno `healthy`, banco conectado e latência de 1,56 ms; readiness HTTP 200 com banco `ok`. Commit publicado correto, gate `passed` com evidência gerada às `2026-10-13T19:54:17.790366Z`, e Git do servidor limpo confirmado em leitura auditada às 17:06 BRT. A observação curta valida a estabilidade inicial das mitigações, sem confirmar a causa histórica.

## Contenção e recuperação

- A investigação inicial foi somente por leitura. Após aprovação explícita de Lucas, as mitigações foram publicadas pelo procedimento oficial; a validação funcional não criou vendas, recebimentos nem movimentações de caixa.
- A atualização das 15:46 precedeu a investigação e a recuperação observada; não se atribui a recuperação dos 727 registros à correção específica de bipagem dessa versão.
- Correção publicada: consulta compacta única no PDV; erro/desconhecido separados de caixa fechado; resposta 204/vazia rejeitada; uma repetição somente de GET transitório; respostas antigas descartadas na troca de usuário/empresa.
- Movimentações em outra aba preservam o formulário e o caixa confirmado; abertura/fechamento relevante revalidam o estado. Saldo de sangria pendente não é exibido como zero.
- Monitoramento: resposta ASGI real observada, 5xx/desconexão/registro legado/stream incompleta separados, origem técnica segura e PID, persistência em thread e sessão próprias.
- PR: #1492 mergeado; commit publicado `a2f9f63b4822e0cea71e0dc7f8457f57c06afcd5`.
- Autorização: Lucas aprovou explicitamente diagnóstico SSH, correções, merge e deploy. Publicação concluída às 17:00:53 BRT.
- Evidências de recuperação: backup operacional `/opt/petshop/backups/deploy_20261013_165414` e dump anterior às migrations `/opt/petshop/backups/db/petshop_prod_20261013_165857.dump`.
- Rollback disponível: procedimento oficial e retorno à versão anterior aprovada, sujeito à autorização e à revisão de compatibilidade. Não houve migration nova nesta correção.
- Regressão local: caixa aberto/falha/recuperação, caixa confirmado ausente, mudança de contexto, concorrência, fechamento por outra aba, saldo pendente, status HTTP real, cancelamentos e isolamento.

## Comunicação

| Data/hora BRT | Público/canal | Fato informado | Próxima atualização |
|---|---|---|---|
| 13/10/2026, conversa da tarefa | Lucas/Chat Codex | Falhas confirmadas, defeito de exibição do caixa, lacuna de contagem e ausência de causa interna comprovada | Resultado dos gates e validação publicada |
| 13/10/2026, após publicação | Lucas/Chat Codex | Merge/deploy aprovados e executados; serviços e jornadas validados; causa histórica permanece não confirmada | Observação pós-publicação e investigação caso surja nova exceção |

## Causa raiz

- Sintoma: caixa aparenta fechar/reabrir e consultas de produtos falham.
- Causa imediata confirmada do aviso incorreto: o PDV convertia qualquer falha ou resposta vazia da consulta em `false`, sem confirmação de fechamento.
- Carga desnecessária confirmada: PDV e menu consultavam estado separadamente, com serialização de movimentações; passam a compartilhar GET compacto.
- Lacuna confirmada: exceções eram registradas sem status e ficavam fora do contador 5xx; produção também removia o ponto de origem. Registros antigos permanecem classificados como desconhecidos.
- Risco técnico corrigido: persistência síncrona de telemetria no event loop; nova camada observa ASGI sem criar outra tarefa/stream de `BaseHTTPMiddleware`.
- Causa dos 727 `RuntimeError` e do erro interno de produtos: **não confirmada**. Reproduções com PostgreSQL/RLS, duas empresas sintéticas, configuração estrita e concorrência não reproduziram o incidente. Não foram afrouxadas guardas de tenant ou autenticação.
- Risco residual: a exceção interna pode retornar; novo diagnóstico fornece código, processo e arquivo/função/linha sem mensagem, SQL, variáveis locais ou segredos.

## Métricas

| Métrica | Valor |
|---|---|
| MTTD/MTTA/MTTC | Não calculados: horários formais de detecção e contenção indisponíveis |
| Intervalo observado das exceções | Aproximadamente 71 minutos |
| Recuperação observada | Após a atualização das 15:46; causa da recuperação não comprovada |
| Reprodução PostgreSQL/RLS | 226 respostas HTTP 200 e 20 HTTP 429 esperados pelo limitador; zero RuntimeError/InvalidRequestError |
| Consulta real do caixa PostgreSQL/RLS | 30 GETs compactos concorrentes HTTP 200; dono vê caixa, outros operadores/empresas veem null legítimo; zero consultas de movimentações |
| Reprodução de desconexão TCP | 70 conexões locais abortadas, sem reprodução da exceção histórica |
| Janela após início do backend publicado, até 17:03 BRT | 11 eventos de lentidão; zero 5xx, falhas sem status, respostas incompletas ou cancelamentos registrados pela aplicação |
| Janela após início do backend publicado, até 17:06:14 BRT | 12 eventos, todos de lentidão; zero 5xx, falhas sem status, respostas incompletas ou cancelamentos registrados pela aplicação; zero HTTP 5xx no nginx após o fim do deploy |
| Janela do deploy desta entrega | 68 respostas 502 transitórias no nginx; sem reinício após inicialização |

## Ações preventivas

Validação desta entrega (13/10/2026, Codex, desenvolvimento isolado):

- Comando: `pytest` nas suítes de caixa, contexto HTTP, sanitização, observabilidade e isolamento de tenant; `node --test` nos testes do monitor e renderização; `npm run build`.
- Resultado: 52 testes Python e 21 testes frontend passaram; Ruff e build de produção passaram.
- Gate local completo: 203 testes smoke aprovados e dois ignorados, 760 testes multi-tenant e 93 testes mobile aprovados.
- GitHub: oito checks obrigatórios aprovados no SHA de merge `a2f9f63b4822e0cea71e0dc7f8457f57c06afcd5`; a aprovação do head do PR não foi usada como substituto do gate do commit publicado.
- Evidência: testes versionados desta entrega e `runtime/frontend-build-final.log` local, ignorado pelo Git.
- Impacto: mitigações publicadas em produção por procedimento autorizado; schema existente preservado e jornada validada sem operações financeiras de teste.
- Próxima ação: manter observação da versão publicada e investigar a origem de eventual nova exceção com o diagnóstico seguro, sem declarar resolvida a causa histórica.

| Ação | Tipo | Prioridade | Responsável | Prazo | Issue/PR | Estado |
|---|---|---|---|---|---|---|
| Corrigir consulta e estado do caixa; testes de falha/recuperação | Código/teste | P1 | Codex | Esta entrega | PR #1492 | Publicada e validada |
| Corrigir observação da resposta e classificação dos eventos | Código/teste | P1 | Codex | Esta entrega | PR #1492 | Publicada e validada |
| Localizar origem de eventual nova exceção e corrigir somente a causa reproduzida | Diagnóstico/código | P1 | Codex/Lucas | Quando nova evidência estiver disponível | Este incidente | Aberta |
| Validar jornada de caixa e produtos no ambiente publicado | Homologação | P1 | Lucas/Codex | 13/10/2026 17:01–17:03 BRT | PR #1492 | Concluída por leitura |
| Observar estabilidade após publicação, preservando a lacuna histórica | Monitoramento | P1 | Codex/Lucas | Após publicação | Este incidente | Em observação |

## Encerramento

- [x] Impacto e intervalo observado delimitados com as limitações registradas.
- [x] Causas comprovadas e hipóteses não confirmadas separadas.
- [x] Ações preventivas e responsáveis registrados.
- [x] Retenção normal preservada; nenhuma purga executada.
- [x] Nenhum segredo ou dado pessoal desnecessário incluído.
- [x] Correção publicada e jornadas de caixa/produtos validadas em produção.
- [ ] Origem da exceção interna identificada ou risco residual aceito por Lucas.

Decisão: manter em observação; mitigações publicadas e validadas, causa histórica não confirmada.
