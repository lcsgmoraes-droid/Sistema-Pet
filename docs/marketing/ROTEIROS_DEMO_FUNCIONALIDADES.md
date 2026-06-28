# Roteiros de Demos por Funcionalidade - Sistema Pet

Uso: orientar a gravacao de videos mostrando a tela real do sistema. Estes
roteiros servem para treinamento, onboarding, venda consultiva e conteudo de
produto.

## Preparacao da base demo

Use dados ficticios consistentes:

- Cliente: Maria Oliveira.
- Pet: Thor.
- Produto: Racao Adulto 10kg.
- Servico: Banho medio completo.
- Veterinario: Dra. Ana Martins.
- Fornecedor: Distribuidora Pet Brasil.
- Forma de pagamento: PIX e Cartao de credito.
- Banco: Conta Banco Demo.
- Categoria financeira: Venda de produtos.

Antes de gravar:

- Fechar abas e notificacoes.
- Usar tenant/base de demonstracao.
- Conferir que nao ha dados reais na tela.
- Abrir a tela inicial do roteiro.
- Deixar zoom do navegador entre 90% e 100%.
- Gravar o mouse com movimentos calmos.

## Demo 1 - Configuracao inicial

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar que o usuario novo tem uma ordem segura para configurar o sistema |
| Duracao | 60s |
| Telas | `/ajuda`, Introducao Guiada, Central de Ajuda |

Sequencia:

1. Abrir a Introducao Guiada.
2. Mostrar o resumo das secoes.
3. Dar zoom nas etapas obrigatorias.
4. Abrir um item de financeiro.
5. Voltar e mostrar que existem itens condicionais por modulo.
6. Encerrar na Central de Ajuda.

Narracao:

```text
Para comecar bem, o Sistema Pet organiza a configuracao inicial em etapas.
Primeiro vem empresa e acesso. Depois financeiro obrigatorio, impostos, cadastros base e operacao.
Se o negocio usa banho e tosa, veterinario, compras ou ecommerce, o guia tambem mostra o que configurar.
Assim o usuario novo nao precisa adivinhar a ordem certa.
```

Checklist:

- Mostrar claramente os badges obrigatorio, recomendado e condicional.
- Evitar passar rapido demais pelas etapas.
- Encerrar com CTA para seguir o guia.

## Demo 2 - Financeiro antes da primeira venda

| Campo | Conteudo |
|---|---|
| Objetivo | Explicar por que bancos, formas de pagamento e categorias precisam existir antes da venda |
| Duracao | 75s |
| Telas | `/cadastros/financeiro/formas-pagamento`, bancos, categorias, `/pdv`, contas a receber |

Sequencia:

1. Mostrar formas de pagamento cadastradas.
2. Mostrar conta bancaria ou banco demo.
3. Mostrar categoria financeira.
4. Fazer uma venda simples no PDV.
5. Mostrar reflexo em contas a receber.

Narracao:

```text
Antes de vender, o financeiro precisa estar preparado.
As formas de pagamento dizem como o cliente paga.
A conta bancaria ajuda a organizar para onde o dinheiro vai.
As categorias ajudam a classificar o resultado.
Quando a venda acontece no PDV, o recebimento ja nasce com mais contexto para conferencia.
```

Checklist:

- Usar venda pequena e simples.
- Mostrar PIX e Cartao como exemplos.
- Nao usar valores reais.

## Demo 3 - Produto, PDV e estoque

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar a ligacao entre cadastro de produto, venda e estoque |
| Duracao | 60s |
| Telas | `/produtos`, `/pdv`, alertas ou movimentacoes de estoque |

Sequencia:

1. Abrir produto ficticio.
2. Mostrar preco, categoria e estoque.
3. Ir para o PDV.
4. Inserir o produto na venda.
5. Finalizar com forma de pagamento demo.
6. Voltar ao produto ou estoque para mostrar conferencia.

Narracao:

```text
No Sistema Pet, o produto cadastrado alimenta a venda.
Ao vender no PDV, a operacao deixa rastro para conferencia de estoque e financeiro.
Isso ajuda a equipe a entender o que saiu, quando saiu e por qual venda.
```

Checklist:

- Mostrar produto antes e depois da venda quando possivel.
- Evitar carrinho com muitos itens.
- Usar apenas um produto para ficar didatico.

## Demo 4 - Compras e entrada XML

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar a rotina de conferencia de compras, custo e estoque |
| Duracao | 75s |
| Telas | `/compras/entrada-xml`, pedidos de compra, produtos |

Sequencia:

1. Abrir entrada XML.
2. Selecionar nota fiscal demo.
3. Mostrar itens importados.
4. Conferir produto, fornecedor e custo.
5. Mostrar atualizacao/conferencia de estoque.

Narracao:

```text
Quando a nota chega, a operacao precisa conferir produto, custo, fornecedor e estoque.
A entrada XML ajuda a reduzir digitacao manual e centraliza a conferencia.
O objetivo e deixar a compra pronta para refletir corretamente na operacao.
```

Checklist:

- Usar XML ficticio ou ambiente de demonstracao.
- Nao expor CNPJ real de fornecedor.
- Explicar que a conferencia continua sendo importante.

## Demo 5 - Banho e tosa

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar servicos, agenda e fila do dia |
| Duracao | 60s |
| Telas | `/banho-tosa/servicos`, `/banho-tosa/agenda`, `/banho-tosa/fila` |

Sequencia:

1. Mostrar servico cadastrado.
2. Abrir agenda.
3. Criar ou abrir agendamento demo para Thor.
4. Mostrar fila do dia.
5. Encerrar com a rotina da equipe.

Narracao:

```text
Banho e tosa precisa de agenda clara e fila facil de acompanhar.
No Sistema Pet, os servicos cadastrados ajudam a padronizar o atendimento.
A agenda mostra os horarios e a fila ajuda a equipe a enxergar o que esta acontecendo no dia.
```

Checklist:

- Mostrar nome do pet ficticio.
- Evitar muitos agendamentos na tela.
- Se houver status, mostrar uma troca simples de etapa.

## Demo 6 - Veterinario

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar agenda, atendimento e historico do pet |
| Duracao | 75s |
| Telas | `/veterinario/agenda`, consultas, pet, catalogos |

Sequencia:

1. Abrir agenda veterinaria.
2. Selecionar atendimento demo.
3. Mostrar tutor e pet.
4. Mostrar campo de consulta/historico.
5. Mostrar catalogos quando fizer sentido.

Narracao:

```text
No atendimento veterinario, contexto importa.
O Sistema Pet conecta agenda, tutor, pet e historico em uma rotina mais organizada.
Assim a equipe consegue consultar informacoes importantes sem depender de papel espalhado.
```

Checklist:

- Usar dados ficticios.
- Nao mostrar informacao clinica real.
- Evitar termos medicos sensiveis ou diagnosticos reais.

## Demo 7 - Ecommerce e app

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar configuracao de loja, catalogo e pedidos online |
| Duracao | 60s |
| Telas | `/ecommerce/configuracoes`, ecommerce, pedidos |

Sequencia:

1. Abrir configuracoes do ecommerce.
2. Mostrar catalogo/produtos habilitados.
3. Mostrar tela da loja ou preview.
4. Abrir pedidos online.
5. Encerrar mostrando que a operacao fica conectada.

Narracao:

```text
O ecommerce ajuda a loja a vender alem do balcao.
No Sistema Pet, a configuracao, o catalogo e os pedidos online fazem parte da mesma operacao.
Isso facilita acompanhar o canal digital junto com a rotina da loja.
```

Checklist:

- Mostrar apenas loja demo.
- Evitar prometer venda garantida.
- Deixar claro que ecommerce depende da configuracao do tenant.

## Demo 8 - Relatorios gerenciais

| Campo | Conteudo |
|---|---|
| Objetivo | Mostrar que o gestor consegue acompanhar indicadores |
| Duracao | 60s |
| Telas | dashboard gerencial, relatorios de venda, DRE |

Sequencia:

1. Abrir dashboard ou relatorio.
2. Mostrar filtros de periodo.
3. Mostrar indicadores principais.
4. Abrir detalhe quando houver.
5. Encerrar com decisao pratica: conferir vendas, estoque ou financeiro.

Narracao:

```text
Gestao precisa de conferencia.
Com relatorios e dashboards, o Sistema Pet ajuda o gestor a acompanhar vendas, financeiro e resultado.
O objetivo e transformar a rotina do dia a dia em informacao mais facil de analisar.
```

Checklist:

- Usar periodo curto e dados demo.
- Dar zoom em um indicador por vez.
- Nao deixar tabela pequena demais no video vertical.

## Padrao de encerramento

Use uma frase final curta:

- "Sistema Pet: gestao mais organizada para operacao pet."
- "Conheca o Sistema Pet e veja a rotina funcionando."
- "Comece pela configuracao guiada e evolua modulo por modulo."
- "Venda, estoque e financeiro no mesmo fluxo."
