# Catálogo mestre de produtos

## Objetivo

Manter uma base global, progressivamente enriquecida, que possa ser oferecida
como referência aos usuários do Sistema Pet. A primeira fonte autorizada é o
catálogo do **Atacadão das Rações Pet**.

O escopo da primeira fase é propositalmente limitado a produtos padronizáveis e
normalmente identificados por marca:

- rações;
- petiscos e biscoitos;
- medicamentos/farmácia;
- areias sanitárias, sílicas e granulados higiênicos, incluindo linhas como
  Pipicat.

Brinquedos, caixas, pás, comedouros e acessórios genéricos ficam fora desta
primeira carga. A regra é uma lista positiva: um produto só entra se for
classificado em um dos quatro grupos acima.

O catálogo mestre não é o cadastro operacional de nenhuma loja. Ele não contém
preço, custo, estoque, margem, comissão, fornecedor ou promoções e não atualiza
automaticamente a tabela `produtos` de nenhum tenant.

## Linha de base verificada em produção

Auditoria somente leitura realizada em 29/08/2026 no tenant do Atacadão:

| Indicador | Quantidade |
| --- | ---: |
| Produtos não excluídos | 7.022 |
| Produtos ativos e vendáveis antes do filtro de escopo | 6.773 |
| Candidatos sem imagem antes do filtro de escopo | 6.045 |
| Candidatos com exatamente 1 imagem antes do filtro | 669 |
| Candidatos com 2 a 4 imagens antes do filtro | 4 |
| Candidatos com 5 ou mais imagens antes do filtro | 55 |
| Posições de imagem no universo anterior ao filtro | 32.912 |
| Produtos não excluídos com algum EAN/GTIN | 4.891 |
| Produtos não excluídos com descrição curta/completa | 388 / 348 |
| Produtos não excluídos com NCM legado / NCM fiscal V2 | 3.892 / 6.461 |

O fiscal V2 é a melhor referência disponível para NCM e deve prevalecer sobre o
campo legado quando estiver preenchido. Mesmo assim, CFOP, CST e alíquotas são
armazenados apenas como referência: a aplicação em uma loja deve considerar UF,
regime tributário e tipo de operação.

Há 19 GTINs repetidos na origem. A sincronização mantém esses itens separados e
os marca para revisão; não existe fusão automática por código de barras.

O primeiro `dry-run` após a publicação informará a quantidade exata dentro do
novo escopo. Os números de imagem acima são o teto operacional anterior ao
filtro e, portanto, não devem ser usados como tamanho final da fila inicial.

## Estrutura criada

- `catalogo_mestre_produtos`: conteúdo canônico, qualidade, lacunas, snapshot e
  proveniência por campo.
- `catalogo_mestre_imagens`: imagem, origem, posição, dimensões, indicação de IA,
  direitos de uso e revisão.
- `catalogo_mestre_pendencias`: fila idempotente de melhoria por produto e
  posição.
- `catalogo_mestre_sincronizacoes`: auditoria das cargas efetivamente aplicadas.

A identificação da origem usa `origem_tenant_id` e `origem_produto_id`, sem
alterar nem adicionar vínculo ao registro original.

## Política das cinco imagens

A meta representa cinco ângulos/conteúdos úteis, não cinco variações artificiais
da mesma foto:

1. frente da embalagem;
2. verso/rótulo e composição;
3. lateral, tabela nutricional, consumo ou instruções;
4. detalhe do produto e escala da embalagem;
5. imagem complementar oficial ou contextual.

A ordem de preferência da fila é: fabricante/licenciada, distribuidor
autorizado, material próprio e, por último, geração assistida. Imagem gerada:

- recebe `gerada_por_ia = true`;
- mantém modelo e versão do prompt;
- não pode inventar ou reconstruir embalagem, rótulo, selo ou texto fiscal;
- não é publicada automaticamente;
- precisa de revisão e de uma situação de direitos de uso definida.

Para medicamentos, geração assistida só pode produzir uma imagem contextual. A
embalagem, a bula e a posologia devem vir de fonte oficial e requerem revisão
antes de publicação.

## Melhoria contínua

Cada sincronização recalcula a qualidade e mantém uma fila para:

- posições de imagem faltantes;
- GTIN ausente ou inválido;
- descrição completa;
- referência fiscal/NCM;
- tabela nutricional e tabela de consumo de rações;
- bula e posologia de medicamentos.

As lacunas resolvidas fecham automaticamente apenas tarefas ainda pendentes.
Itens em processamento ou revisão não são encerrados por uma sincronização.

O ciclo operacional recomendado é:

1. sincronizar diariamente o Atacadão para capturar novos produtos e alterações;
2. selecionar um lote pequeno da fila, priorizando segurança e marcas de maior
   demanda;
3. buscar material oficial e só gerar conteúdo quando permitido;
4. revisar identidade, direitos e conteúdo técnico;
5. publicar no catálogo mestre;
6. disponibilizar ao usuário como escolha, sem sobrescrever o cadastro da loja.

## Execução segura

O comando sempre inicia em modo de simulação:

```powershell
python -m app.scripts.run_catalogo_mestre_sync
```

Carga efetiva fora de produção:

```powershell
python -m app.scripts.run_catalogo_mestre_sync --apply
```

Em produção, `--apply` permanece bloqueado sem
`--allow-production-apply`. A flag é apenas uma trava técnica adicional: a
execução em produção continua exigindo autorização operacional explícita.

Esta primeira versão também rejeita qualquer e-mail de origem diferente de
`atacadaopetpp@gmail.com`.

## Imagens fornecidas com EAN no nome

Lotes de imagens podem ser inventariados quando cada arquivo segue o formato
`EAN_NOME.jpg`, `EAN_NOME.jpeg`, `EAN_NOME.png` ou `EAN_NOME.webp`:

```powershell
python -m app.scripts.run_catalogo_mestre_image_import `
  --source-dir C:\caminho\para\imagens `
  --source-ref identificador-do-lote
```

O comando tambem inicia em simulacao. Ele valida o digito verificador do GTIN,
o formato real da imagem, tamanho, dimensoes e SHA-256. Quando o lote inclui
`relatorio_download.csv`, a fonte informada de cada arquivo tambem acompanha a
proveniencia, mas nao e tratada como licenca de uso. O casamento e sempre por
GTIN exato com um produto que ja existe no catalogo mestre e pertence ao escopo
inicial. Nome de arquivo nunca cria produto e GTIN ambiguo fica bloqueado.

Com `--apply`, o arquivo e apenas copiado para
`uploads/catalogo_mestre_pendente`, prefixo que nao e servido publicamente pelo
backend. A imagem entra inativa, com direitos `nao_verificado` e revisao
`pendente`; `arquivo_url` permanece vazio. Assim, a carga nao publica imagem,
nao preenche automaticamente as cinco posicoes e nao altera nenhum cadastro de
loja. Em producao, a aplicacao ainda exige `--allow-production-apply` e
autorizacao operacional explicita.

