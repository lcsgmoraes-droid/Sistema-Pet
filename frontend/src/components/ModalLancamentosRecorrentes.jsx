import React, { useState, useEffect } from 'react';
import { X, Plus, Edit2, Trash2, Play } from 'lucide-react';
import api from '../api';

const ModalLancamentosRecorrentes = ({ isOpen, onClose, onSave }) => {
  const [lancamentos, setLancamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editando, setEditando] = useState(null);
  
  const [formData, setFormData] = useState({
    tipo: 'saida',
    descricao: '',
    valor_medio: '',
    categoria_id: '',
    conta_bancaria_id: '',
    frequencia: 'mensal',
    dia_vencimento: '10',
    data_inicio: new Date().toISOString().split('T')[0],
    data_fim: '',
    gerar_automaticamente: true,
    gerar_com_antecedencia_dias: 5,
    observacoes: ''
  });
  
  const [categorias, setCategorias] = useState([]);
  const [contas, setContas] = useState([]);

  useEffect(() => {
    if (isOpen) {
      carregarDados();
    }
  }, [isOpen]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      // Carregar lançamentos recorrentes
      const lancRes = await api.get('/api/lancamentos/recorrentes');
      setLancamentos(lancRes.data);

      // Carregar categorias
      const catRes = await api.get('/financeiro/categorias');
      setCategorias(catRes.data);

      // Carregar contas bancárias
      const contasRes = await api.get('/api/contas-bancarias');
      setContas(contasRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        valor_medio: parseFloat(formData.valor_medio),
        dia_vencimento: parseInt(formData.dia_vencimento),
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        conta_bancaria_id: formData.conta_bancaria_id ? parseInt(formData.conta_bancaria_id) : null,
        data_fim: formData.data_fim || null
      };

      if (editando) {
        await api.put(`/api/lancamentos/recorrentes/${editando.id}`, payload);
        alert('✅ Lançamento recorrente atualizado!');
      } else {
        await api.post('/api/lancamentos/recorrentes', payload);
        alert('✅ Lançamento recorrente criado!');
      }
      
      setShowForm(false);
      setEditando(null);
      resetForm();
      carregarDados();
      onSave();
    } catch (error) {
      console.error('Erro ao salvar lançamento recorrente:', error);
      alert('❌ Erro: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleEditar = (lancamento) => {
    setEditando(lancamento);
    setFormData({
      tipo: lancamento.tipo,
      descricao: lancamento.descricao,
      valor_medio: lancamento.valor_medio.toString(),
      categoria_id: lancamento.categoria_id || '',
      conta_bancaria_id: lancamento.conta_bancaria_id || '',
      frequencia: lancamento.frequencia,
      dia_vencimento: lancamento.dia_vencimento.toString(),
      data_inicio: lancamento.data_inicio,
      data_fim: lancamento.data_fim || '',
      gerar_automaticamente: lancamento.gerar_automaticamente,
      gerar_com_antecedencia_dias: lancamento.gerar_com_antecedencia_dias,
      observacoes: lancamento.observacoes || ''
    });
    setShowForm(true);
  };

  const handleExcluir = async (id) => {
    if (!confirm('Deseja realmente excluir este lançamento recorrente?')) return;

    try {
      await api.delete(`/api/lancamentos/recorrentes/${id}`);
      alert('🗑️ Lançamento recorrente excluído!');
      carregarDados();
      onSave();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      alert('❌ Erro ao excluir: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleGerarParcelas = async (id, descricao) => {
    const meses = prompt(`Quantos meses deseja gerar para "${descricao}"?`, '3');
    if (!meses || isNaN(parseInt(meses))) return;

    setLoading(true);
    try {
      const res = await api.post(
        `/api/lancamentos/recorrentes/${id}/gerar?meses=${meses}`,
        {}
      );
      
      alert(`✅ ${res.data.parcelas} parcela(s) gerada(s) com sucesso!`);
      onSave();
    } catch (error) {
      console.error('Erro ao gerar parcelas:', error);
      alert('❌ Erro: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      tipo: 'saida',
      descricao: '',
      valor_medio: '',
      categoria_id: '',
      conta_bancaria_id: '',
      frequencia: 'mensal',
      dia_vencimento: '10',
      data_inicio: new Date().toISOString().split('T')[0],
      data_fim: '',
      gerar_automaticamente: true,
      gerar_com_antecedencia_dias: 5,
      observacoes: ''
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-blue-600">🔄 Lançamentos Recorrentes</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X size={24} />
          </button>
        </div>

        {!showForm ? (
          <>
            <button
              onClick={() => { resetForm(); setShowForm(true); setEditando(null); }}
              className="mb-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus size={18} />
              Novo Lançamento Recorrente
            </button>

            {loading ? (
              <p className="text-center py-8">Carregando...</p>
            ) : lancamentos.length === 0 ? (
              <p className="text-center py-8 text-gray-500">Nenhum lançamento recorrente cadastrado</p>
            ) : (
              <div className="space-y-3">
                {lancamentos.map(lanc => (
                  <div key={lanc.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-lg">{lanc.descricao}</h3>
                          <span className={`text-xs px-2 py-1 rounded ${lanc.tipo === 'entrada' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {lanc.tipo === 'entrada' ? '💰 Entrada' : '💸 Saída'}
                          </span>
                          {!lanc.ativo && <span className="text-xs px-2 py-1 rounded bg-gray-200 text-gray-600">Inativo</span>}
                        </div>
                        
                        <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-gray-600">
                          <div><strong>Valor Médio:</strong> R$ {lanc.valor_medio.toFixed(2)}</div>
                          <div><strong>Frequência:</strong> {lanc.frequencia}</div>
                          <div><strong>Dia Vencimento:</strong> {lanc.dia_vencimento}</div>
                          <div><strong>Categoria:</strong> {lanc.categoria_nome || '-'}</div>
                          <div><strong>Início:</strong> {new Date(lanc.data_inicio).toLocaleDateString('pt-BR')}</div>
                          <div><strong>Último Gerado:</strong> {lanc.ultimo_mes_gerado ? new Date(lanc.ultimo_mes_gerado).toLocaleDateString('pt-BR') : 'Nunca'}</div>
                        </div>

                        {lanc.observacoes && (
                          <p className="mt-2 text-sm text-gray-500 italic">{lanc.observacoes}</p>
                        )}
                      </div>

                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleGerarParcelas(lanc.id, lanc.descricao)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded"
                          title="Gerar Parcelas"
                        >
                          <Play size={18} />
                        </button>
                        <button
                          onClick={() => handleEditar(lanc)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                          title="Editar"
                        >
                          <Edit2 size={18} />
                        </button>
                        <button
                          onClick={() => handleExcluir(lanc.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded"
                          title="Excluir"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
                <select
                  value={formData.tipo}
                  onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                >
                  <option value="saida">💸 Saída (Despesa)</option>
                  <option value="entrada">💰 Entrada (Receita)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Frequência *</label>
                <select
                  value={formData.frequencia}
                  onChange={(e) => setFormData({...formData, frequencia: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                >
                  <option value="mensal">Mensal</option>
                  <option value="semanal">Semanal</option>
                  <option value="anual">Anual</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
              <input
                type="text"
                value={formData.descricao}
                onChange={(e) => setFormData({...formData, descricao: e.target.value})}
                className="w-full px-3 py-2 border rounded-md"
                required
                placeholder="Ex: Aluguel, Conta de Luz, Salário..."
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor Médio *</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.valor_medio}
                  onChange={(e) => setFormData({...formData, valor_medio: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dia Vencimento *</label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={formData.dia_vencimento}
                  onChange={(e) => setFormData({...formData, dia_vencimento: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Antecedência (dias)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.gerar_com_antecedencia_dias}
                  onChange={(e) => setFormData({...formData, gerar_com_antecedencia_dias: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
                <select
                  value={formData.categoria_id}
                  onChange={(e) => setFormData({...formData, categoria_id: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="">Selecione...</option>
                  {categorias
                    .filter(c => c.tipo === (formData.tipo === 'entrada' ? 'receita' : 'despesa'))
                    .map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.nome}</option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Conta Bancária</label>
                <select
                  value={formData.conta_bancaria_id}
                  onChange={(e) => setFormData({...formData, conta_bancaria_id: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="">Selecione...</option>
                  {contas.map(conta => (
                    <option key={conta.id} value={conta.id}>{conta.nome}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Início *</label>
                <input
                  type="date"
                  value={formData.data_inicio}
                  onChange={(e) => setFormData({...formData, data_inicio: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Fim (opcional)</label>
                <input
                  type="date"
                  value={formData.data_fim}
                  onChange={(e) => setFormData({...formData, data_fim: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.observacoes}
                onChange={(e) => setFormData({...formData, observacoes: e.target.value})}
                className="w-full px-3 py-2 border rounded-md"
                rows="2"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="gerar_auto"
                checked={formData.gerar_automaticamente}
                onChange={(e) => setFormData({...formData, gerar_automaticamente: e.target.checked})}
                className="rounded"
              />
              <label htmlFor="gerar_auto" className="text-sm text-gray-700">
                Gerar automaticamente (sistema criará os lançamentos)
              </label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => { setShowForm(false); setEditando(null); }}
                className="flex-1 px-4 py-2 border rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Salvando...' : (editando ? 'Atualizar' : 'Criar')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ModalLancamentosRecorrentes;
