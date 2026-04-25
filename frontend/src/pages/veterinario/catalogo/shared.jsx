import { Loader2, Pencil, Trash2, X } from "lucide-react";

export function formatLista(lista) {
  if (!Array.isArray(lista) || lista.length === 0) return "-";
  return lista.join(", ");
}

export function parseListaTexto(texto) {
  return String(texto || "")
    .split(/[,\n;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function parseNumero(value) {
  if (value == null || value === "") return undefined;
  const numero = Number(String(value).replace(",", "."));
  return Number.isFinite(numero) ? numero : undefined;
}

export function Modal({ titulo, subtitulo, onClose, onSave, salvando, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-800">{titulo}</h2>
            {subtitulo && <p className="mt-1 text-sm text-gray-500">{subtitulo}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal"
          >
            <X size={18} />
          </button>
        </div>
        <div className="mt-5 space-y-4">{children}</div>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={salvando}
            className="flex-1 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function LinhaAcoes({ onEditar, onExcluir, removendo }) {
  return (
    <div className="flex justify-end gap-2">
      <button
        type="button"
        onClick={onEditar}
        className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
      >
        <Pencil size={13} />
        Editar
      </button>
      <button
        type="button"
        onClick={onExcluir}
        disabled={removendo}
        className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
      >
        {removendo ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
        Excluir
      </button>
    </div>
  );
}
