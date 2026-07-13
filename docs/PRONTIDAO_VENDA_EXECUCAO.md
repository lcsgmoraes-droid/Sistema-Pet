# Prontidao para venda - plano de execucao

Atualizado em: 2026-07-13

## Objetivo

Preparar o Sistema Pet para os primeiros clientes pagantes sem prometer maturidade
enterprise antes das evidencias tecnicas, operacionais e comerciais necessarias.

Este plano nao executa deploy de producao automaticamente. Em 2026-07-13, o
responsavel autorizou a preparacao da subida, condicionada ao aviso previo quando
existir uma fatia tecnicamente segura.

## Escopo atual

Entram nesta etapa:

- estabilidade do Plano Basico;
- seguranca de autenticacao, logs e isolamento multiempresa;
- gate de release reproduzivel;
- backup, restore e monitoramento;
- operacao de suporte e onboarding;
- piloto pago e acompanhado com 2 a 5 clientes.

Ficam fora do escopo por decisao de produto neste momento:

- Stone;
- WhatsApp;
- cobranca automatica da assinatura do Sistema Pet.

Esses componentes nao devem receber novas funcionalidades agora. O codigo existente
continua sujeito a verificacoes gerais de qualidade e seguranca para nao quebrar o
restante da aplicacao.

## Gates de liberacao

| Gate | Situacao inicial | Criterio de saida |
| --- | --- | --- |
| G1 - Release reproduzivel | Em execucao | `FLUXO_UNICO.bat release-check` executa qualidade, testes, builds e auditorias sem falso positivo |
| G2 - Seguranca critica | Em execucao | Sem vulnerabilidade bloqueadora, segredo em log ou erro interno exposto |
| G3 - Recuperacao e operacao | Em execucao | Backup externo monitorado e restore recorrente comprovado |
| G4 - Oferta comercial | Pendente | Escopo, contrato, suporte, onboarding e resposta a incidente definidos |
| G5 - Piloto pago | Pendente | 2 a 5 clientes acompanhados, sem incidente critico e com indicadores registrados |
| G6 - Escala enterprise | Futuro | Staging, PITR, testes de carga, monitoramento externo, pentest e governanca formal |

## Evidencias do primeiro ciclo

Executado em 2026-07-13:

- gate rapido aprovado;
- 68 smoke tests aprovados;
- 736 testes multiempresa aprovados;
- cobertura global observada de 32%;
- build de producao do frontend aprovado;
- auditoria do frontend sem vulnerabilidades conhecidas;
- Pillow atualizado de 12.2.0 para 12.3.0;
- auditoria Python sem vulnerabilidades conhecidas apos a atualizacao;
- typecheck mobile aprovado;
- 24 testes mobile aprovados apos atualizar contratos que apontavam para arquivos anteriores a refatoracao;
- auditoria mobile ainda bloqueada por 15 alertas moderados ligados ao Expo 54.

A correcao sugerida para os alertas mobile exige migracao do Expo 54 para o Expo 57.
Essa migracao deve ser executada em pacote proprio, com build Android/iOS e regressao
funcional. Nao deve ser aplicada automaticamente por `npm audit fix --force`.

## Evidencias do segundo ciclo

Executado em 2026-07-13:

- respostas HTTP 5xx de producao e staging deixaram de expor detalhes internos;
- respostas 5xx passaram a preservar o `request_id` para correlacao operacional;
- erros 422 deixaram de registrar corpo, valores submetidos e contexto inseguro;
- eventos do middleware deixaram de persistir a mensagem da excecao em ambientes
  restritos;
- logs do middleware de tenant deixaram de incluir mensagem e stack trace em
  producao e staging;
- 6 testes especificos de sanitizacao aprovados;
- 15 testes de regressao dos middlewares e rotas de analytics aprovados;
- gate rapido, 68 smoke tests e 736 testes multiempresa aprovados apos as mudancas.

Este ciclo reduz um risco critico, mas nao encerra o G2. Ainda faltam as revisoes de
autenticacao, rate limit, confiabilidade do IP de origem e headers HTTP.

## Evidencias do terceiro ciclo

Executado em 2026-07-13:

- backup local diario configurado para 03:15;
- restore controlado semanal configurado para domingo as 04:30;
- exclusao mutua adicionada para impedir backup e restore simultaneos;
- eventos append-only registram apenas horario, status, tamanho, checksum e contagens;
- permissoes ajustadas para o backend nao-root ler a evidencia criada pelo cron;
- cockpit `/ops` passou a classificar backup, restore, RPO e evidencia de RTO;
- ausencia de copia externa permanece visivel como alerta, sem falso estado saudavel;
- 18 testes da area Ops e 2 testes de contrato aprovados;
- sintaxe Bash, lint, formatacao, auditoria frontend e build de producao aprovados;
- gate rapido de release aprovado.

Este ciclo ainda nao encerra o G3. O dump permanece no mesmo servidor ate a escolha
e configuracao de um armazenamento externo. Depois disso, uma execucao real em
producao deve comprovar backup, copia externa, restore e exibicao correta no `/ops`.

## Evidencias do quarto ciclo

Executado em 2026-07-13:

- aplicativo mobile migrado incrementalmente do Expo 54 para o Expo 57;
- React Native atualizado de 0.81 para 0.86 e React atualizado para 19.2;
- dependencias nativas alinhadas pelo `expo install --fix` em cada marco;
- configuracao legada de splash migrada para o plugin `expo-splash-screen`;
- projeto Android regenerado para o SDK 57;
- modulo nativo de compartilhamento restaurado e protegido por teste de contrato;
- auditoria npm mobile passou de 15 alertas moderados para zero;
- typecheck e 25 testes mobile aprovados;
- bundle Android Hermes aprovado com 1.943 modulos.

A compilacao nativa Android ainda precisa ser comprovada por EAS Build, pois o
computador local nao possui JDK. O alerta do `expo-doctor` sobre projeto hibrido e
esperado: Android e versionado por conter modulo nativo proprio, enquanto iOS usa a
configuracao gerada pelo Expo.

## Evidencias do quinto ciclo

Executado em 2026-07-13:

- o Nginx deixou de aceitar `CF-Connecting-IP` de conexoes fora das redes oficiais
  da Cloudflare;
- conexoes diretas passaram a usar obrigatoriamente o IP observado pelo servidor;
- o rate limit do Nginx passou a separar clientes finais, em vez de agrupar todos
  que chegavam pela mesma borda da Cloudflare;
- o backend passou a confiar em `X-Forwarded-For`, `X-Real-IP` e
  `X-Forwarded-Proto` somente quando o par direto pertence a uma rede de proxy
  configurada;
- login, auditoria de autenticacao e solicitacoes LGPD passaram a compartilhar a
  mesma resolucao segura de IP;
- testes focados de IP, autenticacao, erros HTTP, analytics e configuracao de
  producao foram aprovados.

Este ciclo fecha a divida conhecida de confiabilidade do IP de origem. O G2 segue em
execucao ate concluir a revisao final dos fluxos de autenticacao e dos headers HTTP.

## Evidencias do sexto ciclo

Executado em 2026-07-13:

- HTML, API e arquivos publicos passaram a compartilhar uma politica unica de
  headers HTTP de seguranca;
- headers duplicados ou conflitantes foram removidos e a versao do Nginx deixou
  de ser divulgada publicamente;
- CSP, HSTS, protecao contra enquadramento, MIME sniffing e politica de referencia
  foram validados no dominio publico;
- a revisao final confirmou tokens de acesso curtos, refresh token vinculado a
  sessao, revogacao no logout e na troca de senha, bloqueio por falhas de login,
  respostas genericas de recuperacao e tokens de recuperacao armazenados como hash;
- o limite duravel de cinco requisicoes por minuto passou a cobrir tambem cadastro,
  recuperacao de senha, confirmacao de e-mail e os fluxos publicos equivalentes do
  e-commerce, sem depender dos contadores em memoria dos workers do backend.

Com estas evidencias, o G2 atende a linha de base para pilotos controlados. Isso nao
substitui pentest independente nem os controles adicionais previstos no G6 para uma
declaracao enterprise formal.

## G1 - Release reproduzivel

O primeiro pacote adiciona `scripts/validar_release.ps1` ao `release-check` oficial.

O gate completo deve bloquear a liberacao quando falhar qualquer um destes grupos:

- lint e formatacao do backend;
- sincronia do ambiente Python com as dependencias declaradas;
- smoke tests e suite critica multiempresa;
- importacao do backend;
- auditoria de dependencias Python;
- auditoria, lint, formatacao e build do frontend;
- auditoria, typecheck e testes do aplicativo mobile.

A suite completa do backend sera classificada e estabilizada em uma entrega propria.
Ela ainda nao entra no gate enquanto falhas de ambiente, fixtures e falhas funcionais
nao estiverem separadas de forma confiavel. Isso deve ficar visivel como divida, sem
ser usado para declarar a release pronta.

## Observabilidade existente

O cockpit `https://corepet.com.br/ops` e a base oficial de operacao. Nao sera criada
uma segunda central.

Ja existem no cockpit:

- saude atual e historico do periodo;
- conexao e latencia do banco;
- erros 5xx e requisicoes lentas;
- incidentes por rota e por tenant;
- eventos de deploy e watchdog;
- alertas acionaveis, notificacoes e acoes de recuperacao;
- visao operacional dos tenants.

Evolucoes planejadas para o mesmo cockpit:

- copia externa do backup e sua idade (standby por decisao do responsavel em
  2026-07-13; manter o alerta visivel ate a retomada);
- validade do certificado TLS;
- resultado de monitoramento externo;
- versao implantada e estado do gate que autorizou a versao;
- indicadores de RPO e RTO.

## Ordem de execucao

1. Tornar o release-check um gate tecnico real.
2. Corrigir formatacao, dependencias e testes que bloquearem o gate.
3. Remover dados sensiveis de logs e padronizar erros HTTP.
4. Fortalecer autenticacao, rate limit, IP real e headers HTTP.
5. Automatizar backup externo, alerta e restore recorrente.
6. Expor os indicadores de continuidade no cockpit `/ops`.
7. Formalizar oferta do Plano Basico, suporte e onboarding.
8. Iniciar pilotos controlados e medir a operacao.

## Regra de decisao

Uma falha do gate significa apenas que a versao nao esta pronta. Nao se deve contornar
o gate, tornar verificacoes nao bloqueantes ou fazer deploy para descobrir o resultado
em producao.
