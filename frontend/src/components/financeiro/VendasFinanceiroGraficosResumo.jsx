import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function percentualFormaPagamento(valor, formasRecebimentoFiltradas) {
  const total = formasRecebimentoFiltradas.reduce(
    (sum, item) => sum + item.valor_total,
    0,
  );

  if (!total) return "0.0";

  return ((valor / total) * 100).toFixed(1);
}

export default function VendasFinanceiroGraficosResumo({
  coresGraficos,
  formasRecebimentoFiltradas,
  formatarData,
  formatarDataLocal,
  formatarMoeda,
  melhorDiaSemana,
  melhorHorario,
  mostrarGraficos,
  produtosDetalhadosFiltrados,
  vendasPorDataCalendario,
  vendasPorDiaSemanaResumo,
  vendasPorHorarioComMovimento,
}) {
  if (!mostrarGraficos) return null;

  return (
    <div className="grid grid-cols-2 gap-6 mb-6">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Vendas no Periodo
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={vendasPorDataCalendario}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="data"
              tickFormatter={(value) =>
                formatarDataLocal(value, { day: "2-digit", month: "2-digit" })
              }
            />
            <YAxis
              tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip
              formatter={(value) => formatarMoeda(value)}
              labelFormatter={(label) => formatarData(label)}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="valor_bruto"
              stroke="#3B82F6"
              strokeWidth={2}
              name="Venda Bruta"
            />
            <Line
              type="monotone"
              dataKey="valor_liquido"
              stroke="#10B981"
              strokeWidth={2}
              name="Venda Liquida"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Formas de Pagamento
        </h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={formasRecebimentoFiltradas}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              tickFormatter={(value) => formatarMoeda(value)}
            />
            <YAxis
              type="category"
              dataKey="forma_pagamento"
              width={110}
              style={{ fontSize: "12px" }}
            />
            <Tooltip
              formatter={(value) => [
                `${formatarMoeda(value)} (${percentualFormaPagamento(
                  value,
                  formasRecebimentoFiltradas,
                )}%)`,
                "Valor",
              ]}
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #ccc",
                borderRadius: "4px",
                padding: "8px",
              }}
            />
            <Bar
              dataKey="valor_total"
              fill="#3B82F6"
              radius={[0, 8, 8, 0]}
              label={{
                position: "right",
                formatter: (value) =>
                  `${percentualFormaPagamento(value, formasRecebimentoFiltradas)}%`,
                style: { fontSize: "11px", fontWeight: "bold" },
              }}
            >
              {formasRecebimentoFiltradas.map((entry, index) => (
                <Cell
                  key={`cell-forma-${entry.forma_pagamento || entry.name || index}`}
                  fill={coresGraficos[index % coresGraficos.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg shadow p-4 col-span-2">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Top 10 Categorias de Produtos
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={produtosDetalhadosFiltrados.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="categoria" />
            <YAxis
              tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip formatter={(value) => formatarMoeda(value)} />
            <Legend />
            <Bar dataKey="total_liquido" fill="#3B82F6" name="Valor Liquido" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            Vendas por dia da semana
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
            <span>
              Melhor dia: {melhorDiaSemana?.nome || "-"} com{" "}
              {formatarMoeda(melhorDiaSemana?.valor_liquido || 0)}.
            </span>
            <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
              {melhorDiaSemana?.quantidade || 0} venda(s)
            </span>
          </p>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={vendasPorDiaSemanaResumo}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="curto" />
            <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
            <Tooltip
              formatter={(value, name, props) => {
                const isQuantidade =
                  props?.dataKey === "quantidade" || name === "Vendas";

                return [
                  isQuantidade ? value : formatarMoeda(value),
                  isQuantidade ? "Vendas" : "Valor liquido",
                ];
              }}
              labelFormatter={(label) => {
                const dia = vendasPorDiaSemanaResumo.find(
                  (item) => item.curto === label,
                );
                return dia?.nome || label;
              }}
            />
            <Legend />
            <Bar
              dataKey="valor_liquido"
              fill="#14B8A6"
              name="Valor liquido"
              radius={[6, 6, 0, 0]}
            />
            <Bar
              dataKey="quantidade"
              fill="#94A3B8"
              name="Vendas"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            Vendas por horario
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
            <span>
              Pico: {melhorHorario?.faixa || "-"} com{" "}
              {formatarMoeda(melhorHorario?.valor_liquido || 0)}.
            </span>
            <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
              {melhorHorario?.quantidade || 0} venda(s)
            </span>
          </p>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={vendasPorHorarioComMovimento}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="faixa" />
            <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
            <Tooltip
              formatter={(value, name, props) => {
                const isQuantidade =
                  props?.dataKey === "quantidade" || name === "Vendas";

                return [
                  isQuantidade ? value : formatarMoeda(value),
                  isQuantidade ? "Vendas" : "Valor liquido",
                ];
              }}
            />
            <Legend />
            <Bar
              dataKey="valor_liquido"
              fill="#3B82F6"
              name="Valor liquido"
              radius={[6, 6, 0, 0]}
            />
            <Bar
              dataKey="quantidade"
              fill="#F59E0B"
              name="Vendas"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
