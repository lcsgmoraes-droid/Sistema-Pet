import React, { useState, useEffect } from 'react';
import { X, Plus } from 'lucide-react';
import api from '../api';

const ModalLancamentoDebito = ({ isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    descricao: '',
    valor: '',
    data_lancamento: new Date().toISOString().split('T')[0],
    categoria_id: '',
    conta_bancaria_id: '',
    status: 'previsto',
    observacoes: ''
  });
  
  const [categorias, setCategorias] = useState([]);
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mostrarModalCategoria, setMostrarModalCategoria] = useState(false);
  const [mostrarModalConta, setMostrarModalConta] = useState(false);
  const [categoriaBusca, setCategoriaBusca] = useState('');

  useEffect(() => {
    if (isOpen) {
      carregarDados();
    }
  }, [isOpen]);

  const carregarDados = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // Carregar categorias de despesa hierarquicamente
      const catRes = await api.get('/api/categorias-financeiras/arvore?tipo=despesa&apenas_ativas=true', { headers });
      setCategorias(catRes.data);

      // Carregar contas bancárias
      const contasRes = await api.get('/api/contas-bancarias?apenas_ativas=true', { headers });
      setContas(contasRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      alert('Erro ao carregar dados: ' + (error.response?.data?.detail || error.message));
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const payload = {
        ...formData,
        tipo: 'saida',
        valor: parseFloat(formData.valor),
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        conta_bancaria_id: formData.conta_bancaria_id ? parseInt(formData.conta_bancaria_id) : null,
        data_prevista: formData.status === 'previsto' ? formData.data_lancamento : null,
        data_efetivacao: formData.status === 'realizado' ? formData.data_lancamento : null
      };

      await api.post('/api/lancamentos/manuais', payload, { headers });
      
      alert('💸 Lançamento de débito criado com sucesso!');
      onSave();
      handleClose();
    } catch (error) {
      console.error('Erro ao criar lançamento:', error);
      alert('❌ Erro ao criar lançamento: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      descricao: '',
      valor: '',
      data_lancamento: new Date().toISOString().split('T')[0],
      categoria_id: '',
      conta_bancaria_id: '',
      status: 'previsto',
      observacoes: ''
    });
    setCategoriaBusca('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-red-600">💸 Lançamento de Débito (Saída)</h2>
          <button onClick={handleClose} className="text-gray-500 hover:text-gray-700">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Descrição *
            </label>
            <input
              type="text"
              value={formData.descricao}
              onChange={(e) => setFormData({...formData, descricao: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              required
              placeholder="Ex: Conta de luz, Aluguel, Fornecedor..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Valor *
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.valor}
              onChange={(e) => setFormData({...formData, valor: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              required
              placeholder="0,00"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data *
            </label>
            <input
              type="date"
              value={formData.data_lancamento}
              onChange={(e) => setFormData({...formData, data_lancamento: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Categoria
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  list="categorias-list"
                  value={categoriaBusca}
                  onChange={(e) => {
                    setCategoriaBusca(e.target.value);
                    // Buscar categoria pelo caminho completo
                    const cat = categorias.find(c => c.caminho_completo === e.target.value);
                    if (cat) {
                      setFormData({...formData, categoria_id: cat.id});
                    }
                  }}
                  onFocus={(e) => {
                    // Selecionar categoria atual ao focar
                    if (formData.categoria_id) {
                      const cat = categorias.find(c => c.id === parseInt(formData.categoria_id));
                      if (cat) setCategoriaBusca(cat.caminho_completo);
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
                  placeholder="Digite para buscar ou selecione..."
                />
                <datalist id="categorias-list">
                  {categorias.map(cat => (
                    <option key={cat.id} value={cat.caminho_completo} />
                  ))}
                </datalist>
              </div>
              <button
                type="button"
                onClick={() => window.open('/financeiro', '_blank')}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md border border-gray-300"
                title="Adicionar nova categoria"
              >
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Conta Bancária
            </label>
            <div className="flex gap-2">
              <select
                value={formData.conta_bancaria_id}
                onChange={(e) => setFormData({...formData, conta_bancaria_id: e.target.value})}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              >
                <option value="">Selecione...</option>
                {contas.map(conta => (
                  <option key={conta.id} value={conta.id}>
                    {conta.icone || '💳'} {conta.nome} - {formatarMoeda(conta.saldo_atual)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => window.open('/financeiro', '_blank')}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md border border-gray-300"
                title="Adicionar nova conta bancária"
              >
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status *
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({...formData, status: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              required
            >
              <option value="previsto">📅 Previsto (a pagar)</option>
              <option value="realizado">✅ Realizado (pago)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações
            </label>
            <textarea
              value={formData.observacoes}
              onChange={(e) => setFormData({...formData, observacoes: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              rows="2"
              placeholder="Informações adicionais..."
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {loading ? 'Salvando...' : '💸 Salvar Débito'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ModalLancamentoDebito;
