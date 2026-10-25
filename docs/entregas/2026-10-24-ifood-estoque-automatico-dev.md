# Estoque automático iFood — SKU 227 em DEV e piloto real restrito

## Escopo e resultado

Preparação da rotina automática de estoque para um único produto já vinculado.
O piloto é independente da ponte de pedidos do SKU 018631.1 e permanece
desligado por padrão. A validação inicial de 24/10 usou somente DEV, sem envio
externo, anúncio ou deploy de produção. A preparação do modo real em 25/10 está
descrita ao final; ela não constitui evidência de execução em produção.

A rotina observa o saldo confirmado no banco, desconta reservas e segurança,
respeita a pausa local e agrupa mudanças próximas. Cada tentativa persistida
contém somente EAN e estoque absoluto. Preço, promoção, conteúdo e ativação
do anúncio não fazem parte do PATCH.

## Proteções

- Allowlist exata de empresa, loja, produto, SKU 227 e EAN; vínculo existente
  e saldo inicial conferido com presença e atividade declaradas.
- No ensaio DEV, ambiente DEV e provedor falso em HTTP loopback obrigatórios.
  Nesse modo, produção, staging, URL externa e proxy de ambiente são bloqueados.
- Flags desligadas por padrão e scheduler líder já existente, sem novo daemon.
- Estado e tentativas duráveis, lock concorrente e releitura antes do envio.
- Janela conservadora de 35 minutos compartilhada com envio manual; 429 usa
  backoff persistido e limite de cinco falhas. Mudanças são coalescidas.
- Timeout, 5xx ou crash não geram repetição cega. Uma conferência posterior
  válida pode reabrir o fluxo após a janela e a revisão do vínculo.
- HTTP 202 é aceite do simulador, sem confirmação externa. A API e as telas
  distinguem esse ensaio de recebimento pelo iFood real.
- Operações manuais conflitantes ficam bloqueadas enquanto o piloto está ativo.
- FK composta por tenant/vínculo, RLS e histórico preservado no downgrade.

## Validação

- 58 testes unitários novos do worker e contratos de escopo, falhas e recuperação.
- 196 testes focados passaram, incluindo catálogo, estoque, pausa e cliente HTTP.
- 44 testes PostgreSQL passaram: 37 anteriores e sete novos. Incluem venda
  PDV, cancelamento, entrada manual, reserva/baixa/liberação, rollback,
  concorrência, mudança durante envio, migration real, FK composta e RLS com
  papel temporário sem superusuário nem bypass.
- Runtime DEV: scheduler e cliente HTTP reais contra servidor falso local.
  Referência 21; reserva 20; liberação 21; venda finalizada 20; repetição sem
  novo envio; cancelamento 21; reposição de duas unidades 23. Cinco PATCHes
  exclusivamente de estoque, sem chamada externa. Relógio lógico avançado
  para exercitar a janela, sem mudar o intervalo de 30 segundos registrado.
- Preços de ERP, app, ecommerce e iFood preservados. Produtos anteriores,
  lotes, vendas e pagamentos protegidos permaneceram iguais, incluindo o
  pedido oficial 1420 e o segundo tenant.
- Cadastro e central compartilham o acompanhamento, usando componentes V2
  para todas as ações e campos existentes. Nenhuma ativação automática pela UI.

As evidências detalhadas ficam no diretório privado do ensaio, fora do Git:
`stock227-runtime-proof.json`, `stock227-before.json`, `stock227-after.json`
e os logs de testes/build. Configuração e credenciais não são versionadas.
O gate completo e o CI do head final devem ser conferidos no PR 1561.

## Limite do ensaio inicial

O produto sintético deste primeiro ensaio não possuía lotes. A limitação do
cancelamento genérico identificada aqui recebeu uma correção posterior em DEV:
ver `2026-10-25-cancelamento-lotes-dev.md`. Esse registro original não comprova
a recomposição; os testes da correção posterior exercitam lotes reais de DEV,
histórico de custo, SKU repetido, concorrência e rollback.

Uma liberação real exige concluir a homologação do cenário com lotes, respeitar
a política de volumetria e a autorização do provedor real. O sucesso deste
ensaio não equivale a sincronização contínua homologada em produção. O guia de
implantação contém o roteiro para treinamento e o procedimento do piloto real.

Rollback operacional em DEV: desligar as duas flags e parar o worker de ensaio.
Isso preserva tentativas e saldos; não executar downgrade destrutivo com
histórico existente.

## Preparação do piloto real — 25/10/2026

O modo LIVE foi preparado para o teste autorizado de estoque no SKU `227`.
Este registro descreve o procedimento e as guardas. Os testes novos, o deploy
e os resultados efetivamente observados devem ser registrados separadamente,
sem reaproveitar a evidência do simulador como prova da API real.

### Escopo fechado

- Loja: Atacadão das Rações Avenida Brasil, merchant
  `adf87cbc-3858-413b-ae1e-3be36b1533e2`.
- Produto CorePet `5867`, SKU `227`, EAN `7898242031448`.
- Tenant exato na configuração protegida, validado contra a identidade fixa
  do piloto. Nenhum outro produto ou empresa é aceito.
- Ambiente e aliases presentes restritos a `production`/`prod`, flag DEV
  desligada e origem HTTPS exata `https://merchant-api.ifood.com.br`, com
  barra final opcional. Staging, proxy de ambiente e outro servidor bloqueiam.
- `IFOOD_STOCK_SYNC_LIVE_ENABLED` e `IFOOD_STOCK_SYNC_POLLING_ENABLED` são
  opt-ins distintos e começam `false`. A configuração completa exige também
  escrita de catálogo e as variáveis de tenant, merchant, produto, SKU e EAN.
- Estado e tentativas persistem `provider_mode`. Os registros antigos de
  `auto_stock` continuam `local_simulator`; os manuais são `ifood_api`. Trocar
  o modo de um estado existente bloqueia, sem reclassificar o histórico.
- O PATCH continua somente com `barcode` e `inventory.stock`, sem preço,
  promoção, conteúdo, ativação ou publicação de anúncio.

### Ordem da operação

1. Validar o commit final em DEV e CI, conferir a diferença entre o commit
   servido e a `main`, registrar o escopo completo e usar o deploy oficial
   autorizado. Publicar primeiro com LIVE e POLLING desligados e DEV `false`.
2. Conferir saúde, commit servido e migração `zzzzw20261025a1`. Guardar as
   referências do backup/deploy. A migração mantém a origem das evidências.
3. Com a rotina desligada, buscar o EAN novamente no catálogo do Portal,
   confirmar presença e atividade e registrar saldo, preços e estado local.
   Não depender de detalhe antigo cuja URL pode carregar dados em cache.
4. Se CorePet e Portal concordarem em `S > 1`, reduzir somente o estoque do
   item no Portal para `S − 1`, sem movimentar ERP, reservas ou lotes. Confirmar
   a mudança por nova busca e registrar no CorePet a conferência humana real
   de `S − 1`. Uma divergência natural já existente pode servir de referência;
   não registrar um saldo que não foi observado.
5. Conferir o escopo protegido exato, ativar LIVE e POLLING mantendo DEV
   desligado e recriar somente o backend com a mesma imagem aprovada. O
   Compose propaga essas variáveis explicitamente apenas para esse serviço;
   editar `.env` sem recriar o container não basta. Conferir o job no scheduler
   líder. Não habilitar o `worker-bling` para essa rotina.
6. Aguardar o PATCH automático do saldo atual `S`, sem botão de envio manual.
   O intervalo mínimo de observação é de 30 segundos; o cooldown conservador
   de 35 minutos permanece. Não alterar relógio nem reduzir janela em produção.
7. Distinguir o HTTP 202, aceito para processamento, do saldo aplicado no
   Portal. Conferir por nova busca que o saldo voltou a `S` e que um ciclo
   posterior sem alteração não gera outra tentativa. Comparar todos os preços,
   lotes, reservas, estoque físico e outros produtos com a referência inicial.

O cenário reduz uma unidade anunciada temporariamente e permite comprovar uma
atualização automática sem criar venda nem ajuste físico. Se houver venda real
durante o teste, usar o disponível atual correto como destino, sem repor um
saldo antigo. Uma pausa até zero e sua retomada são outro cenário e podem
exigir esperar a janela de 35 minutos. Venda, cancelamento e reposição só ficam
validados em produção quando esses eventos forem observados separadamente.

O roteiro detalhado está em [Guia da integração](../GUIA_INTEGRACAO_IFOOD.md),
na seção **Estoque automático real — piloto restrito ao SKU 227**. As referências
oficiais diferenciam [aceite assíncrono e conferência no Portal](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/how-it-works)
de [atualização parcial e volumetria](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/endpoints).
A janela de 35 minutos por produto é uma proteção conservadora do CorePet;
não deve ser apresentada como uma exigência individual comprovada do iFood.

### Interrupção e preservação do histórico

Desligar LIVE e POLLING, manter DEV `false` e recriar somente o backend. Isso
interrompe novas tentativas; não cancela o processamento já aceito pelo iFood.
Conferir o Portal e, se ainda necessário, restaurar somente o saldo anunciado
correto desse item após conferir o saldo atual no CorePet. Preços, estoque
físico, lotes, reservas e outros produtos são preservados.

Envio manual e nova conferência do vínculo ficam bloqueados com a automação
ativa. Desligá-la antes de conferir é parte do procedimento. Uma falha incerta
exige leitura do resultado externo, sem repetição cega nem edição direta do
estado para desbloquear o piloto.

Preservar `IfoodStockSyncState`, tentativas e conferências. Não executar
downgrade destrutivo após histórico real: a migração recusa remover a origem se
existir estado ou tentativa automática `ifood_api`. Para voltar código, revisar
a compatibilidade do esquema e seguir o checklist oficial de rollback.
