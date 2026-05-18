import { X } from 'lucide-react';
import EntradaXmlDetalhesFooter from './EntradaXmlDetalhesFooter';
import EntradaXmlDetalhesItemCard from './EntradaXmlDetalhesItemCard';
import ActionButton from '../ui/ActionButton';
import IconActionButton from '../ui/IconActionButton';
import SegmentedControl from '../ui/SegmentedControl';

function EntradaXmlDetalhesModal({
  acaoConferenciaOpcoes,
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
              <IconActionButton
                aria-label="Fechar detalhes da nota"
                icon={X}
                intent="neutral"
                onClick={() => {
                  setMostrarDetalhes(false);
                  setNotaSelecionada(null);
                }}
                size="md"
                tone="ghost"
              />
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
                  <ActionButton
                    onClick={() => navigate(`/clientes/${notaSelecionada.fornecedor_id}`)}
                    intent="edit"
                    size="xs"
                  >
                    Completar Cadastro
                  </ActionButton>
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
                    <ActionButton
                      onClick={criarTodosProdutosNaoVinculados}
                      loading={loading}
                      intent="create"
                      size="md"
                      title="Cria automaticamente todos os produtos nao vinculados com os padrões: Estoque mín: 10, máx: 100, Margem: 50%"
                    >
                      <span>Criar Todos Nao Vinculados</span>
                      <span className="rounded bg-emerald-800 px-2 py-0.5 text-xs text-white">
                        {notaSelecionada.itens.filter(i => !i.produto_id).length}
                      </span>
                    </ActionButton>
                  )}
                </div>
              </div>
              
              <div className="space-y-3">
                {itensExibidosNota.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                    Nenhum produto encontrado para este filtro.
                  </div>
                )}
                {itensExibidosNota.map((item) => (
                  <EntradaXmlDetalhesItemCard
                    key={item.id}
                    item={item}
                    acaoConferenciaOpcoes={acaoConferenciaOpcoes}
                    abrirModalCriarProduto={abrirModalCriarProduto}
                    aplicarMultiplicadorPackAoItem={aplicarMultiplicadorPackAoItem}
                    atualizarCampoConferenciaItem={atualizarCampoConferenciaItem}
                    atualizarFiltroProduto={atualizarFiltroProduto}
                    buscandoProduto={buscandoProduto}
                    calcularConferenciaItem={calcularConferenciaItem}
                    conferenciaItens={conferenciaItens}
                    desvincularProduto={desvincularProduto}
                    detectarDivergencias={detectarDivergencias}
                    filtroProduto={filtroProduto}
                    formatarOpcaoProduto={formatarOpcaoProduto}
                    formatarValorFiscal={formatarValorFiscal}
                    getConfiancaBadge={getConfiancaBadge}
                    mostrarCamposConferencia={mostrarCamposConferencia}
                    multiplicadoresPack={multiplicadoresPack}
                    notaSelecionada={notaSelecionada}
                    obterConfiguracaoPackItem={obterConfiguracaoPackItem}
                    obterCustoAquisicaoItem={obterCustoAquisicaoItem}
                    quantidadesOnline={quantidadesOnline}
                    resultadosBuscaProduto={resultadosBuscaProduto}
                    salvarQuantidadeOnlineItem={salvarQuantidadeOnlineItem}
                    setFiltroProduto={setFiltroProduto}
                    setMultiplicadoresPack={setMultiplicadoresPack}
                    setQuantidadesOnline={setQuantidadesOnline}
                    setResultadosBuscaProduto={setResultadosBuscaProduto}
                    tipoRateio={tipoRateio}
                    vincularProduto={vincularProduto}
                  />
                ))}
              </div>
            </div>

            <EntradaXmlDetalhesFooter
              carregarPreviewProcessamento={carregarPreviewProcessamento}
              excluirNota={excluirNota}
              loading={loading}
              notaSelecionada={notaSelecionada}
              processarNota={processarNota}
              reverterNota={reverterNota}
              salvarTipoRateio={salvarTipoRateio}
              setMostrarDetalhes={setMostrarDetalhes}
              setNotaSelecionada={setNotaSelecionada}
              tipoRateio={tipoRateio}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default EntradaXmlDetalhesModal;
