# Ajustes de estoque, caixa, vendas e entregador — validação local

Data: 2026-10-09.
PR: não aberto; trabalho solicitado somente local.
Commit: esta ficha acompanha o commit da branch abaixo.
Branch: `codex/ajustes-estoque-caixa-vendas-entregador`.
Base: `origin/main` em `5cbd05c18`, conferida no início e no fechamento.
Ambiente: homologação local, `http://127.0.0.1:18080`, com dados fictícios.
Responsável: Codex / Lucas.
Resultado: implementação e testes locais concluídos.
Impacto: novos registros de recebimento passam a identificar o caixa recebedor;
identificações de lotes preservam saldo/custo; alterações de vendas recalculam benefícios.
Próxima ação: revisão de Lucas no ambiente local; publicação depende de pedido específico.

## Uso e comportamento

- **Produto → Movimentações → Lotes e validade:** informar a quantidade atual
  que pertence a um lote e sua validade. Repetir o lote substitui a quantidade,
  sem somar estoque. Quantidades identificadas não podem exceder o saldo, salvo
  correção para baixo de divergência preexistente. Reservas são preservadas.
- **Cadastro/edição do produto → Estoque/Lotes:** o botão
  “Salvar e abrir lançamentos de estoque e lotes” salva e leva às movimentações.
  Mantém as confirmações de alteração dos preços dos produtos compostos.
- **Recebimentos:** pagamentos de vendas anteriores entram no caixa que recebeu
  a parcela; o caixa original conserva o registro da venda. Dinheiro compõe o
  saldo físico; PIX e cartões aparecem no resumo por forma e na auditoria.
  A conclusão de uma baixa parcial não baixa o estoque novamente.
- **Meus Caixas → Auditar:** conferir vendas, pagamentos e lançamentos
  individualmente, filtrar por forma de pagamento e consultar o histórico.
  Alterar a venda invalida sua conferência anterior.
- **Meus Caixas → Reabrir:** informar motivo. O fechamento anterior permanece
  registrado no histórico e será necessário fechar novamente. A reabertura
  física exige que não exista outro caixa ativo no escopo do operador/empresa;
  a auditoria pode ser feita sem fechar o caixa atual.
- **Benefícios:** reabrir suspende cupons elegíveis e revoga o saldo disponível
  de cashback da venda. Ao finalizar novamente, recalcula com os itens/valores
  atuais e a regra original; não duplica o que já foi usado ou expirou.
  Excesso de benefício já consumido fica registrado para análise.
- **Pessoa/entregador → Acerto financeiro → Sem acerto:** permite salvar
  o entregador sem periodicidade e limpa dias anteriormente configurados.
  A opção não impede os lançamentos normais de entrega/comissão.

## Integridade e migrations

Head única: `zzzl20261009a1`.

- `zzzk20261009a1`: adiciona `venda_pagamentos.caixa_id`. O backfill associa
  somente recebimento em loja física cuja data identifica um único caixa do
  mesmo tenant. Intervalos ambíguos ficam sem associação; não se atribui o
  recebimento ao caixa original por suposição.
- `zzzl20261009a1`: adiciona `produto_lotes.apenas_identificacao`, padrão
  falso para lotes existentes. Novas identificações não acionam baixa automática
  por vencimento, não mudam custo e não ativam controle obrigatório de lotes.
  Lotes reais de entrada preservam sua regra anterior.
- Escritores e fechamento compartilham bloqueio da linha do caixa. A devolução
  em dinheiro adota a mesma ordem Caixa → Venda.
- Auditoria do fechamento, reabertura e conferência é gravada na mesma transação
  da alteração, respeitando tenant e acesso individual/compartilhado.

## Diagnóstico da devolução da Loja 1

Inspeção via SSH autorizada no pedido, somente leitura, com transação SQL
explicitamente read-only. Produção estava em `5cbd05c18`.

Na venda `1364727`, os pagamentos registrados eram R$ 38,90 e R$ 56,90 em
cartão de débito. Havia R$ 38,90 recebido e somente R$ 18,00 pendente em contas
a receber. A nova finalização havia abatido o repasse anterior do cartão,
reduzindo indevidamente a nova conta. O bloqueio da devolução também confundia
o repasse pendente da operadora com dívida do cliente.

O código local separa repasse da operadora da baixa de dívida do cliente.
Para permitir devolução de cartão antes do repasse, exige pagamentos válidos
da mesma venda/tenant/forma cobrindo as contas registradas. Crediário pendente,
cartão insuficiente, forma desconhecida e pagamento estornado continuam bloqueados.
Cartões legados sem vínculo com forma de pagamento não são liberados por inferência.

**Os registros dessa venda em produção não foram alterados.** A divergência
histórica deve ser conciliada separadamente antes de considerar o caso encerrado
em produção. Não houve deploy, push ou alteração do banco remoto.

## Evidências de validação

Comandos executados:

- `FLUXO_UNICO.bat check` no início.
- `scripts/homologacao_local.ps1 -Acao subir`: imagens reconstruídas,
  migrations aplicadas e frontend/backend/PostgreSQL saudáveis.
- `python -m pytest` em 27 módulos de regressão relacionados aos ajustes:
  **252 testes distintos passaram**, incluindo migrations e disputas reais de
  recebimento/fechamento/finalização em PostgreSQL local descartável.
  Foram 250 no conjunto inicial e 2 novos após a correção da dupla baixa;
  os 37 testes afetados pela última correção passaram novamente.
- Jornada HTTP local:
  `tests/test_plano_basico_e2e.py`,
  `tests/test_caixa_auditoria_e2e.py` e
  `tests/test_estoque_entregador_local_e2e.py`: **4 passaram**.
  Confirmaram recebimento no novo caixa, preservação do anterior, reabertura,
  conferência invalidada após editar venda, saldo/custo/extrato preservados ao
  identificar lote e cadastro de entregador sem acerto.
- `node --test` nos testes de revisão/contagem/textos do caixa e
  `entregadorAcerto.test.mjs`: **8 passaram**.
- Ruff nos arquivos Python alterados; ESLint sem avisos e Prettier nos arquivos
  JavaScript/JSX alterados; `git diff --check`: passaram.
- `npm run build`, também executado no build Docker do frontend: passou.
  Avisos preexistentes de chunk grande do PDV e variável de Analytics ausente
  na homologação não impediram o build.

Os testes de lote incluem saldo 30 com identificação de 5, consumo clínico e
fracionamento de 8, publicação do produto e preservação do controle de lotes
preexistente. Os testes de benefícios cobrem aumento/redução/remoção, reaberturas
repetidas, devolução posterior, cashback usado/expirado e isolamento por tenant.

Falhas encontradas nas primeiras jornadas foram corrigidas: fixtures compartilhadas
dos testes, preparação de saldo pelo endpoint real de entrada e dupla baixa de
estoque na última parcela. A execução final das quatro jornadas passou.

## Recuperação do Docker local

O Docker Desktop falhava ao renomear o socket antigo do Secrets Engine.
A pasta `%LOCALAPPDATA%/docker-secrets-engine` foi preservada como
`docker-secrets-engine.preservado-20261009-102730`, e uma pasta vazia foi criada
para o Docker iniciar. O Engine voltou a responder e os volumes existentes
foram reutilizados. Nenhum reset de fábrica ou exclusão de volumes foi feito.

A identidade fictícia “CorePet Homologacao Local” estava com trial expirado.
O trial foi renovado somente nesse tenant do banco local, com validação do
ambiente staging e da identidade, para permitir as jornadas de aceite.
