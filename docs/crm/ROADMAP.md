# Módulo CRM — ROADMAP (documento vivo)

Este é o guia de todo o desenvolvimento do CRM. Ele registra o que já foi feito, o que mudou e as decisões tomadas pelo caminho. **Toda conversa que mude escopo, ordem ou decisão termina com uma atualização aqui** (seções "Registro de decisões" e "Histórico de mudanças").

- Branch de trabalho: `notificacoes` (a partir da `main`).
- Documentos irmãos: [`FASE1_ESCOPO_E_ROADMAP.md`](FASE1_ESCOPO_E_ROADMAP.md) (escopo, diagnóstico e riscos) e, como histórico, `docs/notificacoes/FASE1_DIAGNOSTICO_E_ROADMAP.md`.
- Protótipo navegável anterior (notificações): artefato publicado, será revisado na Fase 2.

## Como usar este documento

**Situação de cada item:** `[ ]` pendente · `[~]` em andamento · `[x]` concluído · `[?] DECIDIR` falta decisão (descrever como lidar com o assunto quando chegar a hora) · `[-]` descartado (manter a linha e explicar por quê).

**Regras do jogo**
1. Itens `DECIDIR` ficam como estão até a etapa chegar. Quando a decisão sair, ela vai para o "Registro de decisões" e o item vira uma ou mais tarefas novas.
2. Cada etapa só fecha com: código, testes, documentação atualizada (skill do módulo e este roadmap), validação visual do Lucas e ensaio com cópia do banco de produção. **Nada vai para produção sem autorização explícita do Lucas.**
3. Em caso de dúvida ou regra em conflito, parar e discutir.
4. Tudo que tocar telas usa componentes v2 (e cria o componente novo no styleguide quando faltar).

## Premissas (não negociáveis)

Centralização de código · zero redundância · boas práticas (DDD, SOLID) para robustez e manutenção simples · documentação completa da evolução e das interações com o resto do sistema.

## Registro de decisões

| Data | Decisão | Origem |
|---|---|---|
| 19/10 | O escopo original era uma central de avisos internos; por isso, os avisos da plataforma para a loja (se existirem) saem de um número e e-mail do CorePet, configurados no OPS. | Lucas |
| 19/10 | Mensagem proativa pelo WhatsApp usa **modelos aprovados pela Meta, com variáveis** preenchidas pelo sistema. A loja não edita a frase do WhatsApp. | Lucas |
| 19/10 | As lojas não disparam mensagens livremente; só processos do sistema (e o atendimento) enviam. Haverá limite de envio (rate) para evitar spam. | Lucas |
| 19/10 | LGPD entra desde a primeira fase: aceite registrado com prova, confirmação pelo próprio WhatsApp, SAIR bloqueia na hora. | Lucas |
| 19/10 | Envio síncrono no processo que dispara; se falhar, o erro fica registrado e a fila reprocessa sem derrubar o fluxo de negócio. | Lucas |
| 19/10 | E-mail no MVP segue pelo Gmail; provedor profissional com SPF/DKIM/DMARC fica como pendência importante para o fim. | Lucas |
| 19/10 | Fila: evoluir a `notification_queue` do Postgres; sem Redis/RabbitMQ por enquanto. | Lucas |
| 21/10 | **Escopo mudou:** o foco passa a ser um **módulo de CRM com o cliente final (tutor)**: Kanban de leads, conversa por WhatsApp, atendimento por IA com passagem para humano, tudo cruzado com compras, pets e interações. | Lucas |
| 21/10 | **Cada loja usa o seu próprio número oficial** de WhatsApp para falar com tutores. | Lucas |
| 21/10 | Módulo novo **"CRM"**, que absorve o WhatsApp atual (dashboard e bot). | Lucas |
| 21/10 | Ordem: **Kanban primeiro**; WhatsApp como link manual no começo. | Lucas |
| 21/10 | Os 9 problemas que travam a conversa com o tutor viram **etapas do roadmap** (Etapa 0), atacadas uma a uma. | Lucas |
| 21/10 | **Como conectar o número de cada loja (parceiro de tecnologia da Meta ou intermediário): decidir quando chegar a Etapa 4.** | Lucas |
| 21/10 | **Consentimento:** fazer os ajustes necessários e decidir a melhor forma de solicitar o aceite (Etapa 0.7). | Lucas |
| 21/10 | **O CRM é por loja.** Usuário com permissão para mais de uma loja vê as lojas dele no CRM: cada card indica claramente a loja e há filtro fácil para ver tudo ou lojas específicas. | Lucas |
| 21/10 | **Custo da IA e das mensagens fica com o CorePet.** Venda por **pacotes de créditos** consumidos pelo cliente, na mesma lógica de tokens dos modelos de IA. Detalhes da cobrança ficam para mais adiante. | Lucas |
| 21/10 | Lembretes continua como central operacional interna; o CRM é a camada de relacionamento. | Lucas |
| 21/10 | **A conversa também se acessa pelo card do Kanban:** botão "Conversar" (com contador de não lidas e estado do atendimento) abre a conversa num painel lateral sobre o quadro, sem perder filtros; o painel tem abas Conversa e Ficha 360. | Lucas |

## Visão geral das fases e etapas

| Fase | Entrega | Situação |
|---|---|---|
| Fase 1 | Planejamento macro, documentação e roadmap | **Em andamento** (escopo e roadmap prontos; revisão com o Lucas) |
| Fase 2 | Protótipo navegável (artefato) com backend conceitual, sem acesso ao sistema | **Versão 1 pronta; aguardando ajustes (P.9)** |
| Fase 3 | Desenvolvimento em etapas 0 a 8 | Pendente |

| Etapa | Tema | Situação |
|---|---|---|
| 0 | Saneamento (9 sub-etapas: itens que travam a conversa com o tutor) | Pendente |
| 1 | Fundação do módulo CRM | Pendente |
| 2 | Kanban de leads | Pendente |
| 3 | Ficha 360 e sinais do tutor | Pendente |
| 4 | Canal WhatsApp por loja (+ e-mail, fila, créditos) | Pendente |
| 5 | Caixa de conversas | Pendente |
| 6 | IA no atendimento | Pendente |
| 7 | Automações de mensagem | Pendente |
| 8 | Relatórios, convivência com o legado e fechamento | Pendente |
| T | Temas transversais (créditos, datas, e-mail, segurança, desempenho) | Contínuo |

---

## FASE 1 — Planejamento

- [x] Diagnóstico de envio de WhatsApp e e-mail (`docs/notificacoes/`).
- [x] Levantamento de infraestrutura de fila e agendamento.
- [x] Levantamento do que existe de CRM, bot de IA, atendimento humano e dados do cliente.
- [x] Escopo e roadmap macro (`FASE1_ESCOPO_E_ROADMAP.md`).
- [x] Este roadmap detalhado.
- [ ] Revisão deste roadmap pelo Lucas.
- [ ] Criar `.claude/skills/crm/SKILL.md` (nasce vazia na Etapa 1 e cresce a cada etapa).

---

## FASE 2 — Protótipo (artefato, dados simulados)

Objetivo: fechar a ideia das telas e dos contratos antes de escrever código de produto. Sem acesso ao backend.

- [x] P.1 Revisar o protótipo anterior (incorporado ao novo protótipo, versão 1) de notificações (tela do OPS e histórico de envios) para o novo escopo.
- [x] P.2 **Kanban de leads:** colunas, cartões (tutor, pets, última compra, origem, responsável, próxima ação), arrastar entre colunas, criação manual, **identificação visual da loja em cada card**, **filtro de lojas** (ver tudo ou lojas específicas), filtros por responsável, origem e segmento.
- [x] P.3 **Ficha 360 do tutor:** linha do tempo unificada, pets, oportunidades sugeridas, consentimento e canais.
- [x] P.4 **Caixa de conversas:** lista, conversa, quem responde (IA, humano, aguardando), assumir e devolver, notas internas, janela de 24h e modelos de mensagem.
- [x] P.5 **Atendimento por IA:** regras de parada, resumo para o atendente, o que a IA consulta e faz, limites e créditos.
- [x] P.6 **Automações:** catálogo de gatilhos (aniversário, ração acabando, vacina, medicação, inativo, recompra), modelos, limites, liga/desliga por loja.
- [x] P.7 **Configuração do canal por loja** e tela do OPS (revisada); saldo e consumo de créditos.
- [x] P.8 Contratos conceituais: lead, etapa, interação, canal, modelo de mensagem, consentimento, crédito (dados e regras).
- [ ] P.9 Rodada de ajustes com o Lucas e congelamento do protótipo.

**Protótipo versão 1 (21/10):** `docs/crm/prototipo/crm-prototipo.html` (publicado também como artefato privado). Cobre Kanban com filtro de lojas e loja em cada card, ficha 360, caixa de conversas (IA, assumir, devolver, resumo, janela de 24h, notas), automações com bloqueios, configurações da loja, créditos e OPS. Contratos em `CONTRATOS_CONCEITUAIS.md`.

---

## FASE 3 — Desenvolvimento

### Etapa 0 — Saneamento (atacar um item por vez, na ordem que fizer sentido)

Origem: os 9 problemas que travam a conversa com o tutor. Cada sub-etapa tem testes que provam a correção.

**0.1 Bot não pode responder durante atendimento humano**
- [ ] Barrar o bot quando a conversa está com humano ou aguardando humano.
- [ ] Teste: mensagem nova do tutor em conversa com humano não gera resposta da IA.
- [ ] Definir o que acontece com mensagens recebidas enquanto aguarda atendente (aviso ao tutor? fila?). `[?] DECIDIR`

**0.2 Atendimento humano: estados e devolução ao bot**
- [ ] Unificar os estados do atendimento (hoje há dois vocabulários diferentes entre modelo, regra e tela).
- [ ] Assumir um atendimento passa a mudar também o estado da conversa.
- [ ] Encerrar devolve a conversa ao bot ou fecha, conforme escolha explícita do atendente.
- [ ] Corrigir a atribuição ao atendente (tipo de identificador incompatível).
- [ ] Ligar a transferência por sentimento, repetição e tempo de espera (hoje existe e não é chamada). `[?] DECIDIR` quais regras valem.
- [ ] Testes ponta a ponta: assumir, responder, resolver, devolver.

**0.3 Tempo real (WebSocket) separado por loja**
- [ ] Validar que o atendente da conexão pertence ao usuário e à loja.
- [ ] Gerenciar conexões e eventos por loja; nenhum evento cruza lojas.
- [ ] Exigir o módulo contratado na conexão.
- [ ] Emitir de fato os eventos de mensagem nova e de nova fila (hoje nunca são chamados).
- [ ] Escala com mais de uma instância (mensagens entre processos). `[?] DECIDIR` quando houver mais de uma réplica.
- [ ] Testes de isolamento entre lojas.

**0.4 Serviço único: telefone → tutor**
- [ ] Normalizar o telefone (DDI 55, 9º dígito, formatos com e sem máscara, identificadores especiais do WhatsApp).
- [ ] Um único serviço de resolução com correspondência rígida (substitui a correspondência frouxa da criação da sessão).
- [ ] Tratar ambiguidade (dois cadastros com o mesmo número): `[?] DECIDIR` como lidar (pedir confirmação? lead sem vínculo?).
- [ ] Ampliar o tamanho do campo de telefone da sessão.
- [ ] Reconciliar sessões já gravadas com o vínculo errado (script de conferência, sem alteração automática).
- [ ] Testes com casos reais de formato de telefone.

**0.5 Segredos e exposição de dados**
- [ ] Token interno do orquestrador: por loja ou por integração, comparação segura, nunca com valor padrão.
- [ ] Remover valores padrão de desenvolvimento do fluxo n8n (loja e token fixos).
- [ ] Remover ou corrigir o webhook antigo com token fixo.
- [ ] Não devolver erro interno ao usuário no teste de conexão.
- [ ] Tirar telefone e resultados de ferramentas dos logs (ou mascarar).
- [ ] Revisar quem pode ler e alterar a configuração do WhatsApp (permissão específica, não só estar logado).
- [ ] Testes de segurança dos contratos.

**0.6 Custo e abuso**
- [ ] Limite de uso da IA por loja ligado ao **saldo de créditos** (ver tema T.1).
- [ ] Limite de frequência por telefone e por tutor.
- [ ] Decidir o destino da chave de IA de reserva compartilhada entre lojas (a chave passa a ser do CorePet). `[?] DECIDIR`
- [ ] Ligar o controle de custo existente (hoje sem uso) ou substituí-lo.
- [ ] Medição por mensagem: modelo usado, tokens de entrada e saída, custo.

**0.7 LGPD operacional e consentimento**
- [ ] Consentimento verificado em todo envio (bot, automações e atendimento ativo).
- [ ] Palavra SAIR (e variações) bloqueia na hora e fica registrada.
- [ ] Exclusão, exportação e anonimização passam a executar de verdade (hoje são casca).
- [ ] Auditoria de acesso a dados do tutor no atendimento.
- [ ] **Decidir a melhor forma de solicitar o consentimento** (aceite no cadastro/PDV, mensagem de confirmação pelo WhatsApp, ou os dois). `[?] DECIDIR` — proposta inicial: aceite registrado no sistema + confirmação com botão no WhatsApp.
- [ ] Mudar a regra atual (presume consentimento) e avaliar impacto nas campanhas que já existem. `[?] DECIDIR` migração dos tutores atuais.
- [ ] Prazo de retenção das conversas. `[?] DECIDIR`

**0.8 Duplicidade e código morto**
- [ ] Decidir o modelo de conversa definitivo e remover o paralelo sem uso.
- [ ] Remover/ajustar código sem uso do bot e do envio em massa.
- [ ] Consertar o envio de mensagem do atendente (hoje não envia e o contrato com a tela está quebrado).
- [ ] Alinhar tela e API do chat (nomes de campos e respostas).
- [ ] Testes de contrato entre tela e API.

**0.9 Processamento confiável das mensagens**
- [ ] Fila com nova tentativa para as mensagens recebidas (hoje a falha é perdida).
- [ ] O processamento usa sessão de banco própria (hoje reutiliza a da requisição).
- [ ] Tirar chamadas bloqueantes de dentro de rotas assíncronas.
- [ ] O fluxo do n8n não deve segurar a requisição até a IA terminar.
- [ ] Suporte a mensagens que não são texto no canal oficial (áudio, imagem). `[?] DECIDIR` escopo.
- [ ] Testes de falha e reprocessamento.

### Etapa 1 — Fundação do módulo CRM

- [ ] 1.1 Registrar o módulo "crm" no back e no front (lista de módulos premium, informações do módulo, tela de módulo bloqueado, menu, rotas protegidas).
- [ ] 1.2 Entrada em planos e preço do módulo. `[?] DECIDIR` (avulso ou dentro de planos).
- [ ] 1.3 Permissões do CRM (visualizar, atender, gerenciar leads, configurar, ver todas as lojas) e **backfill** para quem hoje usa o WhatsApp, sem bloquear ninguém. Ajustar o teste de contrato do catálogo de permissões.
- [ ] 1.4 Modelo de dados: funil, etapa (configurável), lead, movimentação de etapa (histórico), interação, responsável. Todos por loja, com isolamento.
- [ ] 1.5 **Multi-loja:** o CRM é por loja; o usuário com acesso a mais de uma loja escolhe quais ver. Contrato de dados com a loja em cada registro e filtro por lojas permitidas.
- [ ] 1.6 Serviço de identificação do tutor (usa o serviço da Etapa 0.4); regra de número desconhecido vira lead sem cadastro.
- [ ] 1.7 Migração do menu: onde ficam o dashboard e o bot atuais no novo módulo. `[?] DECIDIR` convivência durante a transição.
- [ ] 1.8 Skill de documentação `.claude/skills/crm/SKILL.md` e entradas no catálogo do styleguide para componentes novos.
- [ ] 1.9 Testes de contrato do módulo e isolamento entre lojas.

### Etapa 2 — Kanban de leads

- [ ] 2.1 Funil padrão e etapas configuráveis pela loja (nome, ordem, cor, final ganho ou perdido). `[?] DECIDIR` etapas iniciais.
- [ ] 2.2 Tela do quadro (v2): colunas, cartões, contagem e valor por coluna, estados vazio, carregando e erro.
- [ ] 2.3 Arrastar e soltar entre colunas (com alternativa por teclado e por menu), gravando o histórico de movimentação.
- [ ] 2.4 Cartão do lead: tutor, pets, última compra, origem, responsável, próxima ação, **identificação clara da loja** (nome e marca visual).
- [ ] 2.5 **Filtro de lojas:** ver tudo ou lojas específicas, limitado às lojas que o usuário pode acessar; lembrar a última escolha.
- [ ] 2.6 Criação manual de lead (com busca de tutor existente).
- [ ] 2.7 Criação automática de leads a partir de sinais já existentes (cliente inativo, cashback a vencer, VIP em risco, recompra atrasada). `[?] DECIDIR` quais sinais e como evitar duplicar leads.
- [ ] 2.8 Detalhe do lead: interações, notas, tarefas e próxima ação com data.
- [ ] 2.9 Filtros e busca (responsável, origem, segmento, etapa, período).
- [ ] 2.10b Botão "Conversar" no card com contador de não lidas e painel lateral (conversa e ficha 360), reaproveitando o painel de conversa da Etapa 5 (um único componente).
- [ ] 2.10 Contato manual por WhatsApp (link com registro da interação) enquanto o canal oficial não existe.
- [ ] 2.11 Ganho e perda: motivos de perda. `[?] DECIDIR` lista de motivos.
- [ ] 2.12 Desempenho com muitos cartões (paginação por coluna) e uso no celular.
- [ ] 2.13 Testes e documentação.

### Etapa 3 — Ficha 360 e sinais do tutor

- [ ] 3.1 Linha do tempo unificada do tutor: compras, contas a receber, pets, vacinas, consultas, exames, banho e tosa, lembretes, contatos, mensagens, cashback, pedidos online, entregas e avaliações. Substitui a linha do tempo atual (que só cobre vendas, contas e pets).
- [ ] 3.2 Painel de pets do tutor (espécie, porte, peso atual e histórico, saúde, aniversário).
- [ ] 3.3 Sinais calculados por tutor: segmento, risco, frequência, ticket, produtos recorrentes. `[?] DECIDIR` se haverá pontuação consolidada (RFM) e quando recalcular (hoje não há rotina automática).
- [ ] 3.4 **Previsão de fim da ração** ligando peso do pet, consumo do produto e embalagem comprada (hoje só vem da recorrência ou da previsão informada no PDV).
- [ ] 3.5 **Vacina vencendo e retorno vencido:** rotinas que geram sinais (hoje só relatório).
- [ ] 3.6 **Fim de medicação:** calcular a partir da prescrição e da duração.
- [ ] 3.7 Oportunidades sugeridas por tutor e por pet (com a explicação de por que apareceu).
- [ ] 3.8 Contatos duplicados e números de familiares (para enviar ao número certo).
- [ ] 3.9 Dados do grupo comercial: cliente e pet são compartilhados entre lojas do grupo, vendas e histórico são por loja. Garantir que a ficha mostre a origem de cada dado e respeite o filtro de lojas.
- [ ] 3.10 Testes e documentação.

### Etapa 4 — Canal WhatsApp por loja

- [ ] 4.1 **Como cada loja conecta o seu número oficial** (parceiro de tecnologia da Meta, intermediário oficial, ou outro caminho): `[?] DECIDIR NESTA ETAPA` — levantar custos, prazo e esforço de cadastro; o código deve manter o provedor trocável.
- [ ] 4.2 Modelo de dados do canal por loja (número, provedor, estado de saúde, credenciais criptografadas).
- [ ] 4.3 Camada única de envio com interface de provedor (substitui os envios espalhados), com registro persistente de cada envio: estado, tentativas e motivo da falha.
- [ ] 4.4 Retorno de status do provedor (enviado, entregue, lido, falhou) e tratamento de mensagens recebidas de qualquer tipo.
- [ ] 4.5 Modelos de mensagem aprovados: catálogo padrão do CorePet por loja, variáveis, categorias e acompanhamento da aprovação.
- [ ] 4.6 Regra da janela de 24h: dentro dela texto livre, fora dela só modelo.
- [ ] 4.7 Consentimento no ponto de envio, SAIR, e fluxo de confirmação definido na Etapa 0.7.
- [ ] 4.8 Fila: evoluir a fila existente (canal WhatsApp, espera crescente entre tentativas, estado em processamento, trava para mais de uma instância) e processo dedicado como o do Bling.
- [ ] 4.9 **Consumo de créditos** por mensagem (ver T.1).
- [ ] 4.10 Telas de configuração do canal na loja e no OPS (estado de saúde, qualidade do número, modelos, limites).
- [ ] 4.11 E-mail como segundo canal pelo mesmo caminho único (Gmail no MVP): corrigir os pontos falhos do diagnóstico (simulações marcadas como enviadas, falta de registro, erro engolido).
- [ ] 4.12 Substituir os pontos de contato manuais (links) pelo canal oficial, onde fizer sentido.
- [ ] 4.13 Testes de envio, falha, janela e consentimento; ensaio ponta a ponta com número de teste.

### Etapa 5 — Caixa de conversas

- [ ] 5.1 Lista de conversas (todas, do bot, aguardando, minhas), com busca, filtro de lojas e indicação da loja.
- [ ] 5.2 Conversa: histórico, resposta do atendente pelo sistema, estado de entrega, notas internas.
- [ ] 5.3 Tempo real seguro por loja (usa a Etapa 0.3).
- [ ] 5.4 Atribuição, fila e prioridade, tempo de resposta esperado. `[?] DECIDIR` metas de atendimento.
- [ ] 5.5 Mídia (imagem, áudio, documento) e anexos.
- [ ] 5.6 Painel lateral com a Ficha 360 e o lead da conversa.
- [ ] 5.7 Número desconhecido: criar lead e, quando fizer sentido, ligar ao cadastro existente (fusão assistida).
- [ ] 5.8 Respostas rápidas e modelos para o atendente. `[?] DECIDIR` escopo.
- [ ] 5.9 Mover o dashboard de WhatsApp atual para este padrão visual (v2) e remover o legado.
- [ ] 5.10 Testes e documentação.

### Etapa 6 — IA no atendimento

- [ ] 6.1 Regras de parada, transferência e retorno ao bot (sobre a base da Etapa 0.1 e 0.2).
- [ ] 6.2 Resumo da conversa e do contexto para o atendente que assume.
- [ ] 6.3 Ferramentas da IA ligadas à Ficha 360 (pets, vacinas, histórico, ração) e à agenda de banho e tosa e veterinária (hoje a IA não consulta agenda).
- [ ] 6.4 O que a IA pode fazer sozinha (criar pedido, agendar, aplicar cupom): `[?] DECIDIR` por ação, com confirmação do tutor e trilha de auditoria.
- [ ] 6.5 Atualização automática do estágio do lead conforme a conversa.
- [ ] 6.6 Personalização por loja (tom, políticas, horários, regras de entrega e pagamento, hoje fixas em código).
- [ ] 6.7 Proteções: nunca revelar dados de outro tutor ou loja, não inventar preço ou prazo, limite de tamanho e de ferramentas por conversa.
- [ ] 6.8 Consumo de créditos e bloqueio ao esgotar (ver T.1); aviso ao tutor e à loja.
- [ ] 6.9 Avaliação de qualidade: amostra revisada por humano, métricas, problemas recorrentes. `[?] DECIDIR` método.
- [ ] 6.10 Modelo e provedor de IA: manter OpenAI ou preparar troca. `[?] DECIDIR`
- [ ] 6.11 Testes de comportamento (conversas simuladas) e documentação.

### Etapa 7 — Automações de mensagem

- [ ] 7.1 Catálogo de gatilhos e de mensagens (aniversário do tutor e do pet, ração acabando, recompra, vacina, retorno, medicação, inativo, cashback a vencer, pós-venda, pós-atendimento, avaliação).
- [ ] 7.2 Motor de regras por gatilho: condição, quando enviar, modelo, canal, limite.
- [ ] 7.3 **Limite de frequência por tutor** em todas as mensagens ativas (global, não por fluxo) e horário de silêncio.
- [ ] 7.4 Liga/desliga por loja e, quando fizer sentido, por segmento.
- [ ] 7.5 Mensagens viram cartão ou interação no Kanban e a resposta do tutor cai na caixa de conversas.
- [ ] 7.6 Migrar os envios atuais por notificação no app para o novo motor, sem duplicar mensagens. `[?] DECIDIR` convivência.
- [ ] 7.7 Fuso e horário de cada loja (depende do tema T.2).
- [ ] 7.8 Medição de conversão (mensagem → resposta → compra).
- [ ] 7.9 Testes e documentação.

### Etapa 8 — Relatórios, convivência com o legado e fechamento

- [ ] 8.1 Relatórios: funil e conversão, tempo de atendimento, volume por canal, resultado das automações, consumo de créditos.
- [ ] 8.2 Convivência com Lembretes (central operacional interna) e remoção do que ficou duplicado.
- [ ] 8.3 Revisão de permissões, segurança e desempenho do módulo inteiro.
- [ ] 8.4 Documentação final (skill, manual do usuário na Ajuda, guia de operação para o OPS).
- [ ] 8.5 Plano de implantação por lojas (piloto, depois liberação). `[?] DECIDIR`
- [ ] 8.6 Ensaio final com cópia do banco de produção e pedido de autorização de publicação.

---

## Temas transversais

**T.1 Créditos e cobrança** (decisão: custo é do CorePet, vendido por pacotes de créditos)
- [ ] Modelo de crédito: pacote, saldo, consumo, histórico, alerta de saldo baixo. Detalhes da cobrança ficam para mais adiante.
- [ ] Definir o que consome crédito e quanto (mensagem por categoria do WhatsApp, resposta da IA por tokens, outros). `[?] DECIDIR`
- [ ] Tela de saldo e extrato para a loja e para o OPS; compra de pacotes. `[?] DECIDIR`
- [ ] Comportamento ao acabar o saldo (parar IA? parar automações? aviso?). `[?] DECIDIR`

**T.2 Datas e fuso**
- [ ] Depende da atividade separada de padronização de datas (guardar em UTC, exibir no fuso de quem vê). O CRM nasce usando a convenção definida lá; até lá, evitar novas fontes de data inconsistente.

**T.3 E-mail**
- [ ] Provedor profissional com SPF, DKIM e DMARC no fim do projeto (Gmail no MVP).

**T.4 Segurança e LGPD contínuas**
- [ ] Revisão de segurança ao final de cada etapa; nenhum dado de tutor em log; acesso a dados auditado.

**T.5 Desempenho e escala**
- [ ] Observar volume de mensagens e de cartões; revisar quando houver mais de uma instância do sistema.

**T.6 Qualidade**
- [ ] Testes de contrato por etapa, isolamento entre lojas em todo endpoint novo, ensaio em cópia do banco de produção antes de qualquer publicação.

---

## Assuntos em aberto (resumo dos `DECIDIR`)

| Assunto | Quando decidir |
|---|---|
| Conexão do número de cada loja (provedor) | Etapa 4 |
| Forma de solicitar consentimento e tratamento dos tutores atuais | Etapa 0.7 |
| Ambiguidade de telefone (dois cadastros) | Etapa 0.4 |
| Mensagens recebidas enquanto aguarda atendente | Etapa 0.1 |
| Chave de IA de reserva e modelo/provedor de IA | Etapas 0.6 e 6 |
| Planos e preço do módulo CRM | Etapa 1 |
| Etapas iniciais do funil e motivos de perda | Etapa 2 |
| Sinais que geram leads automaticamente | Etapa 2 |
| Pontuação consolidada de cliente (RFM) | Etapa 3 |
| O que a IA faz sozinha | Etapa 6 |
| O que consome crédito e como cobrar | Tema T.1 |
| Convivência e migração dos envios atuais | Etapas 1, 5 e 7 |
| Implantação por lojas | Etapa 8 |

## Histórico de mudanças deste documento

| Data | Mudança |
|---|---|
| 21/10/2026 | Protótipo versão 2: conversa acessível pelo card do Kanban (painel lateral com abas Conversa e Ficha 360). |
| 21/10/2026 | Protótipo versão 1 e contratos conceituais criados; itens P.1 a P.8 concluídos. |
| 21/10/2026 | Criação do roadmap detalhado: fases 1 a 3, Etapas 0 a 8 e temas transversais, com as decisões de 19/10 e 21/10 registradas. |
