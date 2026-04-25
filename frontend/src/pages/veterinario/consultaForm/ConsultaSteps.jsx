import { CheckCircle, ChevronRight } from "lucide-react";

export default function ConsultaSteps({
  etapas,
  etapaAtual,
  modoSomenteLeitura,
  onChangeEtapa,
}) {
  function handleClick(indice) {
    if (modoSomenteLeitura || indice < etapaAtual) {
      onChangeEtapa(indice);
    }
  }

  return (
    <div className="flex items-center gap-1">
      {etapas.map((nome, indice) => (
        <div key={nome} className="flex items-center gap-1">
          <button
            onClick={() => handleClick(indice)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              indice === etapaAtual
                ? "bg-blue-600 text-white"
                : indice < etapaAtual
                ? "bg-blue-100 text-blue-700 cursor-pointer hover:bg-blue-200"
                : "bg-gray-100 text-gray-400 cursor-default"
            }`}
          >
            {indice < etapaAtual ? <CheckCircle size={12} /> : null}
            {indice + 1}. {nome}
          </button>
          {indice < etapas.length - 1 && <ChevronRight size={14} className="text-gray-300" />}
        </div>
      ))}
    </div>
  );
}
