# Guia de Demo - Modulo Veterinario para Clinica

Atualizado em: 2026-05-17

Este guia organiza a apresentacao do modulo veterinario para uma clinica ou
veterinaria interessada. A finalidade e mostrar bem o que existe, sem vender
como final algo que ainda deve ser tratado como piloto acompanhado.

## Veredito atual

Status recomendado: demonstravel e bom para piloto controlado.

Nao recomendado ainda: vender em escala como modulo veterinario fechado, sem
validacao de perfis reais e fluxo operacional de uma clinica piloto.

Nota pratica para demo: 8/10.

Motivo da nota:

- o modulo tem muita coisa implementada e buildando;
- existem testes focados passando;
- agenda, consulta, vacinas, exames, internacao, catalogo, IA e repasse existem;
- ja passou por smoke autenticado em producao com usuario admin de teste;
- ainda falta validar perfis reais de clinica antes de prometer uso diario sem
  acompanhamento.

## Evidencias de 2026-05-17

Rodadas locais:

- `backend` veterinario: 41 testes focados passaram.
- `frontend`: `npm --prefix frontend run build` passou.
- `backend` veterinario: `py_compile` dos arquivos `veterinario*.py` e
  `pdf_veterinario.py` passou.
- `main.py`: rotas `/vet` protegidas pelo modulo premium `veterinario`.

Checagem publica de producao:

- `https://mlprohub.com.br/api/health`: 200, `status=ok`.
- `https://mlprohub.com.br/api/health/watchdog`: 200, `status=healthy`,
  banco conectado.
- `https://mlprohub.com.br/veterinario`: 200, SPA acessivel publicamente antes
  da autenticacao/gate.

Smoke autenticado de producao:

- Usuario admin de teste autenticou no tenant `PET TESTE LUCAS`.
- O tenant tinha o modulo `veterinario` ativo.
- Todas as abas principais do modulo abriram sem erro critico de console/rede:
  dashboard, agenda, consultas, nova consulta, exames, IA, calculadora de doses,
  vacinas, internacoes, catalogo, repasse e configuracoes.
- O email da Maiara informado pelo Lucas no chat nao foi encontrado no cadastro
  global, e nenhum usuario foi criado durante a checagem.

## Como posicionar na conversa

Mensagem honesta:

> Temos uma vertical veterinaria em beta/piloto, com agenda, prontuario,
> vacinas, exames, internacao, catalogos, calculadora de doses, IA de apoio e
> repasse. Para uma primeira clinica, eu recomendaria entrar como piloto
> acompanhado, com implantacao assistida e validacao dos fluxos reais antes de
> transformar em plano comercial aberto.

Evitar dizer:

- "Modulo veterinario 100% pronto para qualquer clinica."
- "IA diagnostica ou prescreve sozinha."
- "Assinatura digital juridica completa ja substitui qualquer processo."
- "Push/app esta homologado em todos os celulares."
- "Financeiro/repasse ja cobre qualquer modelo de parceria sem ajuste."

## O que mostrar na demo

Roteiro sugerido de 20 minutos:

1. Abrir o painel veterinario.
2. Mostrar agenda veterinaria.
3. Mostrar lista de consultas.
4. Abrir/navegar pelo formulario de consulta.
5. Mostrar campos clinicos do pet: alergias, peso, restricoes e historico.
6. Mostrar prescricao e calculadora de dose.
7. Mostrar vacinas/carteirinha e proxima dose.
8. Mostrar exames anexados e interpretacao/apoio de IA como recurso beta.
9. Mostrar internacao em nivel visual, sem prometer fluxo completo se nao for
   testado ao vivo.
10. Mostrar catalogo de medicamentos/procedimentos.
11. Mostrar repasse como controle operacional, nao como financeiro final de
    clinica grande.
12. Fechar explicando o modelo de piloto acompanhado.

## Funcionalidades mais fortes para impressionar

- Agenda veterinaria com fluxo de atendimento.
- Prontuario com sinais vitais, anamnese, exame fisico, diagnostico e conduta.
- Prescricao/receita e PDF.
- Calculadora de doses por peso.
- Vacinas com proxima dose e calendario preventivo.
- Exames com upload, texto estruturado e apoio de IA.
- Internacao com evolucao e historico.
- Catalogo de procedimentos com insumos e custo/margem.
- Repasse veterinario.
- Alertas clinicos do pet integrados ao restante do sistema.

## Pontos que devem ficar como beta

- IA clinica: apresentar como apoio e triagem, nunca como diagnostico final.
- Push/notificacoes: so prometer depois de homologar em dispositivo real.
- Internacao: boa para demo, mas validar fluxo real antes de uso intenso.
- App do tutor na parte veterinaria: carteirinha e resumo existem, mas fluxo
  completo de clinica ainda nao deve ser promessa principal.
- Modelo veterinario parceiro multi-tenant: existe base, mas precisa validacao
  comercial e operacional caso a veterinaria seja independente da loja.

## Checklist antes da demo real

- [ ] Entrar com um usuario que tenha o modulo `veterinario` ativo.
- [ ] Confirmar que o menu Veterinario aparece.
- [ ] Abrir `/veterinario`.
- [ ] Abrir `/veterinario/agenda`.
- [ ] Abrir `/veterinario/consultas`.
- [ ] Abrir `/veterinario/consultas/nova`.
- [ ] Abrir `/veterinario/vacinas`.
- [ ] Abrir `/veterinario/exames`.
- [ ] Abrir `/veterinario/catalogo`.
- [ ] Abrir `/veterinario/calculadora-doses`.
- [ ] Abrir `/veterinario/internacoes`.
- [ ] Abrir `/veterinario/repasse`.
- [ ] Confirmar que nao ha erro visivel de tela branca.
- [ ] Confirmar que nao ha erro critico no console/rede.
- [ ] Ter pelo menos um tutor/pet de teste pronto.
- [ ] Ter pelo menos um produto/medicamento/procedimento de exemplo.

## Checklist minimo para vender piloto

- [ ] Criar tenant/empresa da clinica.
- [ ] Ativar modulo `veterinario` no tenant.
- [ ] Rodar seed veterinario base sem lancamentos de teste.
- [ ] Criar usuarios: admin, recepcao, veterinario e financeiro.
- [ ] Validar permissoes por perfil.
- [ ] Cadastrar tutor e pet.
- [ ] Criar agenda/consultorio.
- [ ] Criar agendamento.
- [ ] Iniciar atendimento.
- [ ] Preencher consulta.
- [ ] Registrar prescricao.
- [ ] Baixar prontuario PDF.
- [ ] Baixar receita PDF.
- [ ] Validar assinatura/hash da consulta.
- [ ] Registrar vacina.
- [ ] Anexar exame e testar download/preview.
- [ ] Criar internacao, evolucao e alta.
- [ ] Conferir repasse/financeiro gerado.
- [ ] Registrar evidencias sem senhas, tokens ou dados sensiveis.

## Perguntas boas para fazer para a veterinaria

- Ela atende so consulta, ou tambem internacao/cirurgia?
- Ela precisa de agenda por veterinario, por sala/consultorio ou ambos?
- Ela usa prontuario hoje em papel, planilha ou outro sistema?
- Ela emite receita/prontuario PDF?
- Ela precisa controlar vacinas e retornos?
- Ela anexa exames/laudos?
- Ela trabalha como clinica propria ou como parceira dentro de pet shop?
- Ela precisa de repasse/comissao?
- Ela quer app para tutor agora ou isso pode ser fase 2?
- Ela precisa de fiscal/NF ligado ao atendimento veterinario?

## Go/No-Go para a demo de amanha

Go:

- usar como demonstracao guiada;
- falar em piloto acompanhado;
- focar em agenda, prontuario, vacina, exames e controle clinico;
- explicar que o Plano Basico pet shop ja esta mais maduro, e que Veterinario e
  uma vertical adicional em validacao.

No-Go:

- fechar contrato de clinica grande sem validar fluxo real;
- prometer IA como diagnostico;
- prometer push/app completo sem homologacao;
- prometer assinatura juridica avancada;
- prometer financeiro completo da clinica sem revisar necessidade.

## Proxima acao recomendada

Antes da apresentacao, decidir se a demo sera feita no tenant de teste ou se
Lucas quer criar um tenant/acesso proprio para a Maiara. Se for criar acesso
real, registrar a acao e manter a implantacao como piloto acompanhado.

## Referencias

- `docs/PENTE_FINO_VETERINARIO_CLINICA_PILOTO_2026-04-24.md`
- `docs/PLANEJAMENTO_MODULO_VETERINARIO.md`
- `docs/PLANO_COMERCIAL_PRONTIDAO_MODULOS_2026-05.md`
- `docs/GUIA_VENDA_PLANO_BASICO.md`
- `docs/CRONOGRAMA_MAIARA_VETERINARIO_ADMIN_SAAS.md`
