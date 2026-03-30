import { X } from "lucide-react";

export default function PDVDescontoTotalModal({
  itens,
  onAplicar,
  onClose,
  setTipoDescontoTotal,
  setValorDescontoTotal,
  tipoDescontoTotal,
  valorDescontoTotal,
}) {
  const totalBruto = itens.reduce(
    (sum, item) =>
      sum + (item.preco_unitario || item.preco_venda) * item.quantidade,
    0,
  );
  const descontoPreview =
    tipoDescontoTotal === "valor"
      ? Math.min(valorDescontoTotal, totalBruto)
      : (totalBruto * Math.min(valorDescontoTotal, 100)) / 100;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">
            💰 Aplicar desconto
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="bg-gray-100 p-4 rounded-lg">
            <div className="text-sm text-gray-600">
              Total bruto (sem desconto)
            </div>
            <div className="text-2xl font-bold text-gray-900">
              R$ {totalBruto.toFixed(2)}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de desconto
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setTipoDescontoTotal("valor")}
                className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                  tipoDescontoTotal === "valor"
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "bg-white border-gray-300 text-gray-700 hover:border-blue-400"
                }`}
              >
                R$
              </button>
              <button
                onClick={() => setTipoDescontoTotal("percentual")}
                className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                  tipoDescontoTotal === "percentual"
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "bg-white border-gray-300 text-gray-700 hover:border-blue-400"
                }`}
              >
                %
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Valor
            </label>
            <div className="relative">
              <span className="absolute left-3 top-3 text-gray-500">
                {tipoDescontoTotal === "valor" ? "R$" : "%"}
              </span>
              <input
                type="number"
                step="0.01"
                value={valorDescontoTotal}
                onChange={(e) =>
                  setValorDescontoTotal(parseFloat(e.target.value) || 0)
                }
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-700">Desconto</span>
              <span className="text-red-600 font-medium">
                - R$ {descontoPreview.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-baseline border-t border-blue-200 pt-2 mt-2">
              <span className="text-sm text-gray-700">Total líquido</span>
              <span className="text-2xl font-bold text-green-600">
                R$ {Math.max(0, totalBruto - descontoPreview).toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Fechar
          </button>
          <button
            onClick={() => onAplicar(tipoDescontoTotal, valorDescontoTotal)}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
