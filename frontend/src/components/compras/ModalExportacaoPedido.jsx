import SeletorColunasDocumentoPedido from "./pedidoDocumentoColunas";

const ModalExportacaoPedido = ({
  pedido,
  onClose,
  onConfirmar,
  loading,
  colunasSelecionadas,
  onChangeColunas,
}) => {
  if (!pedido) return null;

  const formatoLabel = pedido.formato === "pdf" ? "PDF" : "Excel";

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
        <div className="flex justify-between items-center gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-800">Exportar {formatoLabel}</h2>
            <p className="mt-1 text-sm text-gray-500">Pedido {pedido.numero_pedido}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={loading}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <SeletorColunasDocumentoPedido
          colunasSelecionadas={colunasSelecionadas}
          onChange={onChangeColunas}
          titulo="Colunas do documento"
          descricao="Escolha exatamente o que deve aparecer no arquivo antes de baixar ou encaminhar."
        />

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onConfirmar}
            disabled={loading}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? `Gerando ${formatoLabel}...` : `Gerar ${formatoLabel}`}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-lg border border-slate-300 px-4 py-3 font-semibold text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModalExportacaoPedido;
