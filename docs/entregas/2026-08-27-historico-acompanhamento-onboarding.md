# Entrega - agenda e historico do acompanhamento de onboarding

Data: 2026-08-27

## Problema e prioridade

Com as primeiras empresas em uso, os dados atuais do onboarding eram
substituidos a cada edicao. Faltavam uma data objetiva para o proximo contato e
uma trilha simples que permitisse entender o que ja foi acompanhado, quando e
por quem.

Prioridade: alta para a operacao dos pilotos atuais. Esta entrega nao cria CRM,
automacao de mensagens nem teste de carga para centenas de empresas.

## Usuarios e requisitos

Usuario: administrador interno da plataforma que acompanha as empresas.

Requisitos funcionais:

- agendar ou limpar a data do proximo contato;
- colocar na fila contatos vencidos ou marcados para hoje;
- registrar notas cronologicas sem edicao ou exclusao pela interface;
- mostrar autor, data e a agenda vigente no momento de cada nota;
- impedir que o historico de uma empresa apareca em outra.

Requisitos nao funcionais:

- acesso exclusivo de administrador da plataforma;
- nota entre 3 e 1.000 caracteres, validada na API e no banco;
- consulta limitada a 100 registros por requisicao e a 20 na tela;
- migration linear, reversivel e sem alterar dados existentes;
- frontend organizado em componente e hook separados.

## Arquitetura, dados e seguranca

- `tenants.onboarding_next_contact_on` guarda somente o estado atual da agenda.
- `ops_tenant_onboarding_notes` guarda o historico imutavel de forma separada.
- Cada nota possui empresa, texto, agenda vigente, administrador autor e data.
- Chaves estrangeiras impedem nota sem empresa ou autor existente.
- Exclusao de uma empresa remove suas notas; exclusao de um autor com historico
  e bloqueada para preservar a auditoria.
- A tabela e global por desenho porque o cockpit administrativo precisa operar
  varias empresas, mas toda leitura e escrita exige `tenant_id` e autenticacao
  de administrador da plataforma.
- A interface orienta a nao registrar senhas, documentos ou dados pessoais
  sensiveis. O React exibe o texto escapado.
- O lockfile atualiza `react-router` e `react-router-dom` de 7.18.1 para 7.18.2,
  eliminando os dois alertas altos encontrados durante a homologacao.

## Criterios de aceite

- [x] Proximo contato pode ser salvo e limpo.
- [x] Contato vencido entra como acao necessaria na fila.
- [x] Nota registra autor, data e agenda vigente.
- [x] Historico retorna somente registros da empresa solicitada.
- [x] Nao existem endpoints de editar ou apagar notas.
- [x] Contratos backend, isolamento, validacoes e utilitarios frontend possuem
  testes automatizados.
- [x] Build de producao do frontend conclui.
- [x] Fluxo funcional validado pela API real com PostgreSQL na homologacao local.
- [ ] Revisao visual autenticada da nova area no navegador, sem bloquear o
  aceite tecnico e funcional.

## Operacao, mudanca e treinamento

Na aba `Pilotos` de `/ops/tenants`, selecionar a empresa, salvar a proxima data
de contato e registrar uma nota curta depois de cada conversa ou verificacao.
Nao copiar conversas inteiras nem dados privados; registrar somente a evidencia
operacional necessaria.

A mudanca e interna e nao altera a rotina dos clientes. Nao exige comunicado,
treinamento de cliente ou mudanca no aplicativo mobile.

## Publicacao, observabilidade e rollback

- A versao implantada continuara identificada pelo commit do deploy oficial.
- O deploy aplicara a migration antes de iniciar o backend atualizado.
- Falhas aparecem nos logs e no painel operacional ja existente.
- Rollback de codigo e migration remove a tabela de notas e a nova coluna. Antes
  de um downgrade depois de uso real, exportar as notas, pois o downgrade apaga
  esse historico.
- Esta entrega nao executa nem autoriza producao.

## Evidencias

O resultado da homologacao esta registrado em
`docs/homologacoes/2026-08-27-historico-acompanhamento-onboarding.md`.
