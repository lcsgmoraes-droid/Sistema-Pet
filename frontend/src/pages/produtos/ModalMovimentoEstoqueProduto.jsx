import { useState } from "react";
import { montarEstadoMovimentoEstoque, montarPayloadMovimentoEstoque } from "../produtosFormUtils";

export default function ModalMovimentoEstoqueProduto({ tipo, onSave, onClose }) {
  const [dados, setDados] = useState(() => montarEstadoMovimentoEstoque());

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(montarPayloadMovimentoEstoque(tipo, dados));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold">
            {tipo === "entrada" ? "➕ Entrada de Estoque" : "➖ Saída de Estoque"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quantidade *</label>
            <input
              type="number"
              value={dados.quantidade}
              onChange={(e) => setDados({ ...dados, quantidade: e.target.value })}
              step="0.01"
              min="0.01"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="0"
              autoFocus
            />
          </div>

          {tipo === "entrada" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Número do Lote
                </label>
                <input
                  type="text"
                  value={dados.numero_lote}
                  onChange={(e) => setDados({ ...dados, numero_lote: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="LOTE-001"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preço de Custo
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                  <input
                    type="number"
                    value={dados.preco_custo}
                    onChange={(e) => setDados({ ...dados, preco_custo: e.target.value })}
                    step="0.01"
                    min="0"
                    className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0,00"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data de Validade
                </label>
                <input
                  type="date"
                  value={dados.data_validade}
                  onChange={(e) => setDados({ ...dados, data_validade: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Observação</label>
            <textarea
              value={dados.observacao}
              onChange={(e) => setDados({ ...dados, observacao: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Observações sobre este movimento..."
            />
          </div>

          {tipo === "saida" && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>FIFO:</strong> A saída será descontada automaticamente dos lotes mais
                antigos primeiro.
              </p>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className={`px-4 py-2 text-white rounded-lg ${
                tipo === "entrada"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-red-600 hover:bg-red-700"
              }`}
            >
              Confirmar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
