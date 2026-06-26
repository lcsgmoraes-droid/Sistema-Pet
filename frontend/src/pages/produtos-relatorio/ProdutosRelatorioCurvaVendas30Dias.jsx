import { formatarDiaCurto, formatarQuantidade } from "./produtosRelatorioFormatters";

export default function ProdutosRelatorioCurvaVendas30Dias({ pontos }) {
  const maximo = Math.max(...pontos.map((ponto) => Number(ponto.quantidade || 0)), 1);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Ritmo de vendas nos ultimos 30 dias
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Ajuda a enxergar picos, dias sem giro e o padrao real do item.
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          Janela curta para compra
        </span>
      </div>

      <div className="mt-5 flex h-32 items-end gap-1.5">
        {pontos.map((ponto, index) => {
          const quantidade = Number(ponto.quantidade || 0);
          const altura = quantidade <= 0 ? 8 : Math.max((quantidade / maximo) * 100, 10);
          const destacar = index >= pontos.length - 7;

          return (
            <div key={ponto.data} className="group flex flex-1 flex-col items-center justify-end">
              <div
                className={`w-full rounded-t-md transition-all ${
                  destacar ? "bg-blue-500" : "bg-slate-300"
                }`}
                style={{ height: `${altura}%` }}
                title={`${formatarDiaCurto(ponto.data)} - ${formatarQuantidade(quantidade)} un`}
              />
              <span className="mt-2 text-[10px] text-gray-500 group-hover:text-gray-700">
                {index % 5 === 0 || index === pontos.length - 1 ? formatarDiaCurto(ponto.data) : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
