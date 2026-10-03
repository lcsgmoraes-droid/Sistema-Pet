# Importacao JN Moura para Vira Lata Tres Lagoas

Esta importacao usa o backup JN Moura de 02/10/2026 e carrega a primeira etapa
operacional: clientes, fornecedores, categorias, produtos e saldo de estoque.
Vendas, contas, usuarios, dados fiscais da empresa e historico de movimentacoes
de estoque ficam fora desta etapa.

## Origem e destino

- Backup original: SHA-256 `9a6ea2dfe6a03379807fa1ecc994601130472834c5ce7b68c5589ea0d08ce9e9`.
- CNPJ registrado no backup: `54.032.717/0001-44`.
- Tenant de destino: `cb731f87-2a2e-4e05-a09d-153dd9371854`, CNPJ `17.467.592/0001-59`.
- Usuario administrador responsavel no destino: ID `92`.

O cadastro da empresa ja existente no tenant de destino prevalece. O CNPJ e o
endereco antigos do backup nao sao copiados. A origem diferente foi confirmada
pelo responsavel como uma mudanca real da empresa.

O tenant ja possui os modelos operacionais de cadastro e cinco formas de
pagamento ativas (credito, debito, crediario, dinheiro e PIX). A importacao nao
duplica esses registros.

## Resultado esperado da conversao

| Registro | Quantidade |
| --- | ---: |
| Clientes | 848 |
| Fornecedores | 19 |
| Categorias | 31 |
| Produtos e servicos | 2.625 |
| Produtos genericos excluidos | 2 |
| Saldos negativos zerados | 971 |
| Produtos com saldo positivo | 878 |
| Produtos com codigo de barras duplicado removido | 23 |

Tres pessoas constam como cliente e fornecedor na origem. Entram como dois
cadastros de papeis distintos, identificados pelo codigo de origem e pelo prefixo
`F-` no cadastro de fornecedor. Os nomes `VARIADOS` e `DIVERSOS` sao excluidos
por igualdade exata, preservando descricoes como "cores variadas". Quando um
codigo de barras aparece em mais de um produto, ele e removido de todos esses
produtos para evitar que a leitura escolha o item errado.

## Procedimento

1. Restaurar o backup apenas em banco isolado e exportar os tres CSVs com
   `scripts/exportar_jnm_catalogo.py`. O extrator le somente o arquivo
   `VIRALATA_21451_2026-10-02 11-45-01.jnmbak` em Downloads, confere o hash
   informado em `--expected-backup-sha256` e grava apenas em
   `runtime/viralata-migration/source-20261002`, fora do Git. Conferir as
   contagens do manifesto.
2. Fazer backup do banco de destino antes da aplicacao em producao. Confirmar
   que o tenant ainda nao tem clientes ou produtos cadastrados.
3. Depois do merge e deploy do codigo pelo fluxo oficial, copiar apenas os tres
   CSVs e o manifesto para `/app/data/importacoes-jnm/source-20261002` no volume
   de dados do backend. Nao copiar o backup SQL Server para producao.
4. Executar `plan` no proprio ambiente de destino, informando tenant, usuario,
   CNPJs, hash do backup, diretorio de origem e diretorio de relatorios. O plano
   executa toda a carga e faz rollback. Conferir contagens, nome/CNPJ do destino,
   `plan_id` e validade de 24 horas.
5. Com autorizacao explicita do responsavel, executar `apply` com o caminho do
   plano, o tenant ID e o `plan_id`. Em producao, tambem informar
   `--allow-production-apply` e
   `--confirm-production IMPORTAR-JNM-PRODUCAO-cb731f87-2a2e-4e05-a09d-153dd9371854`.
6. Conferir as contagens gravadas, o CNPJ do tenant preservado, ausencia de
   estoque negativo e o recibo de aplicacao. A segunda aplicacao e recusada
   porque o destino deixa de estar vazio.
7. Executar `python enriquecer_jnm_imagens.py plan` no backend com `--tenant-id`,
   `--user-id`, `--expected-target-cnpj` e `--report-dir`. Conferir o numero de
   correspondencias e o plano gravado. Depois, executar `apply` com `--plan-file`,
   `--confirm-tenant-id` e `--confirm-plan-id`; em producao adicionar
   `--allow-production-apply` e
   `--confirm-production IMPORTAR-JNM-IMAGENS-cb731f87-2a2e-4e05-a09d-153dd9371854`.
   As imagens sao copiadas para caminhos exclusivos do tenant de destino e
   vinculadas apenas a produtos com descricao normalizada identica e unica no
   catalogo padrao. Codigos de barras isolados nao sao suficientes, pois alguns
   apontam para sabores ou embalagens diferentes.

O importador valida hashes dos arquivos, banco, tenant, usuario administrador e
prazo do plano antes de gravar. A aplicacao usa uma unica transacao. CSVs,
manifestos, planos e recibos nao devem entrar no Git ou em Pull Requests.
