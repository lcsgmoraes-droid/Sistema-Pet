import PropTypes from "prop-types";
import { ArrowLeft, CheckCircle2, Download, FileText, X } from "lucide-react";
import CardFiscal from "../CardFiscal";
import { formatMoneyBRL } from "../../utils/formatters";
import ActionButton from "../ui/ActionButton";

function formatarValorFiscal(valor, casas = 4) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function obterCustoAquisicaoItem(item) {
  return Number(
    item?.custo_aquisicao_unitario ??
      item?.custo_aquisicao_unitario_nf ??
      item?.composicao_custo?.custo_aquisicao_unitario ??
      item?.custo_unitario_efetivo ??
      item?.custo_unitario_efetivo_nf ??
      item?.valor_unitario ??
      0,
  );
}

function StatusBadge({ status }) {
  const styles = {
    pendente: "bg-yellow-200 text-yellow-800",
    processada: "bg-green-200 text-green-800",
    cancelada: "bg-red-200 text-red-800",
    erro: "bg-red-300 text-red-900",
  };
  const labels = {
    pendente: "Pendente",
    processada: "Conciliada",
    cancelada: "Cancelada",
    erro: "Erro",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles[status] || "bg-gray-200"}`}
    >
      {labels[status] || String(status || "").toUpperCase()}
    </span>
  );
}

StatusBadge.propTypes = {
  status: PropTypes.string,
};

StatusBadge.defaultProps = {
  status: "",
};

function EntradaXmlVisualizacaoNotaModal({
  aberto,
  baixarDocumentoNota,
  documentoBaixando,
  notaSelecionada,
  resumoConferenciaAtual,
  metaConferenciaAtual,
  onClose,
  onAbrirConferencia,
  onAbrirDetalhes,
  onAjustarCustos,
}) {
  if (!aberto || !notaSelecionada) return null;

  const itens = notaSelecionada.itens || [];
  const temProdutosVinculados = Number(notaSelecionada.produtos_vinculados || 0) > 0;
  const podeAbrirProcessamento =
    ["pendente", "processada"].includes(notaSelecionada.status) && temProdutosVinculados;
  const textoBotaoProcessamento =
    notaSelecionada.status === "processada"
      ? "Lancar movimentos pendentes"
      : "Revisar acoes e processar";

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/50">
      <div className="flex h-full w-full flex-col overflow-hidden bg-slate-50">
        <div className="shrink-0 border-b border-slate-200 bg-white">
          <div className="mx-auto flex w-full max-w-[1600px] items-center gap-3 px-4 py-2.5">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 items-center gap-2 rounded-lg px-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Voltar</span>
            </button>

            <div className="min-w-0 flex-1 border-l border-slate-200 pl-3">
              <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                <h2 className="truncate text-lg font-bold text-slate-900">
                  NF-e {notaSelecionada.numero_nota}
                </h2>
                <span className="text-xs text-slate-400">Serie {notaSelecionada.serie}</span>
                <StatusBadge status={notaSelecionada.status} />
              </div>
              <p className="truncate text-xs text-slate-500">{notaSelecionada.fornecedor_nome}</p>
            </div>

            {notaSelecionada.serie !== "PDF" && (
              <div className="flex shrink-0 items-center gap-2">
                <ActionButton
                  disabled={Boolean(documentoBaixando)}
                  icon={FileText}
                  intent="pdf"
                  loading={documentoBaixando === "pdf"}
                  onClick={() => baixarDocumentoNota("pdf")}
                  size="sm"
                >
                  <span className="hidden md:inline">Baixar PDF</span>
                  <span className="md:hidden">PDF</span>
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
                  <span className="hidden md:inline">Baixar XML</span>
                  <span className="md:hidden">XML</span>
                </ActionButton>
              </div>
            )}

            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
              title="Fechar"
              aria-label="Fechar visualizacao da nota"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1600px] space-y-3 p-3 md:p-4">
            <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                    <div className="min-w-0">
                      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                        Fornecedor
                      </div>
                      <div className="truncate font-semibold text-slate-800">
                        {notaSelecionada.fornecedor_nome}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                        Emissao
                      </div>
                      <div className="font-semibold text-slate-700">
                        {new Date(notaSelecionada.data_emissao).toLocaleDateString("pt-BR")}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                        CNPJ
                      </div>
                      <div className="font-mono text-xs font-medium text-slate-600">
                        {notaSelecionada.fornecedor_cnpj}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex min-w-0 items-center gap-2 border-t border-slate-100 pt-2 text-xs text-slate-500">
                    <span className="shrink-0 font-medium">Chave</span>
                    <span className="truncate font-mono" title={notaSelecionada.chave_acesso}>
                      {notaSelecionada.chave_acesso}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 xl:justify-end">
                  <div className="min-w-[112px] rounded-lg bg-emerald-50 px-3 py-2">
                    <div className="text-[11px] font-medium text-emerald-700">Valor total</div>
                    <div className="font-bold text-emerald-700">
                      {formatMoneyBRL(notaSelecionada.valor_total || 0)}
                    </div>
                  </div>
                  <div className="min-w-[82px] rounded-lg bg-slate-100 px-3 py-2">
                    <div className="text-[11px] text-slate-500">Itens</div>
                    <div className="font-bold text-slate-800">{itens.length}</div>
                  </div>
                  <div className="min-w-[82px] rounded-lg bg-emerald-50 px-3 py-2">
                    <div className="text-[11px] text-emerald-700">Vinculados</div>
                    <div className="font-bold text-emerald-700">
                      {notaSelecionada.produtos_vinculados}
                    </div>
                  </div>
                  <div className="min-w-[82px] rounded-lg bg-amber-50 px-3 py-2">
                    <div className="text-[11px] text-amber-700">Pendentes</div>
                    <div className="font-bold text-amber-700">
                      {notaSelecionada.produtos_nao_vinculados}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {resumoConferenciaAtual && (
              <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 px-3 py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
                    <div
                      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || "bg-gray-100 text-gray-700 border-gray-200"}`}
                    >
                      {metaConferenciaAtual?.label || "Nao conferida"}
                    </div>
                    <p className="text-sm text-slate-600">
                      Entrada prevista:{" "}
                      <strong className="text-slate-800">
                        {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}
                      </strong>
                      {resumoConferenciaAtual.itens_com_divergencia > 0 && (
                        <>
                          <span className="mx-2 text-slate-300">|</span>
                          Divergencias:{" "}
                          <strong className="text-orange-700">
                            {resumoConferenciaAtual.itens_com_divergencia}
                          </strong>
                        </>
                      )}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onAbrirConferencia(notaSelecionada.id)}
                    className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white transition-colors hover:bg-emerald-700"
                  >
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    Conferencia
                  </button>
                </div>
              </section>
            )}

            <section>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800">Itens da Nota</h3>
                <span className="text-xs text-slate-500">{itens.length} produto(s)</span>
              </div>
              <div className="space-y-2">
                {itens.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-xl border border-slate-200 bg-white p-3"
                  >
                    <div className="mb-1.5 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-sm font-semibold text-slate-800">{item.descricao}</div>
                        <div className="mt-0.5 text-[11px] text-slate-500">
                          Codigo: {item.codigo_produto} | NCM: {item.ncm}
                        </div>
                      </div>
                      {item.vinculado ? (
                        <span className="rounded-full bg-green-100 px-2 py-1 text-[11px] font-semibold text-green-800">
                          Vinculado
                        </span>
                      ) : (
                        <span className="rounded-full bg-orange-100 px-2 py-1 text-[11px] font-semibold text-orange-800">
                          Nao Vinculado
                        </span>
                      )}
                    </div>

                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-slate-100 pt-2 text-xs md:grid-cols-5">
                      <div>
                        <span className="text-gray-600">Qtd:</span>
                        <div className="font-semibold">{item.quantidade}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Unit:</span>
                        <div className="font-semibold text-rose-700">
                          {formatMoneyBRL(item.valor_unitario || 0)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Custo Aq.:</span>
                        <div className="font-semibold text-amber-700">
                          R$ {formatarValorFiscal(obterCustoAquisicaoItem(item), 4)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Total fiscal:</span>
                        <div className="font-semibold text-rose-700">
                          {formatMoneyBRL(item.valor_total || 0)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">CFOP:</span>
                        <div className="font-semibold">{item.cfop}</div>
                      </div>
                    </div>

                    <CardFiscal
                      nota={notaSelecionada}
                      item={item}
                      composicao={item.composicao_custo}
                    />

                    {(item.lote || item.data_validade) && (
                      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 rounded-lg bg-slate-50 px-3 py-2 text-xs">
                        {item.lote && (
                          <div>
                            <span className="text-slate-500">Lote: </span>
                            <span className="font-semibold text-slate-800">{item.lote}</span>
                          </div>
                        )}
                        {item.data_validade && (
                          <div>
                            <span className="text-slate-500">Validade: </span>
                            <span className="font-semibold text-slate-800">
                              {new Date(item.data_validade).toLocaleDateString("pt-BR")}
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {item.vinculado && item.produto_nome && (
                      <div className="mt-2 border-t border-slate-100 pt-2">
                        <span className="text-xs text-gray-600">Produto vinculado: </span>
                        <span className="text-xs font-semibold text-blue-600">
                          {item.produto_nome}
                        </span>
                      </div>
                    )}

                    {item.tem_divergencia && (
                      <div className="mt-3 rounded-lg border border-orange-200 bg-orange-50 p-3 text-xs text-orange-900">
                        <div className="font-semibold mb-1">Divergencia registrada</div>
                        <div>
                          Estoque: {formatarValorFiscal(item.quantidade_conferida, 2)} | Avaria:{" "}
                          {formatarValorFiscal(item.quantidade_avariada, 2)} | Faltante:{" "}
                          {formatarValorFiscal(item.quantidade_faltante, 2)}
                        </div>
                        {item.observacao_conferencia && (
                          <div className="mt-1">Obs.: {item.observacao_conferencia}</div>
                        )}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
          <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-600">
              {notaSelecionada.entrada_estoque_realizada ? (
                <span className="text-green-600 font-semibold">Entrada realizada no estoque</span>
              ) : (
                <span className="text-orange-600 font-semibold">Entrada ainda nao processada</span>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {podeAbrirProcessamento && (
                <>
                  {notaSelecionada.status === "pendente" && (
                    <button
                      onClick={() => onAbrirConferencia(notaSelecionada.id)}
                      className="h-9 rounded-lg bg-emerald-600 px-3.5 text-sm font-semibold text-white hover:bg-emerald-700"
                    >
                      Conferencia
                    </button>
                  )}
                  <button
                    onClick={() => onAjustarCustos(notaSelecionada.id)}
                    className="h-9 rounded-lg bg-violet-600 px-3.5 text-sm font-semibold text-white hover:bg-violet-700"
                  >
                    {textoBotaoProcessamento}
                  </button>
                </>
              )}
              {notaSelecionada.status === "pendente" && (
                <button
                  onClick={() => onAbrirDetalhes(notaSelecionada.id)}
                  className="h-9 rounded-lg bg-blue-600 px-3.5 text-sm font-semibold text-white hover:bg-blue-700"
                >
                  Vincular Produtos
                </button>
              )}
              <button
                onClick={onClose}
                className="h-9 rounded-lg border border-slate-300 px-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Voltar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

EntradaXmlVisualizacaoNotaModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  baixarDocumentoNota: PropTypes.func.isRequired,
  documentoBaixando: PropTypes.string.isRequired,
  notaSelecionada: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    numero_nota: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    serie: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    data_emissao: PropTypes.string,
    status: PropTypes.string,
    valor_total: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    fornecedor_nome: PropTypes.string,
    fornecedor_cnpj: PropTypes.string,
    chave_acesso: PropTypes.string,
    produtos_vinculados: PropTypes.number,
    produtos_nao_vinculados: PropTypes.number,
    entrada_estoque_realizada: PropTypes.bool,
    itens: PropTypes.arrayOf(PropTypes.object),
  }),
  resumoConferenciaAtual: PropTypes.shape({
    quantidade_total_conferida: PropTypes.number,
    itens_com_divergencia: PropTypes.number,
  }),
  metaConferenciaAtual: PropTypes.shape({
    cls: PropTypes.string,
    label: PropTypes.string,
  }),
  onClose: PropTypes.func.isRequired,
  onAbrirConferencia: PropTypes.func.isRequired,
  onAbrirDetalhes: PropTypes.func.isRequired,
  onAjustarCustos: PropTypes.func.isRequired,
};

EntradaXmlVisualizacaoNotaModal.defaultProps = {
  notaSelecionada: null,
  resumoConferenciaAtual: null,
  metaConferenciaAtual: null,
};

export default EntradaXmlVisualizacaoNotaModal;
