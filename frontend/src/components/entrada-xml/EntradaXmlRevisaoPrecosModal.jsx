import PropTypes from "prop-types";
import { formatBRL, formatMoneyBRL, formatPercent } from "../../utils/formatters";
import ExportActionButton from "../ui/ExportActionButton";
import TooltipComposicao from "../TooltipComposicao";

function EntradaXmlRevisaoPrecosModal({
  aberto,
  previewProcessamento,
  filtroCusto,
  setFiltroCusto,
  obterResumoCustoItem,
  exportarRelatorioCustosMaioresCSV,
  exportarRelatorioCustosMaioresPDF,
  gerandoRelatorioCustos,
  baseCalculoMargem,
  setBaseCalculoMargem,
  baseCalculoMargemOpcoes,
  precosAjustados,
  inputsRevisaoPrecos,
  inputsRevisaoCustos,
  buscarHistoricoPrecos,
  atualizarCustoSistema,
  normalizarCamposRevisaoCustos,
  atualizarPrecoVenda,
  normalizarCamposRevisaoPrecos,
  atualizarMargem,
  confirmarProcessamento,
  loading,
  onVoltar,
}) {
  if (!aberto || !previewProcessamento) return null;

  const itensVinculados = (previewProcessamento.itens || []).filter(
    (item) => item.produto_vinculado !== null || item.produto_id !== null,
  );

  const resumoFiltros = itensVinculados.reduce(
    (acc, item) => {
      const variacao = obterResumoCustoItem(item).variacaoCustoPercentual;

      if (variacao > 0) acc.aumentos += 1;
      else if (variacao < 0) acc.reducoes += 1;
      else acc.iguais += 1;

      return acc;
    },
    {
      aumentos: 0,
      reducoes: 0,
      iguais: 0,
    },
  );

  const itensFiltrados = (previewProcessamento.itens || []).filter((item) => {
    const vinculado = item.produto_vinculado !== null || item.produto_id !== null;

    if (!vinculado) return false;

    const custoVariacao = obterResumoCustoItem(item).variacaoCustoPercentual;

    if (filtroCusto === "todos") return true;
    if (filtroCusto === "aumentou") return custoVariacao > 0;
    if (filtroCusto === "diminuiu") return custoVariacao < 0;
    if (filtroCusto === "igual") return custoVariacao === 0;
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/50">
      <div className="bg-white w-full h-full overflow-hidden flex flex-col">
        <div className="bg-slate-900 text-white p-4 md:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                onClick={onVoltar}
                className="px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 text-sm font-semibold transition-colors"
              >
                Voltar
              </button>
              <div>
                <h2 className="text-xl md:text-2xl font-bold">
                  Ajuste de Custos, Precos e Margens
                </h2>
                <p className="text-slate-300 mt-1 text-sm">
                  NF-e {previewProcessamento.numero_nota} - {previewProcessamento.fornecedor_nome}
                </p>
                <p className="text-slate-400 mt-2 text-xs md:text-sm max-w-3xl">
                  O valor fiscal da NF permanece intacto. O ajuste abaixo altera apenas o custo que
                  o sistema vai receber ao processar a entrada no estoque.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="px-4 md:px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-semibold text-gray-700">Filtrar:</span>
            <button
              onClick={() => setFiltroCusto("todos")}
              className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                filtroCusto === "todos"
                  ? "bg-slate-800 text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
              }`}
            >
              Todos ({itensVinculados.length})
            </button>

            {resumoFiltros.aumentos > 0 && (
              <button
                onClick={() => setFiltroCusto("aumentou")}
                className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                  filtroCusto === "aumentou"
                    ? "bg-red-600 text-white"
                    : "bg-white border border-red-200 text-red-700 hover:bg-red-50"
                }`}
              >
                {resumoFiltros.aumentos} custo{resumoFiltros.aumentos > 1 ? "s" : ""} maior
                {resumoFiltros.aumentos > 1 ? "es" : ""}
              </button>
            )}

            {resumoFiltros.reducoes > 0 && (
              <button
                onClick={() => setFiltroCusto("diminuiu")}
                className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                  filtroCusto === "diminuiu"
                    ? "bg-green-700 text-white"
                    : "bg-white border border-green-200 text-green-700 hover:bg-green-50"
                }`}
              >
                {resumoFiltros.reducoes} custo{resumoFiltros.reducoes > 1 ? "s" : ""} menor
                {resumoFiltros.reducoes > 1 ? "es" : ""}
              </button>
            )}

            {resumoFiltros.iguais > 0 && (
              <button
                onClick={() => setFiltroCusto("igual")}
                className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                  filtroCusto === "igual"
                    ? "bg-gray-700 text-white"
                    : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
                }`}
              >
                {resumoFiltros.iguais} sem alteracao
              </button>
            )}

            <div className="ml-auto flex items-center gap-2">
              <ExportActionButton
                type="csv"
                onClick={exportarRelatorioCustosMaioresCSV}
                disabled={gerandoRelatorioCustos || resumoFiltros.aumentos === 0}
                title="Exportar CSV dos custos maiores"
              >
                {gerandoRelatorioCustos ? "Gerando..." : "Exportar CSV custos maiores"}
              </ExportActionButton>
              <ExportActionButton
                type="pdf"
                onClick={exportarRelatorioCustosMaioresPDF}
                disabled={gerandoRelatorioCustos || resumoFiltros.aumentos === 0}
                title="Exportar PDF dos custos maiores"
              >
                {gerandoRelatorioCustos ? "Gerando..." : "Exportar PDF custos maiores"}
              </ExportActionButton>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="space-y-6">
            <div className="rounded-xl border border-sky-200 bg-sky-50 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                    <span>Base da margem</span>
                    <span
                      className="text-slate-400 cursor-help"
                      title={
                        'A base da margem muda a conta do preco e da margem nesta tela. O custo gravado ao processar continua sendo o campo "Custo no sistema".'
                      }
                    >
                      i
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    Padrao em custo da NF. Se quiser, voce pode recalcular usando o custo que vai
                    para o sistema, sem alterar o valor fiscal da nota.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {baseCalculoMargemOpcoes.map((opcao) => (
                    <button
                      key={opcao.value}
                      onClick={() => setBaseCalculoMargem(opcao.value)}
                      title={opcao.descricao}
                      className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
                        baseCalculoMargem === opcao.value
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      {opcao.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {itensFiltrados
              .map((item) => {
                const resumoCusto = obterResumoCustoItem(item);
                const produtoVinc = resumoCusto.produto;

                if (!produtoVinc.produto_id) return null;

                const custoItemId = item.item_id ?? item.id;
                const custoVariacao = resumoCusto.variacaoCustoPercentual;
                const custoAumentou = custoVariacao > 0;
                const margemReferencia = resumoCusto.margemReferencia;
                const margemProjetadaComCustoNovo = resumoCusto.margemProjetada;

                const precosAtuais = precosAjustados[produtoVinc.produto_id] || {
                  preco_venda: produtoVinc.preco_venda_atual || 0,
                  margem: margemProjetadaComCustoNovo,
                };

                const camposTexto = inputsRevisaoPrecos[produtoVinc.produto_id] || {
                  preco_venda: formatBRL(precosAtuais.preco_venda),
                  margem: formatBRL(precosAtuais.margem),
                };
                const custoTexto =
                  inputsRevisaoCustos[custoItemId] || formatBRL(resumoCusto.custoSistema);
                const custoBaseMargem = resumoCusto.baseMargem.valor;
                const custoBaseMargemDiferenteDoSistema =
                  Math.abs(custoBaseMargem - resumoCusto.custoSistema) > 0.0001;
                const descricaoBaseMargem = resumoCusto.baseMargem.fallback
                  ? `${resumoCusto.baseMargem.label} (${formatMoneyBRL(custoBaseMargem || 0)}) - sem custo informado, usando a NF`
                  : `${resumoCusto.baseMargem.label} (${formatMoneyBRL(custoBaseMargem || 0)})`;

                const tooltipMargem =
                  `Margem = ((Preco de Venda - Custo) / Preco de Venda) x 100\n` +
                  `Base ativa: ${resumoCusto.baseMargem.label}\n` +
                  `Com os valores atuais:\n` +
                  `(${formatBRL(precosAtuais.preco_venda)} - ${formatBRL(custoBaseMargem || 0)}) / ${formatBRL(precosAtuais.preco_venda)} x 100\n` +
                  `Resultado: ${formatPercent(precosAtuais.margem)}`;

                return (
                  <div
                    key={item.item_id}
                    className="border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all"
                  >
                    <div className="bg-gray-100 border-b border-gray-200 p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-semibold text-xl text-gray-900 mb-1">
                            {produtoVinc.produto_nome}
                          </h3>
                          <p className="text-sm text-gray-600">
                            SKU: {produtoVinc.produto_codigo || "Nao informado"} | EAN:{" "}
                            {produtoVinc.produto_ean || "Nao informado"}
                          </p>
                        </div>
                        <div className="text-right">
                          <button
                            onClick={() =>
                              buscarHistoricoPrecos(
                                produtoVinc.produto_id,
                                produtoVinc.produto_nome,
                              )
                            }
                            className="px-3 py-1 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded text-sm font-medium transition-colors"
                          >
                            Historico
                          </button>
                          <div className="mt-1 text-sm text-gray-700">
                            Quantidade{" "}
                            <strong>
                              {item.quantidade_efetiva_nf ||
                                item.quantidade ||
                                item.quantidade_nf ||
                                0}
                            </strong>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="p-5 bg-white space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div>
                          <div className="text-xs text-gray-500 mb-1 flex items-center justify-between">
                            <span>Custo Anterior</span>
                          </div>
                          <div className="text-2xl font-bold text-gray-700">
                            {formatMoneyBRL(resumoCusto.custoAnterior || 0)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1 flex items-center justify-between">
                            <span>Custo da NF</span>
                            <TooltipComposicao
                              custo={resumoCusto.custoNF}
                              composicao={item.composicao_custo}
                              texto="detalhar"
                            />
                          </div>
                          <div className="text-2xl font-bold text-gray-900">
                            {formatMoneyBRL(resumoCusto.custoNF || 0)}
                          </div>
                          <div className="mt-1 text-xs text-gray-500">Valor fiscal da nota</div>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1 font-semibold">
                            Custo no sistema
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                              R$
                            </span>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={custoTexto}
                              onChange={(event) => atualizarCustoSistema(item, event.target.value)}
                              onBlur={() => normalizarCamposRevisaoCustos(item)}
                              className="w-full pl-10 pr-3 py-3 border-2 border-amber-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                            />
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            {resumoCusto.custoManual
                              ? "Custo manual aplicado so no processamento; a NF fiscal nao sera alterada"
                              : "Igual ao custo fiscal da NF"}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">Variacao</div>
                          <div
                            className={`text-2xl font-bold ${custoAumentou ? "text-red-600" : custoVariacao < 0 ? "text-emerald-700" : "text-gray-600"}`}
                          >
                            {custoVariacao > 0 ? "+" : custoVariacao < 0 ? "-" : "="}{" "}
                            {formatPercent(Math.abs(custoVariacao))}
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            Comparado ao custo atual do cadastro
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2">
                            Preco de Venda
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                              R$
                            </span>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={camposTexto.preco_venda}
                              onChange={(event) =>
                                atualizarPrecoVenda(
                                  produtoVinc.produto_id,
                                  event.target.value,
                                  custoBaseMargem,
                                )
                              }
                              onBlur={() => normalizarCamposRevisaoPrecos(produtoVinc.produto_id)}
                              className="w-full pl-10 pr-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            Anterior: {formatMoneyBRL(produtoVinc.preco_venda_atual || 0)}
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                            Margem de Lucro
                            <span className="text-gray-400 cursor-help" title={tooltipMargem}>
                              i
                            </span>
                          </label>
                          <div className="relative">
                            <input
                              type="text"
                              inputMode="decimal"
                              value={camposTexto.margem}
                              onChange={(event) =>
                                atualizarMargem(
                                  produtoVinc.produto_id,
                                  event.target.value,
                                  custoBaseMargem,
                                )
                              }
                              onBlur={() => normalizarCamposRevisaoPrecos(produtoVinc.produto_id)}
                              className="w-full pr-10 pl-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
                              %
                            </span>
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            Base ativa: {descricaoBaseMargem}
                            {baseCalculoMargem === "nf" && custoBaseMargemDiferenteDoSistema
                              ? ` | O custo salvo no processamento continua sendo ${formatMoneyBRL(resumoCusto.custoSistema || 0)} em "Custo no sistema"`
                              : ""}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3">
                          Referencia dos valores anteriores
                        </h4>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-xs text-gray-600 mb-1">Custo Anterior</div>
                            <div className="text-lg font-bold text-gray-700">
                              {formatMoneyBRL(produtoVinc.custo_anterior || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-600 mb-1">Preco Anterior</div>
                            <div className="text-lg font-bold text-gray-700">
                              {formatMoneyBRL(produtoVinc.preco_venda_atual || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-600 mb-1">Margem Anterior</div>
                            <div className="text-lg font-bold text-gray-700">
                              {formatPercent(margemReferencia)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
              .filter(Boolean)}
          </div>
        </div>

        <div className="border-t border-gray-200 p-4 md:p-6 bg-gray-50 flex flex-wrap justify-between items-center gap-3">
          <button
            onClick={onVoltar}
            className="px-6 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-semibold transition-colors"
          >
            Voltar
          </button>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm text-gray-600">Valor Total da Nota</div>
              <div className="text-2xl font-bold text-green-600">
                R$ {Number(previewProcessamento.valor_total || 0).toFixed(2)}
              </div>
            </div>
            <button
              onClick={confirmarProcessamento}
              disabled={loading}
              className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold text-lg shadow disabled:opacity-50 transition-all"
            >
              {loading ? "Processando..." : "Confirmar e Processar Nota"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

EntradaXmlRevisaoPrecosModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  previewProcessamento: PropTypes.shape({
    numero_nota: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    fornecedor_nome: PropTypes.string,
    valor_total: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    itens: PropTypes.arrayOf(PropTypes.object),
  }),
  filtroCusto: PropTypes.string.isRequired,
  setFiltroCusto: PropTypes.func.isRequired,
  obterResumoCustoItem: PropTypes.func.isRequired,
  exportarRelatorioCustosMaioresCSV: PropTypes.func.isRequired,
  exportarRelatorioCustosMaioresPDF: PropTypes.func.isRequired,
  gerandoRelatorioCustos: PropTypes.bool.isRequired,
  baseCalculoMargem: PropTypes.string.isRequired,
  setBaseCalculoMargem: PropTypes.func.isRequired,
  baseCalculoMargemOpcoes: PropTypes.arrayOf(PropTypes.object).isRequired,
  precosAjustados: PropTypes.objectOf(PropTypes.object).isRequired,
  inputsRevisaoPrecos: PropTypes.objectOf(PropTypes.object).isRequired,
  inputsRevisaoCustos: PropTypes.objectOf(PropTypes.string).isRequired,
  buscarHistoricoPrecos: PropTypes.func.isRequired,
  atualizarCustoSistema: PropTypes.func.isRequired,
  normalizarCamposRevisaoCustos: PropTypes.func.isRequired,
  atualizarPrecoVenda: PropTypes.func.isRequired,
  normalizarCamposRevisaoPrecos: PropTypes.func.isRequired,
  atualizarMargem: PropTypes.func.isRequired,
  confirmarProcessamento: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  onVoltar: PropTypes.func.isRequired,
};

EntradaXmlRevisaoPrecosModal.defaultProps = {
  previewProcessamento: null,
};

export default EntradaXmlRevisaoPrecosModal;
