import { BedDouble } from "lucide-react";
import InternacaoAcoes from "./InternacaoAcoes";
import InternacaoDetalhe from "./InternacaoDetalhe";
import { STATUS_CORES, formatData } from "./internacaoUtils";

export default function InternacaoCard({
  aberta,
  evolucoes,
  internacao,
  onAbrirAlta,
  onAbrirDetalhe,
  onAbrirEvolucao,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
  onAbrirInsumoRapido,
  procedimentos,
}) {
  const estaAtiva = internacao.status === "ativa" || internacao.status === "internado";

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div
        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => onAbrirDetalhe(internacao.id)}
      >
        <BedDouble size={18} className="text-purple-400 shrink-0" />
        <ResumoInternacao internacao={internacao} />
        <DatasInternacao internacao={internacao} />
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            STATUS_CORES[internacao.status] ?? "bg-gray-100"
          }`}
        >
          {internacao.status}
        </span>
        {estaAtiva && (
          <InternacaoAcoes
            internacao={internacao}
            onAbrirInsumoRapido={onAbrirInsumoRapido}
            onAbrirEvolucao={onAbrirEvolucao}
            onAbrirAlta={onAbrirAlta}
            onAbrirFichaPet={onAbrirFichaPet}
            onAbrirHistoricoPet={onAbrirHistoricoPet}
          />
        )}
      </div>

      {aberta && <InternacaoDetalhe internacao={internacao} evolucoes={evolucoes} procedimentos={procedimentos} />}
    </div>
  );
}

function ResumoInternacao({ internacao }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="font-semibold text-gray-800">
        {internacao.pet_nome ?? `Pet #${String(internacao.pet_id ?? "").slice(0, 6)}`}
      </p>
      {internacao.tutor_nome && <p className="text-xs text-gray-500">Tutor: {internacao.tutor_nome}</p>}
      <p className="text-xs text-gray-400 truncate">{internacao.motivo ?? internacao.motivo_internacao}</p>
    </div>
  );
}

function DatasInternacao({ internacao }) {
  return (
    <div className="text-right shrink-0">
      <p className="text-xs text-gray-400">Entrada: {formatData(internacao.data_entrada)}</p>
      {internacao.data_saida && <p className="text-xs text-gray-400">Alta: {formatData(internacao.data_saida)}</p>}
      {internacao.box && <p className="text-xs text-gray-500">Box: {internacao.box}</p>}
    </div>
  );
}
