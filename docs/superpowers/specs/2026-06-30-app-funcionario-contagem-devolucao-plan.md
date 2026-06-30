# Plano: contagem mobile para devolucao

## Objetivo

Criar no app do funcionario uma funcao de contagem avulsa para devolucao/controle, separada do balanco de estoque. A contagem deve permitir bipar ou buscar produtos, informar quantidade contada, salvar historico no ERP e exportar PDF/Excel com colunas opcionais de custo e venda.

## Escopo aprovado

- Nova tela no app do funcionario chamada "Contagem".
- A contagem nao altera estoque, nao cria movimentacao e nao sincroniza Bling.
- Produto pode estar com estoque zero e ainda assim entrar na contagem.
- Fornecedor opcional no cabecalho.
- Itens com quantidade e observacao opcional.
- PDF/Excel com checkboxes de exportacao.
- Quando "Mostrar custo" estiver marcado, entram custo unitario e total de custo.
- Quando "Mostrar venda" estiver marcado, entram venda unitaria e total de venda.
- Salvar a contagem para historico e reexportacao.

## Passos de implementacao

1. Criar testes de contrato cobrindo as rotas novas, a tela mobile e a garantia de que a contagem nao movimenta estoque.
2. Criar modelos e migration para `funcionario_contagens` e `funcionario_contagem_itens`.
3. Criar rotas mobile de funcionario para buscar fornecedor, salvar/listar/abrir contagem e exportar PDF/Excel.
4. Registrar as novas rotas no roteador mobile.
5. Criar servico mobile para salvar contagem e baixar/compartilhar PDF/Excel.
6. Criar tela `FuncionarioContagemScreen` com leitor de codigo de barras, busca manual, quantidade, fornecedor opcional, lista de itens, checkboxes e botoes de exportacao.
7. Adicionar a entrada "Contagem" na home do funcionario e registrar a rota na navegacao.
8. Rodar testes focados do backend e typecheck do app mobile.
9. Fechar a branch pelo script oficial do repositorio.

## Validacoes esperadas

- `pytest` focado nos contratos da contagem.
- `npm --prefix app-mobile run typecheck`.
- `git diff --check`.
- Conferencia de `git status --short` antes do commit.
