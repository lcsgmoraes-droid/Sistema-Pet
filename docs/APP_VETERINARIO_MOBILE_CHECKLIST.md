# App Veterinario Mobile - Checklist

Objetivo: criar uma experiencia de veterinario dentro do app mobile atual, reaproveitando login, tenant, notificacoes e estrutura ja usada pelo entregador.

## Status geral

- [x] Producao checada antes de iniciar: `/`, `/api/health` e `/health/watchdog` responderam HTTP 200 em menos de 500 ms.
- [x] Branch criada: `feat/20260517-2135-app-veterinario-mobile`.
- [x] MVP pronto para teste do Lucas no app.
- [x] PR aberto e validado.
- [x] Producao atualizada apos aprovacao.

## Sequencia de execucao

### 1. Identificacao do veterinario no app

- [x] Backend retorna `is_veterinario`, `veterinario_id` e `perfil_operacional` no login/perfil mobile.
- [x] App salva/cacheia o perfil operacional, como ja faz com entregador.
- [x] Regra de prioridade definida: veterinario primeiro, entregador depois, cliente por ultimo.
- [x] Testes backend cobrindo perfil veterinario.

### 2. Navegacao mobile veterinaria

- [x] Criar `VeterinarioNavigator`.
- [x] Direcionar usuario veterinario para o navigator correto.
- [x] Criar tela inicial com resumo do dia.
- [x] Manter botao de sair simples, como no app do entregador.
- [x] Typecheck do app passando.

### 3. API mobile do veterinario

- [x] Criar endpoints `/app/vet/...` usando o token mobile atual.
- [x] Resumo do dia: agendamentos, internados e procedimentos pendentes.
- [x] Agenda do veterinario.
- [x] Internacoes ativas.
- [x] Procedimentos/medicacoes pendentes.
- [x] Catalogo de medicamentos/procedimentos para consulta rapida.
- [x] Testes backend dos endpoints principais.

### 4. Telas MVP e refinamentos

- [x] Agenda do dia com horarios, pet, tutor e tipo.
- [x] Agenda mobile com visao de dia, semana e mes.
- [x] Internados com situacao e proximos cuidados.
- [x] Internados clicaveis com detalhe rapido de resumo, agenda de cuidados,
      procedimentos realizados e evolucoes clinicas.
- [x] Procedimentos/medicacoes com marcar como feito.
- [x] Calculadora de dose com peso do pet e medicamento pre-cadastrado.
- [x] Busca da calculadora por autocomplete: medicamentos aparecem apenas apos
      digitar, evitando lista inicial gigante.
- [x] Tela de detalhes rapida para o evento selecionado.
- [x] Agenda de procedimentos da internacao com autocomplete digitavel para
      medicamento/procedimento e labels mais claros de dose, quantidade,
      unidade e via.
- [x] Correcao do horario digitado em procedimentos de internacao para preservar
      o horario de Brasilia escolhido na tela.

### 5. Lembretes e alarmes

- [x] Reaproveitar push token ja registrado no app.
- [x] Sincronizar lembretes do veterinario para o celular.
- [x] Agendar notificacoes locais para horarios de consulta, medicacao e procedimento.
- [x] Ao tocar na notificacao, abrir a tela correta do app.
- [x] Preparar canal de notificacao com som/vibracao.

### 6. Validacao

- [x] Backend: testes unitarios relevantes passando.
- [x] App mobile: `npm run typecheck` passando.
- [ ] Teste manual com usuario veterinario da Maiara.
- [x] Checklist atualizado com o que ficou pronto e o que ficou para fase 2.

## Habilitacao de tenant no app

- [x] Guia operacional criado em `docs/GUIA_HABILITAR_APP_MOBILE_TENANT.md`.
- [x] Central de Ajuda recebeu artigo com o passo a passo para habilitar app
      mobile por loja/tenant.
- [x] Clinica Veterinaria Sao Jose configurada em producao com codigo publico
      `clinica-veterinaria-sao-jose`, cidade `Presidente Prudente`, UF `SP` e
      CEP provisorio `19010-000`.
- [ ] Criar tela administrativa para o dono do sistema validar e corrigir slug,
      cidade, UF, CEP, app ativo e vinculos de perfil sem acessar banco.

## Controle de visibilidade veterinaria

- [ ] Parametrizar se o veterinario ve todos os dados clinicos do tenant ou
      apenas pacientes vinculados a ele.
- [ ] Criar permissao/flag para proprietario clinico ou veterinario geral ver
      internacoes, agenda e procedimentos de todos.
- [ ] Manter padrao restritivo para veterinario comum: ver apenas pacientes,
      agenda e internacoes vinculados ao proprio veterinario.

## Fora do MVP inicial

- App separado para veterinarios.
- Chat em tempo real.
- Offline completo.
- Som personalizado por tipo de alerta.
- Escalonamento de alerta para outro funcionario.
