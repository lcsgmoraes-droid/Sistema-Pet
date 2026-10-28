# Ficha de entrega — variacoes compostas e estoque Bling

## Identificacao

- Data: 2026-10-28.
- Responsavel de negocio: Lucas. Executor: Codex.
- Prioridade: P1. Risco: medio, por afetar estoque e integracao.
- Dominios: produtos, vendas, estoque, compras e Bling.
- PR: registrado na entrega pelo GitHub.

## 1. Necessidade e requisitos

Uma embalagem pode ser variacao de um pai e tambem kit virtual. A venda deve
consumir seus componentes, e o Bling deve receber a disponibilidade calculada.
Exemplo de aceite: tubo com saldo 50 e reserva 3 permite 11 pacotes de 4 ou
1 caixa de 24. Vender duas embalagens deve consumir 8 ou 48 tubos.

Preservar estoque proprio das variacoes comuns e dos kits fisicos, isolamento,
historico e os bloqueios existentes de devolucao/cancelamento de kits virtuais.
Fora do escopo: devolucao automatica por snapshot de componentes, alteracao de
precos de clientes, dados operacionais de producao e novas migrations.

## 2. Regras de negocio e dados

- Produto pai continua agrupador sem estoque; tubos possuem estoque fisico.
- Variacao virtual segue a composicao nas vendas e reducoes de quantidade.
- Fornecedor local tem prioridade, inclusive sua reativacao existente. Somente
  na ausencia dele pode ser reutilizado fornecedor ativo do mesmo grupo ativo,
  pelo mesmo CNPJ e pelo predicado canonico de visibilidade de pessoas.
- Nao copiar nem alterar contatos, origem ou tenant do fornecedor compartilhado.
- Nenhuma mudanca de schema, retroacao de historico ou ajuste de saldo em massa.

## 3. Arquitetura e integracoes

Classificacao comum de kit nas vendas; calculo existente de estoque virtual
reutilizado na fila, worker, reconciliacao e status Bling. O worker recalcula o
saldo antes do envio. A listagem calcula os kits em lote.

Mudancas dos componentes agendam dependentes no commit externo, depois das
baixas, com tenant de origem preservado. Rollback limpa as pendencias. A fila
mantem seus retries e indisponibilidade do Bling nao desfaz a venda.

## 4. Seguranca e privacidade

Preservadas autenticacao, permissoes, RLS e contexto de tenant. Selecionar uma
variacao de outra empresa falha sem baixar o produto original. O fornecedor
compartilhado exige grupo e membros ativos; CNPJ diferente, nao-fornecedor,
pessoa inativa e empresa externa nao sao reutilizados. Nenhum secret novo.
XML real, identificadores de clientes e logs operacionais ficam fora do Git.

## 5. Desenvolvimento e qualidade

Fatias: baixa das variacoes compostas; saldo/propagacao Bling; reutilizacao do
fornecedor autorizado na importacao. Testes com dados ficticios e SQLite cobrem
pacote 4/caixa 24, variacoes comuns/fisicas, reservas, worker, rollback, falha
isolada, contexto compartilhado e regras de acesso ao fornecedor.

Validacao integrada: 134 testes passaram nos 13 arquivos focados de vendas,
estoque, Bling, importacao e isolamento. Ruff e diff check passaram. As rodadas
ampliadas identificaram dois mocks antigos de UUID em custo de produtos e um
contrato antigo de router incompativel com o FastAPI atual; detalhes no PR.
Revisao independente examinou concorrencia da fila e prioridade do fornecedor
local, com correcoes e regressao especifica para os pontos encontrados.

## 6. Ambientes e homologacao

Validacao local isolada por testes, sem dados de producao. Homologacao funcional
em producao pendente de autorizacao separada e publicacao. Nao ha E2E de venda
real: nao gerar movimentacao financeira ficticia no ambiente do cliente.

Limite preservado: cancelamento/devolucao de virtual exige conciliacao manual
dos componentes; nao reconstruir consumo passado pela composicao atual.

## 7. Publicacao e rollback

Entrega de backend, sem alteracao de frontend/mobile ou migration. Publicar
somente pelo fluxo oficial apos PR/checks e autorizacao explicita do Lucas.
Validar health/watchdog e importacao/cadastro/saldo antes da sincronizacao.
Em falha, suspender a operacao e usar o rollback oficial para o commit anterior;
nao desfazer banco ou documentos fiscais automaticamente.

## 8. Observabilidade e sustentacao

Usar logs existentes de importacao e fila Bling, com identificador de requisicao.
Conferir saldo dos tubos e disponibilidade derivada de cada embalagem. Erros da
fila ficam registrados para retry/reconciliacao. Evitar reverter nota inteira
como correcao de embalagem quando houver vendas ou financeiro associados.

## 9. Mudanca e comunicacao

O usuario continua cadastrando variacoes e composicoes nas telas existentes.
Comunicar a diferenca entre custo e preco de venda, a entrada por tubos e o
limite de cancelamento/devolucao manual. Nao ha nova tela ou treinamento formal.

## 10. Fechamento

- Implementacao e testes locais: preparados para revisao.
- Producao e cadastros comerciais: pendentes de publicacao autorizada.
- Conferencia da NF e sincronizacao final: pendentes da etapa operacional.
- Decisao: aprovado para revisao; publicacao exige autorizacao separada.
