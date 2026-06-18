import { useState } from "react";
import FornecedorSelector from "../../components/fornecedores/FornecedorSelector";
import {
  montarEstadoFornecedorProduto,
  montarPayloadFornecedorProduto,
} from "../produtosFormUtils";

export default function ModalFornecedorProduto({ fornecedor, clientes, onSave, onClose }) {
  const [dados, setDados] = useState(() => montarEstadoFornecedorProduto(fornecedor));
  const fornecedorSelecionado = clientes.find(
    (cliente) => String(cliente.id) === String(dados.fornecedor_id),
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(montarPayloadFornecedorProduto(dados));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold">
            {fornecedor ? "Editar Fornecedor" : "Adicionar Fornecedor"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Fornecedor *</label>
            <FornecedorSelector
              fornecedores={clientes}
              fornecedorId={dados.fornecedor_id}
              fornecedorSelecionado={fornecedorSelecionado}
              showLabel={false}
              required
              disabled={Boolean(fornecedor)}
              placeholder="Digite o fornecedor..."
              inputClassName="rounded-lg border-gray-300"
              onInputChange={(termo) => {
                if (!termo || dados.fornecedor_id) {
                  setDados({ ...dados, fornecedor_id: "" });
                }
              }}
              onSelect={(fornecedorSelecionado) =>
                setDados({ ...dados, fornecedor_id: String(fornecedorSelecionado.id) })
              }
              onClear={() => setDados({ ...dados, fornecedor_id: "" })}
              onFornecedorCriado={(fornecedorSelecionado) =>
                setDados({ ...dados, fornecedor_id: String(fornecedorSelecionado.id) })
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Código no Fornecedor
            </label>
            <input
              type="text"
              value={dados.codigo_fornecedor}
              onChange={(e) => setDados({ ...dados, codigo_fornecedor: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="SKU-FORNECEDOR-001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Preço de Custo</label>
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
              Prazo de Entrega (dias)
            </label>
            <input
              type="number"
              value={dados.prazo_entrega}
              onChange={(e) => setDados({ ...dados, prazo_entrega: e.target.value })}
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="7"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Estoque no Fornecedor
            </label>
            <input
              type="number"
              value={dados.estoque_fornecedor}
              onChange={(e) => setDados({ ...dados, estoque_fornecedor: e.target.value })}
              step="0.01"
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="100"
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={dados.e_principal}
              onChange={(e) => setDados({ ...dados, e_principal: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded"
            />
            <label className="text-sm font-medium text-gray-700">Fornecedor Principal</label>
          </div>

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
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Salvar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
