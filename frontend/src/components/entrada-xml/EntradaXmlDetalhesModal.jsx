import { AlertTriangle, Download, FileText, X } from "lucide-react";
import EntradaXmlDetalhesConferenciaPanel from "./EntradaXmlDetalhesConferenciaPanel";
import EntradaXmlDetalhesFooter from "./EntradaXmlDetalhesFooter";
import EntradaXmlDetalhesItemCard from "./EntradaXmlDetalhesItemCard";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";
import SegmentedControl from "../ui/SegmentedControl";
import { formatMoneyBRL } from "../../utils/formatters";

function EntradaXmlDetalhesModal({
  acaoConferenciaOpcoes,
  aberto,
  abrirModalCriarProduto,
  aplicarMultiplicadorPackAoItem,
  atualizarCampoConferenciaItem,
  atualizarFiltroProduto,
  baixarDocumentoNota,
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
  documentoBaixando,
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-2 md:p-3">
          <div className="flex max-h-[96vh] w-[96vw] max-w-[1600px] flex-col overflow-hidden rounded-xl bg-slate-50 shadow-2xl">
            {/* Cabecalho */}
            <div className="z-10 flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-2.5 md:px-5">
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-bold text-slate-900">
                  {notaSelecionada.serie === "PDF" ? "Detalhes da entrada PDF" : "Detalhes da NF-e"}
                </h2>
                <p className="truncate text-xs text-slate-500" title={notaSelecionada.chave_acesso}>
                  {notaSelecionada.serie === "PDF" ? "Identificador interno" : "Chave"}:{" "}
                  {notaSelecionada.chave_acesso}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                {notaSelecionada.serie !== "PDF" && (
                  <>
                    <ActionButton
                      disabled={Boolean(documentoBaixando)}
                      icon={FileText}
                      intent="pdf"
                      loading={documentoBaixando === "pdf"}
                      onClick={() => baixarDocumentoNota("pdf")}
                      size="sm"
                    >
                      Baixar PDF
                    </ActionButton>
                    <ActionButton
                      disabled={Boolean(documentoBaixando)}
                      icon={Download}
                      intent="neutral"
                      loading={documentoBaixando === "xml"}
                      onClick={() => baixarDocumentoNota("xml")}
                      size="sm"
                      tone="soft"
                    >
                      Baixar XML
                    </ActionButton>
                  </>
                )}
                <IconActionButton
                  aria-label="Fechar detalhes da nota"
                  icon={X}
                  intent="neutral"
                  onClick={() => {
                    setMostrarDetalhes(false);
                    setNotaSelecionada(null);
                  }}
                  size="sm"
                  tone="ghost"
                />
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {/* Informacoes da Nota */}
              <div className="border-b border-slate-200 bg-white px-4 py-2.5 md:px-5">
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-[minmax(0,1fr)_140px_160px]">
                  <div className="min-w-0">
                    <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      Fornecedor
                    </span>
                    <div className="truncate font-semibold text-slate-800">
                      {notaSelecionada.fornecedor_nome}
                    </div>
                    <div className="text-xs text-slate-500">{notaSelecionada.fornecedor_cnpj}</div>
                    {notaSelecionada.fornecedor_id && (
                      <span className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                        Cadastrado
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      Emissao
                    </span>
                    <div className="font-semibold text-slate-700">
                      {new Date(notaSelecionada.data_emissao).toLocaleDateString("pt-BR")}
                    </div>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      Valor total
                    </span>
                    <div className="text-base font-bold text-emerald-600">
                      {formatMoneyBRL(notaSelecionada.valor_total || 0)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Alerta de Fornecedor Novo - Versao Compacta */}
              {notaSelecionada.fornecedor_id &&
                notaSelecionada.fornecedor_criado_automaticamente && (
                  <div className="border-b border-blue-200 bg-blue-50 px-4 py-2 md:px-5">
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
                <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 md:px-5">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <strong>Entrada importada por PDF.</strong> Revise vinculos, custos e dados
                      fiscais antes de processar. O PDF nao traz chave NF-e real, CFOP, NCM,
                      impostos, lotes ou validacao SEFAZ.
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
              <div className="px-4 py-2.5 md:px-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-800">
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
                        size="sm"
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
                          size="sm"
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

                <div className="space-y-3.5">
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
            </div>

            <EntradaXmlDetalhesFooter
              carregarPreviewProcessamento={carregarPreviewProcessamento}
              excluirNota={excluirNota}
              loading={loading}
              notaSelecionada={notaSelecionada}
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
