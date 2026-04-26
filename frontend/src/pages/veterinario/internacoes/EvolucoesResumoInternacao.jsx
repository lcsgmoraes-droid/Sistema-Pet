import { Clock } from "lucide-react";
import { formatDateTime } from "./internacaoUtils";

export default function EvolucoesResumoInternacao({ evolucoes }) {
  return (
    <>
      <p className="text-xs font-semibold text-gray-500 mb-3">Evoluções</p>
      {evolucoes.length === 0 ? (
        <p className="text-xs text-gray-400">Nenhuma evolução registrada ainda.</p>
      ) : (
        <div className="space-y-2">
          {evolucoes.map((evolucao, index) => (
            <EvolucaoResumoCard key={index} evolucao={evolucao} />
          ))}
        </div>
      )}
    </>
  );
}

function EvolucaoResumoCard({ evolucao }) {
  return (
    <div className="bg-white border border-gray-100 rounded-lg px-3 py-2 text-xs">
      <div className="flex items-center gap-2 text-gray-400 mb-1">
        <Clock size={10} />
        <span>{formatDateTime(evolucao.data_hora)}</span>
      </div>
      <div className="flex gap-4 text-gray-600">
        {evolucao.temperatura && <span>Temp: {evolucao.temperatura}°C</span>}
        {evolucao.freq_cardiaca && <span>FC: {evolucao.freq_cardiaca} bpm</span>}
        {evolucao.freq_respiratoria && <span>FR: {evolucao.freq_respiratoria} rpm</span>}
      </div>
      {evolucao.observacoes && <p className="text-gray-500 mt-1">{evolucao.observacoes}</p>}
    </div>
  );
}
