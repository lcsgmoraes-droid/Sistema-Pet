# Tarefas de melhorias operacionais — 26/10/2026

Responsável pelo pedido: Lucas Guerra.

Objetivo: concluir os itens abaixo, validar em DEV e publicar pelo fluxo oficial
somente quando a validação estiver concluída e a autorização de produção estiver
atendida. A sessão do tenant `james_dionizio` foi disponibilizada para consultas;
testes que gravam dados devem acontecer em DEV.

## Como acompanhar

- Marcar `[x]` apenas quando o critério do item estiver atendido e validado.
- Registrar implementação e testes nas evidências, mesmo enquanto o item estiver aberto.
- Manter pendências e limitações explícitas; implementação não equivale a publicação.
- Preservar isolamento entre empresas, autenticação e histórico financeiro.
- Usar componentes V2 e cadastrar novas células reutilizáveis no styleguide.

## Lista de tarefas

- [x] **01 — Editar cliente no PDV.** Botão pequeno junto ao cliente selecionado,
      reutilizando a célula de edição de pessoas. Atualizar os dados exibidos após
      salvar, sem perder a venda em andamento.
- [x] **02 — Melhorar e centralizar a busca.** Células reutilizáveis para pessoas
      e produtos, baseadas no PDV; melhorar a busca durante a digitação e priorizar
      código/nome exatos, prefixos e correspondências mais próximas.
- [x] **03 — Padronizar buscas em todas as telas.** Mapear as buscas de pessoas
      e produtos e adotar as células compartilhadas. Registrar o inventário e as
      migrações para conferir a cobertura tela por tela.
- [x] **04 — Busca no gestor de campanhas.** Aplicar a busca compartilhada,
      priorizando o cliente com código ou nome mais próximo do termo digitado.
- [x] **05 — Códigos visíveis ao usuário.** Exibir o código público de clientes
      e produtos em todas as telas; IDs internos continuam apenas nas referências
      técnicas. Seleção e pesquisa por código validadas. Após a correção publicada
      pelo PR #1570, o modal da conta 11119 foi conferido novamente em produção e
      mostra o código público 1848 de Osvaldo, em vez do ID interno 47644.
- [x] **06 — Célula compartilhada de recebimento.** Reutilizar o recebimento do
      PDV em pagamentos de contas a receber, preservando formas de pagamento,
      valores, parcelas e regras financeiras existentes.
- [x] **07 — Parcelamento na baixa de vendas em aberto.** Permitir receber
      parcelado usando a mesma célula, com consistência entre venda, recebíveis,
      parcelas e caixa.
- [ ] **08 — Histórico rápido e paginado.** Corrigir demora/falha na abertura,
      paginar dados e evitar carregar todo o histórico de uma vez. Caso de consulta:
      Fernanda Pedraza, tenant `james_dionizio`. Aceite reaberto em 27/10/2026 para
      corrigir fechamento duplicado e conteúdo do histórico no PDV; preservar a
      paginação, os filtros e a tentativa de atualização já entregues.
- [x] **09 — Conferir alcance da importação Simplesvet.** Vendas importadas até
      **18/09/2026**, total de 111.266 vendas, primeira em 19/11/2019. Consulta de
      produção somente de leitura confirmada. A data/hora da execução não foi
      comprovada: `created_at` conserva a data original do Simplesvet.
- [x] **10 — Carimbo manual no app.** Causa corrigida em código e produção: o
      acesso foi unificado no cadastro 2061, preservando o carimbo 13739; o handler
      de benefícios passou a retornar um carimbo de meta 12. A conferência no aparelho
      físico da cliente permanece como acompanhamento separado, abaixo.
- [x] **11 — Caixas reabertos simultaneamente.** Permitir reabrir mais de um
      caixa e selecionar em qual caixa registrar cada recebimento, respeitando
      permissões e identificação do operador.
- [x] **12 — Status depois de baixa em lote.** Corrigir títulos pagos que
      permanecem vencidos no contas a receber. Caso de consulta: Osvaldo Cano,
      referência informada 47644 (ID interno confirmado; código público **1848**),
      tenant `james_dionizio`.
- [ ] **13 — Histórico financeiro completo.** Exibir movimentos de todo o fluxo
      de baixa, incluindo data e observação, especialmente nas baixas em lote.
      Preservar rastreabilidade de recebimentos e estornos sem duplicar valores.
      Aceite reaberto em 27/10/2026: data/observação ausentes no PDV e detalhes
      financeiros com IDs tratados como moeda, datas cruas e status pouco claros.
- [x] **14 — Grupos de produtos para comissão.** Em vendas por vendedor,
      melhorar filtros, selecionar múltiplos produtos, salvar grupos reutilizáveis
      para comissão e gerar contas a pagar sem duplicidade.
- [x] **15 — Comissão por valor fixo.** Novo tipo em reais por unidade vendida:
      R$ 5,00 por unidade gera R$ 10,00 ao vender duas. Cadastro, cálculo e exibição
      completos; vale somente para novas vendas, sem recalcular as anteriores.
- [x] **16 — Impedir telefone compartilhado por pessoas diferentes.** Solicitação
      complementar: aplicar a mesma regra entre todas as lojas do grupo, conforme
      confirmação do Lucas. Comparar telefone, celular e contatos adicionais com
      máscara/DDI normalizados; proteger API, importações e gravações concorrentes
      no banco. Preservar legados e aliases fundidos, sem fusão automática.
      Publicado pelo PR #1573 e conferido tecnicamente em produção em 27/10/2026.

## Validação e publicação

- [x] Regras do repositório e estado inicial do Git conferidos.
- [x] `FLUXO_UNICO.bat check` aprovado na abertura da tarefa.
- [x] Sessão Chrome do James identificada pelo perfil, URL e usuário exibido.
- [x] Casos relatados investigados por consulta, sem alterações em produção.
- [x] Testes automatizados focados aprovados por frente.
- [x] Fluxos revisados no ambiente DEV, incluindo isolamento entre empresas.
- [x] Build do frontend e `FLUXO_UNICO.bat release-check` aprovados.
- [x] Mudanças revisadas, commitadas e integradas pelos PRs #1567, #1570 e #1573.
- [x] Publicação pelo fluxo oficial e verificação técnica após publicação.

## Evidências e andamento

Os registros de etapas abaixo preservam o estado observado na ocasião. O estado
atual da entrega está no fechamento confirmado ao final deste documento.

### Abertura — 26/10/2026

- Branch já existente: `feat/20261019-1708-cadastro-e-central-ifood`; mantida
  conforme as regras do projeto. `origin/main` conferida no início.
- Alteração local preexistente em `frontend/tests/e2e/README.md`; preservar e
  separar do escopo desta entrega ao preparar o commit.
- Check inicial: nenhum artefato proibido rastreado e uma única head Alembic.
- Consulta autorizada: Chrome, perfil Atacadao, aba CorePet `/dashboard`,
  usuário James e loja Atacadão Loja 1 Presidente Prudente confirmados.
- Frentes iniciadas em paralelo: busca/PDV; financeiro/caixas;
  histórico/carimbo/importação; comissões/grupos.

## Inventário das buscas e códigos

Mapa de 85 campos/telas e adaptadores em
`docs/INVENTARIO_BUSCAS_PESSOAS_PRODUTOS.md`, incluindo fontes especializadas,
catálogos externos e campos de documentos que não selecionam pessoa/produto.
Os códigos públicos foram auditados também nas APIs de NF, entregas e relatório.

### Validação parcial em DEV — 26/10/2026

- E2E real de navegador: `frontend/tests/e2e/melhorias-operacionais.spec.js`,
  **2 aprovados**. Edição de pessoa pelo PDV preservou produto e valor da venda;
  gestor selecionou cliente pelo código público na célula compartilhada.
- Busca de pessoas/produtos validada também por HTTP local: sem acentos, palavras
  em ordem diferente e código exato no gestor.
- Corrigidas respostas atrasadas de buscas/contexto do cliente e confirmação
  pelo teclado quando uma lista assíncrona fica menor; regressões aprovadas.
- A busca de produto não interpreta texto com letras e números como código
  numérico exato; preservados os códigos de barras e SKUs completos.
- Histórico de Fernanda: consulta em produção reproduziu timeout de 20 segundos
  para o cadastro técnico 43087, código público 2292. Implementação DEV pagina
  em SQL e mantém mensagem de erro com opção de tentar novamente.
- Osvaldo: código público visto na listagem é **1848**. Consulta somente de
  leitura confirmou que **47644**, referência do relato original, é o ID interno.
- Michele: código público **2061**, cadastro técnico 47188; gestor mostra um
  carimbo manual disponível (13739), lançado em 26/10/2026 às 12:29:33 conforme
  a tela. API/cartão mobile sintéticos e atualização ao retornar à tela foram
  testados; vínculo real do app ainda em investigação.
- Estruturas A1/A2/A3 aplicadas apenas no PostgreSQL DEV. Backend DEV não usa
  recarregamento automático: aceites HTTP finais devem ocorrer após reiniciar
  esse container para carregar todas as correções revisadas.
- Lucas confirmou que comissão fixa/grupos devem valer **somente para novas
  vendas**. Não recalcular vendas antigas; valor fixo é por unidade vendida
  (ex.: R$ 5,00 por unidade, duas unidades = R$ 10,00).
- Consulta SSH exclusivamente de leitura autorizada por Lucas nesta conversa
  para conferir importação e vínculo do app do tenant James. Isso não é
  autorização para alterar seus dados operacionais.
- Lucas autorizou em seguida a unificação do cadastro do app **10851** no
  cadastro completo **2061** da Michele, preservando todo o histórico, após os
  testes finais. Procedimento e ensaio em `docs/CORRECAO_VINCULO_APP_CARIMBOS.md`;
  ainda não executado em produção nesta etapa.
- Aceite de comissão fixa/grupo: navegador real comprovou seleção múltipla,
  persistência, R$ 5,00 por unidade, venda anterior preservada, nova venda com
  valor novo e geração de contas sem duplicação. Aceite HTTP de duas baixas
  parciais produziu R$ 0,82 + R$ 0,81 = R$ 1,63; reenvios não duplicaram.
- Aceites financeiros finais ocorreram após reiniciar DEV com a fonte atual:
  cartão em três parcelas, duas vendas no mesmo lote, NSU protegida, taxa única,
  caixa escolhido, nenhum realizado antecipado e previsão sem duplicação.
- Verificação EAS: canal `production` atende runtimes 1.0.3 e 1.0.4, nas duas
  plataformas. Alteração mobile é somente TypeScript (OTA), sem versão,
  dependência nativa, credencial de loja ou novo binário.
- Aceite adicional de navegação: **4/4** em Pessoas por código público, tutor de
  Pet com setas/Enter, fornecedor em nova conta a pagar e produto por SKU em kit.
  Massa e identidade fictícias, sem salvar alteração de kit.
- Ruff aprovado nos 67 arquivos Python alterados e ESLint aprovado nas 152
  fontes JS/JSX alteradas, antes do gate completo.

### Gate e revisão — histórico das etapas de 26/10/2026

- `origin/main` incorporada sem conflitos no commit `297059ce8`, após o
  checkpoint de implementação `ac143f11a`.
- Build frontend de produção aprovado. ESLint e Prettier completos aprovados.
- Regressão iFood/frontend: **324/324**. Regressão operacional/frontend:
  **48/48**. Aceite PDV/gestor repetido: **2/2**, mantendo produto e valor após
  editar a pessoa.
- Gate financeiro: **274 aprovados, 6 pulados**. Atualizados o teste que exigia
  impedir dois caixas reabertos e a fixture que não criava a tabela de fluxo de
  caixa. Mantidas verificações de saldo, auditoria, encargos e rollback do lote.
- Novas regressões de busca, histórico, carimbo, fusão, recebimento e comissão
  incluídas no gate oficial e no CI; teste mobile do carimbo incluído no gate.
- Publicação e correção real da Michele ainda pendentes nesta etapa. Não
  confundir os aceites com dados fictícios com a aplicação em produção.
- Ensaio da fusão repetido em PostgreSQL: **2/2** com e sem colisão de perfil.
  Preservados também IDs, datas de criação, notas e concedentes dos grants;
  conflitos mantêm o registro histórico inativo e o estado anterior na auditoria.
- Regressão frontend de faturamento aprovada: **233/233**.
- Após a revisão final, regressão operacional frontend **51/51** e financeiro
  combinado **301 aprovados, 6 pulados**. Foram corrigidos comissão repetida na
  liquidação de repasse, cartão com prazo zero e metadados de cartão em
  recebimento Pix/dinheiro; **29 testes financeiros focados** aprovados.
- Backend DEV reiniciado com essas fontes. Os três aceites HTTP finais passaram:
  caixas/recebimento, vendas parceladas e comissão por baixas parciais.
- Revisão das fontes especializadas corrigiu elegibilidade SIMPLES/VARIACAO na
  entrada de XML, loading ao limpar busca veterinária e respostas fora de ordem
  em granel/fracionamento. Novas regressões incluídas no gate/CI.
- Migration smoke oficial aprovado no PostgreSQL local: banco limpo, revisão
  histórica e simulação local de tenant UUID chegaram a `zzzzz20261026a3`, com
  RLS validado nos três cenários. Bancos temporários removidos e DEV preservado.
- Gate completo aprovado no commit `c6c2b433c`, incluindo 777 testes de tenant
  aprovados (22 pulados) e 104 testes mobile mais os dois testes do carimbo.
  PR #1567 aberto; teste de validade no CI revelou dependência do fuso da
  fixture. Ajuste determinístico em andamento, sem alterar a regra de produção.
- Revisão adicional encontrou que uma venda antiga ainda aberta adotaria a
  regra de comissão atual ao receber. O item 15 foi reaberto para preservar a
  regra conforme a venda, inclusive nas parcelas posteriores; publicar somente
  depois dessa correção e de repetir o gate.
- A4 concluída e validada em DEV: âncora técnica imutável da venda e versões
  das regras preservam o valor aplicável às parcelas, independentemente da data
  comercial editável. Baseline registra a regra legada conhecida na implantação;
  não reconstrói alterações históricas que o sistema anterior não guardava.
- Aceite real de navegador da vigência **1/1**: venda antiga sem pagamento e
  antiga parcialmente paga mantiveram R$ 3,00 após alteração para R$ 5,00;
  venda anterior à primeira regra continuou sem comissão; venda nova usou
  R$ 5,00. Snapshots anteriores e rateio R$ 0,82 + R$ 0,81 preservados.
- Migration smoke A4 aprovado nos três bancos efêmeros, RLS **3/3** e **12/12**
  aprovações da regressão PostgreSQL. Os bancos temporários foram removidos.
- Teste de validade corrigido para datas fixas: **212/212** no Linux UTC e
  **26/26** seletivos no Windows. Nenhuma regra de estoque foi alterada.
- A revisão concorrente reproduziu uma alteração ainda não commitada sendo
  escolhida depois para uma venda aberta no intervalo. A4 agora ordena a gravação
  da regra e a criação da venda por empresa, mantendo vendas paralelas e outras
  empresas livres. Fusão adquire a proteção antes de bloquear pessoas.
- Validação final dessa proteção: **6/6** cenários PostgreSQL, **18 aprovações**
  nos três bancos do smoke com RLS, **69** regressões de código e E2E **1/1**
  repetido após restart do DEV. Nenhuma contagem operacional foi alterada pela
  atualização do DDL de teste; todos os bancos efêmeros foram removidos.
- Os oito checks oficiais passaram na head `1ea504840`. A análise adicional do
  Sonar apontou uma promessa sem tratamento explícito, execução dinâmica no
  harness mobile e duplicação na base estática de Ajuda. Correções aplicadas sem
  alterar negócios: catch com guarda de desmontagem, compilação de fontes locais
  com whitelist/realpath/imports restritos e artigos estáticos em JSON.
- Comparação do catálogo antes/depois confirmou os dez módulos extraídos e seus
  30 artigos idênticos, incluindo ícones, ordem, títulos, tags e textos. Respostas
  HTTP 400/404/409 documentadas nas rotas novas; testes focados e OpenAPI passaram.
- Sonar aprovado na head `56400ec0a`, duplicação **1,4%**. Gate completo e oito
  checks oficiais aprovados nessa revisão.
- Durante a integração, `main` recebeu o PR #1568 (fiscal Amazon). Resolvidos os
  conflitos preservando a matriz de nove casos de validade e a semântica ARIA do
  modal; códigos públicos e fluxo fiscal revisados sem perda. **106 backend**,
  **21 frontend** e **3/3 E2E** aprovados com a main integrada.
- Criada a união vazia de migrations `zzzzzb20261027a1`, com pais A4 e fiscal
  `zzzzza20261027a1`, sem mudar dados. DEV e três bancos efêmeros chegaram à única
  head; RLS **3/3** e **18** aprovações PostgreSQL. Bancos temporários removidos.

### Publicação principal confirmada em produção — 26/10/2026

- PR **#1567** integrado por squash na `main`, commit
  **`3f2e78f34ecfae558431008832452fa9ad22dfb6`**. O gate completo passou sobre a
  árvore `6dbed4d3`; os **oito checks oficiais** passaram no commit integrado.
  Evidência: `runtime/tarefas-melhorias-20261026/release-gate-main-3f2e78f3.json`.
- Deploy oficial concluído às **22:35:49 BRT**. A revisão servida nessa publicação
  foi `3f2e78f3`, a head do banco era `zzzzzb20261027a1`, os **cinco containers estavam healthy**, o
  health público respondeu corretamente e o watchdog está healthy.
- Backups registrados pelo deploy: banco
  `/opt/petshop/backups/db/petshop_prod_20261026_223444.dump` e operacional
  `/opt/petshop/backups/deploy_20261026_223341`.
- OTA concluída com saída zero no canal `production`, para Android e iOS:
  runtime **1.0.4**, grupo `9e3a71b4-8882-4a7d-a778-0e8fbaffa060`, às
  **22:36:47 BRT**; runtime **1.0.3**, grupo
  `b736b409-f55d-41e7-aad1-348339ee6c99`, às **22:37:02 BRT**. Os dois grupos
  usam o mesmo JavaScript/assets do commit `3f2e78f3`; versões, runtimes e
  configurações dos binários foram preservados. Resumo dos quatro updates em
  `runtime/tarefas-melhorias-20261026/ota-publicacao-resumo.json`.
- Fusão autorizada da Michele concluída às **22:38:01 BRT**, auditoria **227**:
  principal **2061/47188**, duplicado **10851/50401** inativo e apontando ao
  principal. Conta 84 e cargos de `UserTenant` preservados; as **306 vendas**
  conservaram IDs, números, status e totais. Carimbo **13739** preservado; o
  handler `meus_beneficios` passou a retornar **1 carimbo, meta 12**.
- Os seis grants **391–396** foram transferidos ao principal com IDs, datas,
  notas e concedentes intactos. O total final é de **sete perfis**, pois a
  sincronização materializou o perfil `funcionario` da flag legada já existente:
  grant **458**, ator **83**, auditado. Não confundir os seis grants preservados
  com o total de perfis após a operação. Mantidos `is_cliente`, `is_funcionario`
  e crédito zero; conferência posterior somente de leitura aprovada.

### Acompanhamento após a publicação

- [x] Histórico de Fernanda Pedraza consultado em produção somente para leitura:
      abertura em **1.584 ms** (aproximadamente **1,58 s**), página **1/21 → 2/21**.
- [x] Osvaldo Cano: título **11119**, **recebido integralmente**, com saldo
      **zero**. Histórico mostra **26/10/2026** e **“Baixa em lote - pix”**.
      Nenhuma baixa ou outra escrita financeira foi realizada nessa conferência.
- [x] Exibição do código público **1848** corrigida, validada e publicada no modal
      de detalhes dessa conta. A conferência inicial encontrou o ID interno
      **47644**, reabrindo o item 05; após o segundo deploy, nova consulta em
      produção confirmou o código correto, com status e histórico preservados.
- [ ] Conferir o cartão e a atualização dos benefícios no aparelho físico da
      Michele. A correção técnica do vínculo e o saldo em produção já foram validados;
      a conferência humana no aparelho não bloqueia a entrega técnica desse vínculo.

Evidências das consultas em
`runtime/tarefas-melhorias-20261026/fernanda-historico-producao.json` e
`runtime/tarefas-melhorias-20261026/osvaldo-conta-producao.json`. A conferência
final do código está em
`runtime/tarefas-melhorias-20261026/osvaldo-codigo-publico-producao-final.json`
e na captura `.png` de mesmo nome. Os **15 itens técnicos estão concluídos e
publicados**; permanece apenas o acompanhamento humano no aparelho físico.

### Correção dos detalhes de código público — validação local

A consulta de detalhes de contas a receber/pagar passou a retornar o código
público da pessoa. O modal de recebíveis e os dois modais fiscais deixaram de
usar IDs internos como alternativa. O detalhe fiscal Bling também conserva o
código do cadastro local vinculado; sem código, a interface mostra “—”.
Regressões com código público diferente do ID, nulo e ausente passaram:
**33 testes financeiros backend, 10 frontend financeiros, 96 backend fiscais e
6 frontend fiscais**. Ruff, ESLint e Prettier focados passaram. Essa etapa foi
complementada pelo gate completo e pelos checks do PR/main registrados abaixo.

O aceite HTTP em DEV também revelou que detalhes de contas a pagar de comissão
falhavam quando desconto, juros ou multa estavam nulos. A leitura agora devolve
zero nesses três campos opcionais, sem gravar alterações nem recalcular os
valores original, pago, final ou saldo. **36 testes financeiros backend** passaram,
incluindo nulo, zero e valor positivo com conferência dos dados persistidos.

### Publicação corretiva e fechamento técnico — 26/10/2026

- PR **#1570** integrado na `main`, commit
  **`cafeef28f30fc66f812def8def4bce6ae117bdcb`**. O `release-check` completo passou
  com saída zero na head **`c56d227288a09ab1a051ad836ed11014b2792d14`**;
  **12/12 checks do PR**, incluindo Sonar, e **8/8 checks da main** aprovados.
  Evidências: `runtime/tarefas-melhorias-20261026/release-check-codigo-publico-final.log`
  e `runtime/tarefas-melhorias-20261026/release-gate-main-cafeef28.json`.
- Aceites HTTP reais em DEV confirmaram os detalhes de contas a receber e pagar
  com códigos públicos diferentes dos IDs. A conta a pagar de comissão que antes
  respondia HTTP 500 passou a responder **200** com desconto, juros e multa nulos
  apresentados como zero, sem alterar valores financeiros persistidos.
- Segundo deploy oficial concluído às **23:17:21 BRT**, com saída zero. O domínio
  público confirmou a revisão completa **`cafeef28f30fc66f812def8def4bce6ae117bdcb`**;
  **cinco containers healthy**, head **`zzzzzb20261027a1`**, health público correto
  e watchdog healthy.
- Backups dessa publicação: banco
  `/opt/petshop/backups/db/petshop_prod_20261026_231620.dump` e operacional
  `/opt/petshop/backups/deploy_20261026_231327`. Logs em
  `runtime/tarefas-melhorias-20261026/deploy-producao-corretivo.log` e
  `runtime/tarefas-melhorias-20261026/status-producao-final.log`.
- A interface de produção, após recarregamento da sessão James, mostrou
  **Cód. cliente 1848** no modal da conta **11119** de Osvaldo. Permaneceram o
  status **Recebido** e o histórico de **26/10/2026**, **“Baixa em lote - pix”**.
  Evidências JSON e PNG em `runtime/tarefas-melhorias-20261026/osvaldo-codigo-publico-producao-final.*`.

**Decisão: entrega técnica concluída**, com os 15 itens atendidos, validados e
publicados. Os registros anteriores de deploy, OTA e fusão permanecem preservados;
a conferência no aparelho físico da Michele segue como acompanhamento separado.

### Solicitação complementar — telefone único entre lojas, 27/10/2026

O item 16 foi acrescentado após a primeira entrega. A validação antiga apenas
avisava parte das duplicidades e não cobria campos cruzados, DDI, SQL direto ou
concorrência. A implementação usa um normalizador compartilhado, erro 409 textual
e por campo, além de proteção PostgreSQL. Alterações de grupo também não podem
introduzir uma colisão nova entre lojas. Empresas independentes permanecem
separadas; parceiros veterinários não ampliam o escopo de unicidade.

Os testes focados de API/interface passaram. **18 testes PostgreSQL** passaram em
banco descartável local, incluindo concorrência, rollback, RLS com role sem
BYPASSRLS, múltiplos grupos e preservação de legado/fusão. O smoke de migrations
passou nos três cenários, com RLS 3/3 e 24 testes PostgreSQL por cenário (18 de
telefone e 6 de vigência financeira).

O aceite HTTP e os **2/2 fluxos de interface headless em DEV** foram aprovados na
revisão `af83f49ff`; o CRUD de telefone dessa revisão é idêntico ao da fonte final.
Uma pessoa fictícia foi criada, levando a contagem de **40 para 41**. Tentativas
com o mesmo número em telefone/celular e máscara `+55` retornaram **409**, sem
nova linha; editar o próprio número retornou **200**. A interface manteve
**41 → 41**, destacou o campo na aba Contatos e preservou o rascunho, o produto e
o subtotal do PDV, sem salvar venda ou movimentação financeira. Evidências em
`runtime/tarefas-telefone-unico-20261027/aceite-http.json` e `aceite-ui.json`, com
capturas no mesmo diretório.

A revisão final do cadastro público ambíguo passou por **33 testes unitários**:
retorna **409**, sem criar usuário ou executar fusão. O perfil do app também não
funde pessoas automaticamente; variações de DDI podem reutilizar a mesma pessoa.
O gate completo passou na head **`e2ed899d213da5d95d833e248c6ae93e3915484f`**.
O PR **#1573** teve **13/13 checks aprovados**, incluindo Sonar, e foi integrado
por squash na `main` **`833a962d21701b6b2f2766aa84653f3b52fe50b9`**. Na main,
**8/8 checks obrigatórios** e os **nove resultados publicados** ficaram em
`SUCCESS`. Evidências em
`runtime/tarefas-telefone-unico-20261027/release-gate-pr1573-e2ed899d.json` e
`runtime/tarefas-telefone-unico-20261027/release-gate-main-833a962d.json`.

O deploy oficial foi concluído em **27/10/2026 às 00:48:45 BRT**, com saída zero.
A revisão pública confirmou **`833a962d21701b6b2f2766aa84653f3b52fe50b9`**,
**cinco containers healthy**, head **`zzzzzc20261027a1`**, health público correto
e watchdog healthy. Backups: banco
`/opt/petshop/backups/db/petshop_prod_20261027_004747.dump` e operacional
`/opt/petshop/backups/deploy_20261027_004645`. Logs em
`runtime/tarefas-telefone-unico-20261027/deploy-producao.log` e `status-producao.log`.

A conferência de metadados em produção, somente de leitura, confirmou **oito
triggers ativos**, **três índices válidos**, **nove funções privadas sem EXECUTE
público** e **dois wrappers SECURITY DEFINER**, com owner BYPASSRLS e search_path
fixo. A normalização de `+55`, `0055` e DDD `55` foi aprovada com valores
fictícios enviados apenas à função. Nenhuma pessoa fictícia foi cadastrada e
nenhuma fusão foi executada em produção nesta extensão. Evidência em
`runtime/tarefas-telefone-unico-20261027/guard-producao.json`.

**Fechamento da extensão: item 16 concluído e publicado em produção.** Os 16
itens técnicos estão atendidos. Os registros das 15 entregas anteriores, das
OTAs e da fusão autorizada permanecem preservados; a conferência humana no
aparelho físico da Michele continua como acompanhamento separado, ainda pendente.

Detalhes e limites na [ficha de telefone único](entregas/2026-10-27-telefone-unico-pessoas.md).

### Aceite reaberto — históricos e baixas, 27/10/2026

Novos prints enviados pelo Lucas apontam dois ícones de fechar no histórico do
PDV, ausência de data/observação da baixa nesse histórico e detalhes financeiros
que exibem IDs como valores em reais, datas ISO sem apresentação local,
"registrado em" redundante e status confusos. Os itens **08 e 13 estão novamente
abertos**. Os registros anteriores de publicação e seus aceites permanecem como
evidência histórica; não comprovam o novo aceite completo dessas duas telas.

O item 12 mantém a quitação e o saldo já conferidos. A clareza dos status, dos
filtros e de seus respectivos movimentos será revalidada nesta correção; não há
nova comprovação de saldo incorreto nem autorização para refazer baixas reais.

Critérios pendentes:

- [x] Histórico do PDV com um único ícone na ação de fechar, sem perder a venda
      em andamento ao abrir ou fechar a janela.
- [x] Data da baixa, forma, valor e observação visíveis junto ao recebimento
      correspondente; baixa em lote conferida por HTTP e nas telas em DEV.
- [x] Observação da baixa preservada; observação da venda não pode substituí-la.
- [x] Nas duas apresentações financeiras, IDs/referências não aparecem como
      dinheiro; somente valores monetários usam reais com formato brasileiro.
- [x] Datas sem ISO cru ou mudança indevida de dia; a data de negócio fica clara
      e o horário técnico de registro não aparece como informação redundante.
- [ ] Status legíveis e coerentes com o tipo de movimento, saldo e filtros;
      distinguir finalização da venda de recebimento efetivo quando necessário.
- [x] Aceites HTTP e de interface em DEV nas três entradas, com evidências do
      mesmo recebimento, preservação dos valores e nenhuma nova movimentação.
- [ ] Regressões, gate completo, PR e publicação pelo fluxo oficial.

A revisão de código confirmou o armazenamento da observação em lote/recebimento
e sua ausência no resumo de pagamentos do PDV. Confirmou também o uso de
formatação monetária para todo número no renderer genérico financeiro. Esses
achados motivaram a rota paginada `/vendas/{id}/recebimentos-historico`, que usa o
vínculo explícito do lote para recuperar a observação original, e a apresentação
compartilhada por tipo de campo. Venda finalizada e recebimento efetivo passaram
a ter estados separados na resposta e rótulos claros na interface.

O aceite DEV reutilizou a massa fictícia existente: pessoa **10035**, lote **13**,
duas vendas e dois recebimentos. Não foi criada nova massa financeira. Após o
reinício do backend, a rota nova e o financeiro devolveram os mesmos recibos,
data de negócio **26-10-2026**, observação integral e formas/valores preservados.
Os **3/3 fluxos de navegador headless** passaram: histórico do PDV, financeiro
principal e aba Histórico por Cliente da consulta de vendas. O botão superior de
fechar contém um SVG; abrir/fechar preservou cliente, produto e subtotal do PDV.
As referências dos recibos apareceram sem moeda, sem ISO cru e sem "Registrado em".
O filtro "Pago / recebido" da aba encontrou os dois movimentos.

Snapshots de IDs, valores, datas e observações dos recibos permaneceram iguais
antes/depois; contagem de pessoas **41 → 41**, sem POST de venda/financeiro.
Provas e capturas inspecionadas em
`runtime/correcao-historicos-baixas-20261027/aceite-http.json`, `aceite-ui.json` e
`aceite-ui-clone.json`. O caso visual usa lote confirmado; recebimentos parciais,
estornos e navegação com várias páginas ficam nas regressões automatizadas, sem
criar baixas extras apenas para gerar tela. A consolidação final dos filtros de
contas, regressões integradas, gate, CI e publicação permanece pendente.

**Estado atual: aceites DEV aprovados; itens 08 e 13 continuam abertos até o
fechamento das validações e da publicação.**
A conferência humana no aparelho físico da Michele continua separada e pendente.
Detalhes na [ficha da correção dos históricos](entregas/2026-10-27-correcao-historicos-baixas.md).
