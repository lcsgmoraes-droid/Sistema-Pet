export default function ComissaoModalFooter({
  canSaveFooter,
  itemSelecionado,
  onClose,
  salvarItem,
}) {
  return (
    <div className="p-6 border-t bg-gray-50">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <p className="text-sm text-gray-600">
            ℹ️ As configurações se aplicam <strong>apenas às comissões futuras</strong>. Comissões
            já geradas não são alteradas.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded hover:bg-gray-50 bg-white">
            Fechar
          </button>
          <button
            onClick={salvarItem}
            disabled={!canSaveFooter}
            className={`px-6 py-2 rounded font-medium ${
              canSaveFooter
                ? "bg-blue-600 hover:bg-blue-700 text-white cursor-pointer"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }`}
          >
            💾 {itemSelecionado ? "Salvar Alterações" : "Atualizar Regras"}
          </button>
        </div>
      </div>
    </div>
  );
}
