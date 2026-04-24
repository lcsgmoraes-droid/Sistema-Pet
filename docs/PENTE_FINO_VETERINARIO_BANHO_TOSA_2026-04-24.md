# Pente fino - Veterinario, app/ecommerce e Banho & Tosa

Data: 2026-04-24

Objetivo: organizar a proxima fase para liberar app/ecommerce em piloto, implantar uma clinica veterinaria real e preparar o modulo Banho & Tosa enterprise sem improviso.

## 1. App e ecommerce - release candidate

Status atual: validado e publicado em producao em 2026-04-24, no commit `d2ae92b1`.

O que esta pronto nesta leva:

- app mobile com URL por ambiente (`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_DEV_API_URL`, `EXPO_PUBLIC_PROD_API_URL`)
- comandos `npm run typecheck` e `npm run check` no app
- permissoes mobile reduzidas para camera, localizacao foreground, notificacoes, fotos e vibracao
- beneficios do app mais resilientes para cliente novo, resposta parcial do backend e cupons sem dados legados
- home do app levando o cliente para beneficios pelo card de pontos e atalho rapido
- checkout app/ecommerce alinhado ao contrato: carrinho nao e pedido, carrinho nao reserva estoque, sem dinheiro, somente PIX/debito/credito
- backend bloqueando finalizacao enquanto gateway nao estiver configurado
- webhook recusando boleto, transferencia, voucher ou metodo ausente
- entrega/PDV protegidos contra reabrir rota/venda entregue em retry do app
- smoke de release criado em `docs/SMOKE_RELEASE_APP_ECOMMERCE.md`

Validacoes executadas:

- `app-mobile`: `npm run check`
- `backend`: 22 testes-alvo de beneficios, checkout, carrinho, webhook e entrega/PDV
- `backend`: `py_compile` das rotas alteradas
- `frontend`: `npm run build`

Observacoes da publicacao:

- A finalizacao de checkout ficara bloqueada em producao enquanto a intermediadora de pagamento nao estiver configurada.
- Isso esta correto para o contrato definido: nao gerar pedido/venda antes de pagamento aprovado.
- Se houver cliente usando ecommerce para pedido manual sem gateway, esse comportamento precisa ser comunicado.

Documentos detalhados desta fase:

- `docs/PENTE_FINO_VETERINARIO_CLINICA_PILOTO_2026-04-24.md`
- `docs/BLUEPRINT_BANHO_TOSA_ENTERPRISE_2026-04-24.md`

## 2. Veterinario - leitura tecnica do estado atual

O modulo ja tem base funcional forte para piloto de clinica, mas precisa de uma rodada de estabilizacao operacional antes de uso diario sem acompanhamento.

Arquitetura encontrada:

- backend central em `backend/app/veterinario_routes.py` com 5833 linhas e dezenas de endpoints
- modelos em `backend/app/veterinario_models.py` cobrindo medicamentos, protocolos, consultorios, agenda, consultas, prescricoes, vacinas, exames, procedimentos, internacoes, peso, fotos, perfil comportamental e parceria veterinaria
- frontend em 13 telas veterinarias, com destaque para arquivos grandes:
  - `VetConsultaForm.jsx`: 2549 linhas
  - `VetInternacoes.jsx`: 1716 linhas
  - `VetAgenda.jsx`: 1402 linhas
  - `VetCatalogo.jsx`: 1146 linhas
  - `VetExamesAnexados.jsx`: 954 linhas
- `vetApi.js` centraliza as chamadas e cobre agenda, consultas, prescricoes, vacinas, exames, peso, procedimentos, internacoes, catalogos, perfil comportamental, parceiros, repasse, IA e calendario preventivo

Validacoes executadas:

- `python -m py_compile app/veterinario_routes.py app/veterinario_models.py app/pdf_veterinario.py`
- `npm run build`

Correcao aplicada nesta rodada:

- `VetInternacoes.jsx` agora isola agenda local e quantidade de baias por tenant/usuario.
- tambem foi evitado sobrescrever dados salvos no `localStorage` antes da leitura inicial terminar.

## 3. Veterinario - P0 para piloto da clinica

Antes de implantar na clinica da sua amiga, eu trataria estes pontos como obrigatorios:

- criar um checklist de smoke autenticado cobrindo tutor, pet, agenda, consulta, prontuario, PDF, vacina, exame, internacao, alta e repasse
- rodar seed veterinario de base no tenant da clinica sem `--with-test-launches`
- configurar `organization_type` como `veterinary_clinic` quando for clinica pura
- validar usuarios/perfis: admin da clinica, veterinario, recepcao e financeiro
- conferir se o veterinario visualiza apenas o que deve visualizar no modelo parceiro ou funcionario
- homologar upload/download de exames e PDFs em producao
- validar assinatura/hash do prontuario finalizado e download de receituario
- testar criacao de agendamento, remarcacao, cancelamento, inicio de atendimento e desfazer inicio
- confirmar que consulta finalizada fica somente leitura e nao permite alteracao clinica silenciosa
- testar fluxo financeiro de procedimento: custo, margem, conta a receber, repasse e baixa
- validar internacao: criar, evoluir, lancar procedimento/insumo, registrar alta e consultar historico
- homologar push/notificacao de agenda em dispositivo real antes de prometer para a clinica
- definir comportamento da IA quando OpenAI nao estiver configurada: esconder, desativar ou mostrar aviso claro
- criar pelo menos testes unitarios/contrato para agenda, consulta finalizada e repasse

## 4. Veterinario - P1 logo depois do piloto

Melhorias importantes, mas que podem vir depois do primeiro uso controlado:

- quebrar `veterinario_routes.py` por dominio: agenda, consultas, exames, catalogo, internacoes, financeiro/repasse, IA e relatorios
- quebrar `VetConsultaForm.jsx` em etapas menores com hooks de dominio
- quebrar `VetInternacoes.jsx` separando mapa de baias, agenda de procedimentos, historico e lancamento de insumos
- migrar agenda local de procedimentos de internacao para tabela no backend
- transformar quantidade/nome de baias em configuracao persistida por tenant
- trocar `window.confirm` por modais padronizados nas telas veterinarias
- paginar/buscar pets sob demanda em vez de carregar `limit=500` em telas pesadas
- criar testes E2E Playwright para os fluxos clinicos principais
- criar trilha de auditoria mais visivel para prontuario, prescricoes, exames e repasses

## 5. Smoke manual do Veterinario para a clinica piloto

Fluxo minimo para liberar a clinica:

1. Criar tenant/empresa da clinica.
2. Criar usuarios de admin, recepcao e veterinario.
3. Cadastrar tutor.
4. Cadastrar pet com especie, raca, peso, alergias e comportamento.
5. Criar agendamento veterinario.
6. Iniciar atendimento a partir da agenda.
7. Preencher anamnese, sinais vitais, exame clinico, diagnostico e conduta.
8. Adicionar prescricao.
9. Adicionar procedimento do catalogo.
10. Salvar e finalizar consulta.
11. Baixar prontuario PDF.
12. Baixar receituario PDF.
13. Validar assinatura/hash da consulta.
14. Registrar vacina e proxima dose.
15. Anexar exame e validar preview/download.
16. Criar internacao, registrar evolucao, procedimento/insumo e alta.
17. Conferir dashboard e relatorio clinico.
18. Conferir repasse/financeiro gerado.

## 6. Banho & Tosa enterprise - blueprint inicial

O modulo deve nascer integrado ao que ja existe: clientes, pets, funcionarios, produtos/estoque, financeiro, campanhas, entregas/taxi dog e alertas veterinarios.

Entidades principais:

- `banho_tosa_servicos`: banho simples, banho completo, tosa higienica, tosa maquina, tosa tesoura, hidratacao, desembolo, corte de unha, limpeza de ouvido etc.
- `banho_tosa_parametros_porte`: porte, faixa de peso, tempo padrao, agua media, energia media e insumos padrao.
- `banho_tosa_agendamentos`: agenda exclusiva com profissional, sala/box, pet, tutor, servico, status e observacoes.
- `banho_tosa_atendimentos`: check-in, inicio, pausas, termino, entrega, responsaveis e fotos/observacoes.
- `banho_tosa_etapas`: chegou, aguardando, em banho, secagem, tosa, revisao, pronto, entregue.
- `banho_tosa_insumos`: produtos previstos e utilizados, desperdicio, baixa de estoque e custo real.
- `banho_tosa_custos`: agua, energia, produto, mao de obra, comissao, taxa de cartao, taxi dog, desconto e margem.
- `banho_tosa_taxi_dog`: busca/entrega, janela de horario, rota, motorista, taxa e status.
- `banho_tosa_pacotes`: pacotes recorrentes, assinatura mensal, creditos e regras de vencimento.

Status operacional sugerido:

- agendado
- confirmado
- taxi_busca_agendada
- a_caminho
- chegou
- aguardando
- em_banho
- em_secagem
- em_tosa
- em_revisao
- pronto
- taxi_entrega_agendada
- entregue
- cancelado
- no_show

Formula de custo por atendimento:

- custo_insumos = soma dos produtos usados e desperdicio
- custo_agua = litros estimados ou medidos * custo litro
- custo_energia = minutos por equipamento * custo minuto
- custo_mao_obra = tempo do funcionario * custo hora com encargos
- custo_taxidog = custo da rota quando houver
- custo_total = insumos + agua + energia + mao de obra + taxidog + rateios
- margem = valor_cobrado - custo_total - impostos/taxas

MVP recomendado:

1. Cadastro de servicos, portes e parametros de custo.
2. Agenda exclusiva com check-in/check-out e status por etapa.
3. Atendimento com insumos previstos/usados e baixa de estoque.
4. Calculo de custo/margem por atendimento.
5. Taxi dog vinculado ao agendamento.
6. Dashboard de ocupacao, produtividade, custo medio e margem.
7. Pacotes/recorrencia e campanhas de retorno.

Dependencias antes de codar:

- decidir se banho/tosa sera modulo proprio no menu ou submodulo operacional de servicos
- confirmar se profissionais serao `funcionarios` atuais ou tipo especifico `tosador/banhista`
- definir se taxi dog reaproveita rotas de entrega ou nasce como agenda/logistica de servico
- definir centro de custo/DRE padrao para receitas e custos de banho/tosa
- definir quais parametros entram no setup inicial obrigatorio do tenant
