import { MessageSquarePlus, RefreshCw } from "lucide-react";
import { assistenteIaCss } from "./assistenteIAUtils";

export default function AssistenteIAConversaSelector({
  conversaId,
  conversas,
  filtrarConversasContexto,
  onAtualizarConversas,
  onNovaConversa,
  setConversaId,
  setFiltrarConversasContexto,
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
      <div className="md:col-span-2">
        <label htmlFor="vet-ia-conversa" className="block text-xs font-medium text-gray-600 mb-1">
          Conversa salva
        </label>
        <select
          id="vet-ia-conversa"
          value={conversaId}
          onChange={(event) => setConversaId(event.target.value)}
          className={assistenteIaCss.select}
        >
          <option value="">Nova conversa</option>
          {conversas.map((conversa) => (
            <option key={conversa.id} value={conversa.id}>
              {conversa.titulo || `Conversa #${conversa.id}`}
            </option>
          ))}
        </select>
        <label className="mt-2 inline-flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={filtrarConversasContexto}
            onChange={(event) => setFiltrarConversasContexto(event.target.checked)}
          />
          <span>Filtrar conversas pelo contexto atual (pet/consulta/exame)</span>
        </label>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onNovaConversa}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-gray-200 hover:bg-gray-50"
        >
          <MessageSquarePlus size={14} /> Nova
        </button>
        <button
          type="button"
          onClick={onAtualizarConversas}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-gray-200 hover:bg-gray-50"
        >
          <RefreshCw size={14} /> Atualizar
        </button>
      </div>
    </div>
  );
}
