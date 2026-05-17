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
- [ ] Confirmar com Lucas o nome exato da empresa/clinica.
- [ ] Criar tenant da clinica, se a Maiara for usar ambiente proprio.
- [ ] Criar usuario admin da Maiara.
- [ ] Ativar o modulo `veterinario` para o tenant dela.
- [ ] Rodar seed veterinario base sem dados falsos sensiveis.
- [ ] Criar ao menos um tutor e um pet de exemplo para demo.
- [ ] Criar consultorio/sala e agenda basica.
- [ ] Criar procedimento/medicamento de exemplo.
- [ ] Fazer smoke autenticado no tenant dela.
- [ ] Registrar evidencia da demo sem senhas, tokens ou dados sensiveis.

Regra operacional: criar usuario real da Maiara em producao deve ser uma acao
explicita, feita apenas depois de Lucas confirmar que quer criar o acesso.

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

- nome exato da clinica/empresa;
- se ela deve usar um tenant proprio agora ou apenas assistir a demo no tenant
  de teste;
- se o acesso deve ser criado antes ou depois da apresentacao.
