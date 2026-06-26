import ProdutosValidadeMobileList from "./ProdutosValidadeMobileList";
import ProdutosValidadePagination from "./ProdutosValidadePagination";
import ProdutosValidadeTable from "./ProdutosValidadeTable";

export default function ProdutosValidadeLotesPanel({ controller }) {
  const { dados, fimItem, inicioItem, loading } = controller;

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-gray-200 px-4 py-4 md:px-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Lotes ordenados por vencimento</h2>
          <p className="text-sm text-gray-600">
            {loading
              ? "Atualizando dados..."
              : `Exibindo ${inicioItem}-${fimItem} de ${dados.total} lote(s).`}
          </p>
        </div>

        <div className="flex flex-wrap gap-2 text-xs text-gray-500">
          <span className="rounded-full bg-slate-100 px-3 py-1.5">
            Ordenacao padrao: validade crescente
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1.5">
            Paginacao leve para uso operacional
          </span>
        </div>
      </div>

      <ProdutosValidadeMobileList controller={controller} />
      <ProdutosValidadeTable controller={controller} />
      <ProdutosValidadePagination controller={controller} />
    </div>
  );
}
