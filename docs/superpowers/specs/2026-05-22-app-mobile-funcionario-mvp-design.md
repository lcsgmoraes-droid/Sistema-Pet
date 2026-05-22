# App mobile funcionario - MVP base

Data: 2026-05-22

## Contexto

O app mobile ja possui fluxos separados para cliente, entregador e veterinario. O
roadmap do vendedor/funcionario pede um perfil proprio para operacao de loja,
com consulta por camera, busca manual e montagem de um carrinho de PDV
simplificado.

O primeiro ciclo deve criar a base segura para esse fluxo sem finalizar vendas
ainda. A finalizacao real precisa reaproveitar regras do PDV web para estoque,
preco, beneficios, cliente, financeiro e comissoes.

## Escopo aprovado

- Identificar usuario com perfil operacional `funcionario` no login mobile.
- Direcionar o funcionario para um navegador proprio, separado de cliente,
  entregador e veterinario.
- Permitir consulta de produto por codigo de barras usando a camera.
- Permitir busca manual por nome, codigo, SKU ou codigo de barras.
- Mostrar produto, preco, estoque e avisos basicos relevantes.
- Permitir montar um carrinho PDV local com adicionar, ajustar quantidade e
  remover itens.
- Nao baixar estoque e nao registrar venda neste ciclo.

## Fora deste ciclo

- Selecionar cliente da venda.
- Aplicar beneficios, saldo, historico e alertas do cliente.
- Finalizar venda com PIX, cartao externo ou dinheiro.
- Gerar recibo/comprovante.
- Integrar baixa de estoque, financeiro e comissoes.
- Rotinas de caixa, NFC-e e autorizacao de desconto.

## Arquitetura

### Backend

O endpoint de perfil do app deve retornar os campos operacionais do funcionario:

- `is_funcionario`
- `funcionario_id`
- `perfil_operacional: "funcionario"`

A prioridade de perfil deve continuar protegendo fluxos especificos:

1. Veterinario
2. Entregador
3. Funcionario
4. Cliente

Essa ordem evita que alguem que tambem esteja cadastrado como funcionario perca
o fluxo operacional mais especifico, como veterinario ou entregador.

### App mobile

O `AppNavigator` deve reconhecer `funcionario` e abrir um
`FuncionarioNavigator`.

O novo navegador deve ter telas focadas em operacao:

- Consulta/PDV: busca manual, acesso ao scanner e lista de resultados.
- Scanner: leitura de codigo de barras com a mesma base tecnica ja usada no app.
- Carrinho PDV: itens locais, quantidade, subtotal e limpeza do carrinho.

O carrinho do funcionario deve ser separado do carrinho de e-commerce do
cliente. Neste ciclo ele fica local no app para evitar misturar pedidos online
com uma venda de balcao ainda nao finalizada.

## Fluxo de dados

1. Usuario seleciona a loja e faz login.
2. Backend retorna o perfil operacional.
3. App salva/cacheia o perfil e escolhe o navegador correto.
4. Funcionario busca ou escaneia produto.
5. App consulta endpoints ja existentes de produto quando possivel.
6. Funcionario adiciona itens ao carrinho local.
7. Estoque permanece inalterado ate uma futura finalizacao de venda.

## Estados e erros

- Sem permissao de camera: mostrar pedido de permissao e permitir voltar.
- Produto nao encontrado: avisar e permitir nova leitura/busca.
- Produto sem estoque: mostrar aviso e bloquear adicao ao carrinho quando o
  estoque conhecido for zero ou negativo.
- Erro de API: exibir mensagem amigavel e manter a tela recuperavel.
- Perfil nao identificado como funcionario: manter fallback para o fluxo de
  cliente.

## Testes e validacao

- Teste/contrato backend garantindo retorno de `is_funcionario` e
  `perfil_operacional`.
- Teste/contrato ou checagem de fonte garantindo que o app roteia funcionario
  para `FuncionarioNavigator`.
- Validar que o tipo `EcommerceUser` aceita `funcionario`.
- Rodar typecheck do app mobile.
- Rodar testes backend relacionados ao app mobile/perfil.

## Criterio de pronto

- Um funcionario logado nao cai mais no app de cliente.
- Ele consegue abrir a area propria do funcionario.
- Ele consegue buscar ou escanear produtos e montar um carrinho PDV local.
- O ciclo nao altera estoque nem cria venda antes da etapa de finalizacao.
