import { AlertCircle, RefreshCw } from "lucide-react";
import {
  calcularLucro,
  calcularMargem,
  calcularROI,
  formatarMoedaCompacta,
  formatarPesoCompacto,
  getCorMargem,
  getCorValor,
} from "./dashboardRacoesComparacaoUtils";

const DashboardRacoesComparacaoDetalhada = ({
  loadingAnalise,
  produtosComparacao,
  ordenarProdutos,
  ordenacao,
}) => {
  if (loadingAnalise) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mr-3" />
        <span className="text-gray-600">Carregando produtos...</span>
      </div>
    );
  }

  if (produtosComparacao.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <AlertCircle className="h-16 w-16 mx-auto mb-3 text-gray-400" />
        <p className="text-lg font-medium mb-2">Nenhum produto encontrado</p>
        <p className="text-sm">Selecione filtros acima e clique em "Aplicar Filtros"</p>
      </div>
    );
  }

  const custos = produtosComparacao.map((produto) => produto.preco_custo || 0);
  const margens = produtosComparacao.map((produto) =>
    calcularMargem(produto.preco_custo, produto.preco_venda),
  );
  const lucros = produtosComparacao.map((produto) =>
    calcularLucro(produto.preco_custo || 0, produto.preco_venda || 0),
  );
  const rois = produtosComparacao.map((produto) =>
    calcularROI(produto.preco_custo, produto.preco_venda),
  );

  const custosPositivos = custos.filter((custo) => custo > 0);
  const menorCusto = custosPositivos.length > 0 ? Math.min(...custosPositivos) : 0;
  const melhorMargem = Math.max(...margens);
  const maiorLucro = Math.max(...lucros);
  const melhorROI = Math.max(...rois);

  // Componente de header ordenável
  const HeaderOrdenavel = ({ campo, children, className = "" }) => (
    <th
      onClick={() => ordenarProdutos(campo)}
      className={`px-3 py-3 text-xs font-bold text-slate-600 uppercase cursor-pointer hover:bg-slate-100 transition-colors ${className}`}
    >
      <div className="flex items-center justify-center gap-1">
        {children}
        {ordenacao.campo === campo && (
          <span className="text-blue-600">{ordenacao.direcao === "asc" ? "▲" : "▼"}</span>
        )}
      </div>
    </th>
  );

  return (
    <div className="space-y-4">
      {/* Cards de Melhores Valores */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">💰</span>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Menor custo
            </span>
          </div>
          <p className="text-2xl font-bold text-slate-900">R$ {menorCusto.toFixed(2)}</p>
          <p className="text-xs text-green-600 mt-1">Melhor preço de compra</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">⭐</span>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Melhor margem
            </span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{melhorMargem.toFixed(2)}%</p>
          <p className="text-xs text-blue-600 mt-1">Maior percentual de lucro</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🎯</span>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Melhor ROI
            </span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{melhorROI.toFixed(2)}%</p>
          <p className="text-xs text-purple-600 mt-1">Retorno sobre investimento</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">💵</span>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Maior lucro
            </span>
          </div>
          <p className="text-2xl font-bold text-slate-900">R$ {maiorLucro.toFixed(2)}</p>
          <p className="text-xs text-amber-600 mt-1">Lucro absoluto por unidade</p>
        </div>
      </div>

      {/* Resumo Rápido */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Total de Produtos Encontrados</p>
            <p className="text-3xl font-bold text-gray-900">{produtosComparacao.length}</p>
          </div>

          {produtosComparacao.length > 0 && (
            <>
              <div>
                <p className="text-sm text-gray-600 mb-1">Margem Média</p>
                <p className="text-2xl font-bold text-blue-700">
                  {(margens.reduce((a, b) => a + b, 0) / margens.length).toFixed(2)}%
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Custo Médio/kg</p>
                <p className="text-2xl font-bold text-slate-900">
                  R${" "}
                  {(
                    produtosComparacao.reduce(
                      (acc, p) => acc + (p.preco_custo || 0) / (p.peso_embalagem || 1),
                      0,
                    ) / produtosComparacao.length
                  ).toFixed(2)}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Preço Venda Médio/kg</p>
                <p className="text-2xl font-bold text-emerald-700">
                  R${" "}
                  {(
                    produtosComparacao.reduce(
                      (acc, p) => acc + (p.preco_venda || 0) / (p.peso_embalagem || 1),
                      0,
                    ) / produtosComparacao.length
                  ).toFixed(2)}
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Dica de Uso */}
      <div className="flex items-start gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" />
        <div className="text-sm text-slate-700">
          <strong>💡 Dica:</strong> Clique nos cabeçalhos das colunas para ordenar. As cores indicam
          valores melhores (verde) e piores (vermelho). Produtos destacados com badges são os
          melhores em cada categoria.
        </div>
      </div>

      {/* Tabela de Comparação */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full bg-white">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="sticky left-0 border-r border-slate-200 bg-slate-50 px-4 py-3 text-left text-xs font-bold uppercase text-slate-600">
                Produto / Marca
              </th>
              <th className="border-r border-slate-200 px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                Linha
              </th>
              <th className="border-r border-slate-200 px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                Peso
              </th>
              <HeaderOrdenavel campo="custo" className="border-r border-slate-200">
                💰 Custo
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="venda" className="border-r border-slate-200">
                💵 Venda
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="lucro" className="border-r border-slate-200">
                Lucro R$
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="margem" className="border-r border-slate-200">
                📊 Margem %
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="roi" className="border-r border-slate-200">
                🎯 ROI %
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="custokg" className="border-r border-slate-200">
                Custo/kg
              </HeaderOrdenavel>
              <HeaderOrdenavel campo="vendakg" className="border-r border-slate-200">
                Venda/kg
              </HeaderOrdenavel>
              <th className="px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                Estoque
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {produtosComparacao.map((produto) => {
              const margem = calcularMargem(produto.preco_custo, produto.preco_venda);
              const lucro = calcularLucro(produto.preco_custo || 0, produto.preco_venda || 0);
              const roi = calcularROI(produto.preco_custo, produto.preco_venda);
              const custoKg = (produto.preco_custo || 0) / (produto.peso_embalagem || 1);
              const vendaKg = (produto.preco_venda || 0) / (produto.peso_embalagem || 1);

              // Identificar se é o melhor em cada categoria
              const isMenorCusto = (produto.preco_custo || 0) === menorCusto && menorCusto > 0;
              const isMelhorMargem = margem === melhorMargem && melhorMargem > 0;
              const isMaiorLucro = lucro === maiorLucro && maiorLucro > 0;
              const isMelhorROI = roi === melhorROI && melhorROI > 0;

              const destaque = isMenorCusto || isMelhorMargem || isMaiorLucro || isMelhorROI;

              return (
                <tr
                  key={produto.id}
                  className={`transition-colors hover:bg-slate-50 ${
                    destaque ? "bg-blue-50/40 border-l-4 border-blue-300" : ""
                  }`}
                >
                  <td className="sticky left-0 border-r border-slate-200 bg-white px-4 py-3">
                    <div className="max-w-xs">
                      <p className="font-semibold text-gray-900 text-sm">{produto.nome}</p>
                      <p className="text-xs text-gray-600 mt-0.5">
                        {produto.marca?.nome || "Sem marca"} • Cód: {produto.codigo}
                      </p>
                      <div className="flex gap-1 mt-1.5 flex-wrap">
                        {/* Badges de características */}
                        {produto.porte_animal &&
                          Array.isArray(produto.porte_animal) &&
                          produto.porte_animal.map((p) => (
                            <span
                              key={p}
                              className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                            >
                              {p}
                            </span>
                          ))}
                        {produto.fase_publico &&
                          Array.isArray(produto.fase_publico) &&
                          produto.fase_publico.map((f) => (
                            <span
                              key={f}
                              className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                            >
                              {f}
                            </span>
                          ))}
                        {produto.sabor_proteina && (
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            {produto.sabor_proteina}
                          </span>
                        )}
                      </div>
                      {/* Badges de destaque */}
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {isMenorCusto && (
                          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                            💰 MENOR CUSTO
                          </span>
                        )}
                        {isMelhorMargem && (
                          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
                            ⭐ MELHOR MARGEM
                          </span>
                        )}
                        {isMelhorROI && (
                          <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                            🎯 MELHOR ROI
                          </span>
                        )}
                        {isMaiorLucro && (
                          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                            💵 MAIOR LUCRO
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                      {produto.classificacao_racao || "-"}
                    </span>
                  </td>

                  <td className="border-r border-slate-200 px-3 py-3 text-center text-sm font-medium text-gray-900">
                    {produto.peso_embalagem ? (
                      <span className="inline-flex whitespace-nowrap rounded-full bg-slate-100 px-2.5 py-1 font-bold text-slate-700">
                        {formatarPesoCompacto(produto.peso_embalagem)}
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>

                  <td
                    className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${getCorValor(
                      produto.preco_custo || 0,
                      menorCusto,
                      Math.max(...custos),
                      true,
                    )}`}
                  >
                    {formatarMoedaCompacta(produto.preco_custo)}
                  </td>

                  <td
                    className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${getCorValor(
                      produto.preco_venda || 0,
                      Math.min(...produtosComparacao.map((p) => p.preco_venda || 0)),
                      Math.max(...produtosComparacao.map((p) => p.preco_venda || 0)),
                    )}`}
                  >
                    {formatarMoedaCompacta(produto.preco_venda)}
                  </td>

                  <td
                    className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${getCorValor(
                      lucro,
                      Math.min(...lucros),
                      Math.max(...lucros),
                    )}`}
                  >
                    {formatarMoedaCompacta(lucro)}
                  </td>

                  <td className="border-r border-slate-200 px-3 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <span
                        className={`rounded-full border px-3 py-1.5 text-sm font-bold ${getCorMargem(margem)}`}
                      >
                        {margem.toFixed(2)}%
                      </span>
                      {/* Barra de progresso */}
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                        <div
                          className={`h-full transition-all ${
                            margem >= 40
                              ? "bg-green-500"
                              : margem >= 30
                                ? "bg-green-400"
                                : margem >= 20
                                  ? "bg-yellow-400"
                                  : margem >= 10
                                    ? "bg-orange-400"
                                    : "bg-red-400"
                          }`}
                          style={{ width: `${Math.min(margem, 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  <td
                    className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold ${getCorValor(
                      roi,
                      Math.min(...rois),
                      Math.max(...rois),
                    )}`}
                  >
                    {roi.toFixed(2)}%
                  </td>

                  <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                    <span
                      className={`inline-flex whitespace-nowrap rounded-full bg-slate-50 px-2.5 py-1 font-semibold ${getCorValor(
                        custoKg,
                        Math.min(
                          ...produtosComparacao.map(
                            (p) => (p.preco_custo || 0) / (p.peso_embalagem || 1),
                          ),
                        ),
                        Math.max(
                          ...produtosComparacao.map(
                            (p) => (p.preco_custo || 0) / (p.peso_embalagem || 1),
                          ),
                        ),
                        true,
                      )}`}
                    >
                      {formatarMoedaCompacta(custoKg)}
                    </span>
                  </td>

                  <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                    <span
                      className={`inline-flex whitespace-nowrap rounded-full bg-slate-50 px-2.5 py-1 font-semibold ${getCorValor(
                        vendaKg,
                        Math.min(
                          ...produtosComparacao.map(
                            (p) => (p.preco_venda || 0) / (p.peso_embalagem || 1),
                          ),
                        ),
                        Math.max(
                          ...produtosComparacao.map(
                            (p) => (p.preco_venda || 0) / (p.peso_embalagem || 1),
                          ),
                        ),
                      )}`}
                    >
                      {formatarMoedaCompacta(vendaKg)}
                    </span>
                  </td>

                  <td className="px-3 py-3 text-sm text-center">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        (produto.estoque_atual || 0) > 10
                          ? "bg-green-100 text-green-700 border border-green-300"
                          : (produto.estoque_atual || 0) > 0
                            ? "bg-yellow-100 text-yellow-700 border border-yellow-300"
                            : "bg-red-100 text-red-700 border border-red-300"
                      }`}
                    >
                      {produto.estoque_atual || 0}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legenda */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="mb-3 text-sm font-bold text-slate-800">Legenda de leitura</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <div className="flex items-start gap-2 text-xs">
              <span className="font-bold text-emerald-700">Verde:</span>
              <span className="text-gray-700">melhor indicador do grupo naquela coluna.</span>
            </div>
            <div className="flex items-start gap-2 text-xs">
              <span className="font-bold text-rose-700">Vermelho:</span>
              <span className="text-gray-700">pior indicador relativo naquela comparação.</span>
            </div>
            <div className="flex items-start gap-2 text-xs">
              <span className="font-bold text-blue-700">Selos:</span>
              <span className="text-gray-700">
                mostram apenas os destaques reais de custo, margem, ROI e lucro.
              </span>
            </div>
          </div>
          <div className="space-y-1.5 text-xs text-gray-700">
            <p>
              <strong>Margem %:</strong> (Venda - Custo) / Venda × 100
            </p>
            <p>
              <strong>ROI %:</strong> (Lucro / Custo) × 100
            </p>
            <p>
              <strong>Lucro R$:</strong> Venda - Custo (valor absoluto)
            </p>
            <p>
              <strong>Custo/Venda por kg:</strong> Preço dividido pelo peso
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardRacoesComparacaoDetalhada;
