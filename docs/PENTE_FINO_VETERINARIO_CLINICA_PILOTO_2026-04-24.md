# Pente fino Veterinario - Clinica piloto

Data: 2026-04-24

Objetivo: deixar claro o que ja esta forte, o que precisa ser validado com usuario real e o que eu nao venderia ainda sem corrigir antes. Minha leitura atual: o modulo veterinario ja serve para um piloto acompanhado em uma clinica real, mas ainda precisa de uma rodada de estabilizacao antes de virar promessa comercial ampla.

## 1. Veredito

Status recomendado: piloto controlado, com acompanhamento proximo.

Nao recomendado ainda: venda comercial em escala sem roteiro de implantacao, testes autenticados e ajustes de permissao/auditoria.

Por que da para pilotar:

- O backend tem dominio clinico real em `/vet`: agenda, consultas, prescricoes, vacinas, exames, internacoes, catalogos, repasse, PDF, IA e calendario preventivo.
- O frontend ja tem rotas/telas dedicadas em `/veterinario/*`.
- O pet ja carrega dados clinicos estruturados e a area de detalhes do pet consome historico veterinario.
- Existem seeds veterinarios idempotentes para criar base de medicamentos, protocolos, materiais e procedimentos.
- O app mobile ja enxerga carteira do pet, alertas, exames, consultas e status de push.

Por que ainda nao da para vender sem ressalva:

- `backend/app/veterinario_routes.py` tem 5833 linhas e mistura agenda, prontuario, exames, catalogo, financeiro, internacao, IA e relatorios.
- `VetConsultaForm.jsx`, `VetInternacoes.jsx`, `VetAgenda.jsx`, `VetCatalogo.jsx` e `VetExamesAnexados.jsx` sao grandes demais para manutencao segura no medio prazo.
- A maior parte do modulo ainda nao tem testes de contrato dedicados.
- Internacao ainda tem parte operacional local no navegador, mesmo com escopo por tenant/usuario corrigido.
- Fluxos de permissao por perfil clinico precisam ser homologados com usuarios reais.
- A IA tem fallback e memoria, mas precisa guardrails e mensagens de responsabilidade antes de uso clinico diario.

## 2. Inventario tecnico encontrado

Backend:

- `backend/app/veterinario_routes.py`: 5833 linhas.
- `backend/app/veterinario_models.py`: 412 linhas.
- `backend/app/pdf_veterinario.py`: geracao de prontuario e receituario.
- `backend/app/scripts/seed_veterinario_base.py`: seed idempotente por tenant com materiais, medicamentos, protocolos, procedimentos e opcional de lancamentos de teste.

Modelos principais:

- `MedicamentoCatalogo`: medicamentos, principio ativo, dose mg/kg, interacoes, antibiotico/controlado.
- `ProtocoloVacina`: protocolos por especie, serie, intervalo e reforco.
- `ConsultorioVet`: salas/consultorios para agenda.
- `AgendamentoVet`: agenda clinica, consultorio, veterinario, status, inicio/fim.
- `ConsultaVet`: prontuario clinico, sinais vitais, diagnostico, conduta, retorno, hash e assinatura.
- `PrescricaoVet` e `ItemPrescricao`: receituario e itens.
- `VacinaRegistro`: aplicacoes, lote, proxima dose e protocolo.
- `ExameVet`: exames, arquivo, resultado estruturado/textual e interpretacao IA.
- `CatalogoProcedimento` e `ProcedimentoConsulta`: servicos/procedimentos, insumos, baixa de estoque e financeiro.
- `InternacaoVet` e `EvolucaoInternacao`: internacao, evolucao e procedimentos.
- `PesoRegistro` e `FotoClinica`: curva de peso e fotos clinicas.
- `PerfilComportamental`: temperamento e restricoes uteis para banho/tosa.
- `VetPartnerLink`: relacao tenant loja x tenant veterinario parceiro.

Frontend:

- `VetDashboard.jsx`: 442 linhas.
- `VetAgenda.jsx`: 1402 linhas.
- `VetConsultas.jsx`: 215 linhas.
- `VetConsultaForm.jsx`: 2549 linhas.
- `VetExamesAnexados.jsx`: 954 linhas.
- `VetAssistenteIA.jsx`: 580 linhas.
- `VetCalculadoraDoses.jsx`: 289 linhas.
- `VetVacinas.jsx`: 647 linhas.
- `VetInternacoes.jsx`: 1741 linhas.
- `VetCatalogo.jsx`: 1146 linhas.
- `VetRepasse.jsx`: 273 linhas.
- `VetConfiguracoes.jsx`: 488 linhas.
- `vetApi.js`: 174 linhas.

Rotas de tela:

- `/veterinario`
- `/veterinario/agenda`
- `/veterinario/consultas`
- `/veterinario/consultas/nova`
- `/veterinario/consultas/:consultaId`
- `/veterinario/exames`
- `/veterinario/ia`
- `/veterinario/calculadora-doses`
- `/veterinario/vacinas`
- `/veterinario/internacoes`
- `/veterinario/catalogo`
- `/veterinario/configuracoes`
- `/veterinario/repasse`

## 3. Pontos fortes para a clinica

Agenda:

- Agenda por dia/semana.
- Veterinario e consultorio vinculados.
- Deteccao de conflito por profissional/sala.
- Acao de iniciar atendimento a partir do agendamento.
- Link/arquivo `.ics` para calendario externo.
- Push 24h e 1h antes, com diagnostico de push.

Consulta/prontuario:

- Anamnese, sinais vitais, exame fisico, diagnostico e conduta.
- Bloqueio de edicao direta em consulta com status `finalizada`.
- Hash do prontuario ao finalizar.
- PDF de prontuario.
- Timeline clinica por consulta.

Prescricao:

- Receituario com itens, posologia, via, duracao e hash.
- PDF de receita.
- Catalogo de medicamentos com dose mg/kg.

Vacinas:

- Protocolos configuraveis.
- Registro por pet.
- Proxima dose.
- Vacinas vencendo.
- Carteirinha no app.

Exames:

- Cadastro de exame.
- Upload de arquivo.
- Resultado textual/estruturado.
- Interpretacao IA e chat por exame.

Internacao:

- Criacao, alta, evolucao e procedimento.
- Grafico de evolucao.
- Mapa/lista/agenda operacional.
- Historico por pet.

Financeiro:

- Procedimentos podem gerar contas a receber.
- Insumos de procedimento podem baixar estoque.
- Relatorio de repasse veterinario.
- Baixa de repasse.

App:

- Carteirinha digital do pet.
- Alertas e status vacinal.
- Consultas e exames recentes.
- Diagnostico de push.

## 4. Riscos P0 antes da amiga usar no dia a dia

1. Permissoes por perfil ainda precisam ser homologadas.

Risco: recepcao, veterinario, admin e financeiro podem enxergar ou alterar mais do que deveriam.

Acao: criar usuarios reais de teste e validar cada tela com cada perfil. Bloquear prontuario completo para quem so deve ver agenda/financeiro.

2. Imutabilidade clinica precisa de teste de contrato.

Risco: a rota `PATCH /vet/consultas/{id}` bloqueia consulta finalizada, mas rotas satelites como prescricoes, procedimentos, exames e vacinas precisam de regra clara sobre o que pode ou nao pode ser incluido depois da finalizacao.

Acao: definir regra comercial/clinica e criar testes:

- consulta finalizada nao edita campos clinicos.
- prescricao pos-finalizacao exige justificativa ou fica bloqueada.
- procedimento pos-finalizacao exige reabertura controlada ou fica bloqueado.
- anexo de exame pos-finalizacao deve gerar evento auditavel.

3. Internacao ainda tem estado operacional local.

Risco: agenda de procedimentos de internacao e total de baias ficaram isolados por tenant/usuario, mas ainda dependem de `localStorage`.

Acao: migrar agenda de procedimentos de internacao, baias e configuracoes para backend antes de uso intenso com mais de um computador.

4. Seed veterinario precisa de politica de producao.

Risco: seed com `--with-test-launches` pode contaminar tenant real se usado errado.

Acao: criar comando/documentacao de seed de producao somente base e deixar lancamentos de teste restritos a DEV/staging.

5. Upload de exames precisa smoke real.

Risco: path de arquivo, permissao, preview e download podem se comportar diferente em producao.

Acao: testar PDF, imagem, arquivo grande, download no navegador e link no app.

6. Push precisa homologacao fora do Expo Go.

Risco: o proprio app informa que push remoto nao funciona no Expo Go nas versoes atuais.

Acao: validar com build dev client/APK e token real.

7. IA clinica precisa de postura de seguranca.

Risco: resposta da IA pode ser tratada como prescricao.

Acao: exibir aviso claro de apoio, nao substituicao do veterinario; logar contexto/resposta; permitir feedback; evitar dose sem peso/especie.

8. Arquivos grandes aumentam risco de regressao.

Risco: pequenas mudancas no formulario de consulta/internacao podem quebrar fluxos distantes.

Acao: refatorar apos o primeiro smoke, antes de escalar.

## 5. Checklist de implantacao da clinica piloto

Preparacao do tenant:

- Criar empresa/tenant da clinica.
- Definir `organization_type = veterinary_clinic` quando for clinica pura.
- Confirmar todos os modulos liberados temporariamente.
- Rodar `python -m app.scripts.seed_veterinario_base --tenant-id <TENANT_UUID>` sem `--with-test-launches`.
- Cadastrar categorias/DRE padrao para receita veterinaria.
- Configurar dados da empresa, logo, endereco, telefone e termos de uso.

Usuarios:

- Admin da clinica.
- Recepcao.
- Veterinario.
- Financeiro.
- Opcional: auxiliar/internacao.

Pessoas e pets:

- Cadastrar tutor.
- Cadastrar pet com especie, raca, peso, porte, alergias, doencas cronicas, medicamentos continuos e restricoes.
- Cadastrar veterinario em Pessoas com `tipo_cadastro = veterinario` e CRMV.
- Validar se o veterinario aparece na agenda.

Agenda:

- Criar consultorios/salas.
- Criar agendamento.
- Remarcar agendamento.
- Cancelar agendamento.
- Validar conflito de horario por veterinario e sala.
- Iniciar atendimento pela agenda.
- Desfazer inicio quando consulta nao tiver conteudo clinico.

Consulta:

- Preencher queixa, anamnese, sinais vitais e exame fisico.
- Registrar peso e confirmar atualizacao do pet.
- Adicionar prescricao.
- Adicionar procedimento do catalogo.
- Anexar exame.
- Finalizar consulta.
- Tentar editar consulta finalizada e confirmar bloqueio.
- Baixar prontuario PDF.
- Baixar receituario PDF.
- Validar assinatura/hash.

Vacinas:

- Registrar vacina.
- Definir proxima dose.
- Verificar lista de vacinas vencendo.
- Conferir carteirinha no app.

Internacao:

- Criar internacao.
- Registrar evolucao.
- Registrar procedimento/medicacao.
- Consultar historico.
- Dar alta.
- Conferir se historico aparece no pet.

Financeiro:

- Validar conta a receber criada por procedimento.
- Validar custo, margem e estoque baixado.
- Validar relatorio de repasse.
- Dar baixa no repasse quando aplicavel.

App:

- Login do tutor.
- Carteirinha do pet.
- Exames/consultas recentes.
- Push status.
- Push real em build fora do Expo Go.

## 6. Ordem de correcao recomendada

Semana 1 - liberar clinica piloto com seguranca:

- Criar testes de contrato para consulta finalizada, agenda e repasse.
- Criar smoke manual autenticado especifico da clinica piloto.
- Homologar upload/download em producao.
- Validar perfis com usuarios reais.
- Rodar seed base no tenant da clinica.
- Fazer primeiro atendimento acompanhado.

Semana 2 - estabilizacao:

- Migrar agenda local de internacao/baias para backend.
- Padronizar modais no lugar de `window.confirm`.
- Reduzir carregamento de pets em massa (`limit=500`) para busca paginada/autocomplete.
- Melhorar mensagens de erro para recepcao/veterinario.
- Criar auditoria visivel para eventos clinicos relevantes.

Semana 3 - refatoracao tecnica:

- Quebrar `veterinario_routes.py` por dominio:
  - `vet_agenda_routes.py`
  - `vet_consultas_routes.py`
  - `vet_exames_routes.py`
  - `vet_catalogo_routes.py`
  - `vet_internacoes_routes.py`
  - `vet_financeiro_routes.py`
  - `vet_ia_routes.py`
  - `vet_relatorios_routes.py`
- Quebrar `VetConsultaForm.jsx` em etapas e hooks.
- Quebrar `VetInternacoes.jsx` em mapa, lista, agenda, historico e procedimentos.
- Criar suite E2E Playwright dos fluxos clinicos.

## 7. Definition of Done para vender o veterinario

- Smoke autenticado completo aprovado em producao.
- Perfis e permissoes validados.
- Consulta finalizada imutavel ou alteracao com justificativa/auditoria.
- PDF e assinatura/hash funcionando.
- Upload/download de exames funcionando.
- Seed base documentado e seguro para producao.
- Push homologado em dispositivo real ou funcionalidade marcada como beta.
- Testes de contrato cobrindo agenda, consulta finalizada, prescricao/procedimento, internacao e repasse.
- Primeiro ciclo real da clinica concluido: agendamento, atendimento, financeiro e retorno.

