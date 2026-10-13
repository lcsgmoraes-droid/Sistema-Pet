# PDV: descontos por origem e endereço nas sugestões

Data: 09/10/2026. Branch: `codex/ajustes-estoque-caixa-vendas-entregador`.
Ambiente de aceite: `http://127.0.0.1:18080`, empresa fictícia CorePet Homologacao Local.
Trabalho solicitado somente local, sem push ou deploy.
Resultado: implementação e aceite local concluídos. `origin/main` conferida
no início e no fechamento, em `5cbd05c1857caea8afa6040fb939700378de7425`.

## Comportamento

- Desconto do produto é gravado no próprio `VendaItem.desconto_item`. Não é
  distribuído aos outros produtos. Dois produtos de R$ 100, com desconto de
  R$ 20 somente em A, resultam em A R$ 80 e B R$ 100, inclusive na lista
  financeira e na prévia de devolução.
- Desconto manual da venda e campanha/cupom têm origens separadas. No PDV,
  pagamento e recibo aparecem os descontos dos produtos, da venda e de
  campanha/cupom. No financeiro, desconto manual e campanha/cupom têm colunas
  distintas. Somente desconto geral e campanha/cupom são distribuídos às linhas.
- Quantidade, preço e desconto do item podem mudar sem apagar os demais
  descontos. Cupom percentual acompanha a base após os descontos manuais e
  exclui frete. Remover/reaplicar cupom preserva o desconto manual, e vice-versa.
- Durante a edição, desconto percentual do produto acompanha a quantidade
  mesmo depois de salvar uma alteração com saldo pendente.
- Configurações → Parâmetros Gerais → Busca de clientes no PDV →
  **Mostrar endereço nas sugestões de clientes**. Padrão desativado por empresa.
  Quando ativado, mantém o telefone e acrescenta o endereço disponível; cliente
  sem endereço continua com a sugestão normal.

## Integridade

Migration `zzzn20261009a1`, acima de `zzzm20261009a1`, aplicada na homologação:

- `vendas.desconto_venda_valor`: numérico, nullable. `NULL` identifica vendas
  antigas cuja origem dos descontos não foi registrada separadamente.
- `empresa_config_geral.mostrar_endereco_cliente_pdv`: booleano, padrão falso.

O servidor recalcula os totais modernos com os valores normalizados que serão
persistidos: dinheiro em centavos e quantidade em três casas. Não confia no
subtotal/agregado enviado pelo navegador. Análise de pagamento, rentabilidade,
comissões, devoluções e integrações fiscais usam a mesma composição.

Vendas antigas conservam linhas, total, recebimentos e snapshots históricos.
Não há conversão ou reprocessamento automático do histórico. Alterar explicitamente
o desconto geral/cupom de uma venda antiga pede revisão dos descontos de produto
antes da conversão; simples consulta ou refinalização conserva o contrato antigo.

## Evidências já verificadas

- Jornada HTTP de desconto por produto, três origens, cupom percentual com frete,
  precisão decimal, venda legada, configuração/endereço e fechamento de venda
  reaberta paga: **sete testes passaram** na imagem final do backend.
- Interface: venda `202610090032` exibiu desconto manual de R$ 20 somente no
  produto A; B ficou sem desconto. Venda `202610090029` manteve descontos
  produto R$ 20, venda R$ 10 e cupom R$ 5 nas alterações de quantidade/preço e
  na remoção/reaplicação independente de descontos.
- Interface: ativar a configuração, salvar e recarregar preservou o checkbox.
  Cliente fictício com endereço passou a mostrá-lo junto ao telefone; cliente
  sem endereço permaneceu sem linha vazia.

Evidências visuais ficam na pasta de visualizações desta conversa, fora do Git:
`financeiro-desconto-por-produto.png`, `pdv-descontos-separados.png` e
`pdv-endereco-sugestao.png`.

## Regressão descoberta durante o aceite

O antigo botão Salvar de uma venda reaberta paga usava PUT seguido de PATCH
de status. A venda ficava finalizada sem consumir o cupom ou restabelecer os
benefícios. O fechamento agora usa o orquestrador normal com pagamentos vazios,
preservando os recebimentos já registrados e consumindo o cupom novamente.
PUT e exclusão de pagamento mantêm a venda aberta; somente finalizar executa
o fechamento. PATCH para finalizada usa o mesmo orquestrador para compatibilidade
com cancelar edição, conserva a opção de não gerar benefícios e é idempotente
quando a venda já está finalizada.

Cancelar edição conserva tela e referência quando a restauração falha. A
referência contém também o ID da venda, impedindo restaurar o status de outra.
Salvar com saldo pendente conserva a edição e atualiza os itens persistidos,
inclusive IDs novos de linhas cuja quantidade foi alterada.

O PUT devolve o vínculo transitório `item_id_anterior` apenas para itens cuja
identidade foi validada. O navegador mantém a preferência percentual por esse
vínculo ou pelo ID atual, somente quando o percentual reproduz o desconto
monetário persistido. Não associa produtos por SKU ou posição. O GET não inclui
esse vínculo transitório e nenhuma informação financeira adicional foi gravada.

Aceite HTTP final da venda fictícia `202610090048` / ID 53, com vendedor e cupom:
R$ 45 → 25 → 65 → 45; cashback R$ 4,50 → 2,50 → 6,50 → 4,50; carimbos
4 → 2 → 6 → 4. Recebimentos ficaram exatamente R$ 45 + R$ 20. A conclusão
via PATCH repetido não duplicou pagamentos, caixa ou benefícios; o estoque
final permaneceu 17. Regras temporárias das campanhas foram restauradas.

Aceite pela interface na venda `202610090029` / ID 34, sem recarregar entre
salvamentos: edição pendente R$ 265 → 365 → 165, seguida de fechamento sem novo
pagamento. Em seguida, desconto de produto de 10%: R$ 175 → 265 → 355, com
descontos R$ 10 → 20 → 30, todos salvos com saldo pendente. Restaurar o desconto
original de R$ 20 e uma unidade concluiu a venda em R$ 165. O banco confirmou
somente o pagamento PIX ID 43, de R$ 165, no caixa ID 7, com a data original
`2026-10-09T12:46:19.791158`; ambos os produtos ficaram com estoque 19. A tela
mostrou três carimbos e o cupom de recompra original após a conclusão.

Cancelar edição com restauração recusada manteve a tela e permitiu nova tentativa.
Cancelar uma reabertura sem alterações restaurou o fechamento e os benefícios.

## Verificações de código

- Conjunto final de 25 módulos Python: **235 testes passaram e um foi pulado**.
  Inclui descontos, rentabilidade, comissão, devolução, pagamento, DRE,
  integrações fiscais, fechamento, cashback, identidade/custo dos itens e
  configuração de endereço. O teste de concorrência pulado requer
  `TEST_RECEBIVEIS_POSTGRES_URL`; as jornadas HTTP usaram PostgreSQL real local.
- Sete módulos Node: **57 testes passaram**, incluindo totais, recibo,
  payload, salvamento/cancelamento da edição, percentual e endereço.
- Jornada HTTP final após reconstrução: **7 testes passaram em 45,43 segundos**.
  Vendas fictícias IDs 48 a 53; configuração restaurada ao valor anterior.
- Ruff nos arquivos Python alterados, ESLint sem avisos, Prettier,
  `git diff --check` e build frontend/Docker passaram.
- Backend, frontend e PostgreSQL locais saudáveis. Migration na head única
  `zzzn20261009a1`. As 184 alterações preexistentes do checkout original foram
  preservadas.

## Limitações preexistentes fora destes ajustes

Excluir um pagamento ainda remove todas as contas a receber vinculadas à
venda; não existe vínculo individual suficiente nessa rota para conciliar
somente a conta correspondente. Essa conciliação não foi alterada nesta tarefa.

Na execução ampliada anterior houve uma falha preexistente em
`test_business_audit_service.py::test_build_user_access_metadata_normalizes_actor_target_and_role`:
o teste não inclui os campos `actor_username`/`target_username` que o código
retorna com valor `None`. Esses arquivos não foram alterados nesta tarefa.
