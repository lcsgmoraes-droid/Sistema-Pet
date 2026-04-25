import { Calculator, MessageSquare, Stethoscope } from "lucide-react";

export default function ConsultaHeader({
  tituloConsulta,
  consultaIdAtual,
  onAbrirAssistente,
  onAbrirCalculadora,
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-xl">
          <Stethoscope size={22} className="text-blue-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-800">
            {tituloConsulta}
          </h1>
          <p className="text-xs text-gray-400">
            {consultaIdAtual ? `Código da consulta: #${consultaIdAtual}` : "Ainda não salva"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {consultaIdAtual && (
          <button
            type="button"
            onClick={onAbrirAssistente}
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
          >
            <MessageSquare size={16} />
            IA da consulta
          </button>
        )}
        <button
          type="button"
          onClick={onAbrirCalculadora}
          className="inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm font-medium text-cyan-700 hover:bg-cyan-100"
        >
          <Calculator size={16} />
          Calculadora
        </button>
      </div>
    </div>
  );
}
