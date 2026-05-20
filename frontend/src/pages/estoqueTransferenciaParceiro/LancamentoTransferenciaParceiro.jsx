import { formatarMoeda } from "../../api/produtos";
import { ResumoTransferenciaCard } from "./transferenciaParceiroComponents";
import { formatarQuantidade } from "./transferenciaParceiroUtils";

export default function LancamentoTransferenciaParceiro({
  parceiroRef,
  parceiroSelecionado,
  limparParceiro,
  buscaParceiro,
  setBuscaParceiro,
  setDropdownParceiroAberto,
  dropdownParceiroAberto,
  loadingParceiros,
  sugestoesParceiros,
  selecionarParceiro,
  form,
  atualizarCampo,
  produtoRef,
  produtoInputRef,
  buscaProduto,
  setBuscaProduto,
  setDropdownProdutoAberto,
  dropdownProdutoAberto,
  adicionarProdutoPorBuscaAtual,
  loadingProdutos,
  sugestoesProdutos,
  adicionarProduto,
  itensRef,
  itens,
  totalQuantidade,
  totalRessarcimento,
  registrarTransferencia,
  salvando,
  modoEdicao,
  itensSemValor,
  atualizarCustoUnitario,
  atualizarQuantidade,
  atualizarTotalItem,
  removerItem,
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              1. Pessoa responsavel e dados da transferencia
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Primeiro selecione quem vai ressarcir o custo desta saida.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-4">
          <div ref={parceiroRef} className="relative">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Pessoa / parceiro
            </label>
            {parceiroSelecionado ? (
              <div className="flex items-start justify-between gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
                <div>
                  <p className="text-sm font-semibold text-blue-900">
                    {parceiroSelecionado.nome}
                  </p>
                  <p className="mt-1 text-xs text-blue-800">
                    Codigo: {parceiroSelecionado.codigo || "-"}
                    {parceiroSelecionado.celular
                      ? ` | Celular: ${parceiroSelecionado.celular}`
                      : ""}
                  </p>
                  <p className="mt-1 text-xs text-blue-800">
                    Tipo: {parceiroSelecionado.tipo_cadastro || "pessoa"}
                    {parceiroSelecionado.parceiro_ativo ? " | Parceiro ativo" : ""}
                  </p>
                  {parceiroSelecionado.email ? (
                    <p className="mt-1 text-xs text-blue-800">
                      {parceiroSelecionado.email}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={limparParceiro}
                  className="rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                >
                  Trocar
                </button>
              </div>
            ) : (
              <>
                <input
                  type="text"
                  value={buscaParceiro}
                  onChange={(event) => setBuscaParceiro(event.target.value)}
                  onFocus={() => setDropdownParceiroAberto(true)}
                  placeholder="Buscar pessoa por nome, codigo, telefone ou email"
                  className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                />

                {dropdownParceiroAberto && (
                  <div className="absolute z-20 mt-2 w-full rounded-2xl border border-gray-200 bg-white p-2 shadow-xl">
                    {loadingParceiros ? (
                      <p className="px-3 py-3 text-sm text-gray-500">
                        Buscando pessoas...
                      </p>
                    ) : sugestoesParceiros.length > 0 ? (
                      sugestoesParceiros.map((parceiro) => (
                        <button
                          key={parceiro.id}
                          type="button"
                          onClick={() => selecionarParceiro(parceiro)}
                          className="flex w-full flex-col rounded-xl px-3 py-3 text-left transition-colors hover:bg-slate-50"
                        >
                          <span className="text-sm font-semibold text-gray-900">
                            {parceiro.nome}
                          </span>
                          <span className="mt-1 text-xs text-gray-500">
                            Codigo: {parceiro.codigo || "-"}
                            {parceiro.celular ? ` | ${parceiro.celular}` : ""}
                          </span>
                          <span className="mt-1 text-xs text-gray-500">
                            {parceiro.tipo_cadastro || "pessoa"}
                            {parceiro.parceiro_ativo ? " | Parceiro ativo" : ""}
                          </span>
                        </button>
                      ))
                    ) : (
                      <p className="px-3 py-3 text-sm text-gray-500">
                        Nenhuma pessoa ativa encontrada para esta busca.
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Vencimento do ressarcimento
              </label>
              <input
                type="date"
                value={form.data_vencimento}
                onChange={(event) => atualizarCampo("data_vencimento", event.target.value)}
                className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Documento interno
              </label>
              <input
                type="text"
                value={form.documento}
                onChange={(event) => atualizarCampo("documento", event.target.value)}
                placeholder="Opcional. Se vazio, o sistema gera um codigo."
                className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Observacao
            </label>
            <textarea
              value={form.observacao}
              onChange={(event) => atualizarCampo("observacao", event.target.value)}
              rows={4}
              placeholder="Ex.: itens enviados para reposicao da loja parceira, acerto no fim do mes."
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">2. Produtos</h2>
          <p className="mt-1 text-sm text-gray-600">
            Pesquise por nome, SKU, codigo ou codigo de barras e monte a
            transferencia.
          </p>
        </div>

        <div ref={produtoRef} className="relative mt-5">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Buscar produto
          </label>
          <input
            ref={produtoInputRef}
            type="text"
            value={buscaProduto}
            onChange={(event) => setBuscaProduto(event.target.value)}
            onFocus={() => setDropdownProdutoAberto(true)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void adicionarProdutoPorBuscaAtual();
              }
            }}
            placeholder="Digite nome, SKU ou codigo de barras"
            className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          />

          {dropdownProdutoAberto && (
            <div className="absolute z-20 mt-2 w-full rounded-2xl border border-gray-200 bg-white p-2 shadow-xl">
              {loadingProdutos ? (
                <p className="px-3 py-3 text-sm text-gray-500">
                  Buscando produtos...
                </p>
              ) : sugestoesProdutos.length > 0 ? (
                sugestoesProdutos.map((produto) => (
                  <button
                    key={produto.id}
                    type="button"
                    onClick={() => adicionarProduto(produto)}
                    className="flex w-full flex-col rounded-xl px-3 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <span className="text-sm font-semibold text-gray-900">
                      {produto.nome}
                    </span>
                    <span className="mt-1 text-xs text-gray-500">
                      Codigo: {produto.codigo || "-"}
                      {produto.codigo_barras ? ` | CB: ${produto.codigo_barras}` : ""}
                    </span>
                    <span className="mt-1 text-xs text-gray-500">
                      Estoque: {formatarQuantidade(produto.estoque_atual)} | Custo:{" "}
                      {formatarMoeda(produto.preco_custo || 0)}
                    </span>
                  </button>
                ))
              ) : (
                <p className="px-3 py-3 text-sm text-gray-500">
                  Nenhum produto encontrado para esta busca.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
          Depois de selecionar o produto, confira quantidade e valores na lista
          abaixo. O botao de registrar fica junto da conferencia final.
        </div>
      </section>

      <section ref={itensRef} className="rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-100 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              3. Itens da transferencia
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Ajuste as quantidades e confira o total de ressarcimento antes de salvar.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
              {itens.length} item(ns) | {formatarQuantidade(totalQuantidade)} un |{" "}
              {formatarMoeda(totalRessarcimento)}
            </div>
            <button
              type="button"
              onClick={registrarTransferencia}
              disabled={salvando || itens.length === 0}
              className="inline-flex items-center justify-center rounded-2xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              {salvando
                ? modoEdicao
                  ? "Salvando..."
                  : "Registrando..."
                : modoEdicao
                  ? "Salvar edicao"
                  : "Registrar transferencia"}
            </button>
          </div>
        </div>

        <div className="grid gap-3 border-b border-gray-100 px-6 py-4 md:grid-cols-2 xl:grid-cols-4">
          <ResumoTransferenciaCard
            titulo="Itens"
            valor={String(itens.length)}
            descricao="Linhas de produto conferidas."
            destaque="slate"
          />
          <ResumoTransferenciaCard
            titulo="Quantidade total"
            valor={formatarQuantidade(totalQuantidade)}
            descricao="Unidades que sairao do estoque."
            destaque="blue"
          />
          <ResumoTransferenciaCard
            titulo="Ressarcimento"
            valor={formatarMoeda(totalRessarcimento)}
            descricao="Total do acerto financeiro."
            destaque="emerald"
          />
          <ResumoTransferenciaCard
            titulo="Itens sem valor"
            valor={String(itensSemValor)}
            descricao="Precisam ser corrigidos antes de salvar."
            destaque="amber"
          />
        </div>

        {itens.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-base font-semibold text-gray-900">
              Nenhum item adicionado ainda
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Use a busca acima para incluir os produtos que sairao para a pessoa responsavel.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-slate-50">
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <th className="px-6 py-4">Produto</th>
                  <th className="px-6 py-4">Estoque atual</th>
                  <th className="px-6 py-4">Custo unit.</th>
                  <th className="px-6 py-4">Quantidade</th>
                  <th className="px-6 py-4">Total</th>
                  <th className="px-6 py-4 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {itens.map((item) => {
                  const semValor = Number(item.total_item || 0) <= 0;
                  return (
                    <tr key={item.uid} className="align-top">
                      <td className="px-6 py-4">
                        <p className="text-sm font-semibold text-gray-900">
                          {item.produto_nome}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          Codigo: {item.codigo || "-"}
                          {item.codigo_barras ? ` | CB: ${item.codigo_barras}` : ""}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {formatarQuantidade(item.estoque_atual)}
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.custo_unitario ?? ""}
                          onChange={(event) =>
                            atualizarCustoUnitario(item.uid, event.target.value)
                          }
                          className={`w-28 rounded-xl border px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 ${
                            semValor ? "border-amber-300 bg-amber-50" : "border-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0.001"
                          step="0.001"
                          value={item.quantidade ?? ""}
                          onChange={(event) => atualizarQuantidade(item.uid, event.target.value)}
                          className="w-28 rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.total_item ?? ""}
                          onChange={(event) =>
                            atualizarTotalItem(item.uid, event.target.value)
                          }
                          className={`w-32 rounded-xl border px-3 py-2 text-sm font-semibold text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 ${
                            semValor ? "border-amber-300 bg-amber-50" : "border-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => removerItem(item.uid)}
                          className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-100"
                        >
                          Remover
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
