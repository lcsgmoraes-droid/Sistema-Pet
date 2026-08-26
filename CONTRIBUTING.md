# Contribuindo com o CorePet

Este guia vale para alteracoes feitas por pessoas, assistentes de IA ou uma
combinacao dos dois. A origem da digitacao nao muda o padrao de qualidade.

## Principios

- A `main` representa uma base estavel e protegida.
- Toda mudanca entra por branch de tarefa e Pull Request.
- Producao nunca e usada para descobrir se uma mudanca funciona.
- Refatoracao preserva comportamento; mudanca de regra e outra tarefa.
- Dinheiro, estoque, fiscal, autenticacao e tenant exigem protecao reforcada.
- Codigo simples, explicito e testavel e preferido a solucoes engenhosas.

Leia primeiro:

1. `AGENTS.md`;
2. `docs/MAPA_CODIGO_FONTE.md`;
3. `docs/ARQUITETURA.md`;
4. `docs/GOVERNANCA_ENTERPRISE.md`;
5. `docs/auditorias/estrutura-geral-definition-of-done.md`;
6. o guia do dominio que sera alterado.

## Fluxo Git

Antes de editar:

```powershell
git status --short --branch
```

Se estiver em `main`, abra a tarefa pelo script oficial:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"
```

Ao terminar, rode testes focados e feche a tarefa pelo fluxo oficial:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push
```

Nunca faça commit ou push direto em `main` ou `master`.

## Antes de implementar

Registre de forma curta:

- problema observado;
- comportamento que deve permanecer;
- arquivos e dominios afetados;
- riscos para tenant, dinheiro, estoque, fiscal e integracoes;
- testes que provarao o resultado;
- necessidade ou nao de migration.

Nova funcionalidade, mudanca de regra, integracao, migration, seguranca,
arquitetura ou operacao relevante deve usar
`docs/templates/FICHA_ENTREGA.md`. Quando houver aceite funcional, registrar a
evidencia com `docs/templates/REGISTRO_HOMOLOGACAO.md`.

Uma mudanca grande deve ser dividida antes da edicao.

## Padrao do backend

- `routes`: protocolo HTTP, auth, permissao e serializacao;
- `schemas`: contratos de entrada e saida;
- `services`: regra de negocio e orquestracao;
- `queries` ou `repositories`: acesso a dados compartilhado ou complexo;
- `events`: auditoria e eventos de dominio;
- testes: comportamento publico e regras puras.

Evite colocar regra extensa diretamente em routers. Nao crie uma segunda
implementacao de regra que ja exista em outro modulo.

## Padrao do frontend

- paginas montam fluxos;
- componentes apresentam dados;
- hooks coordenam estado e efeitos;
- services encapsulam chamadas HTTP;
- utils contem funcoes puras;
- regra sensivel e validada novamente no backend.

Novas telas devem reutilizar o cliente HTTP oficial e os formatadores globais.

## Banco e migrations

- Toda mudanca estrutural usa Alembic.
- Uma migration aplicada nao deve ser reescrita.
- Nao usar `Base.metadata.create_all` como substituto de migration em ambiente
  compartilhado.
- Mudanca de schema nao deve ficar escondida dentro de uma refatoracao.
- A migration precisa ser testada em banco limpo e historico pelo gate oficial.
- Nunca copiar banco ou dados de DEV para producao.

## Testes por risco

O objetivo e provar comportamento, nao apenas procurar texto nos arquivos.

Preferencia:

1. teste unitario de regra pura;
2. teste de integracao com banco para persistencia e concorrencia;
3. teste de contrato HTTP para rotas publicas;
4. teste de isolamento entre empresas;
5. E2E para jornadas criticas.

Testes textuais existentes podem permanecer como protecao temporaria, mas
devem ser substituidos gradualmente por testes de comportamento quando a area
for alterada.

## Regras para mudancas feitas com IA

- A IA deve ler as regras do repositorio antes de agir.
- Codigo gerado recebe os mesmos testes, lint, revisao de diff e PR.
- A IA nao inventa uma nova arquitetura local sem registrar a decisao.
- Mudancas de alto risco exigem uma segunda verificacao independente da
  implementacao: testes de comportamento, auditoria do diff e checklist.
- Nenhum segredo deve aparecer em prompt, log, commit ou resposta.
- A IA nao executa producao sem autorizacao explicita.
- A justificativa do PR deve explicar o comportamento, nao apenas dizer que o
  codigo foi gerado ou refatorado.

## Definition of Done

Uma tarefa esta pronta quando:

- a mudanca esta pequena e compreensivel;
- o comportamento esperado esta testado;
- tenant, permissoes e auditoria foram preservados;
- lint e formatacao aplicaveis passaram;
- build passou quando o frontend mudou;
- migrations foram validadas quando o banco mudou;
- documentacao oficial foi atualizada quando necessario;
- o diff nao contem segredo, dado local, build ou arquivo temporario;
- existe caminho claro de rollback;
- o PR descreve risco, validacao e impacto operacional.

## Producao

Contribuir com codigo nao autoriza deploy. O procedimento de producao esta em
`docs/PRODUCAO_DEPLOY_SSH.md` e sempre exige autorizacao explicita antes de
qualquer comando no servidor.
