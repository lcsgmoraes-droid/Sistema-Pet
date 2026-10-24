# Ponte de pedidos iFood para o PDV — piloto em DEV

## Identificação

| Campo | Valor |
|---|---|
| Título | Importação assistida de um pedido de teste iFood no PDV |
| Data | 2026-10-24 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Issue/PR | PR da branch `codex/ifood-preservar-cadastro-na-pausa`; número a registrar na abertura |
| Prioridade | P2 |
| Risco | Alto: reserva, baixa FIFO, pagamentos e isolamento entre empresas |
| Domínios afetados | Integração iFood, PDV, vendas, estoque e caixa |

## 1. Necessidade e requisitos

Permitir testar a entrada de um pedido iFood no PDV, sem operar a loja real ou
outros produtos. O usuário autorizado importa explicitamente um pedido já
armazenado, confere a reserva e finaliza a venda pelo fluxo normal do PDV.

O aceite técnico exige uma venda, uma reserva e uma baixa FIFO para uma unidade
do SKU `018631.1`, sem duplicação por reenvio ou concorrência. Cancelar antes da
finalização deve liberar apenas a reserva. A interface identifica o canal iFood
e preserva os itens, valores e a modalidade recebidos do provedor.

Devem permanecer os fluxos de app, ecommerce, WhatsApp e loja física. Ficam fora
do escopo produção, publicação de outros produtos, operação contínua, pagamentos
online/mistos, descontos, cupons, pesagem variável e conciliação Financial. O
ensaio sintético não substitui o aceite de um pedido oficial da loja de testes.

## 2. Regras de negócio e dados

O piloto fica desligado por padrão e exige DEV, tenant, loja de testes, pedido
exato e SKU autorizados. O payload precisa declarar `test=true`, um item de uma
unidade fixa, EAN correspondente, preço positivo e dinheiro presencial. São
aceitos retirada ou entrega com frete e taxas adicionais comprovados como zero.
Condições desconhecidas ou divergentes impedem a importação/finalização.

`IfoodOrder` mantém a origem; `ifood_pdv_bridges` liga pedido, produto, venda e
reserva. A reserva usa `PedidoIntegradoItem`, sem inventar um ID Bling. A venda
permanece aberta até a finalização explícita. Baixa FIFO e encerramento da
reserva pertencem à mesma transação; unicidade, bloqueios e validação da sacola
protegem contra duplicação e alteração posterior da origem.

A migration `zzzzt20261024a1`, filha de `zzzzs20261023a1`, cria a ponte com
unicidade, chaves estrangeiras compostas por tenant e RLS, e permite
`pedido_bling_id=NULL`. Preserva histórico, usuário da ação e evidência da sacola.
Não cria cadastro de cliente a partir do consumidor de teste.

## 3. Arquitetura e integrações

`POST /integracoes/ifood/pedidos/{order_id}/piloto-pdv/importar` importa o pedido
local. Consultas retornam `pdv_bridge` com elegibilidade, estado, venda, reserva e
baixa. A ação usa componentes V2 e abre a venda existente pelo vínculo do painel.
Importar localmente não depende de habilitar operações externas nem faz ACK,
Picking, entrega ou envio ao Bling.

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
  aprovados na fonte final `ae3356755`, já integrada à base atual. Foram aprovados
  632 testes backend iFood, 248 frontend, 769 multiempresa e as demais suítes,
  builds e auditorias. Os 15 cenários PostgreSQL passaram juntos nessa fonte.
  O CI remoto do PR ainda precisa ser conferido.

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

O pedido **oficial permanece pendente**. Após identificar a loja de testes já
configurada pelo suporte, apenas o SKU `018631.1` foi enviado e aceito com HTTP
202. Isso não comprova disponibilidade para compra nem recebimento de pedido;
falta concluir o acesso do consumidor e gerar o pedido oficial.

## 7. Publicação e rollback

Entrega backend/frontend, migration e documentação; não há alteração mobile.
Fonte identificável pela branch indicada; referência do ensaio PostgreSQL:
`ae3356755`. O PR deve registrar o commit final e seu CI.

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

Guia e fase 2 foram atualizados com o roteiro. A equipe de implantação e Lucas
devem conferir estoque/reservas/lotes antes e depois do ensaio oficial. A
comunicação aos usuários finais depende da homologação oficial e de aprovação
posterior de publicação; não anunciar a ponte como operação de produção pronta.

## 10. Fechamento

- [x] Critérios técnicos do ensaio sintético atendidos e limitações registradas.
- [x] Testes e evidências técnicas registrados.
- [x] Tenant, permissões, integridade e auditoria avaliados.
- [x] Documentação de uso e contrato atualizados.
- [x] Homologação local registrada; homologação oficial pendente explicitada.
- [x] Publicação, observabilidade e rollback definidos para o piloto.
- [x] Comunicação e treinamento avaliados.
- [ ] Revalidação final/CI do commit do PR confirmados.
- [ ] Pedido oficial recebido e jornada completa homologada no DEV.

Decisão técnica: **aprovado com pendências para revisão do piloto DEV**. Não é
aceite de operação contínua, de pedido oficial concluído ou de produção.

Pendências: Codex e Lucas devem concluir o pedido oficial assim que o acesso à
loja de testes pelo consumidor estiver disponível e registrar a evidência. O
responsável pelo PR deve confirmar o gate/CI final antes da conclusão da revisão.
Não há prazo de liberação de produção definido nesta entrega.
