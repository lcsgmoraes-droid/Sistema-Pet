# Módulo CRM — contratos conceituais (versão 1, a partir do protótipo)

Descrevem dados e regras como o protótipo (`prototipo/crm-prototipo.html`) as simula. Servem de ponto de partida para a modelagem real (Etapa 1) e podem mudar. Tudo é **por loja**; o usuário só vê as lojas a que tem acesso.

## Entidades

| Entidade | Para que serve | Campos principais |
|---|---|---|
| Funil e Etapa | Colunas do Kanban, configuráveis pela loja | nome, ordem, final (ganho ou perdido) |
| Lead | Pessoa em acompanhamento comercial | loja, tutor (cadastro opcional), telefone, etapa, origem, responsável, valor estimado, próxima ação e data, motivo de perda |
| Movimentação | Histórico de cada mudança de etapa | lead, de, para, quem, quando |
| Interação | Tudo que aconteceu com o tutor (mensagem, ligação, compra, vacina, banho, etapa) | lead ou tutor, tipo, resumo, origem, quando |
| Conversa | Troca de mensagens por WhatsApp | loja, lead, estado, última mensagem do tutor, mensagens |
| Mensagem | Item da conversa | de (tutor, IA, atendente, sistema, nota interna), texto ou modelo, estado de entrega, custo em créditos |
| Canal da loja | Número oficial da loja | loja, número, provedor, estado, qualidade |
| Modelo de mensagem | Texto aprovado pela Meta com variáveis | código, categoria, situação, texto, variáveis |
| Automação | Regra gatilho → modelo | gatilho, modelo, lojas em que está ligada, limite |
| Consentimento | Prova de que o tutor quer receber | tutor, canal, estado, prova (aceite no sistema e/ou botão no WhatsApp), data, SAIR |
| Crédito | Saldo e extrato da loja | pacote, saldo, lançamentos (compra, consumo por mensagem ou IA) |

## Estados e regras

**Conversa:** IA atendendo → (pedido de atendente, reclamação, créditos acabaram) → aguardando atendente → humano atendendo → devolvida à IA ou encerrada. Nova mensagem do tutor reabre uma conversa encerrada. Enquanto está com humano ou aguardando, a IA não responde.

**Transferência:** a IA passa para humano quando o tutor pede, quando há reclamação e quando os créditos acabam; gera um **resumo** para quem assume.

**Janela de 24h:** dentro dela o atendente escreve texto livre; fora dela só modelo aprovado.

**Consentimento:** sem consentimento ou com SAIR não sai mensagem ativa (modelo ou automação). SAIR bloqueia qualquer envio. Responder a uma mensagem que o próprio tutor iniciou segue a regra da janela.

**Automação:** só dispara se a loja ligou, o tutor consentiu, o limite por tutor não foi atingido, está fora do horário de silêncio e há créditos. O disparo cai na conversa e na linha do tempo do lead e consome créditos pela categoria do modelo.

**Créditos:** cada mensagem com modelo e cada resposta da IA consomem créditos (valores de exemplo); o atendente em texto livre consome pouco. Sem saldo, a IA para e a conversa vai para a fila humana. Valores e cobrança serão definidos depois.

**Kanban:** o card mostra a loja (nome e marca), tutor, pets, origem, responsável, próxima ação e valor. Mover entre colunas grava Movimentação. O filtro de lojas é limitado às lojas do usuário.

**Lead sem cadastro:** número desconhecido vira lead sem tutor e pode ser vinculado a um cadastro existente.

## O que o protótipo ainda não decide

Conexão do número por loja (Etapa 4), forma do pedido de consentimento (Etapa 0.7), ambiguidade de telefone (Etapa 0.4), o que a IA faz sozinha (Etapa 6), valores e cobrança de créditos (tema T.1). Ver `ROADMAP.md`.
