import { formatMoneyBRL } from "../../../utils/formatters";

export default function TopListCard({ itens, title, vazio }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      {itens.length === 0 ? (
        <p className="text-xs text-gray-400">{vazio}</p>
      ) : (
        <div className="space-y-2">
          {itens.map((item, idx) => (
            <div key={`${item.nome}-${idx}`} className="rounded-lg border border-gray-100 px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-gray-700 truncate">{item.nome}</span>
                <span className="text-xs font-semibold text-blue-700 bg-blue-50 rounded-full px-2 py-0.5">
                  {item.quantidade}
                </span>
              </div>
              {item.valor_total != null && (
                <div className="grid grid-cols-3 gap-2 mt-2 text-[11px]">
                  <span className="text-gray-500">Fat. {formatMoneyBRL(item.valor_total)}</span>
                  <span className="text-amber-700">Custo {formatMoneyBRL(item.custo_total || 0)}</span>
                  <span className={(item.margem_total || 0) < 0 ? "text-red-600" : "text-emerald-700"}>
                    Margem {formatMoneyBRL(item.margem_total || 0)}
                  </span>
                </div>
              )}
              {item.entrada_empresa_total != null && (
                <div className="grid grid-cols-3 gap-2 mt-2 text-[11px]">
                  <span className="text-sky-700">Empresa {formatMoneyBRL(item.entrada_empresa_total || 0)}</span>
                  <span className="text-violet-700">Repasse {formatMoneyBRL(item.repasse_empresa_total || 0)}</span>
                  <span className="text-gray-500">Líquido vet {formatMoneyBRL(item.receita_tenant_total || 0)}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
