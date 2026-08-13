# Matriz da demonstração CorePet — Growth AgroPet

Apresentação: sexta-feira, 14/08/2026, às 16h  
Público principal: Lucas (proprietário) e Valdo (administrador)  
Objetivo: demonstrar ganho operacional e financeiro em uma loja física com vendas, estoque, compras e entregas.

## Regra da demonstração

Cada lançamento mostrado deve terminar com a conferência dos seus efeitos colaterais. Não basta o botão responder: a informação precisa chegar ao estoque, financeiro, DRE, comissão, entrega ou pendência correspondente.

## Roteiro principal — 35 a 45 minutos

| Ordem | Tela / história | Ação ao vivo | Efeitos que precisam aparecer | Situação em 12/08 |
|---|---|---|---|---|
| 1 | Dashboard | Abrir visão geral em 30 dias | venda bruta, caixa, ticket médio, bancos, contas, produtos e clientes | Pronto, com 54 vendas operacionais distribuídas em até 88 dias |
| 2 | PDV — venda simples | Vender produto à vista, sem entrega e sem comissão | baixa de estoque, venda paga, entrada no caixa, receita/CMV/lucro e DRE | Dados existentes; refazer teste final |
| 3 | PDV — cartão e margem | Vender no cartão os produtos `DEMO-MARGEM-VERDE`, `DEMO-MARGEM-AMARELA` e `DEMO-MARGEM-VERMELHA` | taxa do cartão, conta a receber, margem líquida e alerta verde/amarelo/vermelho | Validado visualmente no DEV em 13/08 |
| 4 | PDV — comissão | Fazer venda com Beatriz Vendedora Demo | comissão em aberto e redução correta do resultado | Validado: comissões abertas e DRE vinculadas |
| 5 | PDV — entrega | Fazer venda com Carlos Entregador Demo | entrega aberta, rota, taxa, custo, resultado da entrega e histórico | Pronto, com rotas em 3 estados |
| 6 | Produtos e estoque | Abrir o produto comprado/vendido | saldo, custo, preço, fornecedor e movimentações | Pronto, com catálogo |
| 7 | Pedido inteligente | Selecionar Distribuidora Horizonte Pet Demo e gerar o pedido | sugestão, PDF/envio, pedido em rascunho/enviado/recebido/cancelado | Pacote local pronto; aguarda publicação |
| 8 | Entrada de NF-e | Importar a NF sintética `901010` | fornecedor e oito produtos reconhecidos, pedido novo disponível para vínculo e conferência | XML preparado para o pedido gerado pela Sugestão Inteligente |
| 9 | Confronto com divergência | Importar XML com quantidade e preço diferentes | diferença de quantidade/preço, relatório, novo orçamento e opção de devolução | XML divergente validado + cenários prontos |
| 10 | Pendências | Alternar Aberta, Aguardando, Tratativa, Resolvida e Cancelada | cards, filtros, histórico e valores por status | Seed local com 5 status; aguarda publicação |
| 11 | Financeiro | Abrir venda, contas a receber, fluxo, bancos e DRE | rastreabilidade da venda até caixa e resultado | Pronto, com dados |
| 12 | Conciliação de cartões | Processar o confronto PDV x Stone Demo | 7 matches corretos, 1 divergência de parcelas, 1 NSU órfão e 1 venda sem NSU | Validado pela tela real no DEV em 13/08 |
| 13 | Fechamento | Abrir Análise Inteligente e DRE por canal | oportunidades, CMV, impostos, lucro e margem | Pronto; selecionar Loja Física + E-commerce + App |

## Cenários de compras preparados

O seed do Demo prepara oito pedidos para que a apresentação não dependa de alterar o mesmo registro no meio da reunião. O fornecedor fica sem rascunho aberto, permitindo gravar uma nova Sugestão Inteligente sem aviso de substituição:

1. Enviado ao fornecedor.
2. Recebido totalmente, sem divergência.
3. Recebido com divergência de quantidade e preço.
4. Pendência aguardando fornecedor.
5. Pendência em tratativa.
6. Pendência resolvida.
7. Pedido cancelado.
8. Pedido confirmado como modelo para refazer e confrontar o XML ao vivo.

Fornecedor: `Distribuidora Horizonte Pet Demo LTDA` — código `DEMO-FOR-001`.
Marca: `VivaPata Demo`.
Catálogo de compras: dez produtos fictícios `DEMO-VP-001` a `DEMO-VP-010`,
todos ligados ao mesmo fornecedor e com histórico de venda/estoque suficiente
para preencher a Sugestão Inteligente. O produto principal dos pedidos e XMLs
é `Ração VivaPata Essencial Cães Adultos Frango 10 kg`.

## XMLs sintéticos para a demonstração

O XML `DEMO_NFE_901010_PEDIDO_INTELIGENTE.xml` é um cenário de homologação,
não tem valor fiscal e nunca deve ser usado como documento real. Ele contém os
oito itens que a Sugestão Inteligente preenche no pedido, com total de
R$ 2.507,48.

Sete itens coincidem com as quantidades e custos do pedido sugerido. O item
`HORIZONTE-002` traz a divergência controlada: pedido de 39 unidades a
R$ 22,17 e NF de 37 unidades a R$ 23,10. O número `901010` não colide com as
seis notas `900001` a `900006` que deixam os demais estados preenchidos.

Fluxo do ensaio final pela interface: criar um novo pedido para a Distribuidora
Horizonte Pet Demo, abrir a Sugestão Inteligente, selecionar os itens
preenchidos e salvar o pedido. Depois acessar `Compras > Central NF-e Entradas >
Importar XML`, escolher a NF `901010`, voltar ao pedido recém-criado, clicar em
`Confrontar XML` e selecionar a nota. Não processe a entrada no ensaio anterior
à gravação; encerre antes da etapa que altera estoque e financeiro.

Arquivos locais: `C:\Users\lcs_g\Downloads\CorePet_Demo_XML`.

## Cenários controlados de margem no PDV

Os três produtos abaixo custam R$ 100,00 na venda e existem apenas para tornar a demonstração previsível. A forma `Cartao de credito` usa taxa de 3,49% e a operadora `Stone Demo` fica selecionada automaticamente.

| Pesquisa no PDV | Custo | Resultado esperado |
|---|---:|---|
| `DEMO-MARGEM-VERDE` | R$ 45,00 | indicador verde; parcelamento permitido dentro da faixa saudável |
| `DEMO-MARGEM-AMARELA` | R$ 69,50 | indicador amarelo; aviso para evitar desconto/parcelamento adicional |
| `DEMO-MARGEM-VERMELHA` | R$ 82,00 | indicador vermelho; justificativa obrigatória para prosseguir |

O teste visual no DEV confirmou os três estados. A auditoria também detectou e corrigiu uma inconsistência antiga: o endpoint usava limites fixos de 20%/10%. Agora ele respeita os limites configurados para a empresa (30% saudável e 15% alerta no Demo).

## Conferência aba por aba

### Já demonstráveis

| Módulo | Evidência encontrada no Demo | Conferência ainda necessária |
|---|---|---|
| Dashboard | 54 vendas demo retroativas, ticket médio, bancos, contas, produtos e clientes | pronto no DEV |
| PDV | cliente, produto, entrega, comissão, vendas recentes e cartão nas 3 faixas | repetir ensaio final sem concluir as vendas vermelhas |
| Entregas abertas | entrega disponível para roteirização | diálogo novo após publicação |
| Rotas | pendente, em rota e concluída | iniciar/reverter sem estragar o cenário principal |
| Histórico de entregas | rota concluída, distância e custo | conferir detalhamento |
| Financeiro de entregas | cards de custo e desempenho | cruzar com rota concluída |
| Produtos | catálogo paginado e fornecedores | conferir produto principal e movimentação |
| Giro/movimentações | filtros, período e exportação | selecionar produto principal |
| Vendas | 54 vendas demo distribuídas na janela de 90 dias; gráficos, taxas, comissão e entrega | pronto no DEV |
| Fluxo de caixa | períodos e lançamentos | abrir detalhes do lançamento do teste |
| Bancos | Caixa Loja Demo e Conta Banco Demo, com extratos e saldos | selecionar `Caixa Loja Demo`, não o `Caixa` vazio |
| DRE | R$ 44.165,77 de receita, R$ 27.027,43 de CMV, R$ 4.396,08 de lucro líquido | selecionar Loja Física + E-commerce + App |
| Contas a pagar | fornecedor, vencimento, editar e pagar | usar compra/NF após publicação |
| Contas a receber | registros de PDV e manuais | conferir recebível do cartão |
| Comissões | Beatriz Vendedora Demo | conferir comissão gerada pelo PDV |
| Funcionários | dois registros operacionais | conferir vínculo de Beatriz e Carlos |
| Formas de pagamento | quatro formas cadastradas e `Stone Demo` como operadora padrão | conferir taxa/cartão/banco de destino |
| Conciliação de cartões | 26 vendas de cartão pendentes e planilha Stone Demo com 9 linhas | processamento validado: 7 OK, 1 divergência de parcelas, 1 órfão e 1 venda sem NSU |

### Vazios ou incompletos hoje

| Módulo | Problema encontrado | Solução preparada |
|---|---|---|
| Pedidos de compra | preenchido no DEV | 8 cenários históricos e nenhum rascunho aberto; o novo pedido será criado ao vivo |
| Central NF-e Entrada | preenchida no DEV | 6 notas sintéticas + XML manual `901010` validado |
| Pendências de fornecedor | preenchida no DEV | 5 pendências: aberta, aguardando, tratativa, resolvida e cancelada |
| Alertas de estoque | produto `DEMO-MARGEM-VERMELHA` fica com 8 unidades e mínimo 12 | card de reposição + alertas persistentes pendente, resolvido e ignorado preparados |
| Bancos — extrato selecionado | uma conta pode aparecer sem movimentação | selecionar conta movimentada e validar lançamentos |
| DRE detalhada | a tabela `dre_detalhe_canais` faltava mesmo com o Alembic no head | migração idempotente criada e tela retestada sem erro |

### Segunda camada — auditada, mas fora do roteiro principal da Growth AgroPet

A varredura final percorreu 100 rotas. A única falha encontrada era a consulta da
conciliação de cartões sobre um campo JSON; ela foi corrigida e retestada pela
tela real. Estas telas funcionam, mas ainda têm estados vazios que não devem ser
improvisados na reunião:

- Lembretes recorrentes: nenhum lembrete pendente.
- Veterinário: sem consultas, exames, internações, medicamentos, parceiros e repasses demonstráveis.
- Banho & Tosa: agenda, pacotes, retornos, táxi-dog e relatórios sem lançamentos.
- Campanhas: sem aniversários no dia da auditoria.
- E-commerce Analytics: sem venda, reposição ou pedido pago no período.
- Bling: sem pedidos; monitor sem incidente, o que é um estado saudável.
- NF de saída: sem nota emitida.
- Imobilizado: sem bens cadastrados.
- Conciliação bancária: precisa selecionar uma conta e ter extrato OFX.
- Conciliação de cartões: agora faz parte do roteiro principal, com vendas e
  planilha sintética preparadas para confronto.
- Fechamentos de comissão: nenhum fechamento histórico.
- IA financeira: sem conversa e sem projeção gerada.
- WhatsApp: sem conversa ativa.
- LGPD: sem titular selecionado e sem solicitações.

Esses módulos entram em uma segunda carga de demonstração, depois da apresentação de loja física. Para sexta-feira, serão citados apenas se a Growth AgroPet demonstrar interesse específico; não serão usados como parte central do roteiro.

## Testes de efeitos colaterais

### Venda sem entrega e sem comissão

- Estoque diminui na quantidade vendida.
- Venda aparece como paga ou aberta conforme recebimento.
- Receita, imposto e CMV aparecem em Vendas/DRE.
- Dinheiro ou recebível aparece no banco/contas correto.
- Não cria entrega nem comissão.

### Venda no cartão

- Usa a taxa cadastrada para a forma/parcela.
- Cria conta a receber com vencimento correto.
- Reduz resultado e margem líquida.
- O alerta de margem usa o custo total, inclusive a taxa de cartão.
- A cor verde/amarela/vermelha corresponde às faixas configuradas.
- O ensaio em 6 parcelas gerou seis contas a receber com vencimentos separados.

### Venda com comissão

- Exige funcionário com regra de comissão ativa.
- Cria comissão em aberto para Beatriz.
- Mantém vínculo com venda e item.
- O valor não pode ser duplicado ao reabrir/salvar a venda.

### Venda com entrega

- Cria entrega aberta com endereço válido.
- Permite selecionar e criar rota.
- A rota pode ficar pendente, em andamento e concluída.
- Custo e taxa de entrega alimentam o painel financeiro e o resultado da venda.

### Compra e NF-e

- Pedido nasce com número único, inclusive entre empresas diferentes.
- Pedido sugere item do fornecedor principal.
- XML reconhece CNPJ, EAN, quantidade, custo e total.
- Confronto correto aprova o recebimento.
- Confronto divergente cria pendência e preserva o histórico.
- Processar a NF atualiza estoque, custo, contas a pagar e vínculo fornecedor/produto.

### Conciliação de cartões

- A lista inicial mostra somente pagamentos de débito/crédito/cartão.
- A operadora `Stone Demo` exibe 9 registros pendentes para confronto.
- O processamento encontra 7 correspondências corretas, 1 divergência de
  parcelas e 1 NSU existente somente na planilha.
- Uma venda de cartão sem NSU permanece visível como pendência real do PDV.
- Dinheiro e Pix não aparecem como falsas pendências de cartão.

## Melhorias de interface deste pacote

- Substituição dos alertas do Chrome nos fluxos críticos de PDV, compras, NF-e e entregas por diálogo CorePet.
- Ponte global de compatibilidade: avisos nativos remanescentes passam a aparecer como toast CorePet; confirmações destrutivas continuam sendo migradas explicitamente para o diálogo seguro.
- Sucesso de venda exibido como notificação discreta, sem travar a tela.
- Confirmações com título, explicação e botões consistentes.
- Sidebar redimensionável entre 232 e 440 px.
- Nome completo do item mostrado ao passar o mouse quando estiver cortado ou recolhido.
- Correção do número de pedido para respeitar a unicidade global do banco.

## Checklist de 30 minutos antes da reunião

- Entrar como `corepeterp@gmail.com` e confirmar tenant Demo.
- Deixar Dashboard, PDV, Pedidos, NF-e, Pendências, Entregas, Vendas e DRE em favoritos.
- Conferir que não há modal, rascunho ou venda incompleta aberta.
- Conferir cliente, Beatriz, Carlos, fornecedor e produto principal.
- Separar os dois XMLs em uma pasta fácil de abrir.
- Na DRE, ativar `Loja Física`, `E-commerce` e `App` antes de comentar os cards.
- Em Bancos, selecionar `Caixa Loja Demo` para mostrar o extrato preenchido.
- Executar uma venda pequena de ensaio e conferir seus efeitos.
- Atualizar Dashboard, Vendas, Fluxo, DRE e Entregas.
- Deixar o roteiro aberto em uma segunda tela.
- Não excluir cenários durante a apresentação; apenas navegar e filtrar.
