# Procedimento padrao para criar tenants

Este runbook define o fluxo operacional para cadastrar um novo cliente no CorePet.
O objetivo e reduzir o trabalho manual sem perder isolamento, auditoria ou seguranca.

## Escolha do fluxo

Todo cadastro deve comecar por uma destas duas opcoes:

1. **Tenant com estrutura vazia**: cria o tenant, o usuario administrador e os
   cadastros estruturais obrigatorios. Nao copia produtos.
2. **Tenant com catalogo base**: executa o fluxo anterior e, depois de uma
   simulacao sem erros, copia o catalogo base sanitizado.

Uma migracao de historico de outro sistema nao pertence a nenhuma dessas opcoes.
Ela segue o procedimento de importacao externa, com arquivos, hashes, backup e
conciliacao descritos em `docs/IMPORTACAO_SIMPLESVET_SEGURA.md`.

## Dados de entrada obrigatorios

- razao social e nome fantasia;
- CNPJ;
- nome de acesso da loja;
- nome do responsavel;
- e-mail do usuario administrador;
- plano e tipo de organizacao;
- valor acordado por loja;
- primeiro vencimento e dia recorrente;
- opcao de confirmacao de e-mail;
- fluxo escolhido: `estrutura_vazia` ou `catalogo_base`.

A senha temporaria deve ser gerada de forma forte e entregue apenas ao cliente.
Ela nao pode ser registrada em notas, logs, Git ou no manifesto de onboarding.

## Fontes cadastrais

Consultar o CNPJ em pelo menos duas fontes publicas atuais. Usar os dados apenas
quando as fontes coincidirem. Registrar nas notas do tenant as fontes e a data da
consulta.

Podem ser preenchidos automaticamente quando confirmados:

- razao social e nome fantasia;
- situacao cadastral;
- endereco, CEP, municipio e UF;
- telefone e e-mail publicos;
- CNAE principal e secundarios;
- porte, opcao pelo Simples e responsavel publico.

Nao presumir inscricao estadual, inscricao municipal, regime fiscal detalhado,
CFOP, CST ou aliquotas. Esses campos ficam vazios ate existir fonte oficial ou
confirmacao do contador.

## Etapa comum aos dois fluxos

1. Executar o readiness check do onboarding.
2. Criar o tenant e o usuario administrador pela rotina oficial de cadastro.
3. Confirmar que foram criados role, permissoes e vinculo `user_tenants`.
4. Executar `onboard_tenant_defaults(..., strict_required=True)` na mesma
   transacao do cadastro.
5. Preencher `tenants` e `empresa_config_geral` com os dados cadastrais validados.
6. Aplicar a condicao comercial sem criar cobranca automatica nao autorizada.
7. Quando houver autorizacao expressa, marcar o e-mail como verificado sem envio.
8. Registrar nota imutavel com fontes, campos pendentes e condicao comercial.
9. Validar login, plano, status de cobranca e proximo vencimento.

Se qualquer item obrigatorio falhar, o tenant nao deve ser liberado como concluido.

## Fluxo A - estrutura vazia

Este e o padrao para clientes que vao cadastrar os proprios produtos.

O tenant recebe:

- usuario administrador, role e permissoes;
- formas de pagamento;
- estrutura de DRE e financeiro;
- tipos de despesa;
- departamentos e categorias iniciais;
- opcoes auxiliares de cadastro;
- configuracao geral da empresa.

O tenant nao recebe produtos, imagens, estoque, custos, precos, fornecedores ou
historico operacional.

Resultado esperado: `produtos = 0` e onboarding obrigatorio completo.

## Fluxo B - estrutura com catalogo base

Este fluxo e usado quando o cliente quer comecar com o cadastro de produtos de
referencia do CorePet.

1. Concluir integralmente o Fluxo A.
2. Executar a simulacao da importacao no painel Ops ou pelo comando abaixo:

   ```powershell
   python -m app.scripts.run_base_catalog_import `
     --target-tenant-id TENANT_UUID `
     --target-user-id USER_ID
   ```

3. Conferir `ok = true`, `errors = []`, origem e destino.
4. Aplicar somente depois da simulacao aprovada:

   ```powershell
   python -m app.scripts.run_base_catalog_import `
     --target-tenant-id TENANT_UUID `
     --target-user-id USER_ID `
     --apply
   ```

5. Em producao, acrescentar `--allow-production-apply` e executar pelo wrapper de
   auditoria, somente com autorizacao explicita.
6. Conferir a auditoria do bundle `catalogo-base-loja-lucas`.
7. Confirmar que estoque, custo, margem, preco de venda, preco de aplicativo e
   preco de e-commerce ficaram zerados.

A carga copia somente cadastros reutilizaveis, como departamentos, categorias,
marcas, opcoes de racao, produtos e imagens. Nao copia fornecedores, Bling,
identificadores externos, lotes, movimentacoes nem historico de precos.

## Condicao comercial

O plano, valor, primeiro vencimento e recorrencia devem ficar registrados em nota
de onboarding. Os campos de status do tenant precisam refletir o momento real:

- `trial`: acesso liberado antes do primeiro pagamento;
- `active`: assinatura manual paga ou ativada;
- `past_due`: vencimento nao pago;
- `blocked` ou `canceled`: somente por decisao operacional explicita.

Preencher `billing_next_due_date` mesmo em acordos manuais. Nao criar cobranca no
Asaas ou em outro provedor apenas com base na nota comercial.

## Validacao final

- CNPJ, razao social, endereco e contato conferidos;
- usuario ativo e e-mail no estado combinado;
- login realizado com sucesso;
- plano e tipo de organizacao corretos;
- datas comerciais coerentes;
- nota de onboarding registrada;
- defaults obrigatorios presentes;
- no fluxo com catalogo, simulacao e aplicacao sem erros;
- no fluxo com catalogo, todos os valores operacionais continuam zerados;
- nenhuma informacao sensivel apareceu em logs ou no Git.

## Evolucao recomendada do painel Ops

O proximo passo e transformar este runbook em um assistente unico de **Novo
tenant** no painel Ops:

1. etapa de identidade e CNPJ, com sugestoes vindas de fontes publicas;
2. etapa de acesso, com senha temporaria gerada e opcao autorizada de dispensar
   confirmacao por e-mail;
3. etapa comercial, com plano, valor e vencimentos;
4. escolha entre `Estrutura vazia` e `Estrutura + catalogo base`;
5. revisao final e criacao atomica;
6. carga do catalogo em segundo plano, com progresso, resultado e possibilidade
   de reexecucao idempotente.

O assistente deve criar primeiro o tenant e retornar o acesso rapidamente. A
carga pesada do catalogo nao deve manter a tela de criacao bloqueada.
