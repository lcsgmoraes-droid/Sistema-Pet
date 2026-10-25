# Estoque automático iFood — SKU 227 em DEV

## Escopo e resultado

Preparação da rotina automática de estoque para um único produto já vinculado.
O piloto é independente da ponte de pedidos do SKU 018631.1 e permanece
desligado por padrão. Nenhum envio externo, anúncio ou deploy de produção
integra esta entrega.

A rotina observa o saldo confirmado no banco, desconta reservas e segurança,
respeita a pausa local e agrupa mudanças próximas. Cada tentativa persistida
contém somente EAN e estoque absoluto. Preço, promoção, conteúdo e ativação
do anúncio não fazem parte do PATCH.

## Proteções

- Allowlist exata de empresa, loja, produto, SKU 227 e EAN; vínculo existente
  e saldo inicial conferido com presença e atividade declaradas.
- Ambiente DEV e provedor falso em HTTP loopback obrigatórios. Produção,
  staging, URL externa e proxy de ambiente não são aceitos pelo worker.
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

## Limite e próximo passo

O produto sintético deste ensaio não possui lotes. O cancelamento genérico
existente devolve o saldo agregado, mas não recompõe os lotes consumidos.
Este trabalho não altera esse serviço para os demais produtos e não valida
FIFO genérico; a correção anterior de FIFO continua restrita ao piloto de
pedidos 018631.1 em DEV.

Antes de uma liberação real para o SKU 227, resolver e validar o cenário com
lotes, definir a política de volumetria da loja e autorizar separadamente
o provedor real. Depois executar o piloto assistido e conferir o Portal.
O sucesso deste ensaio não equivale a sincronização contínua homologada em
produção. O guia de implantação contém o roteiro para treinamento.

Rollback operacional em DEV: desligar as duas flags e parar o worker de ensaio.
Isso preserva tentativas e saldos; não executar downgrade destrutivo com
histórico existente. Produção permanece sem ativação desta rotina.
