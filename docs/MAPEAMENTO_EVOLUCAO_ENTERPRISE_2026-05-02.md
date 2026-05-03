# Mapeamento de evolucao enterprise - sistema inteiro - 2026-05-02

Este documento organiza a evolucao visual, estrutural e logica do sistema inteiro. Produtos, campanhas e comissoes foram apenas exemplos iniciais; a meta e repassar todas as telas e todos os fluxos recorrentes.

## Objetivo

Transformar o sistema em uma base mais modular, previsivel e facil de manter:

- Componentes reutilizaveis para pessoas, produtos, pets, filtros, tabelas, botoes, cards, modais e dashboards.
- Regras visuais claras: mesmas cores, tamanhos, fontes, espacamentos e estados para a mesma intencao.
- Regras de negocio centrais e auditaveis, sem depender do caminho executado pelo usuario.
- Arquivos grandes sendo reduzidos por etapas, sem refatoracao cega.
- Conteudo rico seguro via Markdown/renderizacao controlada.

## Andamento

### Fase 1 - Fundacao visual e piloto PDV

Status: iniciada.

Componentes globais criados ou consolidados:

- `ActionButton` e `IconActionButton` para a regra unica de cores por intencao.
- `Panel` para cards/blocos com borda, raio, sombra e padding consistentes.
- `PageHeader` para cabecalho padrao de telas e modulos.
- `StatusBadge` para status como pago, aberto, cancelado, ativo e entregue.
- `MetricCard` e `MetricGrid` para padronizar dashboards e cards de indicadores.
- `MoneyCell`, `ChannelBadges` e `SafeMarkdown`, ja iniciados na fatia de produtos.
- `FormField`, `TextField` e `SelectField` para campos de formulario com tons visuais reaproveitaveis sem quebrar telas existentes.

Separacao operacional iniciada:

- `MLProHub Ops`: central propria em `/ops`, fora do layout de operacao do Pet Shop.
- Cockpit inicial em `/ops`, com health, alertas automaticos, tenants/rotas sensiveis, deploys recentes e auto-recuperacao.
- A observabilidade detalhada saiu do menu normal de Administracao e passou para `/ops/observabilidade`.
- A rota antiga `/admin/observabilidade` deve apenas redirecionar, para nao quebrar link salvo.
- Backend consolidado em `/admin/observabilidade/ops-summary`, para a inteligencia operacional ficar centralizada e reutilizavel.
- Watchdog passou a registrar eventos em `logs/watchdog_events.jsonl`, permitindo auditar quando o sistema tentou se recuperar sozinho.
- Painel de suporte em `/ops/incidentes`, com drilldown por tenant, rota e request_id para investigar producao sem depender apenas de relato do cliente.
- Alertas acionaveis por tenant/rota em `/ops/incidentes`, com severidade, filtro em um clique e sugestao de correcao para erro repetido, lentidao recorrente e recuperacao automatica.
- Incidentes operacionais passaram a ter persistencia em banco (`ops_error_events`, `ops_alerts`, `ops_recovery_actions`), mantendo os `.jsonl` apenas como fallback/backfill.
- Deploy seguro agora aplica Alembic automaticamente antes das validacoes finais, para evitar producao com codigo novo e banco antigo.
- Watchdog ganhou registro de recuperacao de health e guarda contra loop de restart em janela curta.

Tela piloto:

- PDV: cabecalho, botoes principais, botoes de modo visualizacao, sidebar de vendas recentes e cards principais comecaram a consumir a fundacao global.
- Banho & Tosa: agenda, ficha operacional, creditos, fotos, ocorrencias e taxi dog passaram a usar os campos reutilizaveis mantendo o tom visual atual.
- Banho & Tosa: listas de servicos, recursos, parametros e pacotes passaram a usar `ActionButton` global para edicao/exclusao com cores por intencao.
- Banho & Tosa: formularios de pacotes e campanhas de retorno tambem passaram a usar `TextField`/`SelectField` globais.

Proxima varredura recomendada:

- Finalizar PDV cliente/produtos/modais.
- Depois aplicar o mesmo padrao em Financeiro/Vendas, DRE, Produtos, Pessoas, Pets, Veterinario, Banho & Tosa, Campanhas e demais modulos.

## Escopo global

O trabalho vale para todos os modulos:

- Dashboard e Dashboard Gerencial.
- Pessoas/clientes e pets.
- Veterinario.
- Banho & Tosa.
- Produtos, estoque, validade, balanco, movimentacoes e Bling.
- Lembretes.
- Calculadora de racao.
- PDV/vendas.
- Campanhas.
- E-commerce/app.
- Pedidos Bling e monitor Bling.
- NF de saida e NF de entrada.
- Compras.
- Financeiro/contabil: vendas, DRE, fluxo de caixa, contas, conciliacoes.
- Comissoes.
- Entregas.
- Cadastros.
- RH.
- IA.
- Administracao, usuarios, roles e configuracoes.
- Telas publicas como rastreio e e-commerce.
- Central MLProHub Ops: saude tecnica, erros por tenant, watchdog, deploys, alertas e suporte interno.

## Principios obrigatorios

1. Antes de criar componente novo, procurar se ja existe algo em `frontend/src/components` ou `frontend/src/components/ui`.
2. O componente deve nascer transversal quando o padrao aparece em mais de uma tela.
3. Cor representa intencao da acao, nao gosto do modulo.
4. Cards, botoes, filtros e tabelas devem ter densidade operacional, sem visual de landing page.
5. Regras de negocio nao devem depender do caminho da tela. Se a regra existe, deve valer ao criar, editar, reabrir, cancelar, reprocessar ou importar.
6. Toda regra financeira/campanha/comissao/estoque/cupom deve ser rastreavel por extrato, log, ledger ou evento.
7. Refatorar em fatias pequenas, com comportamento externo preservado.
8. Nao misturar melhoria visual, regra de negocio e reorganizacao grande no mesmo pacote quando isso aumentar risco.

## Regra visual base

Ver `docs/DESIGN_SYSTEM_UI.md`.

Resumo de intencoes:

| Intencao | Uso | Cor |
| --- | --- | --- |
| `create` | Novo, adicionar, cadastrar, incluir, importar quando adiciona dados | verde/emerald |
| `edit` | Editar, salvar alteracao, atualizar cadastro | azul |
| `delete` | Excluir, remover, cancelar destrutivo, estornar destrutivo | vermelho |
| `neutral` | Voltar, fechar, limpar, navegar, imprimir, atualizar lista | slate/cinza |
| `warning` | Reabrir, alerta, pendencia, conflito, acao sensivel reversivel | amber/orange |
| `success` | Pago, concluido, ativo, entregue, reconciliado | emerald |
| `info` | Informativo, sincronizacao, detalhes, ajuda | blue/cyan |

## Padrao de tamanho e alinhamento

### Botoes

- Altura padrao compacta: `h-9` ou equivalente.
- Botao principal de tela: `md`, com icone + texto.
- Botao de linha/tabela: quadrado `h-8 w-8`, com tooltip/title.
- O mesmo verbo deve usar o mesmo intent em todas as telas.
- Evitar botao grande quando a acao e secundaria.

### Cards e dashboards

Problema observado: dashboards e cards de resumo variam muito em altura, largura, cor e densidade, como no PDV.

Padrao desejado:

- `MetricCard`: mesmo padding, borda, raio, titulo, valor e subtitulo.
- Grid com linhas alinhadas: `auto-rows-fr` ou `items-stretch`.
- Cards de uma mesma faixa devem ter mesma altura minima.
- Valor principal sempre no mesmo ponto visual.
- Zero pode virar traco quando o objetivo for destacar numeros relevantes.
- Cores dos cards indicam natureza do dado, nao modulo.

### Paineis

- `Panel`: bloco de trabalho com titulo, subtitulo opcional e acoes.
- Nao usar card dentro de card.
- Evitar paineis muito altos quando a informacao e pequena.

### Tabelas e listas

- `DataTable`: cabecalho, colunas, linhas, empty/loading/error state, acoes e paginacao.
- `MobileList`: versao responsiva de tabela.
- Colunas monetarias e numericas sempre alinhadas a direita.
- Status, canais e tags sempre via componentes de badge.

## Mapa de componentes globais

### Fundacao UI

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `ActionButton` | Botao semantico com intent, tone, size, icone, loading e disabled | Todas as telas |
| `IconActionButton` | Acao compacta de tabela/card com tooltip | Produtos, PDV, financeiro, cadastros, campanhas |
| `ButtonGroup` | Agrupar acoes relacionadas sem desalinhamento | PDV, DRE, vendas, dashboards |
| `PageHeader` | Titulo da pagina, subtitulo, icone, acoes principais | Todos os modulos internos |
| `ModuleTabs` | Abas padronizadas | Veterinario, banho/tosa, campanhas, DRE, produtos |
| `Panel` | Area de trabalho padrao | Formularios, dashboards, relatorios |
| `EmptyState` | Lista vazia com mensagem e acao opcional | Todas as listas |
| `LoadingState` | Carregamento padrao | Todas as telas |
| `ErrorState` | Erro padrao com tentar novamente | Todas as telas |

### Formularios

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `FormField` | Label, ajuda, erro, obrigatorio, input/select/textarea | Todos os formularios |
| `FormSection` | Agrupar campos com titulo e descricao curta | Produto, cliente, pet, venda, configuracoes |
| `SearchInput` | Campo de busca com icone, limpar e loading | Produtos, pessoas, PDV, financeiro |
| `FilterBar` | Filtros horizontais/empilhados responsivos | Produtos, vendas, campanhas, entregas, financeiro |
| `DateRangeFilter` | Periodos rapidos + personalizado | Financeiro, campanhas, entregas, relatorios |
| `MoneyInput` | Moeda BR com mascara | PDV, financeiro, produtos, comissoes |
| `PercentInput` | Percentual consistente | Produtos, margem, campanhas, comissoes |
| `QuantityInput` | Stepper de quantidade | PDV, compras, estoque |
| `SafeMarkdownField` | Texto rico seguro com editar/previa | Produtos, e-commerce, app, mensagens |

### Entidades recorrentes

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `PessoaSelector` | Buscar/selecionar cliente/tutor/pessoa | PDV, financeiro, campanhas, veterinario, banho/tosa |
| `TutorPetSelector` | Selecionar tutor + pet + novo pet | Veterinario, banho/tosa, vacinas, internacoes, exames, calculadoras |
| `PetSelector` | Selecionar pet quando tutor ja esta definido | PDV item pet, campanhas pet, app/vet |
| `ProdutoSelector` | Buscar produto/servico/SKU/codigo de barras | PDV, compras, NF, estoque, kits, campanhas |
| `FornecedorSelector` | Buscar fornecedor | Produtos, compras, NF entrada |
| `FuncionarioSelector` | Buscar funcionario/vendedor/entregador/veterinario | PDV, comissoes, entregas, RH, veterinario |
| `ContaBancariaSelector` | Selecionar conta | Financeiro, caixa, conciliacao |
| `FormaPagamentoSelector` | Selecionar forma de pagamento | PDV, financeiro, contas, configuracoes |

### Dados, status e badges

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `MoneyCell` | Valor em BRL, com `zeroAsDash` | Vendas, DRE, PDV, relatorios, produtos |
| `NumberCell` | Numero alinhado e com traco opcional | Dashboards, relatorios, estoque |
| `PercentCell` | Percentual padrao | Margem, DRE, campanhas, comissoes |
| `StatusBadge` | Status semantico | Venda, pedido, NF, campanha, pet, produto, entrega |
| `ChannelBadges` | App/E-commerce/PDV, sem exibir desligados | Produtos, campanhas, vendas |
| `StockBadge` | Estoque baixo/zerado/ok/reservado | Produtos, PDV, compras |
| `PaymentStatusBadge` | Pago/aberto/parcial/cancelado | PDV, financeiro, contas |
| `DueDateBadge` | Vencido/vencendo/ok | Contas, validade, campanhas |

### Tabelas, cards e dashboards

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `DataTable` | Tabela padrao desktop | Todas as listagens |
| `MobileList` | Lista mobile equivalente a tabela | Produtos, vendas, campanhas, entregas |
| `ColumnSelector` | Mostrar/ocultar colunas | Produtos, vendas, relatorios |
| `PaginationControls` | Paginacao padrao | Todas as listas paginadas |
| `MetricCard` | Card de indicador com altura padronizada | Dashboards, PDV, financeiro, campanhas |
| `MetricGrid` | Grade alinhada de cards | PDV, DRE, Dashboard, entregas |
| `SummaryStrip` | Faixa compacta de indicadores | Vendas, PDV, campanhas |
| `InfoCard` | Card de informacao nao numerica | Cliente, pet, produto, ajuda |
| `EntityCard` | Card de pessoa/produto/pet com campos alinhados | Pessoas, pets, produtos, campanhas |

### Modais e fluxos

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `AppModal` | Modal padrao com header/body/footer | Todas as telas |
| `ConfirmDialog` | Confirmacao destrutiva/sensivel | Excluir, cancelar, estornar |
| `Drawer` | Painel lateral de detalhes | Vendas recentes, analise, cliente, produto |
| `WizardSteps` | Passos de fluxo | Consulta vet, importacoes, cadastro cliente |
| `InlineAlert` | Aviso dentro da tela | PDV, DRE, campanhas, estoque |
| `ToastPattern` | Mensagem de sucesso/erro consistente | Sistema inteiro |

### Conteudo rico seguro

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `SafeMarkdown` | Renderizar Markdown sem HTML cru | Produtos, mensagens, ajuda, app/e-commerce |
| `MarkdownPreview` | Previa de texto editavel | Produtos, campanhas, mensagens |
| `RichTextSanitizer` | Limpar HTML legado de ERP/Bling | Produtos, descricoes importadas |

## Mapa por entidade

### Pessoas/clientes/tutores

Telas provaveis:

- Clientes/pessoas.
- PDV.
- Financeiro vendas e historico por cliente.
- Campanhas.
- Veterinario.
- Banho & Tosa.
- Contas a receber.
- Entregas.

Padronizar:

- Busca, selecao, card resumido, link para detalhes, telefone/documento, status.
- Acoes: novo cliente, editar, ver historico, selecionar.

### Pets

Telas provaveis:

- Pets.
- Pet detalhes.
- Veterinario.
- Banho & Tosa.
- Calculadora de racao.
- PDV quando item/venda exige pet.
- Campanhas de aniversario de pet.

Padronizar:

- `TutorPetSelector`.
- `PetInfoRow` com nome, especie, raca, sexo, idade, codigo.
- Cards de pet com campos sempre alinhados, mesmo quando vazios.
- Botao `Novo pet` sempre `create`.

### Produtos/servicos

Telas provaveis:

- Produtos.
- Produto novo/editar.
- PDV.
- Compras.
- Entrada XML/NF.
- Estoque.
- Kits/variacoes.
- E-commerce/app.
- Calculadora de racao.
- Alertas de racao/IA.

Padronizar:

- `ProdutoSelector`.
- `ChannelBadges`.
- `StockBadge`.
- `MoneyCell`, `PercentCell`, `QuantityInput`.
- `SafeMarkdownField` para descricoes.

### Vendas/caixa/financeiro

Telas provaveis:

- PDV.
- Meus caixas.
- Financeiro/vendas.
- DRE.
- Fluxo de caixa.
- Contas a pagar/receber.
- Conciliacao.
- Comissoes.
- Campanhas quando envolve cupom/cashback.

Padronizar:

- `PaymentStatusBadge`.
- `MoneyCell` com `zeroAsDash`.
- `DateRangeFilter`.
- `MetricGrid`.
- `DataTable`.
- Regras centrais para comissao, cupom, cashback, imposto e rentabilidade.

### Campanhas/cupons/creditos

Telas provaveis:

- Campanhas.
- PDV.
- Cliente.
- App/e-commerce.
- Financeiro/vendas.

Padronizar:

- Extrato/ledger.
- `StatusBadge` para cupom.
- `ChannelBadges`.
- `MetricCard`.
- Reprocessamento idempotente.

### Entregas

Telas provaveis:

- Entregas abertas.
- Rotas.
- Historico.
- Financeiro entregas.
- PDV com taxa/entrega.

Padronizar:

- Status de entrega.
- Cards de rota.
- Tabelas com motorista/cliente/valor/status.
- Mapas e paineis com mesma estrutura.

## Mapa por modulo

| Modulo | Componentes prioritarios |
| --- | --- |
| Dashboard/Dashboard Gerencial | `PageHeader`, `MetricGrid`, `MetricCard`, `Panel`, `DataTable` |
| Pessoas/clientes | `PessoaSelector`, `EntityCard`, `DataTable`, `StatusBadge`, `ActionButton` |
| Pets | `TutorPetSelector`, `PetInfoRow`, `EntityCard`, `ActionButton`, `EmptyState` |
| Veterinario | `TutorPetSelector`, `ModuleTabs`, `FormField`, `Panel`, `WizardSteps`, `MetricCard` |
| Banho & Tosa | `TutorPetSelector`, `ModuleTabs`, `DataTable`, `MetricGrid`, `StatusBadge` |
| Produtos/Estoque | `ProdutoSelector`, `DataTable`, `ChannelBadges`, `StockBadge`, `SafeMarkdown` |
| Calculadora de Racao | `PetSelector`, `ProdutoSelector`, `Panel`, `Dropdown/Combobox`, `MetricCard` |
| PDV | `PessoaSelector`, `ProdutoSelector`, `PetSelector`, `ActionButton`, `MetricGrid`, `Drawer`, `StatusBadge` |
| Campanhas | `PessoaSelector`, `DataTable`, `MetricGrid`, `StatusBadge`, `Statement/Extrato` |
| E-commerce/App | `SafeMarkdown`, `ChannelBadges`, `ProdutoSelector`, `StatusBadge` |
| Compras/NF Entrada | `FornecedorSelector`, `ProdutoSelector`, `DataTable`, `UploadArea`, `ConfirmDialog` |
| NF Saida | `DataTable`, `StatusBadge`, `ActionButton`, `FilterBar` |
| Financeiro | `DateRangeFilter`, `MetricGrid`, `MoneyCell`, `DataTable`, `PaymentStatusBadge` |
| Comissoes | `FuncionarioSelector`, `MoneyCell`, `StatusBadge`, `DataTable`, `Statement/Extrato` |
| Entregas | `FuncionarioSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, `MapPanel` |
| Cadastros | `DataTable`, `FormField`, `AppModal`, `ActionButton`, `ConfirmDialog` |
| RH | `FuncionarioSelector`, `DataTable`, `StatusBadge`, `FormField` |
| IA | `Panel`, `MetricCard`, `MarkdownPreview`, `DataTable`, `InlineAlert` |
| Administracao/Configuracoes | `FormSection`, `FormField`, `ActionButton`, `DataTable`, `StatusBadge` |

## Markdown seguro

### Problema

Descricoes de produtos e textos vindos de ERP/Bling podem vir com HTML, tags ou codigos de formatacao. Renderizar HTML puro resolve aparencia, mas abre risco de seguranca.

### Direcao

Usar Markdown como formato principal para conteudo rico editavel pelo usuario.

### Padrao

- `SafeMarkdown`: renderizacao segura, HTML desligado.
- `SafeMarkdownField`: textarea + previa.
- `normalizeMarkdownContent`: limpar HTML legado antes de salvar/exibir.
- Evitar `dangerouslySetInnerHTML` fora de componentes controlados.

Primeiros usos:

- Produtos.
- App/e-commerce.
- Mensagens de campanhas.
- Central de ajuda.
- Observacoes padronizadas quando fizer sentido.

## Regras de negocio centrais auditaveis

Esta frente vale para todo o sistema, nao so campanhas/comissoes.

### Nome pratico

**Regras centrais auditaveis**.

### Problema

Algumas regras podem depender do caminho executado.

Exemplos:

- Parametro X carimbos = 1 cupom deve valer sempre, inclusive apos cancelamento, restauracao ou reprocessamento.
- Se uma venda tem comissao marcada/configurada, a comissao deve existir mesmo se foi incluida depois, reaberta ou ajustada.
- Se estoque muda por venda, devolucao, NF, ajuste ou kit, o saldo deve reconciliar pela mesma regra.
- Se uma venda muda de status, financeiro, cupom, comissao, caixa, DRE e estoque devem ser atualizados pelo mesmo mecanismo central.

### Padrao recomendado

Para cada dominio sensivel:

1. `sync_<dominio>_for_<entidade>()`
2. `reconcile_<dominio>()`
3. ledger/extrato com creditos, debitos, reversoes e origem
4. testes de dominio cobrindo criar, editar, cancelar, reabrir e reprocessar
5. rotas e telas chamando o mesmo service

### Dominios prioritarios

| Dominio | Regra central |
| --- | --- |
| Campanhas/carimbos/cupons/cashback | Credito, debito, conversao, anulacao, saldo negativo |
| Comissoes | Gerar, recalcular, estornar, reabrir, auditar |
| Estoque | Venda, devolucao, compra, NF, kit, reserva, ajuste |
| Financeiro/caixa | Baixa, reabertura, cancelamento, contas, conciliacao |
| DRE/rentabilidade | Snapshot, rateio, imposto, custo, comissao |
| Entregas | Taxa, status, financeiro do entregador |
| NF/Bling | Importacao, vinculo, conciliacao, idempotencia |

## Arquivos grandes e risco

### Frontend mais criticos

| Arquivo | Linhas aprox. | Risco |
| --- | ---: | --- |
| `frontend/src/components/EntradaXML.jsx` | 4640 | Muito alto |
| `frontend/src/components/VendasFinanceiro.jsx` | 4594 | Muito alto |
| `frontend/src/components/PedidosCompra.jsx` | 3225 | Alto |
| `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | 2533 | Alto |
| `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | 2418 | Alto |
| `frontend/src/components/ModalPagamento.jsx` | 1760 | Medio/alto |
| `frontend/src/pages/ProdutosForm.jsx` | 1670 | Medio/alto |
| `frontend/src/pages/CalculadoraRacao.jsx` | 1424 | Medio |
| `frontend/src/components/Layout.jsx` | 1324 | Alto por ser global |
| `frontend/src/components/DRE.jsx` | 835 | Medio |

### Backend mais criticos

| Arquivo | Linhas aprox. | Risco |
| --- | ---: | --- |
| `backend/app/produtos_routes.py` | 4842 | Muito alto |
| `backend/app/estoque_routes.py` | 4064 | Muito alto |
| `backend/app/notas_entrada_routes.py` | 3411 | Alto |
| `backend/app/campaigns/routes.py` | 3295 | Alto |
| `backend/app/vendas/service.py` | 3036 | Muito alto |
| `backend/app/clientes_routes.py` | 2724 | Alto |
| `backend/app/bling_sync_routes.py` | 2599 | Alto |
| `backend/app/pedidos_compra_routes.py` | 2550 | Alto |
| `backend/app/nfe_routes.py` | 2280 | Alto |
| `backend/app/vendas_routes.py` | 2181 | Alto |

## Como refatorar sem quebrar

1. Primeiro criar componente global com API pequena.
2. Aplicar em uma tela piloto.
3. Validar visual e build.
4. Aplicar em telas irmas.
5. So depois remover duplicacoes antigas.
6. Para regra de negocio, adicionar teste antes ou junto.
7. Para tela grande, extrair primeiro componentes de apresentacao, depois hooks, depois services.

## Sequencia sugerida

### Fase 0 - Inventario e governanca

- Criar checklist de componentes globais.
- Marcar cada tela com: botoes, cards, filtros, tabelas, seletores, modais, regras sensiveis.
- Atualizar `docs/DESIGN_SYSTEM_UI.md` com tamanhos oficiais de botao/card/tabela.

### Fase 1 - Fundacao visual global

- `ActionButton`, `IconActionButton`, `PageHeader`, `Panel`.
- `MetricCard`, `MetricGrid`.
- `StatusBadge`, `ChannelBadges`, `MoneyCell`, `NumberCell`.
- `EmptyState`, `LoadingState`, `ErrorState`.

### Fase 2 - Seletores de entidades

- `PessoaSelector`.
- `TutorPetSelector` consolidado.
- `ProdutoSelector`.
- `FornecedorSelector`.
- `FuncionarioSelector`.
- `FormaPagamentoSelector`.

### Fase 3 - Tabelas, filtros e modais

- `DataTable`.
- `MobileList`.
- `FilterBar`.
- `DateRangeFilter`.
- `AppModal`.
- `ConfirmDialog`.
- `Drawer`.

### Fase 4 - Aplicacao por modulo

Ordem sugerida por impacto e repeticao:

1. PDV, porque concentra pessoa, produto, pet, cards, botoes, status e drawer.
2. Financeiro/vendas/DRE, porque concentra cards, tabelas, periodo e dinheiro.
3. Pessoas e pets, porque viram fonte para outros fluxos.
4. Produtos/estoque/compras/NF, porque compartilham produto, fornecedor, estoque e canal.
5. Veterinario e banho/tosa, porque ja tem parte do `TutorPetSelector`.
6. Campanhas e comissoes, porque precisam de padrao visual e regra central auditavel.
7. Entregas, e-commerce/app, cadastros, RH, IA, configuracoes.

### Fase 5 - Regras centrais auditaveis

- Campanhas/carimbos/cupons/cashback.
- Comissoes.
- Estoque.
- Financeiro/caixa.
- DRE/rentabilidade.
- NF/Bling.

### Fase 6 - Refatoracao dos arquivos grandes

- Atacar um arquivo grande por vez.
- Extrair componentes sem mudar comportamento.
- Criar testes nos dominios sensiveis.

## Definition of Done para padronizacao

Uma melhoria so esta pronta quando:

- usa componente existente ou justifica componente novo;
- aplica `ActionButton`/`IconActionButton` quando for acao;
- usa `MetricCard`/`MetricGrid` em indicadores;
- usa `DataTable`/`MobileList` em listagens novas ou refatoradas;
- usa seletor de entidade quando selecionar pessoa, produto, pet, fornecedor ou funcionario;
- segue `docs/DESIGN_SYSTEM_UI.md`;
- mantem alinhamento e tamanho consistente no desktop e mobile;
- regra de negocio fica em service/domain, nao so na tela;
- caso sensivel tem teste ou roteiro de validacao;
- tem rastreabilidade quando envolve dinheiro, campanha, estoque, cupom, NF ou comissao;
- build/check passam antes de deploy.

## Situacao atual da primeira fatia

Ja foi iniciada uma primeira aplicacao em Produtos:

- `ActionButton`.
- `ChannelBadges`.
- `MoneyCell`.
- `SafeMarkdown`.
- limpeza de HTML legado em descricao.

Isso deve ser tratado como **piloto de fundacao**, nao como prioridade exclusiva de Produtos.

## Inventario operacional do frontend - 2026-05-02

Este inventario foi extraido do codigo atual em `frontend/src`, principalmente `App.jsx`, `pages` e `components`. Ele serve como mapa de execucao, nao como documentacao estatica definitiva.

### Volume por area

| Area | Arquivos aproximados | Leitura |
| --- | ---: | --- |
| `pages/veterinario` | 265 | Modulo mais componentizado; bom candidato para padronizacao incremental por subpasta |
| `components/campanhas` | 64 | Ja tem decomposicao, mas precisa consolidar tabelas, badges, extrato e regras visuais |
| `pages/banhoTosa` | 49 | Precisa reaproveitar seletores e paineis padrao |
| `components/pdv` | 26 | Tela piloto transversal; concentra pessoa, pet, produto, financeiro, campanhas e caixa |
| `components/produto` | 22 | Produto novo/editar ja esta separado em secoes; bom para `FormField`, `SafeMarkdownField` e `ChannelBadges` |
| `components/clientes` | 15 | Deve alimentar `PessoaSelector`, `EntityCard` e padrao de wizard/modal |
| `components/produtos` | 12 | Ja iniciou tabela/listagem padronizada |
| `components/ui` | 11 | Fundacao existe, mas ainda precisa ganhar `DataTable`, `FilterBar`, `AppModal`, `EmptyState`, `NumberCell` |

### Hotspots de padronizacao visual

Estes arquivos combinam muito botao, modal, card, filtro, tabela ou dashboard. Sao bons alvos para migracao para componentes globais porque cada ajuste elimina muita repeticao.

| Prioridade | Arquivo | Motivo principal |
| --- | --- | --- |
| 1 | `frontend/src/components/VendasFinanceiro.jsx` | Financeiro, filtros, cards, tabelas, dinheiro, periodo e status |
| 2 | `frontend/src/components/PedidosCompra.jsx` | Compras, produtos, fornecedor, acoes, modais e tabelas |
| 3 | `frontend/src/components/EntradaXML.jsx` | Arquivo muito grande, NF/itens/produtos, modais e conciliacao |
| 4 | `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | Estoque, produtos, filtros, cards e acoes |
| 5 | `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | Produto/canal/markdown/aparencia e telas publicas |
| 6 | `frontend/src/pages/ProdutosValidadeProxima.jsx` | Produtos, alertas, tabelas e status |
| 7 | `frontend/src/components/ContasPagar.jsx` e `ContasReceber.jsx` | Financeiro, dinheiro, vencimento, filtros e modais |
| 8 | `frontend/src/components/DRE.jsx` | Indicadores, periodo, dinheiro, tabelas e exportacoes |
| 9 | `frontend/src/pages/GerenciamentoPets.jsx` | Cards desalinhados, entidade pet e acoes repetidas |
| 10 | `frontend/src/pages/comissoes/ComissoesListagem.jsx` | Regras sensiveis, dinheiro, funcionario, tabelas e status |

### Padroes repetidos encontrados

| Padrao textual no codigo | Ocorrencias aproximadas | Direcao |
| --- | ---: | --- |
| `button` | 4206 | Migrar gradualmente para `ActionButton` e `IconActionButton` |
| `Modal` | 1658 | Criar `AppModal` e `ConfirmDialog` antes de mexer em todos |
| `Filtro/Filtros` | 2638 | Criar `FilterBar`, `DateRangeFilter`, `SearchInput` |
| `toast` | 830 | Criar padrao de mensagens por tipo de operacao |
| `Card` | 595 | Consolidar `Panel`, `MetricCard`, `EntityCard`, `InfoCard` |
| `confirm` | 555 | Padronizar confirmacao destrutiva/sensivel |
| `Badge` | 341 | Expandir `StatusBadge` e badges especificos |
| `<select` | 297 | Criar `FormField`/`SelectField` e depois `Combobox` |
| `<table` | 138 | Criar `DataTable` antes de refatorar listas grandes |
| `dangerouslySetInnerHTML` | 1 | Manter excecao monitorada; preferir `SafeMarkdown` |

### Adoção dos componentes globais

| Componente | Referencias aproximadas | Estado |
| --- | ---: | --- |
| `ActionButton` | 90 | Ja util; precisa virar padrao obrigatorio em novas telas/refatores |
| `Panel` | 85 | Ja entrou no PDV; precisa migrar cards soltos |
| `StatusBadge` | 47 | Bom inicio, faltam mapeamentos por dominio |
| `MetricCard` | 30 | Ainda pouco frente aos dashboards existentes |
| `IconActionButton` | 10 | Prioritario para acoes de tabela |
| `MoneyCell` | 6 | Deve ir para financeiro, DRE, vendas e relatorios |
| `ChannelBadges` | 5 | Deve ir para produtos, campanhas, app/e-commerce |
| `SafeMarkdown` | 3 | Deve ir para produtos, app/e-commerce, campanhas e ajuda |
| `TutorPetSelector` | 6 | Ja existe; deve ser padrao para vet, banho/tosa, vacinas, internacoes e calculadoras |
| `PageHeader` | 3 | Prioritario para uniformizar telas |
| `MetricGrid` | 1 | Prioritario para dashboards/resumos |

### Rotas e modulos que precisam entrar no ciclo

| Grupo | Rotas principais | Componentes base obrigatorios |
| --- | --- | --- |
| Publico/e-commerce | `/landing`, `/ecommerce`, `/:tenantId`, `/rastreio/:token` | `SafeMarkdown`, `ChannelBadges`, `StatusBadge`, `Panel` |
| Dashboard | `/dashboard`, `/dashboard-gerencial` | `PageHeader`, `MetricGrid`, `MetricCard`, `Panel` |
| Pessoas/clientes | `/clientes`, `/clientes/:id/financeiro`, `/clientes/:id/timeline` | `PessoaSelector`, `EntityCard`, `DataTable`, `StatusBadge` |
| Pets | `/pets`, `/pets/novo`, `/pets/:id`, `/pets/:id/editar` | `TutorPetSelector`, `PetInfoRow`, `EntityCard`, `ActionButton` |
| Veterinario | `/veterinario/*` | `TutorPetSelector`, `ModuleTabs`, `FormField`, `Panel`, `DataTable` |
| Banho & Tosa | `/banho-tosa/*` | `TutorPetSelector`, `ModuleTabs`, `Panel`, `DataTable`, `StatusBadge` |
| Produtos/estoque | `/produtos/*`, `/estoque/*` | `ProdutoSelector`, `DataTable`, `FilterBar`, `ChannelBadges`, `StockBadge` |
| PDV/caixa | `/pdv`, `/meus-caixas` | `PessoaSelector`, `ProdutoSelector`, `PetSelector`, `ActionButton`, `Panel`, `MetricGrid` |
| Fiscal/Bling/compras | `/notas-fiscais/*`, `/compras/*`, `/vendas/bling-*`, `/produtos/sinc-bling` | `ProdutoSelector`, `FornecedorSelector`, `StatusBadge`, `DataTable`, `ConfirmDialog` |
| Financeiro | `/financeiro/*` | `MoneyCell`, `DateRangeFilter`, `MetricGrid`, `DataTable`, `PaymentStatusBadge` |
| Comissoes | `/comissoes/*` | `FuncionarioSelector`, `MoneyCell`, `StatusBadge`, `DataTable`, extrato/regra central |
| Campanhas | `/campanhas`, `/campanhas/canais` | `PessoaSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, extrato/ledger |
| Entregas | `/entregas/*` | `FuncionarioSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, `MapPanel` |
| Cadastros/RH/Admin | `/cadastros/*`, `/rh/*`, `/admin/*`, `/configuracoes/*` | `PageHeader`, `FormField`, `DataTable`, `AppModal`, `ConfirmDialog` |
| IA/Ajuda | `/ia/*`, `/ajuda` | `Panel`, `SafeMarkdown`, `MetricCard`, `InlineAlert` |

## Onda 1 - Fundacao realmente transversal

Objetivo: parar de resolver cada tela como se fosse unica. Esta onda nao tenta "embelezar tudo"; ela cria blocos pequenos e aplica em telas que mais repetem padrao.

### Componentes a fechar primeiro

| Componente | Por que vem agora | Telas piloto |
| --- | --- | --- |
| `DataTable` | Existem muitas tabelas com cabecalho, empty state, paginacao e acoes repetidas | Produtos, financeiro/vendas, pets |
| `FilterBar` + `SearchInput` | Filtros aparecem em praticamente todos os modulos | Produtos, financeiro/vendas, pets |
| `FormField` + `SelectField` | Muitos formularios e selects soltos | Produto editar, pet, banho/tosa agenda |
| `AppModal` + `ConfirmDialog` | Modais e confirms estao espalhados | Produtos, PDV, campanhas |
| `EntityCard` | Pessoas, pets e produtos precisam de alinhamento consistente | Pets, cliente no PDV, pessoas |
| `NumberCell` + ampliar `MoneyCell` | Zero como traco e alinhamento numerico deve ser padrao | Financeiro/vendas, DRE, produtos |
| `StockBadge` + `PaymentStatusBadge` | Status precisa parar de variar por tela | Produtos, vendas, contas |

### Ordem de aplicacao da Onda 1

1. **Pets**: resolver desalinhamento de cards e criar `EntityCard`/`PetInfoRow`.
2. **Financeiro/Vendas**: aplicar `MoneyCell`, `NumberCell`, `MetricGrid`, `FilterBar` e preparar `DataTable`.
3. **Produtos**: terminar listagem com `DataTable`/`FilterBar` e consolidar `ChannelBadges`.
4. **PDV**: manter como vitrine de interacao compacta e aplicar `EntityCard` no cliente.
5. **Banho & Tosa + Veterinario**: reaproveitar `TutorPetSelector` e padronizar formularios.

### Progresso da Onda 1

- 2026-05-02: criado `EntityCard`/`EntityInfoRow` e aplicado em `/pets`, com campos fixos mesmo vazios, botoes padronizados e card preparado para reuso em pessoas/produtos.
- 2026-05-02: ampliado `MoneyCell` com sinal/zero como traco, criado `NumberCell` e aplicado na consulta de vendas em resumo por data, lista de vendas e itens expandidos.
- 2026-05-02: criado `FilterBar`/`FilterRow`/`FilterAdvanced` e aplicado em `/pets` como primeiro padrao de filtros reutilizaveis.
- 2026-05-03: iniciada a fatia Financeiro/DRE, com `MetricGrid`/`MetricCard` na DRE e `MoneyCell`/`NumberCell`/`StatusBadge`/`ActionButton` aplicados em DRE, contas a pagar e contas a receber.
- 2026-05-03: `FluxoCaixa` entrou na mesma fundacao visual, com cards de resumo via `MetricGrid`/`MetricCard`, valores via `MoneyCell`, botoes via `ActionButton` e status de movimentacao via `StatusBadge`.
- 2026-05-03: `VendasFinanceiro` recebeu primeira fatia da fundacao, com filtros avancados em `FilterBar`, status da lista via `StatusBadge` e totalizadores compactos em `MetricGrid`/`MetricCard`.
- 2026-05-03: criado `DataTable` base para migrar listagens com cabecalho, alinhamento, loading, vazio, clique de linha e linha expandida sem reescrever cada tela.
- 2026-05-03: `ContasPagar` e `ContasReceber` migraram a listagem principal para `DataTable`, mantendo `MoneyCell`, `StatusBadge` e `ActionButton` como padrao financeiro.
- 2026-05-03: `DataTable` ganhou compatibilidade com colunas legadas que renderizam `<th>`/`<td>`, permitindo migrar a listagem desktop de `ProdutosTabelaSection` sem reescrever as colunas existentes.
- 2026-05-03: `ProdutosFiltrosPanel` passou a usar `FilterBar`, preservando a grade atual de filtros e alinhando o container ao padrao global.
- 2026-05-03: `ProdutosHeaderActions` passou a usar `PageHeader`, padronizando titulo, subtitulo, tour e acoes principais da tela de Produtos.
- 2026-05-03: filtros de `ContasPagar` e `ContasReceber` passaram a usar `FilterBar`, mantendo os campos e handlers atuais.
- 2026-05-03: cabecalhos de `ContasPagar` e `ContasReceber` passaram a usar `PageHeader`, com acoes em `ActionButton` e icones padronizados.
- 2026-05-03: `PDVClienteCard` foi quebrado em blocos internos de busca, resumo, fidelidade, credito, acoes e seletor de pet, preparando o card de cliente para virar componente reutilizavel sem mudar o fluxo do PDV.
- 2026-05-03: criado `ProdutoSelector` reutilizavel e aplicado na busca de produtos/servicos do PDV, mantendo a renderizacao customizada das sugestoes do carrinho.
- 2026-05-03: criado `PessoaSelector` reutilizavel e aplicado na busca de cliente do PDV, preservando a busca externa atual e preparando o reaproveitamento em pets, financeiro, campanhas e banho/tosa.
- 2026-05-03: `/pets` passou a usar `PessoaSelector` na busca de tutor, removendo o dropdown manual duplicado e consolidando o segundo uso real do selector de pessoa.

### Nao fazer nesta onda

- Nao reescrever arquivos gigantes inteiros.
- Nao mexer em regra de negocio junto com refator visual grande.
- Nao trocar todos os botoes do sistema em massa sem validar por modulo.
- Nao criar mais um componente se `ActionButton`, `Panel`, `StatusBadge`, `MetricCard` ou `TutorPetSelector` ja resolverem.

## Onda 2 - Regras centrais auditaveis

Depois da fundacao visual, atacar a logica sensivel com pouco ruido visual.

| Dominio | Primeira entrega concreta |
| --- | --- |
| Campanhas | Extrato/ledger geral: credito, debito, conversao, estorno, origem, saldo |
| Carimbos/cupons | Reconciliador: parametro X carimbos = 1 cupom, independente do caminho |
| Comissoes | Reconciliador por venda: se tem comissao configurada, gera/atualiza/estorna |
| Estoque | Extrato unico por produto: venda, compra, ajuste, cancelamento, NF, kit |
| Financeiro/caixa | Evento unico para venda criada/editada/cancelada/reaberta/baixada |
| DRE | Snapshot/recalculo auditavel por periodo e origem |

### Nome tecnico interno

Usar o termo **orquestradores/reconciliadores de dominio com ledger**.

Na pratica:

- Orquestrador: decide o que precisa acontecer quando uma entidade muda.
- Reconciliador: confere e corrige o estado final esperado.
- Ledger/extrato: registra por que houve credito, debito, estorno, cupom, comissao ou ajuste.

## Proximo passo recomendado

Continuar a **Onda 1 / Passo 2: Financeiro/Vendas**.

Entrega esperada:

1. Levar `MoneyCell`/`NumberCell` para DRE, contas a pagar/receber e compras.
2. Levar `FilterBar` para Financeiro/Vendas, Produtos e Compras.
3. Preparar `DataTable` sem reescrever a tela inteira.
4. Padronizar `StatusBadge` em vendas, contas e compras.
5. Rodar build e validar visual local a cada fatia.
