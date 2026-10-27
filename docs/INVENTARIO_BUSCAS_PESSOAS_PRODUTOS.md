# Inventário de buscas de pessoas e produtos

Atualizado em 26/10/2026. Escopo: frontend web do ERP, módulos operacionais e catálogo público.

## Padrão aplicado

- `BuscaPessoa` e `BuscaProduto` são as células visuais V2: ordenação por código público/nome, teclado, lista acessível e posicionamento do painel.
- `PessoaSelector` e `ProdutoSelector` mantêm compatibilidade e delegam às células V2.
- `TutorAutocomplete`, `FornecedorSelector` e `ProdutoEstoqueAutocomplete` preservam suas APIs especializadas e usam a mesma célula. Fornecedor continua filtrando `is_fornecedor`; grupos e cadastro rápido foram preservados.
- `useBuscaEntidadeLocal` adapta seleções por ID quando o formulário já recebe um catálogo restrito. O ID continua apenas no vínculo enviado à API; a busca e a tela mostram o código público.
- Campos de filtro sem seleção usam a célula com sugestões desativadas; a tabela/grade continua exibindo o resultado da consulta.
- `renderSuggestionContent` preserva informações de estoque, aptidão clínica, empresa e situação de cadastro dentro do botão acessível padrão.

## Mapa tela por tela

Os caminhos abaixo são os componentes responsáveis pelo campo nas respectivas telas. “Compartilhada” confirma a migração no código; o aceite visual de cada fluxo deve ser acompanhado no DEV. A presença da célula não substitui o teste da API especializada.

| Arquivo da tela/campo | Célula ou adaptador | Situação |
| --- | --- | --- |
| `frontend/src/components/ComprasPendencias.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/EstoqueEntrada.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/components/EstoqueSaida.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/ModaisCaixa.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/TutorAutocomplete.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/campanhas/CampanhasGestorHeader.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/clientes/ClientesNovoActionsBar.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/clientes/PessoaSelector.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/compras/ModalGruposFornecedores.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/compras/PedidoCompraCatalogoProdutos.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/compras/PedidoCompraFormulario.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/compras/PedidosCompraFiltros.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/compras/PedidosCompraSugestaoHeader.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/contas-pagar/ContasPagarAnalise.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/contas-pagar/ContasPagarFilters.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/contasReceber/ContasReceberAnalise.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/contasReceber/ContasReceberPanels.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/contasReceber/ModalNovaContaReceberContent.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/entrada-xml/EntradaPdfUploadModal.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/entrada-xml/EntradaXmlDetalhesItemCard.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/estoque/FracionamentoClinicoModal.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/estoque/GranelLancamentoModal.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/financeiro/VendasPorVendedorPanel.jsx` | BuscaProdutoMultiplo | Compartilhada |
| `frontend/src/components/fornecedores/FornecedorSelector.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/modalNovaContaPagar/ContaPagarBasicFields.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/pdv/ModalPendenciasEstoque.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/pdv/NaoVendaItemEditor.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/components/pdv/NaoVendaRegistroForm.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/components/pdv/PDVClienteCard.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/components/pdv/PDVProdutosCard.jsx` | ProdutoSelector | Compartilhada |
| `frontend/src/components/pessoas/PessoasRelatorioModal.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/components/produto/ProdutosNovoComposicaoTab.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/produto/ProdutosNovoEstruturaSection.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/produto/ProdutosNovoFornecedorModal.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/produto/ProdutosNovoRacaoTab.jsx` | ProdutoSelector | Compartilhada |
| `frontend/src/components/produtoBalanco/ProdutosBalancoFiltros.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/components/produtos/ProdutoSelector.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/produtos/ProdutosFiltrosPanel.jsx` | ProdutoSelector, FornecedorSelector | Compartilhada |
| `frontend/src/components/produtos/ProdutosFornecedoresLoteSection.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/components/veterinario/ProdutoEstoqueAutocomplete.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/components/veterinario/TutorPetSelector.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/Financeiro/HistoricoVendasClienteTab.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/GerenciamentoPets.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/pages/IfoodCentral.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/Pessoas.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/ProdutosLimitesEstoque.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/pages/ProdutosValorizacaoEstoque.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/pages/analise-produtos/AnaliseProdutoEspecifico.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/analise-produtos/AnaliseProdutosFiltros.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/pages/banhoTosa/components/BanhoTosaCreditoForm.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/calculadora-racao/CalculadoraRacaoComparativoFields.jsx` | RacaoSearchInput | Compartilhada |
| `frontend/src/pages/calculadora-racao/CalculadoraRacaoProdutoFields.jsx` | RacaoSearchInput | Compartilhada |
| `frontend/src/pages/calculadora-racao/RacaoSearchInput.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/configuracoes/EstoqueCompartilhadoGrupo.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/configuracoes/visaoGrupo/GrupoAnaliseFiltros.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/configuracoes/visaoGrupo/GrupoProdutosVendidosTab.jsx` | GrupoAnaliseFiltros com entidadeBusca="produto" | Compartilhada |
| `frontend/src/pages/configuracoes/visaoGrupo/GrupoReposicaoInteligenteTab.jsx` | GrupoAnaliseFiltros com entidadeBusca="produto" | Compartilhada |
| `frontend/src/pages/configuracoes/visaoGrupo/GrupoVinculosProdutosTab.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/ecommerce/EcommerceCatalogControls.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/ecommerce/EcommerceStorefrontChrome.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaFilters.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/pages/estoqueTransferenciaParceiro/LancamentoTransferenciaParceiro.jsx` | BuscaPessoa, BuscaProduto | Compartilhada |
| `frontend/src/pages/lembretes/LembretesClientesInativos.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/lgpd/LGPDTitularPanel.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/pages/ofertas/OfertaSelecao.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/orcamentosGrupo/EmpresaGrupoConfigPanel.jsx` | PessoaSelector | Compartilhada |
| `frontend/src/pages/orcamentosGrupo/OrcamentoGrupoItemRow.jsx` | ProdutoSelector | Compartilhada |
| `frontend/src/pages/petForm/PetFormDadosGeraisTab.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/produtos-relatorio/ProdutosRelatorioFiltros.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/produtos-validade-proxima/ProdutosValidadeFiltros.jsx` | BuscaProduto, FornecedorSelector | Compartilhada |
| `frontend/src/pages/produtos/ModalFornecedorProduto.jsx` | FornecedorSelector | Compartilhada |
| `frontend/src/pages/veterinario/agenda/NovoAgendamentoTutorPetSection.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/assistenteIA/AssistenteIASelecaoContexto.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/calculadoraDoses/CalculadoraDosesForm.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/catalogo/ProcedimentoInsumoRow.jsx` | BuscaProduto | Compartilhada |
| `frontend/src/pages/veterinario/consultaForm/InsumoRapidoModal.jsx` | ProdutoEstoqueAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/consultaForm/TutorVeterinarioFields.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/veterinario/examesAnexados/ExamesAnexadosFiltros.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/veterinario/examesAnexados/NovoExameTutorPetSection.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/internacoes/HistoricoInternacoesFiltros.jsx` | BuscaPessoa | Compartilhada |
| `frontend/src/pages/veterinario/internacoes/InsumoRapidoInternacaoModal.jsx` | ProdutoEstoqueAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/internacoes/NovaInternacaoTutorPetSection.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/orcamentos/OrcamentoMvpPanel.jsx` | ProdutoEstoqueAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/vacinas/CarteiraVacinasTab.jsx` | TutorAutocomplete | Compartilhada |
| `frontend/src/pages/veterinario/vacinas/RegistrarVacinaTutorPetSection.jsx` | TutorAutocomplete | Compartilhada |

## Consultas especializadas preservadas

| Fluxo | Fonte e regra preservada |
| --- | --- |
| XML | Catálogo ERP com ativos/inativos; duas consultas tipadas por termo, somente SIMPLES e VARIACAO, com filtro antes da paginação e cancelamento por item. PAI/KIT não entram nas sugestões e o endpoint de vínculo também os rejeita. Situação inativa, código/EAN e estoque permanecem nas sugestões. |
| Composição de kits | Catálogo de componentes elegíveis; exclui o próprio kit e itens proibidos pela regra existente. |
| Granel e fracionamento clínico | Rotas de estoque próprias, unidades e vínculos existentes. Busca anterior é cancelada ao trocar termo ou fechar; resposta tardia não substitui a lista/seleção atual. Bipagem e conversão de estoque continuam nos fluxos originais. |
| Grupos comerciais | Empresa e grupo enviados às rotas autorizadas existentes; a célula não abre acesso a outra empresa. |
| Calculadora de ração | Catálogo específico e aptidão nutricional preservados; produto incompleto continua sem poder ser selecionado. |
| Catálogo público | Mantém as consultas públicas e seus filtros; trocar a célula não usa API privada do ERP. |

## Exceções: campos que não são busca do catálogo ERP

| Arquivo/fluxo | Motivo |
| --- | --- |
| `frontend/src/components/estoqueBling/EstoqueBlingTabs.jsx` | Procura cadastros no provedor Bling para vínculo de integração. O ID externo é referência do provedor; preservar consulta e contrato específicos. |
| `frontend/src/pages/veterinario/catalogo/CatBularioRegulatorio.jsx` | Consulta bulário regulatório externo por produto/princípio ativo/fabricante; não seleciona produto do estoque ERP. |
| `frontend/src/pages/estoqueFullNF/EstoqueFullNFLancamentoPanel.jsx` | Digitação de SKU em linhas de prévia/importação, com validação posterior do lote; não é seletor de cadastro. |
| Filtros de NF, vendas, compras, rotas e lembretes mistos | Consultam documentos/rotas/eventos e podem aceitar nome do cliente como texto; não resolvem nem selecionam uma pessoa ou produto. Mantêm seus campos de consulta do domínio. |
| Dados extraídos de XML/PDF, códigos de barras de conferência e SKU de fornecedor | São dados de entrada/referências para conferência e não buscas livres no cadastro ERP. |
| Categorias, marcas, espécies, raças, usuários/perfis, procedimentos e medicamentos clínicos | São outros catálogos/entidades. A busca genérica de pessoas/produtos não substitui seus filtros de domínio. |

## Códigos públicos

- `frontend/src/utils/codigosPublicos.js` centraliza a identificação de código público e não usa `id`, `cliente_id` ou `produto_id` como código alternativo.
- Ficha de pessoa, notas fiscais, entregas, campanhas, impressão de crédito, cupom de transferência, histórico financeiro e seus PDFs usam código público ou informação de ausência.
- Fallbacks visuais “Tutor #ID”, “Cliente #ID” e “Produto #ID” foram removidos dos módulos auditados. IDs permanecem nas URLs, vínculos, chaves de linha e chamadas técnicas.
- Código de venda, de pendência de compra e ID de provedor externo são referências de outros domínios; não foram trocados por código de cliente/produto.

### Conferência das fontes de código

| Fluxo/API | Situação verificada no código |
| --- | --- |
| Pessoa e gestor de campanhas | Cadastro retorna `codigo`; resumo do gestor usa esse valor público. No caso confirmado em produção, a pessoa 2061 tem referência técnica 47188; a tela não deve exibir 47188 como código. |
| Detalhe de entrega, `GET /vendas/{id}` | `Venda.to_dict` já inclui `cliente.codigo`; a identidade da pessoa recebe esse objeto. |
| Vendas pendentes de entrega | A API passa a devolver `cliente_codigo` e carregar pessoa/entregador na consulta; evita fallback técnico e consultas adicionais por venda. |
| NF de venda local/INTNFE | Normalização passa a incluir `cliente.codigo`; páginas vindas do cache são enriquecidas pela venda vinculada, com pessoa carregada junto à consulta em lote. |
| NF do Bling vinculada a venda local | Enriquecimento preserva referência externa e acrescenta o código público da pessoa do ERP. Há teste distinguindo ID do provedor e código público. |
| NF apenas do provedor, sem vínculo local | Não há código de pessoa do ERP comprovado no payload. A tela informa ausência; ocultar o ID técnico não é considerado validação de um código público. |
| Produto e fornecedor | Sugestões usam códigos de catálogo; `FornecedorIdentity` não transforma ID de fornecedor nem código de documento/produto em código da pessoa. Testes cobrem essa diferença. |

## Verificações e limites

- Testes de seleção local, tutor, histórico paginado, recibos, PDFs, transferência e carimbo manual executados separadamente.
- Revisão adicional confirmou e corrigiu ampliação indevida do catálogo XML para PAI/KIT, loading veterinário preso ao limpar busca e consultas concorrentes em granel/fracionamento. Cinco regressões frontend e cinco backend passaram; vínculo de produto de outra empresa é rejeitado sem alterar o item.
- A revisão de comissão por vigência usa uma referência técnica nova, UTC e imutável, pois `created_at` legado é sem fuso e a data comercial pode ser informada no passado. Quatro ensaios PostgreSQL independentes passaram: fronteiras antes/exata/depois, regra R$ 3→R$ 5→R$ 7 sem mudar parcelas antigas, desativação/exclusão com fallback histórico, isolamento e transferência das versões na fusão. O banco recusa alterar a referência técnica. A migração mantém o baseline legado conhecido; não reconstrói edições anteriores que nunca foram registradas. O CI de migrations passa a executar esses testes antes de apagar cada banco efêmero.
- O build geral e o aceite visual final devem rodar após a integração de todas as frentes da tarefa.
- A ordenação na célula prioriza os candidatos recebidos. As rotas especializadas de estoque/grupo/ração conservam a elegibilidade existente; validar buscas longas e códigos exatos nesses fluxos durante o aceite.
- O histórico de Fernanda Pedraza, código público 2292, foi reproduzido em produção somente para leitura: a rota antiga `/clientes/43087/historico-compras` excede o timeout de 20 segundos. A nova consulta pagina no banco; o teste usa 45 vendas fictícias, valida totais globais e limita consultas à página. A UI mantém erro visível e permite tentar novamente.
- A causa do carimbo de Michele foi confirmada por leitura autorizada dos dados de produção: o carimbo pertence à pessoa 2061, enquanto o usuário de app 84 está ligado à duplicata 10851. A conta tem `login_phone`, mas telefone/e-mail/CPF do perfil vazios; o resolvedor não considerava `login_phone`. O fallback foi corrigido para prevenir novos casos e preservar vínculos explícitos. A correção da duplicata existente exige revisão administrativa; ver `docs/CORRECAO_VINCULO_APP_CARIMBOS.md`.
- O ensaio PostgreSQL DEV validou prévia, fusão, saldo 0→1, seis perfis ativos, flags operacionais, cargo e 306 referências fictícias de vendas. Todos os dados foram desfeitos por rollback. O cartão do app renderiza 1/10 mesmo sem compras e atualiza ao voltar à tela; o aparelho físico da cliente real ainda não foi testado.
- A leitura autorizada do tenant confirmou 111266 vendas `IMP-`, entre 19/11/2019 e **18/09/2026**. Esta última é a data final dos dados importados encontrada. A data/hora de execução da importação continua não comprovada: `created_at` conserva as datas originais e não é recibo de importação.
- Os 27 testes unitários focados de histórico, benefício, código fiscal e segurança da fusão passaram, além dos dois cenários PostgreSQL de preservação dos grants. A suíte de contexto mobile tem uma falha preexistente na política de push: `test_registrar_push_token_keeps_same_device_active_for_other_accounts` exige ausência de `_disable_same_push_token_for_other_users`, mas a implementação no próprio `HEAD` já o chama. `app_mobile_routes.py` permanece sem alterações nesta tarefa; não foi removida proteção nem declarada essa suíte inteira verde.
