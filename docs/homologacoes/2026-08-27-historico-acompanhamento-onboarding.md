# Homologacao - agenda e historico do acompanhamento de onboarding

Data: 2026-08-27

Ambiente: homologacao local isolada em Docker, com dados ficticios

## Objetivo

Comprovar a migration, o rollback, a autorizacao administrativa, o calculo da
fila, o registro de autoria e a leitura isolada do historico sem acessar
producao.

## Resultado estrutural

- Alembic atualizado para uma unica head: `zxg20260827a1`.
- Coluna `tenants.onboarding_next_contact_on` presente.
- Tabela `ops_tenant_onboarding_notes` presente com chaves estrangeiras,
  indices e limite de 3 a 1.000 caracteres.
- Downgrade ate `zxf20260827a1` e novo upgrade ate a head concluiram no
  PostgreSQL descartavel.
- Backend e frontend permaneceram saudaveis depois da reversao e reaplicacao.

## Resultado funcional

- Administrador temporario exclusivo da homologacao autenticou pela API real.
- Data vencida gerou o motivo `follow_up_overdue` na fila da empresa ficticia.
- Reagendamento para data futura foi salvo.
- Nota foi criada com texto, empresa, autor, data e copia da agenda vigente.
- Consulta do historico retornou a nota para a empresa correta.
- Logout foi executado e nota, agenda e administrador temporarios foram
  removidos ao final.
- Verificacao posterior encontrou zero notas e zero administradores temporarios.

## Interface

- O build de producao compilou os novos campos e o historico.
- ESLint, Prettier, contrato de tamanho dos componentes e utilitarios passaram.
- O navegador interno confirmou a disponibilidade local e a protecao que exige
  login administrativo.
- A digitacao de credencial pelo navegador nao fez parte desta execucao; a
  revisao visual autenticada do painel permanece como conferencia complementar.

## Testes executados

- Servico, isolamento, rotas, migration e registro dos modelos: 24 aprovados.
- Utilitarios frontend: 7 aprovados.
- Contrato de organizacao da area Ops: aprovado.
- Ruff e ESLint: aprovados.
- Build local e build pelos Dockerfiles de producao: aprovados.
- E2E do Plano Basico contra a homologacao: aprovado.
- `alembic heads`: uma unica head.

## Inconsistencias

Nenhuma falha funcional desta entrega ficou aberta. O primeiro build local
falhou porque a dependencia `qrcode`, adicionada anteriormente em outra frente,
ainda nao estava instalada neste worktree. `npm install --ignore-scripts`
sincronizou o `node_modules` com o lockfile ja versionado; o build seguinte
passou sem alterar versoes.

O `npm install` informou duas vulnerabilidades altas no `react-router` 7.18.1.
A correcao compativel foi aplicada somente no lockfile, atualizando
`react-router` e `react-router-dom` para 7.18.2. O `npm audit` posterior encontrou
zero vulnerabilidades e nenhuma atualizacao ampla foi executada.

## Decisao

Aceite tecnico e funcional aprovado para Pull Request. Producao nao foi
executada nem autorizada nesta homologacao.
