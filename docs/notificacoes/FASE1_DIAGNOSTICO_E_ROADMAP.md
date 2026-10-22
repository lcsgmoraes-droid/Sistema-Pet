# Central de Notificações — Fase 1: diagnóstico e roadmap (19/10/2026)

> **Atenção (21/10/2026):** o escopo mudou para o módulo CRM voltado ao tutor. Este documento permanece como histórico do diagnóstico de WhatsApp e e-mail; o planejamento vigente está em `docs/crm/FASE1_ESCOPO_E_ROADMAP.md`. A decisão de número único do CorePet vale só para avisos da plataforma; a conversa com tutores usa o número de cada loja.

## Contexto

O Lucas quer uma central de notificações: o sistema avisa por WhatsApp e/ou e-mail quando um fluxo gera um alerta (ex.: produtos perto do vencimento). Cada notificação é criada só por nós, ligada a um fluxo, e a loja apenas liga/desliga os canais e (opcionalmente) personaliza o texto. Antes disso, é preciso garantir que envio de WhatsApp e de e-mail funcionam. O trabalho segue 3 fases: (1) planejamento/roadmap, (2) protótipo de telas + backend simulado em artefato, (3) desenvolvimento por etapas. Premissas: centralização, zero redundância, DDD/SOLID, tudo documentado, discutir conflitos.

Esta fase 1 não escreve código de produto. Entrega: branch `notificacoes` (a partir da `main`), relatório de diagnóstico e roadmap.

## Decisões já tomadas (respostas do Lucas)

- **Destinatário:** os dois, definido por notificação (contatos da loja, usuários do sistema ou tutores). Exige modelo de "destinatário" por notificação; o remetente é sempre o CorePet.
- **Remetente único da plataforma (decisão da equipe, 19/10):** todas as mensagens saem de uma conta de negócio e de um número do CorePet, e todos os e-mails saem de um SMTP do CorePet. As lojas não configuram credencial nenhuma. A configuração de WhatsApp e SMTP fica numa tela nova no **OPS** (equipe CorePet), não em Configurações da loja.
- **WhatsApp:** com conta única nossa, o caminho natural é a API oficial da Meta (Cloud API) com um número CorePet; escolher entre Meta direta ou intermediário (ex.: 360dialog) continua adiado até avaliar custos. O desenho mantém o provedor trocável.
- **Fila:** evoluir a fila já existente no Postgres. Sem Redis/RabbitMQ agora.

## Diagnóstico (resumo)

### E-mail — existe e funciona, mas só em parte
- Envio real: um único SMTP síncrono (`backend/app/services/email_service.py`, `send_email`). Configuração global por variáveis de ambiente; senha só no `.env`. Não há SMTP por loja nem tela de configuração (só Reply-To por loja).
- Pontos de chamada: ~12 rotas chamam `send_email` direto (verificação, senha, pedido de compra, onboarding, alertas, campanhas). Transporte centralizado; montagem de HTML duplicada (ERP, e-commerce, plataforma).
- Problemas graves: (a) `EmailService.enviar_email` em `acerto_service.py:421` é stub: não envia, mas marca "enviado"; (b) campanhas e "avise-me" marcam como enviado quando SMTP não está configurado; (c) sem log persistente central, sem bounce, erro engolido (só `True/False`); (d) tudo síncrono no request.
- Reaproveitável: núcleo `send_email` (TLS, correlation id), `email_envios` (status/backoff), `Tenant.email_resposta`.

### WhatsApp — só o bot de IA envia de verdade
- Envio real apenas na resposta do bot (`backend/app/whatsapp/sender.py`: 360dialog e WAHA; produção cai por padrão em WAHA, não oficial). Não há API direta da Meta.
- Notificações proativas não funcionam: entrega é mock que devolve sucesso; lista de espera importa módulo inexistente; campanhas não têm canal WhatsApp; lembretes só abrem `wa.me` no navegador; `send_bulk_messages` e `NotificationManager` são código morto.
- Lacunas: sem status de entrega (queued/sent/delivered/failed), sem retry, sem templates aprovados (HSM) nem regra da janela de 24h, consentimento não aplicado no envio, atendente humano não envia (só grava), sem tela de configuração do provedor (só OpenAI), token fixo `meu_token_secreto` em `whatsapp_routes.py:169`, `message_id` nulo no WAHA.
- Bom e reaproveitável: credenciais criptografadas (Fernet) em `tenant_whatsapp_config`, RLS, webhook de entrada autenticado e idempotente.

### Infra de fila/agendamento
- Não há Redis/RabbitMQ no servidor. Fila real = Postgres (`notification_queue`, `campaign_event_queue`) com `SKIP LOCKED`, idempotência por chave, retry (sem espera entre tentativas), consumidor `NotificationSender` (só email e push).
- Jobs: APScheduler dentro do backend, líder por arquivo (vale por container; impede escalar réplicas). Crons em horário fixo do servidor; `Tenant` não tem fuso. Não existe job das 23:00 diário.
- Modelos a copiar: `worker-bling` (processo dedicado com heartbeat), tick por loja de `product_recurrence`, tela de config (card em `Configuracoes.jsx` + rota em `SettingsAdminRoutes.jsx` + submenu em `menuConfig.js` + página em `pages/configuracoes/`), `AppointmentReminderConfig` (config de notificação por loja), Fernet para segredos.

### Veredito
Os dois recursos NÃO estão prontos para sustentar a central. E-mail precisa de log, correção dos stubs/falsos "enviado" e config por loja. WhatsApp precisa de envio proativo de verdade, status, templates e consentimento. Primeiro nasce uma camada única de envio por canal; a central usa só essa camada.

## Roadmap proposto

**Fase 1 (esta):** branch `notificacoes`; documento de diagnóstico completo; este roadmap; decisões pendentes abaixo.

**Fase 2 — protótipo (artefato, backend simulado, sem acesso ao back):**
1. Tela OPS → Mensageria: configuração global do WhatsApp (conta/número, provedor, modelos aprovados) e do SMTP (remetente), com teste de envio e estado de saúde. Tela da loja Configurações → Notificações: lista de notificações (descrição em markdown, canais, textos, variáveis disponíveis, destinatários, "enviar teste").
2. Painel de histórico/estado dos envios (fila, falhas, reenviar).
3. Contratos conceituais: modelo de notificação (código, descrição, canais, frase por canal, variáveis, destinatários), regras de variáveis (`{{produto}}`), idempotência, janela de 24h/template.

**Fase 3 — desenvolvimento em etapas (front primeiro, uma peça por vez):**
- A. Fundação de canais: `EmailSender` e `WhatsAppSender` com interface única de provedor; log persistente de envios (status/erro/tentativas); corrigir stubs e falsos "enviado".
- B. Config global da plataforma (OPS): tabela de configuração da plataforma (não por loja) com segredos criptografados (Fernet) para SMTP e WhatsApp; tela no OPS; hoje o SMTP vem só do `.env` e o WhatsApp é por loja (`tenant_whatsapp_config`), então o envio proativo passa a ignorar a config por loja. O bot de IA continua com a config por loja. Na loja fica só: contatos que recebem (celular/e-mail), liga/desliga por canal e texto.
- C. Fila: evoluir `notification_queue` (espera entre tentativas, estado "em processamento", canal WhatsApp), worker dedicado no compose; lease/lock para suportar mais de uma réplica.
- D. Central: catálogo de notificações definido em código (loja só liga/desliga e edita texto), serviço único `notificar(codigo, contexto)` chamado pelos fluxos; destinatários por notificação; consentimento aplicado no ponto de envio.
- E. Primeira integração: produtos próximos do vencimento (hoje processado só ao abrir /lembretes; exige job agendado e fuso da loja — ver backlog da skill `lembretes`).
- F. Status de entrega (webhooks do provedor), templates WhatsApp, tratamento de opt-out.

Cada etapa: documentação em `.claude/skills/notificacoes/SKILL.md`, testes, ensaio com cópia do banco de produção antes de qualquer deploy (regra do projeto).

## Pontos a discutir (conflitos/dúvidas)

1. Destinatário "tutor" reabre a regra de consentimento (LGPD) e a janela/template do WhatsApp; confirmar se entra já na primeira entrega ou só depois.
2. Fuso: `Tenant` não tem timezone e a padronização de datas (UTC) é atividade separada; a central precisa de pelo menos fuso por loja para o horário das 23:00.
3. Custo do WhatsApp agora é nosso: levantar preço por conversa da Meta e definir limite/cota por loja e por plano para evitar abuso.
4. Número único: toda mensagem à loja precisa abrir com o nome da loja e usar modelos aprovados pela Meta (envio proativo sempre exige modelo); texto livre da loja vira variáveis dentro de modelos aprovados — conflito com "personalizar a frase", a discutir.
5. Opt-in/LGPD: o CorePet passa a ser o remetente; cada contato (loja ou tutor) precisa de consentimento registrado e opt-out ("SAIR"). Reputação do número único: uma loja com spam pode derrubar a qualidade do número de todos; exige limite de envio e monitoramento.
6. E-mail com remetente único: reputação do domínio (SPF/DKIM/DMARC) e provedor transacional em vez de Gmail; Reply-To por loja (já existe) para respostas.
7. Segurança: corrigir o token fixo do webhook e o vazamento de erro no teste de conexão independentemente da central.

## Verificação (quando executar)
- Branch criada a partir da `main` atualizada; `git status` limpo.
- Documento de diagnóstico revisado com o Lucas antes de iniciar a Fase 2.
- Fase 2 em artefato publicado privado para validação visual; nada tocará o backend.

## Decisões da segunda conversa (19/10/2026)

1. **Modelos prontos na Meta, com variáveis.** A mensagem proativa usa modelo aprovado pela Meta; as partes que mudam (ex.: dias restantes) são variáveis do modelo preenchidas pelo sistema. A loja não edita a frase; edita, no máximo, o que o modelo permitir.
2. **Sem disparo ativo pelas lojas nesta fase.** Só processos específicos do sistema disparam. Mesmo assim, haverá limite de envio (rate) por loja e por destinatário como proteção.
3. **LGPD/consentimento entra já nesta fase.** Registro de consentimento com prova (quem, quando, como), confirmação pelo próprio WhatsApp ("quero continuar recebendo") e opt-out.
4. **Fuso fica na atividade de padronização de datas.** Por ora os processos que disparam chamam a notificação de forma síncrona, no próprio método, com envio imediato (falha registrada e reprocessada pelo worker, sem quebrar o fluxo de negócio).
5. **E-mail segue pelo Gmail no MVP.** Provedor transacional + SPF/DKIM/DMARC fica como pendência importante, tratada no final.
