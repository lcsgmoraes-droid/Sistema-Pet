import FornecedorIdentity from "../ui/FornecedorIdentity";
import PedidosCompraSugestaoUnidadeCell from "./PedidosCompraSugestaoUnidadeCell";

export default function PedidosCompraSugestaoTable({
  modoAplicacaoSugestao,
  loadingSugestao,
  sugestoes,
  mostrarSoPreenchidos,
  setMostrarSoPreenchidos,
  selecionarTodosCriticos,
  selecionarPreenchidosVisiveis,
  desmarcarVisiveis,
  produtosSelecionados,
  selecionadosComQuantidade,
  sugestoesFiltradas,
  cabecalhoTabelaSugestaoRef,
  classeTabelaSugestao,
  renderColGroupSugestao,
  classeCabecalhoTabelaSugestao,
  setProdutosSelecionados,
  corpoTabelaSugestaoRef,
  toggleSelecionarProduto,
  copiarSkuSugestao,
  montarTooltipGiroSugestao,
  formatarQuantidadeCurta,
  obterVendaJanelaSugestao,
  consumoFoiAjustado,
  incluirGrupoFornecedor,
  obterQuantidadeInteira,
  obterEmbalagemSugestao,
  atualizarUnidadeCompraSugestao,
  atualizarQuantidadePorEmbalagemSugestao,
  marcarQuantidadePorEmbalagemDesconhecida,
  formatarQuantidadeCompraSugestao,
  montarTooltipQuantidadeCompraSugestao,
  calcularValorTotalSugestao,
  atualizarQuantidadeSugerida,
  setProdutoEditandoQuantidade,
  fecharModalSugestao,
  adicionarSugestoesAoPedido,
}) {
  return (
    <>
      {/* Tabela de Sugestões */}
      <div className="flex-1 overflow-auto p-5">
        {modoAplicacaoSugestao === "replace" && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            A sugestão selecionada vai substituir os itens atuais do rascunho quando você confirmar.
          </div>
        )}
        {loadingSugestao ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Analisando produtos e calculando sugestões...</p>
            </div>
          </div>
        ) : sugestoes.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">
              Nenhuma sugestão encontrada com os filtros aplicados
            </p>
            <p className="text-gray-400 text-sm mt-2">Tente ajustar os filtros acima</p>
          </div>
        ) : (
          <>
            {/* Ações Rápidas */}
            <div className="sticky top-0 z-30 -mx-5 mb-3 bg-white/95 shadow-[0_10px_20px_-18px_rgba(15,23,42,0.45)] backdrop-blur-sm">
              <div className="border-b border-gray-200 px-5 py-3">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={mostrarSoPreenchidos}
                        onChange={(e) => setMostrarSoPreenchidos(e.target.checked)}
                        className="w-4 h-4 rounded"
                      />
                      Mostrar só preenchidos (qtd {`>`} 0)
                    </label>
                    <button
                      onClick={selecionarTodosCriticos}
                      className="rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-200"
                    >
                      🔴 Selecionar Todos Críticos
                    </button>
                    <button
                      onClick={selecionarPreenchidosVisiveis}
                      className="rounded-lg bg-green-100 px-4 py-2 text-sm font-semibold text-green-700 transition hover:bg-green-200"
                    >
                      ✅ Selecionar Preenchidos
                    </button>
                    <button
                      onClick={desmarcarVisiveis}
                      className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-200"
                    >
                      ⛔ Desmarcar Visíveis
                    </button>
                  </div>
                  <span className="text-sm text-gray-500 xl:ml-auto">
                    {`${produtosSelecionados.length} selecionados (${selecionadosComQuantidade.length} preenchidos) · ${sugestoesFiltradas.length} exibidos de ${sugestoes.length} total`}
                  </span>
                </div>
              </div>

              <div className="border-b border-slate-200 bg-white/95 px-5">
                <div ref={cabecalhoTabelaSugestaoRef} className="overflow-hidden">
                  <table className={classeTabelaSugestao}>
                    {renderColGroupSugestao()}
                    <thead>
                      <tr>
                        <th className={`${classeCabecalhoTabelaSugestao} text-left`}>
                          <input
                            type="checkbox"
                            onChange={(e) => {
                              const visiveis = sugestoesFiltradas;
                              if (e.target.checked) {
                                setProdutosSelecionados((prev) => [
                                  ...new Set([...prev, ...visiveis.map((s) => s.produto_id)]),
                                ]);
                              } else {
                                const idsVisiveis = new Set(visiveis.map((s) => s.produto_id));
                                setProdutosSelecionados((prev) =>
                                  prev.filter((id) => !idsVisiveis.has(id)),
                                );
                              }
                            }}
                            checked={
                              sugestoesFiltradas.length > 0 &&
                              sugestoesFiltradas.every((s) =>
                                produtosSelecionados.includes(s.produto_id),
                              )
                            }
                            className="w-4 h-4 rounded"
                          />
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-left`}
                          title="CRÍTICO = menos de 7 dias. ALERTA = menos de 14 dias. ATENÇÃO = menos de 30 dias."
                        >
                          Prioridade ℹ️
                        </th>
                        <th className={`${classeCabecalhoTabelaSugestao} text-left`}>Produto</th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Estoque atual. Valor negativo e tratado como ruptura para compra."
                        >
                          Estoque ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Media diaria usada na compra. Se houve ruptura, o sistema ajusta pelos dias em que havia estoque."
                        >
                          Consumo/dia ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Quantos dias o estoque atual dura ao ritmo de consumo atual. ∞ = sem venda recente."
                        >
                          Dias Restantes ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Unidade usada para pedir ao fornecedor e quantidade de unidades por caixa, fardo ou pacote."
                        >
                          Unidade ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Quantidade a pedir na unidade escolhida. Ex: 14 CX quando cada caixa tem 12 unidades."
                        >
                          Qtd. pedida ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Último preço de custo registrado para este produto."
                        >
                          Preço Unit. ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-right`}
                          title="Qtd sugerida × preço unitário."
                        >
                          Total ℹ️
                        </th>
                        <th
                          className={`${classeCabecalhoTabelaSugestao} text-left`}
                          title="Tendência de vendas: comparação entre a primeira e segunda metade do período."
                        >
                          Tendência ℹ️
                        </th>
                      </tr>
                    </thead>
                  </table>
                </div>
              </div>
            </div>

            <div ref={corpoTabelaSugestaoRef} className="overflow-x-auto">
              <table className={classeTabelaSugestao}>
                {renderColGroupSugestao()}
                <tbody className="divide-y divide-gray-200">
                  {sugestoesFiltradas.map((sugestao) => (
                    <tr
                      key={sugestao.produto_id}
                      className={`hover:bg-gray-50 ${
                        produtosSelecionados.includes(sugestao.produto_id) ? "bg-purple-50" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={produtosSelecionados.includes(sugestao.produto_id)}
                          onChange={() => toggleSelecionarProduto(sugestao.produto_id)}
                          className="w-4 h-4 rounded"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            sugestao.prioridade === "CRÍTICO"
                              ? "bg-red-100 text-red-700"
                              : sugestao.prioridade === "ALERTA"
                                ? "bg-yellow-100 text-yellow-700"
                                : sugestao.prioridade === "ATENÇÃO"
                                  ? "bg-orange-100 text-orange-700"
                                  : "bg-green-100 text-green-700"
                          }`}
                        >
                          {sugestao.prioridade}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium text-gray-900">{sugestao.produto_nome}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500">
                            <span>SKU: {sugestao.produto_sku || "N/A"}</span>
                            <button
                              type="button"
                              onClick={() => copiarSkuSugestao(sugestao)}
                              className="inline-flex h-6 w-6 items-center justify-center rounded-md border border-slate-200 text-slate-500 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
                              title="Copiar SKU"
                              aria-label={`Copiar SKU de ${sugestao.produto_nome}`}
                            >
                              <svg
                                viewBox="0 0 24 24"
                                className="h-3.5 w-3.5"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.8"
                              >
                                <rect x="9" y="9" width="11" height="11" rx="2" />
                                <path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" />
                              </svg>
                            </button>
                            <span>| Barras: {sugestao.produto_codigo_barras || "N/A"}</span>
                            {sugestao.marca_nome ? (
                              <span>| Marca: {sugestao.marca_nome}</span>
                            ) : null}
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                            <span
                              title={montarTooltipGiroSugestao(sugestao)}
                              className="inline-flex cursor-help items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-semibold text-slate-600"
                            >
                              Giro 30d:{" "}
                              {formatarQuantidadeCurta(obterVendaJanelaSugestao(sugestao, 30))}
                            </span>
                            {consumoFoiAjustado(sugestao) && (
                              <span
                                title={montarTooltipGiroSugestao(sugestao)}
                                className="inline-flex cursor-help items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-semibold text-amber-700"
                              >
                                media ajustada
                              </span>
                            )}
                            {(sugestao.ruptura_ativa || sugestao.teve_ruptura) && (
                              <span
                                title={montarTooltipGiroSugestao(sugestao)}
                                className="inline-flex cursor-help items-center rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 font-semibold text-rose-700"
                              >
                                ruptura
                              </span>
                            )}
                            {sugestao.estoque_derivado && (
                              <span
                                title={montarTooltipGiroSugestao(sugestao)}
                                className="inline-flex cursor-help items-center rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700"
                              >
                                derivado
                              </span>
                            )}
                            {Number(sugestao?.granel_consumo?.kg_periodo || 0) > 0 && (
                              <span
                                title={montarTooltipGiroSugestao(sugestao)}
                                className="inline-flex cursor-help items-center rounded-full border border-cyan-200 bg-cyan-50 px-2 py-0.5 font-semibold text-cyan-700"
                              >
                                granel
                              </span>
                            )}
                          </div>
                          {sugestao.fornecedor_nome && incluirGrupoFornecedor && (
                            <div className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                              <FornecedorIdentity
                                fallback=""
                                label="Origem"
                                layout="inline"
                                nameClassName="font-semibold text-emerald-700"
                                record={sugestao}
                                showDocument={false}
                                showLabel
                              />
                            </div>
                          )}
                          {sugestao.observacao && (
                            <div className="text-xs text-gray-600 mt-1 italic">
                              {sugestao.observacao}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-medium">
                          {Number(sugestao.estoque_atual)
                            .toFixed(2)
                            .replace(/\.?0+$/, "") || "0"}
                        </div>
                        <div className="text-xs text-gray-500">Mín: {sugestao.estoque_minimo}</div>
                      </td>
                      <td
                        className="px-4 py-3 text-right font-medium"
                        title={montarTooltipGiroSugestao(sugestao)}
                      >
                        <div>{Number(sugestao.consumo_diario || 0).toFixed(2)}</div>
                        {consumoFoiAjustado(sugestao) && (
                          <div className="text-[10px] font-semibold text-amber-600">ajustado</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          title={montarTooltipGiroSugestao(sugestao)}
                          className={`font-semibold ${
                            sugestao.ruptura_ativa ||
                            (sugestao.dias_estoque !== null && sugestao.dias_estoque < 7)
                              ? "text-red-600"
                              : sugestao.dias_estoque !== null && sugestao.dias_estoque < 14
                                ? "text-yellow-600"
                                : "text-green-600"
                          }`}
                        >
                          {sugestao.ruptura_ativa
                            ? "ruptura"
                            : sugestao.dias_estoque !== null && sugestao.dias_estoque !== undefined
                              ? `${sugestao.dias_estoque} dias`
                              : "∞"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <PedidosCompraSugestaoUnidadeCell
                          sugestao={sugestao}
                          obterEmbalagemSugestao={obterEmbalagemSugestao}
                          atualizarUnidadeCompraSugestao={atualizarUnidadeCompraSugestao}
                          atualizarQuantidadePorEmbalagemSugestao={
                            atualizarQuantidadePorEmbalagemSugestao
                          }
                          marcarQuantidadePorEmbalagemDesconhecida={
                            marcarQuantidadePorEmbalagemDesconhecida
                          }
                          formatarQuantidadeCompraSugestao={formatarQuantidadeCompraSugestao}
                          montarTooltipQuantidadeCompraSugestao={
                            montarTooltipQuantidadeCompraSugestao
                          }
                        />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input
                          type="text"
                          inputMode="numeric"
                          pattern="[0-9]*"
                          value={obterQuantidadeInteira(sugestao)}
                          title={montarTooltipQuantidadeCompraSugestao(sugestao)}
                          onChange={(e) =>
                            atualizarQuantidadeSugerida(sugestao.produto_id, e.target.value)
                          }
                          onFocus={() => setProdutoEditandoQuantidade(sugestao.produto_id)}
                          onBlur={() => {
                            setProdutoEditandoQuantidade((atual) =>
                              atual === sugestao.produto_id ? null : atual,
                            );
                            const valorAtual = obterQuantidadeInteira(sugestao);
                            atualizarQuantidadeSugerida(sugestao.produto_id, valorAtual);
                          }}
                          onWheel={(e) => e.currentTarget.blur()}
                          className="w-20 px-2 py-1 text-right font-bold text-purple-600 border rounded focus:ring-2 focus:ring-purple-300"
                        />
                      </td>
                      <td className="px-4 py-3 text-right">
                        R$ {sugestao.preco_unitario.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">
                        R$ {calcularValorTotalSugestao(sugestao).toFixed(2)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs ${
                            sugestao.tendencia === "CRESCIMENTO"
                              ? "text-green-600"
                              : sugestao.tendencia === "QUEDA"
                                ? "text-red-600"
                                : "text-gray-600"
                          }`}
                        >
                          {sugestao.tendencia === "CRESCIMENTO"
                            ? "📈"
                            : sugestao.tendencia === "QUEDA"
                              ? "📉"
                              : sugestao.tendencia === "ESTÁVEL"
                                ? "➡️"
                                : "—"}
                          {sugestao.tendencia}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Footer com Ações */}
      {!loadingSugestao && sugestoes.length > 0 && (
        <div className="border-t p-6 bg-gray-50">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              <div className="font-semibold mb-1">Resumo da Sugestão:</div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  🔴 <strong>{sugestoes.filter((s) => s.prioridade === "CRÍTICO").length}</strong>{" "}
                  críticos
                </div>
                <div>
                  ⚠️ <strong>{sugestoes.filter((s) => s.prioridade === "ALERTA").length}</strong> em
                  alerta
                </div>
                <div>
                  💰 Total:{" "}
                  <strong>
                    R${" "}
                    {sugestoes
                      .filter((s) => produtosSelecionados.includes(s.produto_id))
                      .reduce((sum, s) => sum + calcularValorTotalSugestao(s), 0)
                      .toFixed(2)}
                  </strong>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={fecharModalSugestao}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={adicionarSugestoesAoPedido}
                disabled={selecionadosComQuantidade.length === 0}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {modoAplicacaoSugestao === "replace"
                  ? `Substituir rascunho com ${selecionadosComQuantidade.length} produtos`
                  : `Adicionar ${selecionadosComQuantidade.length} produtos ao pedido`}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
