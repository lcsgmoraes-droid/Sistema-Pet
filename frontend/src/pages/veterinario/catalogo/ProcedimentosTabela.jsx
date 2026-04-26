import { Loader2 } from "lucide-react";
import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { LinhaAcoes } from "./shared";

export default function ProcedimentosTabela({ carregando, lista, onEditar, onExcluir, removendoId }) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      {carregando ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
        </div>
      ) : lista.length === 0 ? (
        <div className="p-8 text-center text-sm text-gray-400">Nenhum procedimento cadastrado.</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Procedimento</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Insumos</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Duracao</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Preco sugerido</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Margem estimada</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {lista.map((item) => (
              <LinhaProcedimento
                key={item.id}
                item={item}
                onEditar={onEditar}
                onExcluir={onExcluir}
                removendo={removendoId === item.id}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function LinhaProcedimento({ item, onEditar, onExcluir, removendo }) {
  const duracao = item.duracao_minutos || item.duracao_estimada_min;

  return (
    <tr className="hover:bg-teal-50">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{item.nome}</p>
        <p className="text-xs text-gray-500">
          {item.categoria || item.descricao || (item.requer_anestesia ? "Requer anestesia" : "-")}
        </p>
      </td>
      <td className="px-4 py-3 text-gray-600">
        {Array.isArray(item.insumos) && item.insumos.length > 0 ? `${item.insumos.length} item(ns)` : "-"}
      </td>
      <td className="px-4 py-3 text-gray-600">{duracao ? `${duracao} min` : "-"}</td>
      <td className="px-4 py-3 text-gray-600">{formatMoneyBRL(item.valor_padrao || 0)}</td>
      <td className="px-4 py-3">
        <p className={`font-medium ${(item.margem_estimada || 0) < 0 ? "text-red-600" : "text-emerald-700"}`}>
          {formatMoneyBRL(item.margem_estimada || 0)}
        </p>
        <p className="text-xs text-gray-400">{formatPercent(item.margem_percentual_estimada || 0)}</p>
      </td>
      <td className="px-4 py-3">
        <LinhaAcoes onEditar={() => onEditar(item)} onExcluir={() => onExcluir(item)} removendo={removendo} />
      </td>
    </tr>
  );
}
