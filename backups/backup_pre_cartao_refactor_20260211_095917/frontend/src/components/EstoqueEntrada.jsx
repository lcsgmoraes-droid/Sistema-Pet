import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const EstoqueEntrada = () => {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    produto_id: '',
    quantidade: '',
    custo_unitario: '',
    numero_lote: '',
    data_fabricacao: '',
    data_validade: '',
    fornecedor: '',
    motivo: 'Entrada manual de estoque',
    observacoes: ''
  });

  useEffect(() => {
    carregarProdutos();
  }, []);

  const carregarProdutos = async () => {
    try {
            const response = await api.get(`/produtos/`);
      setProdutos(response.data);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
            const payload = {
        produto_id: parseInt(formData.produto_id),
        quantidade: parseFloat(formData.quantidade),
        custo_unitario: parseFloat(formData.custo_unitario),
        numero_lote: formData.numero_lote || undefined,
        data_fabricacao: formData.data_fabricacao || undefined,
        data_validade: formData.data_validade || undefined,
        fornecedor: formData.fornecedor || undefined,
        motivo: formData.motivo,
        observacoes: formData.observacoes || undefined
      };

      await api.post(`/estoque/entrada`, payload);

      toast.success('✅ Entrada de estoque realizada com sucesso!');
      
      // Limpar formulário
      setFormData({
        produto_id: '',
        quantidade: '',
        custo_unitario: '',
        numero_lote: '',
        data_fabricacao: '',
        data_validade: '',
        fornecedor: '',
        motivo: 'Entrada manual de estoque',
        observacoes: ''
      });
      
      carregarProdutos();
    } catch (error) {
      console.error('Erro ao dar entrada:', error);
      toast.error(error.response?.data?.detail || 'Erro ao dar entrada no estoque');
    } finally {
      setLoading(false);
    }
  };

  const produtoSelecionado = produtos.find(p => p.id === parseInt(formData.produto_id));

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📦 Entrada de Estoque</h1>
        <p className="text-gray-600">Registre a entrada de produtos no estoque</p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Produto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Produto *
            </label>
            <select
              value={formData.produto_id}
              onChange={(e) => setFormData({ ...formData, produto_id: e.target.value })}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Selecione um produto</option>
              {produtos.map(produto => (
                <option key={produto.id} value={produto.id}>
                  {produto.codigo} - {produto.nome} (Estoque atual: {produto.estoque_atual || 0})
                </option>
              ))}
            </select>
          </div>

          {/* Informações do Produto Selecionado */}
          {produtoSelecionado && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Informações do Produto</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Estoque Atual:</span>
                  <span className="ml-2 font-semibold">{produtoSelecionado.estoque_atual || 0}</span>
                </div>
                <div>
                  <span className="text-gray-600">Estoque Mínimo:</span>
                  <span className="ml-2 font-semibold">{produtoSelecionado.estoque_minimo || 0}</span>
                </div>
                <div>
                  <span className="text-gray-600">Custo Médio:</span>
                  <span className="ml-2 font-semibold">
                    R$ {produtoSelecionado.custo_medio?.toFixed(2) || '0.00'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Preço Venda:</span>
                  <span className="ml-2 font-semibold">
                    R$ {produtoSelecionado.preco_venda?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Quantidade e Custo */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quantidade *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={formData.quantidade}
                onChange={(e) => setFormData({ ...formData, quantidade: e.target.value })}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custo Unitário (R$) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.custo_unitario}
                onChange={(e) => setFormData({ ...formData, custo_unitario: e.target.value })}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Lote e Fornecedor */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Número do Lote
              </label>
              <input
                type="text"
                value={formData.numero_lote}
                onChange={(e) => setFormData({ ...formData, numero_lote: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Ex: LOTE-2026-001"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Fornecedor
              </label>
              <input
                type="text"
                value={formData.fornecedor}
                onChange={(e) => setFormData({ ...formData, fornecedor: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Nome do fornecedor"
              />
            </div>
          </div>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Data de Fabricação
              </label>
              <input
                type="date"
                value={formData.data_fabricacao}
                onChange={(e) => setFormData({ ...formData, data_fabricacao: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Data de Validade
              </label>
              <input
                type="date"
                value={formData.data_validade}
                onChange={(e) => setFormData({ ...formData, data_validade: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Motivo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Motivo *
            </label>
            <input
              type="text"
              value={formData.motivo}
              onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Ex: Compra do fornecedor X"
            />
          </div>

          {/* Observações */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observações
            </label>
            <textarea
              value={formData.observacoes}
              onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
              rows="3"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Observações adicionais..."
            />
          </div>

          {/* Resumo */}
          {formData.quantidade && formData.custo_unitario && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-2">Resumo da Entrada</h3>
              <div className="text-sm space-y-1">
                <div>
                  <span className="text-gray-600">Quantidade:</span>
                  <span className="ml-2 font-semibold">{formData.quantidade}</span>
                </div>
                <div>
                  <span className="text-gray-600">Custo Unitário:</span>
                  <span className="ml-2 font-semibold">R$ {parseFloat(formData.custo_unitario || 0).toFixed(2)}</span>
                </div>
                <div className="pt-2 border-t border-green-300">
                  <span className="text-gray-600">Valor Total:</span>
                  <span className="ml-2 font-bold text-lg text-green-700">
                    R$ {(parseFloat(formData.quantidade || 0) * parseFloat(formData.custo_unitario || 0)).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Botões */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '⏳ Processando...' : '✅ Confirmar Entrada'}
            </button>
            <button
              type="button"
              onClick={() => setFormData({
                produto_id: '',
                quantidade: '',
                custo_unitario: '',
                numero_lote: '',
                data_fabricacao: '',
                data_validade: '',
                fornecedor: '',
                motivo: 'Entrada manual de estoque',
                observacoes: ''
              })}
              className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
            >
              🔄 Limpar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EstoqueEntrada;
