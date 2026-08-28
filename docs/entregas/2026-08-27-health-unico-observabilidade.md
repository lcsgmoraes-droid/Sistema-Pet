# Health unico e observabilidade operacional

Data: 2026-08-27

## Problema e usuarios

O backend registrava `GET /health` tres vezes e `GET /ready` duas vezes. Apenas
a primeira implementacao respondia, enquanto as demais permaneciam escondidas
pela ordem de registro. Isso dificultava manutencao e poderia alterar o
comportamento dos monitores depois de uma simples reorganizacao de imports.

Os usuarios desta entrega sao a operacao tecnica, o deploy automatizado e os
monitores que verificam se o sistema esta vivo e pronto para receber trafego.

## Requisitos e prioridade

- manter `GET /health` como verificacao rapida de processo;
- manter `GET /ready` com banco e migrations, retornando 503 quando indisponivel;
- manter `GET /health/watchdog` com banco e limite de latencia;
- garantir uma unica implementacao por metodo e caminho;
- nao expor estado interno do pool nem tipo de excecao no watchdog publico;
- nao alterar rotas de negocio, banco, migrations ou interfaces de usuario.

Prioridade: media. O sistema continuava operando, mas a ambiguidade reduzia a
confiabilidade da observabilidade e aumentava o risco de manutencao.

## Decisao tecnica

`backend/app/routes/health_routes.py` passa a ser a fonte oficial de `/health`
e `/ready`. `backend/app/health_router.py` permanece responsavel pelas rotas
operacionais sob `/health/*`, como `/health/watchdog`, `/health/detailed` e
`/health/metrics`. `main_basic_routes.py` fica apenas com rotas basicas que nao
duplicam os health checks.

O watchdog publico conserva somente estado, conexao, latencia e horario. Estado
do pool e excecoes continuam disponiveis nos logs e no painel Ops protegido.
Configuracao de latencia invalida volta ao limite seguro de 3 segundos, e uma
falha ao consultar o estado do pool nao impede o watchdog de responder.

## Criterios de aceite e testes

- existe exatamente uma rota GET para `/health` e uma para `/ready` na
  composicao oficial;
- `/health/watchdog` continua registrado;
- falha do watchdog retorna 503 sem mensagem sensivel, tipo de excecao ou pool;
- sucesso continua informando `healthy`, banco conectado e latencia;
- configuracao invalida e falha na leitura do pool nao derrubam o health check;
- o teste de saude dos modelos de leitura independe da ordem de importacao dos
  demais modelos da aplicacao;
- formatacao, analise estatica e testes focados passam.

## Publicacao, observabilidade e rollback

Nao ha migration nem mudanca de configuracao. O deploy do backend, se autorizado
em etapa separada, precisa reconstruir a imagem. Depois da publicacao devem ser
validados `/api/health`, `/health/watchdog` e o painel Ops.

Rollback: reverter o commit e reconstruir o backend. Como os codigos HTTP e os
campos essenciais do watchdog foram preservados, o risco operacional e baixo.
