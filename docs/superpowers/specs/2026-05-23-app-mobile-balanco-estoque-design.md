# App Mobile Balanco de Estoque por Camera Design

## Contexto

Lucas quer priorizar, antes do PDV mobile, um fluxo operacional para funcionario fazer balanco de estoque usando a camera como leitor de codigo de barras. O app mobile atual ja tem autenticacao por tenant, scanner com `expo-camera` e navegadores separados para perfis operacionais como entregador e veterinario. O fluxo novo deve seguir esse padrao, mas consultar o cadastro ERP, nao o catalogo publico do app/e-commerce.

## Decisoes Confirmadas

- A fonte da verdade e o ERP.
- A busca do produto deve consultar produtos do ERP por codigo de barras, SKU, codigo interno ou nome.
- A quantidade digitada no app representa o saldo final contado no balanco.
- O backend calcula a diferenca entre saldo atual e saldo contado.
- Se o saldo contado for maior, registra entrada de estoque da diferenca.
- Se o saldo contado for menor, registra saida de estoque da diferenca.
- Lote e validade sao opcionais e entram apenas quando houver entrada positiva.
- O PDV mobile fica para uma etapa posterior.

## Objetivo

Criar uma area de funcionario no app mobile com uma tela de "Balanco" em que o funcionario escaneia ou busca produto do ERP, confere dados basicos, informa o saldo final contado, lote e validade, e salva um ajuste de estoque com motivo `balanco`.

## Experiencia do Usuario

1. Funcionario abre o app e faz login.
2. O app identifica perfil operacional de funcionario e entra no navegador operacional.
3. A tela inicial mostra a opcao de balanco por camera.
4. Ao escanear um codigo, o app busca o produto no ERP.
5. O app mostra nome, codigo/SKU, preco de venda, custo, unidade, estoque atual e avisos de produto pai, kit virtual ou produto inativo.
6. Funcionario informa saldo final contado.
7. Opcionalmente informa lote e validade.
8. Ao salvar, o app mostra a diferenca que sera lancada.
9. O backend registra a movimentacao de entrada ou saida e devolve o estoque novo.
10. A tela lista os lancamentos feitos na sessao para conferencia rapida.

## Arquitetura

### Backend

Adicionar endpoints operacionais mobile sob `/app/funcionario/estoque`, usando o mesmo token mobile e tenant atual.

- `GET /app/funcionario/estoque/produtos/buscar`
  - Parametros: `q`.
  - Busca em produtos do ERP, respeitando tenant.
  - Procura por nome, codigo, sku, codigo de barras, GTIN e codigos alternativos.
  - Nao exige `anunciar_app` nem `is_sellable`, pois e uso interno.
  - Retorna lista curta para busca manual.

- `GET /app/funcionario/estoque/produtos/barcode/{barcode}`
  - Busca produto ERP por codigo de barras/codigo/SKU.
  - Retorna 404 se nao encontrar.

- `POST /app/funcionario/estoque/balanco`
  - Payload: `produto_id`, `saldo_final`, `numero_lote`, `data_validade`, `observacao`.
  - Verifica se usuario mobile e funcionario operacional.
  - Busca produto por tenant.
  - Bloqueia produto pai.
  - Bloqueia kit virtual para movimentacao direta, mantendo a regra atual do ERP.
  - Calcula `diferenca = saldo_final - estoque_atual`.
  - Se diferenca positiva, chama a mesma logica de entrada atual com motivo `balanco`.
  - Se diferenca negativa, chama a mesma logica de saida atual com motivo `balanco`.
  - Se diferenca zero, nao cria movimentacao e retorna mensagem de sem alteracao.
  - Marca observacao com origem `App funcionario - balanco por camera`.

### App Mobile

Adicionar um navegador de funcionario, seguindo o padrao de `VeterinarioNavigator` e `EntregadorNavigator`.

- Extender `EcommerceUser.perfil_operacional` para incluir `funcionario`.
- Login/perfil devem manter cache operacional tambem para funcionario.
- `AppNavigator` deve rotear funcionario para o novo navegador.
- Tela principal: `FuncionarioBalancoScreen`.
- Reaproveitar `expo-camera` para scanner, mas chamar o endpoint operacional ERP.
- Criar service dedicado, por exemplo `funcionarioEstoque.service.ts`, para nao misturar com `shop.service.ts`.
- Criar tipos dedicados para produto operacional e lancamento de balanco.

## Regras de Produto

- Produto ativo do ERP deve aparecer mesmo que nao esteja anunciado no app.
- Produto pai com variacoes nao pode receber estoque direto.
- Kit virtual nao pode receber ajuste direto; o saldo vem dos componentes.
- Produtos inativos podem ser encontrados somente se o backend decidir retornar com aviso, mas o MVP deve preferir ativos para reduzir erro operacional.
- Entrada positiva com lote ou validade cria ou atualiza lote como o fluxo web ja faz.
- Saida negativa usa FIFO dos lotes existentes, como o fluxo web ja faz.

## Tratamento de Erros

- Codigo nao encontrado: mostrar mensagem e permitir escanear novamente.
- Produto pai: mostrar aviso explicando para movimentar a variacao.
- Kit virtual: mostrar aviso explicando que deve ajustar os componentes.
- Saldo final invalido: impedir salvar.
- Saida maior que estoque: nao deve ocorrer se o saldo final for menor ou igual ao atual; ainda assim o backend deve proteger.
- Falha de rede: manter formulario preenchido e permitir tentar novamente.

## Testes

### Backend

- Contrato de perfil: funcionario ativo retorna `perfil_operacional = funcionario`.
- Busca operacional nao deve exigir `anunciar_app`.
- Barcode operacional deve encontrar produto ERP por codigo/SKU/GTIN.
- Balanco com saldo final maior cria entrada com motivo `balanco`.
- Balanco com saldo final menor cria saida com motivo `balanco`.
- Balanco com saldo igual nao cria movimentacao.
- Produto pai e kit virtual retornam erro claro.

### App Mobile

- Typecheck deve passar.
- Service deve montar URLs operacionais corretas.
- Tela deve aceitar scanner, busca manual e formulario de saldo final.
- Navegacao deve enviar funcionario para area operacional.

## Fora do Escopo

- PDV mobile.
- NFC-e no app.
- Desconto/autorizacao.
- Rotina completa de caixa.
- Entrada de compra/nota fiscal por app.
- Contagem offline com sincronizacao posterior.
