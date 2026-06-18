import { CheckCircle, ChevronRight } from "lucide-react";

export default function ConsultaSteps({
  etapas,
  etapaAtual,
  modoSomenteLeitura,
  podeNavegarLivremente = false,
  onChangeEtapa,
}) {
  function podeAbrirEtapa(indice) {
    return modoSomenteLeitura || podeNavegarLivremente || indice <= etapaAtual;
  }

  function handleClick(indice) {
    if (podeAbrirEtapa(indice)) {
      onChangeEtapa(indice);
    }
  }

  return (
    <div className="flex items-center gap-1">
      {etapas.map((nome, indice) => {
        const liberada = podeAbrirEtapa(indice);
        const concluida = indice < etapaAtual;
        const classeEtapa =
          indice === etapaAtual
            ? "bg-blue-600 text-white"
            : liberada
              ? "bg-blue-100 text-blue-700 cursor-pointer hover:bg-blue-200"
              : "bg-gray-100 text-gray-400 cursor-not-allowed";

        return (
          <div key={nome} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => handleClick(indice)}
              disabled={!liberada}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${classeEtapa}`}
            >
              {concluida ? <CheckCircle size={12} /> : null}
              {indice + 1}. {nome}
            </button>
            {indice < etapas.length - 1 && <ChevronRight size={14} className="text-gray-300" />}
          </div>
        );
      })}
    </div>
  );
}
