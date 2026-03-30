import { X } from "lucide-react";

export default function PDVDescontoItemModal({
  itemEditando,
  onChangeItem,
  onClose,
  onRemover,
  onSalvar,
}) {
  if (!itemEditando) {
    return null;
  }

  const totalBruto = itemEditando.preco * itemEditando.quantidade;
  const descontoCalculado =
    itemEditando.tipoDesconto === "valor"
      ? itemEditando.descontoValor
      : (totalBruto * itemEditando.descontoPercentual) / 100;
  const percentualEquivalente =
    itemEditando.tipoDesconto === "percentual"
      ? itemEditando.descontoPercentual
      : totalBruto > 0
        ? (itemEditando.descontoValor / totalBruto) * 100
        : 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">
            Alterar item da venda
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold text-gray-900">
              {itemEditando.produto_nome}
            </h4>
            <p className="text-sm text-gray-600">
              Código: {itemEditando.produto_codigo}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Preço <span className="text-red-600">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-gray-500">
                  R$
                </span>
                <input
                  type="number"
                  step="0.01"
                  value={itemEditando.preco}
                  onChange={(e) =>
                    onChangeItem({
                      ...itemEditando,
                      preco: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Quantidade
              </label>
              <input
                type="number"
                step="0.001"
                value={itemEditando.quantidade}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subtotal
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-gray-500">
                  R$
                </span>
                <input
                  type="text"
                  value={totalBruto.toFixed(2)}
                  readOnly
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de desconto
            </label>
            <div className="flex gap-2">
              <button
                onClick={() =>
                  onChangeItem({
                    ...itemEditando,
                    tipoDesconto: "valor",
                    descontoPercentual: 0,
                  })
                }
                className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                  itemEditando.tipoDesconto === "valor"
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "bg-white border-gray-300 text-gray-700 hover:border-blue-400"
                }`}
              >
                R$
              </button>
              <button
                onClick={() =>
                  onChangeItem({
                    ...itemEditando,
                    tipoDesconto: "percentual",
                    descontoValor: 0,
                  })
                }
                className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                  itemEditando.tipoDesconto === "percentual"
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
              Valor do desconto
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-gray-500">
                {itemEditando.tipoDesconto === "valor" ? "R$" : "%"}
              </span>
              <input
                type="number"
                step="0.01"
                value={
                  itemEditando.tipoDesconto === "valor"
                    ? itemEditando.descontoValor
                    : itemEditando.descontoPercentual
                }
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  if (itemEditando.tipoDesconto === "valor") {
                    onChangeItem({
                      ...itemEditando,
                      descontoValor: val,
                    });
                    return;
                  }

                  onChangeItem({
                    ...itemEditando,
                    descontoPercentual: val,
                  });
                }}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex justify-between text-sm">
              <span className="text-gray-700">Total bruto</span>
              <span className="font-medium">R$ {totalBruto.toFixed(2)}</span>
            </div>
            {(itemEditando.descontoValor > 0 ||
              itemEditando.descontoPercentual > 0) && (
              <>
                <div className="flex justify-between text-sm text-red-600 mt-1">
                  <span>Desconto</span>
                  <span className="font-medium">
                    - R$ {descontoCalculado.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm text-orange-600 mt-1">
                  <span>{percentualEquivalente.toFixed(2)}% de desconto</span>
                </div>
              </>
            )}
            <div className="flex justify-between font-bold text-lg mt-2 pt-2 border-t border-blue-200">
              <span>Total líquido</span>
              <span className="text-green-600">
                R$ {(totalBruto - descontoCalculado).toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-between gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Fechar
          </button>
          <button
            onClick={onRemover}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Remover
          </button>
          <button
            onClick={onSalvar}
            className="flex-1 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}
