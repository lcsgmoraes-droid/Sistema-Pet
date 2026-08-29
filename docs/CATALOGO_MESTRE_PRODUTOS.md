# Catálogo mestre de produtos

## Objetivo

Manter uma base global, progressivamente enriquecida, que possa ser oferecida
como referência aos usuários do Sistema Pet. A primeira fonte autorizada é o
catálogo do **Atacadão das Rações Pet**.

O catálogo mestre não é o cadastro operacional de nenhuma loja. Ele não contém
preço, custo, estoque, margem, comissão, fornecedor ou promoções e não atualiza
automaticamente a tabela `produtos` de nenhum tenant.

## Linha de base verificada em produção

Auditoria somente leitura realizada em 29/08/2026 no tenant do Atacadão:

| Indicador | Quantidade |
| --- | ---: |
| Produtos não excluídos | 7.022 |
| Produtos ativos, vendáveis e elegíveis para o catálogo mestre | 6.773 |
| Elegíveis sem imagem | 6.045 |
| Elegíveis com exatamente 1 imagem | 669 |
| Elegíveis com 2 a 4 imagens | 4 |
| Elegíveis com 5 ou mais imagens | 55 |
| Posições de imagem ainda necessárias para atingir a meta de 5 | 32.912 |
| Produtos não excluídos com algum EAN/GTIN | 4.891 |
| Produtos não excluídos com descrição curta/completa | 388 / 348 |
| Produtos não excluídos com NCM legado / NCM fiscal V2 | 3.892 / 6.461 |

O fiscal V2 é a melhor referência disponível para NCM e deve prevalecer sobre o
campo legado quando estiver preenchido. Mesmo assim, CFOP, CST e alíquotas são
armazenados apenas como referência: a aplicação em uma loja deve considerar UF,
regime tributário e tipo de operação.

Há 19 GTINs repetidos na origem. A sincronização mantém esses itens separados e
os marca para revisão; não existe fusão automática por código de barras.

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

