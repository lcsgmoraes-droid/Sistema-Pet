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
  técnicas. Conferir também seleção e pesquisa por código.
- [x] **06 — Célula compartilhada de recebimento.** Reutilizar o recebimento do
  PDV em pagamentos de contas a receber, preservando formas de pagamento,
  valores, parcelas e regras financeiras existentes.
- [x] **07 — Parcelamento na baixa de vendas em aberto.** Permitir receber
  parcelado usando a mesma célula, com consistência entre venda, recebíveis,
  parcelas e caixa.
- [x] **08 — Histórico rápido e paginado.** Corrigir demora/falha na abertura,
  paginar dados e evitar carregar todo o histórico de uma vez. Caso de consulta:
  Fernanda Pedraza, tenant `james_dionizio`.
- [x] **09 — Conferir alcance da importação Simplesvet.** Vendas importadas até
  **18/09/2026**, total de 111.266 vendas, primeira em 19/11/2019. Consulta de
  produção somente de leitura confirmada. A data/hora da execução não foi
  comprovada: `created_at` conserva a data original do Simplesvet.
- [ ] **10 — Carimbo manual no app.** Investigar e corrigir por que o carimbo
  manual de Michele Pelegrino, tenant `james_dionizio`, não apareceu no aplicativo.
- [x] **11 — Caixas reabertos simultaneamente.** Permitir reabrir mais de um
  caixa e selecionar em qual caixa registrar cada recebimento, respeitando
  permissões e identificação do operador.
- [x] **12 — Status depois de baixa em lote.** Corrigir títulos pagos que
  permanecem vencidos no contas a receber. Caso de consulta: Osvaldo Cano,
  referência informada 47644 (ID interno confirmado; código público **1848**),
  tenant `james_dionizio`.
- [x] **13 — Histórico financeiro completo.** Exibir movimentos de todo o fluxo
  de baixa, incluindo data e observação, especialmente nas baixas em lote.
  Preservar rastreabilidade de recebimentos e estornos sem duplicar valores.
- [x] **14 — Grupos de produtos para comissão.** Em vendas por vendedor,
  melhorar filtros, selecionar múltiplos produtos, salvar grupos reutilizáveis
  para comissão e gerar contas a pagar sem duplicidade.
- [x] **15 — Comissão por valor fixo.** Novo tipo em reais por unidade vendida:
  R$ 5,00 por unidade gera R$ 10,00 ao vender duas. Cadastro, cálculo e exibição
  completos; vale somente para novas vendas, sem recalcular as anteriores.

## Validação e publicação

- [x] Regras do repositório e estado inicial do Git conferidos.
- [x] `FLUXO_UNICO.bat check` aprovado na abertura da tarefa.
- [x] Sessão Chrome do James identificada pelo perfil, URL e usuário exibido.
- [x] Casos relatados investigados por consulta, sem alterações em produção.
- [x] Testes automatizados focados aprovados por frente.
- [x] Fluxos revisados no ambiente DEV, incluindo isolamento entre empresas.
- [ ] Build do frontend e `FLUXO_UNICO.bat release-check` aprovados.
- [ ] Mudanças revisadas, commitadas e enviadas pela branch/PR.
- [ ] Publicação pelo fluxo oficial e verificação após publicação.

## Evidências e andamento

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

### Gate final em andamento — 26/10/2026

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
