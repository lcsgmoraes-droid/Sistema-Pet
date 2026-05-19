# Catalogo Base Administrativo Design

## Objetivo

Criar uma estrutura padrao para que um administrador importe, sob demanda, o catalogo base da loja `admin@mlprohub.com.br` para qualquer novo tenant que queira iniciar com uma lista pronta de produtos.

## Regra Principal

O catalogo base e uma copia cadastral inicial. Depois de importado, cada tenant passa a ser dono dos seus registros. Alteracoes no tenant destino nao alteram a loja base, e alteracoes futuras na loja base nao sobrescrevem registros ja importados.

## Fonte Padrao

- Usuario fonte: `admin@mlprohub.com.br`.
- Tenant fonte: resolvido pelo usuario fonte no momento da execucao.
- A fonte e a loja do Lucas e sera usada como catalogo de referencia do SaaS.

## Destino

- Tenant escolhido pelo administrador.
- A execucao deve aceitar `dry-run` para mostrar o que sera criado antes de gravar.
- A execucao `apply` deve ser explicita.
- Tenants existentes podem receber a importacao, mas registros ja importados nao devem duplicar.

## O Que Importar

- Departamentos, usados como grupo macro dos produtos.
- Categorias, preservando hierarquia por `categoria_pai_id` e vinculo com departamento.
- Marcas.
- Cadastros auxiliares de racao usados pelos produtos, quando existirem:
  - linhas de racao;
  - portes de animal;
  - fases/publicos;
  - tipos de tratamento;
  - sabores/proteinas;
  - apresentacoes de peso.
- Produtos, com dados cadastrais, fiscais, recorrencia, caracteristicas fisicas, codigos, classificacoes e imagens.
- Imagens dos produtos, copiadas para o caminho do tenant destino.
- Relacoes cadastrais entre produtos:
  - produto pai/variacao;
  - predecessor/sucessor;
  - kits;
  - vinculos granel.

## O Que Nao Importar

- Bling, sync, filas, IDs externos ou qualquer dado de integracao.
- Estoque atual, estoque fisico, estoque ecommerce, estoque minimo e estoque maximo.
- Lotes.
- Fornecedores, fornecedor principal e fornecedores alternativos.
- Custo, margem, preco de venda, preco promocional, preco app e preco ecommerce.
- Historico de preco.
- Movimentacoes de estoque.
- Vendas, compras, notas, pedidos ou dados financeiros.

## Transformacoes Obrigatorias

Todo produto importado deve sair com:

- `estoque_atual = 0`;
- `estoque_fisico = 0`;
- `estoque_ecommerce = 0`;
- `estoque_minimo = 0`;
- `estoque_maximo = 0`;
- `preco_custo = 0`;
- `preco_venda = 0`;
- campos promocionais de preco limpos;
- `fornecedor_id = null`;
- sem lotes e sem vinculos com fornecedor.

## Idempotencia

A importacao deve registrar mapeamentos item a item usando a infraestrutura existente de templates:

- `tenant_template_installs` para resumo da execucao;
- `tenant_template_item_installs` para mapear cada item fonte para seu registro destino.

O `bundle_code` sugerido e `catalogo-base-loja-lucas`, com versao `v1`. O `template_code` deve ser estavel por tipo e ID fonte, por exemplo `produto:123`, `categoria:45`, `marca:9`.

Se um item fonte ja tiver mapeamento no tenant destino, a nova execucao deve pular esse item. Isso preserva edicoes feitas pelo cliente.

## Fluxo Administrativo

1. Administrador escolhe tenant destino.
2. Sistema roda dry-run e retorna contagens de criados, pulados e avisos.
3. Administrador confirma apply.
4. Sistema cria cadastros basicos, produtos e imagens em transacao.
5. Sistema registra auditoria e resumo.
6. Sistema retorna relatorio da execucao.

## Erros E Seguranca

- Bloquear importacao se fonte e destino forem o mesmo tenant.
- Bloquear apply se o tenant destino nao existir.
- Falhar fechado se algum vinculo cadastral obrigatorio nao puder ser remapeado.
- Nao fazer delete em massa no destino.
- Nao sobrescrever item ja mapeado.
- Em producao, continuar exigindo backup/manual ops conforme regras do repositorio.

## Primeiro Entregavel

O primeiro entregavel sera um servico backend reutilizavel e um script administrativo:

- `BaseCatalogImportService` com `dry_run` e `apply`.
- Script `run_base_catalog_import.py` para uso operacional seguro.
- Testes unitarios/multitenant cobrindo transformacoes, idempotencia e isolamento.

Uma tela administrativa pode ser adicionada depois chamando o mesmo servico.
