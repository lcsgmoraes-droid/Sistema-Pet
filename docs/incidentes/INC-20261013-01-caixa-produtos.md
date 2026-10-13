# Registro de incidente: caixa e listagem de produtos

## Identificação

| Campo | Valor |
|---|---|
| Incidente | INC-20261013-01 |
| Título factual | Falhas intermitentes em consultas autenticadas e aviso incorreto de caixa fechado |
| Ambiente | Produção investigada somente por leitura; correções em desenvolvimento isolado |
| Severidade atual | P1 no período relatado, por bloqueio da jornada de caixa; serviço atualmente recuperado, causa interna ainda em investigação |
| Estado | Em correção; publicação pendente de autorização |
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

## Evidências técnicas

- Request de caixa exemplificativo: `d3d77550-5819-45bf-b48b-2bad70a1c2ad`, às 15:42:37 BRT.
- Request de listagem exemplificativo: `641159ec-14f4-43ca-a940-4da61e259589`, às 15:41:53 BRT.
- Versão publicada durante a leitura: `1bc5bb221851fbe14538202edb80b95dbd70e1bc`.
- 741 exceções no intervalo de hoje: 727 `RuntimeError` e 14 `InvalidRequestError`. Os eventos legados omitem status HTTP, mensagem e origem.
- `/api/health/ready` retornou HTTP 200 e banco `ok`; os containers atuais estavam saudáveis, sem OOM ou reinício desde a atualização. Recursos de memória e disco disponíveis.
- Nenhuma ação de reinício dos watchdogs nos últimos sete dias. Paradas/inícios registrados coincidiram com atualizações.
- Evidência preservada: logs originais no servidor, sem edição/purga; script local de reprodução em `runtime/repro_auth_state.py`, ignorado pelo Git, com dados sintéticos.
- Hipóteses não reproduzidas: autenticação sem contexto, inicialização de mappers, consultas fiscais com tabela opcional ausente, campos obrigatórios nulos em produtos, cancelamentos de sockets como explicação dos 727 registros.

## Contenção e recuperação

- Nenhum reinício, alteração de dados, credencial ou deploy foi executado nesta investigação.
- A atualização das 15:46 precedeu a investigação e a recuperação observada; não se atribui a recuperação dos 727 registros à correção específica de bipagem dessa versão.
- Correção preparada: consulta compacta única no PDV; erro/desconhecido separados de caixa fechado; resposta 204/vazia rejeitada; uma repetição somente de GET transitório; respostas antigas descartadas na troca de usuário/empresa.
- Movimentações em outra aba preservam o formulário e o caixa confirmado; abertura/fechamento relevante revalidam o estado. Saldo de sangria pendente não é exibido como zero.
- Monitoramento: resposta ASGI real observada, 5xx/desconexão/registro legado/stream incompleta separados, origem técnica segura e PID, persistência em thread e sessão próprias.
- PR: em preparação na branch `codex/caixa-monitoramento`; commit: consultar histórico desta entrega.
- Autorização: Lucas autorizou diagnóstico SSH e correções; deploy ainda não autorizado.
- Rollback proposto: procedimento oficial e retorno à versão anterior aprovada. Não há migration nesta correção.
- Regressão local: caixa aberto/falha/recuperação, caixa confirmado ausente, mudança de contexto, concorrência, fechamento por outra aba, saldo pendente, status HTTP real, cancelamentos e isolamento.

## Comunicação

| Data/hora BRT | Público/canal | Fato informado | Próxima atualização |
|---|---|---|---|
| 13/10/2026, conversa da tarefa | Lucas/Chat Codex | Falhas confirmadas, defeito de exibição do caixa, lacuna de contagem e ausência de causa interna comprovada | Resultado dos gates e aprovação de publicação |

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

## Ações preventivas

Validação desta entrega (13/10/2026, Codex, desenvolvimento isolado):

- Comando: `pytest` nas suítes de caixa, contexto HTTP, sanitização, observabilidade e isolamento de tenant; `node --test` nos testes do monitor e renderização; `npm run build`.
- Resultado: 52 testes Python e 21 testes frontend passaram; Ruff e build de produção passaram.
- Evidência: testes versionados desta entrega e `runtime/frontend-build-final.log` local, ignorado pelo Git.
- Impacto: correções somente no código da branch; produção preservada.
- Próxima ação: gates do PR, autorização de publicação e validação da jornada publicada; manter investigação da exceção histórica.

| Ação | Tipo | Prioridade | Responsável | Prazo | Issue/PR | Estado |
|---|---|---|---|---|---|---|
| Corrigir consulta e estado do caixa; testes de falha/recuperação | Código/teste | P1 | Codex | Esta entrega | Branch desta entrega | Preparada |
| Corrigir observação da resposta e classificação dos eventos | Código/teste | P1 | Codex | Esta entrega | Branch desta entrega | Preparada |
| Localizar origem de eventual nova exceção e corrigir somente a causa reproduzida | Diagnóstico/código | P1 | Codex/Lucas | Após publicação autorizada e evidência disponível | Este incidente | Aberta |
| Validar jornada de caixa e produtos no ambiente publicado | Homologação | P1 | Lucas/Codex | Após deploy autorizado | Este incidente | Pendente |

## Encerramento

- [x] Impacto e intervalo observado delimitados com as limitações registradas.
- [x] Causas comprovadas e hipóteses não confirmadas separadas.
- [x] Ações preventivas e responsáveis registrados.
- [x] Retenção normal preservada; nenhuma purga executada.
- [x] Nenhum segredo ou dado pessoal desnecessário incluído.
- [ ] Correção publicada e jornadas de caixa/produtos validadas em produção.
- [ ] Origem da exceção interna identificada ou risco residual aceito por Lucas.

Decisão: manter em correção/observação; não declarar a causa interna resolvida.
