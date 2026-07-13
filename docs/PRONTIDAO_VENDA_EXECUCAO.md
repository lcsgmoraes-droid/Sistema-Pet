# Prontidao para venda - plano de execucao

Atualizado em: 2026-07-13

## Objetivo

Preparar o Sistema Pet para os primeiros clientes pagantes sem prometer maturidade
enterprise antes das evidencias tecnicas, operacionais e comerciais necessarias.

Este plano nao autoriza deploy de producao.

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
| G2 - Seguranca critica | Pendente | Sem vulnerabilidade bloqueadora, segredo em log ou erro interno exposto |
| G3 - Recuperacao e operacao | Pendente | Backup externo monitorado e restore recorrente comprovado |
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

- idade e resultado do ultimo backup;
- data e resultado do ultimo restore controlado;
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
