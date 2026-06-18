import { useState } from "react";
import { toast } from "react-hot-toast";

// Modal de Recebimento
const ModalRecebimento = ({ pedido, onClose, onReceber }) => {
  const [itensRecebimento, setItensRecebimento] = useState(
    pedido.itens.map((item) => ({
      item_id: item.id,
      quantidade_recebida: item.quantidade_pedida - item.quantidade_recebida,
      max: item.quantidade_pedida - item.quantidade_recebida,
    })),
  );

  const handleReceber = () => {
    const itens = itensRecebimento
      .filter((i) => i.quantidade_recebida > 0)
      .map((i) => ({
        item_id: i.item_id,
        quantidade_recebida: parseFloat(i.quantidade_recebida),
      }));

    if (itens.length === 0) {
      toast.error("Informe a quantidade recebida de pelo menos 1 item");
      return;
    }

    onReceber(itens);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">📦 Receber Pedido {pedido.numero_pedido}</h2>

        <div className="space-y-4">
          {pedido.itens.map((item, index) => (
            <div key={item.id} className="border rounded-lg p-4">
              <div className="font-semibold mb-2">{item.produto_nome}</div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Pedido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_pedida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Já Recebido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_recebida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Pendente:</span>
                  <span className="ml-2 font-semibold text-orange-600">
                    {item.quantidade_pedida - item.quantidade_recebida}
                  </span>
                </div>
              </div>
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade a Receber
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max={itensRecebimento[index].max}
                  value={itensRecebimento[index].quantidade_recebida}
                  onChange={(e) => {
                    const novoValor = parseFloat(e.target.value) || 0;
                    const novaLista = [...itensRecebimento];
                    novaLista[index].quantidade_recebida = Math.min(
                      novoValor,
                      novaLista[index].max,
                    );
                    setItensRecebimento(novaLista);
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 mt-6">
          <button
            onClick={handleReceber}
            className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
          >
            ✅ Confirmar Recebimento
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
          >
            ❌ Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModalRecebimento;
