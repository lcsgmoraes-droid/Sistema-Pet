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
import ProdutosPromocionaisTable from "./ProdutosPromocionaisTable";

export default function VendasPromocoesResumoPanel({ analisePromocoes, formatarMoeda }) {
  return (
    <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">
            Vendas normais x preco promocional
          </h3>
          <p className="text-sm text-gray-500">
            Itens vendidos pelo preco promocional ativo no ERP, ecommerce ou app.
          </p>
        </div>
        <div className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700">
          {analisePromocoes.percentualPromocao}% das vendas com promocao
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase text-slate-500">Vendas normais</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{analisePromocoes.vendasNormais}</p>
          <p className="text-xs text-slate-500">
            {formatarMoeda(analisePromocoes.valorVendasNormais)}
          </p>
        </div>
        <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-3">
          <p className="text-xs font-semibold uppercase text-cyan-700">Com preco promocional</p>
          <p className="mt-1 text-2xl font-bold text-cyan-800">{analisePromocoes.vendasPromocao}</p>
          <p className="text-xs text-cyan-700">
            {formatarMoeda(analisePromocoes.valorVendasPromocao)}
          </p>
        </div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-xs font-semibold uppercase text-blue-700">Itens promocionais</p>
          <p className="mt-1 text-2xl font-bold text-blue-800">
            {formatarMoeda(analisePromocoes.valorItensPromocionais)}
          </p>
          <p className="text-xs text-blue-700">Valor dos itens identificados</p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-semibold uppercase text-amber-700">Economia promocional</p>
          <p className="mt-1 text-2xl font-bold text-amber-800">
            {formatarMoeda(analisePromocoes.descontoPromocional)}
          </p>
          <p className="text-xs text-amber-700">Soma estimada nos itens marcados</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="h-[260px] rounded-lg border border-slate-100 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analisePromocoes.comparativo}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="tipo" />
              <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
              <Tooltip
                formatter={(value, name, props) => {
                  const isQuantidade = props?.dataKey === "quantidade" || name === "Vendas";

                  return [
                    isQuantidade ? value : formatarMoeda(value),
                    isQuantidade ? "Vendas" : "Valor",
                  ];
                }}
              />
              <Legend />
              <Bar dataKey="valor" name="Valor" fill="#06B6D4" radius={[6, 6, 0, 0]} />
              <Bar dataKey="quantidade" name="Vendas" fill="#64748B" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-slate-100">
          <ProdutosPromocionaisTable produtos={analisePromocoes.topProdutos} />
        </div>
      </div>
    </div>
  );
}
