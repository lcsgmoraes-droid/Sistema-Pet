import { CheckCircle, Clock, DollarSign } from "lucide-react";

import { formatMoneyBRL } from "../../../utils/formatters";

export default function RepasseResumoCards({
  itensFiltrados,
  qtdPendentes,
  qtdRecebidos,
  totalFiltrado,
  totalPendenteFiltrado,
  totalRecebidoFiltrado,
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <ResumoCard
        icon={<DollarSign size={16} className="text-sky-500" />}
        label="Total no periodo"
        value={formatMoneyBRL(totalFiltrado)}
        hint={`${itensFiltrados.length} lancamento(s)`}
      />
      <ResumoCard
        icon={<CheckCircle size={16} className="text-green-500" />}
        label="Recebido"
        value={formatMoneyBRL(totalRecebidoFiltrado)}
        hint={`${qtdRecebidos} lancamento(s) baixado(s)`}
        valueClassName="text-green-700"
      />
      <ResumoCard
        icon={<Clock size={16} className="text-yellow-500" />}
        label="Pendente"
        value={formatMoneyBRL(totalPendenteFiltrado)}
        hint={`${qtdPendentes} aguardando baixa`}
        valueClassName="text-yellow-700"
      />
    </div>
  );
}

function ResumoCard({ hint, icon, label, value, valueClassName = "text-gray-800" }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${valueClassName}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-1">{hint}</p>
    </div>
  );
}
