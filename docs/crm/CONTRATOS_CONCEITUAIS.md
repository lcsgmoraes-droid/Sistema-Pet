# Módulo CRM — contratos conceituais (versão 1, a partir do protótipo)

Descrevem dados e regras como o protótipo (`prototipo/crm-prototipo.html`) as simula. Servem de ponto de partida para a modelagem real (Etapa 1) e podem mudar. Tudo é **por loja**; o usuário só vê as lojas a que tem acesso.

## Entidades

| Entidade | Para que serve | Campos principais |
|---|---|---|
| Coluna | Colunas do Kanban, configuráveis pela loja | nome, ordem, **tipo** (entrada, em andamento, concluído, encerrado sem resultado); mínimo 1 entrada e 1 concluído, máximo 8 |
| Oportunidade | Motivo de contato dentro do lead (vacina, ração, sem comprar, aniversário, cashback, VIP em risco...) | lead, ciclo, tipo, detalhe, estado (aberta, resolvida, descartada), motivo, marca de sinal genérico |
| Lead | **Um por tutor por loja**, permanente; contém as oportunidades e os ciclos | loja, tutor (cadastro opcional), telefone, etapa, origem, responsável, valor estimado, próxima ação e data, motivo de perda |
| Movimentação | Histórico de cada mudança de coluna, inclusive reaberturas e voltas | lead, ciclo, de, para, quem, quando, nota |
| Interação | Tudo que aconteceu com o tutor (mensagem, ligação, compra, vacina, banho, etapa) | lead ou tutor, tipo, resumo, origem, quando |
| Ação registrada | O que o usuário fez com o tutor (ligação, mensagem, visita, atendimento, observação) | lead, tipo, observação, quem, quando; atualiza "último contato" |
| Próximo passo | O que será feito e quando | lead, tipo (ligar, enviar mensagem, visita, oferecer, outro), descrição, data, hora, responsável |
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

**Vocabulário do consentimento (usar em todas as telas):** Autorizou mensagens · Autorizou no sistema (falta confirmar pelo WhatsApp) · Sem autorização de mensagens · Recusou mensagens automáticas. "Sem comprar há 60+ dias" é a origem do lead e "Reativação de cliente" é a automação.

**Regra por situação (configurável por loja):** quando o tutor recusou ou ainda não autorizou, a loja escolhe (1) se o atendente pode iniciar conversa ou só responder dentro da janela, (2) o que fazer com o lead (manter, pausar, mover para Perdido com motivo), (3) se tarefas de contato por outros meios (ligação, presencial) continuam. Mensagens automáticas e modelos ficam sempre bloqueados. Padrões: bloquear, manter, manter. Se o tutor recusou e escreve de novo, a IA não responde e o atendimento humano decide.

**Consentimento:** sem consentimento ou com SAIR não sai mensagem ativa (modelo ou automação). SAIR bloqueia qualquer envio. Responder a uma mensagem que o próprio tutor iniciou segue a regra da janela.

**Automação:** só dispara se a loja ligou, o tutor consentiu, o limite por tutor não foi atingido, está fora do horário de silêncio e há créditos. O disparo cai na conversa e na linha do tempo do lead e consome créditos pela categoria do modelo.

**Créditos:** cada mensagem com modelo e cada resposta da IA consomem créditos (valores de exemplo); o atendente em texto livre consome pouco. Sem saldo, a IA para e a conversa vai para a fila humana. Valores e cobrança serão definidos depois.

**Card por tutor e oportunidades:** o card é do tutor e traz todas as oportunidades abertas (a mais específica primeiro). Um sinal novo é somado ao card aberto; se o card estava concluído ou encerrado, ele **volta para a coluna de entrada** com um novo ciclo. Sinal genérico (ex.: sem comprar) fica esmaecido enquanto houver oportunidade específica. "Separar em outro card" cria um card próprio para uma oportunidade, mantendo a mesma conversa.

**Ciclo e colunas finais:** mover o card para uma coluna de tipo concluído ou encerrado pede o resultado de cada oportunidade aberta (resolvida ou descartada com motivo) e registra o fechamento do ciclo. Colunas finais mostram só os últimos N dias (configurável). Reabrir (mover de volta para coluna em andamento) devolve as oportunidades do ciclo ao estado aberto. Cada ciclo guarda a sua caminhada de colunas.

**Última ação e próximo passo:** o usuário registra ações e agenda o próximo passo (data, hora, responsável). Registrar uma ação pode concluir o passo agendado. Mensagens enviadas e recebidas pelo WhatsApp atualizam o último contato automaticamente. No card, passo ausente ou de hoje aparece em amarelo e passo atrasado em vermelho.

**Informações do card:** loja, tutor, pets, oportunidades abertas, selo de ciclo, estado do atendimento, consentimento, próxima ação, último contato, tempo na coluna (atenção após 5 dias) e valor.

**Kanban:** o card mostra a loja (nome e marca), tutor, pets, origem, responsável, próxima ação e valor. Mover entre colunas grava Movimentação. O filtro de lojas é limitado às lojas do usuário.

**Conversa pelo card:** o card do Kanban abre a conversa do lead num painel lateral (mesmo componente da caixa de conversas); o contador de não lidas e o estado (aguardando, humano) aparecem no card.

**Lead e cadastro:** o lead pode estar ligado a uma pessoa já cadastrada (tela Pessoas) ou não. O card mostra "Lead novo · sem cadastro" só para lead sem pessoa e, antes do nome, um ícone nos dois casos (pessoa com visto verde = ligado ao cadastro; pessoa com X amarelo = sem cadastro), cada um com dica ao passar o mouse (30/10). Lead vindo do WhatsApp usa o nome do perfil do WhatsApp (ou "Sem nome no WhatsApp"); o número é só registro (aparece na ficha) e preenche o cadastro quando ele for criado ou vinculado. Com cadastro, os dados da pessoa (contato, endereço, compras, ticket, cashback, crédito, pets) vêm do cadastro e aparecem na ficha, com atalho para abrir o cadastro completo; edições são feitas no cadastro, não no lead. Sem cadastro, só temos telefone e conversa; a ficha oferece vincular a um cadastro existente ou criar um. Em aberto: um lead por tutor ou por oportunidade; regra de vínculo automático; grupo de lojas.

## O que o protótipo ainda não decide

Conexão do número por loja (Etapa 4), forma do pedido de consentimento (Etapa 0.7), ambiguidade de telefone (Etapa 0.4), o que a IA faz sozinha (Etapa 6), valores e cobrança de créditos (tema T.1). Ver `ROADMAP.md`.
