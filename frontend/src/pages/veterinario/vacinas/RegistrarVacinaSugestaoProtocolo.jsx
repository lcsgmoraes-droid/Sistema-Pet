import { formatData } from "./vacinaUtils";

export default function RegistrarVacinaSugestaoProtocolo({ form, onSetCampo, sugestaoDose }) {
  if (!sugestaoDose?.protocolo) return null;

  return (
    <div className="md:col-span-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
      <p className="font-semibold text-emerald-800">Sugestao automatica de protocolo</p>
      <p className="text-emerald-700 mt-1">
        Protocolo encontrado: {sugestaoDose.protocolo.nome}
        {sugestaoDose.protocolo.especie ? ` - ${sugestaoDose.protocolo.especie}` : ""}
      </p>
      <p className="text-emerald-700 mt-1">
        Proxima dose sugerida:{" "}
        {sugestaoDose.proximaDose ? formatData(sugestaoDose.proximaDose) : "sem calculo automatico"}
      </p>
      {sugestaoDose.proximaDose && !form.proxima_dose && (
        <button
          type="button"
          onClick={() => onSetCampo("proxima_dose", sugestaoDose.proximaDose)}
          className="mt-2 inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
        >
          Usar esta sugestao
        </button>
      )}
    </div>
  );
}
