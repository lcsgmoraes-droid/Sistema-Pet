import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import TopProdutosLucroTable from "./TopProdutosLucroTable";

function CardIndicador({ label, value, hint, className = "" }) {
  return (
    <div className={`bg-white rounded-lg shadow-md p-4 border ${className}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{hint}</div>
    </div>
  );
}

export default function VendasAnaliseInteligentePanel({
  alertasInteligentesVendas = [],
  formatarMoeda,
  loading,
  mostrarGraficos,
  previsaoProximos7Dias,
  produtosMaisLucrativos = [],
  produtosPorCategoria = {},
  resumo = {},
  sanitizarNumero,
}) {
  const produtosBaixaMargem = produtosMaisLucrativos
    .filter((produto) => sanitizarNumero(produto.margem) < 25)
    .slice(0, 5);

  const oportunidadesBaixaVenda = produtosMaisLucrativos
    .filter(
      (produto) =>
        sanitizarNumero(produto.margem) >= 40 && sanitizarNumero(produto.quantidade) < 10,
    )
    .slice(0, 3);

  const oportunidadesCampeoes = produtosMaisLucrativos
    .filter((produto) => sanitizarNumero(produto.margem) >= 40)
    .slice(0, 2);

  return (
    <div className="space-y-6">
      {loading && (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}

      {!loading && (
        <>
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
            <div className="flex items-center gap-3 mb-2">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <h2 className="text-2xl font-bold">Analise Inteligente de Produtos</h2>
            </div>
            <p className="text-blue-100">
              Identifique produtos lucrativos, alertas e oportunidades de melhoria no mix.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CardIndicador
              className="border-blue-100 text-blue-700"
              hint="Baseado na media diaria dos ultimos dias"
              label="Previsao proximos 7 dias"
              value={formatarMoeda(previsaoProximos7Dias)}
            />
            <CardIndicador
              className="border-amber-100 text-amber-700"
              hint="Atualizados sempre que o periodo ou filtros mudam"
              label="Alertas automaticos"
              value={alertasInteligentesVendas.length}
            />
            <CardIndicador
              className="border-emerald-100 text-emerald-700"
              hint="Periodo atual"
              label="Ticket medio estimado"
              value={formatarMoeda(
                resumo.quantidade_vendas > 0 ? resumo.venda_liquida / resumo.quantidade_vendas : 0,
              )}
            />
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">Alertas Inteligentes Automaticos</h3>

            {alertasInteligentesVendas.length === 0 ? (
              <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
                Nenhum alerta critico no momento. O desempenho esta estavel para o periodo
                analisado.
              </div>
            ) : (
              <div className="space-y-3">
                {alertasInteligentesVendas.map((alerta) => {
                  const classes =
                    alerta.tipo === "critico"
                      ? "bg-red-50 border-red-200"
                      : alerta.tipo === "oportunidade"
                        ? "bg-blue-50 border-blue-200"
                        : "bg-amber-50 border-amber-200";

                  return (
                    <div key={alerta.id} className={`p-4 rounded-lg border ${classes}`}>
                      <div className="font-semibold text-gray-800">{alerta.titulo}</div>
                      <div className="text-sm text-gray-700 mt-1">{alerta.mensagem}</div>
                      <div className="text-sm text-gray-600 mt-2">
                        <strong>Acao sugerida:</strong> {alerta.recomendacao}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <svg
                className="w-6 h-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <h3 className="text-lg font-semibold">Top Produtos por Lucro</h3>
            </div>
            <TopProdutosLucroTable produtos={produtosMaisLucrativos} />
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">Desempenho por Categoria</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(produtosPorCategoria).map(([categoria, dados]) => (
                <div
                  key={categoria}
                  className="border rounded-lg p-4 hover:shadow-lg transition-shadow"
                >
                  <div className="font-semibold text-gray-800 mb-2">{categoria}</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Vendas:</span>
                      <span className="font-semibold">{sanitizarNumero(dados.quantidade)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Faturamento:</span>
                      <span className="font-semibold text-green-600">
                        {formatarMoeda(sanitizarNumero(dados.total))}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Margem Media:</span>
                      <span
                        className={`font-semibold ${
                          sanitizarNumero(dados.margem_media) >= 40
                            ? "text-green-600"
                            : sanitizarNumero(dados.margem_media) >= 25
                              ? "text-yellow-600"
                              : "text-red-600"
                        }`}
                      >
                        {sanitizarNumero(dados.margem_media).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center gap-2 mb-4">
                <svg
                  className="w-6 h-6 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <h3 className="text-lg font-semibold">Atencao: Margens Baixas</h3>
              </div>
              <div className="space-y-2">
                {produtosBaixaMargem.map((produto) => (
                  <div
                    key={`margem-baixa-${produto.nome}-${produto.marca || "sem-marca"}`}
                    className="p-3 bg-red-50 rounded-lg border-l-4 border-red-500"
                  >
                    <div className="font-medium text-sm">{produto.nome}</div>
                    <div className="text-xs text-gray-600 mt-1">
                      Margem:{" "}
                      <span className="font-semibold text-red-600">
                        {sanitizarNumero(produto.margem).toFixed(1)}%
                      </span>
                      {" - "}Revisar preco de custo ou venda
                    </div>
                  </div>
                ))}
                {produtosBaixaMargem.length === 0 && (
                  <div className="text-center text-gray-500 py-4">
                    Nenhum produto com margem critica
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center gap-2 mb-4">
                <svg
                  className="w-6 h-6 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
                <h3 className="text-lg font-semibold">Oportunidades</h3>
              </div>
              <div className="space-y-3">
                {oportunidadesBaixaVenda.map((produto) => (
                  <div
                    key={`oportunidade-${produto.nome}-${produto.marca || "sem-marca"}`}
                    className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-500"
                  >
                    <div className="font-medium text-sm">{produto.nome}</div>
                    <div className="text-xs text-blue-800 mt-1">
                      <strong>Alta margem ({sanitizarNumero(produto.margem).toFixed(1)}%)</strong>{" "}
                      mas poucas vendas ({sanitizarNumero(produto.quantidade)} un.)
                      <br />
                      Considere promover este produto
                    </div>
                  </div>
                ))}
                {oportunidadesCampeoes.map((produto, index) => (
                  <div
                    key={`camp-${produto.nome || index}`}
                    className="p-3 bg-green-50 rounded-lg border-l-4 border-green-500"
                  >
                    <div className="font-medium text-sm">{produto.nome}</div>
                    <div className="text-xs text-green-800 mt-1">
                      <strong>Campeao de vendas</strong> com excelente margem
                      <br />
                      Mantenha em destaque
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {mostrarGraficos && produtosMaisLucrativos.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Margem vs Volume de Vendas</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={produtosMaisLucrativos.slice(0, 15).map((produto) => ({
                    ...produto,
                    margem: sanitizarNumero(produto.margem),
                    quantidade: sanitizarNumero(produto.quantidade),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="nome"
                    angle={-45}
                    textAnchor="end"
                    height={120}
                    interval={0}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    yAxisId="left"
                    orientation="left"
                    stroke="#10B981"
                    label={{
                      value: "Margem %",
                      angle: -90,
                      position: "insideLeft",
                    }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="#3B82F6"
                    label={{
                      value: "Quantidade",
                      angle: 90,
                      position: "insideRight",
                    }}
                  />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="margem" fill="#10B981" name="Margem %" />
                  <Bar yAxisId="right" dataKey="quantidade" fill="#3B82F6" name="Qtd Vendida" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
