export default function AltaInternacaoModal({
  isOpen,
  formAlta,
  setFormAlta,
  onClose,
  onConfirm,
  salvando,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-bold text-gray-800">Dar alta</h2>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Observações de alta</label>
          <textarea
            value={formAlta}
            onChange={(e) => setFormAlta(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-28"
            placeholder="Instruções para o tutor, condição na saída..."
          />
        </div>
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={salvando}
            className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
          >
            {salvando ? "Processando..." : "Confirmar alta"}
          </button>
        </div>
      </div>
    </div>
  );
}
