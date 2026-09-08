# Fusao de produtos e identidades de SKU

Este fluxo consolida cadastros do mesmo produto sem transformar SKU de marketplace
em codigo de barras. A identificacao do item do pedido e a autorizacao para atualizar
catalogo, custo ou estoque sao controles distintos.

## Operacao autenticada

Usar a tela existente de fusao de produtos. O tenant vem da sessao autenticada e
a permissao continua sendo `produtos.editar`.

1. Escolher o cadastro que permanece e o cadastro duplicado.
2. Escolher `somar` para quantidades fisicas distintas, ou `manter_principal`
   quando o saldo do duplicado ja esta incluido no principal.
3. Conferir o estoque final, os dois vinculos Bling, as filas pendentes e os campos.
4. Registrar a evidencia da identidade e da contagem. Para manter saldo ou incluir
   aliases extras, a justificativa explicita deve ter pelo menos 10 caracteres.
5. Havendo dois IDs Bling diferentes, confirmar a preservacao do ID retirado como
   historico, sem envio. O cadastro remoto nao e apagado ou alterado pela fusao.
6. Aplicar somente apos gerar o preview atual. Cadastro, saldo ou vinculo alterado
   desde o preview exige nova revisao.

Exemplo: principal tem 50 pacotes e duplicado tem 4, mas a contagem confirmou que
os 4 ja estao incluidos nos 50. `manter_principal` conserva 50 e zera o cadastro
arquivado na mesma transacao. Nunca grava 54. Identidade, unidade, custo e precos
do principal sao preservados nessa estrategia. Ela exige dois produtos simples,
sem kit/granel e com a mesma unidade local; nao converte caixas em unidades.

## Contrato HTTP

As rotas abaixo usam o prefixo `/api/produtos` da aplicacao.

- `POST /fusao/preview`: `produto_principal_id`, `produto_duplicado_id`,
  `estrategia_estoque` (`somar` ou `manter_principal`). A resposta inclui os campos
  existentes, `preview_token`, `estoque_final` (tres saldos), `conflito_bling`,
  `vinculos_bling`, `filas_pendentes` e `rollback_automatico: false`.
- `POST /fusao/executar`: mesmos campos, `preview_token`, `observacao`,
  `decisoes_campos`, `preservar_vinculo_bling_duplicado` e `aliases_sku` opcionais.
  O token e obrigatorio. A resposta inclui `auditoria_id`.
- `POST /{produto_id}/aliases-sku/preview`: `{ "sku": "SKU-ANTIGO" }`.
  Retorna cadastro canonico, SKU alternativo, token e indicacao de que nao altera
  estoque nem reservas.
- `POST /{produto_id}/aliases-sku/aplicar`: `sku`, `motivo` (10 a 2000 caracteres)
  e `preview_token`. Mantem a mesma permissao de editar produto.

Na edicao de um produto, a acao de SKU alternativo usa as duas ultimas rotas.
Aliases aceitam 1 a 100 caracteres, normalizados por trim e casefold. A unicidade
vale por tenant; cadastro/renomeacao de outro produto nao pode reutilizar o alias.
Colisoes com SKU, EAN ou outro alias bloqueiam a operacao. Nenhum EAN e preenchido
com SKU alternativo.

## Transacao, reservas e Bling

Na edicao de um produto, `Sincronizacao Bling` permite pausar ou retomar o envio
automatico desse cadastro. `GET /api/estoque/sync/habilitacao/{produto_id}` consulta
o estado e `PATCH` no mesmo caminho recebe somente `{ "sincronizar": false }`
(ou `true`). Ambos exigem sessao do tenant e `produtos.editar`. A acao preserva o
ID Bling e `estoque_compartilhado`, inclusive `NULL`, e nao altera estoque/precos.
Sem vinculo ou com origem retirada, nao cria ligacao nem permite retomada.

A pausa espera eventual worker em andamento terminar sob os mesmos locks e
impede envios seguintes. A retomada apenas habilita a rotina existente, que pode
enfileirar o saldo atual; nao comprova sincronizacao concluida. Durante saneamento
de carrinhos, manter o produto pausado ate definir o saldo e validar os pedidos.
O controle nao seleciona a autoridade Bling/EcommerceAI do projeto de integracao.

A ordem de locks e namespace de aliases do tenant, produtos em ordem de ID e
vinculos Bling. Os caminhos de fila, configuracao e reconciliacao recarregam os
objetos sob lock antes de usar sua autoridade. Filas de estoque ou custo em
`pendente`, `processando` ou `erro` impedem a fusao.

Baixa e estorno do EstoqueService enfileiram o Bling na mesma transacao do estoque,
sem abrir outra conexao que espere o proprio produto. O commit torna saldo e fila
visiveis juntos; rollback remove ambos. O enfileiramento usa savepoint: falha na
fila registra aviso e preserva a operacao de estoque, conforme a politica existente
de reconciliacao posterior. Nao ha chamada remota durante essa transacao.

O autocadastro por nota repete a resolucao de identidade apos a consulta remota,
sob o namespace. Como a nota pode ja ter locks de outros itens, essa aquisicao e
nao bloqueante: identidade em revisao deixa o autocadastro pendente para repetir,
evitando inversao de locks ou recriacao de SKU durante a fusao.

O SKU original do duplicado e seus aliases anteriores passam ao principal.
Aliases extras exigem identidade confirmada, nunca aproximacao pelo titulo.
Reservas mantem SKU original, quantidade, timestamps e estado; o resolvedor central
passa a identifica-las pelo alias. A fusao nao libera reservas, nao cria nova baixa
e nao marca pedidos como vendidos. O catalogo EcommerceAI usa esse mesmo mapa.

Quando existem dois vinculos, o vinculo retirado continua ligado ao produto
arquivado, com seu ID remoto original, `sincronizar=false` e
`retirado_para_produto_id` apontando para o principal. O marcador prevalece sobre
status e flags, inclusive em normalizacao e reprocessamento de filas. Historicos
de filas de estoque e custo nao sao transferidos para outro vinculo remoto.

Pedidos podem resolver um ID Bling retirado para o principal. Importacao de
catalogo/saldo e religacao desse ID sao recusadas; snapshots tambem o excluem,
inclusive quando vier de cache anterior. Nenhum dado desse ID pode sobrescrever
custo, preco ou saldo do principal. Se ambos os cadastros ja compartilham o mesmo
ID remoto, a identidade continua ativa pelo vinculo sobrevivente.

Uma fusao posterior redireciona as identidades retiradas anteriores ao novo
principal. Destino arquivado, tenant divergente e ciclo evidente sao recusados.

## Auditoria e recuperacao

`produto_sku_aliases` registra tenant, destino, SKU, origem, justificativa e
operador. `produto_fusao_logs` guarda antes/depois, estrategia, operador, motivo e
referencias originais com chaves primarias. O log tem unicidade por duplicado;
repetir uma fusao ja concluida e recusado. As novas tabelas tem RLS obrigatoria.

Falha antes do commit desfaz estoque, aliases, referencias e arquivamento juntos.
Depois de confirmada a fusao nao ha desfusao automatica. Recuperacao exige revisao
dos registros da auditoria e das operacoes posteriores, com o backup do fluxo
oficial de publicacao como apoio; nao executar SQL manual para contornar guardas.
A API nao altera o Bling remoto ou anuncios. A desativacao/correcao remota e uma
etapa coordenada separada.

## Validacao local

Os testes `test_produto_alias_merge.py` e `test_produto_alias_merge_api.py` cobrem
saldo 50 sem estado 54, reservas preservadas, pedidos por identidade retirada,
precos canonicos, repeticao, colisao, escopo de tenant, permissao e rollback HTTP.
`test_bling_retired_origin_guards.py` cobre as entradas e filas do Bling.

`test_produto_merge_postgres.py` usa somente banco descartavel explicitamente
identificado em `127.0.0.1:55487/corepet_merge_test`. O teste recusa outro destino.
Abrange concorrencia de saldo/preview, namespace de aliases, objetos ORM antigos
nas entradas Bling, e a migracao com upgrade/downgrade, unicidade e RLS. Os dados
sao sinteticos; esse teste nao valida dados ou credenciais de uma loja real.

Antes de publicar, executar o gate oficial `FLUXO_UNICO.bat release-check` em
branch de tarefa limpa, apos os testes focados e revisao do diff conjunto.
