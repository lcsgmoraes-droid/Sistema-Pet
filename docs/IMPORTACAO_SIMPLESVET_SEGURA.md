# Importacao SimplesVet segura

Este e o unico procedimento oficial para importar uma exportacao do SimplesVet.
Ele foi desenhado para impedir que dados sejam enviados para a empresa errada.

## Garantias do fluxo

- empresa de destino e usuario responsavel sao obrigatorios;
- o usuario informado precisa pertencer a empresa informada;
- os CSVs e suas colunas sao validados antes de acessar os dados;
- a primeira etapa sempre e uma simulacao com rollback, sem gravar registros;
- a simulacao gera um plano com hash de cada arquivo e validade de 24 horas;
- a aplicacao aceita somente o mesmo plano, banco, empresa e arquivos;
- toda a aplicacao usa uma unica transacao: confirma tudo ou desfaz tudo;
- cada linha usa um ponto de recuperacao, sem apagar linhas validas anteriores;
- um plano aplicado nao pode ser reutilizado no mesmo ambiente;
- um bloqueio exclusivo impede duas aplicacoes simultaneas do mesmo plano;
- o contexto da empresa e removido da memoria ao fim de cada execucao;
- planos e relatorios ficam em `runtime/importacoes-simplesvet/`, fora do Git;
- aplicacao em producao exige liberacao e frase adicionais.

Os CSVs de clientes nunca devem ser copiados para pastas versionadas ou anexados
a Pull Requests. A pasta `simplesvet/` e ignorada pelo Git para uso local.

## Escopos disponiveis

| Escopo | Conteudo |
| --- | --- |
| `base` | especies e racas |
| `catalog` | clientes, contatos, marcas e produtos |
| `pets` | clientes, contatos e pets |
| `sales` | clientes, produtos, vendas e itens |
| `all` | todos os grupos acima |

As dependencias sao executadas automaticamente. Por exemplo, `sales` prepara os
mapas de clientes e produtos antes de processar vendas.

## Etapa 1: simular

Use sempre a empresa e o usuario exibidos no painel administrativo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\importar_simplesvet_seguro.ps1 `
  -Modo Simular `
  -TenantId "UUID-DA-EMPRESA" `
  -UserId 123 `
  -DiretorioDados "C:\dados\empresa\simplesvet" `
  -Escopo all
```

Para uma amostra, acrescente `-Limite 20`. O limite faz parte do plano; um plano
de 20 registros nao consegue aplicar todos os registros por engano.

Ao final, o comando informa:

- nome e identificador da empresa;
- contagens simuladas e rejeitadas;
- caminho do arquivo de plano;
- `plan_id`;
- horario de expiracao.

Revise essas informacoes antes de seguir.

## Etapa 2: aplicar em DEV

Copie o caminho, o identificador da empresa e o `plan_id` retornados pela
simulacao:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\importar_simplesvet_seguro.ps1 `
  -Modo Aplicar `
  -Plano "C:\caminho\simplesvet-plan-....json" `
  -ConfirmarTenantId "UUID-DA-EMPRESA" `
  -ConfirmarPlanId "PLAN-ID-COMPLETO"
```

Se qualquer CSV mudar, o plano expirar, o banco for outro ou a empresa nao
coincidir, a aplicacao e bloqueada e uma nova simulacao deve ser gerada.

## Producao

Antes de importar dados reais em producao:

1. confirmar que o plano foi gerado no proprio banco de producao;
2. revisar as contagens e rejeicoes;
3. fazer backup do banco;
4. receber autorizacao explicita do responsavel;
5. aplicar com `-PermitirProducao` e com a confirmacao
   `IMPORTAR-PRODUCAO-<tenant-id>`.

Essas flags nao substituem a autorizacao humana. Elas sao apenas a ultima trava
tecnica contra execucao acidental.

## Entradas de compatibilidade

`IMPORTAR_SIMPLESVET_TESTE.bat` e
`backend/executar_importacao_completa.ps1` continuam existindo apenas para nao
quebrar atalhos antigos. Ambos encaminham para
`scripts/importar_simplesvet_seguro.ps1`; nao possuem caminho de computador,
credencial ou logica de banco propria.

## Arquitetura

- `backend/importar_simplesvet.py`: regras de transformacao por entidade;
- `backend/importar_simplesvet_cli.py`: transacao, alvo e comandos `plan/apply`;
- `backend/importar_simplesvet_plan.py`: manifestos, hashes e validade do plano;
- `backend/importar_simplesvet_state.py`: contexto isolado da execucao;
- `backend/importar_simplesvet_utils.py`: leitura e conversao dos CSVs;
- `scripts/importar_simplesvet_seguro.ps1`: entrada operacional oficial.

O importador nao recebe URL de banco pela linha de comando. Ele usa a
configuracao oficial do ambiente, sem expor senha em historico de terminal.

Os importadores e diagnosticos antigos da raiz de `backend/` foram removidos da
arvore ativa. Eles duplicavam o fluxo, continham caminhos/bancos fixos,
consultavam dados sem contexto de empresa ou podiam gravar sem o novo plano. O
Git preserva o historico caso seja necessario consultar alguma regra antiga.
