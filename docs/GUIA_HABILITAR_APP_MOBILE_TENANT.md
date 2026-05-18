# Guia - Habilitar app mobile para um tenant

Atualizado em: 2026-05-17

Este guia define o passo a passo minimo para uma loja, clinica ou operacao
usar o app mobile. Vale para cliente, entregador, veterinario e futuros perfis
do app.

## Objetivo

Garantir que o app consiga encontrar a loja certa e, depois do login, direcionar
o usuario para o perfil correto dentro daquele tenant.

## Checklist do tenant

- [ ] Tenant criado e ativo.
- [ ] Nome da empresa preenchido.
- [ ] Cidade preenchida.
- [ ] UF preenchida.
- [ ] CEP preenchido, mesmo que provisorio.
- [ ] `ecommerce_slug` definido como codigo publico da loja.
- [ ] `ecommerce_ativo` ligado quando a loja deve aparecer no app.
- [ ] Modulo necessario ativo: `app_mobile`, `entregas`, `veterinario` ou outro
      modulo usado pelo perfil.
- [ ] Usuario criado e ativo no tenant.
- [ ] Pessoa/cadastro vinculado ao usuario quando o perfil exigir:
      veterinario, entregador, funcionario ou cliente.
- [ ] Email do cadastro igual ao email de login quando o vinculo for por email.
- [ ] Senha inicial temporaria trocada pelo usuario real assim que possivel.

## Como o usuario entra no app

1. Abre o app.
2. Digita ou escaneia o codigo publico da loja.
3. Confirma a loja encontrada.
4. Faz login com email e senha.
5. O app identifica o perfil operacional dentro do tenant selecionado.

Se o mesmo email existir em mais de um tenant, a loja selecionada no app define
qual tenant sera usado. Isso evita que um veterinario, entregador ou cliente
entre na loja errada.

## Regras por perfil

Cliente:

- Precisa ter usuario mobile ativo.
- Precisa ter cadastro de cliente vinculado ao tenant.

Entregador:

- Precisa ter usuario ativo.
- Precisa estar cadastrado como entregador/funcionario conforme a regra atual
  do modulo de entregas.
- O app direciona para as rotas de entrega quando o perfil operacional for
  entregador.

Veterinario:

- Precisa ter usuario ativo.
- Precisa ter pessoa/cadastro com tipo `veterinario`.
- O cadastro deve estar ativo no tenant.
- O email do cadastro deve bater com o email do usuario, ou o cadastro deve
  estar vinculado pelo `user_id`.
- O app direciona para a area veterinaria quando o perfil operacional for
  veterinario.

## Exemplo da Clinica Veterinaria Sao Jose

- Nome: `Clinica Veterinaria Sao Jose`
- Codigo publico do app: `clinica-veterinaria-sao-jose`
- Cidade: `Presidente Prudente`
- UF: `SP`
- CEP provisorio: `19010-000`
- Tipo de organizacao: `veterinary_clinic`

## Pendencias de produto

- [ ] Criar tela administrativa amigavel para configurar o codigo publico do app
      sem SQL.
- [ ] Exibir este checklist dentro da Ajuda/Introducao Guiada de forma mais
      visual.
- [ ] Criar validacao automatica de tenant pronto para app.
- [ ] Parametrizar visibilidade veterinaria:
      `ver todas as internacoes/agendas` ou `ver somente pacientes vinculados`.
