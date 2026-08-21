# Mapa oficial do codigo-fonte

Atualizado em: 2026-08-20

Este documento responde, sem ambiguidade, onde esta o codigo-fonte do CorePet.
Ele e a fonte oficial para manutencao, auditoria tecnica e entrada de novos
colaboradores.

## Resposta curta

O codigo-fonte esta versionado no Git. As tres raizes ativas sao:

| Produto | Codigo-fonte oficial | Entrada principal |
|---|---|---|
| API e regras do negocio | `backend/app/` | `backend/app/main.py` |
| Sistema web | `frontend/src/` | `frontend/src/main.jsx` |
| Aplicativo mobile | `app-mobile/src/` | `app-mobile/App.tsx` |

O banco evolui por migrations versionadas em `backend/alembic/versions/`. Os
testes ficam principalmente em `backend/tests/`, `frontend/src/`,
`frontend/scripts/`, `app-mobile/tests/` e `tests/`.

## Estrutura ativa

```text
Sistema-Pet/
|- backend/
|  |- app/                    API, regras, modelos e integracoes
|  |- alembic/versions/       historico de evolucao do PostgreSQL
|  |- scripts/                processos auxiliares do backend
|  `- tests/                  testes do backend e multiempresa
|- frontend/
|  |- src/                    aplicacao web React
|  |- scripts/                testes de contrato e validadores do frontend
|  `- public/                 arquivos publicos versionados
|- app-mobile/
|  |- src/                    aplicativo React Native/Expo
|  `- tests/                  testes do aplicativo
|- scripts/                   desenvolvimento, validacao, backup e deploy
|- tests/                     contratos gerais do repositorio
|- nginx/                     proxy e entrega do frontend
|- .github/workflows/         integracao continua
`- docs/                      documentacao oficial e historica
```

## Entradas de execucao

### Backend

`backend/app/main.py` cria a aplicacao FastAPI. Ele configura middlewares,
tratamento de erros, arquivos publicos, ciclo de vida e registro de rotas.

As rotas sao reunidas por `backend/app/main_routers.py`. O processo de producao
e iniciado por `backend/scripts/start_with_watchdog.py`, que executa Uvicorn com
a quantidade de workers definida no ambiente.

### Frontend web

`frontend/src/main.jsx` inicia o React. `frontend/src/App.jsx` monta a aplicacao
e as rotas ficam organizadas em `frontend/src/app/` e nos modulos de pagina.

O resultado de `npm run build` e um artefato gerado. Ele nao substitui o
codigo-fonte em `frontend/src/`.

### Aplicativo mobile

`app-mobile/App.tsx` inicia o aplicativo. Navegacao, telas, servicos, estado e
regras de apresentacao ficam em `app-mobile/src/`.

### Banco de dados

Os modelos vivem no backend. Toda alteracao de estrutura do banco deve ser
registrada por uma migration Alembic em `backend/alembic/versions/`. Migrations
antigas formam o historico do banco e nao devem ser apagadas ou reescritas
depois de aplicadas em ambientes compartilhados.

## O que nao e codigo-fonte

Os itens abaixo sao gerados ou locais e nao devem ser usados como origem para
manutencao:

- `frontend/dist/` e `runtime/`: builds gerados;
- `node_modules/`, `.venv/` e caches: dependencias locais;
- `uploads/`, logs e backups: dados operacionais;
- `.env` e certificados: configuracao secreta local;
- imagens Docker e containers em execucao: pacotes criados a partir da fonte.

Se alguem receber apenas o site publicado, um container ou a pasta `dist`, essa
pessoa recebeu o programa montado, nao o repositorio de codigo-fonte.

## Raizes antigas removidas

As pastas `app/` e `src/` da raiz foram criadas na primeira versao do projeto,
mas deixaram de participar do runtime. Elas foram removidas em 2026-08-20 depois
de busca de referencias, comparacao com as fontes ativas, testes de backend e
build do frontend.

O historico desses arquivos continua disponivel no Git. O validador estrutural
impede que codigo novo volte a ser criado nessas duas raizes.

## Como entregar o projeto para manutencao

Uma entrega tecnica completa precisa conter:

1. acesso ao repositorio Git e ao historico de commits;
2. este mapa e `docs/ARQUITETURA.md`;
3. `.env.example`, nunca o `.env` real em mensagens ou commits;
4. procedimento de DEV em `docs/DEV_ENVIRONMENT_CHECK.md`;
5. regras de contribuicao em `CONTRIBUTING.md`;
6. migrations e instrucoes de validacao;
7. acesso a producao separado, minimo e somente quando autorizado.

## Verificacao automatica

Execute:

```powershell
python scripts/validate_repository_structure.py
```

O validador confirma que as raizes oficiais existem, que os documentos de
entrada continuam ligados e que codigo novo nao apareceu nas raizes antigas.

