# App Funcionario Contagem para Devolucao Design

## Contexto

Lucas precisa contar produtos fisicos que serao devolvidos para fornecedor. Em
alguns casos esses produtos ja estao zerados no estoque do ERP, entao o fluxo
atual de balanco por camera nao serve: ele altera estoque de verdade. A nova
funcionalidade deve permitir bipar produtos, informar a quantidade conferida,
salvar a contagem no ERP e gerar PDF/Excel para uso operacional, sem movimentar
estoque, sem sincronizar Bling e sem criar venda, compra ou financeiro.

O app do funcionario ja tem area operacional, leitor por camera, busca de
produtos do ERP e tela de balanco. O pedido de compra web ja tem um padrao de
documento com checkboxes de colunas para PDF/Excel. A nova contagem deve
reaproveitar esses conceitos.

## Decisoes Confirmadas

- A funcionalidade sera uma nova opcao no app do funcionario.
- O nome funcional pode ser `Contagem / Devolucao`.
- A contagem sera salva no ERP para consulta e reexportacao posterior.
- Fornecedor sera opcional no cabecalho da contagem.
- O fluxo nao altera estoque.
- O fluxo nao cria `EstoqueMovimentacao`.
- O fluxo nao sincroniza estoque com Bling.
- O funcionario podera escolher se o documento mostra valores.
- `Mostrar custo` inclui custo unitario e total de custo.
- `Mostrar venda` inclui preco de venda unitario e total de venda.
- Se os checkboxes de valores ficarem desmarcados, o documento sai somente
  operacional.

## Objetivo

Criar uma contagem salva no app mobile do funcionario para listas de devolucao
ou conferencia avulsa. O funcionario escaneia ou busca produtos do ERP, informa
quantidade contada, escolhe fornecedor opcional, salva a contagem e gera PDF ou
Excel com o conteudo selecionado por checkboxes.

## Experiencia do Usuario

1. Funcionario entra no app e acessa a area operacional.
2. Na tela inicial do funcionario, escolhe `Contagem / Devolucao`.
3. Informa um titulo opcional para a contagem.
4. Escolhe fornecedor opcional.
5. Bipa um produto ou busca manualmente por nome, codigo, SKU ou codigo de
   barras.
6. O app mostra o produto encontrado com dados basicos.
7. Funcionario informa a quantidade contada.
8. Se bipar o mesmo produto novamente, o app permite somar quantidade ao item
   existente ou editar a quantidade.
9. Funcionario pode remover item, alterar quantidade e adicionar observacao.
10. Ao salvar, o backend grava a contagem e seus itens.
11. A tela mostra a contagem salva com resumo de itens e quantidades.
12. Funcionario escolhe PDF ou Excel.
13. Antes de gerar, escolhe por checkboxes o que entra no documento.
14. O app baixa ou compartilha o arquivo gerado pelo backend.

## Arquitetura

### Backend

Criar endpoints operacionais mobile sob `/app/funcionario/contagens`, usando o
mesmo token mobile e tenant atual.

- `GET /app/funcionario/contagens`
  - Lista contagens recentes do funcionario/tenant.
  - Permite consultar historico depois.

- `POST /app/funcionario/contagens`
  - Cria uma contagem em rascunho ou salva uma contagem finalizada.
  - Payload: `titulo`, `fornecedor_id`, `observacao`, `itens`.
  - Cada item contem `produto_id`, `quantidade`, `observacao`.
  - Busca produtos por tenant para capturar snapshots de nome, codigo, codigo
    de barras, unidade, preco de custo e preco de venda.
  - Nao altera `Produto.estoque_atual`.
  - Nao cria `EstoqueMovimentacao`.

- `GET /app/funcionario/contagens/{contagem_id}`
  - Retorna cabecalho, fornecedor, funcionario e itens da contagem.

- `GET /app/funcionario/contagens/{contagem_id}/export/pdf`
  - Gera PDF da contagem.
  - Query param `colunas` ou flags equivalentes controlam o conteudo.

- `GET /app/funcionario/contagens/{contagem_id}/export/excel`
  - Gera Excel da contagem.
  - Usa as mesmas colunas selecionadas do PDF.

A busca de produtos deve reaproveitar a busca operacional de estoque do
funcionario, porque ela consulta o cadastro ERP e nao o catalogo publico do app.

### Dados

Adicionar modelos persistentes tenant-safe:

- `FuncionarioContagem`
  - `id`
  - `tenant_id`
  - `funcionario_id`
  - `user_id`
  - `fornecedor_id` opcional
  - `fornecedor_nome_snapshot` opcional
  - `titulo`
  - `observacao`
  - `status`
  - `created_at`
  - `updated_at`

- `FuncionarioContagemItem`
  - `id`
  - `tenant_id`
  - `contagem_id`
  - `produto_id`
  - `produto_nome_snapshot`
  - `produto_codigo_snapshot`
  - `codigo_barras_snapshot`
  - `unidade_snapshot`
  - `quantidade`
  - `preco_custo_snapshot`
  - `preco_venda_snapshot`
  - `observacao`

Snapshots sao importantes porque o documento precisa representar o que foi
contado naquele momento, mesmo se o cadastro do produto mudar depois.

### App Mobile

Adicionar uma nova tela no navegador de funcionario:

- `FuncionarioContagemScreen`
  - Scanner com `expo-camera`.
  - Busca manual por produto.
  - Cabecalho com titulo, fornecedor opcional e observacao.
  - Lista de itens contados.
  - Campo de quantidade por item.
  - Botao salvar contagem.
  - Botao gerar PDF.
  - Botao gerar Excel.
  - Painel de checkboxes para conteudo do documento.

Criar service dedicado ou ampliar o service operacional existente:

- `buscarProdutosFuncionario`
- `buscarProdutoFuncionarioPorBarcode`
- `salvarContagemFuncionario`
- `obterContagemFuncionario`
- `exportarContagemFuncionario`

Se o app precisar salvar/compartilhar arquivo no aparelho, declarar a
dependencia Expo adequada explicitamente no `package.json`, em vez de depender
de pacote interno transitorio.

## Colunas do Documento

Colunas basicas:

- Codigo / SKU
- Codigo de barras
- Produto
- Unidade
- Quantidade contada
- Observacao do item

Opcoes de valores:

- `Mostrar custo`
  - Custo unitario
  - Total de custo (`quantidade * custo unitario`)

- `Mostrar venda`
  - Preco de venda unitario
  - Total de venda (`quantidade * preco de venda unitario`)

O total correspondente entra automaticamente quando o checkbox de valor for
marcado. Nao havera checkbox separado para total de custo ou total de venda no
MVP.

## Regras de Produto

- Produto ativo do ERP pode ser contado mesmo se nao estiver anunciado no app.
- Produto com estoque zero pode ser contado.
- Produto sem custo ou sem preco de venda deve aparecer no documento com valor
  zero ou vazio, conforme o padrao do exportador.
- Produto nao encontrado deve manter o scanner aberto para nova tentativa.
- Produto duplicado na mesma contagem deve atualizar o item existente, nao criar
  linha duplicada silenciosa.

## Regras de Fornecedor

- Fornecedor e opcional.
- Quando informado, o fornecedor aparece no cabecalho da contagem e no arquivo.
- Quando nao informado, o documento usa texto neutro, por exemplo `Fornecedor
  nao informado`.
- A busca de fornecedor deve consultar pessoas do ERP com `tipo_cadastro =
  fornecedor`.

## Tratamento de Erros

- Sem itens: impedir salvar.
- Quantidade menor ou igual a zero: impedir salvar aquele item.
- Produto nao encontrado: mostrar mensagem simples e permitir nova leitura.
- Sem permissao de funcionario: retornar 403 no backend e mostrar aviso no app.
- Contagem de outro tenant: retornar 404.
- Falha ao exportar: manter contagem salva e permitir tentar novamente.

## Testes

### Backend

- Contrato dos endpoints mobile de contagem.
- Criar contagem salva sem alterar `Produto.estoque_atual`.
- Criar contagem salva sem criar `EstoqueMovimentacao`.
- Produto com estoque zero pode entrar na contagem.
- Fornecedor opcional e aceito.
- Export PDF aceita `mostrar_custo` e inclui custo unitario e total de custo.
- Export PDF sem `mostrar_custo` nao inclui custo.
- Export Excel segue as mesmas colunas do PDF.
- Tenant diferente nao acessa contagem.

### App Mobile

- Typecheck deve passar.
- Service deve montar rotas `/app/funcionario/contagens`.
- Tela deve registrar scanner, busca manual, quantidade e lista de itens.
- Checkboxes `Mostrar custo` e `Mostrar venda` devem controlar as flags de
  exportacao.
- Navegador do funcionario deve exibir a nova opcao na home.

## Fora do Escopo

- Criar nota fiscal de devolucao.
- Movimentar estoque automaticamente.
- Integrar Bling.
- Enviar arquivo por e-mail direto do app.
- Fluxo offline com sincronizacao posterior.
- Aprovar ou auditar divergencia de estoque.
