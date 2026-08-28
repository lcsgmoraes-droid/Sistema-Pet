# Credenciais do WhatsApp e OpenAI criptografadas no banco

Data: 2026-08-28

## Problema

A API ja escondia as credenciais do navegador, mas os valores historicos de
`api_key`, `webhook_secret` e `openai_api_key` ainda estavam armazenados em
texto legivel no banco. Uma leitura indevida do banco poderia expor essas
credenciais.

## Decisao

As credenciais de integracoes por empresa passam a usar a mesma chave mestra
ja exigida para as configuracoes de pagamento:
`PAYMENT_CONFIG_ENCRYPTION_KEY` (com `ENCRYPTION_KEY` como compatibilidade).
Nenhum valor de chave e versionado no Git.

O mecanismo de criptografia Fernet foi centralizado para evitar implementacoes
divergentes. O modelo do WhatsApp preserva os nomes publicos `api_key`,
`webhook_secret` e `openai_api_key`, portanto os servicos existentes continuam
lendo e gravando sem conhecer os detalhes da criptografia.

## Migracao e compatibilidade

A migration adiciona colunas criptografadas, converte os valores existentes e
limpa as colunas antigas na mesma transacao. As colunas antigas permanecem
temporariamente como compatibilidade estrutural, mas ficam nulas.

No PostgreSQL, a migration suspende a RLS apenas durante a conversao
administrativa e a restaura imediatamente, inclusive se houver erro. Antes de
uma publicacao, o procedimento continua exigindo backup e teste das migrations.

O downgrade faz o caminho inverso: descriptografa de forma estrita, restaura
as colunas legadas e remove as novas colunas. Se a chave estiver incorreta, ele
interrompe em vez de gravar dados vazios.

## Criterios de aceite

- novas gravacoes nao mantem texto claro nas colunas legadas;
- os tres segredos sao recuperados transparentemente com a chave correta;
- uma chave incorreta nunca devolve o texto criptografado como credencial;
- producao falha de forma explicita quando a chave mestra nao existe;
- configuracoes de pagamento continuam usando o mesmo contrato de criptografia;
- upgrade e downgrade preservam os valores existentes;
- API e frontend continuam sem receber credenciais salvas.

## Operacao e rollback

O valor de `PAYMENT_CONFIG_ENCRYPTION_KEY` nao deve ser alterado diretamente:
rotacao de chave exige procedimento controlado de descriptografar e
recriptografar os dados. Em rollback, restaurar o codigo anterior e executar o
downgrade com a chave mestra ainda disponivel. O backup anterior ao deploy e a
segunda camada de recuperacao.

## Evidencia local

- 157 testes unitarios do WhatsApp aprovados;
- 27 testes de configuracao e OAuth do Mercado Pago aprovados;
- 14 testes de criptografia, migration e RLS aprovados;
- upgrade e downgrade reais executados sobre SQLite preservando os tres valores;
- Ruff e compilacao Python aprovados nos arquivos alterados;
- Alembic validado com uma unica ponta: `zxk20260828a1`.
