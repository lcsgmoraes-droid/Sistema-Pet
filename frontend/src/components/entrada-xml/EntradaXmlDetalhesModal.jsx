import CardFiscal from '../CardFiscal';
import SegmentedControl from '../ui/SegmentedControl';

function EntradaXmlDetalhesModal({
  acaoConferenciaOpcoes: ACAO_CONFERENCIA_OPCOES,
  aberto,
  abrirModalCriarProduto,
  aplicarMultiplicadorPackAoItem,
  atualizarCampoConferenciaItem,
  atualizarFiltroProduto,
  buscandoProduto,
  calcularConferenciaItem,
  carregarPreviewProcessamento,
  conferenciaItens,
  conferenciaObservacaoGeral,
  criandoPendenciaFornecedor,
  criarTodosProdutosNaoVinculados,
  desfazendoConferencia,
  desfazerConferenciaAtual,
  desvincularProduto,
  detectarDivergencias,
  excluirNota,
  filtroItensNota,
  filtroProduto,
  formatarOpcaoProduto,
  formatarValorFiscal,
  gerandoRascunhoDevolucao,
  gerarPendenciaFornecedor,
  gerarRascunhoDevolucao,
  getConfiancaBadge,
  itensComDivergenciaDetalhe,
  itensExibidosNota,
  itensNotaDetalhe,
  loading,
  metaConferenciaAtual,
  mostrarCamposConferencia,
  multiplicadoresPack,
  navigate,
  notaSelecionada,
  obterConfiguracaoPackItem,
  obterCustoAquisicaoItem,
  processarNota,
  quantidadesOnline,
  resultadosBuscaProduto,
  resumoConferenciaAtual,
  reverterNota,
  salvandoConferencia,
  salvarConferenciaAtual,
  salvarQuantidadeOnlineItem,
  salvarTipoRateio,
  setConferenciaObservacaoGeral,
  setFiltroItensNota,
  setFiltroProduto,
  setMostrarCamposConferencia,
  setMostrarDetalhes,
  setMultiplicadoresPack,
  setNotaSelecionada,
  setQuantidadesOnline,
  setResultadosBuscaProduto,
  tipoRateio,
  vincularProduto,
}) {
  return (
    <>
      {/* Modal de Detalhes */}
      {aberto && notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            {/* Cabecalho */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Detalhes da NF-e</h2>
                <p className="text-sm text-gray-600">Chave: {notaSelecionada.chave_acesso}</p>
              </div>
              <button
                onClick={() => {
                  setMostrarDetalhes(false);
                  setNotaSelecionada(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                X
              </button>
            </div>

            {/* Informacoes da Nota */}
            <div className="px-6 py-4 border-b bg-gray-50">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Fornecedor:</span>
                  <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                  <div className="text-xs text-gray-500">{notaSelecionada.fornecedor_cnpj}</div>
                  {notaSelecionada.fornecedor_id && (
                    <div className="text-xs text-green-600 mt-1">Cadastrado</div>
                  )}
                </div>
                <div>
                  <span className="text-gray-600">Data Emissao:</span>
                  <div className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString()}</div>
                </div>
                <div>
                  <span className="text-gray-600">Valor Total:</span>
                  <div className="font-bold text-lg text-green-600">R$ {(notaSelecionada.valor_total || 0).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Alerta de Fornecedor Novo - Versao Compacta */}
            {notaSelecionada.fornecedor_id && notaSelecionada.fornecedor_criado_automaticamente && (
              <div className="px-6 py-2 bg-blue-50 border-b border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-blue-800">
                    <strong>{notaSelecionada.fornecedor_nome}</strong> foi cadastrado automaticamente.
                  </div>
                  <button
                    onClick={() => navigate(`/clientes/${notaSelecionada.fornecedor_id}`)}
                    className="px-3 py-1 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 text-xs"
                  >
                    Completar Cadastro
                  </button>
                </div>
              </div>
            )}

            {resumoConferenciaAtual && (
              <div className="px-6 py-4 border-b bg-emerald-50/40">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-3">
                    <div className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
                      {metaConferenciaAtual?.label || 'Nao conferida'}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Itens OK</div>
                        <div className="font-bold text-lg text-emerald-700">{resumoConferenciaAtual.itens_ok}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Divergencias</div>
                        <div className="font-bold text-lg text-orange-700">{resumoConferenciaAtual.itens_com_divergencia}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Qtd recebida</div>
                        <div className="text-[11px] text-gray-500 mt-1">Entra no estoque</div>
                        <div className="font-bold text-lg text-slate-800">{formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Falta + Avaria</div>
                        <div className="font-bold text-lg text-rose-700">
                          {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_faltante + resumoConferenciaAtual.quantidade_total_avariada, 2)}
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 max-w-3xl">
                      {notaSelecionada.status === 'pendente'
                        ? (
                          <>
                            A conferência nasce assumindo tudo certo. Se a carga estiver perfeita, basta clicar em <strong>Conferido</strong>. Só mexa nos itens com falta ou avaria.
                          </>
                        )
                        : 'Conferencia ja salva. Use as acoes de divergencia para gerar a tratativa sem precisar reverter a entrada.'}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {notaSelecionada.status === 'pendente' && (
                      <>
                        <button
                          onClick={() => setMostrarCamposConferencia((prev) => !prev)}
                          className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg font-semibold hover:bg-slate-100"
                        >
                          {mostrarCamposConferencia ? 'Ocultar ajuste manual' : 'Editar quantidades e avarias'}
                        </button>
                        <button
                          onClick={() => salvarConferenciaAtual()}
                          disabled={salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-60"
                        >
                          {salvandoConferencia
                            ? 'Salvando...'
                            : (resumoConferenciaAtual.status === 'nao_iniciada' ? 'Conferido' : 'Atualizar conferencia')}
                        </button>
                      </>
                    )}
                    {notaSelecionada.status === 'pendente' && resumoConferenciaAtual.status !== 'nao_iniciada' && (
                      <button
                        onClick={desfazerConferenciaAtual}
                        disabled={desfazendoConferencia || salvandoConferencia || Boolean(notaSelecionada?.entrada_estoque_realizada)}
                        className="px-4 py-2 border border-amber-300 bg-amber-50 text-amber-800 rounded-lg font-semibold hover:bg-amber-100 disabled:opacity-60"
                      >
                        {desfazendoConferencia ? 'Desfazendo...' : 'Desfazer conferencia'}
                      </button>
                    )}
                    {notaSelecionada.status !== 'pendente' && resumoConferenciaAtual.itens_com_divergencia > 0 && (
                      <>
                        <button
                          onClick={() => setMostrarCamposConferencia((prev) => !prev)}
                          className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg font-semibold hover:bg-slate-100"
                        >
                          {mostrarCamposConferencia ? 'Ocultar tratativas' : 'Abrir tratativas'}
                        </button>
                        <button
                          onClick={() => salvarConferenciaAtual()}
                          disabled={salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-60"
                        >
                          {salvandoConferencia ? 'Salvando...' : 'Salvar tratativas'}
                        </button>
                      </>
                    )}
                    {resumoConferenciaAtual.itens_com_divergencia > 0 && (
                      <>
                        <button
                          onClick={gerarPendenciaFornecedor}
                          disabled={criandoPendenciaFornecedor || salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 border border-blue-200 bg-blue-50 text-blue-700 rounded-lg font-semibold hover:bg-blue-100 disabled:opacity-60"
                        >
                          {criandoPendenciaFornecedor ? 'Gerando...' : 'Gerar pendencia fornecedor'}
                        </button>
                        <button
                          onClick={gerarRascunhoDevolucao}
                          disabled={gerandoRascunhoDevolucao || salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:opacity-60"
                        >
                          {gerandoRascunhoDevolucao ? 'Gerando...' : 'NF Devolucao das Divergencias'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {mostrarCamposConferencia && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Observacao geral da conferencia</label>
                    <textarea
                      value={conferenciaObservacaoGeral}
                      onChange={(e) => setConferenciaObservacaoGeral(e.target.value)}
                      rows="2"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                      placeholder="Ex.: faltou 1 unidade do item X e 2 vieram avariadas."
                    />
                  </div>
                )}
              </div>
            )}

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold text-xl text-gray-800">
                    Produtos da Nota ({itensExibidosNota.length}
                    {filtroItensNota === 'divergencias' ? ` de ${itensNotaDetalhe.length}` : ''})
                  </h3>
                  {itensComDivergenciaDetalhe.length > 0 && (
                    <p className="mt-1 text-xs text-orange-700">
                      {itensComDivergenciaDetalhe.length} item(ns) com divergencia ou tratativa pendente.
                    </p>
                  )}
                </div>
                
                <div className="flex flex-wrap items-center gap-2">
                  {itensComDivergenciaDetalhe.length > 0 && (
                    <SegmentedControl
                      ariaLabel="Filtrar itens da nota"
                      size="md"
                      value={filtroItensNota}
                      onChange={setFiltroItensNota}
                      options={[
                        { value: 'todos', label: 'Todos' },
                        {
                          value: 'divergencias',
                          label: `Com divergencia (${itensComDivergenciaDetalhe.length})`,
                          activeClassName: 'bg-orange-100 text-orange-800 shadow-sm',
                          onSelect: () => setMostrarCamposConferencia(true),
                        },
                      ]}
                    />
                  )}

                  {notaSelecionada.status === 'pendente' &&
                   notaSelecionada.itens.some(item => !item.produto_id) && (
                    <button
                      onClick={criarTodosProdutosNaoVinculados}
                      disabled={loading}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 flex items-center gap-2 text-sm"
                      title="Cria automaticamente todos os produtos nao vinculados com os padrões: Estoque mín: 10, máx: 100, Margem: 50%"
                    >
                      <span>Criar Todos Nao Vinculados</span>
                      <span className="text-xs bg-purple-800 px-2 py-0.5 rounded">
                        {notaSelecionada.itens.filter(i => !i.produto_id).length}
                      </span>
                    </button>
                  )}
                </div>
              </div>
              
              <div className="space-y-3">
                {itensExibidosNota.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                    Nenhum produto encontrado para este filtro.
                  </div>
                )}
                {itensExibidosNota.map(item => {
                  const divergencias = detectarDivergencias(item);
                  const temDivergencia = divergencias.length > 0;
                  const itemAjustado = aplicarMultiplicadorPackAoItem(item, multiplicadoresPack);
                  const packConfig = obterConfiguracaoPackItem(item, multiplicadoresPack);
                  const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
                  const mostrarTratativaItem = mostrarCamposConferencia && (
                    notaSelecionada.status === 'pendente' ||
                    conferenciaItem.temDivergencia ||
                    Boolean(item.tem_divergencia)
                  );
                  const podeEditarQuantidadesItem = notaSelecionada.status === 'pendente';
                  
                  return (
                    <div key={item.id} className="border-2 border-gray-400 rounded-lg overflow-hidden bg-white shadow-sm">
                      {/* Grade de 2 Colunas: NF-e (esquerda) | Conexão | Produto Sistema (direita) */}
                      <div className="grid grid-cols-[1fr_auto_1fr] gap-0">
                        {/* COLUNA ESQUERDA: Dados da NF-e */}
                        <div className="bg-blue-50 border-r-2 border-gray-300 p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">NF-e</div>
                            {getConfiancaBadge(item.confianca_vinculo)}
                          </div>
                          
                          <div className="font-semibold text-base mb-2 text-blue-900">{item.descricao}</div>
                          
                          <div className="space-y-1.5 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">Codigo:</span>
                              <span className="font-mono font-semibold">{item.codigo_produto}</span>
                            </div>
                            {item.ean && item.ean !== 'SEM GTIN' && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">EAN:</span>
                                <span className="font-mono font-semibold">{item.ean}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span className="text-gray-600">NCM:</span>
                              <span className="font-mono font-semibold">{item.ncm}</span>
                            </div>
                            <div className="flex justify-between border-t pt-1.5 mt-1.5">
                              <span className="text-gray-600">Qtd:</span>
                              <span className="font-semibold">{item.quantidade}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Valor Unit.:</span>
                              <span className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Custo Aquisição:</span>
                              <span className="font-semibold text-amber-700">R$ {formatarValorFiscal(obterCustoAquisicaoItem(itemAjustado), 4)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Total:</span>
                              <span className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">CFOP:</span>
                              <span className="font-semibold">{item.cfop}</span>
                            </div>

                            {/* Pack / Caixa: multiplicador manual ou auto-detectado */}
                            {notaSelecionada.status === 'pendente' && (
                              <div className="mt-2 pt-2 border-t border-blue-200">
                                <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                                  <span className="text-gray-600 text-xs font-semibold">Pack (unid./caixa):</span>
                                  <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                    {packConfig.packDetectadoAutomatico && (
                                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-semibold">📦 auto</span>
                                    )}
                                    {packConfig.sugestaoAutomaticaDiferenteDoPadrao && (
                                      <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-semibold">
                                        Conferir sugestão x{packConfig.multiplicadorDetectado}
                                      </span>
                                    )}
                                    {packConfig.overrideManual && (
                                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-semibold">
                                        Usando x{packConfig.multiplicador} digitado
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <input
                                    type="number"
                                    min="1"
                                    max="200"
                                    value={packConfig.multiplicador}
                                    onChange={(e) => {
                                      const v = Math.max(1, Math.min(200, Number.parseInt(e.target.value) || 1));
                                      setMultiplicadoresPack(prev => ({ ...prev, [item.id]: v }));
                                    }}
                                    className={`w-20 px-2 py-1 border-2 rounded text-sm text-right font-semibold focus:ring-2 ${
                                      packConfig.overrideManual
                                        ? 'border-blue-400 bg-blue-50 text-blue-900 focus:ring-blue-500'
                                        : packConfig.sugestaoAutomaticaDiferenteDoPadrao
                                          ? 'border-amber-400 bg-amber-50 text-amber-900 focus:ring-amber-500'
                                          : 'border-blue-300 focus:ring-blue-500'
                                    }`}
                                  />
                                  <span className="text-xs text-gray-500">unid. por caixa</span>
                                </div>
                                {(packConfig.sugestaoAutomaticaDiferenteDoPadrao || packConfig.overrideManual) && (
                                  <div
                                    className={`mt-1.5 rounded p-2 text-xs space-y-0.5 border ${
                                      packConfig.overrideManual
                                        ? 'bg-blue-50 border-blue-200 text-blue-800'
                                        : 'bg-amber-50 border-amber-200 text-amber-800'
                                    }`}
                                  >
                                    <div>
                                      {packConfig.overrideManual
                                        ? '✏️ Valor digitado considerado nos cálculos.'
                                        : '🤖 Sugestão automática aplicada nos cálculos.'}
                                    </div>
                                    <div>
                                      🔢 Qtd efetiva: <strong>{itemAjustado.quantidade_efetiva}</strong> unid. ({item.quantidade} cx × {packConfig.multiplicador})
                                    </div>
                                    <div>
                                      💰 Custo unit.: <strong>R$ {obterCustoAquisicaoItem(itemAjustado).toFixed(4)}</strong>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            <CardFiscal nota={notaSelecionada} item={itemAjustado} composicao={itemAjustado.composicao_custo} />
                          </div>

                          {/* Lote e Validade */}
                          {(item.lote || item.data_validade) && (
                            <div className="mt-3 pt-3 border-t space-y-2">
                              {item.lote && (
                                <div className="text-xs">
                                  <span className="text-gray-600">Lote:</span>
                                  <div className="font-semibold text-purple-800">{item.lote}</div>
                                </div>
                              )}
                              {item.data_validade && (
                                <div className="text-xs">
                                  <span className="text-gray-600">Validade:</span>
                                  <div className="font-semibold text-orange-800">
                                    {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* COLUNA CENTRAL: Ícone de Conexão + Alerta de Divergência */}
                        <div className="flex flex-col items-center justify-center bg-gray-100 px-2 py-4">
                          {item.produto_id ? (
                            <>
                              <button
                                onClick={() => desvincularProduto(notaSelecionada.id, item.id)}
                                className="text-3xl text-green-600 hover:text-red-600 transition-colors mb-2"
                                title="Vinculado - Clique para desvincular"
                              >
                                V
                              </button>
                              {temDivergencia && (
                                <div className="bg-red-100 border-2 border-red-500 rounded-lg p-2 max-w-[200px]">
                                  <div className="text-center">
                                    <div className="text-2xl mb-1">⚠️</div>
                                    <div className="font-bold text-red-700 text-xs mb-1">
                                      DIVERGÊNCIA!
                                    </div>
                                    <div className="text-[10px] text-red-600 space-y-0.5">
                                      {divergencias.map((div) => (
                                        <div key={`${item.id}-${div}`}>• {div}</div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <div className="text-3xl text-gray-400" title="❌ Não vinculado">
                              X
                            </div>
                          )}
                        </div>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>
                          {notaSelecionada.status === 'pendente' ? (
                            <>
                              {item.produto_id ? (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      PRODUTO SISTEMA
                                    </div>
                                  </div>
                                  
                                  <div className="font-semibold text-base mb-3 text-green-900">
                                    {item.produto_nome}
                                  </div>

                                  <div className="mb-3 rounded border border-green-200 bg-white/80 p-2 text-xs space-y-1">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-gray-600">SKU:</span>
                                      <span className="font-mono text-gray-900">
                                        {item.produto_codigo || 'Nao informado'}
                                      </span>
                                    </div>
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-gray-600">EAN:</span>
                                      <span className="font-mono text-gray-900">
                                        {item.produto_ean || 'Nao informado'}
                                      </span>
                                    </div>
                                    {item.origem_vinculo_automatico && item.referencia_vinculo && (
                                      <div className="mt-2 rounded border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
                                        Match automatico por <strong>{item.origem_vinculo_automatico === 'codigo_barras' ? 'codigo de barras' : 'SKU'}</strong>: <strong>{item.referencia_vinculo}</strong>
                                      </div>
                                    )}
                                  </div>

                                  <div className="text-xs text-green-700 mb-3 italic">
                                    Para alterar o vinculo, selecione outro produto ou clique no V para desvincular
                                  </div>

                                  <input
                                    type="text"
                                    placeholder="Pesquisar outro produto para trocar..."
                                    value={filtroProduto[item.id] || ''}
                                    onChange={(e) => atualizarFiltroProduto(item.id, e.target.value)}
                                    className="w-full px-3 py-2 border-2 border-green-300 rounded focus:ring-2 focus:ring-green-500 text-sm mb-2"
                                  />

                                  {/* Select para trocar produto */}
                                  <select
                                    value={item.produto_id}
                                    onChange={(e) => {
                                      if (e.target.value && e.target.value != item.produto_id) {
                                        vincularProduto(notaSelecionada.id, item.id, e.target.value);
                                      }
                                    }}
                                    className="w-full px-3 py-2 border-2 border-green-400 rounded text-sm focus:ring-2 focus:ring-green-500"
                                  >
                                    <option value={item.produto_id}>
                                      {`${item.produto_codigo || 'Sem SKU'} | EAN: ${item.produto_ean || 'Sem EAN'} | ${item.produto_nome}`}
                                    </option>
                                    {(resultadosBuscaProduto[item.id] || [])
                                      .filter(p => p.id !== item.produto_id)
                                      .map(p => (
                                        <option key={p.id} value={p.id}>
                                          {formatarOpcaoProduto(p)}
                                        </option>
                                      ))}
                                  </select>
                                </>
                              ) : (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-orange-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      ⚠️ NÃO VINCULADO
                                    </div>
                                  </div>
                                  
                                  <div className="space-y-3">
                                    {/* Campo de pesquisa */}
                                    <div>
                                      <div className="block text-xs font-semibold text-gray-700 mb-1">
                                        Pesquisar produto existente:
                                      </div>
                                      <input
                                        type="text"
                                        placeholder="Digite nome ou SKU..."
                                        value={filtroProduto[item.id] || ''}
                                        onChange={(e) => atualizarFiltroProduto(item.id, e.target.value)}
                                        className="w-full px-3 py-2 border-2 border-gray-400 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                                      />
                                    </div>
                                    
                                    {/* Lista de produtos filtrados */}
                                    {filtroProduto[item.id] && filtroProduto[item.id].length >= 2 && (
                                      <div className="border-2 border-gray-300 rounded max-h-48 overflow-y-auto bg-white">
                                        {(() => {
                                          const filtrados = resultadosBuscaProduto[item.id] || [];
                                          if (buscandoProduto[item.id]) {
                                            return (
                                              <div className="px-3 py-4 text-center text-gray-500 text-xs">
                                                Buscando produtos...
                                              </div>
                                            );
                                          }
                                          if (filtrados.length === 0) {
                                            return (
                                              <div className="px-3 py-4 text-center text-gray-500 text-xs">
                                                ❌ Nenhum produto encontrado
                                              </div>
                                            );
                                          }
                                          return filtrados.map(p => (
                                            <button
                                              key={`produto-${item.id}-${p.id}`}
                                              type="button"
                                              onClick={() => {
                                                vincularProduto(notaSelecionada.id, item.id, p.id);
                                                setFiltroProduto(prev => ({ ...prev, [item.id]: '' }));
                                                setResultadosBuscaProduto(prev => ({ ...prev, [item.id]: [] }));
                                              }}
                                              className={`w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-200 last:border-b-0 text-xs ${!p.ativo ? 'text-red-600 font-bold' : ''}`}
                                            >
                                              {!p.ativo && '[INATIVO] '}{p.codigo || 'Sem SKU'} - {p.nome}
                                              <span className="text-gray-500 ml-1">| EAN: {p.codigo_barras || p.gtin_ean || p.gtin_ean_tributario || 'Sem EAN'}</span>
                                              <span className="text-gray-500 ml-1">(Est: {p.estoque_atual || 0})</span>
                                            </button>
                                          ));
                                        })()}
                                      </div>
                                    )}
                                    
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1 border-t border-gray-300"></div>
                                      <span className="text-xs text-gray-500">ou</span>
                                      <div className="flex-1 border-t border-gray-300"></div>
                                    </div>

                                    <button
                                      onClick={() => abrirModalCriarProduto(item)}
                                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 text-sm"
                                    >
                                      ➕ Criar Novo Produto
                                    </button>
                                  </div>
                                </>
                              )}
                            </>
                          ) : (
                            // Nota ja processada - apenas visualizacao
                            <div>
                              {item.produto_id ? (
                                <>
                                  <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold inline-block mb-2">
                                    VINCULADO
                                  </div>
                                  <div className="font-semibold text-base text-green-900">
                                    {item.produto_nome}
                                  </div>
                                </>
                              ) : (
                                <div className="bg-gray-600 text-white px-2 py-1 rounded text-xs font-bold inline-block">
                                  ⚠️ NÃO VINCULADO
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Rateio de Estoque (se modo PARCIAL) - Expande por toda a largura */}
                      {notaSelecionada.status === 'pendente' && 
                       tipoRateio === 'parcial' && 
                       item.produto_id && (
                        <div className="col-span-3 p-4 border-t-2 border-gray-300 bg-gradient-to-r from-blue-50 via-gray-50 to-green-50">
                          <h4 className="font-medium text-gray-700 mb-3 flex items-center text-sm">
                            Quantidade destinada ao estoque online
                          </h4>
                          
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <div className="block text-xs font-medium text-gray-600 mb-1">Total NF</div>
                              <input
                                type="number"
                                value={item.quantidade}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                            
                            <div>
                              <div className="block text-xs font-medium text-gray-700 mb-1">Online</div>
                              <input
                                type="number"
                                min="0"
                                max={item.quantidade}
                                step="0.01"
                                value={quantidadesOnline[item.id] ?? item.quantidade_online ?? 0}
                                onChange={(e) => {
                                  const valor = Number.parseFloat(e.target.value) || 0;
                                  setQuantidadesOnline({
                                    ...quantidadesOnline,
                                    [item.id]: Math.min(valor, item.quantidade)
                                  });
                                }}
                                className="w-full px-3 py-2 border-2 border-blue-400 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base font-semibold"
                                placeholder="0"
                              />
                            </div>
                            
                            <div>
                              <div className="block text-xs font-medium text-gray-600 mb-1">Loja</div>
                              <input
                                type="number"
                                value={(item.quantidade - (quantidadesOnline[item.id] ?? item.quantidade_online ?? 0)).toFixed(2)}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                          </div>
                          
                          <div className="mt-3 text-sm text-gray-700 bg-white rounded-lg p-3 border border-gray-300 font-medium">
                            Valor online: R$ {((quantidadesOnline[item.id] ?? item.quantidade_online ?? 0) * item.valor_unitario).toFixed(2)}
                          </div>
                          
                          {(quantidadesOnline[item.id] !== undefined && 
                            quantidadesOnline[item.id] !== item.quantidade_online) ? (
                            <button
                              onClick={() => salvarQuantidadeOnlineItem(
                                notaSelecionada.id, 
                                item.id, 
                                quantidadesOnline[item.id]
                              )}
                              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 mt-3 text-sm"
                            >
                              Salvar Distribuicao
                            </button>
                          ) : (
                            item.quantidade_online !== null && item.quantidade_online !== undefined && (
                              <div className="mt-3 text-sm text-green-700 bg-green-50 rounded-lg p-3 border border-green-200 flex items-center justify-center font-medium">
                                Salvo: {item.quantidade_online} online / {(item.quantidade - item.quantidade_online).toFixed(2)} loja
                              </div>
                            )
                          )}
                        </div>
                      )}

                      {mostrarTratativaItem && (
                        <div className="border-t border-emerald-200 bg-emerald-50/60 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                            <div>
                              <h4 className="font-semibold text-emerald-900">Conferencia fisica</h4>
                              <p className="text-xs text-emerald-800">
                                {podeEditarQuantidadesItem
                                  ? 'Ajuste apenas o que realmente entrou, o que faltou e o que veio avariado.'
                                  : 'Quantidade ja lancada no estoque. Ajuste aqui a tratativa e a observacao da divergencia.'}
                              </p>
                            </div>
                            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-semibold ${
                              conferenciaItem.temDivergencia
                                ? 'bg-orange-100 text-orange-800 border-orange-200'
                                : 'bg-green-100 text-green-800 border-green-200'
                            }`}>
                              {conferenciaItem.temDivergencia ? `Divergencia: ${conferenciaItem.statusConferencia}` : 'OK'}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Qtd NF</label>
                              <input
                                type="number"
                                value={conferenciaItem.quantidadeNF}
                                disabled
                                className="w-full rounded border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-semibold"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Qtd recebida</label>
                              <input
                                type="number"
                                min="0"
                                max={conferenciaItem.quantidadeNF}
                                step="0.01"
                                disabled={!podeEditarQuantidadesItem}
                                value={conferenciaItens[item.id]?.quantidade_conferida ?? conferenciaItem.quantidadeConferida}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'quantidade_conferida', e.target.value)}
                                className={`w-full rounded border px-3 py-2 text-sm font-semibold focus:ring-2 focus:ring-emerald-500 ${
                                  podeEditarQuantidadesItem
                                    ? 'border-emerald-300'
                                    : 'border-gray-300 bg-gray-100 text-gray-600'
                                }`}
                              />
                              <div className="mt-1 text-[11px] text-emerald-700 font-medium">Entra no estoque</div>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Qtd avariada</label>
                              <input
                                type="number"
                                min="0"
                                max={Math.max(0, conferenciaItem.quantidadeNF - conferenciaItem.quantidadeConferida)}
                                step="0.01"
                                disabled={!podeEditarQuantidadesItem}
                                value={conferenciaItens[item.id]?.quantidade_avariada ?? conferenciaItem.quantidadeAvariada}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'quantidade_avariada', e.target.value)}
                                className={`w-full rounded border px-3 py-2 text-sm font-semibold focus:ring-2 focus:ring-orange-500 ${
                                  podeEditarQuantidadesItem
                                    ? 'border-orange-300'
                                    : 'border-gray-300 bg-gray-100 text-gray-600'
                                }`}
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Qtd faltante</label>
                              <input
                                type="number"
                                value={conferenciaItem.quantidadeFaltante.toFixed(2)}
                                disabled
                                className="w-full rounded border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-semibold"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-3 mt-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Tratativa sugerida</label>
                              <select
                                value={conferenciaItens[item.id]?.acao_sugerida ?? conferenciaItem.acaoSugerida}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'acao_sugerida', e.target.value)}
                                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                              >
                                {ACAO_CONFERENCIA_OPCOES.map((opcao) => (
                                  <option key={opcao.value} value={opcao.value}>
                                    {opcao.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Observacao</label>
                              <input
                                type="text"
                                value={conferenciaItens[item.id]?.observacao_conferencia ?? conferenciaItem.observacaoConferencia}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'observacao_conferencia', e.target.value)}
                                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                                placeholder="Ex.: faltou 1 unidade, embalagem avariada, solicitar reposicao..."
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {notaSelecionada.status === 'processada' && item.produto_id && (
                      <div className="mt-3 pt-3 border-t bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <span className="text-blue-800 font-semibold">Lancado no estoque:</span>
                        <span className="ml-2">{item.produto_nome}</span>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            </div>

            {/* Rodape com Acoes */}
            {notaSelecionada.status === 'pendente' && (
              <div className="sticky bottom-0 bg-white border-t px-6 py-4 space-y-3">
                {/* Secao de Rateio - ANTES de processar */}
                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-700">
                      Distribuicao (informativo para relatorios)
                    </h4>
                    <div className="text-xs text-gray-500">
                      Estoque unificado - Classificacao apenas para analises
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'loja')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'loja'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Loja
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'online')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'online'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Online
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'parcial')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'parcial'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Parcial
                    </button>
                    
                    {(notaSelecionada.percentual_online > 0 || notaSelecionada.tipo_rateio) && (
                      <div className="ml-auto flex gap-3 text-xs text-gray-600">
                        <span>Online: {(notaSelecionada.percentual_online || 0).toFixed(0)}%</span>
                        <span>Loja: {(notaSelecionada.percentual_loja || 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>

                  {tipoRateio === 'parcial' && (
                    <div className="mt-2 text-xs text-gray-600 bg-gray-100 rounded p-2">
                      Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima. O sistema calcula automaticamente a % baseado nos valores.
                    </div>
                  )}
                </div>

                {/* Barra de Status e Botoes de Acao */}
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    {notaSelecionada.itens.filter(i => i.produto_id).length} de {notaSelecionada.itens.length} produtos vinculados
                  </div>
                  <div className="flex gap-3">
                    {notaSelecionada.entrada_estoque_realizada ? (
                      <button
                        onClick={() => reverterNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                        disabled={loading}
                        className="px-6 py-2 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:bg-gray-400"
                      >
                        {loading ? 'Revertendo...' : 'Reverter Entrada'}
                      </button>
                    ) : (
                      <>
                        {!notaSelecionada.entrada_estoque_realizada && (
                          <button
                            onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                            disabled={loading}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400"
                          >
                            Excluir Nota
                          </button>
                        )}
                        {notaSelecionada.itens.some(i => i.produto_id) && (
                          <>
                            <button
                              onClick={() => carregarPreviewProcessamento(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400"
                            >
                              Ajuste de custo
                            </button>
                            <button
                              onClick={() => processarNota(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
                            >
                              {loading ? 'Processando...' : 'Processar Nota'}
                            </button>
                          </>
                        )}
                      </>
                    )}
                    <button
                      onClick={() => {
                        setMostrarDetalhes(false);
                        setNotaSelecionada(null);
                      }}
                      className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default EntradaXmlDetalhesModal;
