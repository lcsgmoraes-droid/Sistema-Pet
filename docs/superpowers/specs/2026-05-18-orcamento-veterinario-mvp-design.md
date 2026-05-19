# Orcamento Veterinario MVP Design

## Objetivo

Criar uma primeira versao do orcamento veterinario para consulta e internacao, permitindo ao veterinario estimar custo, preco de venda e margem antes de executar o atendimento, sem baixar estoque ate que cada item seja realmente utilizado.

## Escopo do MVP

- O veterinario pode criar um orcamento vinculado a uma consulta, internacao, cliente e pet.
- O orcamento aceita itens de catalogo de procedimentos, itens livres e diarias de internacao.
- Cada item guarda quantidade, custo unitario estimado, preco unitario sugerido, preco unitario cobrado, custo total, venda total e margem.
- Ao selecionar um procedimento do catalogo, o sistema usa `valor_padrao` como preco sugerido e os insumos cadastrados no procedimento para calcular o custo estimado.
- Ao selecionar um produto como insumo manual, o sistema usa `preco_custo` e `preco_venda` do cadastro do produto para sugerir custo e venda.
- A previsao de internacao usa quantidade de dias prevista multiplicada pela diaria ou pelo procedimento escolhido para diaria.
- Salvar orcamento nao cria movimentacao de estoque, conta a receber ou venda.
- Os lancamentos reais seguem pelos fluxos existentes de consulta e internacao, que fazem baixa de estoque item a item quando o procedimento/insumo e concluido.

## Fora do MVP Inicial

- Converter orcamento automaticamente em venda consolidada.
- Agrupar venda final como apenas "consulta" ou "internacao" com extrato detalhado.
- Exportacao final em PDF/XLSX com seletor completo de colunas. A API ja deve devolver dados estruturados para essa etapa seguinte.
- Assinatura ou aceite digital do tutor.

## Modelo de Dados

Adicionar duas tabelas multi-tenant:

- `vet_orcamentos`: cabecalho do orcamento, com status, vinculos de consulta/internacao, cliente, pet, veterinario, dias previstos e totais.
- `vet_orcamento_itens`: itens estimados, com origem (`catalogo`, `produto`, `diaria`, `manual`), referencias opcionais, quantidades e totais financeiros.

Os totais do cabecalho sao recalculados no backend a partir dos itens salvos. Isso evita divergencia entre frontend e backend.

## API

Adicionar rotas em `/vet/orcamentos`:

- `GET /vet/orcamentos`: lista orcamentos por consulta, internacao, pet ou status.
- `POST /vet/orcamentos`: cria orcamento com itens e totais calculados.
- `GET /vet/orcamentos/{id}`: retorna cabecalho e itens.
- `PATCH /vet/orcamentos/{id}`: atualiza dados editaveis e substitui itens.

As rotas validam tenant e garantem que consulta/internacao/pet pertencem ao mesmo tenant. O retorno inclui `totais` e `itens` serializados para a tela e para futura exportacao.

## Frontend

Adicionar um painel compacto de orcamento em consulta e internacao:

- Na consulta, o painel aparece perto de procedimentos realizados, reutilizando catalogo de procedimentos e produtos de estoque.
- Na internacao, o painel aparece no detalhe da internacao, com campo de dias previstos e acao para abrir/criar orcamento.
- O painel mostra custo estimado, venda sugerida, venda cobrada e margem.
- O usuario pode ajustar preco cobrado sem alterar custo de cadastro.

## Testes

- Teste backend para criar orcamento sem gerar `EstoqueMovimentacao`.
- Teste backend para calcular custo/preco/margem a partir de catalogo e produto.
- Teste backend para validar tenant dos vinculos.
- Teste frontend unitario dos calculos/normalizacao usados pelo painel.
