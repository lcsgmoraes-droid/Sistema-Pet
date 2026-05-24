# App mobile funcionario - PDV rapido

## Objetivo

Criar no app mobile do funcionario um fluxo simples para passar venda no celular, usando o ERP como fonte da verdade e mantendo os mesmos efeitos do PDV web: venda, baixa de estoque, financeiro, caixa, comissoes e DRE.

O app nao deve virar modulo de gestao de caixa. Abertura, fechamento, sangria, suprimento, conferencia de caixa e rotinas administrativas continuam no ERP web.

## Escopo do MVP

- Tela inicial do funcionario com atalhos para `Balanco de Estoque` e `PDV Rapido`.
- PDV mobile com leitura por camera e busca manual de produtos do ERP.
- Carrinho com ajuste de quantidade, remocao de item, subtotal e total.
- Selecao opcional de cliente, buscando a base do ERP.
- Pagamento simples por dinheiro, Pix, credito ou debito.
- Calculo de troco para pagamento em dinheiro.
- Registro da venda usando o funcionario logado como vendedor/comissionado padrao.
- Bloqueio claro quando nao houver caixa aberto para o usuario/loja atual.

## Fora do MVP

- Abrir caixa pelo celular.
- Fechar caixa pelo celular.
- Sangria, suprimento ou conferencia de caixa.
- NFC-e emitida pelo app mobile.
- Desconto com autorizacao.
- Devolucao.
- Entrega.

## Arquitetura

O app mobile deve chamar endpoints especificos de funcionario em `/app/funcionario/pdv/...`. Esses endpoints funcionam como uma camada simples para o celular, mas delegam a regra principal para os servicos atuais do ERP.

O backend nao deve duplicar regras de venda no mobile. A criacao/finalizacao precisa reaproveitar o fluxo oficial usado pelo PDV web, especialmente a parte que baixa estoque, cria financeiro, movimenta caixa e gera comissoes.

## Fluxo da tela

1. O funcionario entra no app e escolhe `PDV Rapido`.
2. O app consulta se existe caixa aberto.
3. Se nao houver caixa aberto, mostra aviso e bloqueia finalizar venda.
4. O funcionario escaneia ou busca produtos no ERP.
5. Cada produto entra no carrinho com preco atual do ERP.
6. O funcionario pode ajustar quantidade ou remover item.
7. O funcionario pode selecionar cliente, mas isso nao e obrigatorio.
8. O funcionario escolhe forma de pagamento.
9. O app confirma a venda e envia para o backend.
10. O backend registra a venda pelo fluxo oficial e devolve numero da venda, total e status.

## Regras de produto

A busca do PDV mobile deve consultar produtos vendaveis do ERP, nao o catalogo do app/e-commerce. Produto sem estoque, inativo, pai ou com restricao de venda deve seguir a mesma regra do PDV web.

Ao bipar o mesmo produto mais de uma vez, o app incrementa a quantidade no carrinho.

## Regras de caixa

O app apenas usa caixa aberto. Se nao houver caixa aberto, o funcionario deve abrir pelo ERP web.

Essa decisao evita colocar operacoes sensiveis de caixa no celular e deixa o app focado em venda rapida.

## Regras de comissao

O funcionario logado sera enviado como `funcionario_id` da venda. Assim, se houver regra de comissao configurada para ele/parceiro, o fluxo atual de comissoes do ERP deve gerar os lancamentos normalmente.

## Pagamentos

O MVP aceita:

- Dinheiro, com valor recebido e troco.
- Pix, marcado como recebido fora do app.
- Credito, marcado como passado fora do app.
- Debito, marcado como passado fora do app.

O app nao integra maquininha nem captura Pix automaticamente nesta etapa.

## Erros e mensagens

- Produto nao encontrado: permitir escanear novamente ou buscar manualmente.
- Caixa fechado: avisar que a venda so pode ser finalizada com caixa aberto no ERP.
- Estoque insuficiente: mostrar o produto e a quantidade disponivel.
- Falha ao finalizar: mostrar mensagem do ERP e nao limpar o carrinho automaticamente.

## Validacao

Antes de entregar a implementacao:

- Testar contratos dos endpoints mobile de PDV.
- Rodar typecheck do app mobile.
- Verificar que a venda mobile passa pelo mesmo servico de venda do ERP.
- Verificar que a venda finalizada baixa estoque.
- Verificar que venda com funcionario configurado gera comissao.
- Verificar que sem caixa aberto a finalizacao e bloqueada com mensagem clara.
