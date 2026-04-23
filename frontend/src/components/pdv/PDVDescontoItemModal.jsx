import { X } from "lucide-react";
import { resolveMediaUrl } from "../../utils/mediaUrl";

function obterImagemDetalheItem(item) {
  return (
    item?.produto_imagem_principal ||
    item?.produto?.imagem_principal ||
    item?.produto_imagem_thumbnail ||
    item?.produto?.imagem_principal_thumbnail ||
    null
  );
}

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
  const imagemProduto = resolveMediaUrl(obterImagemDetalheItem(itemEditando));

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-xl font-bold text-gray-900">
            Alterar item da venda
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 transition-colors hover:text-gray-600"
          >
            <X size={24} />
          </button>
        </div>

        <div className="space-y-4 p-6">
          <div className="flex items-start gap-4 rounded-lg bg-gray-50 p-4">
            {imagemProduto ? (
              <img
                src={imagemProduto}
                alt={itemEditando.produto_nome || "Produto"}
                className="h-28 w-28 flex-shrink-0 rounded-xl border border-gray-200 bg-white object-cover"
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            ) : (
              <div className="flex h-28 w-28 flex-shrink-0 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-xs text-gray-400">
                Sem foto
              </div>
            )}
            <div className="min-w-0 space-y-2">
              <div>
                <h4 className="text-lg font-semibold leading-tight text-gray-900">
                  {itemEditando.produto_nome}
                </h4>
                <p className="text-sm text-gray-600">
                  Codigo: {itemEditando.produto_codigo}
                </p>
              </div>
              <p className="text-xs text-gray-500">
                Confira a imagem, o preco e o desconto antes de salvar.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Preco <span className="text-red-600">*</span>
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
                  className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-3 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Quantidade
              </label>
              <input
                type="number"
                step="0.001"
                value={itemEditando.quantidade}
                readOnly
                className="w-full rounded-lg border border-gray-300 bg-gray-100 px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
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
                  className="w-full rounded-lg border border-gray-300 bg-gray-100 py-2 pl-10 pr-3"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
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
                className={`flex-1 rounded-lg border-2 px-4 py-2 transition-colors ${
                  itemEditando.tipoDesconto === "valor"
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-gray-300 bg-white text-gray-700 hover:border-blue-400"
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
                className={`flex-1 rounded-lg border-2 px-4 py-2 transition-colors ${
                  itemEditando.tipoDesconto === "percentual"
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-gray-300 bg-white text-gray-700 hover:border-blue-400"
                }`}
              >
                %
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
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
                className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-3 focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="rounded-lg bg-blue-50 p-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-700">Total bruto</span>
              <span className="font-medium">R$ {totalBruto.toFixed(2)}</span>
            </div>
            {(itemEditando.descontoValor > 0 ||
              itemEditando.descontoPercentual > 0) && (
              <>
                <div className="mt-1 flex justify-between text-sm text-red-600">
                  <span>Desconto</span>
                  <span className="font-medium">
                    - R$ {descontoCalculado.toFixed(2)}
                  </span>
                </div>
                <div className="mt-1 flex justify-between text-sm text-orange-600">
                  <span>{percentualEquivalente.toFixed(2)}% de desconto</span>
                </div>
              </>
            )}
            <div className="mt-2 flex justify-between border-t border-blue-200 pt-2 text-lg font-bold">
              <span>Total liquido</span>
              <span className="text-green-600">
                R$ {(totalBruto - descontoCalculado).toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-between gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-6 py-2 text-gray-700 transition-colors hover:bg-gray-100"
          >
            Fechar
          </button>
          <button
            onClick={onRemover}
            className="rounded-lg bg-red-600 px-6 py-2 text-white transition-colors hover:bg-red-700"
          >
            Remover
          </button>
          <button
            onClick={onSalvar}
            className="flex-1 rounded-lg bg-green-600 px-6 py-2 text-white transition-colors hover:bg-green-700"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}
