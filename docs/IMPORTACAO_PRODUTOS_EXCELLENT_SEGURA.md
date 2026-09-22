# Importacao segura de produtos do Excellent Sistemas

Este fluxo substitui o cadastro operacional de produtos de um tenant usando o
PDF `Relatorio Grade` do Excellent Sistemas. O arquivo precisa conter codigo,
codigo interno, estoque, estoque minimo, unidade, nome, classificacao, NCM,
custo unitario e valor de venda.

## Garantias

- a primeira etapa sempre simula tudo e executa rollback;
- o PDF, banco, tenant, usuario, contagens e resultado da simulacao ficam
  vinculados a um plano imutavel com validade de 24 horas;
- a aplicacao usa uma unica transacao;
- produtos anteriores sao arquivados, nao apagados fisicamente, preservando
  referencias historicas;
- SKUs conflitantes dos registros arquivados recebem uma chave tecnica;
- os novos produtos nao sao publicados automaticamente no app ou ecommerce;
- o cruzamento com o catalogo-base usa apenas GTIN/EAN valido e ainda exige
  compatibilidade de nome antes de copiar campos ou imagem;
- custo e preco de venda do PDF sao preservados;
- em producao, a aplicacao exige confirmacao do tenant e referencia do backup;
- plano, recibo e PDF devem permanecer fora do Git.

## Simulacao

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\importar_produtos_excellent_seguro.ps1 `
  -Modo Simular `
  -TenantId "UUID-DO-TENANT" `
  -UserId 123 `
  -TenantFonteId "UUID-DO-CATALOGO-BASE" `
  -Pdf "C:\dados\Relatorio Estoque.pdf" `
  -QuantidadeEsperada 3643
```

Conferir no resultado:

- tenant e usuario de destino;
- `active_products_before`;
- `created_products` igual a 3.643;
- quantidade de EANs validos;
- custos zerados e estoques negativos;
- `matched_products`, `compatible_products` e `images` no enriquecimento;
- caminho, `plan_id` e validade do plano.

## Aplicacao em DEV

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\importar_produtos_excellent_seguro.ps1 `
  -Modo Aplicar `
  -Plano "C:\caminho\excellent-plan-....json" `
  -ConfirmarTenantId "UUID-DO-TENANT" `
  -ConfirmarPlanId "PLAN-ID-COMPLETO"
```

## Producao

Antes de aplicar:

1. gerar o plano no proprio banco de producao;
2. revisar as contagens e amostras;
3. gerar e validar um backup do banco;
4. receber autorizacao explicita do Lucas;
5. usar `--allow-production-apply`, a confirmacao
   `IMPORTAR-PRODUTOS-PRODUCAO-<tenant-id>` e a referencia do backup.

O PDF e os planos podem ficar em `backend/uploads/importacoes-excellent/`, que
e persistido no servidor e nao e versionado.

## Mapeamento

| Excellent | CorePet |
| --- | --- |
| Codigo interno unico | SKU (`codigo`) |
| Codigo, quando o interno falta ou duplica | SKU alternativo |
| Codigo com ate 20 caracteres | Codigo de barras para leitura |
| Codigo com GTIN valido | `gtin_ean` e chave do cruzamento de imagem |
| Produto | Nome; quando `S/R`, usa o codigo de origem |
| Estoque atual | Estoque atual, fisico e ecommerce |
| Aviso de estoque minimo | Estoque minimo |
| Custo unitario | Preco de custo |
| Valor venda | Preco de venda |
| NCM valido com oito digitos | NCM |
| Classificacao contendo `granel` | Produto a granel |

O relatorio nao informa com seguranca o status ativo/inativo nem os canais de
publicacao. Por isso os cadastros entram ativos para operacao, mas com app e
ecommerce desmarcados ate revisao do cliente.
