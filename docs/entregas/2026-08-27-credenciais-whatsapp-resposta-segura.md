# Credenciais do WhatsApp e OpenAI fora da resposta da API

Data: 2026-08-27

## Problema

A consulta autenticada de `/whatsapp/config` devolvia ao navegador os valores
completos de `api_key`, `webhook_secret` e `openai_api_key`. A tela precisava
saber apenas se a chave OpenAI estava cadastrada, nao ler a credencial salva.

## Decisao e compatibilidade

A resposta da API possui agora um contrato separado do contrato de entrada. Os
valores sensiveis foram removidos e substituidos por indicadores booleanos:

- `has_api_key`;
- `has_webhook_secret`;
- `has_openai_api_key`.

POST e PUT continuam aceitando novas credenciais para criacao ou troca. A tela
de configuracao passou a usar `has_openai_api_key`, mantendo a indicacao de
"Chave cadastrada" sem receber a chave real.

## Criterios de aceite

- GET, POST e PUT usam um modelo de resposta que nao declara campos secretos;
- a resposta informa somente se cada segredo esta configurado;
- valores vazios nao aparecem como credenciais configuradas;
- a tela continua permitindo cadastrar e substituir a chave OpenAI;
- nao ha migration nem alteracao dos dados persistidos.

## Evidencia local

- 5 testes focados do contrato e da resposta HTTP aprovados;
- 157 testes unitarios do WhatsApp aprovados;
- contrato do frontend `test:openai-config-security` aprovado;
- build de producao do frontend concluido;
- nenhum segredo real foi usado nos testes.

## Publicacao e rollback

O deploy autorizado deve reconstruir o backend e gerar o frontend. A validacao
pos-publicacao deve abrir Integracoes, confirmar o indicador de chave cadastrada
e salvar uma troca controlada apenas quando houver uma credencial de teste.

Rollback: reverter o commit, reconstruir o backend e gerar novamente o
frontend. Nao ha conversao nem perda de dados.

## Proxima melhoria recomendada

As credenciais continuam armazenadas nas colunas atuais do banco. Criptografia
em repouso deve ser tratada em tarefa separada, com migration e plano de
compatibilidade para valores ja existentes.
