# Inventario para limpeza segura da raiz

Atualizado em: 2026-08-20

Objetivo: reduzir a confusao visual da raiz sem apagar atalhos utilizados ou
alterar o runtime das empresas ativas.

## Decisao desta etapa

Nenhum arquivo antigo foi removido ou movido nesta etapa. Primeiro o projeto
passa a declarar o que e fonte oficial e a impedir crescimento das raizes
antigas. Remocoes serao feitas em PRs separados, com busca de referencias,
testes e validacao em ambiente limpo.

## Itens oficiais na raiz

Devem continuar faceis de localizar:

- `README.md`: entrada geral;
- `CONTRIBUTING.md`: regras de contribuicao;
- `AGENTS.md`: regras obrigatorias dos assistentes;
- `FLUXO_UNICO.bat`: entrada operacional simples;
- `docker-compose.local-dev.yml`: ambiente local;
- `docker-compose.prod.yml`: definicao de producao;
- `.env.example`: contrato de configuracao sem segredos;
- `.github/`: CI e governanca;
- `backend/`, `frontend/` e `app-mobile/`: produtos ativos;
- `scripts/`: automacao oficial;
- `docs/`: documentacao.

## Codigo antigo na raiz

### `app/`

Arquivos encontrados:

- `app/__init__.py`;
- `app/core/settings_validation.py`;
- `app/db/guardrails.py`;
- `app/db/transaction.py`.

Estado: candidato legado. O pacote ativo do backend e `backend/app/`. A busca
por referencias atuais nao encontrou consumidores fora dos exemplos internos
desses proprios arquivos.

### `src/`

Arquivos encontrados:

- `src/services/api.js`;
- `src/pages/NotaFiscalItemRateio.jsx`;
- `src/pages/TransferenciaLote.jsx`.

Estado: candidato legado. O Vite ativo usa `frontend/src/`. A busca por
referencias atuais nao encontrou importacao desses arquivos pela aplicacao web.

Regra temporaria: nao adicionar arquivos a `app/` ou `src/` da raiz.

## Scripts e guias soltos

A raiz possui atalhos historicos com nomes como `INICIAR_*`, `CORRIGIR_*`,
`DIAGNOSTICAR_*`, `deploy*` e guias antigos. Alguns podem ainda ser usados como
atalho local; por isso nao devem ser removidos por aparencia.

O caminho oficial atual e:

- rotina e validacao: `FLUXO_UNICO.bat` e `scripts/fluxo_unico.ps1`;
- Git: `scripts/git_start_task.ps1` e `scripts/git_finish_task.ps1`;
- deploy real: `scripts/deploy_producao_remoto.ps1`;
- documentacao operacional: `docs/INDICE_OPERACIONAL.md`.

## Metodo para cada remocao

1. Escolher um grupo pequeno de candidatos.
2. Procurar referencias no codigo, CI, docs e atalhos locais versionados.
3. Verificar historico e motivo de criacao.
4. Criar teste de comportamento para qualquer funcao ainda relevante.
5. Remover ou consolidar sem mudar o comando oficial.
6. Rodar testes de estrutura, smoke, backend e build aplicaveis.
7. Registrar no PR o que saiu e como recuperar pelo Git.

## Ordem recomendada

1. Provar e remover `src/` da raiz.
2. Provar e remover ou migrar o conteudo de `app/` da raiz.
3. Auditar scripts `deploy*` antigos contra o deploy oficial.
4. Auditar atalhos `INICIAR_*`, `CORRIGIR_*` e `DIAGNOSTICAR_*`.
5. Consolidar Markdown solto em `docs/` e manter redirecionamento quando
   necessario.
6. Recontar arquivos de raiz e endurecer o validador.

## Criterio de sucesso

- uma pessoa nova identifica a fonte ativa sem ajuda;
- existe um unico caminho oficial para cada operacao;
- nenhum atalho usado pelo responsavel deixa de funcionar sem substituto;
- o CI impede retorno de codigo para raizes antigas;
- o historico permanece recuperavel no Git.

