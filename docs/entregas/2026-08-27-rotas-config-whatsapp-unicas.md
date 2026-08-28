# Rotas unicas de configuracao do WhatsApp

Data: 2026-08-27

## Problema

O backend registrava duas implementacoes para os mesmos metodos e caminhos de
`/whatsapp/config`. A primeira implementacao era usada em runtime e a segunda
ficava escondida pela ordem de registro do FastAPI.

As copias tinham contratos diferentes: a criacao escondida exigia `tenant_id`
no corpo, a consulta escondida respondia 404 onde a oficial responde vazio e as
estatisticas escondidas devolviam zeros fixos. Uma reorganizacao de imports
poderia trocar o comportamento sem alterar a URL.

## Decisao e compatibilidade

`backend/app/routers/whatsapp_config.py` e a unica fonte HTTP para configuracao,
teste de conexao e estatisticas. `backend/app/routes/whatsapp_routes.py` continua
responsavel por mensagens de clientes, tools e simulacoes de conversa.

Os nomes Python antigos `get_config`, `create_config`, `update_config`,
`delete_config` e `get_stats` foram preservados como aliases da implementacao
oficial. Isso evita quebrar imports internos sem registrar rotas duplicadas.

## Criterios de aceite

- cada metodo de `/whatsapp/config` possui uma unica implementacao registrada;
- `/whatsapp/config/stats` possui uma unica implementacao e consulta dados reais;
- o corpo de criacao nao aceita nem exige `tenant_id`; a empresa vem da sessao
  autenticada;
- tools, testes de mensagem e conversacao continuam isolados pela empresa
  selecionada;
- nenhuma migration, tabela, URL publica ou tela foi alterada.

## Publicacao e rollback

A mudanca exige rebuild do backend somente quando houver deploy autorizado. A
validacao pos-publicacao deve abrir a configuracao OpenAI/WhatsApp, carregar uma
configuracao existente e salvar uma alteracao controlada em homologacao.

Rollback: reverter o commit e reconstruir o backend. Nao ha alteracao de dados.

## Lacuna observada e resolvida

A exposicao de campos secretos para o navegador foi resolvida na entrega
`2026-08-27-credenciais-whatsapp-resposta-segura.md`. A API passou a informar
somente indicadores booleanos, incluindo `has_openai_api_key`, sem devolver a
credencial gravada.
