import { AlertTriangle, X } from "lucide-react";
import EntradaXmlDetalhesConferenciaPanel from "./EntradaXmlDetalhesConferenciaPanel";
import EntradaXmlDetalhesFooter from "./EntradaXmlDetalhesFooter";
import EntradaXmlDetalhesItemCard from "./EntradaXmlDetalhesItemCard";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";
import SegmentedControl from "../ui/SegmentedControl";

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
                <h2 className="text-xl font-bold">
                  {notaSelecionada.serie === "PDF" ? "Detalhes da entrada PDF" : "Detalhes da NF-e"}
                </h2>
                <p className="text-sm text-gray-600">
                  {notaSelecionada.serie === "PDF" ? "Identificador interno" : "Chave"}:{" "}
                  {notaSelecionada.chave_acesso}
                </p>
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
                  <div className="font-semibold">
                    {new Date(notaSelecionada.data_emissao).toLocaleDateString()}
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Valor Total:</span>
                  <div className="font-bold text-lg text-green-600">
                    R$ {(notaSelecionada.valor_total || 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {/* Alerta de Fornecedor Novo - Versao Compacta */}
            {notaSelecionada.fornecedor_id && notaSelecionada.fornecedor_criado_automaticamente && (
              <div className="px-6 py-2 bg-blue-50 border-b border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-blue-800">
                    <strong>{notaSelecionada.fornecedor_nome}</strong> foi cadastrado
                    automaticamente.
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

            {notaSelecionada.serie === "PDF" && (
              <div className="border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-900">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <strong>Entrada importada por PDF.</strong> Revise vinculos, custos e dados
                    fiscais antes de processar. O PDF nao traz chave NF-e real, CFOP, NCM, impostos,
                    lotes ou validacao SEFAZ.
                  </div>
                </div>
              </div>
            )}

            <EntradaXmlDetalhesConferenciaPanel
              conferenciaObservacaoGeral={conferenciaObservacaoGeral}
              criandoPendenciaFornecedor={criandoPendenciaFornecedor}
              desfazendoConferencia={desfazendoConferencia}
              desfazerConferenciaAtual={desfazerConferenciaAtual}
              formatarValorFiscal={formatarValorFiscal}
              gerarPendenciaFornecedor={gerarPendenciaFornecedor}
              gerarRascunhoDevolucao={gerarRascunhoDevolucao}
              gerandoRascunhoDevolucao={gerandoRascunhoDevolucao}
              metaConferenciaAtual={metaConferenciaAtual}
              mostrarCamposConferencia={mostrarCamposConferencia}
              notaSelecionada={notaSelecionada}
              resumoConferenciaAtual={resumoConferenciaAtual}
              salvandoConferencia={salvandoConferencia}
              salvarConferenciaAtual={salvarConferenciaAtual}
              setConferenciaObservacaoGeral={setConferenciaObservacaoGeral}
              setMostrarCamposConferencia={setMostrarCamposConferencia}
            />

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold text-xl text-gray-800">
                    Produtos da Nota ({itensExibidosNota.length}
                    {filtroItensNota === "divergencias" ? ` de ${itensNotaDetalhe.length}` : ""})
                  </h3>
                  {itensComDivergenciaDetalhe.length > 0 && (
                    <p className="mt-1 text-xs text-orange-700">
                      {itensComDivergenciaDetalhe.length} item(ns) com divergencia ou tratativa
                      pendente.
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
                        { value: "todos", label: "Todos" },
                        {
                          value: "divergencias",
                          label: `Com divergencia (${itensComDivergenciaDetalhe.length})`,
                          activeClassName: "bg-orange-100 text-orange-800 shadow-sm",
                          onSelect: () => setMostrarCamposConferencia(true),
                        },
                      ]}
                    />
                  )}

                  {notaSelecionada.status === "pendente" &&
                    notaSelecionada.itens.some((item) => !item.produto_id) && (
                      <ActionButton
                        onClick={criarTodosProdutosNaoVinculados}
                        loading={loading}
                        intent="create"
                        size="md"
                        title="Cria automaticamente todos os produtos nao vinculados com os padrões: Estoque mín: 10, máx: 100, Margem: 50%"
                      >
                        <span>Criar Todos Nao Vinculados</span>
                        <span className="rounded bg-emerald-800 px-2 py-0.5 text-xs text-white">
                          {notaSelecionada.itens.filter((i) => !i.produto_id).length}
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
