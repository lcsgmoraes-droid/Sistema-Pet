# Módulo CRM — Fase 1: escopo, diagnóstico e roadmap (21/10/2026)

## Contexto

O escopo mudou. A "central de notificações" interna virou um **módulo de CRM voltado ao cliente final (tutor)**: Kanban de leads, conversa por WhatsApp, atendimento por IA com passagem para humano, tudo cruzado com compras, pets, vacinas e histórico para gerar oportunidades. As mensagens automáticas (aniversário, ração acabando, vacina, medicação) passam a ser uma parte do módulo, não o centro. Continuam as três fases combinadas: (1) planejamento e roadmap, (2) protótipo de telas com backend conceitual em artefato, (3) desenvolvimento por etapas. Premissas: centralização, zero redundância, DDD/SOLID, tudo documentado, discutir conflitos.

O diagnóstico e o roadmap anteriores estão em `docs/notificacoes/FASE1_DIAGNOSTICO_E_ROADMAP.md` e o protótipo anterior no artefato já publicado; ambos serão revisados, não descartados.

## Decisões fechadas (Lucas, 21/10)

- **Número do WhatsApp:** cada loja usa o **seu próprio número oficial**. Isso substitui a decisão do número único do CorePet para tudo que é conversa com tutor. O número do CorePet pode continuar existindo só para avisos da plataforma para a loja (a confirmar).
- **Módulo novo "CRM"**, com permissões e menu próprios, absorvendo o WhatsApp atual (dashboard e bot) como parte dele.
- **Ordem: Kanban primeiro.** O funil de leads, com dados do cliente, nasce antes do canal de WhatsApp; no início o WhatsApp é um link manual.
- Fila de envio: evoluir a que já existe no Postgres (decisão anterior mantida). Gmail no MVP para e-mail (decisão anterior mantida). Fuso e datas ficam na atividade separada.

## O que o sistema já tem (resumo dos levantamentos)

**Reaproveitável**
- Entrada de WhatsApp com validação, deduplicação e suporte a áudio e imagem; sessões e mensagens por telefone; envio por dois provedores; segredos criptografados; isolamento por loja.
- Bot de IA (OpenAI, chave por loja) que consulta produtos, estoque, última compra, entrega, crédito e cria rascunho de pedido; regras de transferência para humano.
- Estrutura de atendimento humano: atendentes, fila, prioridade, notas internas e estatísticas.
- Biblioteca de arrastar e soltar já instalada; padrão de WebSocket já usado; estado do módulo e telas em v2.
- Dados para a visão 360: cliente e pets, vendas e itens, recorrência de produto, ração informada no PDV, vacinas, consultas, retornos, prescrições, banho e tosa, aniversários, inativos, segmentos (VIP, risco etc.), cashback, ranking, pedidos online, entregas e avaliações.
- Gatilhos de mensagem que já existem: recompra, próxima dose, lembretes de consulta e banho, aniversário, inativos, cashback a vencer, ranking, cupom pós-compra. Hoje saem por push; WhatsApp é manual ou simulado.

**Não existe**
- Lead, funil, etapas, histórico de movimentação, cartão de Kanban.
- Resposta do atendente humano pelo sistema (a tela de conversa não funciona de ponta a ponta); eventos de mensagem nova em tempo real.
- Consentimento aplicado no envio; opt-in no cadastro; tratamento de SAIR; limite de frequência por cliente.
- Alertas de vacina vencendo, retorno vencido e fim de medicação (só relatório). Linha do tempo do cliente com vacinas, consultas, banho, lembretes e contatos. Previsão de fim de ração ligando peso do pet e consumo.
- Cadastro automático de cliente ou lead a partir de um telefone desconhecido.

## Problemas que precisam ser resolvidos ANTES de colocar tutor em conversa (etapa 0)

1. **O bot continua respondendo quando o atendimento já foi passado para humano** (nenhuma checagem do estado da sessão). Dupla resposta ao tutor.
2. **Encerrar o atendimento humano pela API não devolve a conversa ao bot**; os estados do handoff divergem entre modelo, regra e tela; a atribuição grava um tipo de identificador incompatível.
3. **WebSocket sem separação por loja:** um usuário autenticado pode se conectar como qualquer atendente, e eventos podem ir para lojas erradas; a rota nem exige o módulo contratado.
4. **Vínculo telefone → cliente frouxo na criação da sessão** (pode ligar ao cliente errado e expor dados de outra pessoa); existe uma versão rígida que deve virar o único serviço de resolução, com número normalizado (DDI e 9º dígito).
5. **Segredos:** token interno global com loja na URL, comparação não segura, valores padrão de desenvolvimento no fluxo n8n, token fixo no webhook antigo, vazamento de erro interno no teste de conexão, logs com telefone e dados de ferramentas.
6. **Custo e abuso:** sem limite de custo por loja, sem limite de frequência; chave OpenAI de reserva compartilhada entre lojas.
7. **LGPD ainda é casca:** exclusão, exportação e anonimização não executam; consentimento não é verificado no fluxo do bot; a regra atual presume consentimento (opt-out).
8. **Duplicidade a resolver:** existe um segundo modelo de conversa paralelo e sem uso; código morto do bot e do envio em massa; stub de mensagem do atendente.
9. **Processamento:** webhook sem fila nem nova tentativa (mensagem que falha é perdida para o bot); chamadas bloqueantes dentro de rotas assíncronas.

## Roadmap proposto

**Fase 1 (esta):** documento do CRM em `docs/crm/` (escopo, decisões, diagnóstico, riscos, roadmap) na branch `notificacoes`; revisão do documento anterior.

**Fase 2 — protótipo em artefato (backend simulado, sem acesso ao sistema):**
1. Kanban de leads: etapas configuráveis, cartões com tutor, pets, última compra, origem, responsável e próxima ação; arrastar entre etapas; criação manual e automática.
2. Ficha 360 do tutor: linha do tempo unificada (compras, pets, vacinas, consultas, banho, lembretes, mensagens, cashback), oportunidades sugeridas.
3. Caixa de conversas: todas as conversas, quem responde (bot, humano, aguardando), assumir e devolver ao bot, notas internas, resposta do atendente, janela de 24h e modelos.
4. Atendimento por IA: regras de parada, transferência, resumo da conversa para o atendente, o que a IA pode consultar e fazer.
5. Automações: catálogo de gatilhos (aniversário, ração acabando, vacina, medicação, inativo, recompra), modelo de mensagem, consentimento e limites; o que cada loja liga ou desliga.
6. Configuração do canal por loja: conexão do número, estado de saúde, modelos aprovados; e a tela do OPS (revisada) para a plataforma.

**Fase 3 — desenvolvimento em etapas (cada uma entrega valor e passa por ensaio com cópia do banco de produção antes de qualquer envio para produção):**
- **0. Saneamento** dos itens acima (parar bot em atendimento humano, WebSocket por loja, serviço único de telefone → cliente, segredos, limites).
- **1. Fundação do módulo CRM:** registro do módulo e permissões, menu, rotas, modelos de lead, etapa, movimentação e interação, serviço único de identificação do tutor.
- **2. Kanban** com dados do cliente; leads manuais e automáticos a partir de sinais já existentes (inativo, cashback a vencer, VIP em risco); WhatsApp ainda manual.
- **3. Ficha 360 e linha do tempo unificada;** previsão de fim de ração e alertas de vacina, retorno e medicação (hoje inexistentes).
- **4. Canal WhatsApp por loja:** conexão do número, envio real, status de entrega, modelos, janela de 24h, consentimento com aceite e SAIR, fila com nova tentativa; e-mail como segundo canal.
- **5. Caixa de conversas:** resposta do atendente, tempo real seguro por loja, mídia, notas.
- **6. IA no atendimento:** ferramentas ligadas ao 360 e à agenda, parada e retorno, atualização automática do estágio do lead, controle de custo.
- **7. Automações de mensagem** pelos gatilhos, com limite de frequência por cliente e conversão acompanhada no Kanban.
- **8. Relatórios** de conversão e atendimento; remoção do que ficou obsoleto (tela de lembretes e dashboard antigo migram ou convivem).

## Pontos a discutir antes do protótipo

1. **Conexão do número de cada loja:** exige que o CorePet seja parceiro de tecnologia da Meta ou use um intermediário oficial (como 360dialog, que já existe no código), com cadastro guiado dentro do sistema. Define custo, prazo e esforço de onboarding. Pode ser adiado até a etapa 4 porque o Kanban vem primeiro, mas o protótipo precisa mostrar como será.
2. **Consentimento:** o modelo atual presume consentimento (opt-out). O CRM com mensagens ativas pede opt-in registrado no cadastro e confirmação pelo próprio WhatsApp, com prova e SAIR (decisão anterior mantida). Isso muda regras de campanhas já existentes.
3. **Mensagens ativas fora da janela de 24h** só com modelo aprovado, e agora cada loja precisa aprovar os seus; haverá um catálogo de modelos padrão que o CorePet cadastra por loja.
4. **Dados entre lojas do mesmo grupo:** cliente e pet são legíveis entre lojas do grupo, mas vendas e histórico são por loja. O CRM deve decidir se enxerga o grupo ou só a loja.
5. **IA:** chave OpenAI por loja (cobrança nas mãos da loja) ou cota do CorePet; limite de custo; o que a IA pode fazer sozinha (criar pedido? agendar?). Quem fica responsável em caso de erro.
6. **Telas existentes:** `/lembretes` e o dashboard de WhatsApp coexistem com o CRM ou migram? Sugestão: Lembretes continua como central operacional interna e o CRM é a camada de relacionamento.
7. **Tutor sem cadastro:** número desconhecido vira lead sem cliente; quando e como vira cliente (fusão com cadastro existente).
8. Retenção e LGPD das conversas (prazo, exclusão, auditoria de acesso).

## Verificação (nesta fase)
- Documento do CRM revisado com o Lucas; branch `notificacoes` continua a mesma.
- Protótipo publicado como artefato privado para validação visual; nada toca o backend.
- Em cada etapa da Fase 3: testes de contrato do módulo e de isolamento por loja, ensaio com cópia do banco de produção, validação visual do Lucas e só então pedir autorização para qualquer envio para produção.
