# Atualização automática da promoção iFood

| Campo | Valor |
|---|---|
| Data / executor | 2026-10-20 / Codex |
| Responsável de negócio | Lucas |
| Branch / PR | `codex/ifood-calculadora-central` / #1533 |
| Tipo / risco | Funcionalidade / médio: preço vigente e concorrência de consultas |
| Domínios | Cadastro canônico, central iFood e calculadora de contribuição |

## 1. Necessidade e aceite

O teste de promoção identificou que as telas precisavam de recarga no início e
no fim. Agora devem consultar automaticamente preço, margem e pendências nessas
viradas, preservando campos não salvos, filtros, página, modalidade e preço
simulado. A consulta não salva o produto nem publica no provedor. A calculadora
deve distinguir a oferta salva do resultado do preço simulado.

## 2. Regras e dados

A API continua sendo a autoridade da vigência. Mantém início e fim inclusivos;
a consulta de encerramento é agendada após o fim. Preços, promoções de outros
canais, estoque e taxas não são alterados pela atualização. Horários são enviados
em UTC, com referência ao relógio do servidor. Não há dados pessoais novos.

## 3. Arquitetura e integração

As leituras retornam `evaluated_at` e `next_price_change_at`. O catálogo calcula
a próxima mudança em todos os produtos do tenant, antes de busca/filtro/página,
para não perder itens que passem a ter pendências. O filtro opcional `product_id`
permite atualizar a oferta salva da calculadora mesmo fora da lista visível.

Um agendador compartilhado agenda a próxima virada, recupera a leitura ao voltar
à aba e cancela timers/listeners ao desmontar. Não há polling contínuo. Respostas
novas rearmam o agendamento; falhas têm tentativas limitadas e aviso. Requisições
antigas são canceladas/ignoradas. O cadastro consulta seu rascunho atual; a
calculadora consulta separadamente oferta salva e preço digitado.

## 4. Segurança e privacidade

Endpoints e permissões de consulta existentes, filtro sempre dentro do tenant,
sem credenciais novas. Nenhuma chamada ao iFood, nem alteração de suas flags de
escrita/pedidos/polling. Sem novos logs com dados de clientes ou segredos.

## 5. Desenvolvimento e qualidade

Testes temporais cobrem início, fim inclusivo, fuso, filtros e paginação. Testes
com relógio/timers controlados cobrem cancelamento, suspensão, repetição,
reagendamento e limites de timeout. Lint, build e validação real em Chrome devem
comprovar as duas viradas mantendo um campo não salvo e um preço simulado.
Resultados no [registro de homologação](../homologacoes/2026-10-20-atualizacao-automatica-promocao-ifood.md).

## 6. Ambientes e homologação

DEV isolado `corepet-ifood-dev`, porta 18081, tenant e produto fictícios. A
prévia 18080 e produção ficam fora do escopo. A fonte do rebuild é este worktree,
com override do Compose oficial fora do Git. Dados e imagens locais preservados.

## 7. Publicação e rollback

Entrega frontend/backend. Ao atualizar a branch com a main, identificou-se uma
colisão: nossa merge Alembic ainda em PR e a migration fiscal da main usavam
`zzzzl20261020a1`. A migration fiscal da main permanece intacta. A merge do PR
passa a `zzzzm20261020a1`, unindo iFood g e fiscal l; um teste detecta IDs duplicados.

Somente o DEV que já tinha a antiga merge l precisa corrigir o registro de
versões: verificar esquema e versão, representar os ramos realmente aplicados
g+k com `alembic stamp --purge zzzzg20261019a1 zzzzk20261020a1`, e aplicar o
upgrade para m. Isso não desfaz nem recria dados. Não executar esse reparo em
outro ambiente sem verificar seu histórico. Bancos novos seguem upgrade normal.

Rollback preferencial por código/imagem anterior, preservando colunas aditivas;
não executar downgrade em banco com dados. Produção depende de autorização
específica e está fora desta entrega.

## 8. Observabilidade e sustentação

Sem recarga da página, os valores e avisos mudam após a resposta da virada. Falha
de rede mantém os últimos dados com indicação de erro; tentativas são limitadas.
Voltar à aba ou tentar novamente permite recuperação. Navegador suspenso pode
adiar a atualização até retornar; rede indisponível impede uma leitura nova.

## 9. Comunicação e treinamento

O usuário pode deixar cadastro e calculadora abertos durante a promoção.
Digitar continua sem salvar; somente Atualizar/Aplicar grava alterações. Reforçar
a diferença entre preço regular salvo e preço promocional vigente. Nenhum novo
controle ou fluxo de publicação foi adicionado; componentes V2 preservados.

## 10. Fechamento

Validação técnica aprovada: 47 testes backend e 46 frontend, contrato de rotas,
lint, formatação e build passaram. Revisão independente sem bloqueadores. No
Chrome, a janela real 16:10–16:12 mudou preço, margem e pendências sem recarga,
preservando nome em edição, busca e input 160. Após o fim, oferta salva 150 e
simulação 160; confirmação independente do banco mostrou que os rascunhos não
foram gravados. As duas abas ficaram abertas para o aceite do Lucas.

Migração de convergência aplicada apenas no DEV, com produto e imagem intactos.
Nenhum deploy de produção ou envio ao iFood executado. A promoção de teste ficou
encerrada e armazenada para revisão, sem novas gravações automáticas.
