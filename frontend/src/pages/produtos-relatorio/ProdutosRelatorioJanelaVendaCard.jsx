import { formatarMoeda } from "../../api/produtos";
import { formatarQuantidade } from "./produtosRelatorioFormatters";

export default function ProdutosRelatorioJanelaVendaCard({ janela, ativa }) {
  return (
    <div
      className={`rounded-2xl border p-4 shadow-sm transition-colors ${
        ativa ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">Ultimos {janela.dias} dias</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {formatarQuantidade(janela.quantidade_vendida)}
          </p>
          <p className="mt-1 text-xs font-medium uppercase tracking-wide text-gray-500">
            unidades vendidas
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            ativa ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
          }`}
        >
          {janela.numero_vendas} vendas
        </span>
      </div>
      <div className="mt-3 space-y-1 text-xs text-gray-600">
        <p>Media/dia: {formatarQuantidade(janela.media_diaria)}</p>
        <p>Valor vendido: {formatarMoeda(janela.valor_vendido)}</p>
      </div>
    </div>
  );
}
