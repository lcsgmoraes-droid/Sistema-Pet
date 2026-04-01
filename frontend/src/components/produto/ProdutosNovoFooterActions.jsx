export default function ProdutosNovoFooterActions({ isEdicao, onCancel, salvando }) {
  return (
    <div className="mt-6 flex justify-end gap-4">
      <button
        type="button"
        onClick={onCancel}
        className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Cancelar
      </button>
      <button
        type="submit"
        disabled={salvando}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
      >
        {salvando ? 'Salvando...' : isEdicao ? 'Atualizar' : 'Cadastrar'}
      </button>
    </div>
  );
}
