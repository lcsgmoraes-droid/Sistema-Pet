# Cronograma - Maiara, Veterinario e Admin SaaS

Atualizado em: 2026-05-17

Este documento organiza tres frentes que nao devem se misturar:

1. preparar a demonstracao/piloto da veterinaria Maiara;
2. padronizar a experiencia visual das telas do modulo veterinario;
3. construir uma area global de administracao SaaS para usuarios, clientes,
   planos, modulos e pagamentos.

## Estado confirmado em 2026-05-17

Verificacao de usuario:

- O email da Maiara informado pelo Lucas no chat nao foi encontrado no cadastro
  global de producao.
- A checagem foi feita por API autenticada e segura, sem criar usuario.
- O usuario de teste admin do Lucas conseguiu autenticar com a segunda senha
  informada no chat.
- O tenant usado na checagem foi `PET TESTE LUCAS`.
- O modulo `veterinario` estava ativo nesse tenant.

Decisao de preparacao:

- A clinica sera criada como tenant novo.
- Nome operacional confirmado: `Clinica Veterinaria Sao Jose`.
- O nome pode ser cadastrado com acentos na aplicacao; este documento mantem
  ASCII para evitar problema de encoding no Windows/chat.

Execucao em producao:

- Tenant criado e validado em producao em 2026-05-17.
- Usuario admin da Maiara criado, ativo e com email verificado.
- Plano liberado como `premium` para piloto acompanhado.
- 16 modulos premium configurados como ativos.
- Modulo `veterinario` validado via API autenticada.
- Onboarding base aplicado.
- Seed veterinario base aplicado sem lancamentos falsos de atendimento.
- Senha inicial nao deve ser registrada em documento versionado.

Smoke autenticado do modulo veterinario em producao:

- `/veterinario`: carregou sem erro de console/rede critico.
- `/veterinario/agenda`: carregou sem erro de console/rede critico.
- `/veterinario/consultas`: carregou sem erro de console/rede critico.
- `/veterinario/consultas/nova`: carregou sem erro de console/rede critico.
- `/veterinario/exames`: carregou sem erro de console/rede critico.
- `/veterinario/ia`: carregou sem erro de console/rede critico.
- `/veterinario/calculadora-doses`: carregou sem erro de console/rede critico.
- `/veterinario/vacinas`: carregou sem erro de console/rede critico.
- `/veterinario/internacoes`: carregou sem erro de console/rede critico.
- `/veterinario/catalogo`: carregou sem erro de console/rede critico.
- `/veterinario/repasse`: carregou sem erro de console/rede critico.
- `/veterinario/configuracoes`: carregou sem erro de console/rede critico.

Conclusao: a demo guiada pode acontecer com seguranca operacional razoavel,
mas o modulo continua posicionado como piloto acompanhado para uma clinica real.

## Frente 1 - Preparar Maiara

Objetivo: deixar a Maiara pronta para uma demonstracao honesta e, se fizer
sentido, para um piloto acompanhado.

Checklist:

- [x] Confirmar se o email informado ja existia no sistema.
- [x] Confirmar que o modulo veterinario abre autenticado em producao.
- [x] Confirmar que as abas principais carregam sem erro critico.
- [x] Confirmar com Lucas o nome exato da empresa/clinica.
- [x] Confirmar se a Maiara vai usar ambiente proprio.
- [x] Criar tenant novo `Clinica Veterinaria Sao Jose`.
- [x] Criar usuario admin da Maiara.
- [x] Ativar o modulo `veterinario` para o tenant dela.
- [x] Rodar seed veterinario base sem dados falsos sensiveis.
- [ ] Criar ao menos um tutor e um pet de exemplo para demo.
- [ ] Criar consultorio/sala e agenda basica.
- [ ] Criar procedimento/medicamento de exemplo.
- [x] Fazer smoke autenticado no tenant dela.
- [ ] Registrar evidencia da demo sem senhas, tokens ou dados sensiveis.

Regra operacional: criar usuario real da Maiara em producao deve ser uma acao
explicita, feita apenas depois de Lucas confirmar que quer criar o acesso.

Observacao importante: o fluxo publico `/auth/register` tambem registra aceite
de Termos de Uso e Politica de Privacidade. Para cliente real, o ideal e a
propria Maiara aceitar os termos no cadastro. Se Lucas pedir criacao assistida,
registrar no chat que a criacao foi autorizada e usar estrategia sem compartilhar
senha: senha temporaria aleatoria descartada + confirmacao de email + redefinicao
de senha pela propria usuaria.

Evidencia de validacao:

- Login autenticado da Maiara: passou.
- Tenant selecionado: `Clinica Veterinaria Sao Jose`.
- Email verificado: sim.
- Permissoes carregadas: 55.
- Modulos ativos: 16.
- Plano: `premium`.
- Dashboard veterinario: respondeu com sucesso.
- Catalogo Vet inicial: 8 medicamentos, 4 procedimentos e 5 protocolos de
  vacina.
- Validacao auditada no servidor confirmou: 4 formas de pagamento, 2 especies,
  2 racas, 10 produtos/insumos Vet, 8 medicamentos, 4 procedimentos, 5
  protocolos de vacina e 16 assinaturas de modulo ativas.

## Anotacoes do teste real em 2026-05-17

Lucas testou o fluxo de agenda no tenant da Maiara e registrou pontos que devem
entrar no cronograma sem se perderem.

- [x] Corrigir erro 500 ao criar o segundo agendamento do dia. Causa: a checagem
      de conflito comparava datas com timezone e sem timezone. Corrigido nesta
      entrega normalizando os horarios antes da comparacao.
- [ ] Trocar o campo de foto do cadastro de pet de `url` para upload de arquivo,
      com preview, remocao e validacao de tamanho/formato.
- [ ] Atualizar o cadastro de pet para exibir corretamente servicos/situacoes de
      Banho e Tosa onde o fluxo de servicos do pet precisar aparecer.
- [x] Criar consultorio/sala dentro do modal de novo agendamento, sem levar o
      usuario para outra pagina, e selecionar automaticamente o consultorio
      criado. Implementado na branch de 2026-05-17; falta homologar em producao
      depois de merge/deploy.
- [ ] Melhorar a explicacao e o fluxo de calendario externo. Arquivo `.ics` e o
      formato iCalendar usado por Google Calendar, Outlook e Apple Calendar. Para
      alertas no celular, o usuario precisa importar/assinar esse calendario ou o
      sistema precisa evoluir para integracao/sincronizacao com calendario.
- [ ] Homologar agendamento em dispositivo real depois do deploy: criar primeiro
      agendamento, criar segundo em horario livre e confirmar que conflito real
      retorna mensagem amigavel em vez de erro 500.
- [x] Separar melhor visualmente um agendamento/consulta do outro na agenda,
      especialmente quando ha horarios proximos no mesmo dia.
- [x] Ao clicar em um agendamento da agenda, exibir acao primaria clara para
      `Iniciar consulta`/`Iniciar retorno`, mantendo os dados do agendamento.
- [x] Em `/veterinario/consultas`, mostrar os agendamentos clinicos do dia para
      o veterinario iniciar a consulta sem voltar para a agenda.
- [x] Ao iniciar consulta pela agenda ou pela lista de consultas, preencher pet,
      tutor, veterinario, tipo e motivo a partir do agendamento.
- [x] Trocar o campo `Retorno em dias` por fluxo de `Agendar retorno`, abrindo a
      agenda com contexto do pet/consulta para escolher dia e horario livre.
      Implementado na branch de 2026-05-17: o botao leva para a agenda com
      pet, tutor, consulta, tipo `retorno` e motivo preenchidos.
- [x] Persistir o vinculo do retorno com a consulta de origem
      (`consulta_origem_id`) para a consulta conseguir exibir o retorno
      agendado depois que o modal da agenda fechar.
- [x] Mostrar na consulta em andamento a data e horario do retorno agendado,
      com opcao de alterar o retorno.
- [x] Preservar o horario escolhido na agenda ao exibir retorno dentro da
      consulta, evitando deslocamento de fuso nos agendamentos veterinarios.
- [x] Corrigir falso conflito de horario livre na agenda quando um retorno
      gravado pelo banco vinha com timezone e era convertido para outro horario.
- [x] Ao concluir/cancelar o agendamento de retorno, voltar para a consulta na
      etapa `Diagnostico / Prescricao`, permitindo continuar o atendimento.
- [x] Permitir fechar os modais da agenda veterinaria com `Esc`.
- [x] Se ja existir retorno pendente para a consulta, novo agendamento de
      retorno atualiza o retorno pendente em vez de criar duplicado.
- [x] Diferenciar visualmente agendamentos do tipo `retorno` na agenda para
      nao parecerem consultas comuns.
- [ ] Ampliar catalogo veterinario de produtos/medicamentos com bulas, resumo de
      uso clinico e dados para prescricao.
- [x] Ajustar calculadora de dose para usar primeiro o peso informado na
      consulta; se estiver vazio, usar o peso cadastrado no pet.
- [x] Fazer o botao `Calcular dose pelo peso` da prescricao abrir o modal da
      calculadora de dose dentro da propria consulta, ja preenchido com
      medicamento, peso e dose de referencia quando houver catalogo.
- [x] Ao salvar rascunho da consulta, exibir modal de confirmacao visivel mesmo
      no fim da tela, com acoes para continuar editando, ir para o topo ou sair
      para a lista de consultas.
- [x] Trocar os campos de selecao do fluxo de consulta veterinaria por
      autocomplete digitavel: veterinario, sinais vitais, prognostico, exames,
      medicamentos, via, procedimentos e calculadora de dose.
- [x] Adicionar checkbox na lista de consultas/prontuarios e permitir excluir
      consultas selecionadas que ainda nao foram finalizadas/assinadas.
- [ ] Ampliar a base padrao de procedimentos veterinarios e seus insumos.
- [ ] Revisar padrao de horario do modulo veterinario e do sistema: usar
      Brasilia na exibicao e/ou UTC persistido de forma consistente, com foco em
      inicio/fim de consulta, duracao, custos e relatorios.
      Ajuste imediato feito: a lista de consultas passou a exibir
      `inicio_atendimento` quando existir, em vez de depender de `created_at`.
- [x] Corrigir persistencia do horario de inicio/fim da consulta veterinaria:
      novos marcos clinicos passam a ser gravados em UTC com timezone e exibidos
      em horario de Brasilia.
- [x] Salvar itens de prescricao e procedimentos realizados junto com o
      rascunho da consulta, sem gerar estoque/financeiro antes da finalizacao.
- [x] Ao agendar retorno a partir da consulta, fechar/concluir o modal da agenda
      volta para a consulta de origem para continuar o atendimento.
- [x] Melhorar a agenda de procedimentos da internacao com labels acima dos
      campos, nomes mais claros, busca em catalogos de medicamentos/procedimentos
      e preenchimento inicial de dose/referencia quando houver catalogo.
- [x] Refinar a agenda de procedimentos da internacao para usar campo unico
      digitavel/autocomplete, sem duplicar o medicamento selecionado, com botao
      `Novo` para ir ao catalogo.
- [x] Corrigir o fuso dos procedimentos agendados de internacao: horario digitado
      em `datetime-local` passa a ser interpretado como horario de Brasilia
      antes de persistir.
- [ ] Evoluir prescricao e internacao para agenda de horarios sugeridos por
      posologia, por exemplo a cada 8h/12h gerando os proximos horarios
      operacionais automaticamente.
- [x] Revisar fechamento da consulta: manter `Salvar rascunho` editavel,
      diferenciar finalizacao/assinatura e remover redundancias de `Dar alta`.
      Ajuste feito: removido o botao duplicado `Dar alta / finalizar`.
- [x] Criar botao `Internacao` ao fim da consulta para abrir o modulo de
      internacao ja vinculado, preservando a sequencia chegada -> consulta ->
      internacao -> alta. O link ja abre a nova internacao com pet, tutor,
      consulta e motivo inicial preenchidos.
- [x] Configurar a Clinica Veterinaria Sao Jose para aparecer no app mobile:
      slug `clinica-veterinaria-sao-jose`, cidade `Presidente Prudente`, UF `SP`
      e CEP provisorio `19010-000`.
- [x] Registrar guia operacional para habilitar app por tenant em
      `docs/GUIA_HABILITAR_APP_MOBILE_TENANT.md`.
- [x] Ajustar calculadora de dose do app veterinario para pesquisar medicamento
      por autocomplete sem abrir a lista inteira ao entrar na tela.
- [x] Tornar internacoes do app veterinario clicaveis, com detalhe rapido de
      resumo, agenda de cuidados, procedimentos realizados e evolucoes clinicas.
- [x] Ampliar a agenda do app veterinario para visualizacao de dia, semana e mes.
- [ ] Parametrizar visibilidade do veterinario no app e no web:
      proprietario/veterinario geral pode ver todos os pacientes da clinica;
      veterinario comum ve apenas pacientes, agenda, internacoes e procedimentos
      vinculados a ele.

## Frente 2 - Padronizacao visual do Veterinario

Objetivo: aplicar o modelo visual padrao do sistema nas telas veterinarias:
cores de botoes, componentes reutilizaveis, containers, tabelas, estados vazios,
filtros, paginacao e estilo de pagina.

Componentes padrao que devem ser priorizados:

- `PageHeader`
- `ActionButton`
- `IconActionButton`
- `Panel`
- `MetricGrid`
- `MetricCard`
- `DataTable`
- `FilterBar`
- `ModuleTabs`
- `SegmentedControl`
- `FormField`
- `StatusBadge`
- `LoadingState`
- `ErrorState`
- `EmptyState`
- `MoneyCell`
- `NumberCell`
- `PetIdentity`
- `PetAvatar`

Sequencia recomendada:

- [ ] Criar contrato visual do modulo veterinario: intents de botao, cores,
      estados, tabela, cards, filtros e formularios.
- [ ] Dashboard: trocar cards e KPIs para `PageHeader`, `MetricGrid`,
      `MetricCard` e `Panel`.
- [ ] Agenda: padronizar header, botoes, filtros, navegacao de periodo,
      cards de dia e estados de carregamento.
- [ ] Consultas: padronizar lista com `FilterBar`, `DataTable`,
      `PaginationControls` e `StatusBadge`.
- [ ] Nova consulta/prontuario: padronizar formulario por secoes com
      `FormField`, botoes padrao e estados de erro/sucesso.
- [ ] Exames: padronizar filtros, lista, modal de upload, estados vazios e
      painel de IA.
- [ ] Assistente IA Vet: padronizar layout de conversa, painel de contexto,
      alertas clinicos e botoes.
- [ ] Calculadora de doses: padronizar formulario, resultado, avisos e
      feedbacks.
- [ ] Vacinas: padronizar abas, carteirinha, vencimentos, modal de registro e
      alertas.
- [ ] Internacoes: padronizar cards, listas, modais de evolucao/procedimento,
      status e widgets.
- [ ] Catalogos: padronizar abas, tabelas, toolbars e modais de medicamento,
      procedimento e protocolo.
- [ ] Repasse: padronizar filtros, resumo financeiro, tabela e estados.
- [ ] Configuracoes Vet: padronizar listas, formularios, consultorios,
      parceiros e mensagens de feedback.
- [ ] Rodar build frontend.
- [ ] Rodar smoke visual autenticado das rotas veterinarias.

Regra de execucao: fazer em PRs pequenos por grupo de telas. O modulo esta bom
para demo; nao vale a pena fazer uma grande refatoracao visual antes de uma
apresentacao marcada para o dia seguinte.

## Frente 3 - Admin SaaS global

Objetivo: criar uma area interna do dono do Sistema Pet para acompanhar clientes,
usuarios, planos, modulos, pagamentos, status operacional e acoes administrativas
globais.

Hoje existe:

- tela de usuarios por tenant;
- permissoes por perfil;
- endpoints administrativos de modulos/planos;
- auditoria operacional em evolucao.

Ainda falta:

- tela global fora do tenant atual;
- visao consolidada de clientes/tenants;
- visao consolidada de usuarios de todos os tenants;
- controle manual de assinatura/pagamento;
- historico de alteracoes administrativas;
- acoes seguras para ativar, suspender, reativar e ajustar plano/modulo.

Escopo inicial recomendado:

- [ ] Backend read-only para listar tenants/clientes com filtros.
- [ ] Backend read-only para listar usuarios globais por tenant, email, status e
      perfil.
- [ ] Backend read-only para listar plano/modulos ativos de cada tenant.
- [ ] Frontend `Admin SaaS` somente para superadmin/admin do sistema.
- [ ] Aba `Clientes`: tenant, plano, status, modulos, data de criacao e contato.
- [ ] Aba `Usuarios`: email, nome, tenant, perfil, status e ultimo acesso quando
      existir.
- [ ] Aba `Pagamentos`: valor, vencimento, status, pago em, metodo e observacao.
- [ ] Auditoria obrigatoria para qualquer acao de escrita.
- [ ] Testes garantindo que admin comum de tenant nao acessa a area global.

Depois do read-only:

- [ ] Criar lancamento manual de pagamento/assinatura.
- [ ] Marcar pagamento como pago, atrasado, cancelado ou estornado.
- [ ] Ativar/suspender plano de tenant com motivo obrigatorio.
- [ ] Ativar/desativar modulo com motivo obrigatorio.
- [ ] Reenviar confirmacao de email quando aplicavel.
- [ ] Exportar CSV de clientes, usuarios e pagamentos.
- [ ] Registrar evidencia operacional de cada acao sensivel.

Fora do escopo inicial:

- gateway de pagamento automatico;
- cobranca recorrente automatica;
- impersonar usuario sem trilha de auditoria robusta;
- apagar cliente/tenant em producao;
- editar dados clinicos ou financeiros de um cliente sem contexto.

## Ordem de trabalho sugerida

1. Fechar preparacao da demo da Maiara sem criar usuario real ainda.
2. Depois da demo, decidir se ela entra como piloto acompanhado.
3. Se entrar, criar tenant/usuario/modulo e registrar evidencia.
4. Padronizar telas veterinarias em PRs pequenos.
5. Criar Admin SaaS read-only.
6. Adicionar pagamentos/assinaturas manuais.
7. Adicionar acoes sensiveis com auditoria e testes.
8. So depois avaliar automacao de cobranca/gateway.

## Proxima decisao

Antes de criar qualquer acesso real para a Maiara, Lucas precisa confirmar:

- se a Maiara ja autorizou/aceitou a criacao assistida da conta, ou se ela fara
  o cadastro pela tela publica;
- se o acesso deve ser criado antes ou depois da apresentacao;
- se o modulo `veterinario` deve ser ativado imediatamente no tenant novo.
