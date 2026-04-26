import { CheckCircle, Download } from "lucide-react";

import { formatMoneyBRL } from "../../../utils/formatters";
import { badgeStatus, badgeTipo, formatData } from "./repasseUtils";

export default function RepasseTabela({
  baixando,
  carregando,
  darBaixa,
  itensFiltrados,
}) {
  if (carregando) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
      </div>
    );
  }

  if (itensFiltrados.length === 0) {
    return <RepasseVazio />;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Descricao</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Tipo</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Valor</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Emissao</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Recebimento</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Acao</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {itensFiltrados.map((item) => (
            <RepasseLinha
              key={item.id}
              baixando={baixando}
              item={item}
              onDarBaixa={darBaixa}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RepasseLinha({ baixando, item, onDarBaixa }) {
  const badge = badgeStatus(item.status);
  const tipoBadge = badgeTipo(item.tipo);

  return (
    <tr className="hover:bg-sky-50 transition-colors">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800 text-sm">{item.descricao}</p>
        {item.observacoes && (
          <p className="text-xs text-gray-400 mt-0.5">{item.observacoes}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tipoBadge.cls}`}>
          {tipoBadge.label}
        </span>
      </td>
      <td className="px-4 py-3 font-semibold text-gray-800">
        {formatMoneyBRL(item.valor)}
      </td>
      <td className="px-4 py-3 text-gray-500">{formatData(item.data_emissao)}</td>
      <td className="px-4 py-3 text-gray-500">{formatData(item.data_recebimento)}</td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
          {badge.label}
        </span>
      </td>
      <td className="px-4 py-3">
        {item.status !== "recebido" ? (
          <button
            onClick={() => onDarBaixa(item.id)}
            disabled={baixando === item.id}
            className="flex items-center gap-1.5 text-xs bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
          >
            <CheckCircle size={12} />
            {baixando === item.id ? "Baixando..." : "Dar baixa"}
          </button>
        ) : (
          <span className="flex items-center gap-1 text-xs text-green-600">
            <CheckCircle size={12} />
            Baixado
          </span>
        )}
      </td>
    </tr>
  );
}

function RepasseVazio() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
      <Download size={36} className="mx-auto text-gray-200 mb-3" />
      <p className="text-gray-400 text-sm">Nenhum lancamento encontrado para o filtro selecionado.</p>
      <p className="text-xs text-gray-300 mt-1">
        Os lancamentos sao gerados automaticamente ao finalizar consultas com procedimentos.
      </p>
    </div>
  );
}
