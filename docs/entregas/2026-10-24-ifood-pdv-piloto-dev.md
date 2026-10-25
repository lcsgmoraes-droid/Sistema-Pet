# Ponte de pedidos iFood para o PDV — piloto em DEV

## Identificação

| Campo | Valor |
|---|---|
| Título | Importação assistida de um pedido de teste iFood no PDV |
| Data | 2026-10-24 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Issue/PR | PR #1561, branch `codex/ifood-preservar-cadastro-na-pausa` |
| Prioridade | P2 |
| Risco | Alto: reserva, baixa FIFO, pagamentos e isolamento entre empresas |
| Domínios afetados | Integração iFood, PDV, vendas, estoque e caixa |

## 1. Necessidade e requisitos

Permitir testar a entrada de um pedido iFood no PDV, sem operar a loja real ou
outros produtos. O usuário autorizado importa explicitamente um pedido já
armazenado, confere a reserva e finaliza a venda. No pagamento online iFood,
a conclusao tem acao propria, sem repetir a cobranca no PDV.

O aceite técnico exige uma venda, uma reserva e uma baixa FIFO para uma unidade
do SKU `018631.1`, sem duplicação por reenvio ou concorrência. Cancelar antes da
finalização deve liberar apenas a reserva. A interface identifica o canal iFood
e preserva os itens, valores e a modalidade recebidos do provedor.

Devem permanecer os fluxos de app, ecommerce, WhatsApp e loja física. Ficam fora
do escopo produção, publicação de outros produtos, operação contínua, pagamentos
mistos, outros meios não autorizados, descontos, cupons, pesagem variável e
conciliação Financial. O ensaio sintético não substitui o aceite de um pedido
oficial da loja de testes.

## 2. Regras de negócio e dados

O piloto fica desligado por padrão e exige DEV, tenant, loja de testes, pedido
exato e SKU autorizados. O payload precisa declarar `test=true`, um item de uma
unidade fixa, EAN correspondente e preço positivo. São aceitos retirada ou
entrega com frete explícito não negativo, sem descontos ou cupons. O offline
exige dinheiro presencial no total exato, sem taxas adicionais. O online exige
um crédito sob responsabilidade do iFood, referência válida e evento oficial
recebido; admite apenas serviço cobrado do consumidor e pertencente ao iFood.
Frete online positivo exige responsabilidade `MERCHANT` comprovada. O resumo
separa R$ 65,00 do item + R$ 8,90 de frete = R$ 73,90 operacionais dos R$ 1,99 de
serviço do iFood e R$ 75,89 do consumidor. Condições desconhecidas ou divergentes
impedem a importação/finalização.

`IfoodOrder` mantém a origem; `ifood_pdv_bridges` liga pedido, produto, venda e
reserva. A reserva usa `PedidoIntegradoItem`, sem inventar um ID Bling. A venda
permanece aberta até a finalização explícita. Baixa FIFO e encerramento da
reserva pertencem à mesma transação; unicidade, bloqueios e validação da sacola
protegem contra duplicação e alteração posterior da origem. O hash da evidência
inclui frete, serviço, totais e pagamento; a reserva e a baixa FIFO continuam
limitadas a uma unidade do produto, independentemente do valor do frete.

A migration `zzzzt20261024a1`, filha de `zzzzs20261023a1`, cria a ponte com
unicidade, chaves estrangeiras compostas por tenant e RLS, e permite
`pedido_bling_id=NULL`. Preserva histórico, usuário da ação e evidência da sacola,
incluindo a evidência financeira online em JSON na ponte.
Não cria cadastro de cliente a partir do consumidor de teste.

## 3. Arquitetura e integrações

`POST /integracoes/ifood/pedidos/{order_id}/piloto-pdv/importar` importa o pedido
local. Consultas retornam `pdv_bridge` com elegibilidade, estado, venda, reserva e
baixa. A ação usa componentes V2 e abre a venda existente pelo vínculo do painel.
Importar localmente não depende de habilitar operações externas nem faz ACK,
Picking, entrega ou envio ao Bling.

O online conclui por
`POST /integracoes/ifood/pedidos/{order_id}/piloto-pdv/finalizar-online`, sem
pagamentos novos enviados pela UI. A capacidade `can_finalize_online` controla
o botão V2 na Central e no PDV. O servidor revalida a evidência e registra uma
quitação externa `iFood online`, sem movimento de caixa ou conta global dada
como recebida. A evidência JSON da ponte mantém o repasse aguardando Financial,
recebido zero, líquido/data desconhecidos e margem pendente. O marcador
`Venda.ifood_pdv_pilot` bloqueia a modal de cobrança no online ou modo
desconhecido; somente offline habilitado conserva dinheiro presencial.

Os hooks do PDV usam o vínculo validado para finalizar/cancelar. Entrega conserva
`tem_entrega=True` e aparece como **Entrega acompanhada pelo iFood**, sem
entregador local fictício. Edição, reabertura, devolução e ações locais de entrega
ficam bloqueadas; benefícios de outros canais não são herdados. A finalização
iFood não dispara emissão fiscal automática; emissão manual mantém suas regras.

Reimportação retorna o vínculo existente. Mudança da sacola ou evento remoto
recebido/registrado que invalide o pedido bloqueia a finalização até revisão. O
piloto não inventa estado externo quando o iFood está indisponível: a importação
do espelho local e as operações externas permanecem separadas. Não há novo retry
automático de venda nem estorno retroativo automático por evento remoto.

## 4. Segurança e privacidade

As rotas exigem autenticação e permissões de integração/venda na empresa. As
guardas validam o tenant antes de agir e recusam produção/staging mesmo que a
flag do piloto seja ligada. Pedidos, produtos ou vínculos de outra empresa não
podem ser usados para importar, finalizar, editar ou contornar as restrições.

Credenciais devem pertencer exclusivamente ao aplicativo de testes, em
configuração protegida e nunca versionada. Não registrar tokens, segredos ou
payloads com dados pessoais desnecessários em logs/evidências. A finalidade do
consumidor fictício é homologação; o espelho e a ponte preservam somente o
histórico operacional já previsto pela integração. A validação inclui cenários
de permissão, isolamento, bypass de rotas e RLS real no PostgreSQL.

## 5. Desenvolvimento e qualidade

Fatias: contrato e persistência da ponte; importação/reserva; hooks transacionais
de finalização/cancelamento; canal e interface V2; guardas contra bypass; testes
de banco e ensaio local pela interface.

Validações executadas nesta tarefa:

- `npm run test:ifood`, lint, formatação e build do frontend: aprovados; cobertura
  de canal, importação local com operações externas desligadas, entrega sem
  entregador fictício, ausência de PUT pré-pagamento e bloqueio de emissão fiscal
  automática, preservando os demais canais.
- Testes backend do piloto, permissões e bypasses: aprovados para escopo DEV,
  tenant/SKU/pedido, condições comerciais, importação repetida, cancelamento,
  finalização e tentativas de edição/devolução/exclusão de pagamento.
- `python -m pytest tests/integration/test_ifood_pdv_pilot_postgres.py -q`:
  aprovado em PostgreSQL local dedicado, incluindo concorrência entre conexões,
  RLS, chaves compostas, sacola alterada e baixa FIFO única.
- `FLUXO_UNICO.bat release-check`: entrada oficial com Git limpo e gate completo
  aprovados na fonte `cc4a9ae13`, incluindo o online: 693 testes backend iFood,
  267 frontend e 32 cenários PostgreSQL aprovados, além das demais validações do
  gate. O delta visual `797d4a4ba` passou com 272 testes frontend, lint, formatação
  e build. Inclui totais do consumidor separados, cabeçalho sem cobrança manual
  e recarga da venda pelo ID após concluir, testada com o carregador real do PDV.
  O CI remoto do commit final do PR #1561 continua uma conferência separada.

O schema descartável do ensaio PostgreSQL não comprova a execução de toda a
cadeia histórica do Alembic. A migration nova e suas restrições foram exercidas;
a cadeia/compatibilidade precisa permanecer no gate de release.

## 6. Ambientes e homologação

Validação em DEV local isolado, com empresa fictícia, produto de teste e banco
descartável/dedicado. Produção e os demais produtos não fizeram parte do ensaio.

Configuração padrão: `IFOOD_PDV_PILOT_ENABLED=false`; tenant, merchant, pedido e
SKU vazios. Durante a janela assistida, configurar somente os identificadores
autorizados e `IFOOD_PDV_PILOT_SKU=018631.1`. Catálogo, operações de pedidos e
polling têm flags independentes; nenhuma delas é liberada por esta ficha.

Registro de homologação proporcional ao piloto: notas de validação e roteiro no
[guia do usuário](../GUIA_INTEGRACAO_IFOOD.md#pedido-de-teste-no-pdv--somente-dev)
e no [contrato da fase 2](../INTEGRACAO_IFOOD_FASE2_PEDIDOS.md#piloto-assistido-de-pdv-em-dev).
Evidências locais não versionadas ficam em `ifood-pedidos-dev-2026-10-24`,
incluindo `release-validation-official-final.json`; não contêm autorização de produção
e não substituem os resultados finais do PR.

O ensaio **sintético pela interface passou**: estoque físico de 31 para 30,
reservas de 4 para 3, disponível 27, um pagamento, um movimento e lote FIFO de
10 para 9. Reimportação não duplicou a venda/reserva/baixa.

O pedido **oficial de testes #1420 passou no fluxo assistido em DEV**. Confirmado
pela interface do iFood às 20h43, gerou três eventos recebidos, três ACKs e zero
falhas no CorePet. A importação pela UI criou somente a venda `202610240002`
(ID 2) e uma reserva de uma unidade. A conclusão no PDV fez uma baixa FIFO:
físico 30 para 29, reservas 4 para 3, disponível 26 e primeiro lote 9 para 8.

O checkout do consumidor foi R$ 75,89, composto por produto de R$ 65,00, frete de
R$ 8,90 e serviço exclusivo do iFood de R$ 1,99. A venda e seu único pagamento
externo `iFood online` ficaram em R$ 73,90, sem caixa associado. A evidência JSON
do recebível ficou `awaiting_financial`, bruto R$ 73,90, recebido zero,
líquido/vencimento nulos e margem pendente. Os hashes das 12 tabelas financeiras
de controle permaneceram iguais; o caixa preservou somente os R$ 65,00 da venda
sintética anterior. O pedido oficial não criou entrada nova de caixa.

Reimportar e repetir a conclusão pela API não alterou venda, reserva, pagamento
ou estoque. A evidência local `official1420-finalization-proof.json` registrou
PASS. Outras empresas, produtos e preços do ERP/app/ecommerce foram preservados;
produção permaneceu intacta. Esse aceite não comprova recebimento do repasse,
margem final ou validade dos relatórios gerais para ampliar o piloto.

## 7. Publicação e rollback

Entrega backend/frontend, migration e documentação; não há alteração mobile.
Fonte identificável pela branch indicada: gate do online em `cc4a9ae13` e delta
visual em `797d4a4ba`. O PR deve registrar o commit final e seu CI.

Somente após autorização específica para o ambiente: aplicar a migration antes
de iniciar o backend novo, manter flags desligadas, conferir saúde e consultar
pedidos sem importar. Habilitar o piloto apenas no DEV isolado e na janela
assistida. Esta ficha **não autoriza deploy nem habilitação em produção**.

Abortar diante de divergência de tenant/pedido/sacola, duplicação, reserva sem
venda correspondente, baixa indevida, erro de migration ou regressão em outro
canal. Desligar `IFOOD_PDV_PILOT_ENABLED` impede novos usos, mas não desfaz dados
já criados. Antes de reverter código/imagens, conferir vendas/reservas existentes
e encerrar ou cancelar explicitamente pelo fluxo compatível, preservando a
auditoria. Não corrigir saldo por entrada/saída manual para simular rollback.

A estrutura aditiva pode permanecer sem uso. O downgrade **recusa apagar dados**
se houver pontes ou pedidos com `pedido_bling_id` nulo; não forçar a remoção,
fabricar IDs Bling ou apagar evidências para contornar essa proteção. Qualquer
tratamento de dados existentes exige análise e plano específico.

## 8. Observabilidade e sustentação

O painel deve mostrar vínculo da venda, reserva, baixa confirmada ou motivo do
bloqueio. Sucesso exige contagens e saldo coerentes no banco, não apenas um selo
visual ou HTTP 202. Reenvio, evento remoto e sacola alterada precisam preservar a
evidência e explicar a impossibilidade de continuar.

Após o pedido oficial, a proteção dos relatórios foi adicionada em DEV: vendas
iFood permanecem `pending_ifood_financial`, com taxas desconhecidas, líquido após
despesas, lucro e margens nulos. Isso também protege snapshots antigos e o
reprocessamento, sem recalcular os custos congelados durante uma leitura.
Relatório de vendas, dashboard, DRE, ponto de equilíbrio, rankings/IA e suas
exportações não transformam a pendência em zero. Totais mistos também ficam
pendentes, preservando faturamento, quantidades e custos conhecidos. O canal
iFood possui identificação própria na lista e na DRE.

Na API do perfil Gestor, resultados desconhecidos ficam nulos e a DRE fica
indisponível com aviso específico, pois clientes mobile instalados ainda não
possuem apresentação de pendências. Nenhum código/binário mobile foi publicado.

A validação real local consultou os dois pedidos já existentes, incluindo o
oficial #1420, sem criar vendas, pagamentos ou movimentos. Resultado: receita
operacional R$ 138,90, produtos R$ 130,00, CMV conhecido R$ 87,88 e duas vendas
com margem pendente. PDF e Excel gerados pela API continham “Pendente iFood”.
O segundo tenant permaneceu sem vendas e sem pendências. A conferência visual
incluiu lista, alternância de impostos, DRE e simulador do ponto de equilíbrio.
Os testes novos integram os gates de CI e release; resultados finais devem ser
conferidos na revisão do PR. Evidência local: `pending-reports-api-proof.json`.

Essa proteção resolve a apresentação de lucro indevido por taxas ausentes;
não conclui a conciliação Financial. Taxa de pagamento preenchida, inclusive
zero, pagamento online e previsão contratual não comprovam todas as cobranças.
O extrato de homologação ainda não publica um fechamento canônico na
rentabilidade geral da Venda; até esse vínculo ser implementado e validado,
nenhum valor isolado libera a margem final iFood. Não usar esse aceite para
ampliar automaticamente o piloto ou habilitar produção.

Falhas previstas: loja de testes não configurada, acesso do consumidor
indisponível, pedido fora da allowlist, condição comercial não suportada e falha
de concorrência/rede. Manter o piloto desligado e usar consulta somente leitura
como alternativa segura. Divergência de saldo ou acesso entre empresas exige
interromper o piloto e investigar antes de tentar novamente. Recorrência dessas
falhas deve virar correção estrutural, sem ampliar automaticamente o escopo.

## 9. Mudança, comunicação e treinamento

O usuário passa a enviar explicitamente um pedido de teste ao PDV, conferir seu
vínculo e finalizar/cancelar com os limites descritos. O canal iFood não permite
recompor itens/valores nem operar entrega local no lugar do provedor.

Guia e fase 2 foram atualizados com o roteiro e o resultado oficial de DEV. A
equipe de implantação e Lucas devem preservar essa conferência de saldo/reserva
e lotes nos próximos ensaios. A comunicação de uso amplo depende de avaliação
das pendências e aprovação posterior de publicação; não anunciar a ponte como
operação de produção pronta.

## 10. Fechamento

- [x] Critérios técnicos do ensaio sintético atendidos e limitações registradas.
- [x] Pedido oficial recebido e fluxo específico de PDV/reserva/baixa homologado em DEV.
- [x] Testes e evidências técnicas registrados.
- [x] Tenant, permissões, integridade e auditoria avaliados.
- [x] Documentação de uso e contrato atualizados.
- [x] Homologações sintética e oficial de DEV registradas separadamente.
- [x] Publicação, observabilidade e rollback definidos para o piloto.
- [x] Comunicação e treinamento avaliados.
- [x] Gate do online e validação do delta visual registrados.
- [ ] CI remoto do commit final do PR confirmado.
- [ ] Financial e relatórios gerais com margem pendente homologados para expansão.

Decisão técnica: **aprovado para o fluxo oficial específico de pedido, PDV,
reserva e baixa em DEV, com pendências de Financial e relatórios gerais**.
Não é aceite de operação contínua ou de produção.

Pendências: Codex e Lucas devem validar a conciliação Financial e o tratamento de
margem pendente nos relatórios gerais antes de ampliar o piloto. O responsável
pelo PR deve confirmar o CI do commit final antes da conclusão da revisão.
Não há prazo de liberação de produção definido nesta entrega.
