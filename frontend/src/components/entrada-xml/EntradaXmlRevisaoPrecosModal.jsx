import { useState } from "react";
import PropTypes from "prop-types";
import { ArrowLeft, Info } from "lucide-react";
import { formatBRL, formatMoneyBRL, formatPercent } from "../../utils/formatters";
import ExportActionButton from "../ui/ExportActionButton";
import TooltipComposicao from "../TooltipComposicao";

function EntradaXmlRevisaoPrecosModal({
  aberto,
  previewProcessamento,
  acoesProcessamento,
  filtroCusto,
  setFiltroCusto,
  obterResumoCustoItem,
  exportarRelatorioCustosMaioresCSV,
  exportarRelatorioCustosMaioresPDF,
  gerandoRelatorioCustos,
  precosAjustados,
  inputsRevisaoPrecos,
  inputsRevisaoCustos,
  buscarHistoricoPrecos,
  atualizarCustoSistema,
  normalizarCamposRevisaoCustos,
  atualizarPrecoVenda,
  normalizarCamposRevisaoPrecos,
  atualizarMargem,
  setAcaoProcessamento,
  confirmarProcessamento,
  loading,
  onVoltar,
}) {
  const [mostrarConfirmacaoProcessamento, setMostrarConfirmacaoProcessamento] = useState(false);

  if (!aberto || !previewProcessamento) return null;

  const itensVinculados = (previewProcessamento.itens || []).filter(
    (item) => item.produto_vinculado !== null || item.produto_id !== null,
  );
  const precosAlterados = Object.entries(precosAjustados).filter(([produtoId, dados]) => {
    const itemOriginal = (previewProcessamento.itens || []).find(
      (item) =>
        item.produto_vinculado && String(item.produto_vinculado.produto_id) === String(produtoId),
    );
    return (
      itemOriginal &&
      itemOriginal.produto_vinculado &&
      Number(dados.preco_venda) !== Number(itemOriginal.produto_vinculado.preco_venda_atual)
    );
  }).length;
  const custosAtualizados = itensVinculados.filter((item) => {
    const resumo = obterResumoCustoItem(item);
    return Math.abs(Number(resumo.custoSistema || 0) - Number(resumo.custoAnterior || 0)) > 0.0001;
  }).length;
  const itensComValidade = itensVinculados.filter((item) => Boolean(item.data_validade)).length;
  const itensSemValidade = Math.max(itensVinculados.length - itensComValidade, 0);
  const acoes = {
    lancar_estoque: true,
    atualizar_custo: true,
    atualizar_preco_venda: true,
    gerar_contas_pagar: true,
    ...(acoesProcessamento || {}),
  };
  const acoesRealizadas = previewProcessamento.acoes_processamento_realizadas || {};
  const acaoEstaRealizada = (acao) => Boolean(acoesRealizadas[acao]);
  const acaoVaiLancarAgora = (acao) => Boolean(acoes[acao]) && !acaoEstaRealizada(acao);
  const temAcaoSelecionada = [
    "lancar_estoque",
    "atualizar_custo",
    "atualizar_preco_venda",
    "gerar_contas_pagar",
  ].some(acaoVaiLancarAgora);

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

  const renderAcoesProcessamento = ({ modoConfirmacao = false } = {}) => {
    const resumoEstoque = acaoVaiLancarAgora("lancar_estoque") ? itensVinculados.length : 0;
    const resumoCustos = acaoVaiLancarAgora("atualizar_custo") ? custosAtualizados : 0;
    const resumoPrecos = acaoVaiLancarAgora("atualizar_preco_venda") ? precosAlterados : 0;

    return (
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-gray-900">
              {modoConfirmacao ? "O que sera lancado agora" : "Acoes ao processar"}
            </h3>
            {previewProcessamento.processamento_mensagem && (
              <p className="mt-0.5 text-xs text-gray-500">
                {previewProcessamento.processamento_mensagem}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500 xl:justify-end">
            <span>
              <strong className="text-slate-700">{resumoEstoque}</strong> itens no estoque
            </span>
            <span>
              <strong className="text-slate-700">{resumoCustos}</strong> custos
            </span>
            <span>
              <strong className="text-slate-700">{resumoPrecos}</strong> precos
            </span>
            <span className="text-slate-700">
              {acaoVaiLancarAgora("gerar_contas_pagar") ? "Financeiro ativo" : "Sem contas"}
            </span>
            <span>
              {itensComValidade} validade{itensComValidade === 1 ? "" : "s"} detectada
              {itensSemValidade > 0 ? `, ${itensSemValidade} sem validade` : ""}
            </span>
          </div>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["lancar_estoque", "Lancar estoque, lotes e validade"],
            ["atualizar_custo", "Atualizar custo dos produtos"],
            ["atualizar_preco_venda", "Atualizar preco de venda revisado"],
            ["gerar_contas_pagar", "Gerar contas a pagar"],
          ].map(([acao, label]) => {
            const acaoJaRealizada = acaoEstaRealizada(acao);

            return (
              <label
                key={acao}
                className={`flex min-h-9 items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                  acaoJaRealizada
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-gray-200 bg-gray-50 text-gray-800"
                }`}
              >
                <input
                  type="checkbox"
                  checked={acaoJaRealizada || Boolean(acoes[acao])}
                  disabled={loading || acaoJaRealizada}
                  onChange={(event) => setAcaoProcessamento(acao, event.target.checked)}
                  className="h-4 w-4 accent-green-600 disabled:cursor-not-allowed"
                />
                <span>{label}</span>
                {acaoJaRealizada && (
                  <span className="ml-auto rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">
                    Ja lancado
                  </span>
                )}
              </label>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/50">
      <div className="flex h-full w-full flex-col overflow-hidden bg-slate-50">
        <div className="shrink-0 border-b border-slate-200 bg-white">
          <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-4 py-2.5">
            <button
              type="button"
              onClick={onVoltar}
              className="inline-flex h-9 items-center gap-2 rounded-lg px-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Voltar</span>
            </button>

            <div className="min-w-0 flex-1 border-l border-slate-200 pl-3">
              <h2 className="truncate text-lg font-bold text-slate-900">
                Ajuste de Custos, Precos e Margens
              </h2>
              <p className="truncate text-xs text-slate-500">
                NF-e {previewProcessamento.numero_nota} · {previewProcessamento.fornecedor_nome}
              </p>
            </div>

            <div className="hidden max-w-xl items-center gap-2 text-xs text-slate-500 lg:flex">
              <Info className="h-4 w-4 shrink-0 text-sky-600" aria-hidden="true" />
              <span>O valor fiscal da NF permanece intacto.</span>
            </div>
          </div>
        </div>

        <div className="shrink-0 border-b border-slate-200 bg-white">
          <div className="mx-auto w-full max-w-[1440px] px-4 py-2">
            <div className="flex items-center gap-2 overflow-x-auto">
              <span className="shrink-0 text-xs font-semibold text-slate-500">Filtrar</span>
              <button
                onClick={() => setFiltroCusto("todos")}
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                  filtroCusto === "todos"
                    ? "bg-slate-800 text-white"
                    : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                Todos ({itensVinculados.length})
              </button>

              {resumoFiltros.aumentos > 0 && (
                <button
                  onClick={() => setFiltroCusto("aumentou")}
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    filtroCusto === "aumentou"
                      ? "bg-red-600 text-white"
                      : "border border-red-200 bg-white text-red-700 hover:bg-red-50"
                  }`}
                >
                  {resumoFiltros.aumentos} custo{resumoFiltros.aumentos > 1 ? "s" : ""} maior
                  {resumoFiltros.aumentos > 1 ? "es" : ""}
                </button>
              )}

              {resumoFiltros.reducoes > 0 && (
                <button
                  onClick={() => setFiltroCusto("diminuiu")}
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    filtroCusto === "diminuiu"
                      ? "bg-green-700 text-white"
                      : "border border-green-200 bg-white text-green-700 hover:bg-green-50"
                  }`}
                >
                  {resumoFiltros.reducoes} custo{resumoFiltros.reducoes > 1 ? "s" : ""} menor
                  {resumoFiltros.reducoes > 1 ? "es" : ""}
                </button>
              )}

              {resumoFiltros.iguais > 0 && (
                <button
                  onClick={() => setFiltroCusto("igual")}
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    filtroCusto === "igual"
                      ? "bg-slate-700 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {resumoFiltros.iguais} sem alteracao
                </button>
              )}

              <div className="ml-auto flex shrink-0 items-center gap-2">
                <ExportActionButton
                  type="csv"
                  onClick={exportarRelatorioCustosMaioresCSV}
                  disabled={gerandoRelatorioCustos || resumoFiltros.aumentos === 0}
                  title="Exportar CSV dos custos maiores"
                >
                  {gerandoRelatorioCustos ? "Gerando..." : "Exportar CSV"}
                </ExportActionButton>
                <ExportActionButton
                  type="pdf"
                  onClick={exportarRelatorioCustosMaioresPDF}
                  disabled={gerandoRelatorioCustos || resumoFiltros.aumentos === 0}
                  title="Exportar PDF dos custos maiores"
                >
                  {gerandoRelatorioCustos ? "Gerando..." : "Exportar PDF"}
                </ExportActionButton>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-slate-50">
          <div className="mx-auto w-full max-w-[1440px] space-y-3 p-3 md:p-4">
            <div className="flex items-start gap-2 rounded-xl border border-sky-200 bg-sky-50/70 px-3 py-2.5">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" aria-hidden="true" />
              <div>
                <div className="text-xs font-semibold text-slate-800">
                  Margem e preco usam automaticamente o Custo no sistema
                </div>
                <p className="mt-0.5 text-[11px] text-slate-600">
                  Custo manual recalcula os valores na hora; se ficar invalido, o custo fiscal da NF
                  volta a ser a base.
                </p>
              </div>
            </div>

            {renderAcoesProcessamento()}

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
                  inputsRevisaoCustos[custoItemId] ?? formatBRL(resumoCusto.custoSistema);
                const custoBaseMargem = resumoCusto.baseMargem.valor;
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
                    className="overflow-hidden rounded-xl border-2 border-slate-300 bg-white shadow-sm transition-colors hover:border-slate-400"
                  >
                    <div className="border-b border-slate-200 bg-slate-50 px-3 py-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate text-base font-semibold text-slate-900">
                            {produtoVinc.produto_nome}
                          </h3>
                          <p className="mt-0.5 text-xs text-slate-500">
                            SKU: {produtoVinc.produto_codigo || "Nao informado"} | EAN:{" "}
                            {produtoVinc.produto_ean || "Nao informado"}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <button
                            onClick={() =>
                              buscarHistoricoPrecos(
                                produtoVinc.produto_id,
                                produtoVinc.produto_nome,
                              )
                            }
                            className="h-7 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
                          >
                            Historico
                          </button>
                          <div className="mt-1 text-xs text-slate-500">
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

                    <div className="space-y-2 p-2.5">
                      <section className="rounded-lg border border-slate-300 bg-slate-50/70 p-2.5">
                        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1.5">
                          <h4 className="text-xs font-semibold text-slate-800">
                            Comparacao de custo
                          </h4>
                          <div
                            className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${
                              custoAumentou
                                ? "border-red-200 bg-red-50 text-red-700"
                                : custoVariacao < 0
                                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                  : "border-slate-200 bg-white text-slate-600"
                            }`}
                          >
                            {custoVariacao > 0 ? "+" : custoVariacao < 0 ? "-" : "="}{" "}
                            {formatPercent(Math.abs(custoVariacao))} em relacao ao anterior
                          </div>
                        </div>

                        <div className="grid grid-cols-1 gap-1.5 md:grid-cols-[minmax(130px,0.8fr)_20px_minmax(150px,0.9fr)_20px_minmax(240px,1.3fr)] md:items-start">
                          <div className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5">
                            <div className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                              Custo anterior
                            </div>
                            <div className="text-sm font-bold text-slate-700">
                              {formatMoneyBRL(resumoCusto.custoAnterior || 0)}
                            </div>
                            <div className="mt-0.5 text-[10px] text-slate-500">Cadastro atual</div>
                          </div>

                          <span
                            className="hidden h-full items-center justify-center text-base text-slate-400 md:flex"
                            aria-hidden="true"
                          >
                            →
                          </span>

                          <div className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5">
                            <div className="mb-0.5 flex items-center justify-between gap-2 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                              <span>Custo da NF</span>
                              <TooltipComposicao
                                custo={resumoCusto.custoNF}
                                composicao={item.composicao_custo}
                                texto="detalhar"
                              />
                            </div>
                            <div className="text-sm font-bold text-slate-900">
                              {formatMoneyBRL(resumoCusto.custoNF || 0)}
                            </div>
                            <div className="mt-0.5 text-[10px] text-slate-500">
                              Valor fiscal da nota
                            </div>
                          </div>

                          <span
                            className="hidden h-full items-center justify-center text-base text-slate-400 md:flex"
                            aria-hidden="true"
                          >
                            →
                          </span>

                          <div>
                            <label className="mb-0.5 block text-[11px] font-semibold text-slate-700">
                              Novo custo no sistema
                            </label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                                R$
                              </span>
                              <input
                                type="text"
                                inputMode="decimal"
                                value={custoTexto}
                                onChange={(event) =>
                                  atualizarCustoSistema(item, event.target.value)
                                }
                                onBlur={() => normalizarCamposRevisaoCustos(item)}
                                className="w-full rounded-lg border-2 border-amber-300 bg-white py-1.5 pl-10 pr-3 text-base font-bold text-slate-900 focus:border-amber-500 focus:ring-2 focus:ring-amber-500"
                              />
                            </div>
                            <div className="mt-0.5 text-[10px] leading-tight text-slate-500">
                              {resumoCusto.custoManual
                                ? "Custo manual aplicado so no processamento; a NF fiscal nao sera alterada"
                                : "Igual ao custo fiscal da NF"}
                            </div>
                          </div>
                        </div>
                      </section>

                      <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
                        <section className="rounded-lg border border-slate-300 bg-white p-2.5">
                          <h4 className="mb-1.5 text-xs font-semibold text-slate-800">
                            Comparacao do preco de venda
                          </h4>
                          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-[minmax(120px,0.8fr)_20px_minmax(180px,1.2fr)] sm:items-start">
                            <div className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5">
                              <div className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                                Preco anterior
                              </div>
                              <div className="text-sm font-bold text-slate-700">
                                {formatMoneyBRL(produtoVinc.preco_venda_atual || 0)}
                              </div>
                            </div>

                            <span
                              className="hidden h-full items-center justify-center text-base text-slate-400 sm:flex"
                              aria-hidden="true"
                            >
                              →
                            </span>

                            <div>
                              <label className="mb-0.5 block text-[11px] font-semibold text-slate-700">
                                Novo preco
                              </label>
                              <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
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
                                  onBlur={() =>
                                    normalizarCamposRevisaoPrecos(produtoVinc.produto_id)
                                  }
                                  className="w-full rounded-lg border-2 border-slate-300 py-1.5 pl-10 pr-3 text-base font-bold text-slate-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                          </div>
                        </section>

                        <section className="rounded-lg border border-slate-300 bg-white p-2.5">
                          <h4 className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-slate-800">
                            Comparacao da margem de lucro
                            <span className="cursor-help text-slate-400" title={tooltipMargem}>
                              i
                            </span>
                          </h4>
                          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-[minmax(120px,0.8fr)_20px_minmax(180px,1.2fr)] sm:items-start">
                            <div className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5">
                              <div className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                                Margem anterior
                              </div>
                              <div className="text-sm font-bold text-slate-700">
                                {formatPercent(margemReferencia)}
                              </div>
                            </div>

                            <span
                              className="hidden h-full items-center justify-center text-base text-slate-400 sm:flex"
                              aria-hidden="true"
                            >
                              →
                            </span>

                            <div>
                              <label className="mb-0.5 block text-[11px] font-semibold text-slate-700">
                                Nova margem
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
                                  onBlur={() =>
                                    normalizarCamposRevisaoPrecos(produtoVinc.produto_id)
                                  }
                                  className="w-full rounded-lg border-2 border-slate-300 py-1.5 pl-3 pr-10 text-base font-bold text-slate-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                                />
                                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">
                                  %
                                </span>
                              </div>
                              <div className="mt-0.5 text-[10px] leading-tight text-slate-500">
                                Base ativa: {descricaoBaseMargem}
                              </div>
                            </div>
                          </div>
                        </section>
                      </div>
                    </div>
                  </div>
                );
              })
              .filter(Boolean)}
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
          <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-between gap-3">
            <button
              onClick={onVoltar}
              className="h-9 rounded-lg border border-slate-200 px-3.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              Voltar
            </button>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-[11px] text-slate-500">Valor total da nota</div>
                <div className="text-lg font-bold text-emerald-600">
                  {formatMoneyBRL(previewProcessamento.valor_total || 0)}
                </div>
              </div>
              <button
                onClick={() => setMostrarConfirmacaoProcessamento(true)}
                disabled={loading || !temAcaoSelecionada}
                className="h-10 rounded-lg bg-emerald-600 px-5 text-sm font-bold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                {loading ? "Processando..." : "Processar NF"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {mostrarConfirmacaoProcessamento && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-gray-50 shadow-xl">
            <div className="border-b border-gray-200 bg-white px-5 py-4">
              <h3 className="text-lg font-bold text-gray-900">
                Confirmacao final do processamento
              </h3>
              <p className="mt-1 text-sm text-gray-600">
                Confira uma ultima vez antes de lancar a NF-e {previewProcessamento.numero_nota}.
              </p>
            </div>

            <div className="space-y-4 p-5">
              {renderAcoesProcessamento({ modoConfirmacao: true })}

              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                Ao confirmar, o sistema executa somente as opcoes marcadas acima. Se alguma acao
                estiver desmarcada, ela nao sera lancada nesta NF.
                {!temAcaoSelecionada && (
                  <div className="mt-2 font-semibold">
                    Nenhuma acao pendente esta selecionada para lancar agora.
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap justify-end gap-3 border-t border-gray-200 bg-white px-5 py-4">
              <button
                type="button"
                onClick={() => setMostrarConfirmacaoProcessamento(false)}
                disabled={loading}
                className="rounded-lg border border-gray-300 px-5 py-2.5 font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Voltar para revisar
              </button>
              <button
                type="button"
                onClick={confirmarProcessamento}
                disabled={loading || !temAcaoSelecionada}
                className="rounded-lg bg-green-600 px-6 py-2.5 font-bold text-white shadow hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? "Processando..." : "Processar NF agora"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

EntradaXmlRevisaoPrecosModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  acoesProcessamento: PropTypes.shape({
    lancar_estoque: PropTypes.bool,
    atualizar_custo: PropTypes.bool,
    atualizar_preco_venda: PropTypes.bool,
    gerar_contas_pagar: PropTypes.bool,
  }),
  previewProcessamento: PropTypes.shape({
    numero_nota: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    fornecedor_nome: PropTypes.string,
    valor_total: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    processamento_mensagem: PropTypes.string,
    acoes_processamento_realizadas: PropTypes.objectOf(PropTypes.bool),
    itens: PropTypes.arrayOf(PropTypes.object),
  }),
  filtroCusto: PropTypes.string.isRequired,
  setFiltroCusto: PropTypes.func.isRequired,
  obterResumoCustoItem: PropTypes.func.isRequired,
  exportarRelatorioCustosMaioresCSV: PropTypes.func.isRequired,
  exportarRelatorioCustosMaioresPDF: PropTypes.func.isRequired,
  gerandoRelatorioCustos: PropTypes.bool.isRequired,
  precosAjustados: PropTypes.objectOf(PropTypes.object).isRequired,
  inputsRevisaoPrecos: PropTypes.objectOf(PropTypes.object).isRequired,
  inputsRevisaoCustos: PropTypes.objectOf(PropTypes.string).isRequired,
  buscarHistoricoPrecos: PropTypes.func.isRequired,
  atualizarCustoSistema: PropTypes.func.isRequired,
  normalizarCamposRevisaoCustos: PropTypes.func.isRequired,
  atualizarPrecoVenda: PropTypes.func.isRequired,
  normalizarCamposRevisaoPrecos: PropTypes.func.isRequired,
  atualizarMargem: PropTypes.func.isRequired,
  setAcaoProcessamento: PropTypes.func.isRequired,
  confirmarProcessamento: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  onVoltar: PropTypes.func.isRequired,
};

EntradaXmlRevisaoPrecosModal.defaultProps = {
  acoesProcessamento: null,
  previewProcessamento: null,
};

export default EntradaXmlRevisaoPrecosModal;
