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

## Diretrizes visuais (valem para todo o módulo)

- **Cores de atenção:** tudo que exige atenção ou ação do usuário usa **amarelo, laranja ou vermelho** (pendências, bloqueios, mensagens não lidas, prazo de hoje, saldo baixo, falta confirmar). O que é só informativo usa **azul, verde, rosa, roxo** e afins. As cores de identidade das lojas nunca usam amarelo, laranja ou vermelho.
- Componentes v2 do styleguide em todas as telas; botão de ação em azul, destrutivo em vermelho.

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
| 26/10 | **Decidido: o canal de WhatsApp usa a API oficial da Meta (Cloud API).** Cada loja com o seu número e a sua conta do WhatsApp Business. Começamos pelo caminho **assistido** (a loja cria conta e app na Meta e cola os dados no sistema, guiada por uma página de apoio); a conexão com poucos cliques (cadastro incorporado) e o uso do número junto com o app WhatsApp Business (coexistência) dependem de o CorePet virar **provedor de tecnologia da Meta**. 360dialog e WAHA ficam como provedores antigos/piloto. | Lucas |
| 21/10 | **Consentimento:** fazer os ajustes necessários e decidir a melhor forma de solicitar o aceite (Etapa 0.7). | Lucas |
| 21/10 | **O CRM é por loja.** Usuário com permissão para mais de uma loja vê as lojas dele no CRM: cada card indica claramente a loja e há filtro fácil para ver tudo ou lojas específicas. | Lucas |
| 21/10 | **Custo da IA e das mensagens fica com o CorePet.** Venda por **pacotes de créditos** consumidos pelo cliente, na mesma lógica de tokens dos modelos de IA. Detalhes da cobrança ficam para mais adiante. | Lucas |
| 21/10 | Lembretes continua como central operacional interna; o CRM é a camada de relacionamento. | Lucas |
| 21/10 | **Vocabulário:** "Cliente inativo" vira **"Sem comprar há 60+ dias"** (origem do lead) e a automação passa a se chamar **"Reativação de cliente"**; os estados de consentimento passam a usar a palavra "mensagens": **Autorizou mensagens**, **Autorizou no sistema · falta confirmar**, **Sem autorização de mensagens**, **Recusou mensagens automáticas** (antes "Cancelou (SAIR)"). Botão do card: **"Conversa"** com o ícone do WhatsApp, ocupando a largura do card, pois nem sempre é o ato de conversar. | Lucas |
| 21/10 | **Refino:** o card **só sinaliza "Lead novo · sem cadastro"** quando for o caso; quando o lead está ligado a uma pessoa, não mostra nenhum selo (sem código). Lead vindo do WhatsApp mostra **o nome do perfil do WhatsApp** (ou "Sem nome no WhatsApp"); **o número fica só como registro** (visível na ficha) e entra no cadastro quando a pessoa for criada ou vinculada. | Lucas |
| 21/10 | **O card indica se é só um lead ou uma pessoa já cadastrada:** "Lead novo · sem cadastro" ou "Cliente · código" (substituído pelo refino acima). Quando há cadastro, os dados da pessoa (contato, endereço, compras, cashback, crédito, pets) aparecem na ficha com acesso direto ao cadastro completo; sem cadastro, a ficha oferece vincular a um cadastro existente ou criar um. | Lucas |
| 21/10 | **Mudança de etapa no Kanban só por arrastar e soltar** (sem menu no card). A ficha do tutor mantém o campo de etapa como caminho alternativo, por ora. | Lucas |
| 21/10 | **Cada loja configura o que acontece quando o tutor recusa ou não autorizou mensagens:** conversa iniciada pelo atendente (bloquear ou só responder), lead no funil (manter, pausar, mover para Perdido) e tarefas de contato por outros meios (manter ou remover). Mensagens automáticas e modelos ficam sempre bloqueados. | Lucas |
| 21/10 | **A conversa também se acessa pelo card do Kanban:** botão "Conversar" (com contador de não lidas e estado do atendimento) abre a conversa num painel lateral sobre o quadro, sem perder filtros; o painel tem abas Conversa e Ficha 360. | Lucas |

## Visão geral das fases e etapas

| Fase | Entrega | Situação |
|---|---|---|
| Fase 1 | Planejamento macro, documentação e roadmap | **Em andamento** (escopo e roadmap prontos; revisão com o Lucas) |
| Fase 2 | Protótipo navegável (artefato) com backend conceitual, sem acesso ao sistema | **Concluída: protótipo congelado na versão 11 (22/10/2026)** |
| Fase 3 | Desenvolvimento em etapas 0 a 8 | **Em andamento: iniciando pela Etapa 0.1** |

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
- [x] P.9 Rodada de ajustes com o Lucas e congelamento do protótipo (versão 11, em 22/10/2026).

**Protótipo versão 1 (21/10):** `docs/crm/prototipo/crm-prototipo.html` (publicado também como artefato privado). Cobre Kanban com filtro de lojas e loja em cada card, ficha 360, caixa de conversas (IA, assumir, devolver, resumo, janela de 24h, notas), automações com bloqueios, configurações da loja, créditos e OPS. Contratos em `CONTRATOS_CONCEITUAIS.md`.

---

## FASE 3 — Desenvolvimento

### Etapa 0 — Saneamento (atacar um item por vez, na ordem que fizer sentido)

Origem: os 9 problemas que travam a conversa com o tutor. Cada sub-etapa tem testes que provam a correção.

**0.1 Bot não pode responder durante atendimento humano**
- [x] Barrar o bot quando a conversa está com humano ou aguardando humano (22/10/2026: `atendimento_humano_ativo` em `backend/app/whatsapp/webhook.py`; vale também para a entrada do n8n, que usa a mesma função).
- [x] Teste: mensagem nova do tutor em conversa com humano não gera resposta da IA (`backend/tests/unit/test_whatsapp_ia_pausa_atendimento_humano.py`).
- [x] Decisão de 22/10: o tutor que escreve enquanto aguarda atendente recebe o aviso "Recebemos sua mensagem. Um atendente da loja vai conversar com você em breve." Enviado no máximo 1 vez a cada 30 minutos por conversa, só enquanto aguarda atendente (não quando o atendente já assumiu); falha no envio não derruba o processamento. Implementado em `backend/app/whatsapp/webhook.py`.
- [ ] Regras finas do aviso: usar o texto por loja (configurável), respeitar quem respondeu SAIR e o horário de atendimento. `[?] DECIDIR`

**0.2 Atendimento humano: estados e devolução ao bot**
- [x] Unificar os estados do atendimento (22/10/2026): vocabulário oficial `pending`, `active`, `resolved`, `cancelled` (constantes em `models_handoff.py`); registros antigos `assigned` e `in_progress` são tratados como `active` na leitura, sem migração de dados.
- [x] Assumir um atendimento passa a mudar também o estado da conversa (rota e gerenciador usam o mesmo `sessao_assumida`).
- [x] Encerrar devolve a conversa ao bot ou fecha, conforme escolha explícita do atendente (`return_to_bot` na rota de resolver; padrão: encerrar). Resolver duas vezes é recusado. A tela do atendente ganha a opção "devolver à IA" na migração do dashboard (Etapa 5).
- [x] Corrigir a atribuição ao atendente: a conversa passa a guardar o id do usuário do atendente, não o id do cadastro de atendente.
- [ ] Ligar a transferência por sentimento, repetição e tempo de espera (hoje existe e não é chamada). `[?] DECIDIR` quais regras valem.
- [x] Testes ponta a ponta: assumir, resolver, devolver e a IA parando e voltando (`backend/tests/unit/test_whatsapp_handoff_ciclo_atendimento.py`). Falta o teste de "responder" (o envio pelo atendente é a Etapa 0.8).

**0.3 Tempo real (WebSocket) separado por loja**
- [x] Validar que o atendente da conexão pertence ao usuário e à loja (22/10/2026: `autorizar_conexao_agente` em `backend/app/routers/whatsapp_websocket.py`; qualquer falha recusa a conexão sem detalhes).
- [x] Gerenciar conexões e eventos por loja; nenhum evento cruza lojas (o envio para "todas as lojas" foi removido; todos os emissores exigem a loja).
- [x] Exigir o módulo contratado na conexão (novo `tenant_has_active_module`).
- [x] Emitir de fato os eventos de mensagem nova (webhook) e de nova fila de atendimento (transferência para humano), sempre para a loja certa e sem derrubar o fluxo em caso de falha.
- [ ] Escala com mais de uma instância (mensagens entre processos). `[?] DECIDIR` quando houver mais de uma réplica.
- [x] Testes de isolamento entre lojas e de autorização da conexão (`backend/tests/unit/test_whatsapp_websocket_isolamento_loja.py`).

**0.4 Serviço único: telefone → tutor**
- [x] Normalizar o telefone na comparação (22/10/2026): DDI 55, 9º dígito e máscara não atrapalham; compara DDD e os 8 últimos dígitos; identificadores internos do WhatsApp (@lid) não são telefone.
- [x] Um único serviço de resolução com correspondência rígida: `backend/app/whatsapp/customer_lookup.py` (`resolver_tutor_por_telefone`), usado na criação da conversa, no contexto do atendimento e no pedido pelo WhatsApp. Cadastros fundidos não participam. Vínculo antigo gravado pela regra frouxa só vale se o telefone do cadastro corresponder ao da conversa.
- [ ] Tratar ambiguidade (dois cadastros com o mesmo número): por padrão seguro, a conversa fica **sem vínculo** e a ambiguidade é registrada no log (implementado). `[?] DECIDIR` se haverá confirmação por um atendente e como ela aparece no CRM.
- [x] Ampliar o tamanho do campo de telefone da conversa e do atendimento para 40 caracteres (migração `zzzzk20261022a1`; **precisa ser aplicada no ensaio e na publicação**).
- [x] Script de conferência dos vínculos antigos, somente leitura: `python -m scripts.conferir_vinculo_sessoes_whatsapp --saida relatorio.json` (classifica: ok, duvidoso, sem vínculo único, ambíguo, sem vínculo). **Rodar no ensaio com a cópia do banco de produção antes de qualquer correção.**
- [x] Testes com formatos reais de telefone, ambiguidade e vínculo antigo (`test_whatsapp_customer_lookup.py` e `test_whatsapp_vinculo_telefone_migracao_e_conferencia.py`).

**0.5 Segredos e exposição de dados**
- [x] Token interno do orquestrador (22/10/2026): comparação em tempo constante; em produção/homologação o canal recusa tokens de exemplo (503); `WHATSAPP_ORCHESTRATOR_ALLOWED_TENANTS` (opcional) limita as lojas que o token alcança (403 fora da lista); sem token configurado o canal fica indisponível. `[?] DECIDIR` se a lista de lojas passa a ser obrigatória e se o token vira por loja (hoje é um token para o canal).
- [x] Removidos os valores padrão do fluxo n8n (loja e token fixos) e o token padrão do `docker-compose.prod.yml`. **Antes da próxima publicação: definir um token forte em `WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN` no servidor e no piloto, senão o canal interno (piloto WAHA/n8n e ponte de dados) responde indisponível.**
- [x] Webhook antigo: o token de verificação vem de `WHATSAPP_WEBHOOK_VERIFY_TOKEN` (sem token configurado, recusa) e a comparação é segura.
- [x] Teste de conexão não devolve erro interno nem a resposta crua do provedor.
- [x] Telefone mascarado nos logs (`mascarar_telefone`) e resultados de ferramentas fora dos logs do atendimento.
- [x] Criar, alterar, apagar e testar a configuração do WhatsApp exigem uma destas permissões: `ia.whatsapp`, `configuracoes.editar` ou `usuarios.manage`. Ler a configuração continua só exigindo estar na loja (a tela não recebe segredos). `[?] DECIDIR` uma permissão própria da política de permissões por tela (ver roadmap geral).
- [x] Testes de segurança e contrato (`backend/tests/unit/test_whatsapp_seguranca_canal_interno_e_config.py`).

**0.6 Custo e abuso**
- [~] Limite de uso da IA por loja: **válvula de segurança provisória** (22/10/2026) de tokens por dia por loja, medida pelas respostas já gravadas (`backend/app/whatsapp/usage_limits.py`; padrão 1.000.000 tokens/dia, ajustável em `WHATSAPP_IA_DAILY_TOKEN_LIMIT`, 0 desliga). Ao atingir, a IA para e a conversa vai para a fila de atendimento humano com o aviso de espera. **Falta ligar ao saldo de créditos (tema T.1).**
- [x] Limite de frequência por telefone (22/10/2026): acima de 15 mensagens em 10 minutos na mesma conversa, a IA para de responder em silêncio (ajustável em `WHATSAPP_IA_MAX_MESSAGES_PER_WINDOW` e `WHATSAPP_IA_WINDOW_MINUTES`). Limite por tutor (somando telefones) fica para quando o vínculo com cadastro for central (Etapa 1).
- [ ] Destino da chave de IA de reserva compartilhada entre lojas: com a decisão de 21/10 (custo da IA é do CorePet), a chave da plataforma passa a ser a chave oficial e o consumo de cada loja é medido e limitado. `[?] DECIDIR` se a loja ainda pode usar chave própria e como a chave da plataforma é guardada (hoje é variável de ambiente).
- [x] O controle de custo antigo (`ai/cost_control.py`: em memória, por processo e com identificador de loja inteiro) **não serve** para o WhatsApp e não foi ligado; foi substituído pela medição durável a partir das mensagens gravadas. Ele continua sendo usado pelo motor de IA geral (`ai/engine.py`), fora do escopo do CRM.
- [~] Medição por mensagem: modelo usado, tokens de entrada e saída **já são gravados** em cada resposta; falta o custo em créditos (tema T.1).

**0.7 LGPD operacional e consentimento**
- [~] Consentimento verificado em todo envio: regra única criada (`backend/app/whatsapp/consent_service.py`, `pode_enviar_whatsapp`; recusa do cadastro ou do contato, vale o registro mais recente; quem recusou não recebe nada, com a única exceção de responder ao tutor quando a loja permitir). Já aplicada ao bot (quem recusou não recebe resposta da IA nem aviso automático e vai para um atendente). **Falta ligar nos envios do atendente e das automações quando esses caminhos existirem (Etapas 0.8, 4 e 7).**
- [x] Palavra SAIR (e variações: parar, stop, descadastrar, "não quero receber") bloqueia na hora e fica registrada (cadastro ou contato sem cadastro, pelo número); o tutor recebe uma confirmação. Só vale a mensagem inteira, para não confundir com frases normais.
- [ ] **Configuração por situação (decisão de 21/10):** para "recusou mensagens" e "ainda não autorizou", cada loja escolhe: conversa iniciada pelo atendente (bloquear ou só responder dentro da janela), lead no funil (manter, pausar, mover para Perdido com motivo) e tarefas de contato por outros meios (manter ou remover). Padrões seguros: bloquear, manter, manter. Mensagens automáticas e modelos nunca são liberados.
- [ ] Revisar o vocabulário dos estados de consentimento em todo o sistema (Autorizou mensagens, Autorizou no sistema, Sem autorização, Recusou mensagens automáticas). `[?] DECIDIR` se o termo "SAIR" aparece ao usuário final.
- [x] Exportação e anonimização das conversas de WhatsApp entram no fluxo central de LGPD do cliente (`backend/app/whatsapp/lgpd_dados.py`): dossiê inclui conversas e atendimentos; anonimizar remove mensagens, telefone, notas e vínculo, antes de o cadastro perder o telefone. O fluxo paralelo antigo do WhatsApp (`DataDeletionRequest` e `LGPDService.process_deletion_request`) continua sem executar e será unificado ou removido na Etapa 0.8.
- [~] Auditoria de acesso: a leitura das mensagens de uma conversa passa a ser registrada (quem, quando, titular). Falta nos demais pontos (ficha do tutor, detalhe do atendimento): Etapa 5.
- [ ] **Decidir a melhor forma de solicitar o consentimento** (aceite no cadastro/PDV, mensagem de confirmação pelo WhatsApp, ou os dois). `[?] DECIDIR` — proposta inicial: aceite registrado no sistema + confirmação com botão no WhatsApp.
- [ ] Mudar a regra atual (presume consentimento) e avaliar impacto nas campanhas que já existem. `[?] DECIDIR` migração dos tutores atuais.
- [ ] Prazo de retenção das conversas. `[?] DECIDIR`

**0.8 Duplicidade e código morto**
- [~] Modelo de conversa definitivo: `whatsapp_ia_sessions` e `whatsapp_ia_messages` (decisão de 22/10/2026). O histórico de WhatsApp da ficha do cliente passou a ler deles. O modelo paralelo (`ConversaWhatsApp` e `MensagemWhatsApp`, em `backend/app/ia/aba6_aba9_models.py`) não é mais lido nem escrito por nada; **remover as classes só depois de confirmar, no ensaio com a cópia do banco de produção, que as tabelas estão vazias.**
- [~] Removidos (22/10/2026): envio em massa e notificação de entrega sem chamador em `sender.py` e o módulo de notificações simuladas (`notifications.py`, 475 linhas, sem uso). **Ainda a revisar**: módulos legados do bot (`ai_service.py`, `tools.py`, `tool_executor.py`, `context_manager.py`, `intents.py`, `templates.py`) que só aparecem em rotas de teste, o envio simulado de entrega (`services/whatsapp_service.py`, que devolve sucesso sem enviar) e o fluxo LGPD paralelo do WhatsApp (`DataDeletionRequest`).
- [x] Envio de mensagem do atendente funciona de verdade (`POST /whatsapp/messages`): só em conversa com atendente humano (ou aguardando), respeita quem recusou mensagens, sai pelo canal da loja com o autor registrado, avisa os outros atendentes em tempo real e devolve erro claro se o provedor falhar. Não há mais resposta simulada. A regra da janela de 24h entra com o canal oficial (Etapa 4).
- [x] Tela e API alinhadas: um formato único de mensagem (`backend/app/whatsapp/message_views.py`) para o chat, para o aviso em tempo real e para o histórico da ficha do cliente (que antes lia campos que a API não enviava).
- [x] Testes de contrato entre tela e API (`backend/tests/unit/test_whatsapp_chat_do_atendente.py`: campos esperados pelo chat e pela ficha, corpo do envio, regras de envio e código removido).

**0.9 Processamento confiável das mensagens**
- [~] Nova tentativa para as mensagens recebidas (22/10/2026): se a IA falhar, tenta até 3 vezes com espera (2 s e 5 s); antes de repetir, confere se uma resposta já saiu (evita responder duas vezes); esgotadas as tentativas, a conversa vai para a fila de atendimento humano (motivo `falha_tecnica`) e o tutor recebe o aviso de espera. O erro da IA não aparece no resultado. **Fila durável** (sobrevive a reinício do servidor no meio do processamento) fica para a Etapa 4.8, junto da evolução da fila de envio.
- [x] O processamento em segundo plano usa sessão de banco própria, sempre fechada, e nunca derruba a tarefa (`processar_mensagem_em_segundo_plano`).
- [ ] Tirar chamadas bloqueantes de dentro de rotas assíncronas: **não feito**. As chamadas ao banco são curtas; a que mais pesa (cliente HTTP síncrono da ponte de dados do piloto, até 20 s) só roda quando a ponte remota está ligada. Tratar junto da ponte de dados do piloto. `[?] DECIDIR` se a ponte continua existindo depois do canal oficial.
- [x] A entrada do orquestrador (n8n) responde "aceito" na hora e a IA processa em segundo plano; o atendimento humano de fallback (cliente pediu atendente) roda depois, na mesma sessão.
- [ ] Suporte a mensagens que não são texto no canal oficial (áudio, imagem). `[?] DECIDIR` escopo.
- [x] Testes de falha e nova tentativa (`backend/tests/unit/test_whatsapp_processamento_confiavel.py`).

### Etapa 1 — Fundação do módulo CRM

- [x] 1.1 Módulo "crm" registrado no back e no front (módulos premium, informações do módulo, menu "CRM", rota `/crm` protegida por módulo e permissão, página inicial provisória). Nasce **fora da oferta pública e de contratação separada**: não entra em beta, teste completo nem planos "todos os módulos" — só para lojas habilitadas explicitamente, até a decisão 1.2.
- [ ] 1.2 Entrada em planos e preço do módulo. `[?] DECIDIR` (avulso ou dentro de planos).
- [x] 1.3 Permissões `crm.visualizar`, `crm.atender`, `crm.leads`, `crm.configurar`, `crm.todas_lojas` (migração `zzzzl20261022a1`). **Backfill** sem bloquear ninguém: perfis com `ia.whatsapp` ganham visualizar/atender/leads; configurar só se também administram (`usuarios.manage` ou `configuracoes.editar`); `todas_lojas` não é concedida sozinha. Perfil padrão Gerente das lojas novas já nasce com todas. Teste de contrato do catálogo ajustado para somar as migrações.
- [x] 1.4 Modelo de dados em `backend/app/crm/models.py` + migração `zzzzm20261022a1`: funil, coluna (com tipo e janela de dias), lead, oportunidade, movimentação, interação, ação registrada e próximo passo (tabelas `crm_*`, todas por loja com RLS). Um card por pessoa cadastrada e um por telefone sem cadastro garantidos no banco (exceto cards separados). Sem ligação com a tabela `opportunities` do PDV (outro assunto). A regra de colunas (mínimo 1 entrada e 1 concluído, máximo 8) e os ciclos ficam nos serviços da etapa 2.
- [x] 1.5 **Multi-loja** (`backend/app/crm/lojas.py`, rota `GET /crm/lojas`): sem `crm.todas_lojas` o usuário vê só a loja em que está; com ela, vê também as outras lojas dele onde tem vínculo ativo, `crm.visualizar` e o módulo CRM contratado. Cada consulta roda em uma loja por vez (isolamento por RLS intacto) e cada registro volta marcado com `loja_id`/`loja_nome`; pedir loja não permitida dá 403. A tela do filtro de lojas entra com o quadro (etapa 2.2).
- [x] 1.6 Identificação do tutor e card (`backend/app/crm/leads_service.py`): usa o serviço único de telefone (0.4). Cadastro único → card do cadastro; número desconhecido ou ambíguo → card **sem cadastro** (nome "Sem nome no WhatsApp" até a loja ter outro), nunca vinculado por chute; quando o número passa a ter um único dono, o card sem cadastro é vinculado em vez de duplicar; identificador interno do WhatsApp não vira card. Funil padrão da loja nasce na primeira necessidade com as 6 colunas provisórias (`[?] DECIDIR` 2.1). Lojas com o CRM ativo ganham o card quando a primeira conversa de WhatsApp de um número começa. Falha ao criar o card só vai para o log, nunca atrapalha o atendimento.
- [ ] 1.7 Migração do menu: onde ficam o dashboard e o bot atuais no novo módulo. `[?] DECIDIR` convivência durante a transição.
- [x] 1.8 Skill `.claude/skills/crm/SKILL.md` criada. Entradas no catálogo do styleguide serão feitas junto de cada componente novo (nenhum criado ainda).
- [x] 1.9 Testes de contrato do módulo, modelo/migração, multi-loja e identificação do tutor (`test_crm_*.py`).

### Etapa 2 — Kanban de leads

- [~] 2.1 Colunas configuráveis pela loja (nome, ordem e **tipo**: entrada, em andamento, concluído, encerrado sem resultado; mínimo 1 entrada e 1 concluído; máximo 8). Modelo padrão para pet shop: Novo, Em contato, Proposta enviada, Aguardando tutor, Resolvido, Sem interesse. `[?] DECIDIR` colunas iniciais definitivas. **Regras prontas no servidor (`backend/app/crm/funil_service.py`): validação (1 entrada, 1 concluído, máx. 8, nomes únicos) e salvar colunas (remover só sem cards). Tela "Colunas" no quadro (nome, tipo, janela de dias, ordem, adicionar/remover) para quem tem `crm.configurar`, abre a primeira loja do filtro (o nome da loja aparece no título). `[?] DECIDIR` colunas iniciais definitivas.**
- [~] 2.1a **Oportunidade** como entidade dentro do lead (tipo, detalhe, estado aberta/resolvida/descartada, motivo, ciclo, marca de genérica) e regras: sinal novo soma ao card aberto; sinal genérico esmaece se houver específico; sinal específico ou genérico para card concluído abre novo ciclo e devolve o card à entrada. **Regras prontas no servidor: sinal soma ao card aberto sem duplicar, genérica por último, card final abre novo ciclo e volta à entrada. Falta ligar aos sinais reais (2.7).**
- [~] 2.1b **Ciclo** e histórico: contador de ciclo no lead, movimentações com ciclo e nota, fechamento de ciclo com resultado por oportunidade, reabertura, "Caminhada do card" na ficha, colunas finais com janela de N dias. **Regras prontas no servidor: ciclo, movimentação com ciclo e nota, fechamento com resultado por oportunidade (descartar exige motivo; encerrar exige motivo da perda), reabertura. Faltam a "Caminhada do card" na tela e a janela de N dias nas colunas finais.**
- [ ] 2.1c Ação "Separar em outro card" e marca "Separado de outro card" (a conversa continua a mesma).
- [x] 2.2 Tela do quadro (v2): colunas, cartões, contagem e valor por coluna, estados vazio, carregando e erro. **Tela `/crm` com colunas, cards, contagem e valor por coluna, carregando (esqueleto), vazio e erro.**
- [x] 2.3 Arrastar e soltar entre colunas, gravando o histórico de movimentação. Decisão de 21/10: sem menu de etapa no card. `[?] DECIDIR` como atender teclado e celular (o arrastar nativo do navegador não funciona por toque): usar biblioteca já instalada que suporta toque e teclado, ou manter o campo de etapa na ficha. **Feito com a biblioteca já instalada (dnd-kit): mouse, toque (segurar um instante) e teclado, **pela alça do card** (o resto do card rola e clica normalmente). Concluir/encerrar abre pergunta de resultado das oportunidades e motivo da perda. Decisão tomada como padrão; avisar se preferir arrastar o card inteiro.**
- [~] 2.4a **Indicação de vínculo no card:** selo "Lead novo · sem cadastro" só para lead sem pessoa (sem selo quando vinculado); título com o nome do perfil do WhatsApp, sem número no card; número guardado no lead e usado para preencher o cadastro ao criar ou vincular; ficha com os dados da pessoa vindos do cadastro de Pessoas e atalho para abrir o cadastro completo; ações "Vincular a cadastro existente" e "Criar cadastro". `[?] DECIDIR` regras de vínculo (ver Etapas 0.4 e 1.6), um lead por tutor ou por oportunidade, e leads de lojas diferentes do mesmo grupo. **Selo "Lead novo · sem cadastro" e título sem número feitos. "Ligar a um cadastro" feito na ficha. Falta "Criar cadastro" a partir do card.**
- [~] 2.4 Cartão do lead: tutor, pets, última compra, origem, responsável, próxima ação, **identificação clara da loja** (nome e marca visual). **Card mostra tutor, pets, oportunidades, próxima ação, dias na coluna (atenção após 5), ciclo, valor e loja (quando há mais de uma). Falta última compra e marca visual da loja.**
- [x] 2.5 **Filtro de lojas:** ver tudo ou lojas específicas, limitado às lojas que o usuário pode acessar; lembrar a última escolha. **Filtro de lojas (só as permitidas) com escolha lembrada neste navegador.**
- [x] 2.6 Criação manual de lead (com busca de tutor existente). **Feito: contato novo ou pessoa já cadastrada (busca por nome/telefone; quem já tem card não aparece).**
- [ ] 2.7 Criação automática de leads a partir de sinais já existentes (cliente inativo, cashback a vencer, VIP em risco, recompra atrasada). `[?] DECIDIR` quais sinais e como evitar duplicar leads.
- [~] 2.8 Detalhe do lead: interações, notas, tarefas e próxima ação com data. **Ficha do card (oportunidades, caminhada do card, linha do tempo, registrar ação, próximo passo). Falta notas/tarefas e a ficha 360 (etapa 3).**
- [~] 2.8a **Registrar ação e agendar próximo passo:** ação (tipo, observação, quem e quando) grava interação e atualiza "último contato"; próximo passo (tipo, descrição, data, hora, responsável) com atalhos de data; registrar ação pode concluir o passo; cores de atenção (sem passo e hoje em amarelo, atrasado em vermelho); contato por WhatsApp e mensagens do atendente atualizam o último contato sozinhos. `[?] DECIDIR` se o responsável recebe aviso (notificação no app ou e-mail) quando o passo vence, e se haverá visão "Minha agenda" com os passos do dia. **API pronta (ação atualiza último contato e conclui o passo; observação não conta como contato; novo passo substitui o pendente); falta a tela e as decisões de aviso e agenda.** **Ficha com registrar ação e agendar próximo passo na tela.**
- [~] 2.8c Duplo clique no card abre a ficha 360 (e clique no nome continua abrindo); formulários de ação e de agendamento em coluna única, sob demanda. **Duplo clique e clique no nome abrem a ficha; falta a ficha 360 completa.**
- [ ] 2.8b Cabeçalho fixo no painel do tutor (nome, loja, telefone, consentimento, abas).
- [~] 2.9 Filtros e busca (responsável, origem, segmento, etapa, período). **Busca por nome feita; faltam responsável, origem, segmento e período na tela (a API já filtra responsável e origem).**
- [ ] 2.10b Botão "Conversar" no card com contador de não lidas e painel lateral (conversa e ficha 360), reaproveitando o painel de conversa da Etapa 5 (um único componente).
- [x] 2.10 Contato manual por WhatsApp (link com registro da interação) enquanto o canal oficial não existe. **Botão "Conversar no WhatsApp" na ficha: abre o WhatsApp e registra o contato (atualiza o último contato).**
- [ ] 2.11 Ganho e perda: motivos de perda. `[?] DECIDIR` lista de motivos.
- [~] 2.12 Desempenho com muitos cartões (paginação por coluna) e uso no celular. **Quadro limitado a 50 cards por coluna no servidor; falta paginação "ver mais" e a tela.**
- [ ] 2.13 Testes e documentação.

**Histórico e vínculo da pessoa (27/10/2026) — feito**
- [x] Cada mensagem de WhatsApp enviada ou recebida entra na **linha do tempo do card** (resumo de até 120 letras, com quem enviou) e atualiza o **último contato** automaticamente.
- [x] O livro-razão guarda o **card de cada mensagem**; a ficha mostra o **gasto da pessoa** (enviadas, recebidas, cobráveis e custo estimado).
- [x] **Vínculo automático:** ao cadastrar ou editar uma pessoa, o card sem cadastro com o mesmo telefone passa a ser dela — só quando o número tem um único dono e a pessoa ainda não tem card.
- [x] **Conversas antigas:** ao ativar o CRM numa loja (OPS), as conversas que já existiam ganham card; o mesmo pode ser repetido por `POST /crm/importar-conversas` (por rodadas de 2.000).
- [ ] Limite mensal de gasto por loja com aviso e bloqueio `[?] DECIDIR` (avisar ou bloquear).
- [ ] Gerar oportunidades automáticas (Etapa 2.7) `[?] DECIDIR` quais sinais.

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

### O que a decisão da API oficial da Meta muda (26/10/2026)

1. **Quem paga as mensagens.** Enquanto o CorePet não for parceiro de cobrança da Meta, a Meta cobra cada loja direto no cartão da conta dela. Isso conflita com a decisão de 21/10 (custo das mensagens com o CorePet, vendido em créditos). `[?] DECIDIR` (T.1): créditos cobrem só a IA e a plataforma, ou o CorePet passa a ser parceiro e repassa o custo.
2. **Esforço da loja.** Cada loja verifica a empresa, cria o app e gera o token. `[?] DECIDIR` se o CorePet oferece o cadastro assistido como serviço (pelo OPS) e se isso entra no preço.
3. **Número.** O número não pode estar ativo em um WhatsApp comum. Usar o mesmo número no app WhatsApp Business junto da API (coexistência) só existe pelo cadastro incorporado, que depende de o CorePet ser provedor de tecnologia.
4. **Modelos de mensagem** passam a ser da conta de cada loja: o CorePet precisa criá-los e enviá-los para aprovação por loja (Etapas 4.6 e 7). A decisão de 19/10 (modelos aprovados com variáveis) continua valendo.
5. **Webhook.** Hoje cada loja usa o próprio app e a própria chave secreta, com um endereço por loja. Com o app único do CorePet será preciso mapear número → loja.
6. **Provedores antigos.** 360dialog e WAHA continuam funcionando para quem já usa; nenhuma loja troca sem ativar o oficial.
7. **Versão da API da Meta.** Fica em configuração (`META_GRAPH_API_VERSION`, padrão v26.0) porque a Meta aposenta versões antigas; conferir a cada trimestre.

### Etapa 4 — Canal WhatsApp por loja

- [~] 4.1 **Como cada loja conecta o seu número oficial: decidido em 26/10 — API oficial da Meta.** Caminho assistido pronto (4.2/4.10); caminho com poucos cliques exige o CorePet ser provedor de tecnologia da Meta (verificação da empresa, revisão do app e permissões avançadas) `[?] DECIDIR` quando iniciar essa aprovação. O código mantém o provedor trocável.
- [~] 4.2 Dados do canal por loja **feitos** (migração `zzzzo20261026a1`: ID da conta e do número, token e segredo do app criptografados em colunas próprias, estado do vínculo, qualidade, último webhook). Token e segredo ficam separados das chaves do provedor atual para que testar o vínculo nunca derrube quem está em produção.
- [~] 4.3 Camada única de envio com interface de provedor (substitui os envios espalhados), com registro persistente de cada envio: estado, tentativas e motivo da falha. **Registro persistente de cada envio e recebimento feito (26/10): livro-razão `whatsapp_ledger` (migração `zzzzp20261026a1`) — falta a camada única de envio com interface de provedor e a fila com nova tentativa.**
- [x] 4.3a **Livro-razão de mensagens (base do repasse de custos da Meta), 26/10/2026.** Uma linha por mensagem e por loja: sentido, origem (IA, atendente, sistema, tutor), provedor, tipo, modelo e categoria, janela de 24h aberta ou não, estado (enviada, entregue, lida, falhou) com horário de cada etapa, motivo da falha, e a cobrança informada pela Meta (cobrável, categoria, modelo de preço). Alimentado pelo envio, pelo recebimento e pelos avisos de estado do webhook; registrar nunca atrapalha o atendimento. Consultas: `GET /whatsapp/ledger/resumo` e `/mensagens` (loja, `crm.configurar`) e `GET /admin/whatsapp-consumo?mes=AAAA-MM` (OPS, todas as lojas). Já validado em Postgres com isolamento por loja.
- [~] 4.3b Conferência com a Meta **(27/10/2026): pronto do nosso lado.** Tarifas em reais cadastradas no OPS (nova tarifa vale a partir de uma data e nunca apaga a antiga), custo estimado por mensagem cobrável com a tarifa do dia, fechamento mensal por loja (fotografia imutável com margem e valor de repasse, arredondando o centavo uma única vez), registro da fatura real da Meta com a divergência, e histórico de quem fechou/conferiu. Mensagens cobráveis sem tarifa são sinalizadas. **Falta (depende de conta real da Meta):** confirmar o formato exato dos avisos de cobrança e, se existir, a leitura automática dos relatórios de custo da conta. `[?] DECIDIR` modelo de repasse (a margem hoje é informada no fechamento; padrão por ambiente `WHATSAPP_REPASSE_MARGEM_PERCENT`).
- [~] 4.3c Telas **feitas**: consumo da loja (`/crm/whatsapp/consumo`: totais, custo estimado, categorias, origens, lista de mensagens) e consumo de todas as lojas no OPS (`/ops/consumo-whatsapp`: tarifas, fechar o mês, fatura da Meta e conferência). Falta exportação (planilha) e o gráfico de evolução.
- [x] 4.3d Envio de **modelo aprovado** pelo sistema (`send_whatsapp_template`): respeita quem recusou mensagens (o bloqueio fica registrado como falha), grava no chat e no livro-razão com nome e **categoria do modelo** (marketing, utilidade ou autenticação). As automações da Etapa 7 devem usar sempre esta função.
- [ ] 4.4 Retorno de status do provedor (enviado, entregue, lido, falhou) e tratamento de mensagens recebidas de qualquer tipo.
- [ ] 4.5 Modelos de mensagem aprovados: catálogo padrão do CorePet por loja, variáveis, categorias e acompanhamento da aprovação.
- [ ] 4.6 Regra da janela de 24h: dentro dela texto livre, fora dela só modelo.
- [ ] 4.7 Consentimento no ponto de envio, SAIR, e fluxo de confirmação definido na Etapa 0.7.
- [ ] 4.8 Fila: evoluir a fila existente (canal WhatsApp, espera crescente entre tentativas, estado em processamento, trava para mais de uma instância) e processo dedicado como o do Bling.
- [ ] 4.9 **Consumo de créditos** por mensagem (ver T.1).
- [~] 4.10 Telas de configuração do canal na loja e no OPS (estado de saúde, qualidade do número, modelos, limites). **Feito: página de apoio `/crm/whatsapp` (passo a passo na Meta, formulário, webhook, teste e ativação). Falta a tela do OPS e o acompanhamento da qualidade/limites.**
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

## Notas de ambiente de desenvolvimento

- Testes do backend: o Docker local pode estar desligado e o Python global não tem as dependências. Foi usado um ambiente virtual isolado fora do projeto (instalando `backend/requirements.txt`) e a execução de `tests/unit -k whatsapp`. Rodar poucos arquivos isolados pode falhar na inicialização dos modelos (problema que já existia); rodar o conjunto resolve.
- Alguns testes unitários exigem `pypdf`, que não está no `requirements.txt` (já existia; fora do escopo do CRM).

## Histórico de mudanças deste documento

| Data | Mudança |
|---|---|
| 22/10/2026 | Etapa 0.9 em grande parte concluída: nova tentativa da IA com fallback para atendente, sessão de banco própria no segundo plano e entrada do n8n sem espera; falta a fila durável (Etapa 4.8) e as chamadas bloqueantes da ponte do piloto. |
| 22/10/2026 | Etapa 0.8 em grande parte concluída: envio do atendente funcionando, formato único de mensagem entre tela e API, histórico da ficha lendo do modelo definitivo e código morto removido; falta revisar o restante do legado do bot e remover o modelo paralelo após conferir o banco de produção. |
| 22/10/2026 | Etapa 2 (tela do quadro): `/crm` com colunas, cards, arrastar e soltar (mouse, toque e teclado), filtro de lojas, busca, novo card, ficha e perguntas ao concluir. Ainda não validada visualmente no navegador (sem ambiente de teste ligado). |
| 22/10/2026 | Etapa 2 (API do quadro): leitura do quadro por loja(s), criar card, mover, registrar ação, agendar próximo passo, configurar colunas e ficha do card, com permissões por loja. Telas ainda não feitas. |
| 22/10/2026 | Etapa 2 (regras do funil no servidor): colunas configuráveis, movimentação, ciclos e oportunidades com testes. Telas ainda não feitas. |
| 22/10/2026 | Etapa 1.6: número novo no WhatsApp vira card sem cadastro (ou usa o cadastro do tutor); funil padrão provisório criado sob demanda. |
| 27/10/2026 | Histórico da pessoa: mensagens na linha do tempo do card, último contato automático, gasto por pessoa na ficha, vínculo automático ao cadastrar a pessoa e cards para as conversas antigas ao ativar o CRM. |
| 27/10/2026 | Controle de custos fechado do nosso lado: tarifas, custo estimado, fechamento mensal com repasse, fatura da Meta e divergência, telas da loja e do OPS, e envio de modelo registrando a categoria. Falta só o que depende de uma conta real da Meta. |
| 26/10/2026 | Controle de mensagens: livro-razão de envio/recebimento por loja (estado de entrega, cobrança informada pela Meta, janela de 24h, falhas) e consultas de consumo (loja e OPS). Falta conferência com a Meta, créditos e telas. |
| 26/10/2026 | Canal oficial da Meta (início da Etapa 4): decisão registrada; cliente da API oficial (envio de texto, imagem e modelo), webhook da Meta com assinatura do segredo do app, rotas de salvar/testar/inscrever/ativar e página de apoio com 9 passos. Nada muda no atendimento atual até a loja ativar. |
| 22/10/2026 | Etapa 1.5: visão de várias lojas no CRM com travas de permissão, módulo e vínculo; lista de lojas permitidas pronta para o filtro da tela. |
| 22/10/2026 | Etapa 1.4: modelo de dados do CRM criado (8 tabelas por loja com isolamento) e migração encadeada. |
| 22/10/2026 | Etapa 1.1 e 1.3: módulo CRM registrado (fora da oferta pública), menu/rota/página provisória e permissões próprias com liberação automática para quem já usa o WhatsApp. |
| 22/10/2026 | Etapa 0.7 avançada (sem as decisões de consentimento e retenção): SAIR registrado e confirmado, quem recusou não recebe IA nem aviso, conversas entram no dossiê e na anonimização LGPD, leitura de mensagens auditada. |
| 22/10/2026 | Etapa 0.6 em grande parte concluída: limite de frequência por telefone e válvula de segurança de tokens por dia por loja, medidos no banco; falta ligar ao saldo de créditos (T.1). |
| 22/10/2026 | Etapa 0.5 concluída: canal interno com comparação segura e sem token de exemplo em produção, valores fixos removidos (n8n, compose de produção, webhook antigo), erro do teste de conexão sem vazamento, telefone mascarado nos logs e configuração protegida por permissão. Exige definir token forte no servidor antes da publicação. |
| 22/10/2026 | Etapa 0.4 concluída (exceto a decisão de como tratar ambiguidade na tela): serviço único telefone → tutor, vínculo antigo validado, telefone de 40 caracteres (migração nova) e script de conferência. |
| 22/10/2026 | Etapa 0.3 concluída (exceto escala com mais de uma instância, que segue a decidir): tempo real separado por loja, conexão só para o atendente da própria loja com o módulo contratado, eventos de mensagem nova e de nova fila passam a ser emitidos. |
| 22/10/2026 | Etapa 0.2 concluída (exceto a ligação das regras por sentimento, repetição e tempo, que segue a decidir): estados unificados, assumir e resolver sincronizam a conversa, devolução ao bot por escolha. |
| 22/10/2026 | Etapa 0.1 concluída: a IA não responde com atendimento humano ativo e o tutor que aguarda atendente recebe um aviso de espera (1 vez a cada 30 minutos). |
| 22/10/2026 | Protótipo congelado; Fase 2 concluída; início da Fase 3 (Etapa 0.1). |
| 21/10/2026 | Protótipo versão 11: painel de última ação e próximo passo em coluna única com formulários sob demanda; duplo clique no card abre a ficha 360. |
| 21/10/2026 | Protótipo versão 10: cabeçalho do painel fixo; registrar última ação e agendar próximo passo com data, hora e responsável; cores de atenção para passo atrasado, de hoje ou ausente. |
| 21/10/2026 | Protótipo versão 9: um card por tutor com várias oportunidades, colunas configuráveis com tipos, ciclos, fechamento por oportunidade, reabertura, separação de card, caminhada do card e simulação de sinais do dia. |
| 21/10/2026 | Protótipo versão 8: cor da origem do lead segue a diretriz (risco e prazo em amarelo, aniversário em rosa). |
| 21/10/2026 | Protótipo versão 7: diretriz de cores de atenção aplicada e legenda de cores no Mapa do protótipo. |
| 21/10/2026 | Protótipo versão 6: sem selo de código; só "Lead novo · sem cadastro"; nome do WhatsApp no card e número só na ficha. |
| 21/10/2026 | Protótipo versão 5: indicação de lead novo ou cliente cadastrado no card e dados do cadastro na ficha. |
| 21/10/2026 | Protótipo versão 4: menu de etapa removido do card; mudança só por arrastar e soltar. |
| 21/10/2026 | Protótipo versão 3: novo vocabulário, botão "Conversa" com ícone do WhatsApp, configuração por situação do consentimento (Configurações da loja > Consentimento). |
| 21/10/2026 | Protótipo versão 2: conversa acessível pelo card do Kanban (painel lateral com abas Conversa e Ficha 360). |
| 21/10/2026 | Protótipo versão 1 e contratos conceituais criados; itens P.1 a P.8 concluídos. |
| 21/10/2026 | Criação do roadmap detalhado: fases 1 a 3, Etapas 0 a 8 e temas transversais, com as decisões de 19/10 e 21/10 registradas. |
